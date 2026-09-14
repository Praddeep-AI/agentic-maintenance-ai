"""
Agent: ComplianceAgent
Checks maintenance plans against OSHA, EPA, API, and industry-specific regulatory requirements.
Flags non-compliance issues before any action is executed.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..enterprise_systems.hse_simulator import check_compliance_status, get_overdue_inspections

logger = logging.getLogger(__name__)

# Compliance rules by equipment type
_COMPLIANCE_RULES: dict[str, list[dict]] = {
    "PUMP": [
        {"id": "R-PUMP-001", "rule": "LOTO procedure required before mechanical isolation", "body": "OSHA 1910.147"},
        {"id": "R-PUMP-002", "rule": "P&ID markup and area classification review required", "body": "API RP 505"},
    ],
    "COMPRESSOR": [
        {"id": "R-COMP-001", "rule": "Gas leak test required before startup post-maintenance", "body": "ASME B31.3"},
        {"id": "R-COMP-002", "rule": "PSSR (Pre-Start Safety Review) required for compressor overhaul", "body": "OSHA 1910.119"},
        {"id": "R-COMP-003", "rule": "Flammable gas area classification — hot work permit required", "body": "NFPA 54"},
    ],
    "REACTOR": [
        {"id": "R-REAC-001", "rule": "Management of Change (MOC) required for catalyst change", "body": "OSHA 1910.119 PSM"},
        {"id": "R-REAC-002", "rule": "Confined space permit required for internal work", "body": "OSHA 1910.146"},
        {"id": "R-REAC-003", "rule": "Pyrophoric material handling procedure required", "body": "API RP 2003"},
    ],
    "HEAT_EXCHANGER": [
        {"id": "R-HX-001", "rule": "Pressure test required post tube repair per ASME BPVC Sec VIII", "body": "ASME BPVC"},
        {"id": "R-HX-002", "rule": "Tube plugging limited to maximum 10% per NHT policy", "body": "TEMA/Company-SOP"},
    ],
    "SAFETY_VALVE": [
        {"id": "R-PSV-001", "rule": "API 510 certified inspector required for PSV inspection", "body": "API 510"},
        {"id": "R-PSV-002", "rule": "Inspection results must be entered in inspection database within 24 hours", "body": "OSHA 1910.119"},
        {"id": "R-PSV-003", "rule": "Notify AHJ (Authority Having Jurisdiction) if inspection overdue", "body": "Local Regulation"},
    ],
    "DISTILLATION_COLUMN": [
        {"id": "R-COL-001", "rule": "CUI inspection requires written NDE procedure per API 581", "body": "API 581 RBI"},
        {"id": "R-COL-002", "rule": "Confined space entry requires atmospheric testing and standby person", "body": "OSHA 1910.146"},
        {"id": "R-COL-003", "rule": "High-temperature work requires thermal PPE and burn protocol", "body": "NFPA 70E"},
    ],
}

# Regulatory violation scenarios
_VIOLATION_SCENARIOS = {
    "safety_valve_overdue": {
        "violations": [
            {
                "rule_id": "R-PSV-003",
                "description": "PSV-501 inspection is 7 days overdue. AHJ notification required.",
                "body": "OSHA 1910.119 / Local AHJ",
                "severity": "HIGH",
                "required_action": "Immediate inspection and AHJ notification within 48 hours",
            }
        ]
    },
    "cui_risk": {
        "violations": [
            {
                "rule_id": "R-COL-001",
                "description": "CUI inspection interval exceeded by 26 days. API 581 requires action.",
                "body": "API 581",
                "severity": "MEDIUM",
                "required_action": "Schedule NDE inspection. Document risk basis for delay.",
            }
        ]
    },
    "reactor_fouling": {
        "violations": []
    },
}


class ComplianceAgent:
    """
    Checks maintenance plans against regulatory and safety requirements.
    Must clear before any work order is approved for execution.
    """

    name = "ComplianceAgent"

    def check(
        self,
        equipment_id: str,
        equipment_type: str,
        scenario: Optional[str],
        work_order_draft: Optional[dict] = None,
        maintenance_history: Optional[dict] = None,
    ) -> dict:
        """
        Perform compliance check for a planned maintenance activity.

        Returns:
            Dict with compliance_status, violations, required_actions, applicable_rules.
        """
        applicable_rules = _COMPLIANCE_RULES.get(equipment_type, [])
        violations: list[dict] = []

        # Check for known violation scenarios
        if scenario and scenario in _VIOLATION_SCENARIOS:
            violations.extend(_VIOLATION_SCENARIOS[scenario].get("violations", []))

        # Check overdue inspections
        compliance = check_compliance_status(equipment_id)
        if not compliance["overall_compliant"]:
            overdue = get_overdue_inspections()
            eq_overdue = [o for o in overdue if o["equipment_id"] == equipment_id]
            for item in eq_overdue:
                violations.append({
                    "rule_id": f"OVERDUE-{item['type']}-{equipment_id}",
                    "description": f"{item['type']} inspection overdue by {item.get('days_overdue', '?')} days.",
                    "body": item.get("governing_standard", "N/A"),
                    "severity": "HIGH",
                    "required_action": "Complete overdue inspection before resuming full operation.",
                })

        has_violations = len(violations) > 0
        severity_levels = [v.get("severity", "LOW") for v in violations]
        max_severity = "HIGH" if "HIGH" in severity_levels else "MEDIUM" if "MEDIUM" in severity_levels else "LOW"

        compliance_status = "NON_COMPLIANT" if has_violations else "COMPLIANT"

        reasoning = (
            f"ComplianceAgent: Checked {equipment_id} ({equipment_type}) against "
            f"{len(applicable_rules)} applicable rules. "
            f"Found {len(violations)} violation(s). "
            f"Status: {compliance_status}."
        )
        if violations:
            reasoning += f" Violations: {[v['description'][:50] for v in violations]}"

        result = {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "compliance_status": compliance_status,
            "violations": violations,
            "violation_count": len(violations),
            "max_severity": max_severity if has_violations else "NONE",
            "applicable_rules": applicable_rules,
            "requires_regulatory_notification": any(
                "AHJ" in v.get("required_action", "") or "regulatory" in v.get("description", "").lower()
                for v in violations
            ),
            "reasoning": reasoning,
        }
        logger.info(
            "AGENT:Compliance | %s | status=%s | violations=%d",
            equipment_id, compliance_status, len(violations)
        )
        return result
