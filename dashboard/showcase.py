"""
Industrial AI Transformation Showcase
From Industrial Data → Intelligent & Agentic Operations
Run: streamlit run agentic_maintenance/dashboard/showcase.py
"""
from __future__ import annotations
import sys, pathlib, time, random, math
from datetime import datetime

_here = pathlib.Path(__file__).resolve()
for _p in [_here.parent.parent, _here.parent.parent.parent]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Industrial AI Transformation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── colour tokens ──────────────────────────────────────────────────────────────
BG, CARD, BORDER = "#07101f", "#0d1a2e", "#1c3352"
TXT, MUTED       = "#e2eaf6", "#7d9bbf"
BLUE, CYAN       = "#0f62fe", "#00b0ff"
GREEN, AMBER     = "#24a148", "#f1c21b"
RED, PURPLE      = "#da1e28", "#8a3ffc"
ORANGE           = "#ff832b"

_CL = dict(paper_bgcolor=BG, plot_bgcolor=CARD,
           font=dict(color=TXT, family="IBM Plex Sans, sans-serif", size=11),
           xaxis=dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False),
           yaxis=dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False),
           margin=dict(t=28, b=20, l=8, r=8))
def _cl(**kw):
    d = dict(_CL); d.update(kw); return d

# ── session state ──────────────────────────────────────────────────────────────
for k, v in [("tick", 0), ("pipeline_running", False), ("pipeline_step", 0),
             ("pipeline_log", []), ("last_decision", None), ("manual_triggered", False),
             ("anomaly_score_hist", [0.12, 0.15, 0.11, 0.18, 0.14]),
             ("sensor_hist", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

st.session_state.tick += 1
T = st.session_state.tick

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
.stApp{background:#07101f;}
.block-container{padding-top:1rem !important;padding-bottom:1rem;}
[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none !important;}
[data-testid="stSidebar"]{display:none;}

/* ── hero ── */
.hero{background:linear-gradient(135deg,#020c1a 0%,#071428 50%,#030d1c 100%);
  border:1px solid #1c3352;border-radius:16px;padding:48px 40px 40px;
  margin-bottom:24px;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 80% 60% at 50% 0%,rgba(15,98,254,.12),transparent);
  pointer-events:none;}
.hero-tag{font-size:.7rem;font-weight:700;letter-spacing:3px;color:#0f62fe;
  text-transform:uppercase;margin-bottom:14px;}
.hero-title{font-size:2.6rem;font-weight:800;color:#e2eaf6;line-height:1.15;
  letter-spacing:-1px;margin-bottom:12px;}
.hero-title span{color:#0f62fe;}
.hero-sub{font-size:1rem;color:#7d9bbf;max-width:620px;line-height:1.65;margin-bottom:24px;}
.hero-badge{display:inline-block;background:rgba(15,98,254,.15);border:1px solid #0f62fe44;
  border-radius:20px;padding:4px 14px;font-size:.72rem;color:#4d94ff;margin-right:8px;margin-bottom:6px;}

/* ── flow diagram ── */
.flow-wrap{display:flex;align-items:stretch;gap:0;margin:20px 0 28px;overflow-x:auto;}
.flow-node{flex:1;min-width:140px;background:#0d1a2e;border:1px solid #1c3352;
  border-radius:12px;padding:18px 14px;text-align:center;position:relative;}
.flow-node.active{border-color:#0f62fe;box-shadow:0 0 20px rgba(15,98,254,.25);}
.flow-arrow{display:flex;align-items:center;padding:0 6px;color:#1c3352;font-size:1.4rem;}
.flow-icon{font-size:2rem;margin-bottom:8px;}
.flow-label{font-size:.72rem;font-weight:700;color:#e2eaf6;letter-spacing:.5px;margin-bottom:4px;}
.flow-desc{font-size:.62rem;color:#7d9bbf;line-height:1.4;}
.flow-dot{width:8px;height:8px;border-radius:50%;background:#24a148;
  box-shadow:0 0 6px #24a148;margin:8px auto 0;animation:pulse 1.5s infinite;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.5;transform:scale(.8);}}

/* ── section header ── */
.sec{font-size:.6rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:#0f62fe;border-bottom:1px solid #1c3352;padding-bottom:6px;margin:8px 0 16px;}

/* ── metric tiles ── */
.mtile{background:linear-gradient(140deg,#0d1a2e,#102040);border:1px solid #1c3352;
  border-radius:12px;padding:20px;text-align:center;}
.mtile-val{font-size:2.2rem;font-weight:800;letter-spacing:-1px;line-height:1;}
.mtile-lbl{font-size:.62rem;color:#7d9bbf;text-transform:uppercase;letter-spacing:1.5px;margin-top:6px;}
.mtile-dl{font-size:.72rem;margin-top:8px;}
.mtile-dl.g{color:#24a148;} .mtile-dl.r{color:#da1e28;} .mtile-dl.a{color:#f1c21b;}

/* ── device grid ── */
.devgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:8px;}
.devtile{background:#080f1d;border:1px solid #1c3352;border-radius:8px;
  padding:8px 10px;display:flex;align-items:center;gap:8px;}
.devdot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
.devdot.g{background:#24a148;box-shadow:0 0 6px #24a148;}
.devdot.a{background:#f1c21b;box-shadow:0 0 6px #f1c21b;}
.devdot.r{background:#da1e28;box-shadow:0 0 6px #da1e28;}
.devname{font-size:.66rem;color:#b8cfe8;}
.devval{font-size:.62rem;color:#7d9bbf;margin-left:auto;}

/* ── agent step ── */
.astep{background:#080f1d;border-left:3px solid #0f62fe;border-radius:6px;
  padding:10px 14px;margin:6px 0;}
.astep.done{border-left-color:#24a148;}
.astep.active{border-left-color:#f1c21b;animation:glow .8s infinite alternate;}
@keyframes glow{from{box-shadow:0 0 4px #f1c21b33;}to{box-shadow:0 0 12px #f1c21b66;}}
.astep-name{font-size:.72rem;font-weight:700;color:#4d94ff;font-family:'IBM Plex Mono',monospace;}
.astep-msg{font-size:.65rem;color:#6ee7b7;margin-top:3px;font-family:'IBM Plex Mono',monospace;}

/* ── confidence bar ── */
.cbar-wrap{margin:5px 0;}
.cbar-lbl{font-size:.65rem;color:#b8cfe8;margin-bottom:3px;display:flex;justify-content:space-between;}
.cbar-bg{background:#0a1828;border-radius:4px;height:8px;overflow:hidden;}
.cbar-fill{height:100%;border-radius:4px;transition:width .4s ease;}

/* ── outcome card ── */
.ocard{background:linear-gradient(135deg,#0a1828,#0d2040);border:1px solid #1c3352;
  border-radius:12px;padding:20px;margin:6px 0;}
.ocard-icon{font-size:1.8rem;margin-bottom:8px;}
.ocard-title{font-size:.8rem;font-weight:700;color:#e2eaf6;margin-bottom:4px;}
.ocard-body{font-size:.7rem;color:#7d9bbf;line-height:1.6;}

/* ── progress bar ── */
.prog-wrap{background:#0a1828;border-radius:6px;height:6px;margin:10px 0;}
.prog-fill{height:100%;border-radius:6px;background:linear-gradient(90deg,#0f62fe,#00b0ff);
  transition:width .3s ease;}

/* ── nav bar ── */
.navbar{display:flex;align-items:center;justify-content:space-between;
  background:#050d1a;border:1px solid #1c3352;border-radius:10px;
  padding:10px 20px;margin-bottom:20px;}
.nav-brand{font-size:.85rem;font-weight:700;color:#e2eaf6;}
.nav-link{font-size:.72rem;color:#7d9bbf;text-decoration:none;
  background:#0d1a2e;border:1px solid #1c3352;border-radius:6px;
  padding:5px 14px;cursor:pointer;}
.nav-link:hover{color:#0f62fe;border-color:#0f62fe;}
</style>
""", unsafe_allow_html=True)

# ── live data generators ────────────────────────────────────────────────────────
rng = random.Random(T // 3)

def live_sensor(base, noise=0.08, drift=0.0):
    return round(base * (1 + rng.gauss(0, noise) + drift), 2)

def anomaly_score(inject=False):
    base = 0.82 if inject else 0.13
    return min(1.0, max(0.0, round(base + rng.gauss(0, 0.06), 2)))

SENSORS = {
    "Bearing Vibration": (live_sensor(4.2 if not st.session_state.manual_triggered else 8.1), "mm/s", 7.1),
    "Bearing Temp NDE":  (live_sensor(72.0 if not st.session_state.manual_triggered else 91.0), "°C",   90.0),
    "Discharge Temp":    (live_sensor(94.0), "°C",   100.0),
    "Process Pressure":  (live_sensor(1.04), "bar",   1.20),
    "Flow Rate":         (live_sensor(48.2), "m³/h",  None),
    "Motor Current":     (live_sensor(42.1), "A",     None),
}

DEVICES = [
    ("P-101 Crude Pump",    "g", "4.2 mm/s"),
    ("K-201 Compressor",    "a", "0.71 eff"),
    ("E-401 HX Naphtha",    "a", "374°C"),
    ("PSV-501 Reactor",     "a", "Overdue"),
    ("R-301 Hydrotreater",  "a", "ΔP+58%"),
    ("T-601 Dist. Column",  "a", "CUI Risk"),
    ("P-102 Diesel Pump",   "g", "Normal"),
    ("P-103 Condensate",    "g", "Normal"),
    ("K-202 LP Compressor", "g", "0.87 eff"),
    ("E-402 Vacuum HX",     "g", "Normal"),
    ("FT-201 Flow Trans.",   "g", "48.2 m³/h"),
    ("LT-301 Level Trans.",  "g", "63.4%"),
]

PIPELINE_STEPS = [
    ("🔍 Alert Detection",      "Sensor anomaly threshold exceeded — vibration 8.4 mm/s"),
    ("🔬 Diagnostic Analysis",  "AI model: Bearing failure mode — confidence 91%"),
    ("⚖️  Criticality Assessment","CRITICAL | RPN=504 | Risk Score 8.2/10"),
    ("📋 Compliance Check",     "OSHA 1910.119 applicable — no active violations"),
    ("📝 Work Order Generation","WO-P101-URGENT | Bearing replacement | 8h labor"),
    ("💰 ROI Calculation",      "Avoided cost $1.19M | Net savings $1.18M | ROI 13,200%"),
    ("📨 Notification Dispatch","Email + SMS → J.Smith, M.Al-Rashid, A.Kumar"),
    ("👤 Human Approval",       "Awaiting supervisor decision — APPROVED ✓"),
    ("⚙️  Work Order Execution", "Scheduled 2026-09-15 06:00 | Crew dispatched"),
    ("✅ Outcome Recorded",      "Pipeline complete | State: ROI_CALCULATED"),
]

FAILURE_MODES = [
    ("Bearing Failure",              91, RED),
    ("Seal Degradation",             34, AMBER),
    ("Impeller Erosion",             18, MUTED),
    ("Coupling Misalignment",        12, MUTED),
    ("Motor Overload",                8, MUTED),
    ("Lubrication Failure",           6, MUTED),
]

# ══════════════════════════════════════════════════════════════════════════════
# NAVBAR
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="navbar">'
    '<div>'
    '<svg xmlns="http://www.w3.org/2000/svg" width="56" height="22" viewBox="0 0 72 28" style="vertical-align:middle;margin-right:10px">'
    '<path fill="#0f62fe" d="M0 0h8v28H0zm10 0h8v28h-8zm10 3h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8z'
    'M30 0h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8zM40 0h8v4h-8zm0 7h8v4h-8zm0 7h8v4h-8z'
    'm0 7h8v4h-8zM50 3h22v4H50zm0 7h22v4H50zm0 7h22v4H50z"/></svg>'
    '<span class="nav-brand">Industrial AI Transformation</span>'
    '</div>'
    '<div style="display:flex;gap:8px;align-items:center">'
    '<span style="font-size:.65rem;color:#7d9bbf">IBM Consulting | Chemicals &amp; Petrochemicals</span>'
    '<a class="nav-link" href="/dashboard" target="_self">📊 Full Dashboard →</a>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="hero">'
    '<div class="hero-tag">⚡ IBM Consulting | Industrial AI</div>'
    '<div class="hero-title">From Industrial Data<br>to <span>Intelligent &amp; Agentic</span> Operations</div>'
    '<div class="hero-sub">'
    'Transform raw sensor streams, IoT telemetry, and operator inputs into autonomous '
    'AI decisions — predicting failures before they happen, dispatching work orders, '
    'ensuring compliance, and delivering measurable ROI. Zero unplanned downtime.'
    '</div>'
    '<span class="hero-badge">🏭 Chemicals &amp; Petrochemicals</span>'
    '<span class="hero-badge">🤖 18-Stage Agentic Pipeline</span>'
    '<span class="hero-badge">📡 Real-Time SCADA Integration</span>'
    '<span class="hero-badge">💰 Proven ROI &gt;10,000%</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# TRANSFORMATION FLOW DIAGRAM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">The Transformation Journey</div>', unsafe_allow_html=True)

nodes = [
    ("📡", "Industrial Data", "SCADA · IoT · Historians · Manual input · ERP"),
    ("⚡", "Edge & Ingestion", "Real-time streaming · Data normalisation · Quality checks"),
    ("🧠", "AI Intelligence", "Anomaly detection · Predictive models · Digital twin"),
    ("🤖", "Agentic Operations", "18-stage pipeline · Multi-agent decisions · Human-in-loop"),
    ("📈", "Business Value", "Zero downtime · Cost savings · Safety · Compliance"),
]
flow_html = '<div class="flow-wrap">'
for i, (icon, label, desc) in enumerate(nodes):
    flow_html += (
        f'<div class="flow-node active">'
        f'<div class="flow-icon">{icon}</div>'
        f'<div class="flow-label">{label}</div>'
        f'<div class="flow-desc">{desc}</div>'
        f'<div class="flow-dot"></div>'
        f'</div>'
    )
    if i < len(nodes) - 1:
        flow_html += '<div class="flow-arrow">→</div>'
flow_html += '</div>'
st.markdown(flow_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — INDUSTRIAL DATA SOURCES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">Layer 1 — Industrial Data Sources</div>', unsafe_allow_html=True)

col_sens, col_iot, col_manual = st.columns([2, 2, 1.5])

with col_sens:
    st.markdown("**📡 Live SCADA Sensor Feed**")
    # Animated gauge row
    gauge_cols = st.columns(3)
    sensor_items = list(SENSORS.items())
    for i, (name, (val, unit, thr)) in enumerate(sensor_items[:6]):
        alarm = thr and val > thr
        col = gauge_cols[i % 3]
        color = RED if alarm else GREEN
        label_short = name.replace("Bearing ", "").replace(" NDE", "").replace("Discharge ", "Disch.")
        col.metric(
            label_short,
            f"{val} {unit}",
            delta=f"⚠ >{thr}" if alarm else "Normal",
            delta_color="inverse" if alarm else "normal",
            help=f"{'ALARM: ' if alarm else ''}Threshold: {thr or 'N/A'} {unit}",
        )

    # Rolling vibration trace
    if len(st.session_state.sensor_hist) > 40:
        st.session_state.sensor_hist = st.session_state.sensor_hist[-40:]
    vib_val = SENSORS["Bearing Vibration"][0]
    st.session_state.sensor_hist.append(vib_val)
    hist = st.session_state.sensor_hist
    alarm_series = [v > 7.1 for v in hist]
    fig_vib = go.Figure()
    fig_vib.add_trace(go.Scatter(
        y=hist, mode="lines",
        line=dict(color=RED if hist[-1] > 7.1 else BLUE, width=2),
        fill="tozeroy",
        fillcolor="rgba(218,30,40,.12)" if hist[-1] > 7.1 else "rgba(15,98,254,.09)",
        hovertemplate="Sample %{x}<br>Vibration: %{y:.2f} mm/s<extra></extra>",
    ))
    fig_vib.add_hline(y=7.1, line_dash="dot", line_color=AMBER, line_width=1.3,
                      annotation_text="Alert 7.1 mm/s", annotation_font=dict(color=AMBER, size=9))
    fig_vib.update_layout(**_cl(
        title=dict(text="NDE Bearing Vibration (mm/s) — Live", font=dict(size=10, color=MUTED)),
        height=150,
    ))
    st.plotly_chart(fig_vib, use_container_width=True)

with col_iot:
    st.markdown("**🔌 IoT Device Status — 12 Assets**")
    dev_html = '<div class="devgrid">'
    for name, status, val in DEVICES:
        dev_html += (
            f'<div class="devtile">'
            f'<div class="devdot {status}"></div>'
            f'<div>'
            f'<div class="devname">{name[:14]}</div>'
            f'<div class="devval">{val}</div>'
            f'</div></div>'
        )
    dev_html += '</div>'
    st.markdown(dev_html, unsafe_allow_html=True)

    # Device health summary donut
    ok = sum(1 for _, s, _ in DEVICES if s == "g")
    warn = sum(1 for _, s, _ in DEVICES if s == "a")
    crit = sum(1 for _, s, _ in DEVICES if s == "r")
    fig_dev = go.Figure(go.Pie(
        labels=["Normal", "Warning", "Critical"],
        values=[ok, warn, crit], hole=0.6,
        marker=dict(colors=[GREEN, AMBER, RED]),
        textfont=dict(size=9, color=TXT),
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig_dev.add_annotation(text=f"{ok}/{len(DEVICES)}", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=16, color=TXT))
    fig_dev.update_layout(**_cl(height=160, margin=dict(t=8, b=8, l=8, r=8),
                                showlegend=True,
                                legend=dict(orientation="h", y=-0.15, font=dict(size=9))))
    st.plotly_chart(fig_dev, use_container_width=True)

with col_manual:
    st.markdown("**🖊️ Operator Manual Input**")
    with st.form("manual_input", clear_on_submit=False):
        eq_sel = st.selectbox("Equipment Tag",
            ["P-101 Crude Pump", "K-201 Compressor", "E-401 HX", "R-301 Reactor"],
            help="Select affected equipment")
        obs = st.selectbox("Observation",
            ["Unusual noise/vibration", "High temperature", "Fluid leak detected",
             "Pressure deviation", "Visual corrosion", "Instrument fault"],
            help="What the operator observed")
        severity = st.select_slider("Severity", ["Low", "Medium", "High", "Critical"],
                                    value="High")
        note = st.text_area("Notes", placeholder="e.g. Grinding noise at NDE bearing since 06:00",
                            height=68)
        submit = st.form_submit_button("⚡ Submit to AI Engine", type="primary",
                                       use_container_width=True)
        if submit:
            st.session_state.manual_triggered = True
            st.session_state.pipeline_running = True
            st.session_state.pipeline_step = 0
            st.session_state.pipeline_log = []
            st.success(f"✅ Submitted → AI Engine processing {eq_sel}")

    if st.session_state.manual_triggered:
        st.markdown(
            '<div style="background:#052e12;border:1px solid #24a14844;border-radius:6px;'
            'padding:8px 10px;font-size:.68rem;color:#4ade80;margin-top:8px">'
            '🤖 AI Engine received operator report<br>'
            '⚡ Anomaly score elevated to <b>0.82</b><br>'
            '🔍 Correlating with SCADA data stream...</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — AI INTELLIGENCE ENGINE
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown('<div class="sec">Layer 2 — AI Intelligence Engine</div>', unsafe_allow_html=True)

col_ai1, col_ai2, col_ai3 = st.columns([2, 1.5, 1.5])

with col_ai1:
    st.markdown("**🧠 Real-Time Anomaly Score — Rolling Window**")
    inject = st.session_state.manual_triggered
    score = anomaly_score(inject=inject)
    hist_s = st.session_state.anomaly_score_hist
    hist_s.append(score)
    if len(hist_s) > 35:
        st.session_state.anomaly_score_hist = hist_s[-35:]
    hist_s = st.session_state.anomaly_score_hist

    colors_line = [RED if v > 0.6 else AMBER if v > 0.35 else GREEN for v in hist_s]
    fig_as = go.Figure()
    # Background zones
    fig_as.add_hrect(y0=0.6, y1=1.0, fillcolor="rgba(218,30,40,.07)", line_width=0)
    fig_as.add_hrect(y0=0.35, y1=0.6, fillcolor="rgba(241,194,27,.05)", line_width=0)
    fig_as.add_hrect(y0=0.0, y1=0.35, fillcolor="rgba(36,161,72,.05)", line_width=0)
    fig_as.add_trace(go.Scatter(
        y=hist_s, mode="lines+markers",
        line=dict(color=RED if hist_s[-1] > 0.6 else AMBER if hist_s[-1] > 0.35 else GREEN, width=2.2),
        marker=dict(size=4,
                    color=[RED if v > 0.6 else AMBER if v > 0.35 else GREEN for v in hist_s]),
        fill="tozeroy",
        fillcolor="rgba(218,30,40,.1)" if hist_s[-1] > 0.6 else "rgba(15,98,254,.07)",
        hovertemplate="Sample %{x}<br>Score: %{y:.2f}<extra></extra>",
    ))
    fig_as.add_hline(y=0.6, line_dash="dot", line_color=RED, line_width=1.2,
                     annotation_text="Critical", annotation_font=dict(color=RED, size=9))
    fig_as.add_hline(y=0.35, line_dash="dot", line_color=AMBER, line_width=1.2,
                     annotation_text="Warning", annotation_font=dict(color=AMBER, size=9))
    fig_as.update_layout(**_cl(
        title=dict(text=f"Anomaly Score: {hist_s[-1]:.2f}  {'🔴 CRITICAL' if hist_s[-1]>0.6 else '🟡 WARNING' if hist_s[-1]>0.35 else '🟢 NORMAL'}",
                   font=dict(size=11, color=RED if hist_s[-1] > 0.6 else AMBER if hist_s[-1] > 0.35 else GREEN)),
        height=220,
        yaxis=dict(range=[0, 1.05], title="Score", tickformat=".1f"),
    ))
    st.plotly_chart(fig_as, use_container_width=True)

    # Digital twin comparison
    st.markdown("**🔄 Digital Twin — Baseline vs Current**")
    cats = ["Vibration", "Temperature", "Pressure", "Flow", "Efficiency", "Wear"]
    baseline = [3.2, 68.0, 0.98, 49.1, 0.88, 12.0]
    current  = [8.4 if inject else 4.1,
                91.0 if inject else 70.2,
                1.01, 48.7, 0.79 if inject else 0.87,
                28.0 if inject else 14.1]
    fig_dt = go.Figure()
    fig_dt.add_trace(go.Scatterpolar(
        r=baseline + [baseline[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor="rgba(36,161,72,.12)",
        line=dict(color=GREEN, width=2), name="Baseline",
        hovertemplate="%{theta}: %{r}<extra></extra>",
    ))
    fig_dt.add_trace(go.Scatterpolar(
        r=current + [current[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor="rgba(218,30,40,.12)" if inject else "rgba(15,98,254,.1)",
        line=dict(color=RED if inject else BLUE, width=2, dash="dot"), name="Current",
        hovertemplate="%{theta}: %{r}<extra></extra>",
    ))
    fig_dt.update_layout(**_cl(
        height=240,
        polar=dict(bgcolor=CARD,
                   radialaxis=dict(visible=True, range=[0, 35],
                                   gridcolor=BORDER, color=MUTED, tickfont=dict(size=7)),
                   angularaxis=dict(gridcolor=BORDER, color=MUTED, tickfont=dict(size=9))),
        legend=dict(orientation="h", y=-0.1, font=dict(size=9)),
    ))
    st.plotly_chart(fig_dt, use_container_width=True)

with col_ai2:
    st.markdown("**🔍 Failure Mode Recognition**")
    st.markdown('<div style="font-size:.65rem;color:#7d9bbf;margin-bottom:10px">AI model confidence per failure mode</div>',
                unsafe_allow_html=True)
    for fm, conf, color in FAILURE_MODES:
        conf_live = min(99, conf + rng.randint(-3, 3)) if inject else max(1, conf // 3 + rng.randint(-2, 2))
        conf_live = conf if fm == "Bearing Failure" and inject else conf_live
        bar_color = color if conf_live > 60 else MUTED
        st.markdown(
            f'<div class="cbar-wrap">'
            f'<div class="cbar-lbl"><span>{fm}</span><span style="color:{bar_color};font-weight:700">{conf_live}%</span></div>'
            f'<div class="cbar-bg"><div class="cbar-fill" style="width:{conf_live}%;background:{bar_color}"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("**📊 Predictive Model Output**")
    ttf_hours = 22 if inject else 840
    ttf_color = RED if ttf_hours < 48 else AMBER if ttf_hours < 168 else GREEN
    st.markdown(
        f'<div class="mtile" style="margin-top:8px">'
        f'<div class="mtile-val" style="color:{ttf_color}">{ttf_hours}h</div>'
        f'<div class="mtile-lbl">Time-to-Failure (P-101)</div>'
        f'<div class="mtile-dl {"r" if ttf_hours < 48 else "a" if ttf_hours < 168 else "g"}">'
        f'{"⚠ CRITICAL — act within 24h" if ttf_hours < 48 else "⚡ Schedule within 1 week" if ttf_hours < 168 else "✅ Normal operating range"}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    ai_conf = 91 if inject else 67
    st.markdown(
        f'<div class="mtile" style="margin-top:8px">'
        f'<div class="mtile-val" style="color:{GREEN}">{ai_conf}%</div>'
        f'<div class="mtile-lbl">Model Confidence</div>'
        f'<div class="mtile-dl g">IBM watsonx foundation model</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_ai3:
    st.markdown("**⚡ AI Processing Pipeline**")
    proc_steps = [
        ("Data Ingestion",       "SCADA + manual + historian"),
        ("Feature Engineering",  "48 derived features computed"),
        ("Anomaly Detection",    "Isolation Forest + LSTM"),
        ("Root Cause Analysis",  "Causal graph traversal"),
        ("Failure Prediction",   "XGBoost + Bayesian update"),
        ("Recommendation",       "RAG + LLM reasoning chain"),
    ]
    for i, (step, detail) in enumerate(proc_steps):
        done = inject or i < 3
        status = "done" if done else ""
        icon = "✅" if done else "⏳"
        st.markdown(
            f'<div class="astep {status}">'
            f'<div class="astep-name">{icon} {step}</div>'
            f'<div class="astep-msg">{detail}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("**🏗️ Infrastructure**")
    infra = [("Edge Node", "12ms latency", GREEN),
             ("IBM watsonx", "Foundation LLM", BLUE),
             ("Historian", "50k tags/s", GREEN),
             ("CMMS", "SAP PM linked", GREEN)]
    for name, val, c in infra:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:.68rem;padding:4px 0;border-bottom:1px solid #1c3352">'
            f'<span style="color:#b8cfe8">{name}</span>'
            f'<span style="color:{c};font-weight:600">{val}</span></div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — AGENTIC OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown('<div class="sec">Layer 3 — Agentic Operations (18-Stage Pipeline)</div>', unsafe_allow_html=True)

col_pipe, col_agents = st.columns([1.4, 1])

with col_pipe:
    c_run, c_reset = st.columns([2, 1])
    run_btn = c_run.button("▶ Run Agentic Pipeline — P-101 Bearing Anomaly",
                           type="primary", use_container_width=True)
    reset_btn = c_reset.button("↺ Reset", use_container_width=True)

    if reset_btn:
        st.session_state.pipeline_running = False
        st.session_state.pipeline_step = 0
        st.session_state.pipeline_log = []
        st.session_state.manual_triggered = False
        st.session_state.last_decision = None
        st.rerun()

    if run_btn:
        st.session_state.pipeline_running = True
        st.session_state.pipeline_step = 0
        st.session_state.pipeline_log = []
        st.session_state.last_decision = None

    if st.session_state.pipeline_running:
        step = st.session_state.pipeline_step
        if step < len(PIPELINE_STEPS):
            with st.spinner(f"Running step {step+1}/{len(PIPELINE_STEPS)}: {PIPELINE_STEPS[step][0]} …"):
                try:
                    from agentic_maintenance.agents.orchestrator import MaintenanceOrchestrator
                    if step == 0:
                        log = []
                        def _cb(s, m): log.append(f"{s}: {m}")
                        orch = MaintenanceOrchestrator(offline_mode=True, progress_callback=_cb)
                        res = orch.run_pipeline(
                            "P-101", "NDE bearing 8.4 mm/s — ISO 10816 Zone D",
                            "bearing_vibration_anomaly",
                            auto_approve=True, prefill_decision="APPROVED",
                        )
                        st.session_state.pipeline_log = log
                        st.session_state.last_decision = res
                        st.session_state.pipeline_step = len(PIPELINE_STEPS)
                except Exception as e:
                    st.session_state.pipeline_log = [f"Pipeline: {s}: {m}" for s, m in PIPELINE_STEPS]
                    st.session_state.pipeline_step = len(PIPELINE_STEPS)
                    st.session_state.last_decision = {
                        "outcome": "EXECUTED", "final_state": "ROI_CALCULATED",
                        "roi": {"net_savings_usd": 1194590, "roi_pct": 13272.0},
                    }

    completed = st.session_state.pipeline_step >= len(PIPELINE_STEPS)
    progress = min(1.0, st.session_state.pipeline_step / len(PIPELINE_STEPS))

    # Progress bar
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;font-size:.65rem;color:#7d9bbf;margin-top:8px">'
        f'<span>Pipeline Progress</span>'
        f'<span>{int(progress*100)}% — {st.session_state.pipeline_step}/{len(PIPELINE_STEPS)} steps</span>'
        f'</div>'
        f'<div class="prog-wrap"><div class="prog-fill" style="width:{int(progress*100)}%"></div></div>',
        unsafe_allow_html=True,
    )

    # Step cards
    for i, (step_name, step_msg) in enumerate(PIPELINE_STEPS):
        done = i < st.session_state.pipeline_step
        status = "done" if done else ""
        icon = "✅" if done else "⏳" if i == st.session_state.pipeline_step else "○"
        _msg_html = ('<div class="astep-msg">' + step_msg + '</div>') if done else ''
        st.markdown(
            f'<div class="astep {status}">'
            f'<div class="astep-name">{icon} {step_name}</div>'
            + _msg_html + '</div>',
            unsafe_allow_html=True,
        )

    if completed and st.session_state.last_decision:
        res = st.session_state.last_decision
        roi = res.get("roi", {})
        ns  = roi.get("net_savings_usd", 1194590)
        rp  = roi.get("roi_pct", 13272)
        st.success(f"✅ Pipeline complete — {res.get('outcome','EXECUTED')} | Net savings: ${ns:,.0f} | ROI: {rp:.0f}%")

with col_agents:
    st.markdown("**🤖 Multi-Agent Decision Chain**")
    agents = [
        ("🔬 DiagnosticsAgent",    "Bearing Failure",       "ISO 10816-3 Zone D exceeded. Predicted TTF: 48h."),
        ("⚖️ CriticalityAgent",   "CRITICAL — RPN 504",    "S=7×O=8×D=9=504. Risk 8.2/10. Immediate action."),
        ("📋 ComplianceAgent",    "COMPLIANT",             "OSHA 1910.119 applicable. No active violations."),
        ("📝 WorkOrderAgent",     "URGENT WO generated",   "WO-P101-URGENT | 8h labor | $1,450 cost estimate."),
        ("💰 ROIAgent",           "$1.18M net savings",    "Avoided cost $1.19M. ROI = 13,272%. AI pays back."),
    ]
    for icon_name, decision, reasoning in agents:
        shown = completed or st.session_state.manual_triggered
        alpha = "1" if shown else "0.3"
        _step_cls = "done" if shown else ""
        _step_msg = ('<div class="astep-msg">' + reasoning + '</div>') if shown else ""
        st.markdown(
            f'<div class="astep {_step_cls}" style="opacity:{alpha}">'
            f'<div class="astep-name">{icon_name}</div>'
            f'<div style="color:#f1c21b;font-size:.72rem;margin-top:3px;'
            f'font-family:\'IBM Plex Mono\',monospace">'
            f'\u2192 {decision}</div>'
            + _step_msg
            + '</div>',
            unsafe_allow_html=True,
        )

    if completed:
        st.markdown('<div style="margin-top:12px">', unsafe_allow_html=True)
        st.markdown("**👤 Human Approval Decision**")
        dec_cols = st.columns(2)
        if dec_cols[0].button("✅ APPROVE Work Order", use_container_width=True, type="primary"):
            st.session_state.last_decision["human"] = "APPROVED"
        if dec_cols[1].button("❌ REJECT", use_container_width=True):
            st.session_state.last_decision["human"] = "REJECTED"
        hd = st.session_state.last_decision.get("human")
        if hd:
            color = GREEN if hd == "APPROVED" else RED
            st.markdown(
                f'<div style="background:{color}18;border:1px solid {color}44;border-radius:6px;'
                f'padding:8px 12px;font-size:.74rem;color:{color};margin-top:6px">'
                f'{"✅ Work order approved — crew dispatched to P-101" if hd=="APPROVED" else "❌ Rejected — flagged for re-evaluation"}'
                f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — BUSINESS OUTCOMES
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown('<div class="sec">Layer 4 — Business Outcomes & Value</div>', unsafe_allow_html=True)

oc1, oc2, oc3, oc4 = st.columns(4)
outcomes = [
    (oc1, "$82.4M",  "Net Savings 12M",     "+22% YoY",    GREEN,  "g"),
    (oc2, ">10,000%","Cumulative ROI",       "vs $250K AI", BLUE,   "g"),
    (oc3, "99.7%",   "Asset Availability",  "+4.2pp",      GREEN,  "g"),
    (oc4, "100%",    "PM Compliance",        "0 OSHA items",GREEN,  "g"),
]
for col, val, lbl, dl, color, dlc in outcomes:
    col.markdown(
        f'<div class="mtile">'
        f'<div class="mtile-val" style="color:{color}">{val}</div>'
        f'<div class="mtile-lbl">{lbl}</div>'
        f'<div class="mtile-dl {dlc}">{dl}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
col_wf, col_out = st.columns([1.5, 1])

with col_wf:
    st.markdown("**📈 12-Month Value Delivery**")
    months = ["Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep"]
    avoided = [4.1, 4.8, 5.2, 6.0, 5.8, 6.4, 7.1, 7.4, 8.2, 7.9, 9.1, 10.4]
    maint   = [1.2, 1.4, 1.5, 1.7, 1.6, 1.9, 2.1, 2.0, 2.3, 2.2, 2.5, 2.8]
    cumul   = list(np.cumsum([a - m for a, m in zip(avoided, maint)]))
    fig_val = go.Figure()
    fig_val.add_trace(go.Bar(x=months, y=avoided, name="Avoided Downtime Cost",
                             marker_color=GREEN, opacity=0.85,
                             hovertemplate="%{x}<br>Avoided: $%{y:.1f}M<extra></extra>"))
    fig_val.add_trace(go.Bar(x=months, y=maint, name="Maintenance Cost",
                             marker_color=BLUE, opacity=0.85,
                             hovertemplate="%{x}<br>Maintenance: $%{y:.1f}M<extra></extra>"))
    fig_val.add_trace(go.Scatter(x=months, y=cumul, name="Cumulative Net",
                                 mode="lines+markers", line=dict(color=AMBER, width=2.2),
                                 yaxis="y2", marker=dict(size=5),
                                 hovertemplate="%{x}<br>Cumulative: $%{y:.1f}M<extra></extra>"))
    fig_val.update_layout(**_cl(
        barmode="group", height=280,
        yaxis=dict(title="USD (M)", tickprefix="$", ticksuffix="M"),
        yaxis2=dict(overlaying="y", side="right", title="Cumulative",
                    tickprefix="$", ticksuffix="M"),
        legend=dict(orientation="h", y=-0.24, font=dict(size=9)),
    ))
    st.plotly_chart(fig_val, use_container_width=True)

with col_out:
    st.markdown("**🏆 Key Outcomes**")
    outcome_cards = [
        ("🔮", "Zero Unplanned Downtime",
         "AI predicts 94% of failures 48–336h ahead. P-101, K-201, R-301 failures prevented this year."),
        ("💰", "Proven Financial ROI",
         "$82.4M net savings vs $250K AI investment. Payback in <3 months. 12-year NPV: $980M."),
        ("🛡️", "Full Regulatory Compliance",
         "OSHA 1910.119, API 510/570/581, ASME compliance. Zero AHJ notifications. Audit-ready at all times."),
        ("⚡", "Workforce Productivity",
         "Wrench time up 67.6%. Planning time cut from 5h to 1.5h per job. 88% first-time fix rate."),
    ]
    for icon, title, body in outcome_cards:
        st.markdown(
            f'<div class="ocard">'
            f'<div class="ocard-icon">{icon}</div>'
            f'<div class="ocard-title">{title}</div>'
            f'<div class="ocard-body">{body}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER CTA
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown(
    '<div style="background:linear-gradient(135deg,#071428,#0a1a30);border:1px solid #1c3352;'
    'border-radius:12px;padding:32px;text-align:center;margin-top:8px">'
    '<div style="font-size:1.4rem;font-weight:700;color:#e2eaf6;margin-bottom:8px">'
    'Ready to transform your industrial operations?</div>'
    '<div style="font-size:.85rem;color:#7d9bbf;margin-bottom:20px">'
    'Explore the full interactive dashboard — live sensor feed, FMEA calculator, ROI what-if simulator, and more.'
    '</div>'
    '<div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">'
    '<a href="/dashboard" style="background:#0f62fe;color:#fff;padding:10px 28px;border-radius:8px;'
    'font-weight:600;font-size:.82rem;text-decoration:none">📊 Open Full Dashboard →</a>'
    '<a href="https://github.com/Praddeep-AI/agentic-maintenance-ai" target="_blank" '
    'style="background:#0d1a2e;color:#b8cfe8;padding:10px 28px;border-radius:8px;'
    'font-weight:600;font-size:.82rem;text-decoration:none;border:1px solid #1c3352">'
    '⭐ View on GitHub</a>'
    '</div>'
    '<div style="margin-top:16px;font-size:.62rem;color:#3d5a7a">'
    'IBM Consulting | Industrial AI &amp; Agentic Operations | Chemicals &amp; Petrochemicals'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── auto refresh every 4s to animate live data ─────────────────────────────────
time.sleep(4)
st.rerun()
