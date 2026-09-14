"""
Agent: WorkOrderGenerationAgent
Creates structured maintenance work orders with priority, parts list, crew assignments,
and safety procedures based on diagnostic output.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Work order templates by scenario
_WORK_ORDER_TEMPLATES: dict[str, dict] = {
    "bearing_vibration_anomaly": {
        "title": "URGENT — Bearing Replacement P-101 (NDE Bearing Failure Predicted)",
        "description": (
            "NDE bearing vibration has exceeded ISO 10816 Zone C threshold (8.4 mm/s). "
            "Bearing temperature rising (94°C). Bearing failure predicted within 48 hours. "
            "Switch to standby pump P-101A before commencing work."
        ),
        "maintenance_type": "PdM",
        "failure_mode": "Bearing Failure",
        "labor_hours": 8.0,
        "parts_list": ["SKF-6315-C3", "SKF-6316-C3", "bearing_housing_seal_kit"],
        "assigned_crew": ["J.Smith (Mechanical Fitter)", "A.Kumar (Maintenance Tech)", "M.Al-Rashid (Supervisor)"],
        "safety_requirements": ["LOTO", "Hot Work PTW", "Gas Test", "Mechanical Isolation PTW"],
    },
    "reactor_fouling": {
        "title": "PLANNED — R-301 Catalyst Bed Inspection and Regeneration Planning",
        "description": (
            "Reactor differential pressure at 1.38 bar (58% above baseline). "
            "Catalyst fouling confirmed. Regeneration required within 14 days. "
            "Plan catalyst replacement during next shutdown window."
        ),
        "maintenance_type": "PdM",
        "failure_mode": "Catalyst Fouling",
        "labor_hours": 96.0,
        "parts_list": ["catalyst_bed_R301_full_charge"],
        "assigned_crew": ["S.Chen (Process Engineer)", "J.Smith (Mechanical Fitter)", "A.Kumar (Tech)", "Contractor Team x4"],
        "safety_requirements": ["Process Equipment PTW", "Catalyst Handling PTW", "Confined Space PTW", "Hot Work PTW"],
    },
    "heat_exchanger_tube_leak": {
        "title": "HIGH — E-401 Tube Bundle Inspection and Emergency Tube Plugging",
        "description": (
            "Shell-side temperature cross and pressure drop elevation indicate tube perforation. "
            "Immediate online tube plugging required (up to 10% tube count). "
            "Full bundle replacement to be planned for next turnaround."
        ),
        "maintenance_type": "PdM",
        "failure_mode": "Tube Bundle Tube Leak",
        "labor_hours": 32.0,
        "parts_list": ["tube_plugs_x24", "gasket_set_E401"],
        "assigned_crew": ["J.Smith (Mechanical Fitter)", "A.Kumar (Maintenance Tech)", "S.Chen (Inspector)"],
        "safety_requirements": ["Mechanical Isolation PTW", "Pressure Test PTW", "LOTO", "Hot Work PTW"],
    },
    "compressor_valve_failure": {
        "title": "EMERGENCY — K-201 Stage-1 Discharge Valve Replacement",
        "description": (
            "Stage-1 discharge temperature at 128°C (+28°C above baseline). Efficiency at 0.71. "
            "Valve failure imminent within 24 hours. Transfer load to K-202 before shutdown. "
            "Emergency valve replacement required."
        ),
        "maintenance_type": "CM",
        "failure_mode": "Discharge Valve Failure",
        "labor_hours": 16.0,
        "parts_list": ["suction_valve_stage1_K201", "discharge_valve_stage1_K201", "valve_gasket_kit_K201"],
        "assigned_crew": ["J.Smith (Mechanical Fitter)", "A.Kumar (Tech)", "M.Al-Rashid (Supervisor)", "Contractor-Valves"],
        "safety_requirements": ["Mechanical Isolation PTW", "Gas Release PTW", "LOTO", "H2S Monitor"],
    },
    "safety_valve_overdue": {
        "title": "COMPLIANCE — PSV-501 Mandatory Inspection (OVERDUE 7 DAYS)",
        "description": (
            "PSV-501 annual inspection is 7 days overdue per API 510 and OSHA 1910.119. "
            "Regulatory non-compliance. Immediate isolation and test required. "
            "Regulatory notification to AHJ within 48 hours."
        ),
        "maintenance_type": "STATUTORY",
        "failure_mode": "Inspection Overdue",
        "labor_hours": 12.0,
        "parts_list": ["PSV-501-spring-kit", "PSV-501-seat-disc"],
        "assigned_crew": ["M.Al-Rashid (Supervisor)", "Certified PSV Inspector", "S.Chen (Process Engineer)"],
        "safety_requirements": ["API 510 Test Permit", "Isolation PTW", "Pressure Relief PTW"],
    },
    "cui_risk": {
        "title": "PLANNED — T-601 Corrosion Under Insulation Survey (Overdue)",
        "description": (
            "CUI risk survey overdue by 26 days. Operating temperature range 115-355°C in "
            "highest CUI risk band. Pulsed eddy current / RT inspection required on shell zones A4-A7. "
            "3-day inspection planned during next maintenance window."
        ),
        "maintenance_type": "STATUTORY",
        "failure_mode": "Corrosion Under Insulation",
        "labor_hours": 48.0,
        "parts_list": ["insulation_cladding_T601_zone_A"],
        "assigned_crew": ["S.Chen (Inspector)", "A.Kumar (Tech)", "NDE Contractor x2"],
        "safety_requirements": ["High Temperature PTW", "NDE Procedure AP-CUI-2024", "Confined Space PTW"],
    },
}

# Priority mapping by scenario
_PRIORITY_MAP = {
    "bearing_vibration_anomaly": "URGENT",
    "reactor_fouling": "HIGH",
    "heat_exchanger_tube_leak": "HIGH",
    "compressor_valve_failure": "EMERGENCY",
    "safety_valve_overdue": "HIGH",
    "cui_risk": "MEDIUM",
}


class WorkOrderGenerationAgent:
    """Generates structured work orders from diagnostic and criticality assessment outputs."""

    name = "WorkOrderGenerationAgent"

    def generate(
        self,
        equipment_id: str,
        equipment_type: str,
        failure_mode: str,
        scenario: Optional[str],
        criticality: str,
        risk_score: float,
        fmea_rpn: int,
        diagnosis_result: dict,
        parts_availability: Optional[dict] = None,
        cost_estimate: Optional[dict] = None,
    ) -> dict:
        """
        Generate a complete work order from diagnostic outputs.
        Returns a structured work order dict ready for CMMS submission.
        """
        template = _WORK_ORDER_TEMPLATES.get(scenario or "", {})
        priority = _PRIORITY_MAP.get(scenario or "", "HIGH" if criticality in ("CRITICAL", "HIGH") else "MEDIUM")

        # Override priority if criticality is very high
        if criticality == "CRITICAL" and priority not in ("EMERGENCY", "URGENT"):
            priority = "URGENT"

        title = template.get(
            "title",
            f"{priority} — {failure_mode} on {equipment_id} — AI-Generated Work Order"
        )
        description = template.get(
            "description",
            diagnosis_result.get("llm_narrative", f"Maintenance required for {failure_mode} on {equipment_id}.")
        )

        labor_hours = template.get("labor_hours", 8.0)
        parts_list = template.get("parts_list", [])
        crew = template.get("assigned_crew", ["J.Smith (Fitter)", "A.Kumar (Tech)"])
        safety_reqs = template.get("safety_requirements", ["LOTO", "General Work PTW"])
        maint_type = template.get("maintenance_type", "PdM")

        # Estimate cost
        parts_cost = cost_estimate.get("parts_cost_usd", 0) if cost_estimate else 500.0
        labor_cost = labor_hours * 95.0
        total_estimated_cost = round(parts_cost + labor_cost, 2)

        planned_start = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")

        reasoning = (
            f"WorkOrderGenerationAgent: Generated {priority} work order for {equipment_id}. "
            f"Failure mode '{failure_mode}' with FMEA RPN={fmea_rpn}, Risk Score={risk_score}. "
            f"Parts list: {parts_list}. "
            f"Estimated cost: ${total_estimated_cost:,.0f}. "
            f"Planned start: {planned_start}."
        )

        result = {
            "equipment_id": equipment_id,
            "title": title,
            "description": description,
            "priority": priority,
            "maintenance_type": maint_type,
            "failure_mode": failure_mode,
            "labor_hours": labor_hours,
            "parts_list": parts_list,
            "estimated_cost_usd": total_estimated_cost,
            "safety_requirements": safety_reqs,
            "assigned_crew": crew,
            "planned_start": planned_start,
            "ai_reasoning": reasoning,
            "fmea_rpn": fmea_rpn,
            "risk_score": risk_score,
            "criticality": criticality,
        }
        logger.info(
            "AGENT:WorkOrderGeneration | %s | priority=%s | cost=$%.0f | parts=%d",
            equipment_id, priority, total_estimated_cost, len(parts_list)
        )
        return result
