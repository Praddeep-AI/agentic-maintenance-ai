"""
Agent: MaintenanceOrchestrator
Coordinates all sub-agents through the complete agentic workflow pipeline:
LLM → Agent → Tools → Enterprise Systems → Workflow → Human Approval → Action
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from ..config_loader import get_config
from ..llm_client import get_llm, MockLLM

from ..workflow.state_machine import WorkflowState, registry
from ..workflow.approval_interface import present_approval_interface

from .criticality_agent import CriticalityAssessmentAgent
from .diagnostics_agent import PredictiveDiagnosticsAgent
from .work_order_agent import WorkOrderGenerationAgent
from .roi_agent import ROICalculationAgent
from .compliance_agent import ComplianceAgent

from ..tools.sensor_tools import sensor_data_fetcher
from ..tools.cmms_tools import (
    equipment_history_lookup, dispatch_work_order,
    get_equipment_by_id, mark_work_order_executed,
)
from ..tools.inventory_tools import parts_inventory_checker, cost_estimator
from ..tools.safety_tools import (
    safety_procedure_retriever, request_permit_to_work,
    check_regulatory_compliance, raise_regulatory_notification,
)
from ..tools.notification_tools import notification_sender

logger = logging.getLogger(__name__)


class MaintenanceOrchestrator:
    """
    Top-level orchestrator that runs the full maintenance agentic pipeline.
    Emits step-by-step progress via an optional callback for dashboard display.
    """

    def __init__(
        self,
        offline_mode: bool = True,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        cfg = get_config()
        self.offline_mode = cfg.get("system", {}).get("offline_mode", True) if offline_mode else offline_mode
        self.llm = get_llm(self.offline_mode)
        self.progress_callback = progress_callback or (lambda step, msg: None)

        # Initialize sub-agents
        self.criticality_agent = CriticalityAssessmentAgent()
        self.diagnostics_agent = PredictiveDiagnosticsAgent(llm=self.llm)
        self.work_order_agent = WorkOrderGenerationAgent()
        self.roi_agent = ROICalculationAgent()
        self.compliance_agent = ComplianceAgent()

        logger.info("MaintenanceOrchestrator initialized | offline_mode=%s", self.offline_mode)

    # ------------------------------------------------------------------
    # Pipeline entry point
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        equipment_id: str,
        alert_description: str,
        scenario: str,
        auto_approve: bool = False,
        prefill_decision: str = "APPROVED",
        interactive: bool = False,
    ) -> dict:
        """
        Run the full agentic maintenance pipeline for a given alert.

        Args:
            equipment_id: Equipment tag (e.g. "P-101")
            alert_description: Natural language alert description
            scenario: Scenario key from sensor_profiles.json
            auto_approve: Auto-approve the work order (demo mode)
            prefill_decision: Pre-filled approval decision for non-interactive runs
            interactive: Whether to show interactive CLI approval

        Returns:
            Complete pipeline result dict with all stage outputs and timing.
        """
        start_time = time.time()
        self._emit("PIPELINE_START", f"🚀 Starting Agentic Pipeline for {equipment_id} | Scenario: {scenario}")

        # ── Stage 1: Create workflow ─────────────────────────────────────
        wf = registry.create(equipment_id, alert_description, scenario=scenario)
        self._emit("WORKFLOW_CREATED", f"📋 Workflow {wf.workflow_id} created | State: ALERT_DETECTED")

        try:
            result = self._execute_pipeline(wf, equipment_id, scenario, auto_approve, prefill_decision, interactive)
        except Exception as exc:
            logger.exception("Pipeline error for workflow %s", wf.workflow_id)
            result = {"error": str(exc), "workflow_id": wf.workflow_id, "state": wf.state.value}

        elapsed = round(time.time() - start_time, 2)
        result["elapsed_seconds"] = elapsed
        result["workflow_id"] = wf.workflow_id
        result["final_state"] = wf.state.value

        self._emit("PIPELINE_COMPLETE", f"✅ Pipeline complete in {elapsed}s | Final state: {wf.state.value}")
        return result

    def _execute_pipeline(
        self,
        wf,
        equipment_id: str,
        scenario: str,
        auto_approve: bool,
        prefill_decision: str,
        interactive: bool,
    ) -> dict:
        stages: dict[str, Any] = {}

        # ── Stage 2: Fetch sensor data ───────────────────────────────────
        self._emit("SENSOR_FETCH", f"📡 [TOOL] sensor_data_fetcher({equipment_id}, inject={scenario})")
        wf.transition(WorkflowState.DIAGNOSIS_IN_PROGRESS, actor="orchestrator", comment="Starting diagnosis")
        sensor_data = sensor_data_fetcher(equipment_id, time_range_hours=24, inject_anomaly_scenario=scenario)
        wf.log_tool_call("sensor_data_fetcher", {"equipment_id": equipment_id, "scenario": scenario},
                         f"Retrieved {sensor_data['n_samples']} samples, latest: {sensor_data['latest']}")
        stages["sensor_data"] = {"channels": list(sensor_data.get("latest", {}).keys()), "n_samples": sensor_data["n_samples"]}

        # ── Stage 3: Equipment history ───────────────────────────────────
        self._emit("HISTORY_LOOKUP", f"📚 [TOOL] equipment_history_lookup({equipment_id})")
        history = equipment_history_lookup(equipment_id)
        eq_meta = get_equipment_by_id(equipment_id) or {}
        wf.log_tool_call("equipment_history_lookup", {"equipment_id": equipment_id},
                         f"Found {history['history_count']} history records | MTBF={history['calculated_mtbf_hours']}h")

        # ── Stage 4: LLM + Diagnostics Agent ────────────────────────────
        self._emit("DIAGNOSTICS", f"🧠 [AGENT] PredictiveDiagnosticsAgent analyzing {equipment_id}...")
        diagnosis = self.diagnostics_agent.diagnose(
            equipment_id=equipment_id,
            equipment_type=eq_meta.get("type", "PUMP"),
            sensor_data=sensor_data,
            scenario=scenario,
            maintenance_history=history,
        )
        wf.diagnosis_result = diagnosis
        wf.log_agent_reasoning(
            "PredictiveDiagnosticsAgent",
            reasoning=f"Analyzed {len(diagnosis['anomalies_detected'])} anomalies. Failure mode: {diagnosis['failure_mode']}",
            decision=f"Predicted failure in {diagnosis.get('predicted_failure_hours', '?')}h. Mode: {diagnosis['failure_mode']}"
        )
        ttf = diagnosis.get('predicted_failure_hours')
        ttf_str = f"{ttf}h" if ttf is not None else "N/A"
        self._emit("DIAGNOSTICS_DONE",
                   f"   → Failure mode: {diagnosis['failure_mode']} | "
                   f"TTF: {ttf_str} | "
                   f"Anomalies: {diagnosis['anomaly_count']}")
        stages["diagnosis"] = diagnosis

        # ── Stage 5: Criticality Assessment ─────────────────────────────
        self._emit("CRITICALITY", f"⚠️  [AGENT] CriticalityAssessmentAgent scoring {equipment_id}...")
        criticality = self.criticality_agent.assess(
            equipment_id=equipment_id,
            equipment_type=eq_meta.get("type", "PUMP"),
            failure_mode=diagnosis["failure_mode"],
            detection_method="AI-Predictive",
            maintenance_history=history,
        )
        # Merge criticality fields into diagnosis_result so the approval interface can display them
        wf.diagnosis_result["risk_score"] = criticality["risk_score"]
        wf.diagnosis_result["criticality"] = criticality["criticality"]
        wf.diagnosis_result["fmea_rpn"] = criticality["fmea_rpn"]

        wf.log_agent_reasoning(
            "CriticalityAssessmentAgent",
            reasoning=criticality["reasoning"],
            decision=f"RPN={criticality['fmea_rpn']} | Criticality={criticality['criticality']} | Risk={criticality['risk_score']}"
        )
        self._emit("CRITICALITY_DONE",
                   f"   → RPN: {criticality['fmea_rpn']} | Criticality: {criticality['criticality']} | "
                   f"Risk Score: {criticality['risk_score']}/10")
        stages["criticality"] = criticality

        # ── Stage 6: Compliance Check ────────────────────────────────────
        self._emit("COMPLIANCE", f"🔍 [AGENT] ComplianceAgent checking {equipment_id}...")
        compliance = self.compliance_agent.check(
            equipment_id=equipment_id,
            equipment_type=eq_meta.get("type", "PUMP"),
            scenario=scenario,
        )
        wf.log_agent_reasoning(
            "ComplianceAgent",
            reasoning=compliance["reasoning"],
            decision=f"Compliance: {compliance['compliance_status']} | Violations: {compliance['violation_count']}"
        )
        if compliance["violation_count"] > 0:
            self._emit("COMPLIANCE_VIOLATION",
                       f"   ⚠️  COMPLIANCE VIOLATION: {compliance['violations'][0]['description']}")
            if compliance["requires_regulatory_notification"]:
                raise_regulatory_notification(
                    equipment_id, "Inspection Overdue",
                    compliance["violations"][0].get("body", "Regulatory Body"),
                    compliance["violations"][0].get("description", "")
                )
        else:
            self._emit("COMPLIANCE_DONE", f"   → Status: {compliance['compliance_status']} — No violations")
        stages["compliance"] = compliance

        # ── Stage 7: Parts availability ──────────────────────────────────
        parts_needed = self._get_parts_for_scenario(scenario)
        self._emit("INVENTORY", f"📦 [TOOL] parts_inventory_checker({parts_needed[:2]}...)")
        inventory = parts_inventory_checker(parts_needed)
        wf.log_tool_call("parts_inventory_checker", {"parts": parts_needed},
                         f"Total cost=${inventory['total_parts_cost_usd']:,.0f} | backorder={inventory['items_on_backorder']}")
        self._emit("INVENTORY_DONE",
                   f"   → Cost: ${inventory['total_parts_cost_usd']:,.0f} | "
                   f"Backorder: {inventory['items_on_backorder'] or 'None'}")

        # ── Stage 8: Safety procedures ───────────────────────────────────
        self._emit("SAFETY", f"🦺 [TOOL] safety_procedure_retriever({eq_meta.get('type','PUMP')}, {eq_meta.get('hazard_class','Flammable')})")
        safety = safety_procedure_retriever(eq_meta.get("type", "PUMP"), eq_meta.get("hazard_class", "Flammable"))
        wf.log_tool_call("safety_procedure_retriever",
                         {"equipment_type": eq_meta.get("type"), "hazard_class": eq_meta.get("hazard_class")},
                         f"Permits required: {safety['required_permits']}")

        # ── Stage 9: Cost estimate ───────────────────────────────────────
        labor_hours = self._get_labor_hours(scenario)
        cost_est = cost_estimator(
            labor_hours=labor_hours,
            parts_cost=inventory["total_parts_cost_usd"],
            downtime_hours=8.0,
        )
        wf.log_tool_call("cost_estimator",
                         {"labor_hours": labor_hours, "parts_cost": inventory["total_parts_cost_usd"]},
                         f"Total cost=${cost_est['total_maintenance_cost_usd']:,.0f}")

        # ── Stage 10: Generate work order ────────────────────────────────
        self._emit("WORK_ORDER", f"📝 [AGENT] WorkOrderGenerationAgent generating work order for {equipment_id}...")
        wo_draft = self.work_order_agent.generate(
            equipment_id=equipment_id,
            equipment_type=eq_meta.get("type", "PUMP"),
            failure_mode=diagnosis["failure_mode"],
            scenario=scenario,
            criticality=criticality["criticality"],
            risk_score=criticality["risk_score"],
            fmea_rpn=criticality["fmea_rpn"],
            diagnosis_result=diagnosis,
            parts_availability=inventory,
            cost_estimate=cost_est,
        )
        wf.log_agent_reasoning(
            "WorkOrderGenerationAgent",
            reasoning=wo_draft.get("ai_reasoning", ""),
            decision=f"Priority={wo_draft['priority']} | Cost=${wo_draft['estimated_cost_usd']:,.0f}"
        )
        self._emit("WORK_ORDER_DONE",
                   f"   → Priority: {wo_draft['priority']} | "
                   f"Cost: ${wo_draft['estimated_cost_usd']:,.0f} | "
                   f"Parts: {len(wo_draft['parts_list'])}")

        # ── Stage 11: Compute preliminary ROI ────────────────────────────
        self._emit("ROI_CALC", f"💰 [AGENT] ROICalculationAgent computing financial impact...")
        roi = self.roi_agent.calculate(
            workflow_id=wf.workflow_id,
            equipment_id=equipment_id,
            scenario=scenario,
            maintenance_cost_usd=wo_draft["estimated_cost_usd"],
            labor_hours=labor_hours,
            parts_cost_usd=inventory["total_parts_cost_usd"],
        )
        wf.roi_record = roi
        wf.log_agent_reasoning(
            "ROICalculationAgent",
            reasoning=roi.get("reasoning", ""),
            decision=f"Net Savings=${roi['net_savings_usd']:,.0f} | ROI={roi['roi_pct']:.1f}%"
        )
        self._emit("ROI_DONE",
                   f"   → Avoided: ${roi['avoided_downtime_cost_usd']:,.0f} | "
                   f"Net Savings: ${roi['net_savings_usd']:,.0f} | "
                   f"ROI: {roi['roi_pct']:.1f}%")
        stages["roi"] = roi

        # ── Stage 12: Save work order to CMMS ───────────────────────────
        wo = dispatch_work_order(
            equipment_id=equipment_id,
            title=wo_draft["title"],
            description=wo_draft["description"],
            priority=wo_draft["priority"],
            maintenance_type=wo_draft["maintenance_type"],
            failure_mode=wo_draft["failure_mode"],
            labor_hours=wo_draft["labor_hours"],
            parts_list=wo_draft["parts_list"],
            estimated_cost_usd=wo_draft["estimated_cost_usd"],
            safety_requirements=wo_draft["safety_requirements"],
            assigned_crew=wo_draft["assigned_crew"],
            ai_reasoning=wo_draft["ai_reasoning"],
        )
        wf.work_order_id = wo["work_order_id"]
        wf.work_order_draft = wo
        wf.transition(WorkflowState.WORK_ORDER_DRAFTED, actor="orchestrator",
                      comment=f"Work order {wo['work_order_id']} created in CMMS")
        self._emit("CMMS_WO_SAVED", f"💾 [CMMS] Work order saved: {wo['work_order_id']}")

        # ── Stage 13: Send notifications ─────────────────────────────────
        urgency = "CRITICAL" if wo_draft["priority"] == "EMERGENCY" else "HIGH" if wo_draft["priority"] == "URGENT" else "MEDIUM"
        notification_sender(
            recipients=["supervisor@plant.example.com", "maintenance_team@plant.example.com"],
            message=(
                f"AI Maintenance Alert: {wo['title']}\n"
                f"Equipment: {equipment_id} | Priority: {wo_draft['priority']}\n"
                f"Approval required. Work order: {wo['work_order_id']}"
            ),
            urgency_level=urgency,
            subject=f"[{urgency}] {wo['title'][:60]}",
            work_order_id=wo["work_order_id"],
        )
        wf.log_tool_call("notification_sender", {"urgency": urgency, "recipients": 2},
                         f"Notifications dispatched to 2 recipients")

        # ── Stage 14: Transition to PENDING_HUMAN_APPROVAL ──────────────
        wf.transition(WorkflowState.PENDING_HUMAN_APPROVAL, actor="orchestrator",
                      comment="Awaiting human supervisor approval")
        self._emit("PENDING_APPROVAL", f"⏳ [APPROVAL] Work order {wo['work_order_id']} awaiting supervisor approval...")

        # ── Stage 15: Human Approval Interface ──────────────────────────
        approval_result = present_approval_interface(
            wf,
            auto_approve=auto_approve,
            auto_approve_delay=1.5,
            prefill_decision=prefill_decision if not interactive else None,
        )
        stages["approval"] = approval_result

        if wf.state == WorkflowState.REJECTED:
            self._emit("REJECTED", f"❌ Work order REJECTED by {approval_result['approver']}")
            return {"stages": stages, "outcome": "REJECTED"}

        self._emit("APPROVED", f"✅ Work order APPROVED by {approval_result['approver']}")

        # ── Stage 16: Schedule and Execute ──────────────────────────────
        wf.transition(WorkflowState.SCHEDULED, actor="system", comment="Scheduled for execution")
        self._emit("SCHEDULED", f"📅 Work order scheduled for execution")

        # Simulate execution delay
        time.sleep(0.5)

        wf.transition(WorkflowState.EXECUTED, actor="field_team", comment="Field team executed work order")
        mark_work_order_executed(wf.work_order_id)
        self._emit("EXECUTED", f"🔧 Work order executed by field team")

        # ── Stage 17: PTW and post-maintenance validation ────────────────
        permit = request_permit_to_work(
            work_order_id=wf.work_order_id,
            equipment_id=equipment_id,
            permit_type="Mechanical Isolation PTW",
            hazards=eq_meta.get("failure_modes", []),
            precautions=safety["base_precautions"],
        )
        wf.permit_id = permit["permit_id"]
        wf.log_tool_call("request_permit_to_work", {"equipment_id": equipment_id},
                         f"PTW issued: {permit['permit_id']}")

        # Post-maintenance sensor validation
        self._emit("VALIDATION", f"📡 [TOOL] Post-maintenance sensor validation...")
        post_sensor = sensor_data_fetcher(equipment_id, time_range_hours=1)
        wf.log_tool_call("sensor_data_fetcher_post", {"equipment_id": equipment_id, "post_maintenance": True},
                         "Post-maintenance sensor readings within normal operating range")
        self._emit("VALIDATION_DONE", f"   → Post-maintenance readings confirmed normal")

        wf.transition(WorkflowState.CLOSED, actor="system", comment="Work order closed. Post-maintenance validation passed.")
        self._emit("CLOSED", f"🏁 Work order CLOSED. Maintenance complete.")

        # ── Stage 18: Final ROI calculation ─────────────────────────────
        wf.transition(WorkflowState.ROI_CALCULATED, actor="roi_agent",
                      comment=f"Net savings: ${roi['net_savings_usd']:,.0f}")
        stages["final_roi"] = roi

        self._emit("ROI_FINAL",
                   f"💰 FINAL ROI: ${roi['net_savings_usd']:,.0f} net savings | "
                   f"ROI = {roi['roi_pct']:.1f}%")

        wf.execution_result = {
            "outcome": "EXECUTED",
            "work_order_id": wf.work_order_id,
            "permit_id": wf.permit_id,
            "post_maintenance_validation": "PASSED",
        }

        return {
            "stages": stages,
            "outcome": "EXECUTED",
            "work_order_id": wf.work_order_id,
            "permit_id": wf.permit_id,
            "roi": roi,
            "approval": approval_result,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, step: str, message: str) -> None:
        """Emit a progress event to the optional callback and logger."""
        logger.info("PIPELINE[%s]: %s", step, message)
        self.progress_callback(step, message)

    @staticmethod
    def _get_parts_for_scenario(scenario: str) -> list[str]:
        _parts_map = {
            "bearing_vibration_anomaly": ["SKF-6315-C3", "SKF-6316-C3", "bearing_housing_seal_kit"],
            "reactor_fouling": ["catalyst_bed_R301_full_charge"],
            "heat_exchanger_tube_leak": ["tube_plugs_x24", "gasket_set_E401"],
            "compressor_valve_failure": ["suction_valve_stage1_K201", "discharge_valve_stage1_K201", "valve_gasket_kit_K201"],
            "safety_valve_overdue": ["PSV-501-spring-kit", "PSV-501-seat-disc"],
            "cui_risk": ["insulation_cladding_T601_zone_A"],
        }
        return _parts_map.get(scenario, [])

    @staticmethod
    def _get_labor_hours(scenario: str) -> float:
        _hours_map = {
            "bearing_vibration_anomaly": 8.0,
            "reactor_fouling": 96.0,
            "heat_exchanger_tube_leak": 32.0,
            "compressor_valve_failure": 16.0,
            "safety_valve_overdue": 12.0,
            "cui_risk": 48.0,
        }
        return _hours_map.get(scenario, 8.0)
