"""
ROI Calculation Engine
Computes financial impact of maintenance actions, cumulative savings, MTBF improvement,
and all executive KPIs. Populates with 12 months of simulated historical data.
"""
from __future__ import annotations

import json
import logging
import pathlib
import random
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 12-month historical incident simulation seed
# ---------------------------------------------------------------------------
_RNG = random.Random(42)

_HISTORICAL_INCIDENTS: list[dict] = []
_ACTIVE_ROI_RECORDS: dict[str, dict] = {}

# Plant-wide production parameters (aligned with config.yaml)
PRODUCTION_RATE_USD_PER_HOUR = 85_000
PRODUCT_MARGIN = 0.22
AI_SYSTEM_ANNUAL_COST = 250_000
LABOR_RATE = 95.0
CONTRACTOR_RATE = 145.0


def _seed_historical_data() -> None:
    """Generate 12 months of realistic simulated incident data for 10 equipment items."""
    global _HISTORICAL_INCIDENTS
    equipment_ids = ["P-101", "P-102", "K-201", "R-301", "E-401", "PSV-501", "T-601", "P-103", "K-202", "E-402"]

    # Costs by equipment type
    type_costs = {
        "PUMP":              {"planned": 8500,   "emergency": 42000,  "downtime_planned": 8,  "downtime_emergency": 72},
        "COMPRESSOR":        {"planned": 22000,  "emergency": 185000, "downtime_planned": 24, "downtime_emergency": 168},
        "REACTOR":           {"planned": 45000,  "emergency": 380000, "downtime_planned": 48, "downtime_emergency": 336},
        "HEAT_EXCHANGER":    {"planned": 15000,  "emergency": 95000,  "downtime_planned": 16, "downtime_emergency": 96},
        "SAFETY_VALVE":      {"planned": 2500,   "emergency": 18000,  "downtime_planned": 4,  "downtime_emergency": 24},
        "DISTILLATION_COLUMN": {"planned": 65000, "emergency": 520000, "downtime_planned": 72, "downtime_emergency": 480},
    }

    def eq_type(eid: str) -> str:
        if eid.startswith("P-"): return "PUMP"
        if eid.startswith("K-"): return "COMPRESSOR"
        if eid.startswith("R-"): return "REACTOR"
        if eid.startswith("E-"): return "HEAT_EXCHANGER"
        if eid.startswith("PSV-"): return "SAFETY_VALVE"
        if eid.startswith("T-"): return "DISTILLATION_COLUMN"
        return "PUMP"

    base_date = datetime.now() - timedelta(days=365)
    incident_id = 1

    for month in range(12):
        month_start = base_date + timedelta(days=30 * month)
        # ~3 incidents per month across all equipment
        n_incidents = _RNG.randint(2, 5)
        for _ in range(n_incidents):
            eid = _RNG.choice(equipment_ids)
            etyp = eq_type(eid)
            costs = type_costs.get(etyp, type_costs["PUMP"])
            ai_assisted = _RNG.random() < 0.75  # 75% AI-assisted after system deployment

            if ai_assisted:
                # AI-assisted = planned maintenance, lower cost, less downtime
                maint_cost = costs["planned"] * _RNG.uniform(0.85, 1.15)
                downtime_hours = costs["downtime_planned"] * _RNG.uniform(0.8, 1.2)
                downtime_avoided = costs["downtime_emergency"] - downtime_hours
                incident_type = "PdM"
                detection_method = "AI-Predictive"
            else:
                # Reactive = emergency cost, high downtime
                maint_cost = costs["emergency"] * _RNG.uniform(0.7, 1.0)
                downtime_hours = costs["downtime_emergency"] * _RNG.uniform(0.5, 1.0)
                downtime_avoided = 0.0
                incident_type = "CM"
                detection_method = "Operator Report"

            avoided_cost = downtime_avoided * PRODUCTION_RATE_USD_PER_HOUR * PRODUCT_MARGIN
            net_savings = avoided_cost - maint_cost if ai_assisted else -maint_cost
            incident_date = month_start + timedelta(days=_RNG.randint(0, 28))

            _HISTORICAL_INCIDENTS.append({
                "incident_id": f"INC-HIST-{incident_id:04d}",
                "equipment_id": eid,
                "equipment_type": etyp,
                "incident_date": incident_date.isoformat(),
                "month": incident_date.strftime("%Y-%m"),
                "incident_type": incident_type,
                "detection_method": detection_method,
                "ai_assisted": ai_assisted,
                "maintenance_cost_usd": round(maint_cost, 2),
                "downtime_hours": round(downtime_hours, 1),
                "downtime_hours_avoided": round(downtime_avoided, 1),
                "avoided_downtime_cost_usd": round(avoided_cost, 2),
                "net_savings_usd": round(net_savings, 2),
                "first_time_fix": _RNG.random() < 0.88 if ai_assisted else _RNG.random() < 0.72,
                "wrench_time_hours": round(_RNG.uniform(1, 4) if ai_assisted else _RNG.uniform(4, 10), 1),
                "planning_time_hours": round(_RNG.uniform(0.5, 2) if ai_assisted else _RNG.uniform(3, 8), 1),
            })
            incident_id += 1

    logger.info("ROI: Seeded %d historical incidents (12 months)", len(_HISTORICAL_INCIDENTS))


