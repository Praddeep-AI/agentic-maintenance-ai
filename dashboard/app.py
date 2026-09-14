"""
Agentic Maintenance AI — Interactive Executive Dashboard v3.0
Run: streamlit run agentic_maintenance/dashboard/app.py
"""
from __future__ import annotations
import sys, pathlib

# Works on local (playground root 3 levels up) AND Streamlit Cloud (repo root 2 levels up)
_here = pathlib.Path(__file__).resolve()
for _p in [_here.parent.parent, _here.parent.parent.parent]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import time
from datetime import datetime

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from agentic_maintenance.workflow.state_machine import registry, WorkflowState
from agentic_maintenance.roi.roi_engine import (
    calculate_cumulative_roi, get_monthly_roi_trend,
    get_mtbf_by_equipment, get_all_historical_incidents,
    calculate_incident_roi,
)
from agentic_maintenance.enterprise_systems.scada_simulator import get_sensor_data
from agentic_maintenance.enterprise_systems.cmms_simulator import get_all_work_orders
from agentic_maintenance.enterprise_systems.hse_simulator import get_overdue_inspections, get_inspection_schedule
from agentic_maintenance.tools.notification_tools import get_notification_log

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agentic Maintenance AI",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── colour tokens ─────────────────────────────────────────────────────────────
BG      = "#07101f"
CARD    = "#0d1a2e"
BORDER  = "#1c3352"
TXT     = "#e2eaf6"
MUTED   = "#7d9bbf"
BLUE    = "#0f62fe"
GREEN   = "#24a148"
AMBER   = "#f1c21b"
RED     = "#da1e28"
ORANGE  = "#ff832b"
PURPLE  = "#8a3ffc"

