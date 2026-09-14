"""
Agent: PredictiveDiagnosticsAgent
Analyzes sensor data to detect anomalies, identify failure modes, and
predict time-to-failure using statistical threshold analysis.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ..config_loader import get_config
from ..llm_client import MockLLM

logger = logging.getLogger(__name__)

# Sensor threshold definitions by channel (matches config.yaml sensor_thresholds)
_THRESHOLDS = {
    "vibration_nde":    {"alert": 7.1, "critical": 11.2, "unit": "mm/s"},
    "vibration_de":     {"alert": 7.1, "critical": 11.2, "unit": "mm/s"},
    "bearing_temp_nde": {"alert": 90.0, "critical": 110.0, "unit": "°C"},
    "bearing_temp_de":  {"alert": 90.0, "critical": 110.0, "unit": "°C"},
    "discharge_temp":   {"alert": 130.0, "critical": 155.0, "unit": "°C"},
    "dp_across_bed":    {"alert": 1.35, "critical": 1.70, "unit": "bar"},
    "efficiency":       {"alert": 0.74, "critical": 0.68, "unit": "fraction", "direction": "low"},
    "valve_temp_stage1": {"alert": 130.0, "critical": 150.0, "unit": "°C"},
    "tube_outlet_temp": {"alert": 360.0, "critical": 375.0, "unit": "°C"},  # Tube leak indicator
}

# Failure mode signatures: which channels are elevated for each failure
_FAILURE_SIGNATURES = {
    "Bearing Failure": {"primary": ["vibration_nde"], "secondary": ["bearing_temp_nde"]},
    "Catalyst Fouling": {"primary": ["dp_across_bed"], "secondary": []},
    "Discharge Valve Failure": {"primary": ["discharge_temp", "valve_temp_stage1"], "secondary": ["efficiency"]},
    "Tube Bundle Tube Leak": {"primary": ["tube_outlet_temp"], "secondary": []},
    "Inspection Overdue": {"primary": [], "secondary": []},
    "Corrosion Under Insulation": {"primary": [], "secondary": []},
}


class PredictiveDiagnosticsAgent:
    """
    Analyzes sensor telemetry to detect anomalies and predict failures.
    Uses threshold-based pattern matching + LLM narrative generation.
    """

    name = "PredictiveDiagnosticsAgent"

    def __init__(self, llm: Optional[Any] = None) -> None:
        self.llm = llm
        logger.debug("PredictiveDiagnosticsAgent initialized")

    def diagnose(
        self,
        equipment_id: str,
        equipment_type: str,
        sensor_data: dict,
        scenario: Optional[str] = None,
        maintenance_history: Optional[dict] = None,
    ) -> dict:
        """
        Analyze sensor data and produce a diagnostic assessment.

        Returns:
            Dict with anomalies detected, failure mode, severity, time_to_failure, LLM narrative.
        """
        latest = sensor_data.get("latest", {})
        anomalies: list[dict] = []
        triggered_channels: list[str] = []

        for channel, value in latest.items():
            if channel not in _THRESHOLDS:
                continue
            thresh = _THRESHOLDS[channel]
            direction = thresh.get("direction", "high")
            alert_thresh = thresh["alert"]
            crit_thresh = thresh["critical"]

            if direction == "high":
                if value >= crit_thresh:
                    anomalies.append({
                        "channel": channel,
                        "value": value,
                        "threshold": crit_thresh,
                        "severity": "CRITICAL",
                        "unit": thresh["unit"],
                        "deviation_pct": round((value - alert_thresh) / alert_thresh * 100, 1),
                    })
                    triggered_channels.append(channel)
                elif value >= alert_thresh:
                    anomalies.append({
                        "channel": channel,
                        "value": value,
                        "threshold": alert_thresh,
                        "severity": "ALERT",
                        "unit": thresh["unit"],
                        "deviation_pct": round((value - alert_thresh) / alert_thresh * 100, 1),
                    })
                    triggered_channels.append(channel)
            else:  # low direction (efficiency)
                if value <= crit_thresh:
                    anomalies.append({
                        "channel": channel,
                        "value": value,
                        "threshold": crit_thresh,
                        "severity": "CRITICAL",
                        "unit": thresh["unit"],
                        "deviation_pct": round((alert_thresh - value) / alert_thresh * 100, 1),
                    })
                    triggered_channels.append(channel)
                elif value <= alert_thresh:
                    anomalies.append({
                        "channel": channel,
                        "value": value,
                        "threshold": alert_thresh,
                        "severity": "ALERT",
                        "unit": thresh["unit"],
                        "deviation_pct": round((alert_thresh - value) / alert_thresh * 100, 1),
                    })
                    triggered_channels.append(channel)

        # Identify failure mode from signature
        detected_failure_mode = "Generic"
        best_match = 0
        for fm, sig in _FAILURE_SIGNATURES.items():
            primary_hits = sum(1 for ch in sig["primary"] if ch in triggered_channels)
            secondary_hits = sum(1 for ch in sig["secondary"] if ch in triggered_channels)
            score = primary_hits * 2 + secondary_hits
            if score > best_match:
                best_match = score
                detected_failure_mode = fm

        # If scenario is provided, use its known failure mode
        if scenario:
            scenario_fm_map = {
                "bearing_vibration_anomaly": "Bearing Failure",
                "reactor_fouling": "Catalyst Fouling",
                "heat_exchanger_tube_leak": "Tube Bundle Tube Leak",
                "compressor_valve_failure": "Discharge Valve Failure",
                "safety_valve_overdue": "Inspection Overdue",
                "cui_risk": "Corrosion Under Insulation",
            }
            detected_failure_mode = scenario_fm_map.get(scenario, detected_failure_mode)

        # Time-to-failure estimate (hours) from scenario data
        predicted_failure_hours = self._estimate_time_to_failure(scenario, anomalies)

        # Generate LLM narrative
        if self.llm and isinstance(self.llm, MockLLM):
            prompt = (
                f"Equipment: {equipment_id} ({equipment_type})\n"
                f"Anomalies detected: {[a['channel'] for a in anomalies]}\n"
                f"Failure mode: {detected_failure_mode}\n"
                f"Analyze and provide maintenance recommendation."
            )
            llm_narrative = self.llm.generate(prompt, scenario=scenario or "generic")
        else:
            llm_narrative = f"Diagnostic analysis completed for {equipment_id}. Failure mode: {detected_failure_mode}."

        result = {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "scenario": scenario,
            "anomalies_detected": anomalies,
            "anomaly_count": len(anomalies),
            "has_critical_anomaly": any(a["severity"] == "CRITICAL" for a in anomalies),
            "failure_mode": detected_failure_mode,
            "predicted_failure_hours": predicted_failure_hours,
            "llm_narrative": llm_narrative,
            "triggered_channels": triggered_channels,
        }
        logger.info(
            "AGENT:Diagnostics | %s | failure=%s | anomalies=%d | ttf=%s h",
            equipment_id, detected_failure_mode, len(anomalies), predicted_failure_hours
        )
        return result

    def _estimate_time_to_failure(self, scenario: Optional[str], anomalies: list[dict]) -> Optional[int]:
        """Estimate hours until predicted failure based on scenario or anomaly severity."""
        ttf_map = {
            "bearing_vibration_anomaly": 48,
            "reactor_fouling": 336,
            "heat_exchanger_tube_leak": 96,
            "compressor_valve_failure": 24,
            "safety_valve_overdue": None,
            "cui_risk": None,
        }
        if scenario and scenario in ttf_map:
            return ttf_map[scenario]
        if any(a["severity"] == "CRITICAL" for a in anomalies):
            return 24
        if anomalies:
            return 72
        return None
