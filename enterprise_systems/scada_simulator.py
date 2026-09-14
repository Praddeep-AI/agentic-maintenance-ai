"""
Enterprise Systems Layer — SCADA/DCS Simulator
Generates realistic sensor telemetry using statistical distributions with anomaly injection.
"""
from __future__ import annotations

import json
import logging
import math
import pathlib
import random
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

_RNG = random.Random(42)
_profiles: Optional[dict] = None


def _load_profiles() -> dict:
    global _profiles
    if _profiles is None:
        pfile = pathlib.Path(__file__).parent.parent / "data" / "sensor_profiles.json"
        try:
            _profiles = json.loads(pfile.read_text())
        except Exception:
            _profiles = {}
    return _profiles


# ---------------------------------------------------------------------------
# Sensor data generation
# ---------------------------------------------------------------------------

def _generate_normal_series(mean: float, std: float, n: int) -> list[float]:
    return [round(_RNG.gauss(mean, std), 4) for _ in range(n)]


def _inject_anomaly(base_series: list[float], final_value: float, pattern: str) -> list[float]:
    """Blend a normal series with an anomaly progression."""
    n = len(base_series)
    result = list(base_series)
    for i in range(n):
        progress = i / max(n - 1, 1)
        if pattern == "exponential":
            factor = math.exp(progress * 2) / math.exp(2)
        elif pattern == "step_then_linear":
            factor = 0.4 if progress < 0.3 else 0.4 + (progress - 0.3) / 0.7 * 0.6
        else:  # linear
            factor = progress
        anomaly_delta = (final_value - base_series[0]) * factor
        result[i] = round(base_series[i] + anomaly_delta, 4)
    return result