_seed_historical_data()


# ---------------------------------------------------------------------------
# Public ROI API
# ---------------------------------------------------------------------------

def calculate_incident_roi(
    equipment_id: str,
    maintenance_cost_usd: float,
    downtime_hours_avoided: float,
    detection_method: str = "AI-Predictive",
    labor_hours: float = 0,
    parts_cost_usd: float = 0,
    contractor_hours: float = 0,
    production_rate_usd_per_hour: float = PRODUCTION_RATE_USD_PER_HOUR,
    margin: float = PRODUCT_MARGIN,
) -> dict:
    """
    Compute ROI for a single maintenance incident.

    Returns:
        Dict with avoided cost, maintenance cost, net savings, and ROI%
    """
    avoided_downtime_cost = round(downtime_hours_avoided * production_rate_usd_per_hour * margin, 2)
    labor_cost = round(labor_hours * LABOR_RATE, 2)
    contractor_cost = round(contractor_hours * CONTRACTOR_RATE, 2)
    total_maint_cost = round(maintenance_cost_usd + labor_cost + contractor_cost, 2)
    net_savings = round(avoided_downtime_cost - total_maint_cost, 2)
    roi_pct = round((net_savings / max(total_maint_cost, 1)) * 100, 1) if total_maint_cost > 0 else 0.0

    record = {
        "equipment_id": equipment_id,
        "calculated_at": datetime.now().isoformat(),
        "detection_method": detection_method,
        "avoided_downtime_cost_usd": avoided_downtime_cost,
        "maintenance_cost_usd": total_maint_cost,
        "labor_cost_usd": labor_cost,
        "parts_cost_usd": parts_cost_usd,
        "contractor_cost_usd": contractor_cost,
        "net_savings_usd": net_savings,
        "roi_pct": roi_pct,
        "downtime_hours_avoided": downtime_hours_avoided,
        "inputs": {
            "production_rate_usd_per_hour": production_rate_usd_per_hour,
            "margin": margin,
        },
    }
    return record


def register_incident_roi(incident_id: str, roi_record: dict) -> None:
    """Register a real-time incident ROI record."""
    _ACTIVE_ROI_RECORDS[incident_id] = roi_record
    logger.info("ROI: Registered incident %s | net_savings=%.0f", incident_id, roi_record.get("net_savings_usd", 0))


def calculate_cumulative_roi() -> dict:
    """
    Calculate cumulative annual ROI from all historical and active incidents.
    """
    all_incidents = _HISTORICAL_INCIDENTS + list(_ACTIVE_ROI_RECORDS.values())
    ai_incidents = [i for i in all_incidents if i.get("ai_assisted", True) or i.get("detection_method") == "AI-Predictive"]

    total_avoided_cost = sum(i.get("avoided_downtime_cost_usd", 0) for i in ai_incidents)
    total_maint_cost = sum(i.get("maintenance_cost_usd", 0) for i in all_incidents)
    total_net_savings = sum(i.get("net_savings_usd", 0) for i in ai_incidents)
    cumulative_roi_pct = round((total_net_savings / AI_SYSTEM_ANNUAL_COST) * 100, 1) if AI_SYSTEM_ANNUAL_COST > 0 else 0

    # First-time fix rate
    incidents_with_ftf = [i for i in all_incidents if "first_time_fix" in i]
    ftf_rate = round(
        sum(1 for i in incidents_with_ftf if i["first_time_fix"]) / max(len(incidents_with_ftf), 1) * 100, 1
    )

    # Wrench time improvement (AI-assisted vs reactive)
    ai_wrench = [i.get("wrench_time_hours", 0) for i in all_incidents if i.get("ai_assisted")]
    reactive_wrench = [i.get("wrench_time_hours", 0) for i in all_incidents if not i.get("ai_assisted")]
    avg_ai_wrench = round(sum(ai_wrench) / max(len(ai_wrench), 1), 1)
    avg_reactive_wrench = round(sum(reactive_wrench) / max(len(reactive_wrench), 1), 1)
    wrench_improvement_pct = round(
        (avg_reactive_wrench - avg_ai_wrench) / max(avg_reactive_wrench, 0.1) * 100, 1
    )

    # PM compliance rate (AI-assisted incidents = proactive)
    pm_count = sum(1 for i in all_incidents if i.get("incident_type") == "PdM")
    pm_compliance_pct = round(pm_count / max(len(all_incidents), 1) * 100, 1)

    return {
        "summary": {
            "total_incidents": len(all_incidents),
            "ai_assisted_incidents": len(ai_incidents),
            "total_avoided_downtime_cost_usd": round(total_avoided_cost, 2),
            "total_maintenance_cost_usd": round(total_maint_cost, 2),
            "total_net_savings_usd": round(total_net_savings, 2),
            "ai_system_annual_cost_usd": AI_SYSTEM_ANNUAL_COST,
            "cumulative_roi_pct": cumulative_roi_pct,
        },
        "kpis": {
            "first_time_fix_rate_pct": ftf_rate,
            "pm_compliance_rate_pct": pm_compliance_pct,
            "avg_wrench_time_ai_hours": avg_ai_wrench,
            "avg_wrench_time_reactive_hours": avg_reactive_wrench,
            "wrench_time_improvement_pct": wrench_improvement_pct,
            "backlog_reduction_pct": round(wrench_improvement_pct * 0.6, 1),
        },
        "ai_system_cost_usd": AI_SYSTEM_ANNUAL_COST,
        "calculated_at": datetime.now().isoformat(),
    }


