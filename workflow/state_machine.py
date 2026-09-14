"""
Workflow Layer — State Machine
Implements the maintenance workflow state machine with full audit trail.
States: ALERT_DETECTED → DIAGNOSIS_IN_PROGRESS → WORK_ORDER_DRAFTED →
        PENDING_HUMAN_APPROVAL → APPROVED → SCHEDULED → EXECUTED → CLOSED → ROI_CALCULATED
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    ALERT_DETECTED = "ALERT_DETECTED"
    DIAGNOSIS_IN_PROGRESS = "DIAGNOSIS_IN_PROGRESS"
    WORK_ORDER_DRAFTED = "WORK_ORDER_DRAFTED"
    PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    EXECUTED = "EXECUTED"
    CLOSED = "CLOSED"
    ROI_CALCULATED = "ROI_CALCULATED"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"


# Valid state transitions
_TRANSITIONS: dict[WorkflowState, list[WorkflowState]] = {
    WorkflowState.ALERT_DETECTED: [WorkflowState.DIAGNOSIS_IN_PROGRESS],
    WorkflowState.DIAGNOSIS_IN_PROGRESS: [WorkflowState.WORK_ORDER_DRAFTED],
    WorkflowState.WORK_ORDER_DRAFTED: [WorkflowState.PENDING_HUMAN_APPROVAL],
    WorkflowState.PENDING_HUMAN_APPROVAL: [
        WorkflowState.APPROVED, WorkflowState.REJECTED, WorkflowState.ESCALATED
    ],
    WorkflowState.APPROVED: [WorkflowState.SCHEDULED],
    WorkflowState.SCHEDULED: [WorkflowState.EXECUTED],
    WorkflowState.EXECUTED: [WorkflowState.CLOSED],
    WorkflowState.CLOSED: [WorkflowState.ROI_CALCULATED],
    WorkflowState.ESCALATED: [WorkflowState.APPROVED, WorkflowState.REJECTED],
    WorkflowState.ROI_CALCULATED: [],
    WorkflowState.REJECTED: [],
}


class WorkflowInstance:
    """Represents a single maintenance workflow from alert to resolution."""

    def __init__(
        self,
        equipment_id: str,
        alert_description: str,
        alert_source: str = "SCADA",
        scenario: Optional[str] = None,
    ) -> None:
        self.workflow_id = f"WF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        self.equipment_id = equipment_id
        self.alert_description = alert_description
        self.alert_source = alert_source
        self.scenario = scenario
        self.state = WorkflowState.ALERT_DETECTED
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.work_order_id: Optional[str] = None
        self.roi_record: Optional[dict] = None
        self.permit_id: Optional[str] = None

        # Audit trail: every state transition, agent decision, tool call
        self.audit_trail: list[dict] = []
        self.agent_reasoning: list[dict] = []
        self.tool_calls: list[dict] = []

        # Approval tracking
        self.approval_deadline: Optional[datetime] = None
        self.approver: Optional[str] = None
        self.approval_comment: str = ""

        # Stage-level data
        self.diagnosis_result: Optional[dict] = None
        self.work_order_draft: Optional[dict] = None
        self.execution_result: Optional[dict] = None

        self._log_transition(None, WorkflowState.ALERT_DETECTED, "Workflow initiated", "system")

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def transition(
        self,
        new_state: WorkflowState,
        actor: str = "system",
        data: Optional[dict] = None,
        comment: str = "",
    ) -> None:
        """Perform a validated state transition with full audit logging."""
        allowed = _TRANSITIONS.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition {self.state!r} → {new_state!r}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now()
        self._log_transition(old_state, new_state, comment, actor, data)

        if new_state == WorkflowState.PENDING_HUMAN_APPROVAL:
            from ..config_loader import get_config
            cfg = get_config()
            timeout = cfg.get("workflow", {}).get("approval_timeout_minutes", 30)
            self.approval_deadline = datetime.now() + timedelta(minutes=timeout)

        logger.info(
            "WORKFLOW: %s | %s → %s | actor=%s",
            self.workflow_id, old_state.value, new_state.value, actor
        )

    def _log_transition(
        self,
        from_state: Optional[WorkflowState],
        to_state: WorkflowState,
        comment: str,
        actor: str,
        data: Optional[dict] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "from_state": from_state.value if from_state else None,
            "to_state": to_state.value,
            "actor": actor,
            "comment": comment,
            "data_snapshot": data or {},
        }
        self.audit_trail.append(entry)

    def log_agent_reasoning(self, agent_name: str, reasoning: str, decision: str) -> None:
        """Record an agent's reasoning step."""
        self.agent_reasoning.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "state": self.state.value,
            "reasoning": reasoning,
            "decision": decision,
        })

    def log_tool_call(self, tool_name: str, inputs: dict, output_summary: str) -> None:
        """Record a tool invocation."""
        self.tool_calls.append({
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "state": self.state.value,
            "inputs": inputs,
            "output_summary": output_summary,
        })

    def is_approval_expired(self) -> bool:
        if self.state != WorkflowState.PENDING_HUMAN_APPROVAL:
            return False
        return self.approval_deadline is not None and datetime.now() > self.approval_deadline

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "equipment_id": self.equipment_id,
            "alert_description": self.alert_description,
            "scenario": self.scenario,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "work_order_id": self.work_order_id,
            "permit_id": self.permit_id,
            "approver": self.approver,
            "approval_comment": self.approval_comment,
            "approval_deadline": self.approval_deadline.isoformat() if self.approval_deadline else None,
            "audit_trail": self.audit_trail,
            "agent_reasoning": self.agent_reasoning,
            "tool_calls": self.tool_calls,
            "diagnosis_result": self.diagnosis_result,
            "work_order_draft": self.work_order_draft,
            "execution_result": self.execution_result,
            "roi_record": self.roi_record,
        }


