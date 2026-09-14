"""
Unit Tests — Agentic Maintenance AI System
Covers: agents, tools, ROI engine, workflow state machine, enterprise systems.
Run: pytest agentic_maintenance/tests/ -v
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

import pytest
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# TEST: CriticalityAssessmentAgent
# ─────────────────────────────────────────────────────────────────────────────
class TestCriticalityAgent:
    def setup_method(self):
        from agentic_maintenance.agents.criticality_agent import CriticalityAssessmentAgent
        self.agent = CriticalityAssessmentAgent()

    def test_bearing_failure_pump_critical(self):
        result = self.agent.assess("P-101", "PUMP", "Bearing Failure", "AI-Predictive")
        assert result["fmea_severity"] == 7
        assert result["fmea_occurrence"] == 6
        assert result["fmea_detectability"] == 2
        assert result["fmea_rpn"] == 84  # 7×6×2
        assert result["criticality"] == "MEDIUM"
        assert "FMEA Assessment" in result["reasoning"]

    def test_catalyst_poisoning_is_high_severity(self):
        result = self.agent.assess("R-301", "REACTOR", "Catalyst Poisoning", "Operator-Report")
        assert result["fmea_severity"] == 9
        assert result["criticality"] in ("HIGH", "CRITICAL")

    def test_rpn_calculation(self):
        result = self.agent.assess("K-201", "COMPRESSOR", "Valve Failure", "SCADA-Alert")
        expected_rpn = result["fmea_severity"] * result["fmea_occurrence"] * result["fmea_detectability"]
        assert result["fmea_rpn"] == expected_rpn

    def test_risk_score_bounded(self):
        result = self.agent.assess("PSV-501", "SAFETY_VALVE", "Inspection Overdue", "No-Monitoring")
        assert 0.0 <= result["risk_score"] <= 10.0

    def test_ai_detection_lowest_detectability(self):
        r1 = self.agent.assess("P-101", "PUMP", "Bearing Failure", "AI-Predictive")
        r2 = self.agent.assess("P-101", "PUMP", "Bearing Failure", "No-Monitoring")
        assert r1["fmea_rpn"] < r2["fmea_rpn"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST: PredictiveDiagnosticsAgent
# ─────────────────────────────────────────────────────────────────────────────
class TestDiagnosticsAgent:
    def setup_method(self):
        from agentic_maintenance.agents.diagnostics_agent import PredictiveDiagnosticsAgent
        from agentic_maintenance.llm_client import MockLLM
        self.agent = PredictiveDiagnosticsAgent(llm=MockLLM())

    def test_bearing_anomaly_detection(self):
        # 8.4 mm/s > alert_threshold (7.1) but < critical_threshold (11.2) → ALERT, not CRITICAL
        sensor_data = {
            "latest": {"vibration_nde": 8.4, "bearing_temp_nde": 94.0, "vibration_de": 2.5},
            "n_samples": 48,
        }
        result = self.agent.diagnose("P-101", "PUMP", sensor_data, scenario="bearing_vibration_anomaly")
        assert result["failure_mode"] == "Bearing Failure"
        assert result["anomaly_count"] > 0
        # 8.4 mm/s is above alert (7.1) but below critical (11.2) → ALERT severity only
        assert not result["has_critical_anomaly"]
        assert result["predicted_failure_hours"] == 48

    def test_bearing_anomaly_at_critical_threshold(self):
        # Values above CRITICAL thresholds → has_critical_anomaly = True
        sensor_data = {
            "latest": {"vibration_nde": 12.5, "bearing_temp_nde": 115.0},
            "n_samples": 10,
        }
        result = self.agent.diagnose("P-101", "PUMP", sensor_data, scenario="bearing_vibration_anomaly")
        assert result["has_critical_anomaly"]

    def test_no_anomaly_on_normal_data(self):
        sensor_data = {"latest": {"vibration_nde": 2.1, "bearing_temp_nde": 72.0}, "n_samples": 48}
        result = self.agent.diagnose("P-101", "PUMP", sensor_data)
        assert result["anomaly_count"] == 0
        assert not result["has_critical_anomaly"]

    def test_compressor_valve_failure(self):
        sensor_data = {
            "latest": {
                "discharge_temp": 128.0,
                "valve_temp_stage1": 135.0,
                "efficiency": 0.71,
            },
            "n_samples": 24,
        }
        result = self.agent.diagnose("K-201", "COMPRESSOR", sensor_data, scenario="compressor_valve_failure")
        assert result["failure_mode"] == "Discharge Valve Failure"
        assert result["predicted_failure_hours"] == 24

    def test_llm_narrative_generated(self):
        sensor_data = {"latest": {"vibration_nde": 8.4}, "n_samples": 10}
        result = self.agent.diagnose("P-101", "PUMP", sensor_data, scenario="bearing_vibration_anomaly")
        assert len(result["llm_narrative"]) > 50


# ─────────────────────────────────────────────────────────────────────────────
# TEST: ROI Engine
# ─────────────────────────────────────────────────────────────────────────────
class TestROIEngine:
    def test_incident_roi_calculation(self):
        from agentic_maintenance.roi.roi_engine import calculate_incident_roi
        result = calculate_incident_roi(
            equipment_id="P-101",
            maintenance_cost_usd=8500,
            downtime_hours_avoided=64,
            labor_hours=8.0,
            parts_cost_usd=690.0,
        )
        # Avoided cost = 64h × 85000 × 0.22 = 1,196,800
        assert result["avoided_downtime_cost_usd"] == pytest.approx(1_196_800, rel=0.01)
        assert result["net_savings_usd"] > 0
        assert result["roi_pct"] > 0

    def test_cumulative_roi_structure(self):
        from agentic_maintenance.roi.roi_engine import calculate_cumulative_roi
        result = calculate_cumulative_roi()
        assert "summary" in result
        assert "kpis" in result
        assert result["summary"]["total_incidents"] > 0
        assert result["summary"]["cumulative_roi_pct"] > 0

    def test_monthly_trend_12_months(self):
        from agentic_maintenance.roi.roi_engine import get_monthly_roi_trend
        trend = get_monthly_roi_trend()
        assert len(trend) >= 10  # at least 10 months of data
        for row in trend:
            assert "month" in row
            assert "avoided_cost" in row
            assert "cumulative_savings" in row

    def test_roi_zero_maintenance_cost_guard(self):
        from agentic_maintenance.roi.roi_engine import calculate_incident_roi
        # Should not raise ZeroDivisionError
        result = calculate_incident_roi("P-101", 0, 10)
        assert result["roi_pct"] == 0.0

    def test_net_savings_formula(self):
        from agentic_maintenance.roi.roi_engine import calculate_incident_roi
        avoided = 100 * 85000 * 0.22
        maint = 50000
        result = calculate_incident_roi("K-201", maint, 100)
        assert result["net_savings_usd"] == pytest.approx(avoided - maint, rel=0.05)


# ─────────────────────────────────────────────────────────────────────────────
# TEST: Inventory Tools
# ─────────────────────────────────────────────────────────────────────────────
class TestInventoryTools:
    def test_parts_checker_available(self):
        from agentic_maintenance.tools.inventory_tools import parts_inventory_checker
        result = parts_inventory_checker(["SKF-6315-C3"])
        assert result["parts"]["SKF-6315-C3"]["available"]
        assert result["total_parts_cost_usd"] == 285.0

    def test_parts_checker_out_of_stock(self):
        from agentic_maintenance.tools.inventory_tools import parts_inventory_checker
        result = parts_inventory_checker(["discharge_valve_stage1_K201"])
        assert not result["parts"]["discharge_valve_stage1_K201"]["available"]
        assert "discharge_valve_stage1_K201" in result["items_on_backorder"]

    def test_unknown_part_handled(self):
        from agentic_maintenance.tools.inventory_tools import parts_inventory_checker
        result = parts_inventory_checker(["UNKNOWN-PART-99999"])
        assert not result["parts"]["UNKNOWN-PART-99999"]["available"]

    def test_cost_estimator_output(self):
        from agentic_maintenance.tools.inventory_tools import cost_estimator
        result = cost_estimator(labor_hours=8, parts_cost=690, downtime_hours=10)
        assert result["labor_cost_usd"] == 8 * 95
        assert result["parts_cost_usd"] == 690
        assert result["total_maintenance_cost_usd"] == result["labor_cost_usd"] + 690
        assert result["downtime_production_loss_usd"] == pytest.approx(10 * 85000 * 0.22, rel=0.01)

    def test_cost_estimator_total_includes_downtime(self):
        from agentic_maintenance.tools.inventory_tools import cost_estimator
        result = cost_estimator(labor_hours=0, parts_cost=0, downtime_hours=5)
        assert result["total_cost_with_downtime_usd"] == pytest.approx(5 * 85000 * 0.22, rel=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# TEST: SCADA Simulator
# ─────────────────────────────────────────────────────────────────────────────
class TestSCADASimulator:
    def test_pump_sensor_data_structure(self):
        from agentic_maintenance.enterprise_systems.scada_simulator import get_sensor_data
        result = get_sensor_data("P-101", time_range_hours=24)
        assert result["equipment_id"] == "P-101"
        assert result["equipment_type"] == "PUMP"
        assert "vibration_nde" in result["channels"]
        assert "bearing_temp_nde" in result["channels"]
        assert len(result["timestamps"]) == result["n_samples"]

    def test_anomaly_injection_raises_vibration(self):
        from agentic_maintenance.enterprise_systems.scada_simulator import get_sensor_data
        normal = get_sensor_data("P-101", 24)
        anomaly = get_sensor_data("P-101", 24, inject_anomaly_scenario="bearing_vibration_anomaly")
        # Last value in anomaly should be higher than normal
        assert anomaly["channels"]["vibration_nde"][-1] > normal["channels"]["vibration_nde"][-1]

    def test_compressor_has_discharge_temp(self):
        from agentic_maintenance.enterprise_systems.scada_simulator import get_sensor_data
        result = get_sensor_data("K-201", 12)
        assert "discharge_temp" in result["channels"]
        assert result["equipment_type"] == "COMPRESSOR"

    def test_latest_dict_matches_last_sample(self):
        from agentic_maintenance.enterprise_systems.scada_simulator import get_sensor_data
        result = get_sensor_data("P-101", 6)
        for ch, val in result["latest"].items():
            assert val == result["channels"][ch][-1]


# ─────────────────────────────────────────────────────────────────────────────
# TEST: CMMS Simulator
# ─────────────────────────────────────────────────────────────────────────────
class TestCMMSSimulator:
    def test_create_work_order(self):
        from agentic_maintenance.enterprise_systems.cmms_simulator import create_work_order, get_work_order
        wo = create_work_order(
            equipment_id="P-101",
            title="Test WO",
            description="Test description",
            priority="HIGH",
            maintenance_type="PdM",
            failure_mode="Bearing Failure",
            labor_hours=8.0,
            parts_list=["SKF-6315-C3"],
            estimated_cost_usd=9000,
            safety_requirements=["LOTO"],
            assigned_crew=["J.Smith"],
        )
        assert wo["work_order_id"].startswith("WO-")
        assert wo["status"] == "DRAFT"
        fetched = get_work_order(wo["work_order_id"])
        assert fetched is not None
        assert fetched["equipment_id"] == "P-101"

    def test_approve_work_order(self):
        from agentic_maintenance.enterprise_systems.cmms_simulator import create_work_order, approve_work_order
        wo = create_work_order(
            equipment_id="P-102", title="Test Approval WO", description="desc",
            priority="MEDIUM", maintenance_type="PM", failure_mode="Bearing Failure",
            labor_hours=4.0, parts_list=[], estimated_cost_usd=500,
            safety_requirements=[], assigned_crew=[],
        )
        updated = approve_work_order(wo["work_order_id"], "TestApprover", "APPROVED", "Test approved")
        assert updated["status"] == "APPROVED"
        assert len(updated["approvals"]) == 1

    def test_maintenance_history_seeded(self):
        from agentic_maintenance.enterprise_systems.cmms_simulator import get_equipment_maintenance_history
        history = get_equipment_maintenance_history("P-101")
        assert len(history) > 0

    def test_mtbf_calculation(self):
        from agentic_maintenance.enterprise_systems.cmms_simulator import calculate_mtbf
        # We have seeded CM records, so MTBF may or may not be calculable
        mtbf = calculate_mtbf("P-101")
        # If calculable, must be positive
        if mtbf is not None:
            assert mtbf > 0


# ─────────────────────────────────────────────────────────────────────────────
# TEST: Workflow State Machine
# ─────────────────────────────────────────────────────────────────────────────
class TestStateMachine:
    def test_workflow_creation(self):
        from agentic_maintenance.workflow.state_machine import WorkflowRegistry, WorkflowState
        reg = WorkflowRegistry()
        wf = reg.create("P-101", "Test alert")
        assert wf.state == WorkflowState.ALERT_DETECTED
        assert wf.workflow_id.startswith("WF-")
        assert len(wf.audit_trail) == 1

    def test_valid_transition(self):
        from agentic_maintenance.workflow.state_machine import WorkflowRegistry, WorkflowState
        reg = WorkflowRegistry()
        wf = reg.create("P-101", "Test alert")
        wf.transition(WorkflowState.DIAGNOSIS_IN_PROGRESS, actor="test")
        assert wf.state == WorkflowState.DIAGNOSIS_IN_PROGRESS
        assert len(wf.audit_trail) == 2

    def test_invalid_transition_raises(self):
        from agentic_maintenance.workflow.state_machine import WorkflowRegistry, WorkflowState
        reg = WorkflowRegistry()
        wf = reg.create("P-101", "Test alert")
        with pytest.raises(ValueError):
            wf.transition(WorkflowState.ROI_CALCULATED, actor="test")

    def test_agent_reasoning_logged(self):
        from agentic_maintenance.workflow.state_machine import WorkflowRegistry
        reg = WorkflowRegistry()
        wf = reg.create("K-201", "Compressor alert")
        wf.log_agent_reasoning("TestAgent", "Some reasoning", "Some decision")
        assert len(wf.agent_reasoning) == 1
        assert wf.agent_reasoning[0]["agent"] == "TestAgent"

    def test_full_state_path(self):
        from agentic_maintenance.workflow.state_machine import WorkflowRegistry, WorkflowState
        reg = WorkflowRegistry()
        wf = reg.create("E-401", "HX alert")
        path = [
            WorkflowState.DIAGNOSIS_IN_PROGRESS,
            WorkflowState.WORK_ORDER_DRAFTED,
            WorkflowState.PENDING_HUMAN_APPROVAL,
            WorkflowState.APPROVED,
            WorkflowState.SCHEDULED,
            WorkflowState.EXECUTED,
            WorkflowState.CLOSED,
            WorkflowState.ROI_CALCULATED,
        ]
        for state in path:
            wf.transition(state, actor="test")
        assert wf.state == WorkflowState.ROI_CALCULATED

    def test_registry_active_filter(self):
        from agentic_maintenance.workflow.state_machine import WorkflowRegistry, WorkflowState
        reg = WorkflowRegistry()
        wf1 = reg.create("P-101", "Alert 1")
        wf2 = reg.create("P-102", "Alert 2")
        # Complete wf2
        wf2.transition(WorkflowState.DIAGNOSIS_IN_PROGRESS)
        wf2.transition(WorkflowState.WORK_ORDER_DRAFTED)
        wf2.transition(WorkflowState.PENDING_HUMAN_APPROVAL)
        wf2.transition(WorkflowState.APPROVED)
        wf2.transition(WorkflowState.SCHEDULED)
        wf2.transition(WorkflowState.EXECUTED)
        wf2.transition(WorkflowState.CLOSED)
        wf2.transition(WorkflowState.ROI_CALCULATED)
        active = reg.get_active()
        assert wf1 in active
        assert wf2 not in active


# ─────────────────────────────────────────────────────────────────────────────
# TEST: Compliance Agent
# ─────────────────────────────────────────────────────────────────────────────
class TestComplianceAgent:
    def setup_method(self):
        from agentic_maintenance.agents.compliance_agent import ComplianceAgent
        self.agent = ComplianceAgent()

    def test_psv_overdue_non_compliant(self):
        result = self.agent.check("PSV-501", "SAFETY_VALVE", "safety_valve_overdue")
        assert result["compliance_status"] == "NON_COMPLIANT"
        assert result["violation_count"] >= 1
        assert result["requires_regulatory_notification"]

    def test_reactor_compliant(self):
        result = self.agent.check("R-301", "REACTOR", "reactor_fouling")
        assert result["violation_count"] == 0
        assert result["compliance_status"] == "COMPLIANT"

    def test_applicable_rules_returned(self):
        result = self.agent.check("K-201", "COMPRESSOR", "compressor_valve_failure")
        assert len(result["applicable_rules"]) > 0

    def test_reasoning_generated(self):
        result = self.agent.check("P-101", "PUMP", None)
        assert "ComplianceAgent" in result["reasoning"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST: Notification Tools
# ─────────────────────────────────────────────────────────────────────────────
class TestNotificationTools:
    def test_critical_dispatches_email_and_sms(self):
        from agentic_maintenance.tools.notification_tools import notification_sender
        result = notification_sender(["test@example.com"], "Test message", "CRITICAL", work_order_id="WO-TEST")
        assert result["dispatched"] == 2  # email + sms
        assert "email" in result["channels"]
        assert "sms" in result["channels"]

    def test_medium_dispatches_email_only(self):
        from agentic_maintenance.tools.notification_tools import notification_sender
        result = notification_sender(["test@example.com"], "Test message", "MEDIUM")
        assert "email" in result["channels"]
        assert "sms" not in result["channels"]

    def test_log_filtering_by_wo(self):
        from agentic_maintenance.tools.notification_tools import notification_sender, get_notification_log
        notification_sender(["a@b.com"], "msg", "HIGH", work_order_id="WO-FILTER-TEST")
        log = get_notification_log(work_order_id="WO-FILTER-TEST")
        assert any(e["work_order_id"] == "WO-FILTER-TEST" for e in log)


# ─────────────────────────────────────────────────────────────────────────────
# TEST: WorkOrderGenerationAgent
# ─────────────────────────────────────────────────────────────────────────────
class TestWorkOrderAgent:
    def setup_method(self):
        from agentic_maintenance.agents.work_order_agent import WorkOrderGenerationAgent
        self.agent = WorkOrderGenerationAgent()

    def test_bearing_vibration_work_order(self):
        result = self.agent.generate(
            equipment_id="P-101", equipment_type="PUMP",
            failure_mode="Bearing Failure", scenario="bearing_vibration_anomaly",
            criticality="HIGH", risk_score=8.0, fmea_rpn=192,
            diagnosis_result={"llm_narrative": "Test narrative"},
        )
        assert result["priority"] in ("URGENT", "HIGH", "EMERGENCY")
        assert "SKF" in str(result["parts_list"])
        assert result["labor_hours"] == 8.0
        assert result["estimated_cost_usd"] > 0

    def test_emergency_overrides_priority(self):
        result = self.agent.generate(
            equipment_id="K-201", equipment_type="COMPRESSOR",
            failure_mode="Discharge Valve Failure", scenario="compressor_valve_failure",
            criticality="CRITICAL", risk_score=9.5, fmea_rpn=350,
            diagnosis_result={"llm_narrative": "Test"},
        )
        assert result["priority"] == "EMERGENCY"

    def test_reasoning_in_output(self):
        result = self.agent.generate(
            equipment_id="E-401", equipment_type="HEAT_EXCHANGER",
            failure_mode="Tube Bundle Tube Leak", scenario="heat_exchanger_tube_leak",
            criticality="HIGH", risk_score=7.5, fmea_rpn=240,
            diagnosis_result={"llm_narrative": "Test"},
        )
        assert "WorkOrderGenerationAgent" in result["ai_reasoning"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST: HSE Simulator
# ─────────────────────────────────────────────────────────────────────────────
class TestHSESimulator:
    def test_overdue_inspections_returned(self):
        from agentic_maintenance.enterprise_systems.hse_simulator import get_overdue_inspections
        overdue = get_overdue_inspections()
        assert len(overdue) > 0
        assert any(item["equipment_id"] == "PSV-501" for item in overdue)

    def test_jsa_requirements(self):
        from agentic_maintenance.enterprise_systems.hse_simulator import get_jsa_requirements
        result = get_jsa_requirements("PUMP", "Flammable")
        assert "LOTO (Lockout/Tagout)" in result["base_precautions"]
        assert "Mechanical Isolation PTW" in result["required_permits"]
        assert len(result["ppe_requirements"]) > 0

    def test_ptw_issuance(self):
        from agentic_maintenance.enterprise_systems.hse_simulator import issue_permit_to_work
        permit = issue_permit_to_work(
            work_order_id="WO-TEST",
            equipment_id="P-101",
            permit_type="Mechanical Isolation PTW",
            hazards=["Flammable fluid"],
            precautions=["LOTO", "Gas test"],
        )
        assert permit["permit_id"].startswith("PTW-")
        assert permit["status"] == "ACTIVE"

    def test_compliance_check(self):
        from agentic_maintenance.enterprise_systems.hse_simulator import check_compliance_status
        result = check_compliance_status("PSV-501")
        assert not result["overall_compliant"]

# ─────────────────────────────────────────────────────────────────────────────
# TEST: Tools Layer wrappers
# ─────────────────────────────────────────────────────────────────────────────
class TestSensorTools:
    def test_sensor_data_fetcher(self):
        from agentic_maintenance.tools.sensor_tools import sensor_data_fetcher
        result = sensor_data_fetcher("P-101", time_range_hours=12)
        assert result["equipment_id"] == "P-101"
        assert "latest" in result

    def test_sensor_data_fetcher_with_anomaly(self):
        from agentic_maintenance.tools.sensor_tools import sensor_data_fetcher
        result = sensor_data_fetcher("P-101", time_range_hours=6, inject_anomaly_scenario="bearing_vibration_anomaly")
        assert result["anomaly_injected"] == "bearing_vibration_anomaly"

    def test_process_snapshot(self):
        from agentic_maintenance.tools.sensor_tools import get_process_snapshot
        result = get_process_snapshot()
        assert "P-101" in result
        assert "K-201" in result


class TestCMMSTools:
    def test_equipment_history_lookup(self):
        from agentic_maintenance.tools.cmms_tools import equipment_history_lookup
        result = equipment_history_lookup("P-101")
        assert result["equipment_id"] == "P-101"
        assert "maintenance_history" in result

    def test_get_equipment_catalog(self):
        from agentic_maintenance.tools.cmms_tools import get_equipment_catalog
        catalog = get_equipment_catalog()
        assert len(catalog) >= 10
        assert any(e["id"] == "P-101" for e in catalog)

    def test_dispatch_work_order(self):
        from agentic_maintenance.tools.cmms_tools import dispatch_work_order, get_work_order
        wo = dispatch_work_order(
            equipment_id="K-202",
            title="Test dispatch",
            description="Test",
            priority="MEDIUM",
            maintenance_type="PdM",
            failure_mode="Bearing Failure",
            labor_hours=4.0,
            parts_list=[],
            estimated_cost_usd=2000,
            safety_requirements=["LOTO"],
            assigned_crew=["Technician"],
        )
        assert wo["work_order_id"].startswith("WO-")


class TestSafetyTools:
    def test_safety_procedure_retriever(self):
        from agentic_maintenance.tools.safety_tools import safety_procedure_retriever
        result = safety_procedure_retriever("COMPRESSOR", "Flammable/Explosive")
        assert "Nitrogen purge before opening" in result["hazard_specific_precautions"]
        assert len(result["required_permits"]) > 0

    def test_check_regulatory_compliance(self):
        from agentic_maintenance.tools.safety_tools import check_regulatory_compliance
        result = check_regulatory_compliance("PSV-501")
        assert result["has_overdue_inspections"]

    def test_get_all_overdue_inspections(self):
        from agentic_maintenance.tools.safety_tools import get_all_overdue_inspections
        overdue = get_all_overdue_inspections()
        assert len(overdue) > 0

    def test_raise_regulatory_notification(self):
        from agentic_maintenance.tools.safety_tools import raise_regulatory_notification
        result = raise_regulatory_notification(
            "PSV-501", "Overdue Inspection", "OSHA", "PSV inspection overdue"
        )
        assert result["notification_required"]


class TestROIAgent:
    def test_roi_agent_calculate(self):
        from agentic_maintenance.agents.roi_agent import ROICalculationAgent
        agent = ROICalculationAgent()
        result = agent.calculate(
            workflow_id="WF-TEST-001",
            equipment_id="P-101",
            scenario="bearing_vibration_anomaly",
            maintenance_cost_usd=8500,
            labor_hours=8.0,
            parts_cost_usd=690.0,
        )
        assert result["net_savings_usd"] > 0
        assert result["roi_pct"] > 0
        assert "reasoning" in result
        assert result["workflow_id"] == "WF-TEST-001"


class TestOrchestratorIntegration:
    def test_full_pipeline_bearing_scenario(self):
        """Integration test: full pipeline executes without error."""
        from agentic_maintenance.agents.orchestrator import MaintenanceOrchestrator
        orch = MaintenanceOrchestrator(offline_mode=True)
        result = orch.run_pipeline(
            equipment_id="P-101",
            alert_description="Test bearing alert",
            scenario="bearing_vibration_anomaly",
            auto_approve=False,
            prefill_decision="APPROVED",
            interactive=False,
        )
        assert result["final_state"] == "ROI_CALCULATED"
        assert result["outcome"] == "EXECUTED"
        assert "roi" in result

    def test_pipeline_compressor_scenario(self):
        from agentic_maintenance.agents.orchestrator import MaintenanceOrchestrator
        orch = MaintenanceOrchestrator(offline_mode=True)
        result = orch.run_pipeline(
            equipment_id="K-201",
            alert_description="Compressor valve failure",
            scenario="compressor_valve_failure",
            auto_approve=False,
            prefill_decision="APPROVED",
            interactive=False,
        )
        assert result["final_state"] == "ROI_CALCULATED"

    def test_pipeline_rejection(self):
        from agentic_maintenance.agents.orchestrator import MaintenanceOrchestrator
        orch = MaintenanceOrchestrator(offline_mode=True)
        result = orch.run_pipeline(
            equipment_id="E-401",
            alert_description="HX tube leak",
            scenario="heat_exchanger_tube_leak",
            auto_approve=False,
            prefill_decision="REJECTED",
            interactive=False,
        )
        assert result["outcome"] == "REJECTED"
        assert result["final_state"] == "REJECTED"
