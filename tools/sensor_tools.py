"""
Tools Layer — Sensor Data Tools
Callable by agents to fetch real-time and historical sensor telemetry.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..enterprise_systems.scada_simulator import get_sensor_data, get_process_overview

logger = logging.getLogger(__name__)


def sensor_data_fetcher(
    equipment_id: str,
    time_range_hours: int = 24,
    inject_anomaly_scenario: Optional[str] = None,
) -> dict:
    """
    Fetch sensor telemetry for a given equipment tag and time range.
    Optionally inject a specific failure scenario for demonstration purposes.

    Returns a dict with timestamps, per-channel data series, and latest readings.
    """
    logger.info("TOOL:sensor_data_fetcher | equipment=%s | range=%dh | anomaly=%s",
                equipment_id, time_range_hours, inject_anomaly_scenario)
    data = get_sensor_data(equipment_id, time_range_hours, inject_anomaly_scenario)
    return data


def get_process_snapshot() -> dict:
    """Return latest sensor readings for all monitored equipment (dashboard overview)."""
    logger.info("TOOL:get_process_snapshot")
    return get_process_overview()