# ---------------------------------------------------------------------------
# Workflow Registry — manages all active and historical workflows
# ---------------------------------------------------------------------------
class WorkflowRegistry:
    """Thread-safe registry for all workflow instances."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowInstance] = {}
        self._lock = threading.Lock()

    def create(self, equipment_id: str, alert_description: str,
               alert_source: str = "SCADA", scenario: Optional[str] = None) -> WorkflowInstance:
        wf = WorkflowInstance(equipment_id, alert_description, alert_source, scenario)
        with self._lock:
            self._workflows[wf.workflow_id] = wf
        logger.info("REGISTRY: Workflow created | wf_id=%s | equipment=%s", wf.workflow_id, equipment_id)
        return wf

    def get(self, workflow_id: str) -> Optional[WorkflowInstance]:
        return self._workflows.get(workflow_id)

    def get_all(self) -> list[WorkflowInstance]:
        return list(self._workflows.values())

    def get_active(self) -> list[WorkflowInstance]:
        terminal = {WorkflowState.ROI_CALCULATED, WorkflowState.REJECTED}
        return [wf for wf in self._workflows.values() if wf.state not in terminal]

    def get_pending_approval(self) -> list[WorkflowInstance]:
        return [wf for wf in self._workflows.values()
                if wf.state == WorkflowState.PENDING_HUMAN_APPROVAL]

    def get_escalated(self) -> list[WorkflowInstance]:
        return [wf for wf in self._workflows.values() if wf.state == WorkflowState.ESCALATED]

    def summary(self) -> dict:
        all_wf = self.get_all()
        state_counts: dict[str, int] = {}
        for wf in all_wf:
            state_counts[wf.state.value] = state_counts.get(wf.state.value, 0) + 1
        return {
            "total": len(all_wf),
            "active": len(self.get_active()),
            "pending_approval": len(self.get_pending_approval()),
            "state_breakdown": state_counts,
        }


# Global singleton registry
registry = WorkflowRegistry()
