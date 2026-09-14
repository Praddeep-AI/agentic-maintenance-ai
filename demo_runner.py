"""
Demo Runner — End-to-End Agentic Maintenance Pipeline Demonstration
Completes the full pipeline in under 5 minutes using simulated data and mock LLM.

Run: python demo_runner.py [--scenario <name>] [--interactive]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import pathlib
from datetime import datetime

# Force UTF-8 output on Windows to handle box-drawing and special chars
if sys.platform == "win32":
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Already wrapped or not a real tty

# Ensure the project root is importable
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agentic_maintenance.agents.orchestrator import MaintenanceOrchestrator
from agentic_maintenance.roi.roi_engine import calculate_cumulative_roi, get_monthly_roi_trend
from agentic_maintenance.workflow.state_machine import registry

# ─────────────────────────────────────────────────────────────────────────────
# ANSI colors for terminal output
# ─────────────────────────────────────────────────────────────────────────────
BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
DIM = "\033[2m"


def _print_banner() -> None:
    print(f"""
{BOLD}{BLUE}
╔══════════════════════════════════════════════════════════════════════╗
║      AGENTIC MAINTENANCE AI — END-TO-END DEMONSTRATION              ║
║      Chemicals & Petrochemicals | Critical Asset Management          ║
║      Pipeline: LLM → Agent → Tools → Enterprise Systems →           ║
║               Workflow → Human Approval → Action                     ║
╚══════════════════════════════════════════════════════════════════════╝
{RESET}""")


def _print_stage(n: int, title: str) -> None:
    print(f"\n{BOLD}{CYAN}[STAGE {n}]{RESET} {BOLD}{title}{RESET}")
    print("─" * 70)


def _print_step(icon: str, label: str, value: str = "") -> None:
    print(f"  {icon}  {BOLD}{label}{RESET} {DIM}{value}{RESET}")


def _print_final_report(result: dict, scenario: str, elapsed: float) -> None:
    wf_id = result.get("workflow_id", "N/A")
    roi = result.get("roi", {})
    approval = result.get("approval", {})
    stages = result.get("stages", {})
    diag = stages.get("diagnosis", {})
    criticality = stages.get("criticality", {})
    compliance = stages.get("compliance", {})

    print(f"""
{BOLD}{GREEN}
╔══════════════════════════════════════════════════════════════════════╗
║              FINAL PIPELINE SUMMARY REPORT                          ║
╚══════════════════════════════════════════════════════════════════════╝{RESET}

{BOLD}Workflow ID    :{RESET} {wf_id}
{BOLD}Scenario       :{RESET} {scenario}
{BOLD}Final State    :{RESET} {GREEN}{result.get('final_state', 'N/A')}{RESET}
{BOLD}Total Time     :{RESET} {elapsed:.2f} seconds

{BOLD}── PIPELINE STAGES TRAVERSED ──────────────────────────────────────{RESET}
  ✅  ALERT_DETECTED
  ✅  DIAGNOSIS_IN_PROGRESS
      Failure Mode : {diag.get('failure_mode', 'N/A')}
      Anomalies    : {diag.get('anomaly_count', 0)}
      Time-to-Fail : {str(diag.get('predicted_failure_hours')) + 'h' if diag.get('predicted_failure_hours') is not None else 'N/A (Compliance/Risk-based)'}
  ✅  WORK_ORDER_DRAFTED
      Priority     : {stages.get('approval', {}).get('decision', 'N/A')}
      Criticality  : {criticality.get('criticality', 'N/A')} (RPN={criticality.get('fmea_rpn', 'N/A')})
  ✅  PENDING_HUMAN_APPROVAL
      Approver     : {approval.get('approver', 'N/A')}
      Decision     : {GREEN}{approval.get('decision', 'N/A')}{RESET}
      Comment      : {approval.get('comment', '—')}
  ✅  APPROVED → SCHEDULED → EXECUTED → CLOSED
  ✅  ROI_CALCULATED

