"""
Tools Layer — Safety Tools
Callable by agents to retrieve JSA, PTW, and regulatory safety procedure information.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..enterprise_systems.hse_simulator import (
    get_jsa_requirements,
    issue_permit_to_work,
    get_overdue_inspections,
    get_inspection_schedule,
    check_compliance_status,
    log_regulatory_notification,
)

logger = logging.getLogger(__name__)


def safety_procedure_retriever(equipment_type: str, hazard_class: str) -> dict:
    """
    Return JSA requirements, required permits, and PPE for a given equipment type and hazard class.
    """
    logger.info("TOOL:safety_procedure_retriever | type=%s | hazard=%s", equipment_type, hazard_class)
    return get_jsa_requirements(equipment_type, hazard_class)


def request_permit_to_work(
    work_order_id: str,
    equipment_id: str,
    permit_type: str,
    hazards: list[str],
    precautions: list[str],
) -> dict:
    """Issue a Permit-to-Work for a maintenance job."""
    logger.info("TOOL:request_permit_to_work | wo=%s | equipment=%s | type=%s",
                work_order_id, equipment_id, permit_type)
    return issue_permit_to_work(work_order_id, equipment_id, permit_type, hazards, precautions)


def check_regulatory_compliance(equipment_id: str) -> dict:
    """Check inspection and regulatory compliance status for an equipment item."""
    logger.info("TOOL:check_regulatory_compliance | equipment=%s", equipment_id)
    compliance = check_compliance_status(equipment_id)
    overdue = get_overdue_inspections()
    equipment_overdue = [o for o in overdue if o["equipment_id"] == equipment_id]
    return {
        **compliance,
        "overdue_items": equipment_overdue,
        "has_overdue_inspections": len(equipment_overdue) > 0,
    }


def get_all_overdue_inspections() -> list[dict]:
    """Return all overdue safety valve and CUI inspections across the plant."""
    logger.info("TOOL:get_all_overdue_inspections")
    return get_overdue_inspections()


def raise_regulatory_notification(
    equipment_id: str,
    incident_type: str,
    regulatory_body: str,
    description: str,
) -> dict:
    """Log and raise a regulatory notification event."""
    logger.warning("TOOL:raise_regulatory_notification | equipment=%s | body=%s | type=%s",
                   equipment_id, regulatory_body, incident_type)
    return log_regulatory_notification(equipment_id, incident_type, regulatory_body, description)