def get_monthly_roi_trend() -> list[dict]:
    """Return 12-month monthly ROI trend data for dashboard charts."""
    all_incidents = _HISTORICAL_INCIDENTS
    months: dict[str, dict] = {}

    for inc in all_incidents:
        m = inc.get("month", "unknown")
        if m not in months:
            months[m] = {
                "month": m,
                "avoided_cost": 0,
                "maintenance_cost": 0,
                "net_savings": 0,
                "incident_count": 0,
                "ai_count": 0,
            }
        months[m]["avoided_cost"] += inc.get("avoided_downtime_cost_usd", 0)
        months[m]["maintenance_cost"] += inc.get("maintenance_cost_usd", 0)
        months[m]["net_savings"] += inc.get("net_savings_usd", 0)
        months[m]["incident_count"] += 1
        if inc.get("ai_assisted"):
            months[m]["ai_count"] += 1

    result = sorted(months.values(), key=lambda x: x["month"])
    # Add cumulative savings
    cumulative = 0.0
    for row in result:
        cumulative += row["net_savings"]
        row["cumulative_savings"] = round(cumulative, 2)
        row["avoided_cost"] = round(row["avoided_cost"], 2)
        row["maintenance_cost"] = round(row["maintenance_cost"], 2)
        row["net_savings"] = round(row["net_savings"], 2)
    return result


def get_mtbf_by_equipment() -> dict[str, dict]:
    """Return MTBF before/after AI implementation per equipment."""
    from ..enterprise_systems.cmms_simulator import calculate_mtbf
    equipment_ids = ["P-101", "P-102", "K-201", "R-301", "E-401", "PSV-501", "T-601", "P-103", "K-202", "E-402"]

    result = {}
    baselines = {"PUMP": 8760, "COMPRESSOR": 7000, "REACTOR": 43800,
                 "HEAT_EXCHANGER": 35000, "SAFETY_VALVE": 26280, "DISTILLATION_COLUMN": 87600}

    def eq_type(eid: str) -> str:
        if eid.startswith("P-"): return "PUMP"
        if eid.startswith("K-"): return "COMPRESSOR"
        if eid.startswith("R-"): return "REACTOR"
        if eid.startswith("E-"): return "HEAT_EXCHANGER"
        if eid.startswith("PSV-"): return "SAFETY_VALVE"
        return "DISTILLATION_COLUMN"

    for eid in equipment_ids:
        etyp = eq_type(eid)
        baseline = baselines.get(etyp, 8760)
        actual_mtbf = calculate_mtbf(eid)
        # Simulate improvement: AI gives 15-30% MTBF improvement
        ai_mtbf = round(baseline * _RNG.uniform(1.15, 1.30), 0)
        result[eid] = {
            "equipment_id": eid,
            "equipment_type": etyp,
            "baseline_mtbf_hours": baseline,
            "calculated_mtbf_hours": actual_mtbf,
            "ai_assisted_mtbf_hours": ai_mtbf,
            "improvement_pct": round((ai_mtbf - baseline) / baseline * 100, 1),
        }
    return result


def get_all_historical_incidents() -> list[dict]:
    return list(_HISTORICAL_INCIDENTS)
