"""
Agent: ROICalculationAgent
Computes financial impact of maintenance actions versus unplanned downtime costs.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..roi.roi_engine import calculate_incident_roi, register_incident_roi

logger = logging.getLogger(__name__)

# Downtime hours avoided by scenario
_DOWNTIME_AVOIDED_MAP = {
    "bearing_vibration_anomaly":   {"planned": 8,  "avoided": 64},
    "reactor_fouling":             {"planned": 48, "avoided": 280},
    "heat_exchanger_tube_leak":    {"planned": 16, "avoided": 88},
    "compressor_valve_failure":    {"planned": 16, "avoided": 144},
    "safety_valve_overdue":        {"planned": 12, "avoided": 24},
    "cui_risk":                    {"planned": 48, "avoided": 480},  # Catastrophic brittle fracture avoided
}


class ROICalculationAgent:
    """Computes ROI for a maintenance incident."""

    name = "ROICalculationAgent"

    def calculate(
        self,
        workflow_id: str,
        equipment_id: str,
        scenario: Optional[str],
        maintenance_cost_usd: float,
        labor_hours: float,
        parts_cost_usd: float,
        downtime_hours_avoided: Optional[float] = None,
        production_rate_usd_per_hour: float = 85_000,
        margin: float = 0.22,
    ) -> dict:
        """
        Compute ROI for a single maintenance incident.
        If downtime_hours_avoided is not provided, it is estimated from the scenario map.
        """
        if downtime_hours_avoided is None:
            scenario_data = _DOWNTIME_AVOIDED_MAP.get(scenario or "", {"avoided": 0, "planned": labor_hours})
            downtime_hours_avoided = scenario_data["avoided"]

        roi = calculate_incident_roi(
            equipment_id=equipment_id,
            maintenance_cost_usd=maintenance_cost_usd,
            downtime_hours_avoided=downtime_hours_avoided,
            detection_method="AI-Predictive",
            labor_hours=labor_hours,
            parts_cost_usd=parts_cost_usd,
            production_rate_usd_per_hour=production_rate_usd_per_hour,
            margin=margin,
        )
        roi["workflow_id"] = workflow_id
        roi["scenario"] = scenario
        roi["ai_assisted"] = True

        register_incident_roi(workflow_id, roi)

        reasoning = (
            f"ROICalculationAgent: Avoided downtime cost = "
            f"${roi['avoided_downtime_cost_usd']:,.0f} "
            f"({downtime_hours_avoided:.0f}h × ${production_rate_usd_per_hour:,.0f}/h × {margin:.0%} margin). "
            f"Total maintenance cost = ${roi['maintenance_cost_usd']:,.0f}. "
            f"Net savings = ${roi['net_savings_usd']:,.0f}. ROI = {roi['roi_pct']:.1f}%."
        )
        roi["reasoning"] = reasoning

        logger.info(
            "AGENT:ROI | wf=%s | equipment=%s | net_savings=$%.0f | roi=%.1f%%",
            workflow_id, equipment_id, roi["net_savings_usd"], roi["roi_pct"]
        )
        return roi
