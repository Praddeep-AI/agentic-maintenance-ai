"""
Agent: CriticalityAssessmentAgent
Evaluates equipment failure risk using FMEA (Failure Mode and Effects Analysis) scoring.
Produces Severity, Occurrence, Detectability scores and composite RPN.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# FMEA scoring tables
_SEVERITY_TABLE = {
    "Bearing Failure": 7, "Seal Failure": 6, "Impeller Wear": 5,
    "Cavitation": 5, "Valve Failure": 8, "Piston Ring Wear": 6,
    "Catalyst Fouling": 7, "Catalyst Poisoning": 9, "Hot Spot Formation": 10,
    "Tube Bundle Tube Leak": 8, "Tube Bundle Fouling": 5, "Inspection Overdue": 9,
    "Corrosion Under Insulation": 9, "Discharge Valve Failure": 9,
    "Mechanical Seal Leakage": 7, "Generic": 6,
}

_OCCURRENCE_TABLE = {
    "PUMP": {"Bearing Failure": 6, "Seal Failure": 5, "default": 4},
    "COMPRESSOR": {"Valve Failure": 7, "Bearing Failure": 5, "default": 5},
    "REACTOR": {"Catalyst Fouling": 4, "Hot Spot Formation": 2, "default": 3},
    "HEAT_EXCHANGER": {"Tube Bundle Fouling": 5, "Tube Bundle Tube Leak": 4, "default": 4},
    "SAFETY_VALVE": {"Inspection Overdue": 3, "default": 2},
    "DISTILLATION_COLUMN": {"Corrosion Under Insulation": 5, "Tray Fouling": 4, "default": 3},
}

_DETECTABILITY_TABLE = {
    "AI-Predictive": 2,   # AI with continuous monitoring → very detectable
    "SCADA-Alert": 4,
    "Operator-Report": 7,
    "No-Monitoring": 9,
}


class CriticalityAssessmentAgent:
    """
    FMEA-based criticality scorer for maintenance work orders.
    Computes Severity × Occurrence × Detectability = RPN (Risk Priority Number).
    """

    name = "CriticalityAssessmentAgent"

    def __init__(self) -> None:
        logger.debug("CriticalityAssessmentAgent initialized")

    def assess(
        self,
        equipment_id: str,
        equipment_type: str,
        failure_mode: str,
        detection_method: str = "AI-Predictive",
        sensor_data: Optional[dict] = None,
        maintenance_history: Optional[dict] = None,
    ) -> dict:
        """
        Perform FMEA criticality assessment.

        Returns:
            Dict with severity, occurrence, detectability, RPN, criticality_level, and reasoning.
        """
        severity = _SEVERITY_TABLE.get(failure_mode, _SEVERITY_TABLE["Generic"])
        occ_map = _OCCURRENCE_TABLE.get(equipment_type, {})
        occurrence = occ_map.get(failure_mode, occ_map.get("default", 5))
        detectability = _DETECTABILITY_TABLE.get(detection_method, 5)

        # Adjust occurrence based on maintenance history age
        if maintenance_history:
            failures = maintenance_history.get("metadata", {}).get("maintenance_history", {}).get("failures_last_3yr", 0)
            if failures >= 3:
                occurrence = min(occurrence + 2, 10)
            elif failures == 0:
                occurrence = max(occurrence - 1, 1)

        rpn = severity * occurrence * detectability

        if rpn >= 200:
            criticality = "CRITICAL"
            risk_score = round(9.0 + min((rpn - 200) / 300, 1.0), 1)
        elif rpn >= 100:
            criticality = "HIGH"
            risk_score = round(7.0 + (rpn - 100) / 100, 1)
        elif rpn >= 50:
            criticality = "MEDIUM"
            risk_score = round(5.0 + (rpn - 50) / 50, 1)
        else:
            criticality = "LOW"
            risk_score = round(rpn / 10, 1)

        risk_score = min(risk_score, 10.0)

        reasoning = (
            f"FMEA Assessment for {equipment_id} ({equipment_type}): "
            f"Failure Mode='{failure_mode}' | "
            f"Severity={severity}/10 (impact on safety and production), "
            f"Occurrence={occurrence}/10 (historical failure frequency), "
            f"Detectability={detectability}/10 (detection via {detection_method}). "
            f"RPN={rpn} → Criticality: {criticality}."
        )

        result = {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "failure_mode": failure_mode,
            "fmea_severity": severity,
            "fmea_occurrence": occurrence,
            "fmea_detectability": detectability,
            "fmea_rpn": rpn,
            "criticality": criticality,
            "risk_score": risk_score,
            "reasoning": reasoning,
        }
        logger.info(
            "AGENT:CriticalityAssessment | %s | %s | RPN=%d | %s",
            equipment_id, failure_mode, rpn, criticality
        )
        return result