# ── chart base ────────────────────────────────────────────────────────────────
_CL = dict(
    paper_bgcolor=BG, plot_bgcolor=CARD,
    font=dict(color=TXT, family="IBM Plex Sans, sans-serif", size=11),
    xaxis=dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False),
    yaxis=dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False),
    margin=dict(t=32, b=32, l=8, r=8),
)
def _cl(**kw):
    d = dict(_CL); d.update(kw); return d

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
.stApp{background:#07101f;}
/* push content below Streamlit Cloud toolbar (44px) */
.block-container{padding-top:3.2rem !important;padding-bottom:.5rem;}
[data-testid="stToolbar"]{display:none !important;}
[data-testid="stDecoration"]{display:none !important;}
[data-testid="stStatusWidget"]{visibility:visible !important;}

/* ── KPI strip ── */
.krow{display:flex;gap:10px;margin-bottom:4px;}
.kcard{
  flex:1;background:linear-gradient(140deg,#0d1a2e 0%,#102040 100%);
  border:1px solid #1c3352;border-radius:10px;padding:13px 15px;
  border-left:3px solid #0f62fe;position:relative;overflow:hidden;
  cursor:pointer;
}
.kcard[data-tab]:hover{transform:translateY(-2px);}
.kcard:hover{border-color:#3b7de8;box-shadow:0 0 16px rgba(15,98,254,.18);}
.kcard.g{border-left-color:#24a148;}
.kcard.a{border-left-color:#f1c21b;}
.kcard.r{border-left-color:#da1e28;}
.kcard.p{border-left-color:#8a3ffc;}
.kcard.b{border-left-color:#0f62fe;}
.kv{font-size:1.25rem;font-weight:700;color:#e2eaf6;line-height:1.15;letter-spacing:-.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.kl{font-size:.62rem;color:#7d9bbf;text-transform:uppercase;letter-spacing:1.4px;margin-top:3px;}
.kd{font-size:.72rem;margin-top:5px;}
.kd.pos{color:#24a148;} .kd.neg{color:#da1e28;} .kd.neu{color:#7d9bbf;}
.ktt{display:none;position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);
  background:#05090f;border:1px solid #1c3352;border-radius:6px;padding:7px 10px;
  font-size:.68rem;color:#b8cfe8;width:180px;z-index:99;white-space:normal;line-height:1.5;}
.kcard:hover .ktt{display:block;}

/* ── Equipment tiles ── */
.eqgrid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:10px 0;}
.eqtile{
  background:#0d1a2e;border:1px solid #1c3352;border-radius:10px;
  padding:13px 10px;text-align:center;cursor:default;position:relative;
  transition:transform .15s,box-shadow .15s;
}
.eqtile:hover{transform:translateY(-3px);box-shadow:0 6px 20px rgba(0,0,0,.4);}
.eqtile.r{border-top:3px solid #da1e28;}
.eqtile.a{border-top:3px solid #f1c21b;}
.eqtile.g{border-top:3px solid #24a148;}
.eqdot{width:14px;height:14px;border-radius:50%;margin:0 auto 6px;}
.eqdot.r{background:#da1e28;box-shadow:0 0 8px #da1e28;}
.eqdot.a{background:#f1c21b;box-shadow:0 0 8px #f1c21b;}
.eqdot.g{background:#24a148;box-shadow:0 0 8px #24a148;}
.eqid{font-size:1rem;font-weight:700;color:#e2eaf6;}
.eqname{font-size:.65rem;color:#7d9bbf;margin-top:2px;}
.eqstat{font-size:.65rem;font-weight:700;letter-spacing:.5px;margin-top:4px;}
.eqstat.r{color:#da1e28;} .eqstat.a{color:#f1c21b;} .eqstat.g{color:#24a148;}
.eqmsg{font-size:.63rem;color:#7d9bbf;margin-top:4px;font-family:'IBM Plex Mono',monospace;}
/* tooltip */
.eqtt{display:none;position:absolute;bottom:calc(100%+6px);left:50%;transform:translateX(-50%);
  background:#05090f;border:1px solid #1c3352;border-radius:6px;padding:8px 10px;
  font-size:.65rem;color:#b8cfe8;width:190px;z-index:99;text-align:left;line-height:1.5;}
.eqtile:hover .eqtt{display:block;}

/* ── Section header ── */
.shdr{font-size:.62rem;font-weight:700;letter-spacing:2.2px;text-transform:uppercase;
  color:#0f62fe;border-bottom:1px solid #1c3352;padding-bottom:5px;margin:10px 0 12px;}

/* ── Agent cards ── */
.agcard{background:#080f1d;border:1px solid #142030;border-radius:8px;
  padding:11px 14px;margin:5px 0;}
.agname{color:#4d94ff;font-weight:600;font-size:.78rem;font-family:'IBM Plex Mono',monospace;}
.agdec{color:#6ee7b7;margin-top:3px;font-size:.74rem;font-family:'IBM Plex Mono',monospace;}
.agrsn{color:#7d9bbf;margin-top:2px;font-size:.67rem;}

/* ── Alert badges ── */
.bc{background:#da1e28;color:#fff;padding:1px 7px;border-radius:3px;font-size:.62rem;font-weight:700;}
.bh{background:#ff832b;color:#fff;padding:1px 7px;border-radius:3px;font-size:.62rem;font-weight:700;}
.bm{background:#f1c21b;color:#000;padding:1px 7px;border-radius:3px;font-size:.62rem;font-weight:700;}
.bl{background:#24a148;color:#fff;padding:1px 7px;border-radius:3px;font-size:.62rem;font-weight:700;}

/* ── Log box ── */
.logbox{background:#04080f;border:1px solid #1c3352;border-radius:6px;padding:10px;
  max-height:240px;overflow-y:auto;font-family:'IBM Plex Mono',monospace;
  font-size:.68rem;color:#4ade80;line-height:1.6;}

/* ── Table row highlight ── */
.hrow{background:#0a1828;border:1px solid #1c3352;border-radius:6px;
  padding:8px 12px;margin:3px 0;font-size:.76rem;display:flex;
  align-items:center;gap:10px;}

/* ── Info tooltip icon ── */
.tip{display:inline-block;width:14px;height:14px;border-radius:50%;
  background:#1c3352;color:#7d9bbf;font-size:.6rem;text-align:center;
  line-height:14px;cursor:help;position:relative;margin-left:4px;}
.tip:hover::after{content:attr(data-tip);position:absolute;bottom:18px;left:50%;
  transform:translateX(-50%);background:#05090f;border:1px solid #1c3352;
  border-radius:6px;padding:6px 9px;font-size:.65rem;color:#b8cfe8;
  width:200px;white-space:normal;line-height:1.5;z-index:100;font-family:'IBM Plex Sans',sans-serif;}

/* ── Global dark background (belt-and-braces for Streamlit 1.63) ── */
[data-testid="stAppViewContainer"]{background:#07101f !important;}
[data-testid="stHeader"]{background:#07101f !important;}
.stApp,.main,.block-container{background:#07101f !important;}

/* ── All widget text — global dark theme fallback ── */
.stMarkdown p,.stMarkdown li,.stMarkdown h1,.stMarkdown h2,.stMarkdown h3,
.stMarkdown h4{color:#e2eaf6;}
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] label,
div[class*="stRadio"] label > div > p,
div[class*="stCheckbox"] label > div > p,
div[class*="stToggle"] label > div > p,
div[class*="stSelectbox"] label > div > p,
div[class*="stSlider"] label > div > p{color:#b8cfe8 !important;font-size:.78rem !important;}

/* ── Sidebar container ── */
[data-testid="stSidebar"]{background:#050d1a !important;border-right:1px solid #1c3352;}
/* Nuclear option: every text node in sidebar gets light colour */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label{color:#b8cfe8 !important;}
/* Slightly brighter for interactive widget labels */
[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] label{color:#7d9bbf !important;font-size:.74rem !important;letter-spacing:.3px;}
/* Radio option text (APPROVED / REJECTED) */
[data-testid="stSidebar"] div[data-testid="stRadio"] label > div > p,
[data-testid="stSidebar"] div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] p{color:#e2eaf6 !important;font-size:.8rem !important;font-weight:500;}
/* Checkbox text (Show pipeline trace) */
[data-testid="stSidebar"] div[data-testid="stCheckbox"] label > div > p,
[data-testid="stSidebar"] div[data-testid="stCheckbox"] p{color:#c8dff4 !important;font-size:.78rem !important;}
/* Toggle text */
[data-testid="stSidebar"] div[data-testid="stToggle"] label > div > p{color:#c8dff4 !important;font-size:.78rem !important;}
/* Bold section headers (markdown **text**) */
[data-testid="stSidebar"] strong{color:#e2eaf6 !important;font-size:.82rem !important;}
/* Selectbox displayed value */
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="select"] span{color:#e2eaf6 !important;}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div{
  background:#0d1a2e !important;border:1px solid #1c3352 !important;}
/* Slider value bubble */
[data-testid="stSidebar"] div[data-testid="stSlider"] div[class*="valueContainer"] p,
[data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stTickBarMax"]{color:#7d9bbf !important;}
/* Caption / timestamp line */
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p{color:#4a6a8a !important;font-size:.68rem !important;}
/* Divider */
[data-testid="stSidebar"] hr{border-color:#1c3352 !important;}
/* Button */
[data-testid="stSidebar"] .stButton > button{
  background:#0f62fe !important;color:#ffffff !important;border:none;border-radius:6px;
  font-weight:600;font-size:.78rem;letter-spacing:.3px;transition:background .15s;width:100%;}
[data-testid="stSidebar"] .stButton > button:hover{background:#0353e9 !important;}

/* ── Metric overrides ── */
[data-testid="stMetricValue"]>div{font-size:1.3rem !important;color:#e2eaf6 !important;}
[data-testid="stMetricLabel"]>div{color:#7d9bbf !important;font-size:.68rem !important;}
[data-testid="stMetricDelta"]>div{font-size:.72rem !important;}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"]{font-size:.78rem !important;color:#7d9bbf !important;padding:6px 14px;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{color:#0f62fe !important;font-weight:700;}
[data-testid="stTabs"] [role="tablist"]{border-bottom:1px solid #1c3352;}

/* ── Form inputs ── */
.stSlider [data-testid="stTickBar"]{display:none;}
.stNumberInput input,.stTextInput input{
  background:#0d1a2e !important;border:1px solid #1c3352 !important;
  color:#e2eaf6 !important;border-radius:6px !important;font-size:.82rem !important;}
.stSelectbox [data-baseweb="select"] .css-1hyfx7x{color:#e2eaf6 !important;}

/* ── Dataframe ── */
[data-testid="stDataFrame"]{border:1px solid #1c3352;border-radius:8px;}
</style>
""", unsafe_allow_html=True)

# ── equipment + scenario data ─────────────────────────────────────────────────
_EQ = {
    "P-101":  {"t":"PUMP",                "n":"Crude Oil Pump",        "s":"r","msg":"Bearing Vibration", "tip":"NDE bearing at 8.4 mm/s — ISO 10816 Zone D exceeded. TTF: 48 h. Action required."},
    "K-201":  {"t":"COMPRESSOR",          "n":"HP Gas Compressor",     "s":"r","msg":"Valve Failure",     "tip":"Discharge temp +28°C, efficiency 0.71 (−13%). Stage-1 discharge valve failure imminent."},
    "E-401":  {"t":"HEAT_EXCHANGER",      "n":"Naphtha HX",            "s":"a","msg":"Tube Leak",         "tip":"Tube-side outlet 374°C — exceeds design cross temp. Shell ΔP +24%. Tube bundle leak suspected."},
    "PSV-501":{"t":"SAFETY_VALVE",        "n":"Reactor PSV",           "s":"a","msg":"Insp. Overdue",    "tip":"Annual inspection 7 days overdue. OSHA 1910.119 & API 510 non-compliance. AHJ notification mandatory."},
    "R-301":  {"t":"REACTOR",             "n":"Hydrotreater Reactor",  "s":"a","msg":"Catalyst Fouling", "tip":"ΔP across catalyst bed +58% above baseline. Conversion efficiency declining. Regeneration required."},
    "T-601":  {"t":"DISTILLATION_COLUMN", "n":"Crude Distill. Column", "s":"a","msg":"CUI Risk HIGH",    "tip":"CUI inspection overdue 26 days. Risk score 0.78 (HIGH). API 581 RBI required on zones A4–A7."},
    "P-102":  {"t":"PUMP",                "n":"Diesel Transfer Pump",  "s":"g","msg":"Normal",            "tip":"All parameters within normal operating range. Last PM: 12 days ago. Next PM in 18 days."},
    "P-103":  {"t":"PUMP",                "n":"Condensate Pump",       "s":"g","msg":"Normal",            "tip":"Operating normally. Vibration: 1.2 mm/s. Bearing temp: 65°C. No anomalies detected."},
    "K-202":  {"t":"COMPRESSOR",          "n":"LP Gas Compressor",     "s":"g","msg":"Normal",            "tip":"Efficiency: 0.87. Discharge temp nominal. All sensors green. PM compliance: 100%."},
    "E-402":  {"t":"HEAT_EXCHANGER",      "n":"Vacuum HX",             "s":"g","msg":"Normal",            "tip":"Heat transfer coefficient nominal. No fouling detected. Shell ΔP within design limits."},
}
_SLBL  = {"r":"CRITICAL","a":"WARNING","g":"NORMAL"}
_SC = {
    "bearing_vibration_anomaly": ("P-101",  "NDE bearing 8.4 mm/s — ISO 10816 Zone D exceeded"),
    "reactor_fouling":           ("R-301",  "ΔP +58% baseline — catalyst fouling suspected"),
    "heat_exchanger_tube_leak":  ("E-401",  "Tube-side outlet 374°C — tube bundle leak suspected"),
    "compressor_valve_failure":  ("K-201",  "Discharge temp +28°C, efficiency 0.71 — valve failure imminent"),
    "safety_valve_overdue":      ("PSV-501","Inspection overdue 7 days — OSHA 1910.119 non-compliance"),
    "cui_risk":                  ("T-601",  "CUI inspection overdue 26 days — API 581 RBI required"),
}
_EQ2SC = {"P-101":"bearing_vibration_anomaly","K-201":"compressor_valve_failure",
           "E-401":"heat_exchanger_tube_leak","PSV-501":"safety_valve_overdue",
           "R-301":"reactor_fouling","T-601":"cui_risk"}
_THRESH = {"vibration_nde":7.1,"vibration_de":5.0,"bearing_temp_nde":90.0,
           "discharge_temp":100.0,"efficiency":0.80,"differential_pressure":1.2}

# ── session state ─────────────────────────────────────────────────────────────
for _k,_v in [("pipe_log",[]),("last_res",None),("fmea_hist",[])]:
    if _k not in st.session_state: st.session_state[_k] = _v

# ── helpers ───────────────────────────────────────────────────────────────────
def _h(tag: str) -> str:
    """Section header HTML."""
    return f'<div class="shdr">{tag}</div>'

def _tip(text: str) -> str:
    """Inline ℹ tooltip icon."""
    return f'<span class="tip" data-tip="{text}">i</span>'

def kcard(label: str, value: str, delta: str, color: str, tooltip: str, tab: int = -1) -> str:
    """KPI card with hover tooltip and optional tab-navigation click."""
    dc = "pos" if "+" in delta else "neg" if delta.startswith("-") or delta.startswith("−") else "neu"
    d_html = '<div class="kd ' + dc + '">' + delta + '</div>' if delta else ""
    tt = '<div class="ktt">📌 Click to open source data<br><br>' + tooltip + '</div>'
    nav = (' onclick="window.location.href=window.location.pathname+\'?tab=' + str(tab) + '\'"'
           ' data-tab="' + str(tab) + '" title="Click to view source data"'
           if tab >= 0 else "")
    arrow = ('<div style="position:absolute;top:8px;right:10px;font-size:.6rem;color:#3b7de8">↗</div>'
             if tab >= 0 else "")
    return ('<div class="kcard ' + color + '"' + nav + '>'
            + arrow + tt
            + '<div class="kv">' + value + '</div>'
            + '<div class="kl">' + label + '</div>'
            + d_html + '</div>')

def eqtile(eid: str, meta: dict) -> str:
    """Equipment health tile with hover tooltip."""
    s = meta["s"]
    return (
        '<div class="eqtile ' + s + '">'
        + '<div class="eqtt">'
        + '<b style="color:#e2eaf6">' + eid + '</b> — ' + meta["n"] + '<br>'
        + '<span style="color:#f1c21b">' + _SLBL[s] + '</span><br><br>'
        + meta["tip"]
        + '</div>'
        + '<div class="eqdot ' + s + '"></div>'
        + '<div class="eqid">' + eid + '</div>'
        + '<div class="eqname">' + meta["n"] + '</div>'
        + '<div class="eqstat ' + s + '">' + _SLBL[s] + '</div>'
        + '<div class="eqmsg">' + meta["msg"] + '</div>'
        + '</div>'
    )

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<svg xmlns="http://www.w3.org/2000/svg" width="68" height="26" viewBox="0 0 72 28">'
        '<path fill="#0f62fe" d="M0 0h8v28H0zm10 0h8v28h-8zm10 3h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8z'
        'M30 0h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8zM40 0h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8z'
        'm0 7h8v4h-8zM50 3h22v4H50zm0 7h22v4H50zm0 7h22v4H50z"/></svg>',
        unsafe_allow_html=True,
    )
    st.markdown("**⚙️ Agentic Maintenance AI**")
    st.caption("Chemicals & Petrochemicals | IBM Consulting")
    st.divider()

    cr1, cr2 = st.columns([3, 2])
    auto_ref = cr1.toggle("Auto-refresh", value=False, help="Reload the dashboard on an interval")
    ref_int  = cr2.selectbox("", [10, 30, 60], label_visibility="collapsed",
                             help="Refresh interval in seconds")
    if st.button("↻ Refresh", use_container_width=True):
        st.rerun()

    st.divider()
    st.markdown("**🚀 Run Agentic Pipeline**",
                help="Selects a fault scenario, triggers all AI agents, and logs results")
    run_sc = st.selectbox(
        "Scenario", ["— select —"] + list(_SC.keys()),
        format_func=lambda x: x.replace("_"," ").title() if x != "— select —" else x,
        help="Choose an industrial fault scenario to run the full 18-stage agentic pipeline",
    )
    dec = st.radio("Approval", ["APPROVED","REJECTED"], horizontal=True,
                   help="Pre-fill the human supervisor approval decision")
    show_trace = st.checkbox("Show pipeline trace", value=True,
                             help="Display the live step-by-step log after pipeline completes")
    run_btn = st.button("▶ Run Pipeline", type="primary", use_container_width=True)

    st.divider()
    st.markdown("**🔬 Sensor Monitor**")
    sel_eq   = st.selectbox("Equipment", list(_EQ.keys()),
                             help="Select equipment to drill into live SCADA sensor data")
    s_hours  = st.slider("Window (h)", 6, 72, 24,
                         help="Sensor history window in hours (6–72 h)")
    inj_ano  = st.checkbox("Inject anomaly", value=False,
                            help="Overlay fault progression signal onto the sensor trace")

    st.divider()
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("LLM → Agent → Tools → Enterprise → Workflow → Human → Action")

# ── auto-refresh ──────────────────────────────────────────────────────────────
if auto_ref:
    time.sleep(ref_int)
    st.rerun()

# ── pipeline runner ───────────────────────────────────────────────────────────
if run_btn and run_sc != "— select —":
    eq_id, alert_txt = _SC[run_sc]
    log_lines: list[str] = []

    def _pcb(step: str, msg: str) -> None:
        log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}]  {step:<28s}  {msg}")

    with st.spinner(f"🤖 Pipeline running — **{run_sc.replace('_',' ').title()}** …"):
        try:
            from agentic_maintenance.agents.orchestrator import MaintenanceOrchestrator
            orch = MaintenanceOrchestrator(offline_mode=True, progress_callback=_pcb)
            res  = orch.run_pipeline(eq_id, alert_txt, run_sc,
                                     auto_approve=True, prefill_decision=dec)
            st.session_state.pipe_log = log_lines
            st.session_state.last_res = res
        except Exception as exc:
            st.error(f"Pipeline error: {exc}")

    lr = st.session_state.last_res
    if lr:
        roi_r = lr.get("roi", {})
        pc1,pc2,pc3,pc4 = st.columns(4)
        pc1.success(f"✅ {lr.get('outcome','—')}")
        pc2.metric("Net Savings",  f"${roi_r.get('net_savings_usd',0):,.0f}",
                   help="Avoided downtime cost minus planned maintenance cost")
        pc3.metric("ROI",          f"{roi_r.get('roi_pct',0):.1f}%",
                   help="(Net Savings / Maintenance Cost) × 100")
        pc4.metric("Final State",  lr.get("final_state","—"))
        if show_trace and log_lines:
            with st.expander("🔍 Live Pipeline Trace", expanded=True):
                lines_html = "<br>".join(
                    '<span style="color:#4d94ff">' + l.split("]")[0] + "]</span>"
                    + (l.split("]",1)[1] if "]" in l else "")
                    for l in log_lines
                )
                st.markdown('<div class="logbox">' + lines_html + '</div>',
                            unsafe_allow_html=True)

# ── load data ─────────────────────────────────────────────────────────────────
roi_s   = calculate_cumulative_roi()
m_trend = get_monthly_roi_trend()
mtbf_d  = get_mtbf_by_equipment()
ov_insp = get_overdue_inspections()
wf_sum  = registry.summary()
all_wf  = registry.get_all()
notifs  = get_notification_log(limit=30)
h_inc   = get_all_historical_incidents()
summ    = roi_s["summary"]
kpis    = roi_s["kpis"]

# ── page header ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:12px;margin-bottom:2px">'
    '<span style="font-size:1.7rem">⚙️</span>'
    '<div><div style="font-size:1.4rem;font-weight:700;color:#e2eaf6;line-height:1.2">'
    'Agentic Maintenance AI — Command Centre</div>'
    '<div style="font-size:.72rem;color:#7d9bbf;margin-top:1px">'
    'Chemicals &amp; Petrochemicals | Critical Asset Management | IBM Consulting</div>'
    '</div></div>',
    unsafe_allow_html=True,
)
st.divider()

# ── KPI strip ─────────────────────────────────────────────────────────────────
n_sav  = summ["total_net_savings_usd"]
n_roi  = summ["cumulative_roi_pct"]
n_down = summ["total_avoided_downtime_cost_usd"]
n_act  = wf_sum["active"]
n_pend = wf_sum["pending_approval"]
n_over = len(ov_insp)
n_ftf  = kpis["first_time_fix_rate_pct"]
n_wrench = kpis["wrench_time_improvement_pct"]

_roi_disp = (f"{n_roi:.0f}%" if n_roi < 10000 else ">10,000%")
# Tab indices: 0=Equipment Health, 1=Sensor Feed, 2=AI Activity, 3=Financial Impact, 4=FMEA, 5=ROI What-If, 6=Compliance
kpi_row = "".join([
    kcard("Net Savings (12M)", f"${n_sav/1e6:.1f}M",  "+22% YoY", "g",
          "Total net savings = Avoided downtime cost minus planned maintenance cost across all AI-assisted incidents in the last 12 months.", tab=3),
    kcard("Cumulative ROI",    _roi_disp,               "vs $250K AI system", "b",
          "ROI = (Total Net Savings / AI System Annual Cost) x 100. AI system annual cost: $250,000.", tab=5),
    kcard("Avoided Downtime",  f"${n_down/1e6:.1f}M",  "+18% vs baseline", "g",
          "Downtime hours avoided x $85,000/hr production rate x 22% product margin.", tab=3),
    kcard("Active Workflows",  str(n_act),             "", "b",
          "Workflows currently in progress — from ALERT_DETECTED to ROI_CALCULATED.", tab=0),
    kcard("Pending Approval",  str(n_pend),            "Requires action" if n_pend > 0 else "All clear",
          "a" if n_pend > 0 else "b",
          "Work orders awaiting supervisor APPROVED/REJECTED decision before scheduling.", tab=2),
    kcard("Overdue Inspections", str(n_over),          f"\u2212{n_over} compliance items" if n_over else "All current",
          "r" if n_over else "g",
          "Regulatory inspections past their due date. Non-compliance triggers OSHA/API/ASME notification requirements.", tab=6),
    kcard("First-Time Fix Rate", f"{n_ftf:.1f}%",      "+15% vs baseline", "g",
          "% of work orders completed without a repeat call-back within 30 days. AI-predicted maintenance achieves 88% vs 72% reactive.", tab=4),
    kcard("Wrench Time \u2191",    f"{n_wrench:.1f}%",      "vs reactive baseline", "p",
          "Improvement in hands-on productive maintenance time vs planning/travel overhead. AI reduces planning from ~5h to ~1.5h per job.", tab=5),
])
st.markdown('<div class="krow">' + kpi_row + '</div>', unsafe_allow_html=True)
st.divider()

# ── auto-select tab from ?tab=N query param ───────────────────────────────────
_tab_idx = 0
try:
    _qp = st.query_params.get("tab", "0")
    _tab_idx = int(_qp) if str(_qp).isdigit() else 0
except Exception:
    _tab_idx = 0
if _tab_idx > 0:
    st.markdown(
        "<script>"
        "(function(){"
        "function _go(){"
        "var t=document.querySelectorAll('[data-testid=stTabs] [role=tab]');"
        "if(t.length>" + str(_tab_idx) + "){t[" + str(_tab_idx) + "].click();}"
        "else{setTimeout(_go,250);}}"
        "setTimeout(_go,500);"
        "})();"
        "</script>",
        unsafe_allow_html=True,
    )

# ── tabs ──────────────────────────────────────────────────────────────────────
T1,T2,T3,T4,T5,T6,T7 = st.tabs([
    "🏭 Equipment Health",
    "📡 Live Sensor Feed",
    "🤖 AI Activity",
    "💰 Financial Impact",
    "🧮 FMEA Calculator",
    "💡 ROI What-If",
    "🛡️ Compliance",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EQUIPMENT HEALTH
# ══════════════════════════════════════════════════════════════════════════════
with T1:
    st.markdown(_h("Plant Equipment Health Map — Hover any tile for details"), unsafe_allow_html=True)

    tiles_html = "".join(eqtile(eid, m) for eid, m in _EQ.items())
    st.markdown('<div class="eqgrid">' + tiles_html + '</div>', unsafe_allow_html=True)

    st.divider()
    c_wf, c_sev = st.columns([3, 1])

    with c_wf:
        st.markdown(_h("Active Workflow Pipeline") +
                    _tip("Each row is one agentic pipeline run. States progress from ALERT_DETECTED to ROI_CALCULATED."),
                    unsafe_allow_html=True)
        wf_list = all_wf[-15:] if all_wf else []
        if wf_list:
            rows = []
            for wf in reversed(wf_list):
                rows.append({
                    "Workflow ID":  wf.workflow_id[-14:],
                    "Equipment":    wf.equipment_id,
                    "Scenario":     (wf.scenario or "N/A").replace("_"," "),
                    "State":        wf.state.value,
                    "Work Order":   wf.work_order_id or "—",
                    "Started":      wf.created_at.strftime("%H:%M:%S") if wf.created_at else "—",
                })
            df_wf = pd.DataFrame(rows)
            _ss = {
                "ROI_CALCULATED":        "background:#052e12;color:#4ade80",
                "EXECUTED":              "background:#062041;color:#93c5fd",
                "PENDING_HUMAN_APPROVAL":"background:#1c1000;color:#fde68a",
                "ALERT_DETECTED":        "background:#1c0404;color:#fca5a5",
                "REJECTED":              "background:#1c0000;color:#ef4444",
                "APPROVED":              "background:#0d2410;color:#6ee7b7",
                "CLOSED":                "background:#082030;color:#60a5fa",
            }
            st.dataframe(df_wf.style.map(lambda v: _ss.get(v, ""), subset=["State"]),
                         use_container_width=True, height=260)
        else:
            st.info("No workflows yet — pick a scenario in the sidebar and click ▶ Run Pipeline")

    with c_sev:
        st.markdown(_h("Alert Severity"), unsafe_allow_html=True)
        fig_sev = go.Figure(go.Pie(
            labels=["CRITICAL","HIGH","MEDIUM","LOW"],
            values=[2,2,3,3], hole=0.56,
            marker=dict(colors=[RED,ORANGE,AMBER,GREEN]),
            textfont=dict(size=10,color=TXT),
            hovertemplate="<b>%{label}</b><br>%{value} alerts<extra></extra>",
        ))
        fig_sev.update_layout(**_cl(height=200, margin=dict(t=8,b=8,l=8,r=8), showlegend=True,
                                    legend=dict(orientation="v",font=dict(size=9),x=1,y=0.5)))
        st.plotly_chart(fig_sev, use_container_width=True)

        st.markdown(_h("Live Alerts"), unsafe_allow_html=True)
        for eid,m in _EQ.items():
            if m["s"] in ("r","a"):
                badge = '<span class="bc">CRITICAL</span>' if m["s"]=="r" else '<span class="bh">WARNING</span>'
                st.markdown(
                    f'<div style="margin:4px 0;font-size:.74rem;line-height:1.5">{badge} '
                    f'<b style="color:#e2eaf6">{eid}</b>'
                    f'<span style="color:#7d9bbf"> — {m["msg"]}</span></div>',
                    unsafe_allow_html=True,
                )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LIVE SENSOR FEED
# ══════════════════════════════════════════════════════════════════════════════
with T2:
    eq_meta = _EQ[sel_eq]
    sc_key  = _EQ2SC.get(sel_eq) if inj_ano else None
    raw     = get_sensor_data(sel_eq, time_range_hours=s_hours, inject_anomaly_scenario=sc_key)
    chs     = raw.get("channels", {})
    latest  = raw.get("latest", {})
    n_s     = raw.get("n_samples", 0)

    hdr_color = RED if inj_ano and sc_key else GREEN
    hdr_msg   = (f"⚠️ ANOMALY INJECTED — {sc_key} — fault progression simulated on {sel_eq}"
                 if inj_ano and sc_key
                 else f"✅ {sel_eq} — {eq_meta['n']} — {n_s} samples / {s_hours} h — {_SLBL[eq_meta['s']]}")
    st.markdown(
        f'<div style="background:{hdr_color}18;border:1px solid {hdr_color}44;'
        f'border-radius:8px;padding:9px 14px;font-size:.8rem;color:{hdr_color};margin-bottom:12px">'
        + hdr_msg + '</div>',
        unsafe_allow_html=True,
    )

    # Latest reading metrics with help tooltips
    if latest:
        mc = st.columns(min(len(latest), 7))
        for i,(ch,val) in enumerate(list(latest.items())[:7]):
            thr = _THRESH.get(ch)
            delta_txt = f"⚠ above threshold {thr}" if thr and val > thr else "within range"
            delta_col = "inverse" if thr and val > thr else "normal"
            mc[i].metric(
                ch.replace("_"," ").title(),
                f"{val:.2f}",
                delta=delta_txt,
                delta_color=delta_col,
                help=f"Channel: {ch} | Alert threshold: {thr if thr else 'N/A'} | Latest reading: {val:.3f}",
            )
    st.divider()

    st.markdown(_h("Sensor Channel Traces — alert thresholds shown as dashed lines"), unsafe_allow_html=True)
    ch_names = list(chs.keys())
    for row_s in range(0, len(ch_names), 2):
        pair  = ch_names[row_s:row_s+2]
        pcols = st.columns(len(pair))
        for pi,ch in enumerate(pair):
            vals = chs[ch]
            thr  = _THRESH.get(ch)
            is_alarm = inj_ano and thr and vals[-1] > thr
            lc = RED if is_alarm else BLUE
            ac = "rgba(218,30,40,.12)" if is_alarm else "rgba(15,98,254,.09)"

            fig_ch = go.Figure(go.Scatter(
                x=list(range(len(vals))), y=vals,
                mode="lines",
                line=dict(color=lc, width=1.8),
                fill="tozeroy", fillcolor=ac,
                hovertemplate=f"Sample %{{x}}<br>{ch}: %{{y:.3f}}<extra></extra>",
            ))
            if thr:
                fig_ch.add_hline(y=thr, line_dash="dot", line_color=AMBER, line_width=1.4,
                                 annotation_text=f"Alert: {thr}",
                                 annotation_font=dict(color=AMBER,size=9))
            fig_ch.update_layout(**_cl(
                title=dict(text=ch.replace("_"," ").title(), font=dict(size=11,color=MUTED)),
                height=185, margin=dict(t=26,b=20,l=8,r=8),
            ))
            pcols[pi].plotly_chart(fig_ch, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI ACTIVITY
# ══════════════════════════════════════════════════════════════════════════════
with T3:
    l3,r3 = st.columns([3,2])

    with l3:
        st.markdown(_h("Agent Decision Log") +
                    _tip("Records every agent reasoning step across all pipeline runs. Agents: Diagnostics, Criticality, Compliance, WorkOrder, ROI."),
                    unsafe_allow_html=True)
        rows3 = []
        for wf in reversed(all_wf):
            for rec in wf.agent_reasoning:
                rows3.append({
                    "Time":     rec["timestamp"][:19],
                    "WF":       wf.workflow_id[-10:],
                    "Equip":    wf.equipment_id,
                    "Agent":    rec["agent"].replace("Agent","").replace("Assessment","").strip(),
                    "Decision": rec["decision"][:85],
                })
        if rows3:
            st.dataframe(pd.DataFrame(rows3), use_container_width=True, height=280)
            if all_wf:
                last = all_wf[-1]
                st.markdown(_h("Last Pipeline — Reasoning Chain"), unsafe_allow_html=True)
                for rec in last.agent_reasoning:
                    rsn = rec.get("reasoning","")[:100]
                    st.markdown(
                        '<div class="agcard">'
                        '<div class="agname">🤖 ' + rec["agent"] + '</div>'
                        '<div class="agdec">→ ' + rec["decision"] + '</div>'
                        + ('<div class="agrsn">' + rsn + '</div>' if rsn else '')
                        + '</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No agent activity yet — run a scenario from the sidebar ▶")

    with r3:
        tool_freq: dict[str,int] = {}
        for wf in all_wf:
            for tc in wf.tool_calls:
                tool_freq[tc["tool"]] = tool_freq.get(tc["tool"],0) + 1

        if tool_freq:
            st.markdown(_h("Tool Call Frequency") +
                        _tip("Number of times each tool was invoked across all pipeline runs. Higher = more relied upon."),
                        unsafe_allow_html=True)
            st_tools = dict(sorted(tool_freq.items(), key=lambda x: x[1]))
            fig_t = go.Figure(go.Bar(
                x=list(st_tools.values()), y=list(st_tools.keys()),
                orientation="h",
                marker=dict(color=list(st_tools.values()),
                            colorscale=[[0,"#0353e9"],[1,"#4589ff"]]),
                text=[str(v) for v in st_tools.values()],
                textposition="outside",
                textfont=dict(color=TXT,size=10),
                hovertemplate="%{y}: %{x} calls<extra></extra>",
            ))
            fig_t.update_layout(**_cl(height=280, margin=dict(l=190,t=6,b=6,r=50),
                                      xaxis=dict(title="Invocations")))
            st.plotly_chart(fig_t, use_container_width=True)
        else:
            st.info("Tool calls appear after running a scenario.")

        sc_bd = wf_sum.get("state_breakdown",{})
        if sc_bd:
            st.markdown(_h("Workflow State Distribution"), unsafe_allow_html=True)
            fig_sd = go.Figure(go.Pie(
                labels=list(sc_bd.keys()), values=list(sc_bd.values()), hole=0.52,
                marker=dict(colors=[GREEN,BLUE,AMBER,RED,PURPLE,"#06b6d4","#ec4899"]),
                textfont=dict(size=9,color=TXT),
                hovertemplate="%{label}<br>%{value} workflows<extra></extra>",
            ))
            fig_sd.update_layout(**_cl(height=210, margin=dict(t=8,b=8,l=8,r=8)))
            st.plotly_chart(fig_sd, use_container_width=True)

    st.divider()
    st.markdown(_h("Notification Dispatch Log") +
                _tip("Notifications dispatched to supervisors and maintenance teams. CRITICAL alerts also trigger SMS."),
                unsafe_allow_html=True)
    if notifs:
        df_n = pd.DataFrame([{
            "Time":      n["sent_at"][:19],
            "Urgency":   n["urgency_level"],
            "Channel":   n["channel"].upper(),
            "Recipient": n["recipient"],
            "Work Order": n.get("work_order_id","—"),
        } for n in notifs[-12:]])
        _uc = {"CRITICAL":"background:#da1e28;color:#fff","HIGH":"background:#ff832b;color:#fff",
               "MEDIUM":"background:#f1c21b;color:#000","LOW":"background:#24a148;color:#fff"}
        st.dataframe(df_n.style.map(lambda v: _uc.get(v,""), subset=["Urgency"]),
                     use_container_width=True, height=210)
    else:
        st.info("No notifications sent yet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — FINANCIAL IMPACT
# ══════════════════════════════════════════════════════════════════════════════
with T4:
    c4a,c4b = st.columns([1,2])

    with c4a:
        st.markdown(_h("ROI Meter") +
                    _tip("Cumulative ROI = (Total Net Savings / AI System Annual Cost) × 100. Target: >300%."),
                    unsafe_allow_html=True)
        gauge_val = min(summ["cumulative_roi_pct"],1500)
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=gauge_val,
            delta={"reference":300,"valueformat":".0f","suffix":"%",
                   "increasing":{"color":GREEN},"decreasing":{"color":RED}},
            title={"text":"YTD ROI vs $250K AI Cost","font":{"color":MUTED,"size":11}},
            gauge={"axis":{"range":[0,1500],"tickcolor":MUTED,"tickfont":{"color":MUTED,"size":9}},
                   "bar":{"color":BLUE,"thickness":.2},
                   "bgcolor":CARD,"bordercolor":BORDER,
                   "steps":[{"range":[0,300],"color":"#1c0000"},
                             {"range":[300,700],"color":"#1c1500"},
                             {"range":[700,1500],"color":"#001c08"}],
                   "threshold":{"line":{"color":GREEN,"width":3},"thickness":.8,"value":300}},
            number={"suffix":"%","font":{"color":TXT,"size":28}},
        ))
        fig_g.update_layout(paper_bgcolor=BG, height=270, font_color=TXT,
                            margin=dict(t=20,b=10,l=10,r=10))
        st.plotly_chart(fig_g, use_container_width=True)

        m1,m2 = st.columns(2)
        m1.metric("Avoided Downtime",   f"${summ['total_avoided_downtime_cost_usd']/1e6:.2f}M",
                  help="Sum of (downtime_hours_avoided × $85K/hr × 22% margin) for all AI-assisted incidents")
        m2.metric("Maintenance Spend",  f"${summ['total_maintenance_cost_usd']/1e6:.2f}M",
                  help="Total planned maintenance cost (labor + parts + contractor) for all incidents")
        m1.metric("Net Savings",        f"${summ['total_net_savings_usd']/1e6:.2f}M",
                  help="Avoided Downtime Cost − Total Maintenance Cost")
        m2.metric("AI System Cost",     f"${summ['ai_system_annual_cost_usd']:,.0f}",
                  help="Annual cost of the Agentic AI platform: $250,000")
        m1.metric("PM Compliance",      f"{kpis['pm_compliance_rate_pct']:.1f}%",
                  help="% of maintenance actions that were proactive (AI-predicted or scheduled) vs reactive")
        m2.metric("Wrench Time ↑",      f"{kpis['wrench_time_improvement_pct']:.1f}%",
                  help="Improvement in technician hands-on time ratio vs baseline reactive maintenance")

    with c4b:
        st.markdown(_h("12-Month Monthly Avoided Cost vs Maintenance Spend"), unsafe_allow_html=True)
        if m_trend:
            df_tr = pd.DataFrame(m_trend)
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=df_tr["month"],y=df_tr["avoided_cost"],
                                   name="Avoided Downtime Cost",marker_color=GREEN,opacity=.82,
                                   hovertemplate="%{x}<br>Avoided: $%{y:,.0f}<extra></extra>"))
            fig_m.add_trace(go.Bar(x=df_tr["month"],y=df_tr["maintenance_cost"],
                                   name="Maintenance Cost",marker_color=BLUE,opacity=.82,
                                   hovertemplate="%{x}<br>Maintenance: $%{y:,.0f}<extra></extra>"))
            fig_m.add_trace(go.Scatter(x=df_tr["month"],y=df_tr["cumulative_savings"],
                                       name="Cumulative Net Savings",mode="lines+markers",
                                       line=dict(color=AMBER,width=2.2),yaxis="y2",
                                       marker=dict(size=5),
                                       hovertemplate="%{x}<br>Cumulative: $%{y:,.0f}<extra></extra>"))
            fig_m.update_layout(**_cl(barmode="group",height=300,
                yaxis=dict(title="USD",tickprefix="$",tickformat=",.0f"),
                yaxis2=dict(title="Cumulative",overlaying="y",side="right",
                            tickprefix="$",tickformat=",.0f"),
                legend=dict(orientation="h",y=-0.24,font=dict(size=9))))
            st.plotly_chart(fig_m, use_container_width=True)

        st.markdown(_h("Per-Equipment Net Savings"), unsafe_allow_html=True)
        df_hi = pd.DataFrame(h_inc)
        if not df_hi.empty:
            eq_sav = df_hi.groupby("equipment_id")["net_savings_usd"].sum().sort_values()
            fig_eq = go.Figure(go.Bar(
                x=eq_sav.values, y=eq_sav.index, orientation="h",
                marker=dict(color=eq_sav.values,
                            colorscale=[[0,BLUE],[.5,"#4589ff"],[1,GREEN]],showscale=False),
                text=[f"${v/1e3:.0f}K" for v in eq_sav.values],
                textposition="outside", textfont=dict(color=TXT,size=10),
                hovertemplate="%{y}<br>Net Savings: $%{x:,.0f}<extra></extra>",
            ))
            fig_eq.update_layout(**_cl(height=240,margin=dict(l=80,t=8,b=8,r=60)))
            st.plotly_chart(fig_eq, use_container_width=True)

        c4l,c4r = st.columns(2)
        with c4l:
            ai_c = summ["ai_assisted_incidents"]
            tot  = summ["total_incidents"]
            fig_p = go.Figure(go.Pie(
                labels=["AI-Predictive (PdM)","Reactive (CM)","Scheduled (PM)"],
                values=[ai_c, max(tot-ai_c-5,1), 5], hole=.52,
                marker=dict(colors=[BLUE,RED,GREEN]),
                textfont=dict(size=9,color=TXT),
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            ))
            fig_p.update_layout(**_cl(height=230,
                title=dict(text="Maintenance Type Mix",font=dict(size=10,color=MUTED)),
                margin=dict(t=28,b=8)))
            c4l.plotly_chart(fig_p, use_container_width=True)

        with c4r:
            df_mb = pd.DataFrame(list(mtbf_d.values()))
            fig_mb = go.Figure()
            fig_mb.add_trace(go.Bar(x=df_mb["equipment_id"],y=df_mb["baseline_mtbf_hours"],
                                    name="Baseline",marker_color=RED,opacity=.8,
                                    hovertemplate="%{x}<br>Baseline MTBF: %{y:,.0f} h<extra></extra>"))
            fig_mb.add_trace(go.Bar(x=df_mb["equipment_id"],y=df_mb["ai_assisted_mtbf_hours"],
                                    name="AI-Assisted",marker_color=GREEN,opacity=.8,
                                    hovertemplate="%{x}<br>AI MTBF: %{y:,.0f} h<extra></extra>"))
            fig_mb.update_layout(**_cl(barmode="group",height=230,
                title=dict(text="MTBF Improvement (hours)",font=dict(size=10,color=MUTED)),
                legend=dict(orientation="h",y=-0.28,font=dict(size=9)),
                margin=dict(t=28,b=20)))
            c4r.plotly_chart(fig_mb, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — FMEA CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
with T5:
    st.markdown(
        _h("Interactive FMEA Risk Calculator — Agentic AI") +
        _tip("RPN = Severity (S) × Occurrence (O) × Detectability (D). Range: 1–1000. "
             "≥300 CRITICAL, ≥200 HIGH, ≥100 MEDIUM, <100 LOW."),
        unsafe_allow_html=True,
    )
    st.info(
        "Fill in the equipment parameters below. "
        "Five AI agents (Criticality, Compliance, WorkOrder, ROI, Diagnostics) run in sequence to compute "
        "RPN, criticality band, work order priority, and full financial impact. "
        "Set S/O/D to 0 to let the AI auto-assign based on failure mode and detection method.",
        icon="🤖",
    )

    with st.form("fmea_form"):
        r1c1,r1c2,r1c3,r1c4 = st.columns(4)
        eq_in  = r1c1.selectbox("Equipment Tag", list(_EQ.keys()),
                                 help="Select the equipment for FMEA analysis")
        typ_in = r1c2.selectbox("Equipment Type",
                                 ["PUMP","COMPRESSOR","REACTOR","HEAT_EXCHANGER","SAFETY_VALVE","DISTILLATION_COLUMN"],
                                 help="Equipment type drives default FMEA severity and downtime parameters")
        fm_in  = r1c3.selectbox("Failure Mode",
                                 ["Bearing Failure","Valve Failure","Catalyst Poisoning",
                                  "Tube Bundle Tube Leak","Inspection Overdue",
                                  "Corrosion Under Insulation","Seal Failure",
                                  "Impeller Erosion","Motor Overload","Coupling Misalignment"],
                                 help="Root cause failure mode to analyse")
        det_in = r1c4.selectbox("Detection Method",
                                 ["AI-Predictive","SCADA-Alert","Operator-Report","Routine-PM","No-Monitoring"],
                                 help="How the failure was / will be detected. AI-Predictive gives lowest detectability score (best).")

        st.markdown("**FMEA Scores** — leave at 0 for AI auto-assignment", help="RPN = S × O × D")
        s1,s2,s3 = st.columns(3)
        sev_ov = s1.slider("Severity S  (1=Minor → 10=Catastrophic)", 0,10,0,
                           help="Effect on equipment, process, and personnel safety. 9–10 = plant shutdown or HSE incident.")
        occ_ov = s2.slider("Occurrence O  (1=Rare → 10=Certain)",     0,10,0,
                           help="Historical failure frequency. 8–10 = multiple failures per year.")
        det_ov = s3.slider("Detectability D  (1=Obvious → 10=Hidden)", 0,10,0,
                           help="How detectable the failure mode is. AI-Predictive gives D=1–3; No-Monitoring gives D=8–10.")

        st.markdown("**Financial Parameters**")
        f1,f2,f3,f4 = st.columns(4)
        pr  = f1.number_input("Production Rate ($/hr)",  value=85000,  step=5000,  min_value=1000,
                               help="Plant-wide revenue rate at full capacity. Default: $85,000/hr.")
        mg  = f2.number_input("Product Margin (%)",       value=22.0,   step=1.0,   min_value=0.1, max_value=100.0,
                               help="Gross margin on production. Avoided cost = hours × rate × margin.")
        mc  = f3.number_input("Maintenance Cost ($)",     value=9000,   step=500,   min_value=0,
                               help="Estimated total cost: parts + labor + contractor.")
        lh  = f4.number_input("Labor Hours",               value=8.0,    step=1.0,   min_value=0.0,
                               help="Planned labor hours for the maintenance job.")

        sub = st.form_submit_button("🤖 Run FMEA + Agentic Analysis", type="primary", use_container_width=True)

    if sub:
        from agentic_maintenance.agents.criticality_agent import CriticalityAssessmentAgent
        from agentic_maintenance.agents.work_order_agent  import WorkOrderGenerationAgent
        from agentic_maintenance.agents.compliance_agent  import ComplianceAgent

        with st.spinner("🤖 Running Agentic FMEA pipeline …"):
            crit_ag = CriticalityAssessmentAgent()
            crit    = crit_ag.assess(eq_in, typ_in, fm_in, det_in)
            if sev_ov: crit["fmea_severity"]     = sev_ov
            if occ_ov: crit["fmea_occurrence"]    = occ_ov
            if det_ov: crit["fmea_detectability"] = det_ov
            rpn = crit["fmea_severity"] * crit["fmea_occurrence"] * crit["fmea_detectability"]
            crit["fmea_rpn"]   = rpn
            crit["risk_score"] = round(rpn / 1000 * 10, 2)
            if rpn >= 300:   crit["criticality"] = "CRITICAL"
            elif rpn >= 200: crit["criticality"] = "HIGH"
            elif rpn >= 100: crit["criticality"] = "MEDIUM"
            else:            crit["criticality"] = "LOW"

            comp = ComplianceAgent().check(eq_in, typ_in, None)
            wo   = WorkOrderGenerationAgent().generate(
                eq_in, typ_in, fm_in, None,
                crit["criticality"], crit["risk_score"], rpn,
                {"llm_narrative": f"FMEA: {fm_in} on {eq_in}. Detected by {det_in}.", "anomaly_count":2,
                 "has_critical_anomaly": rpn >= 200},
            )
            _dt = {"PUMP":64,"COMPRESSOR":168,"REACTOR":336,
                   "HEAT_EXCHANGER":96,"SAFETY_VALVE":24,"DISTILLATION_COLUMN":480}
            roi_r = calculate_incident_roi(eq_in, mc, _dt.get(typ_in,64),
                                           labor_hours=lh, production_rate_usd_per_hour=pr, margin=mg/100)

        # ── result KPIs ───────────────────────────────────────────────────────
        _rc = {"CRITICAL":RED,"HIGH":ORANGE,"MEDIUM":AMBER,"LOW":GREEN}
        cc  = _rc.get(crit["criticality"], BLUE)

        rr1,rr2,rr3,rr4,rr5,rr6 = st.columns(6)
        rr1.metric("RPN",         str(rpn),
                   help=f"S={crit['fmea_severity']} × O={crit['fmea_occurrence']} × D={crit['fmea_detectability']}")
        rr2.metric("Criticality", crit["criticality"],
                   help="CRITICAL ≥300 | HIGH ≥200 | MEDIUM ≥100 | LOW <100")
        rr3.metric("Risk Score",  f"{crit['risk_score']}/10",
                   help="RPN normalised to 0–10 scale (RPN/1000 × 10)")
        rr4.metric("WO Priority", wo["priority"],
                   help="EMERGENCY: RPN≥300 or CRITICAL equipment | URGENT: HIGH | MEDIUM: routine")
        rr5.metric("Net Savings", f"${roi_r['net_savings_usd']:,.0f}",
                   help="Avoided downtime cost minus planned maintenance cost for this incident")
        rr6.metric("ROI",         f"{roi_r['roi_pct']:.0f}%",
                   help="(Net Savings / Maintenance Cost) × 100 for this single incident")

        if rpn >= 200:
            st.warning(f"⚠️ HIGH RPN ({rpn}) — Immediate action recommended. Failure mode: **{fm_in}**")
        if comp["violation_count"] > 0:
            st.error(f"🚨 Compliance violation: {comp.get('violations',[{}])[0].get('description','')}")
        else:
            st.success(f"✅ Compliance: {comp['compliance_status']} — no active violations for {eq_in}")

        st.divider()
        fl5,fr5 = st.columns(2)

        with fl5:
            st.markdown(_h("FMEA Factor Radar — Current vs AI-Predicted Reduction"), unsafe_allow_html=True)
            cats   = ["Severity (S)","Occurrence (O)","Detectability (D)","Risk Score","Compliance Risk"]
            cr     = min(comp["violation_count"] * 3, 10)
            v_now  = [crit["fmea_severity"], crit["fmea_occurrence"], crit["fmea_detectability"],
                      min(crit["risk_score"],10), cr]
            v_ai   = [max(v_now[0]-1,1), max(v_now[1]-1,1), max(v_now[2]-3,1),
                      max(v_now[3]-2,0), max(cr-1,0)]
            fig_r  = go.Figure()
            fig_r.add_trace(go.Scatterpolar(
                r=v_now+[v_now[0]], theta=cats+[cats[0]], fill="toself",
                fillcolor="rgba(218,30,40,.18)", line=dict(color=RED,width=2),
                name="Current Risk",
                hovertemplate="%{theta}: %{r}/10<extra></extra>",
            ))
            fig_r.add_trace(go.Scatterpolar(
                r=v_ai+[v_ai[0]], theta=cats+[cats[0]], fill="toself",
                fillcolor="rgba(36,161,72,.13)", line=dict(color=GREEN,width=2,dash="dot"),
                name="With AI PdM",
                hovertemplate="%{theta}: %{r}/10<extra></extra>",
            ))
            fig_r.update_layout(**_cl(height=300,
                polar=dict(bgcolor=CARD,
                           radialaxis=dict(visible=True,range=[0,10],gridcolor=BORDER,color=MUTED,tickfont=dict(size=8)),
                           angularaxis=dict(gridcolor=BORDER,color=MUTED,tickfont=dict(size=9))),
                legend=dict(orientation="h",y=-0.12,font=dict(size=9))))
            st.plotly_chart(fig_r, use_container_width=True)

        with fr5:
            st.markdown(_h("Financial Waterfall"), unsafe_allow_html=True)
            fig_wf = go.Figure(go.Waterfall(
                orientation="v",
                measure=["absolute","relative","relative","total"],
                x=["Avoided Downtime","− Parts/Labor","− Contractor","Net Savings"],
                y=[roi_r["avoided_downtime_cost_usd"], -mc, -(lh*95), 0],
                text=[f"${roi_r['avoided_downtime_cost_usd']:,.0f}",
                      f"-${mc:,.0f}", f"-${lh*95:,.0f}",
                      f"${roi_r['net_savings_usd']:,.0f}"],
                textfont=dict(color=TXT,size=10), textposition="outside",
                connector={"line":{"color":BORDER}},
                increasing={"marker":{"color":GREEN}},
                decreasing={"marker":{"color":RED}},
                totals={"marker":{"color":BLUE}},
                hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
            ))
            fig_wf.update_layout(**_cl(height=300,yaxis=dict(tickprefix="$",tickformat=",.0f")))
            st.plotly_chart(fig_wf, use_container_width=True)

        st.markdown(_h("AI Work Order Recommendation"), unsafe_allow_html=True)
        wc1,wc2,wc3,wc4 = st.columns(4)
        wc1.markdown(f"**Title** — {wo.get('title','—')}")
        wc2.markdown(f"**Priority** — `{wo.get('priority','—')}`")
        wc3.markdown(f"**Type** — `{wo.get('maintenance_type','—')}`")
        wc4.markdown(f"**Labor** — {wo.get('labor_hours','—')} hrs")
        st.markdown(
            '<div class="agcard"><div class="agname">🤖 AI Reasoning Chain</div>'
            '<div class="agdec">' + wo.get("ai_reasoning","")[:320] + '</div></div>',
            unsafe_allow_html=True,
        )

        st.session_state.fmea_hist.append({
            "Equipment": eq_in, "Failure Mode": fm_in, "S": crit["fmea_severity"],
            "O": crit["fmea_occurrence"], "D": crit["fmea_detectability"],
            "RPN": rpn, "Criticality": crit["criticality"],
            "WO Priority": wo["priority"], "Net Savings $": roi_r["net_savings_usd"],
            "Time": datetime.now().strftime("%H:%M:%S"),
        })

    if st.session_state.fmea_hist:
        st.divider()
        st.markdown(_h("Session FMEA History"), unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state.fmea_hist), use_container_width=True, height=180)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ROI WHAT-IF
# ══════════════════════════════════════════════════════════════════════════════
with T6:
    st.markdown(
        _h("ROI What-If Simulator — Real-Time Financial Modelling") +
        _tip("All 12 parameters are live-linked. Adjusting any slider instantly recalculates Year 1 net savings, payback period, and 3-year NPV."),
        unsafe_allow_html=True,
    )
    st.info("Drag any slider to instantly recalculate ROI, payback period, and 3-year NPV.", icon="💡")

    w1,w2 = st.columns(2)
    with w1:
        st.markdown("#### 🏭 Plant Parameters")
        wp   = st.slider("Production Rate ($/hr)",      10_000,200_000,85_000,step=5_000,format="$%d",
                         help="Plant-wide revenue rate at full capacity ($/hr)")
        wm   = st.slider("Product Margin (%)",           5.0,  40.0,  22.0, step=0.5,
                         help="Gross margin on production. Avoided cost = hours × rate × margin")
        wi   = st.slider("Annual Incidents (total)",     10,   100,   42,   step=2,
                         help="Total maintenance incidents per year across all equipment")
        wc   = st.slider("AI Detection Coverage (%)",   10,   100,   75,   step=5,
                         help="% of incidents detected by AI before failure occurs (vs reactive)")
        wai  = st.number_input("AI System Annual Cost ($)", value=250_000, step=25_000, min_value=50_000,
                               help="Total annual cost of the Agentic AI platform")
    with w2:
        st.markdown("#### 🔧 Maintenance Parameters")
        wrd  = st.slider("Avg Reactive Downtime (h/incident)",   8, 480, 72,  step=8,
                         help="Average unplanned downtime when failure is not predicted (reactive/CM)")
        wpd  = st.slider("Avg Planned Downtime (h/incident)",    2,  96,  8,  step=2,
                         help="Average planned downtime with AI prediction (PdM/PM)")
        wrc  = st.slider("Avg Reactive Maint. Cost ($)",     5_000,500_000,45_000,step=5_000,format="$%d",
                         help="Average cost per reactive/emergency maintenance event")
        wpc  = st.slider("Avg Planned Maint. Cost ($)",      2_000,100_000, 9_000,step=1_000,format="$%d",
                         help="Average cost per AI-predicted/planned maintenance event")

    # ── calculations ──────────────────────────────────────────────────────────
    ai_inc   = round(wi * wc / 100)
    re_inc   = wi - ai_inc
    avd_each = (wrd - wpd) * wp * (wm / 100)
    tot_avd  = avd_each * ai_inc
    c_ai_m   = wpc * ai_inc
    c_re_m   = wrc * re_inc
    tot_m    = c_ai_m + c_re_m
    ns1  = tot_avd - tot_m - wai
    ns2  = ns1 * 1.08
    ns3  = ns1 * 1.17
    roi1 = (ns1 / max(wai,1)) * 100
    pay  = wai / max(tot_avd/12, 1)
    npv3 = ns1 + ns2/1.08 + ns3/(1.08**2)

    st.divider()
    st.markdown(_h("What-If Results"), unsafe_allow_html=True)

    wk_row = "".join([
        kcard("Avoided Downtime Cost",  f"${tot_avd/1e6:.2f}M",   f"{ai_inc} AI-detected", "g",
              f"= {ai_inc} AI incidents × {wrd-wpd}h saved × ${wp:,}/hr × {wm}% margin"),
        kcard("Total Maintenance Cost", f"${tot_m/1e6:.2f}M",     f"{wi} total incidents",  "b",
              f"= ${c_ai_m/1e3:.0f}K planned (AI) + ${c_re_m/1e3:.0f}K reactive"),
        kcard("Year 1 Net Savings",     f"${ns1/1e6:.2f}M",       f"after ${wai/1e3:.0f}K AI cost",
              "g" if ns1 > 0 else "r",
              f"= Avoided Cost (${tot_avd/1e6:.2f}M) − Maint. (${tot_m/1e6:.2f}M) − AI (${wai/1e3:.0f}K)"),
        kcard("1-Year ROI",             f"{roi1:.0f}%",            "vs AI system cost",
              "g" if roi1 > 100 else "a",
              f"= Net Savings / AI Cost × 100 = ${ns1/1e3:.0f}K / ${wai/1e3:.0f}K × 100"),
        kcard("Payback Period",         f"{pay:.1f} mo",           "break-even point",        "b",
              f"= AI Cost (${wai/1e3:.0f}K) ÷ Monthly avoided cost (${tot_avd/12/1e3:.0f}K/mo)"),
        kcard("3-Year NPV",             f"${npv3/1e6:.1f}M",       "@ 8% discount rate",
              "g" if npv3 > 0 else "r",
              f"Y1: ${ns1/1e6:.2f}M + Y2: ${ns2/1.08/1e6:.2f}M (disc.) + Y3: ${ns3/(1.08**2)/1e6:.2f}M (disc.)"),
    ])
    st.markdown('<div class="krow">' + wk_row + '</div>', unsafe_allow_html=True)

    st.divider()
    wl,wr = st.columns(2)

    with wl:
        st.markdown(_h("3-Year Net Savings Projection"), unsafe_allow_html=True)
        fig_3y = go.Figure(go.Bar(
            x=["Year 1","Year 2","Year 3"], y=[ns1,ns2,ns3],
            marker=dict(color=[BLUE,"#4589ff",GREEN]),
            text=[f"${v/1e6:.2f}M" for v in [ns1,ns2,ns3]],
            textposition="outside", textfont=dict(color=TXT,size=11),
            hovertemplate="%{x}<br>Net Savings: $%{y:,.0f}<extra></extra>",
        ))
        fig_3y.add_hline(y=0, line_color=BORDER, line_width=1)
        fig_3y.update_layout(**_cl(height=280, yaxis=dict(tickprefix="$",tickformat=",.0f")))
        st.plotly_chart(fig_3y, use_container_width=True)

    with wr:
        st.markdown(_h("ROI Sensitivity vs AI Coverage %") +
                    _tip("Shows how ROI changes as you increase the % of incidents detected by AI. The green dashed line is your current setting."),
                    unsafe_allow_html=True)
        covs  = list(range(10,105,5))
        rois  = []
        for cv in covs:
            ai_i = round(wi * cv / 100)
            re_i = wi - ai_i
            ns_  = avd_each * ai_i - wpc * ai_i - wrc * re_i - wai
            rois.append((ns_ / max(wai,1)) * 100)

        fig_sv = go.Figure(go.Scatter(
            x=covs, y=rois, mode="lines+markers",
            line=dict(color=BLUE,width=2.2),
            fill="tozeroy", fillcolor="rgba(15,98,254,.09)",
            marker=dict(size=4),
            hovertemplate="Coverage %{x}%<br>ROI: %{y:.0f}%<extra></extra>",
        ))
        fig_sv.add_hline(y=0,   line_color=AMBER, line_dash="dot", line_width=1.2,
                         annotation_text="Break-even",
                         annotation_font=dict(color=AMBER,size=9))
        fig_sv.add_vline(x=wc,  line_color=GREEN, line_dash="dash", line_width=1.2,
                         annotation_text=f"Current: {wc}%",
                         annotation_font=dict(color=GREEN,size=9))
        fig_sv.update_layout(**_cl(height=280,
            xaxis=dict(title="AI Coverage %"),
            yaxis=dict(title="ROI %",ticksuffix="%")))
        st.plotly_chart(fig_sv, use_container_width=True)

    st.markdown(_h("Scenario Comparison Table") +
                _tip("Highlighted row = your current AI coverage setting."),
                unsafe_allow_html=True)
    tbl_rows = []
    for cv in [25,50,75,90,100]:
        ai_i = round(wi * cv / 100)
        re_i = wi - ai_i
        avd  = avd_each * ai_i
        mnt  = wpc * ai_i + wrc * re_i
        ns_  = avd - mnt - wai
        tbl_rows.append({
            "AI Coverage %":          cv,
            "AI-Detected Incidents":  ai_i,
            "Avoided Cost $":         round(avd),
            "Maint. Cost $":          round(mnt),
            "Net Savings $":          round(ns_),
            "ROI %":                  round((ns_/max(wai,1))*100,1),
            "Payback (months)":       round(wai/max(avd/12,1),1),
        })
    df_tbl = pd.DataFrame(tbl_rows)

    def _hl(row):
        hl = f"background:{BLUE}22;color:{TXT}"
        if row["AI Coverage %"] == wc:
            return [hl] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_tbl.style.apply(_hl, axis=1)
               .format({"Avoided Cost $":"${:,.0f}","Maint. Cost $":"${:,.0f}","Net Savings $":"${:,.0f}"}),
        use_container_width=True, height=220,
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — COMPLIANCE
# ══════════════════════════════════════════════════════════════════════════════
with T7:
    tc1,tc2 = st.columns([2,1])

    with tc1:
        st.markdown(_h("Overdue Inspection Tracker") +
                    _tip("Equipment with inspection intervals exceeded. Non-compliance with OSHA/API/ASME standards triggers mandatory regulatory notification."),
                    unsafe_allow_html=True)
        if ov_insp:
            for item in ov_insp:
                days = item["days_overdue"]
                badge = '<span class="bc">CRITICAL</span>' if days > 14 else '<span class="bh">OVERDUE</span>'
                st.markdown(
                    '<div class="hrow">'
                    + badge
                    + f'<b style="color:#e2eaf6;margin-left:6px">{item["equipment_id"]}</b>'
                    + f'<span style="color:#7d9bbf"> ({item["type"]})</span>'
                    + f'<span style="color:{RED};margin-left:auto;font-family:\'IBM Plex Mono\',monospace;font-size:.72rem">{days} days overdue</span>'
                    + f'<span style="color:#7d9bbf;font-size:.68rem;margin-left:10px">{item.get("governing_standard","")}</span>'
                    + '</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ All inspections current")

    with tc2:
        st.markdown(_h("Compliance Rate"), unsafe_allow_html=True)
        n_tot   = 12
        comp_rt = round((n_tot - n_over) / n_tot * 100, 0)
        fig_cmp = go.Figure(go.Pie(
            labels=["Compliant","Overdue"],
            values=[n_tot-n_over, n_over], hole=0.62,
            marker=dict(colors=[GREEN,RED]),
            textfont=dict(size=11,color=TXT),
            hovertemplate="%{label}: %{value} equipment<extra></extra>",
        ))
        fig_cmp.add_annotation(text=f"{comp_rt:.0f}%",
                               x=0.5,y=0.5,showarrow=False,
                               font=dict(size=22,color=TXT,family="IBM Plex Sans"))
        fig_cmp.update_layout(**_cl(height=200, margin=dict(t=8,b=8,l=8,r=8), showlegend=True,
                                    legend=dict(orientation="h",y=-0.15,font=dict(size=9))))
        st.plotly_chart(fig_cmp, use_container_width=True)
        st.metric("Compliance Rate", f"{comp_rt:.0f}%",
                  delta=f"−{n_over} overdue" if n_over else "All current",
                  delta_color="inverse" if n_over else "normal",
                  help="% of 12 tracked equipment items with current regulatory inspection status")

    st.divider()
    st.markdown(_h("Full Inspection Schedule"), unsafe_allow_html=True)
    sched = get_inspection_schedule()
    if sched:
        df_sc = pd.DataFrame([{
            "Equipment":       s["equipment_id"],
            "Type":            s["type"],
            "Last Inspection": s.get("last_inspection") or s.get("last_cui_survey","—"),
            "Next Due":        s.get("next_due","—"),
            "Standard":        s.get("governing_standard", s.get("risk_basis",""))[:44],
            "Status":          s["status"],
            "Days Overdue":    s.get("days_overdue",0),
        } for s in sched])
        _sc_map = {"OVERDUE":"background:#1c0000;color:#fca5a5",
                   "CURRENT":"background:#052e12;color:#4ade80"}
        st.dataframe(df_sc.style.map(lambda v: _sc_map.get(v,""), subset=["Status"]),
                     use_container_width=True, height=270)

    st.divider()
    st.markdown(_h("Historical AI vs Reactive — Scatter Analysis") +
                _tip("Each point is one historical incident. Size = downtime hours avoided. Green = AI-predicted. Red = Reactive."),
                unsafe_allow_html=True)
    df_hi2 = pd.DataFrame(h_inc)
    if not df_hi2.empty:
        sha,shb = st.columns([3,2])
        with sha:
            fig_sc = px.scatter(
                df_hi2, x="maintenance_cost_usd", y="net_savings_usd",
                color="ai_assisted",
                color_discrete_map={True:GREEN, False:RED},
                size="downtime_hours_avoided", size_max=18,
                hover_data=["equipment_id","incident_type","downtime_hours_avoided"],
                labels={"maintenance_cost_usd":"Maintenance Cost ($)",
                        "net_savings_usd":"Net Savings ($)",
                        "ai_assisted":"AI Assisted"},
            )
            fig_sc.update_layout(**_cl(height=280,
                title=dict(text="Net Savings vs Cost  (bubble = downtime avoided)",
                           font=dict(size=10,color=MUTED)),
                margin=dict(t=28,b=28)))
            sha.plotly_chart(fig_sc, use_container_width=True)

        with shb:
            ai_pct_h = round(df_hi2["ai_assisted"].mean()*100, 1)
            tot_sav  = df_hi2["net_savings_usd"].sum()
            shb.metric("Total Incidents",   str(len(df_hi2)),  help="12-month historical incident count")
            shb.metric("AI Detection Rate", f"{ai_pct_h}%",    help="% of incidents detected by AI before failure")
            shb.metric("Total Savings",     f"${tot_sav/1e6:.1f}M", help="Total net savings across all AI-assisted incidents")
            shb.metric("Avg Saving/Incident",
                       f"${df_hi2[df_hi2['ai_assisted']]['net_savings_usd'].mean()/1e3:.0f}K",
                       help="Average net saving per AI-detected incident")

# ── footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<div style="text-align:center;color:#3d5a7a;font-size:.65rem;padding:6px 0">'
    '⚙️ <b style="color:#0f62fe">Agentic Maintenance AI v3.0</b> &nbsp;|&nbsp; IBM Consulting '
    '&nbsp;|&nbsp; Chemicals &amp; Petrochemicals '
    f'&nbsp;|&nbsp; 🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    '</div>',
    unsafe_allow_html=True,
)