{BOLD}── FINANCIAL IMPACT ────────────────────────────────────────────────{RESET}
  💰  Avoided Downtime Cost : ${roi.get('avoided_downtime_cost_usd', 0):>12,.0f}
  🔧  Maintenance Cost      : ${roi.get('maintenance_cost_usd', 0):>12,.0f}
  📈  Net Savings           : ${roi.get('net_savings_usd', 0):>12,.0f}
  🎯  ROI                   : {roi.get('roi_pct', 0):>11.1f}%

{BOLD}── COMPLIANCE ──────────────────────────────────────────────────────{RESET}
  Status     : {GREEN if compliance.get('compliance_status') == 'COMPLIANT' else RED}{compliance.get('compliance_status', 'N/A')}{RESET}
  Violations : {compliance.get('violation_count', 0)}

{BOLD}── CUMULATIVE SYSTEM ROI (12-month) ────────────────────────────────{RESET}""")

    cumulative = calculate_cumulative_roi()
    sum_data = cumulative["summary"]
    kpis = cumulative["kpis"]
    print(f"""
  Total Net Savings         : ${sum_data['total_net_savings_usd']:>12,.0f}
  Cumulative ROI            : {sum_data['cumulative_roi_pct']:>10.1f}%
  AI System Cost            : ${sum_data['ai_system_annual_cost_usd']:>12,.0f}
  First-Time Fix Rate       : {kpis['first_time_fix_rate_pct']:>10.1f}%
  PM Compliance Rate        : {kpis['pm_compliance_rate_pct']:>10.1f}%
  Wrench Time Improvement   : {kpis['wrench_time_improvement_pct']:>10.1f}%
  Backlog Reduction         : {kpis['backlog_reduction_pct']:>10.1f}%

{BOLD}{GREEN}Demo complete. Launch dashboard with:{RESET}
  streamlit run agentic_maintenance/dashboard/app.py
