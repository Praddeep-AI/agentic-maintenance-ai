"""
Enterprise Systems Layer — HSE Simulator
Simulates Health, Safety & Environment incident management, permits, and regulatory tracking.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Permit-to-Work registry
# ---------------------------------------------------------------------------
_PERMITS: dict[str, dict] = {}
_REGULATORY_LOG: list[dict] = []
_PSV_INSPECTION_REGISTRY: dict[str, dict] = {
    "PSV-501": {
        "equipment_id": "PSV-501",
        "last_inspection": "2023-07-15",
        "next_due": "2024-07-15",
        "inspection_interval_days": 365,
        "governing_standard": "API 510",
        "regulatory_body": "OSHA 1910.119",
        "days_overdue": 7,
        "status": "OVERDUE",
    },
    "PSV-502": {
        "equipment_id": "PSV-502",
        "last_inspection": "2024-01-10",
        "next_due": "2025-01-10",
        "inspection_interval_days": 365,
        "governing_standard": "API 510",
        "regulatory_body": "OSHA 1910.119",
        "days_overdue": 0,
        "status": "COMPLIANT",
    },
}

_CUI_REGISTRY: dict[str, dict] = {
    "T-601": {
        "equipment_id": "T-601",
        "last_cui_survey": "2022-07-01",
        "next_due": "2024-07-01",
        "inspection_interval_days": 730,
        "risk_score": 0.78,
        "risk_basis": "Operating temperature 50-175°C, insulation age 15yr, previous minor corrosion found",
        "days_overdue": 15,
        "status": "OVERDUE",
    },
    "E-402": {
        "equipment_id": "E-402",
        "last_cui_survey": "2023-03-15",
        "next_due": "2025-03-15",
        "inspection_interval_days": 730,
        "risk_score": 0.54,
        "risk_basis": "Moderate temperature cycling, insulation age 16yr",
        "days_overdue": 0,
        "status": "COMPLIANT",
    },
}


def issue_permit_to_work(
    work_order_id: str,
    equipment_id: str,
    permit_type: str,
    hazards: list[str],
    precautions: list[str],
    issued_by: str = "HSE_System",
) -> dict:
    """Issue a Permit-to-Work for a maintenance activity."""
    permit_id = f"PTW-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    permit = {
        "permit_id": permit_id,
        "work_order_id": work_order_id,
        "equipment_id": equipment_id,
        "permit_type": permit_type,
        "hazards": hazards,
        "precautions": precautions,
        "issued_by": issued_by,
        "issued_at": datetime.now().isoformat(),
        "valid_until": (datetime.now() + timedelta(hours=12)).isoformat(),
        "status": "ACTIVE",
        "closed_at": None,
    }
    _PERMITS[permit_id] = permit
    logger.info("HSE: PTW issued | permit_id=%s | equipment=%s | type=%s", permit_id, equipment_id, permit_type)
    return permit


def close_permit(permit_id: str, closed_by: str = "technician") -> dict:
    """Close a permit after work completion."""
    if permit_id not in _PERMITS:
        raise KeyError(f"Permit {permit_id!r} not found")
    _PERMITS[permit_id]["status"] = "CLOSED"
    _PERMITS[permit_id]["closed_at"] = datetime.now().isoformat()
    _PERMITS[permit_id]["closed_by"] = closed_by
    return _PERMITS[permit_id]


def get_overdue_inspections() -> list[dict]:
    """Return list of overdue safety valve and CUI inspections."""
    overdue = []
    for item in _PSV_INSPECTION_REGISTRY.values():
        if item["status"] == "OVERDUE":
            overdue.append({"type": "PSV", **item})
    for item in _CUI_REGISTRY.values():
        if item["status"] == "OVERDUE":
            overdue.append({"type": "CUI", **item})
    return overdue


def get_inspection_schedule() -> list[dict]:
    """Return full inspection schedule for safety valves and CUI."""
    schedule = []
    for item in _PSV_INSPECTION_REGISTRY.values():
        schedule.append({"type": "PSV", **item})
    for item in _CUI_REGISTRY.values():
        schedule.append({"type": "CUI", **item})
    return schedule


def log_regulatory_notification(
    equipment_id: str,
    incident_type: str,
    regulatory_body: str,
    description: str,
    notification_required: bool = True,
) -> dict:
    """Log a regulatory notification event."""
    entry = {
        "log_id": f"REG-{uuid.uuid4().hex[:8].upper()}",
        "equipment_id": equipment_id,
        "incident_type": incident_type,
        "regulatory_body": regulatory_body,
        "description": description,
        "notification_required": notification_required,
        "notified": False,
        "logged_at": datetime.now().isoformat(),
    }
    _REGULATORY_LOG.append(entry)
    if notification_required:
        logger.warning(
            "HSE: Regulatory notification required | body=%s | equipment=%s | type=%s",
            regulatory_body, equipment_id, incident_type,
        )
    return entry


def get_regulatory_log() -> list[dict]:
    return list(_REGULATORY_LOG)


def check_compliance_status(equipment_id: str) -> dict:
    """Return compliance status for a given equipment item."""
    psv = _PSV_INSPECTION_REGISTRY.get(equipment_id)
    cui = _CUI_REGISTRY.get(equipment_id)
    return {
        "equipment_id": equipment_id,
        "psv_compliance": psv,
        "cui_compliance": cui,
        "overall_compliant": (
            (psv is None or psv["status"] == "COMPLIANT") and
            (cui is None or cui["status"] == "COMPLIANT")
        ),
    }


def get_jsa_requirements(equipment_type: str, hazard_class: str) -> dict:
    """Return Job Safety Analysis requirements based on equipment and hazard class."""
    base_precautions = ["LOTO (Lockout/Tagout)", "Gas test prior to entry", "Fire watch during hot work"]

    hazard_precautions = {
        "Flammable": ["Continuous gas monitoring", "Hot work permit required", "Foam/CO2 extinguisher on site"],
        "Flammable/Explosive": [
            "Nitrogen purge before opening", "Explosion-proof tools only",
            "No ignition sources within 15m", "Emergency gas detector alarm",
        ],
        "Flammable/High-Temp": [
            "Allow cooldown to < 50°C before opening", "Thermal PPE required",
            "Pressure bleed-off verification", "Hydrogen safety briefing",
        ],
        "Flammable/High-Pressure": [
            "Full pressure relief before work", "High-pressure jetting PPE",
            "Hearing protection mandatory", "Buddy system required",
        ],
    }

    type_permits = {
        "PUMP": ["Mechanical Isolation PTW", "Liquid Release PTW"],
        "COMPRESSOR": ["Mechanical Isolation PTW", "Gas Release PTW", "Confined Space PTW (if applicable)"],
        "REACTOR": ["Process Equipment PTW", "Catalyst Handling PTW", "Hot Work PTW"],
        "HEAT_EXCHANGER": ["Mechanical Isolation PTW", "Pressure Test PTW"],
        "SAFETY_VALVE": ["Isolation PTW", "Pressure Relief PTW", "API 510 Test Permit"],
        "DISTILLATION_COLUMN": ["Confined Space Entry PTW", "Hot Work PTW", "High Temperature PTW"],
    }

    return {
        "equipment_type": equipment_type,
        "hazard_class": hazard_class,
        "base_precautions": base_precautions,
        "hazard_specific_precautions": hazard_precautions.get(hazard_class, []),
        "required_permits": type_permits.get(equipment_type, ["General Work PTW"]),
        "ppe_requirements": ["Hard hat", "Safety glasses", "Steel-toe boots", "Flame-resistant coveralls",
                             "Chemical resistant gloves", "H2S detector clip"],
        "minimum_crew": 2,
        "safety_officer_required": hazard_class in ["Flammable/Explosive", "Flammable/High-Temp"],
    }
