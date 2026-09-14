"""
Mock LLM — provides realistic offline reasoning responses without external API calls.
Used when system.offline_mode=true in config.yaml.
"""
from __future__ import annotations

import time
from typing import Any

_MOCK_RESPONSES: dict[str, str] = {
    "bearing_vibration_anomaly": (
        "ANALYSIS: Equipment P-101 (Crude Oil Centrifugal Pump) is exhibiting a classic "
        "bearing defect pattern. The NDE bearing vibration has progressed from 2.4 mm/s to "
        "8.4 mm/s over 18 hours — a 3.5× increase indicating accelerated bearing wear. "
        "Co-rising bearing temperature to 94°C (ISO 10816 Zone C boundary) confirms lubricant "
        "film degradation. The asymmetric rise on NDE only (DE stable at 2.5 mm/s) points to "
        "a single bearing defect rather than misalignment. "
        "PROGNOSIS: Based on vibration trend rate, bearing failure is predicted within 48 hours. "
        "RECOMMENDATION: Schedule immediate bearing replacement using pump standby (P-101A). "
        "Priority: URGENT. Parts required: SKF-6315-C3, SKF-6316-C3."
    ),
    "reactor_fouling": (
        "ANALYSIS: R-301 differential pressure has increased 58% above baseline to 1.38 bar. "
        "Combined with declining outlet temperature (315→309°C), this is a definitive indicator "
        "of progressive catalyst fouling — likely coke deposition or sulfur poisoning. "
        "The bed temperature profile remains stable, ruling out hot spots or channeling. "
        "PROGNOSIS: At current fouling rate, maximum allowable DP (1.70 bar) will be reached in "
        "approximately 14 days, forcing unplanned shutdown. "
        "RECOMMENDATION: Plan catalyst regeneration in next scheduled turnaround window (within 14 days). "
        "Increase monitoring frequency to 4-hour intervals. Consider feed rate reduction by 10%."
    ),
    "heat_exchanger_tube_leak": (
        "ANALYSIS: E-401 exhibits classic tube leak symptoms: shell-side temperature drop "
        "(385→362°C outlet) combined with tube-side outlet temperature rising above expected "
        "cross-temperature limit. Shell-side pressure drop increased 0.8 bar above baseline. "
        "The cross-temperature violation indicates direct fluid mixing through a tube perforation. "
        "This allows cold tube-side naphtha feed to bypass the heat exchanger, impacting reactor "
        "inlet temperature stability. "
        "PROGNOSIS: Progressive tube failure likely. Risk of escalation to multi-tube failure "
        "within 4 days if not addressed. "
        "RECOMMENDATION: Immediate online tube plugging of up to 10% tube count. "
        "Full bundle replacement required in next planned shutdown."
    ),
    "compressor_valve_failure": (
        "ANALYSIS: K-201 Stage-1 discharge temperature has risen 28°C above baseline to 128°C. "
        "Compressor efficiency has dropped from 0.82 to 0.71 (13.4% reduction). "
        "Valve temperature sensor on Stage-1 shows asymmetric heating pattern consistent with "
        "a partially failed discharge valve — valve not fully closing, causing hot gas recirculation. "
        "The discharge pressure decline from 42.1 to 41.0 bar confirms capacity reduction. "
        "PROGNOSIS: Complete valve failure expected within 24 hours. Continued operation risks "
        "compressor trip, potential gas release, and fire hazard. "
        "RECOMMENDATION: De-rate to 70% capacity immediately. Schedule valve replacement in 16 hours. "
        "Transfer load to K-202 wet gas compressor."
    ),
    "safety_valve_overdue": (
        "ANALYSIS: PSV-501 (Reactor Overhead Pressure Safety Valve) is 7 days past its mandatory "
        "annual inspection deadline per API 510 and OSHA 1910.119 (Process Safety Management). "
        "The valve serves as the final overpressure protection layer for R-301 operating at 75 bar. "
        "The operating pressure (78.5 bar) is within normal range; however, valve functionality "
        "cannot be assured without inspection. "
        "REGULATORY STATUS: Non-compliant. Subject to regulatory penalty and potential forced "
        "plant shutdown if discovered during an OSHA inspection. "
        "RECOMMENDATION: Immediate isolation of PSV-501 and replacement with spare "
        "(PSV-501-SPARE in inventory). Full inspection and test within 24 hours. "
        "Submit regulatory notification to AHJ within 48 hours."
    ),
    "cui_risk": (
        "ANALYSIS: Risk-based inspection model has flagged T-601 (Crude Atmospheric Distillation "
        "Column) for Corrosion Under Insulation (CUI) risk assessment. Operating temperature "
        "range of 115-355°C places shell zones A4–A7 in the highest CUI risk band. "
        "Last CUI survey was 756 days ago — 26 days past the 730-day inspection interval. "
        "Risk score of 0.78 (high) is driven by insulation age (15+ years), previous corrosion "
        "findings, and cyclic temperature operation. "
        "CONSEQUENCE: Undetected CUI can cause wall thinning leading to catastrophic brittle "
        "fracture or flammable hydrocarbon release — a Tier-1 process safety event. "
        "RECOMMENDATION: Schedule pulsed eddy current / radiography CUI survey immediately. "
        "Plan 3-day offline inspection during next maintenance window."
    ),
    "generic": (
        "ANALYSIS: Sensor data review indicates anomalous operating conditions on the monitored "
        "equipment. Parameter deviations exceed normal operating envelope thresholds. "
        "RECOMMENDATION: Initiate diagnostic inspection. Review maintenance history and "
        "failure mode analysis. Escalate to senior engineer if deviation continues."
    ),
}


class MockLLM:
    """Simulates LLM responses for offline demonstration mode."""

    def __init__(self, model: str = "mock-gpt4o") -> None:
        self.model = model
        self.total_tokens = 0
        self.total_calls = 0

    def generate(self, prompt: str, scenario: str = "generic", delay: float = 0.8) -> str:
        """Generate a mock LLM response for the given scenario."""
        time.sleep(delay)  # Simulate API latency
        response = _MOCK_RESPONSES.get(scenario, _MOCK_RESPONSES["generic"])
        self.total_tokens += len(prompt.split()) + len(response.split())
        self.total_calls += 1
        return response

    def get_usage_stats(self) -> dict:
        return {
            "model": self.model,
            "total_calls": self.total_calls,
            "total_tokens_approx": self.total_tokens,
            "estimated_cost_usd": round(self.total_tokens * 0.000015, 4),  # mock pricing
        }


def get_llm(offline_mode: bool = True) -> Any:
    """Return appropriate LLM client based on offline mode setting."""
    if offline_mode:
        return MockLLM()
    try:
        from openai import OpenAI  # type: ignore
        import os
        return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    except ImportError:
        return MockLLM()