""")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario definitions
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS = {
    "bearing_vibration_anomaly": {
        "equipment_id": "P-101",
        "alert": (
            "⚠️  SCADA ALERT: P-101 NDE bearing vibration at 8.4 mm/s "
            "(ISO 10816 Zone D, critical threshold exceeded). "
            "Co-rising bearing temperature to 94°C. Trend: exponential over 18 hours."
        ),
        "description": "Bearing Vibration Anomaly — P-101 Crude Oil Centrifugal Pump",
    },
    "reactor_fouling": {
        "equipment_id": "R-301",
        "alert": (
            "⚠️  PROCESS ALERT: R-301 differential pressure across catalyst bed "
            "at 1.38 bar (+58% above baseline). Declining conversion efficiency observed. "
            "Catalyst fouling suspected."
        ),
        "description": "Reactor Catalyst Fouling — R-301 Hydrotreating Fixed-Bed Reactor",
    },
    "heat_exchanger_tube_leak": {
        "equipment_id": "E-401",
        "alert": (
            "⚠️  PROCESS ALERT: E-401 tube-side outlet temperature 374°C — "
            "exceeds design cross temperature. Shell-side ΔP elevated 24%. "
            "Tube bundle tube leak suspected."
        ),
        "description": "Heat Exchanger Tube Leak — E-401 Naphtha Feed/Effluent HX",
    },
    "compressor_valve_failure": {
        "equipment_id": "K-201",
        "alert": (
            "🚨 CRITICAL ALERT: K-201 Stage-1 discharge temperature at 128°C (+28°C). "
            "Compressor efficiency at 0.71 (-13.4%). Valve temperature asymmetry confirmed. "
            "Discharge valve failure imminent — de-rate immediately."
        ),
        "description": "Compressor Valve Failure — K-201 High-Pressure Gas Compressor",
    },
    "safety_valve_overdue": {
        "equipment_id": "PSV-501",
        "alert": (
            "⚠️  COMPLIANCE ALERT: PSV-501 annual inspection overdue by 7 days. "
            "Regulatory non-compliance under OSHA 1910.119 and API 510. "
            "Immediate action required — AHJ notification mandatory."
        ),
        "description": "PSV Inspection Compliance — PSV-501 Reactor Overhead Safety Valve",
    },
    "cui_risk": {
        "equipment_id": "T-601",
        "alert": (
            "⚠️  INSPECTION ALERT: T-601 CUI inspection overdue by 26 days. "
            "Risk score 0.78 (HIGH). Shell zones A4-A7 in maximum CUI risk temperature band. "
            "API 581 RBI inspection required."
        ),
        "description": "Corrosion Under Insulation Risk — T-601 Crude Distillation Column",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline progress printer
# ─────────────────────────────────────────────────────────────────────────────
def _make_progress_printer() -> callable:
    stage_counter = [0]
    stage_groups = {
        "PIPELINE_START": (1, "Pipeline Initialization"),
        "WORKFLOW_CREATED": None,
        "SENSOR_FETCH": (2, "Sensor Data Acquisition (SCADA)"),
        "HISTORY_LOOKUP": (3, "Equipment History (CMMS)"),
        "DIAGNOSTICS": (4, "LLM + Predictive Diagnostics"),
        "CRITICALITY": (5, "FMEA Criticality Assessment"),
        "COMPLIANCE": (6, "Regulatory Compliance Check"),
        "INVENTORY": (7, "Parts Inventory (ERP)"),
        "WORK_ORDER": (8, "Work Order Generation"),
        "ROI_CALC": (9, "ROI Calculation"),
        "CMMS_WO_SAVED": (10, "Work Order → CMMS"),
        "PENDING_APPROVAL": (11, "Human Approval Interface"),
        "APPROVED": (12, "Approval Received"),
        "SCHEDULED": (13, "Scheduled for Execution"),
        "EXECUTED": (14, "Work Order Executed"),
        "VALIDATION": (15, "Post-Maintenance Validation"),
        "CLOSED": (16, "Work Order Closed"),
        "ROI_FINAL": (17, "Final ROI Calculation"),
        "PIPELINE_COMPLETE": (18, "Pipeline Complete"),
    }

    def _callback(step: str, message: str) -> None:
        info = stage_groups.get(step)
        if info:
            n, title = info
            _print_stage(n, title)
        print(f"  {message}")
        time.sleep(0.15)  # Simulate realistic pipeline pacing

    return _callback


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic Maintenance AI Demo Runner")
    parser.add_argument(
        "--scenario",
        default="bearing_vibration_anomaly",
        choices=list(SCENARIOS.keys()),
        help="Scenario to demonstrate (default: bearing_vibration_anomaly)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Show interactive approval prompt (requires terminal input)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all 6 scenarios sequentially",
    )
    args = parser.parse_args()

    _print_banner()
    scenarios_to_run = list(SCENARIOS.keys()) if args.all else [args.scenario]

    for scenario_key in scenarios_to_run:
        scenario_info = SCENARIOS[scenario_key]
        print(f"\n{BOLD}{MAGENTA}{'='*70}{RESET}")
        print(f"{BOLD}{MAGENTA}SCENARIO: {scenario_info['description']}{RESET}")
        print(f"{BOLD}{MAGENTA}{'='*70}{RESET}\n")
        print(f"  {YELLOW}ALERT:{RESET} {scenario_info['alert']}\n")

        time.sleep(0.5)

        progress_printer = _make_progress_printer()
        orchestrator = MaintenanceOrchestrator(
            offline_mode=True,
            progress_callback=progress_printer,
        )

        result = orchestrator.run_pipeline(
            equipment_id=scenario_info["equipment_id"],
            alert_description=scenario_info["alert"],
            scenario=scenario_key,
            auto_approve=not args.interactive,
            prefill_decision="APPROVED",
            interactive=args.interactive,
        )

        _print_final_report(result, scenario_key, result.get("elapsed_seconds", 0))

        if args.all and scenario_key != scenarios_to_run[-1]:
            print(f"\n{DIM}{'─'*70}\nNext scenario in 2 seconds...\n{RESET}")
            time.sleep(2)

    print(f"\n{BOLD}{GREEN}{'='*70}")
    print("  All scenarios complete.")
    print(f"  Total workflows: {registry.summary()['total']}")
    print(f"  Run dashboard: streamlit run agentic_maintenance/dashboard/app.py")
    print(f"{'='*70}{RESET}\n")


if __name__ == "__main__":
    main()
