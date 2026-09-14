"""
Tools Layer — Inventory Tools
Callable by agents to check parts availability and reserve materials.
"""
from __future__ import annotations

import logging

from ..enterprise_systems.erp_simulator import (
    check_parts_availability,
    reserve_parts,
    calculate_parts_cost,
)

logger = logging.getLogger(__name__)


def parts_inventory_checker(part_numbers: list[str]) -> dict:
    """
    Return availability, quantity, unit cost, and lead time for a list of part numbers.
    """
    logger.info("TOOL:parts_inventory_checker | parts=%s", part_numbers)
    availability = check_parts_availability(part_numbers)
    total_cost = calculate_parts_cost(part_numbers)
    all_available = all(v.get("available", False) for v in availability.values())
    max_lead_time = max((v.get("lead_time_days", 0) for v in availability.values()), default=0)
    return {
        "parts": availability,
        "total_parts_cost_usd": total_cost,
        "all_available": all_available,
        "max_lead_time_days": max_lead_time,
        "items_on_backorder": [pn for pn, v in availability.items() if not v.get("available", False)],
    }


def cost_estimator(
    labor_hours: float,
    parts_cost: float,
    downtime_hours: float,
    production_rate_usd_per_hour: float = 85000,
    margin: float = 0.22,
    contractor_hours: float = 0,
    labor_rate: float = 95.0,
    contractor_rate: float = 145.0,
) -> dict:
    """
    Calculate total cost of a maintenance action including opportunity cost of downtime.
    """
    logger.info("TOOL:cost_estimator | labor_h=%.1f | parts=%.0f | downtime_h=%.1f",
                labor_hours, parts_cost, downtime_hours)
    labor_cost = round(labor_hours * labor_rate, 2)
    contractor_cost = round(contractor_hours * contractor_rate, 2)
    downtime_production_loss = round(downtime_hours * production_rate_usd_per_hour * margin, 2)
    total_maintenance_cost = round(labor_cost + contractor_cost + parts_cost, 2)
    total_with_downtime = round(total_maintenance_cost + downtime_production_loss, 2)
    return {
        "labor_cost_usd": labor_cost,
        "contractor_cost_usd": contractor_cost,
        "parts_cost_usd": parts_cost,
        "downtime_production_loss_usd": downtime_production_loss,
        "total_maintenance_cost_usd": total_maintenance_cost,
        "total_cost_with_downtime_usd": total_with_downtime,
        "inputs": {
            "labor_hours": labor_hours,
            "contractor_hours": contractor_hours,
            "downtime_hours": downtime_hours,
            "production_rate_usd_per_hour": production_rate_usd_per_hour,
            "margin": margin,
            "labor_rate": labor_rate,
            "contractor_rate": contractor_rate,
        },
    }
