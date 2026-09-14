"""
Tools Layer — CMMS Tools
Callable by agents to interact with the CMMS system.
"""
from __future__ import annotations

import json
import logging
import pathlib
from typing import Optional

from ..enterprise_systems.cmms_simulator import (
    create_work_order,
    get_work_order,
    get_all_work_orders,
    get_equipment_maintenance_history,
    calculate_mtbf,
    update_work_order_status,
)

logger = logging.getLogger(__name__)
_catalog: Optional[dict] = None


def _load_catalog() -> dict:
    global _catalog
    if _catalog is None:
        p = pathlib.Path(__file__).parent.parent / "data" / "equipment_catalog.json"
        try:
            _catalog = json.loads(p.read_text())
        except Exception:
            _catalog = {"equipment": []}
    return _catalog


def equipment_history_lookup(equipment_id: str) -> dict:
    """
    Return maintenance history, MTBF, and equipment master data for a given equipment ID.
    """
    logger.info("TOOL:equipment_history_lookup | equipment=%s", equipment_id)
    catalog = _load_catalog()
    equipment_meta = next((e for e in catalog["equipment"] if e["id"] == equipment_id), None)
    history = get_equipment_maintenance_history(equipment_id)
    mtbf = calculate_mtbf(equipment_id)

    return {
        "equipment_id": equipment_id,
        "metadata": equipment_meta,
        "maintenance_history": history,
        "calculated_mtbf_hours": mtbf,
        "history_count": len(history),
    }


def get_equipment_catalog() -> list[dict]:
    """Return full equipment catalog."""
    logger.info("TOOL:get_equipment_catalog")
    return _load_catalog().get("equipment", [])


def get_equipment_by_id(equipment_id: str) -> Optional[dict]:
    """Return metadata for a single equipment tag."""
    catalog = _load_catalog()
    return next((e for e in catalog["equipment"] if e["id"] == equipment_id), None)


def dispatch_work_order(
    equipment_id: str,
    title: str,
    description: str,
    priority: str,
    maintenance_type: str,
    failure_mode: str,
    labor_hours: float,
    parts_list: list[str],
    estimated_cost_usd: float,
    safety_requirements: list[str],
    assigned_crew: list[str],
    ai_reasoning: str = "",
) -> dict:
    """Create and dispatch a work order via the CMMS."""
    logger.info("TOOL:dispatch_work_order | equipment=%s | priority=%s", equipment_id, priority)
    return create_work_order(
        equipment_id=equipment_id,
        title=title,
        description=description,
        priority=priority,
        maintenance_type=maintenance_type,
        failure_mode=failure_mode,
        labor_hours=labor_hours,
        parts_list=parts_list,
        estimated_cost_usd=estimated_cost_usd,
        safety_requirements=safety_requirements,
        assigned_crew=assigned_crew,
        ai_generated=True,
        ai_reasoning=ai_reasoning,
    )


def mark_work_order_executed(work_order_id: str) -> dict:
    """Mark a work order as executed/completed."""
    logger.info("TOOL:mark_work_order_executed | wo_id=%s", work_order_id)
    return update_work_order_status(work_order_id, "COMPLETED", comment="Executed by field team", actor="system")
