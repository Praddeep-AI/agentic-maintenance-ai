"""
Workflow Layer — Human Approval Interface
Interactive CLI approval panel for maintenance supervisors to review,
approve, reject, or modify AI-generated work orders.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Optional

from .state_machine import WorkflowInstance, WorkflowState, registry

logger = logging.getLogger(__name__)


def _format_work_order_summary(wf: WorkflowInstance) -> str:
    """Format a human-readable work order summary for the approval interface."""
    wo = wf.work_order_draft or {}
    diag = wf.diagnosis_result or {}
    lines = [
        "",
        "=" * 70,
        "  AGENTIC MAINTENANCE AI — WORK ORDER APPROVAL REQUEST",
        "=" * 70,
        f"  Workflow ID  : {wf.workflow_id}",
        f"  Equipment    : {wf.equipment_id}",
        f"  Work Order   : {wo.get('work_order_id', 'N/A')}",
        f"  Alert        : {wf.alert_description[:80]}",
        f"  Scenario     : {wf.scenario or 'N/A'}",
        "",
        "  ─── DIAGNOSIS SUMMARY ────────────────────────────────────────────",
        f"  Failure Mode  : {diag.get('failure_mode', 'N/A')}",
        f"  Risk Score    : {diag.get('risk_score', 'N/A')} / 10",
        f"  Criticality   : {diag.get('criticality', 'N/A')}",
        f"  FMEA RPN      : {diag.get('fmea_rpn', 'N/A')}",
        f"  Predicted Fail: {str(diag.get('predicted_failure_hours', 'N/A')) + 'h' if diag.get('predicted_failure_hours') is not None else 'N/A (Compliance/Risk-based)'}",
        "",
        "  ─── WORK ORDER DETAILS ───────────────────────────────────────────",
        f"  Title         : {wo.get('title', 'N/A')}",
        f"  Priority      : {wo.get('priority', 'N/A')}",
        f"  Type          : {wo.get('maintenance_type', 'N/A')}",
        f"  Labor Hours   : {wo.get('labor_hours', 'N/A')}",
        f"  Estimated Cost: ${wo.get('estimated_cost_usd', 0):,.0f}",
        f"  Parts List    : {', '.join(wo.get('parts_list', [])[:3])}{'...' if len(wo.get('parts_list', [])) > 3 else ''}",
        f"  Crew          : {', '.join(wo.get('assigned_crew', []))}",
        f"  Planned Start : {wo.get('planned_start', 'N/A')}",
        "",
        "  ─── FINANCIAL IMPACT ────────────────────────────────────────────",
    ]
    if wf.roi_record:
        roi = wf.roi_record
        lines += [
            f"  Avoided Cost  : ${roi.get('avoided_downtime_cost_usd', 0):,.0f}",
            f"  Maint Cost    : ${roi.get('maintenance_cost_usd', 0):,.0f}",
            f"  Net Savings   : ${roi.get('net_savings_usd', 0):,.0f}",
            f"  ROI           : {roi.get('roi_pct', 0):.1f}%",
        ]

    lines += [
        "",
        "  ─── AI REASONING ────────────────────────────────────────────────",
    ]
    for reasoning in wf.agent_reasoning[-3:]:
        lines.append(f"  [{reasoning['agent']}] {reasoning['decision'][:70]}")

    lines += [
        "",
        "  ─── SAFETY & COMPLIANCE ─────────────────────────────────────────",
        f"  Safety Reqs   : {', '.join(wo.get('safety_requirements', [])[:3])}",
    ]
    if wf.approval_deadline:
        remaining = (wf.approval_deadline - datetime.now()).total_seconds() / 60
        lines.append(f"  Approval Due  : {wf.approval_deadline.strftime('%H:%M:%S')} ({remaining:.0f} min remaining)")

    lines += [
        "=" * 70,
        "",
    ]
    return "\n".join(lines)


def present_approval_interface(
    wf: WorkflowInstance,
    auto_approve: bool = False,
    auto_approve_delay: float = 2.0,
    prefill_decision: Optional[str] = None,
    prefill_comment: str = "",
) -> dict:
    """
    Present the human approval interface for a work order.

    Args:
        wf: The workflow instance awaiting approval
        auto_approve: If True, auto-approves after `auto_approve_delay` seconds (demo mode)
        auto_approve_delay: Seconds to wait before auto-approval in demo mode
        prefill_decision: Pre-filled decision for non-interactive runs ("APPROVED"/"REJECTED")
        prefill_comment: Pre-filled comment

    Returns:
        dict with decision, comment, approver, timestamp
    """
    try:
        print(_format_work_order_summary(wf))
    except UnicodeEncodeError:
        print(_format_work_order_summary(wf).encode("ascii", errors="replace").decode("ascii"))

    if prefill_decision:
        decision = prefill_decision.upper()
        comment = prefill_comment
        approver = "AutoApproval-Demo"
        print(f"  [AUTO] Decision: {decision} | Comment: {comment or '(none)'}")
        print()
    elif auto_approve:
        print(f"  [DEMO] Auto-approving in {auto_approve_delay:.0f} seconds (demo mode)...")
        time.sleep(auto_approve_delay)
        decision = "APPROVED"
        comment = "Auto-approved by demo supervisor (simulated)"
        approver = "Demo-Supervisor"
        print(f"  [OK] Auto-approved by: {approver}")
        print()
    else:
        # Interactive CLI
        print("  OPTIONS: [A]pprove  [R]eject  [M]odify comment")
        try:
            choice = input("  Your decision: ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            choice = "A"

        if choice in ("A", "APPROVE", "APPROVED"):
            decision = "APPROVED"
            try:
                comment = input("  Comment (optional): ").strip()
            except (EOFError, KeyboardInterrupt):
                comment = ""
            approver = "Supervisor"
        elif choice in ("R", "REJECT", "REJECTED"):
            decision = "REJECTED"
            try:
                comment = input("  Rejection reason: ").strip()
            except (EOFError, KeyboardInterrupt):
                comment = "Rejected"
            approver = "Supervisor"
        else:
            decision = "APPROVED"
            comment = "Modified and approved"
            approver = "Supervisor"

    result = {
        "decision": decision,
        "approver": approver,
        "comment": comment,
        "timestamp": datetime.now().isoformat(),
        "workflow_id": wf.workflow_id,
    }

    # Apply decision to workflow
    from ..enterprise_systems.cmms_simulator import approve_work_order
    if wf.work_order_id:
        approve_work_order(wf.work_order_id, approver, decision, comment)

    wf.approver = approver
    wf.approval_comment = comment

    if decision == "APPROVED":
        wf.transition(WorkflowState.APPROVED, actor=approver, comment=comment)
    else:
        wf.transition(WorkflowState.REJECTED, actor=approver, comment=comment)
        print(f"  [REJECTED] Work order REJECTED. Reason: {comment}")

    logger.info(
        "APPROVAL: %s | wf=%s | approver=%s | comment=%s",
        decision, wf.workflow_id, approver, comment[:50]
    )
    return result


def check_escalation_timeouts() -> list[str]:
    """
    Check all workflows pending approval and escalate any that have exceeded the timeout.
    Returns list of escalated workflow IDs.
    """
    escalated = []
    for wf in registry.get_pending_approval():
        if wf.is_approval_expired():
            from ..config_loader import get_config
            cfg = get_config()
            escalation_recipient = cfg.get("workflow", {}).get(
                "escalation_recipient", "senior_engineer@plant.example.com"
            )
            wf.transition(
                WorkflowState.ESCALATED,
                actor="auto_escalation",
                comment=f"Approval timeout exceeded. Escalated to {escalation_recipient}",
            )
            from ..tools.notification_tools import notification_sender
            notification_sender(
                recipients=[escalation_recipient],
                message=(
                    f"ESCALATION: Work order {wf.work_order_id} for {wf.equipment_id} "
                    f"has exceeded the approval deadline and requires immediate attention."
                ),
                urgency_level="CRITICAL",
                work_order_id=wf.work_order_id,
            )
            logger.warning("ESCALATION: Workflow %s escalated | equipment=%s", wf.workflow_id, wf.equipment_id)
            escalated.append(wf.workflow_id)
    return escalated
