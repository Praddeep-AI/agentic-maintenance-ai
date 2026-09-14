"""
Enterprise Systems Layer — CMMS Simulator
Simulates SAP PM / IBM Maximo-style CMMS with work orders, equipment records, and maintenance history.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class WorkOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkOrderPriority(str, Enum):
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    ROUTINE = "ROUTINE"


# ---------------------------------------------------------------------------
# In-memory CMMS database
# ---------------------------------------------------------------------------
_WORK_ORDERS: dict[str, dict] = {}
_MAINTENANCE_HISTORY: dict[str, list[dict]] = {}


def _seed_history() -> None:
    """Pre-populate historical maintenance records for all known equipment."""
    import json, pathlib, random
    random.seed(42)
    cat_path = pathlib.Path(__file__).parent.parent / "data" / "equipment_catalog.json"
    try:
        catalog = json.loads(cat_path.read_text())
    except Exception:
        return
    base_date = datetime.now() - timedelta(days=365 * 3)
    for eq in catalog["equipment"]:
        eid = eq["id"]
        _MAINTENANCE_HISTORY.setdefault(eid, [])
        for i in range(random.randint(4, 12)):
            wo_date = base_date + timedelta(days=random.randint(0, 900))
            _MAINTENANCE_HISTORY[eid].append({
                "work_order_id": f"WO-HIST-{eid}-{i:03d}",
                "description": random.choice(["Scheduled PM", "Bearing replacement", "Seal replacement", "Vibration check", "Full overhaul"]),
                "type": random.choice(["PM", "CM", "PdM"]),
                "status": "COMPLETED",
                "priority": random.choice(["HIGH", "MEDIUM", "LOW", "ROUTINE"]),
                "start_date": wo_date.isoformat(),
                "completion_date": (wo_date + timedelta(hours=random.randint(4, 96))).isoformat(),
                "labor_hours": round(random.uniform(4, 80), 1),
                "parts_cost_usd": round(random.uniform(500, 45000), 2),
                "technician": random.choice(["J.Smith", "A.Kumar", "M.Al-Rashid", "S.Chen"]),
                "outcome": random.choice(["Successful", "Successful", "Successful", "Partial - Revisit required"]),
                "root_cause": random.choice(["Normal wear", "Fatigue", "Contamination", "Mis-alignment", "Overload"]),
            })
    logger.debug("CMMS history seeded for %d equipment items", len(catalog["equipment"]))


_seed_history()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_work_order(
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
    planned_start: Optional[str] = None,
    ai_generated: bool = True,
    ai_reasoning: str = "",
) -> dict:
    """Create a new work order in the CMMS. Returns the created work order dict."""
    wo_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    if planned_start is None:
        planned_start = (datetime.now() + timedelta(hours=8)).isoformat()

    wo = {
        "work_order_id": wo_id,
        "equipment_id": equipment_id,
        "title": title,
        "description": description,
        "priority": priority,
        "maintenance_type": maintenance_type,
        "failure_mode": failure_mode,
        "status": WorkOrderStatus.DRAFT.value,
        "labor_hours": labor_hours,
        "parts_list": parts_list,
        "estimated_cost_usd": estimated_cost_usd,
        "safety_requirements": safety_requirements,
        "assigned_crew": assigned_crew,
        "planned_start": planned_start,
        "created_at": datetime.now().isoformat(),
        "created_by": "AgenticMaintenanceAI" if ai_generated else "Manual",
        "ai_generated": ai_generated,
        "ai_reasoning": ai_reasoning,
        "approvals": [],
        "comments": [],
        "actual_start": None,
        "actual_completion": None,
        "actual_labor_hours": None,
        "actual_cost_usd": None,
    }
    _WORK_ORDERS[wo_id] = wo
    logger.info("CMMS: Work order created | wo_id=%s | equipment=%s | priority=%s", wo_id, equipment_id, priority)
    return wo


def update_work_order_status(work_order_id: str, new_status: str, comment: str = "", actor: str = "system") -> dict:
    """Transition work order to a new status."""
    if work_order_id not in _WORK_ORDERS:
        raise KeyError(f"Work order {work_order_id!r} not found")
    wo = _WORK_ORDERS[work_order_id]
    old_status = wo["status"]
    wo["status"] = new_status
    wo["comments"].append({
        "timestamp": datetime.now().isoformat(),
        "actor": actor,
        "text": f"Status changed {old_status} → {new_status}. {comment}".strip(),
    })
    if new_status == WorkOrderStatus.IN_PROGRESS.value:
        wo["actual_start"] = datetime.now().isoformat()
    elif new_status == WorkOrderStatus.COMPLETED.value:
        wo["actual_completion"] = datetime.now().isoformat()
        wo["actual_labor_hours"] = wo["labor_hours"]
        wo["actual_cost_usd"] = wo["estimated_cost_usd"] * 1.05
        # Archive to history
        _MAINTENANCE_HISTORY.setdefault(wo["equipment_id"], []).append({
            "work_order_id": work_order_id,
            "description": wo["title"],
            "type": wo["maintenance_type"],
            "status": "COMPLETED",
            "priority": wo["priority"],
            "start_date": wo["actual_start"],
            "completion_date": wo["actual_completion"],
            "labor_hours": wo["actual_labor_hours"],
            "parts_cost_usd": wo["actual_cost_usd"],
            "technician": wo["assigned_crew"][0] if wo["assigned_crew"] else "Unknown",
            "outcome": "Successful",
            "ai_generated": wo["ai_generated"],
        })
    logger.info("CMMS: WO status updated | wo_id=%s | %s → %s", work_order_id, old_status, new_status)
    return wo


def approve_work_order(work_order_id: str, approver: str, decision: str, comment: str = "") -> dict:
    """Record an approval decision on a work order."""
    if work_order_id not in _WORK_ORDERS:
        raise KeyError(f"Work order {work_order_id!r} not found")
    wo = _WORK_ORDERS[work_order_id]
    approval_entry = {
        "timestamp": datetime.now().isoformat(),
        "approver": approver,
        "decision": decision,
        "comment": comment,
    }
    wo["approvals"].append(approval_entry)
    if decision.upper() == "APPROVED":
        update_work_order_status(work_order_id, WorkOrderStatus.APPROVED.value, comment=comment, actor=approver)
    elif decision.upper() == "REJECTED":
        update_work_order_status(work_order_id, WorkOrderStatus.CANCELLED.value, comment=comment, actor=approver)
    return wo


def get_work_order(work_order_id: str) -> Optional[dict]:
    return _WORK_ORDERS.get(work_order_id)


def get_all_work_orders() -> list[dict]:
    return list(_WORK_ORDERS.values())


def get_equipment_maintenance_history(equipment_id: str, limit: int = 20) -> list[dict]:
    history = _MAINTENANCE_HISTORY.get(equipment_id, [])
    return sorted(history, key=lambda x: x.get("start_date", ""), reverse=True)[:limit]


def calculate_mtbf(equipment_id: str) -> Optional[float]:
    """Calculate Mean Time Between Failures from history (hours)."""
    history = _MAINTENANCE_HISTORY.get(equipment_id, [])
    cm_records = [r for r in history if r.get("type") == "CM" and r.get("start_date")]
    if len(cm_records) < 2:
        return None
    dates = sorted(datetime.fromisoformat(r["start_date"]) for r in cm_records)
    gaps = [(dates[i+1] - dates[i]).total_seconds() / 3600 for i in range(len(dates)-1)]
    return round(sum(gaps) / len(gaps), 1) if gaps else None