def get_sensor_data(
    equipment_id: str,
    time_range_hours: int = 24,
    inject_anomaly_scenario: Optional[str] = None,
) -> dict:
    """
    Return simulated sensor telemetry for an equipment tag.
    If inject_anomaly_scenario is provided, overlays a failure progression.
    """
    profiles = _load_profiles()
    scenarios = profiles.get("anomaly_scenarios", {})
    sensor_profiles = profiles.get("sensor_profiles", {})

    # Determine equipment type from ID prefix
    eq_type = "PUMP" if equipment_id.startswith("P-") else \
              "COMPRESSOR" if equipment_id.startswith("K-") else \
              "REACTOR" if equipment_id.startswith("R-") else \
              "HEAT_EXCHANGER" if equipment_id.startswith("E-") else \
              "SAFETY_VALVE" if equipment_id.startswith("PSV-") else \
              "DISTILLATION_COLUMN"

    n_points = min(time_range_hours * 2, 200)  # 30-minute samples
    timestamps = [
        (datetime.now() - timedelta(hours=time_range_hours) + timedelta(minutes=30 * i)).isoformat()
        for i in range(n_points)
    ]

    channels: dict[str, list[float]] = {}

    # Generate channels based on equipment type
    if eq_type == "PUMP":
        vib_profile = sensor_profiles.get("PUMP_vibration", {})
        temp_profile = sensor_profiles.get("PUMP_bearing_temp", {})
        channels["vibration_nde"] = _generate_normal_series(
            vib_profile.get("normal_mean", 2.1), vib_profile.get("normal_std", 0.4), n_points
        )
        channels["vibration_de"] = _generate_normal_series(2.0, 0.35, n_points)
        channels["bearing_temp_nde"] = _generate_normal_series(
            temp_profile.get("normal_mean", 72.0), temp_profile.get("normal_std", 3.5), n_points
        )
        channels["bearing_temp_de"] = _generate_normal_series(71.5, 3.2, n_points)
        channels["suction_pressure"] = _generate_normal_series(3.5, 0.1, n_points)
        channels["discharge_pressure"] = _generate_normal_series(10.2, 0.2, n_points)
        channels["flow_rate"] = _generate_normal_series(125.0, 4.0, n_points)

    elif eq_type == "COMPRESSOR":
        dt_profile = sensor_profiles.get("COMPRESSOR_discharge_temp", {})
        channels["discharge_temp"] = _generate_normal_series(
            dt_profile.get("normal_mean", 105.0), dt_profile.get("normal_std", 4.0), n_points
        )
        channels["suction_temp"] = _generate_normal_series(42.0, 1.5, n_points)
        channels["suction_pressure"] = _generate_normal_series(6.2, 0.15, n_points)
        channels["discharge_pressure"] = _generate_normal_series(42.0, 0.5, n_points)
        channels["vibration_nde"] = _generate_normal_series(4.0, 0.5, n_points)
        channels["valve_temp_stage1"] = _generate_normal_series(108.0, 3.0, n_points)
        channels["valve_temp_stage2"] = _generate_normal_series(112.0, 3.0, n_points)
        eff_profile = sensor_profiles.get("COMPRESSOR_efficiency", {})
        channels["efficiency"] = _generate_normal_series(
            eff_profile.get("normal_mean", 0.82), eff_profile.get("normal_std", 0.01), n_points
        )

    elif eq_type == "REACTOR":
        dp_profile = sensor_profiles.get("REACTOR_dp", {})
        channels["dp_across_bed"] = _generate_normal_series(
            dp_profile.get("normal_mean", 0.85), dp_profile.get("normal_std", 0.05), n_points
        )
        channels["inlet_temp"] = _generate_normal_series(320.0, 2.0, n_points)
        channels["bed_temp_1"] = _generate_normal_series(330.0, 3.0, n_points)
        channels["bed_temp_2"] = _generate_normal_series(355.0, 3.5, n_points)
        channels["bed_temp_3"] = _generate_normal_series(390.0, 4.0, n_points)
        channels["outlet_temp"] = _generate_normal_series(315.0, 2.5, n_points)
        channels["inlet_pressure"] = _generate_normal_series(74.5, 0.3, n_points)
        channels["outlet_pressure"] = _generate_normal_series(73.6, 0.3, n_points)

    elif eq_type == "HEAT_EXCHANGER":
        dp_profile = sensor_profiles.get("HEAT_EXCHANGER_shell_pressure_drop", {})
        channels["shell_inlet_temp"] = _generate_normal_series(385.0, 3.0, n_points)
        channels["shell_outlet_temp"] = _generate_normal_series(180.0, 4.0, n_points)
        channels["tube_inlet_temp"] = _generate_normal_series(160.0, 3.0, n_points)
        channels["tube_outlet_temp"] = _generate_normal_series(348.0, 4.0, n_points)
        channels["shell_inlet_pressure"] = _generate_normal_series(84.2, 0.2, n_points)
        channels["shell_outlet_pressure"] = _generate_normal_series(83.8, 0.2, n_points)
        channels["tube_inlet_pressure"] = _generate_normal_series(83.5, 0.2, n_points)
        channels["tube_outlet_pressure"] = _generate_normal_series(82.9, 0.2, n_points)

    elif eq_type == "SAFETY_VALVE":
        channels["inlet_pressure"] = _generate_normal_series(78.5, 0.8, n_points)

    elif eq_type == "DISTILLATION_COLUMN":
        channels["overhead_pressure"] = _generate_normal_series(1.8, 0.05, n_points)
        channels["bottom_temp"] = _generate_normal_series(355.0, 4.0, n_points)
        channels["tray_10_temp"] = _generate_normal_series(185.0, 3.0, n_points)
        channels["tray_20_temp"] = _generate_normal_series(240.0, 3.5, n_points)
        channels["tray_30_temp"] = _generate_normal_series(295.0, 4.0, n_points)
        channels["overhead_temp"] = _generate_normal_series(115.0, 2.0, n_points)
        channels["reflux_flow"] = _generate_normal_series(850.0, 15.0, n_points)
        channels["feed_flow"] = _generate_normal_series(2200.0, 30.0, n_points)

    # Inject anomaly if requested
    if inject_anomaly_scenario and inject_anomaly_scenario in scenarios:
        scenario = scenarios[inject_anomaly_scenario]
        # Use the last snapshot values as anomaly injection targets
        snapshots = scenario.get("sensor_snapshots", {})
        if snapshots:
            final_snap = list(snapshots.values())[-1]
            for channel, final_val in final_snap.items():
                if channel in channels and channels[channel]:
                    baseline = channels[channel][0]
                    # Determine pattern from sensor profile
                    pattern = "linear"
                    for _pkey, _pval in sensor_profiles.items():
                        if _pkey.split("_", 1)[-1] in channel:
                            for _fm in _pval.get("failure_modes", {}).values():
                                pattern = _fm.get("pattern", "linear")
                    channels[channel] = _inject_anomaly(channels[channel], final_val, pattern)
        logger.info("SCADA: Anomaly injected | equipment=%s | scenario=%s", equipment_id, inject_anomaly_scenario)

    # Compute latest values (last data point)
    latest = {ch: vals[-1] for ch, vals in channels.items() if vals}

    return {
        "equipment_id": equipment_id,
        "equipment_type": eq_type,
        "time_range_hours": time_range_hours,
        "n_samples": n_points,
        "sample_interval_minutes": 30,
        "timestamps": timestamps,
        "channels": channels,
        "latest": latest,
        "retrieved_at": datetime.now().isoformat(),
        "anomaly_injected": inject_anomaly_scenario,
    }


def get_process_overview() -> dict[str, Any]:
    """Return a high-level process snapshot for all equipment."""
    equipment_ids = ["P-101", "P-102", "K-201", "R-301", "E-401", "PSV-501", "T-601", "P-103", "K-202", "E-402"]
    overview = {}
    for eid in equipment_ids:
        data = get_sensor_data(eid, time_range_hours=1)
        overview[eid] = {"latest": data["latest"], "type": data["equipment_type"]}
    return overview
