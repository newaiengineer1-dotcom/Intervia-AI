import json
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from agents import (
    CoachAgent,
    EvidenceAgent,
    GroqGateway,
    InterviewerAgent,
    ResearchAgent,
    StrategyAgent,
)
from db import init_db, save_session
from report import build_markdown_report, build_pdf_report
from utils import extract_uploaded_text, safe_clamp

st.set_page_config(
    page_title="Intervia AI — Interview Intelligence Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

CATEGORIES = [
    "Behavioral & Situational 🎭",
    "Technical & Role-Specific 💻",
    "HR & Screening Basics 🤝",
    "Leadership & Management 👔",
    "Case & Analytical Interviews 📊",
    "Competency & Skill-Based 🧠",
    "Reverse Interviewing — Questions for the Employer 🔍",
]
DURATIONS = {"30 Minutes": 30, "60 Minutes": 60, "120 Minutes": 120, "180 Minutes": 180}
TARGET_QUESTIONS = {30: 8, 60: 15, 120: 28, 180: 40}

st.markdown(
    """
    <style>
    :root {
        --bg:#050914; --panel:#0b1224; --panel-2:#0f1930; --line:#243454;
        --muted:#a9b7d0; --text:#f4f7ff; --accent:#8b6cff; --accent-2:#45d6ff;
        --good:#7cf2b4; --warn:#ffd27a; --danger:#ff8c9d;
    }
    .stApp { background:
        radial-gradient(circle at 78% -8%, rgba(139,108,255,.25), transparent 30%),
        radial-gradient(circle at 8% 18%, rgba(69,214,255,.10), transparent 24%),
        linear-gradient(180deg,#050914 0%,#07101f 100%);
    }
    [data-testid="stSidebar"] {
        background:rgba(5,9,20,.97); border-right:1px solid var(--line);
    }
    [data-testid="stSidebar"] * { color:var(--text); }
    .hero {
        padding:34px 38px; border:1px solid rgba(139,108,255,.30); border-radius:26px;
        background:linear-gradient(135deg,rgba(139,108,255,.18),rgba(12,20,39,.94) 55%,rgba(69,214,255,.08));
        box-shadow:0 24px 70px rgba(0,0,0,.34); margin-bottom:22px;
    }
    .eyebrow { color:#b9aaff; font-size:11px; font-weight:900; letter-spacing:.18em; text-transform:uppercase; }
    .hero h1 { color:var(--text); margin:8px 0 10px; font-size:42px; line-height:1.08; letter-spacing:-.03em; }
    .muted,.small { color:var(--muted)!important; }
    .card,.cockpit { padding:20px; border:1px solid var(--line); border-radius:20px; background:linear-gradient(180deg,rgba(15,25,48,.94),rgba(9,17,33,.94)); box-shadow:0 14px 40px rgba(0,0,0,.18); margin-bottom:14px; }
    .agent { display:flex; justify-content:space-between; gap:16px; align-items:center; padding:13px 0; border-bottom:1px solid rgba(36,52,84,.72); color:var(--text); }
    .agent:last-child { border-bottom:0; }
    .agent-name { font-weight:750; }
    .status { font-size:10px; font-weight:900; letter-spacing:.10em; padding:5px 9px; border-radius:999px; border:1px solid rgba(124,242,180,.28); color:var(--good); background:rgba(124,242,180,.08); }
    .status.active { color:#bcaeff; border-color:rgba(139,108,255,.35); background:rgba(139,108,255,.10); }
    .status.waiting { color:var(--warn); border-color:rgba(255,210,122,.30); background:rgba(255,210,122,.08); }
    .status.optional { color:#9db0cc; border-color:rgba(157,176,204,.25); background:rgba(157,176,204,.07); }
    .question { font-size:26px; line-height:1.38; font-weight:760; color:var(--text); padding:26px; border:1px solid rgba(139,108,255,.26); border-left:5px solid var(--accent); background:linear-gradient(135deg,#0b1429,#0b1222); border-radius:18px; box-shadow:0 16px 42px rgba(0,0,0,.20); }
    .category { display:inline-block; padding:7px 11px; border:1px solid #3b4f78; border-radius:999px; color:#e0e7f6; font-size:12px; background:#111c35; margin-bottom:10px; }
    .mode-box { padding:16px; border:1px solid #2b4068; border-radius:16px; background:#091326; }
    .cockpit-title { color:#f4f7ff; font-size:13px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; margin-bottom:7px; }
    div[data-testid="stButton"] > button { border-radius:12px; min-height:44px; font-weight:800; border:1px solid #34476f; }
    div[data-testid="stButton"] > button[kind="primary"] { box-shadow:0 10px 30px rgba(139,108,255,.22); }
    div[data-baseweb="tab-list"] { gap:6px; background:rgba(11,18,36,.75); padding:6px; border:1px solid var(--line); border-radius:14px; }
    button[data-baseweb="tab"] { color:#cbd6ea!important; border-radius:10px; }
    button[data-baseweb="tab"][aria-selected="true"] { color:#fff!important; background:linear-gradient(90deg,rgba(139,108,255,.22),rgba(69,214,255,.10)); }
    label, [data-testid="stWidgetLabel"] p { color:#eaf0fc!important; font-weight:650!important; }
    input, textarea { color:#f4f7ff!important; }
    .footer { margin-top:30px; padding:18px 20px; border-top:1px solid var(--line); color:#94a4bf; text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Ultra-premium visual layer: stronger hierarchy, dashboard rhythm and high-contrast controls.
st.markdown(
    """
    <style>
    .main .block-container { max-width: 1480px; padding-top: 1.6rem; padding-bottom: 3rem; }
    .hero { position:relative; overflow:hidden; min-height:220px; display:flex; flex-direction:column; justify-content:center; }
    .hero:after { content:""; position:absolute; width:340px; height:340px; right:-120px; top:-150px; border-radius:50%; background:radial-gradient(circle,rgba(69,214,255,.20),transparent 68%); pointer-events:none; }
    .hero h1 { font-size: clamp(34px, 4vw, 56px); max-width: 900px; }
    .hero .muted { max-width: 920px; font-size: 15px; line-height:1.65; }
    .ats-banner { display:flex; align-items:center; justify-content:space-between; gap:24px; margin:12px 0 18px; padding:20px 24px; border-radius:20px; border:1px solid rgba(69,214,255,.28); background:linear-gradient(100deg,rgba(69,214,255,.09),rgba(139,108,255,.13),rgba(12,20,39,.96)); box-shadow:0 18px 50px rgba(0,0,0,.22); }
    .ats-score { font-size:38px; line-height:1; font-weight:900; color:#ffffff; margin-top:6px; }
    .ats-score span { font-size:15px; color:#9fb0cc; margin-left:3px; }
    .stMetric { background:linear-gradient(145deg,rgba(15,25,48,.96),rgba(8,15,29,.96)); border:1px solid rgba(71,91,133,.42); padding:8px 10px; border-radius:16px; box-shadow:0 12px 30px rgba(0,0,0,.16); }
    [data-testid=stFileUploader] { background:rgba(12,21,40,.72); border:1px dashed #3b4f78; border-radius:16px; padding:8px; }
    textarea, input { border-radius:12px!important; }
    div[data-testid=stButton] > button:hover { transform:translateY(-1px); border-color:#6e83b0; box-shadow:0 12px 32px rgba(69,214,255,.10); }
    div[data-testid=stButton] > button[kind=primary] { background:linear-gradient(100deg,#7157e8,#4f7cff)!important; color:white!important; border:1px solid rgba(164,148,255,.65)!important; }
    .question { box-shadow:0 22px 60px rgba(0,0,0,.30); background:linear-gradient(135deg,rgba(19,32,61,.98),rgba(8,16,31,.98)); }
    .card { backdrop-filter: blur(14px); }
    .section-kicker { color:#7edfff; font-size:10px; font-weight:900; letter-spacing:.16em; text-transform:uppercase; }
    /* Ultra-HD cockpit layer: visual-only enhancements; Streamlit controls remain unchanged. */
    :root { --uhd-bg:#070B16; --uhd-bg2:#111827; --neon-p:#9b7cff; --neon-c:#4de1ff; }
    .stApp { background:
        radial-gradient(circle at 82% 0%, rgba(155,124,255,.20), transparent 28%),
        radial-gradient(circle at 0% 38%, rgba(77,225,255,.10), transparent 26%),
        linear-gradient(135deg,#070B16 0%,#0b1220 48%,#111827 100%);
    }
    .uhd-topbar { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:10px 14px; margin:0 0 14px; border:1px solid rgba(151,167,204,.18); border-radius:16px; background:rgba(7,11,22,.72); backdrop-filter:blur(18px); box-shadow:0 14px 45px rgba(0,0,0,.24); }
    .uhd-brand { display:flex; align-items:center; gap:10px; font-weight:900; color:#f7f9ff; letter-spacing:.02em; }
    .uhd-avatar { width:34px; height:34px; border-radius:11px; display:grid; place-items:center; background:linear-gradient(135deg,#8b6cff,#4de1ff); color:#08101f; box-shadow:0 0 24px rgba(139,108,255,.35); }
    .uhd-pill { display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px; border:1px solid rgba(151,167,204,.22); background:rgba(17,24,39,.72); color:#cbd7ee; font-size:10px; font-weight:850; letter-spacing:.06em; }
    .uhd-pill.live { color:#86f5bd; border-color:rgba(124,242,180,.30); }
    .uhd-pulse { width:7px; height:7px; border-radius:50%; background:#5cf0b0; box-shadow:0 0 0 0 rgba(92,240,176,.55); animation:uhdPulse 1.8s infinite; }
    @keyframes uhdPulse { 0%{box-shadow:0 0 0 0 rgba(92,240,176,.5)} 70%{box-shadow:0 0 0 8px rgba(92,240,176,0)} 100%{box-shadow:0 0 0 0 rgba(92,240,176,0)} }
    .uhd-card { transition:transform .22s ease, box-shadow .22s ease, border-color .22s ease; border:1px solid rgba(143,161,201,.16); border-radius:22px; background:linear-gradient(145deg,rgba(17,24,39,.78),rgba(8,13,26,.82)); backdrop-filter:blur(22px); box-shadow:0 24px 70px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.035); }
    .uhd-stepper { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin:0 0 18px; }
    .uhd-step { min-height:52px; padding:10px 12px; border:1px solid rgba(143,161,201,.16); border-radius:14px; background:rgba(11,18,32,.68); color:#8f9fba; font-size:10px; font-weight:850; }
    .uhd-step.active { color:#fff; border-color:rgba(139,108,255,.55); background:linear-gradient(135deg,rgba(139,108,255,.25),rgba(69,214,255,.08)); box-shadow:0 0 28px rgba(139,108,255,.13); }
    .uhd-step.done { color:#9af7c7; border-color:rgba(124,242,180,.25); }
    .uhd-wave { height:84px; display:flex; align-items:center; justify-content:center; gap:5px; padding:12px 18px; border-radius:18px; background:linear-gradient(180deg,rgba(22,31,56,.86),rgba(8,14,28,.9)); border:1px solid rgba(103,126,177,.18); overflow:hidden; }
    .uhd-wave i { width:5px; border-radius:99px; background:linear-gradient(180deg,#4de1ff,#9b7cff); box-shadow:0 0 13px rgba(77,225,255,.28); animation:uhdWave 1.1s ease-in-out infinite; }
    .uhd-wave i:nth-child(1){height:18px;animation-delay:-.9s}.uhd-wave i:nth-child(2){height:34px;animation-delay:-.7s}.uhd-wave i:nth-child(3){height:56px;animation-delay:-.5s}.uhd-wave i:nth-child(4){height:30px;animation-delay:-.3s}.uhd-wave i:nth-child(5){height:68px;animation-delay:-.1s}.uhd-wave i:nth-child(6){height:42px}.uhd-wave i:nth-child(7){height:62px;animation-delay:-.2s}.uhd-wave i:nth-child(8){height:28px;animation-delay:-.4s}.uhd-wave i:nth-child(9){height:50px;animation-delay:-.6s}.uhd-wave i:nth-child(10){height:22px;animation-delay:-.8s}
    @keyframes uhdWave { 0%,100%{transform:scaleY(.62);opacity:.58} 50%{transform:scaleY(1.16);opacity:1} }
    .uhd-card:hover { transform:translateY(-1px); box-shadow:0 28px 80px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.045); border-color:rgba(139,108,255,.24); }
    .uhd-metric { padding:13px 15px; border:1px solid rgba(143,161,201,.15); border-radius:16px; background:rgba(10,17,31,.72); }
    .uhd-metric .label { color:#8292ae; font-size:9px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
    .uhd-metric .value { margin-top:4px; color:#f8fbff; font-size:22px; font-weight:900; }
    .uhd-metric .hint { color:#70e8ff; font-size:10px; font-weight:800; }
    .uhd-transcript { padding:16px 18px; border:1px solid rgba(143,161,201,.14); border-radius:18px; background:rgba(5,10,21,.72); color:#dce5f7; line-height:1.72; }
    .uhd-filler { color:#0a1020; background:#ffd166; border-radius:5px; padding:1px 4px; font-weight:900; }
    .uhd-cta { border-radius:14px; background:linear-gradient(105deg,#7959ef,#4c8dff 62%,#4de1ff); color:white; padding:12px 16px; font-weight:900; box-shadow:0 12px 36px rgba(98,91,240,.25); }
    @media (max-width: 900px) { .uhd-stepper{grid-template-columns:1fr 1fr}.uhd-topbar{flex-wrap:wrap}.hero{padding:26px 24px} }
    </style>
    """,
    unsafe_allow_html=True,
)


# Final accessibility/visibility layer. This is visual-only and does not alter workflow state.
st.markdown(
    """
    <style>
    :root {
      --ui-bg:#070B16;
      --ui-bg2:#111827;
      --ui-panel:#0F172A;
      --ui-panel2:#111C31;
      --ui-border:#334155;
      --ui-border-strong:#52658A;
      --ui-text:#F8FAFC;
      --ui-text-2:#D7E0EF;
      --ui-muted:#A9B7CC;
      --ui-purple:#9B7CFF;
      --ui-purple-strong:#7C5CFF;
      --ui-cyan:#4DE1FF;
      --ui-green:#55E6A5;
      --ui-yellow:#FFD166;
      --ui-red:#FF718B;
    }

    html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .stApp { color:var(--ui-text); }
    .main .block-container { max-width:1500px !important; padding-left:28px !important; padding-right:28px !important; }

    /* Sidebar: stronger hierarchy and clear field surfaces. */
    [data-testid="stSidebar"] {
      background:linear-gradient(180deg,#090E1A 0%,#0B1220 58%,#0D1628 100%) !important;
      border-right:1px solid rgba(77,225,255,.12) !important;
    }
    [data-testid="stSidebar"] .block-container { padding:20px 16px 28px !important; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color:#FFFFFF !important; }
    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small { color:#AFC0D8 !important; }

    /* Text inputs and text areas: never allow low-contrast gray-on-gray controls. */
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
      color:#F8FAFC !important;
      -webkit-text-fill-color:#F8FAFC !important;
      background:#0B1324 !important;
      border:1px solid #3B4C6B !important;
      border-radius:12px !important;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.025), 0 6px 18px rgba(0,0,0,.12) !important;
    }
    div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stTextArea"] textarea::placeholder { color:#7F91AD !important; opacity:1 !important; }
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stTextArea"] textarea:focus {
      border-color:#8B7CFF !important;
      box-shadow:0 0 0 2px rgba(139,124,255,.18), 0 0 24px rgba(77,225,255,.08) !important;
    }

    /* Select boxes / multiselects. */
    div[data-baseweb="select"] > div {
      background:#0B1324 !important;
      border:1px solid #3B4C6B !important;
      color:#F8FAFC !important;
      border-radius:12px !important;
      min-height:44px !important;
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input { color:#F8FAFC !important; }
    div[data-baseweb="select"] svg { fill:#BFD0E7 !important; }
    [data-baseweb="tag"] { background:#31236F !important; border:1px solid #8B7CFF !important; color:#FFFFFF !important; border-radius:8px !important; }
    [role="listbox"] { background:#0D172A !important; border:1px solid #425579 !important; box-shadow:0 20px 50px rgba(0,0,0,.45) !important; }
    [role="option"] { color:#EAF1FB !important; background:#0D172A !important; }
    [role="option"]:hover, [role="option"][aria-selected="true"] { background:#211B48 !important; color:#FFFFFF !important; }

    /* Radio/checkbox controls. */
    div[data-testid="stRadio"] label, div[data-testid="stCheckbox"] label { color:#EAF1FB !important; }
    div[data-testid="stRadio"] label p, div[data-testid="stCheckbox"] label p { color:#EAF1FB !important; font-weight:700 !important; }
    div[data-testid="stRadio"] [role="radiogroup"] { gap:8px !important; }
    div[data-testid="stRadio"] [role="radio"] { background:#0D172A !important; border:1px solid #3B4C6B !important; border-radius:10px !important; padding:8px 12px !important; }
    div[data-testid="stRadio"] [role="radio"][aria-checked="true"] { background:linear-gradient(100deg,#30236E,#153B50) !important; border-color:#8B7CFF !important; box-shadow:0 0 18px rgba(139,124,255,.15) !important; }

    /* Buttons: primary = purple/cyan, secondary = graphite with visible border. */
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button {
      min-height:44px !important;
      border-radius:12px !important;
      border:1px solid #405274 !important;
      color:#F8FAFC !important;
      background:linear-gradient(180deg,#162238,#101A2D) !important;
      font-weight:850 !important;
      transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
    }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
      transform:translateY(-1px) !important;
      border-color:#6E83B0 !important;
      box-shadow:0 12px 30px rgba(0,0,0,.24), 0 0 20px rgba(77,225,255,.08) !important;
    }
    div[data-testid="stButton"] > button[kind="primary"] {
      background:linear-gradient(105deg,#7759F4 0%,#6378FF 52%,#35CFEF 100%) !important;
      border-color:#A99AFF !important;
      box-shadow:0 12px 34px rgba(102,91,240,.28), 0 0 24px rgba(77,225,255,.10) !important;
    }
    div[data-testid="stButton"] > button[kind="primary"] p { color:#FFFFFF !important; }

    /* Uploaders, audio and camera controls. */
    [data-testid="stFileUploader"] {
      background:linear-gradient(145deg,rgba(17,28,49,.94),rgba(9,16,30,.94)) !important;
      border:1px dashed #52698F !important;
      border-radius:16px !important;
      padding:10px !important;
    }
    [data-testid="stFileUploader"] section { background:transparent !important; }
    [data-testid="stFileUploader"] small, [data-testid="stFileUploader"] span { color:#B9C7DA !important; }
    [data-testid="stAudioInput"] { background:#0B1324 !important; border:1px solid #3B4C6B !important; border-radius:16px !important; padding:8px !important; }

    /* Metrics, progress and status messages. */
    [data-testid="stMetric"] { background:linear-gradient(145deg,#101A2D,#0B1324) !important; border:1px solid #334563 !important; border-radius:16px !important; padding:13px 15px !important; box-shadow:0 12px 28px rgba(0,0,0,.18) !important; }
    [data-testid="stMetricLabel"] p { color:#AFC0D8 !important; font-weight:800 !important; }
    [data-testid="stMetricValue"] { color:#FFFFFF !important; font-weight:900 !important; }
    [data-testid="stMetricDelta"] { color:#6EE7B7 !important; }
    [data-testid="stProgressBar"] > div > div > div { background:linear-gradient(90deg,#8B6CFF,#4DE1FF) !important; }
    [data-testid="stAlert"] { border-radius:14px !important; border:1px solid #3B4C6B !important; background:#101A2D !important; color:#EAF1FB !important; }

    /* Expanders / tables / charts. */
    [data-testid="stExpander"] { background:rgba(11,19,36,.82) !important; border:1px solid #334563 !important; border-radius:16px !important; }
    [data-testid="stExpander"] summary p { color:#F8FAFC !important; font-weight:850 !important; }
    [data-testid="stDataFrame"] { border:1px solid #334563 !important; border-radius:14px !important; overflow:hidden !important; }

    /* Tabs: explicit active/inactive states. */
    div[data-baseweb="tab-list"] { background:#0B1324 !important; border:1px solid #334563 !important; border-radius:15px !important; padding:6px !important; }
    button[data-baseweb="tab"] { color:#9FB0C8 !important; background:transparent !important; border-radius:10px !important; font-weight:850 !important; }
    button[data-baseweb="tab"] p { color:inherit !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color:#FFFFFF !important; background:linear-gradient(105deg,rgba(124,92,255,.42),rgba(77,225,255,.14)) !important; border:1px solid rgba(139,124,255,.55) !important; box-shadow:0 0 22px rgba(139,124,255,.12) !important; }

    /* Headings and helper text. */
    h1,h2,h3,h4,h5,h6 { color:#F8FAFC !important; }
    label, [data-testid="stWidgetLabel"] p { color:#EAF1FB !important; font-weight:750 !important; }
    .stCaption, [data-testid="stCaptionContainer"] p { color:#A9B7CC !important; }
    hr { border-color:#273852 !important; }

    /* Strong focus ring for keyboard accessibility. */
    button:focus-visible, input:focus-visible, textarea:focus-visible, [role="radio"]:focus-visible { outline:2px solid #4DE1FF !important; outline-offset:2px !important; }

    /* Respect reduced-motion preferences. */
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation-duration:.001ms !important; animation-iteration-count:1 !important; transition-duration:.001ms !important; }
    }
    @media (max-width: 900px) {
      .main .block-container { padding-left:16px !important; padding-right:16px !important; }
      .uhd-stepper { grid-template-columns:1fr 1fr !important; }
      .hero { padding:24px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Icon-first cockpit layer: compact navigation, status telemetry, and premium command surfaces.
st.markdown(
    """
    <style>
    .ix-command { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin:0 0 18px; }
    .ix-command a { text-decoration:none !important; color:#DDE7F7 !important; min-height:62px; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:4px; border:1px solid rgba(143,161,201,.18); border-radius:16px; background:linear-gradient(145deg,rgba(17,28,49,.86),rgba(8,14,28,.88)); backdrop-filter:blur(18px); box-shadow:0 14px 34px rgba(0,0,0,.18); transition:all .2s ease; }
    .ix-command a:hover { transform:translateY(-2px); border-color:rgba(77,225,255,.55); box-shadow:0 0 28px rgba(77,225,255,.10),0 18px 40px rgba(0,0,0,.24); }
    .ix-icon { font-size:20px; line-height:1; }
    .ix-label { font-size:9px; font-weight:900; letter-spacing:.11em; text-transform:uppercase; color:#AFC0D8; }
    .ix-telemetry { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin:0 0 18px; }
    .ix-tile { min-height:78px; padding:12px 14px; border:1px solid rgba(143,161,201,.16); border-radius:17px; background:linear-gradient(145deg,rgba(17,24,39,.82),rgba(8,13,26,.86)); backdrop-filter:blur(18px); box-shadow:0 18px 45px rgba(0,0,0,.20); }
    .ix-tile .k { color:#8FA3C0; font-size:9px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
    .ix-tile .v { color:#F8FAFC; font-size:17px; font-weight:900; margin-top:5px; }
    .ix-tile .s { color:#65E3FF; font-size:9px; font-weight:800; margin-top:2px; }
    .ix-command-status { display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; padding:10px 13px; margin:-6px 0 18px; border:1px solid rgba(77,225,255,.14); border-radius:14px; background:rgba(7,12,24,.62); color:#9FB0C8; font-size:10px; }
    .ix-priority { padding:13px 15px; border-radius:16px; border:1px solid rgba(255,209,102,.25); background:linear-gradient(135deg,rgba(255,209,102,.08),rgba(17,24,39,.84)); }
    .ix-priority b { color:#FFF1C4; }
    .ix-chiprow { display:flex; gap:7px; flex-wrap:wrap; margin:8px 0 4px; }
    .ix-chip { padding:6px 9px; border-radius:999px; border:1px solid rgba(143,161,201,.20); background:rgba(17,28,49,.72); color:#D9E4F5; font-size:9px; font-weight:850; }
    .ix-chip.good { color:#9AF7C7; border-color:rgba(85,230,165,.28); }
    .ix-chip.focus { color:#D8CBFF; border-color:rgba(155,124,255,.34); }
    @media (max-width:900px){ .ix-command{grid-template-columns:repeat(2,1fr)} .ix-telemetry{grid-template-columns:repeat(2,1fr)} }
    @media (max-width:520px){ .ix-command{grid-template-columns:1fr 1fr} .ix-telemetry{grid-template-columns:1fr 1fr} }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_speech_controls(text: str, key: str, title: str, language: str, autoplay: bool = False):
    """Browser-native question playback. It automatically ends/cancels when the utterance ends."""
    payload = json.dumps(text or "", ensure_ascii=False)
    lang_payload = json.dumps(language or "en-US")
    safe_key = re.sub(r"[^A-Za-z0-9_]", "_", key)
    auto_delay = 350 if autoplay else 999999
    components.html(
        f"""
        <div style="font-family:Arial,sans-serif;padding:8px 0;">
          <div style="color:#91a2c0;font-size:12px;font-weight:700;margin-bottom:7px;">🔊 {escape(title)}</div>
          <button id="play_{safe_key}" style="border:1px solid #33466f;background:#151f3b;color:#fff;border-radius:10px;padding:9px 14px;cursor:pointer;margin-right:6px;">▶ Play</button>
          <button id="stop_{safe_key}" style="border:1px solid #33466f;background:#0d1830;color:#c9d4ea;border-radius:10px;padding:9px 14px;cursor:pointer;">■ Stop</button>
          <span id="status_{safe_key}" style="color:#91a2c0;font-size:12px;margin-left:8px;"></span>
        </div>
        <script>
        const text_{safe_key} = {payload};
        const lang_{safe_key} = {lang_payload};
        const play_{safe_key} = document.getElementById('play_{safe_key}');
        const stop_{safe_key} = document.getElementById('stop_{safe_key}');
        const status_{safe_key} = document.getElementById('status_{safe_key}');
        let utterance_{safe_key} = null;
        function stopSpeech_{safe_key}(label='Stopped') {{
          if ('speechSynthesis' in window) window.speechSynthesis.cancel();
          utterance_{safe_key} = null;
          status_{safe_key}.textContent = label;
        }}
        function speak_{safe_key}() {{
          if (!('speechSynthesis' in window)) {{ status_{safe_key}.textContent='Browser speech is not supported.'; return; }}
          stopSpeech_{safe_key}('');
          utterance_{safe_key} = new SpeechSynthesisUtterance(text_{safe_key});
          utterance_{safe_key}.lang = lang_{safe_key};
          utterance_{safe_key}.rate = 0.96;
          utterance_{safe_key}.pitch = 1.0;
          utterance_{safe_key}.onstart = () => status_{safe_key}.textContent='Speaking…';
          utterance_{safe_key}.onend = () => {{ utterance_{safe_key}=null; status_{safe_key}.textContent='Question finished'; }};
          utterance_{safe_key}.onerror = () => {{ utterance_{safe_key}=null; status_{safe_key}.textContent='Speech playback failed'; }};
          window.speechSynthesis.speak(utterance_{safe_key});
        }}
        play_{safe_key}.onclick = speak_{safe_key};
        stop_{safe_key}.onclick = () => stopSpeech_{safe_key}();
        window.addEventListener('beforeunload', () => stopSpeech_{safe_key}(''));
        setTimeout(() => {{ if ({str(autoplay).lower()}) speak_{safe_key}(); }}, {auto_delay});
        </script>
        """,
        height=78,
        scrolling=False,
    )


def render_timer(started_at: float, duration_minutes: int):
    remaining = max(0, int(duration_minutes * 60 - (time.time() - started_at)))
    components.html(
        f"""
        <div style="padding:8px 0;text-align:right;font-family:Arial,sans-serif;">
          <span style="color:#91a2c0;font-size:12px;">SESSION TIME REMAINING</span>
          <div id="timer" style="font-size:24px;font-weight:800;color:#e8edff;">--:--</div>
        </div>
        <script>
        let remaining = {remaining};
        const el = document.getElementById('timer');
        function tick() {{
          const m = Math.floor(Math.max(0, remaining) / 60);
          const s = Math.max(0, remaining) % 60;
          el.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
          if (remaining <= 0) el.textContent = '00:00 — TIME';
          remaining -= 1;
        }}
        tick(); setInterval(tick, 1000);
        </script>
        """,
        height=70,
        scrolling=False,
    )


def duration_state(started_at: float, duration_minutes: int):
    elapsed = max(0.0, time.time() - started_at)
    remaining = max(0.0, duration_minutes * 60 - elapsed)
    return elapsed, remaining, remaining <= 0


def question_target(duration_minutes: int, elapsed_seconds: float, completed: int) -> int:
    base = TARGET_QUESTIONS[duration_minutes]
    if elapsed_seconds <= 0:
        return base
    # Faster answers allow more questions; slower answers naturally reduce the target.
    avg_turn = elapsed_seconds / max(1, completed)
    projected = int((duration_minutes * 60) / max(avg_turn, 120))
    return max(3, min(base * 2, max(base, projected)))


def speech_metrics(text: str, estimated_seconds: float | None = None):
    words = re.findall(r"\b[\w']+\b", text or "")
    filler_list = ["um", "uh", "erm", "like", "you know", "basically", "actually", "sort of", "kind of"]
    lowered = (text or "").lower()
    fillers = sum(len(re.findall(r"\b" + re.escape(f) + r"\b", lowered)) for f in filler_list)
    words_count = len(words)
    seconds = estimated_seconds or max(10, words_count / 2.3) if words_count else 0
    wpm = round(words_count / (seconds / 60), 1) if seconds else 0
    return {"words": words_count, "filler_words": fillers, "estimated_seconds": round(seconds, 1), "words_per_minute": wpm}


def highlight_filler_words(text: str) -> str:
    """Return safe HTML with common speech fillers visually highlighted."""
    safe = escape(text or "")
    pattern = r"\b(um|uh|erm|like|basically|actually|you know|sort of|kind of)\b"
    return re.sub(pattern, r'<span class="uhd-filler">\1</span>', safe, flags=re.IGNORECASE)


def render_ultra_stepper(turns: list[dict], started: bool, evidence_ready: bool):
    """Visual-only interview lifecycle indicator; it does not change workflow state."""
    if turns:
        stage = 4
    elif started:
        stage = 3
    elif evidence_ready:
        stage = 2
    else:
        stage = 1
    labels = ["Evidence", "Design", "Adaptive Q&A", "Live Coaching", "Session Report"]
    items = []
    for idx, label in enumerate(labels, start=1):
        cls = "active" if idx == stage else ("done" if idx < stage else "")
        icon = "✓" if idx < stage else str(idx)
        state = "ACTIVE" if idx == stage else ("READY" if idx < stage else "NEXT")
        items.append(f'<div class="uhd-step {cls}"><b>{icon} · {escape(label)}</b><br><span>{state}</span></div>')
    st.markdown('<div class="uhd-stepper">' + ''.join(items) + '</div>', unsafe_allow_html=True)


def render_ultra_topbar(model_label: str, started: bool, session_id: str):
    state = "LIVE SESSION" if started else "READY WORKSPACE"
    dot = '<span class="uhd-pulse"></span>' if started else '<span style="width:7px;height:7px;border-radius:50%;background:#8fa1c9;display:inline-block"></span>'
    st.markdown(
        f'''<div class="uhd-topbar"><div class="uhd-brand"><span class="uhd-avatar">✦</span><span>INTERVIA AI <small style="color:#7edfff;display:block;font-size:8px;letter-spacing:.18em">STUDIO COCKPIT</small></span></div><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap"><span class="uhd-pill">SESSION · {escape((session_id or "--------")[:8])}</span><span class="uhd-pill">MODEL · {escape(model_label)}</span><span class="uhd-pill live">{dot}{state}</span></div></div>''',
        unsafe_allow_html=True,
    )


def render_command_deck():
    """Icon-first in-page navigation. Links are visual/navigation only and never alter session state."""
    items = [
        ("🎙️", "Live", "#live-studio"),
        ("🧬", "Evidence", "#evidence-lab"),
        ("🧠", "Coach", "#live-coaching"),
        ("📊", "Insights", "#session-insights"),
        ("📑", "Report", "#session-report"),
    ]
    html = '<nav class="ix-command" aria-label="Intervia Studio navigation">'
    for icon, label, href in items:
        html += f'<a href="{href}"><span class="ix-icon">{icon}</span><span class="ix-label">{label}</span></a>'
    html += '</nav>'
    st.markdown(html, unsafe_allow_html=True)


def render_session_telemetry(evidence: dict | None, turns: list[dict], started: bool, model_label: str):
    ats = (evidence or {}).get("ats_readiness", {})
    voice_count = sum(1 for t in turns if t.get("answer_mode") == "voice")
    autosave = "SYNCED" if turns else ("READY" if evidence else "WAITING")
    model_short = (model_label or "AUTO").replace("openai/", "")
    cards = [
        ("🧬", "EVIDENCE", "READY" if evidence else "WAITING", "CV + JD grounding"),
        ("⚡", "ENGINE", "LIVE" if started else "READY", model_short[:24]),
        ("💾", "AUTOSAVE", autosave, "Session state"),
        ("🎙️", "VOICE", str(voice_count), "Voice answers"),
        ("🧾", "ATS", f"{ats.get('score', 0)}/100", "Readiness estimate"),
    ]
    cols = st.columns(5)
    for col, (icon, key, value, sub) in zip(cols, cards):
        col.markdown(f'<div class="ix-tile"><div class="k">{icon} {key}</div><div class="v">{escape(value)}</div><div class="s">{escape(sub)}</div></div>', unsafe_allow_html=True)


def render_quality_insights(turns: list[dict]):
    """Deterministic session analytics derived only from completed coaching outputs."""
    scored = [t for t in turns if t.get("feedback")]
    if not scored:
        return
    values = [float(t.get("feedback", {}).get("overall", 0) or 0) for t in scored]
    dimensions = ["technical", "relevance", "evidence", "communication", "structure", "confidence"]
    dim_avg = {}
    for d in dimensions:
        vals = [float(t.get("feedback", {}).get("scores", {}).get(d, 0) or 0) for t in scored]
        dim_avg[d.title()] = round(sum(vals) / max(1, len(vals)), 1)
    trend = {"Question": list(range(1, len(values) + 1)), "Overall": [round(v, 1) for v in values]}
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### 📈")
        st.line_chart(trend, x="Question", y="Overall", height=220)
    with right:
        st.markdown("#### 🎯")
        dim_chart = {"Dimension": list(dim_avg.keys()), "Score": list(dim_avg.values())}
        st.bar_chart(dim_chart, x="Dimension", y="Score", height=220)


def render_question_map(turns: list[dict]):
    if not turns:
        return
    chips = []
    for idx, turn in enumerate(turns, 1):
        score = turn.get("feedback", {}).get("overall", 0)
        cat = (turn.get("category", "General") or "General").split(" ")[0]
        cls = "good" if float(score or 0) >= 75 else ("focus" if float(score or 0) >= 60 else "")
        chips.append(f'<span class="ix-chip {cls}">Q{idx} · {escape(cat)} · {score}</span>')
    st.markdown("<div class='ix-chiprow'>" + "".join(chips) + "</div>", unsafe_allow_html=True)


def render_ultra_waveform():
    bars = ''.join('<i></i>' for _ in range(10))
    st.markdown(f'<div class="uhd-wave" aria-label="Live audio waveform">{bars}</div>', unsafe_allow_html=True)


def render_speech_analytics(turns: list[dict]):
    voice_turns = [t for t in turns if t.get("answer_mode") == "voice"]
    if not voice_turns:
        return
    rows = []
    for idx, turn in enumerate(voice_turns, start=1):
        sm = turn.get("feedback", {}).get("speech_metrics", {}) or {}
        rows.append({"Turn": idx, "WPM": sm.get("words_per_minute") or 0, "Fillers": sm.get("filler_words") or 0, "Words": sm.get("words") or 0})
    st.markdown("#### Real-time speech analytics")
    c1, c2, c3 = st.columns(3)
    avg_wpm = round(sum(r["WPM"] for r in rows) / max(1, len(rows)), 1)
    avg_fillers = round(sum(r["Fillers"] for r in rows) / max(1, len(rows)), 1)
    c1.metric("Average pace", f"{avg_wpm} WPM")
    c2.metric("Average fillers", f"{avg_fillers}")
    c3.metric("Voice answers", len(rows))
    chart_data = {"Turn": [r["Turn"] for r in rows], "WPM": [r["WPM"] for r in rows], "Fillers": [r["Fillers"] for r in rows]}
    st.bar_chart(chart_data, x="Turn", y=["WPM", "Fillers"], height=190)


def build_session_snapshot(turns: list[dict], evidence: dict | None, categories: list[str], model_label: str = "") -> dict:
    """Derive a compact, reportable readiness snapshot from existing session outputs."""
    scored = [t.get("feedback", {}).get("scores", {}) for t in turns if t.get("feedback")]
    overall_values = [float(t.get("feedback", {}).get("overall", 0) or 0) for t in turns if t.get("feedback")]
    overall = round(sum(overall_values) / len(overall_values), 1) if overall_values else 0
    dimension_names = ["technical", "relevance", "evidence", "communication", "structure", "confidence"]
    dimension_avgs = {}
    for name in dimension_names:
        vals = [float(s.get(name, 0) or 0) for s in scored]
        dimension_avgs[name] = round(sum(vals) / len(vals), 1) if vals else 0
    weakest = min(dimension_avgs, key=dimension_avgs.get) if scored else "Not available"
    ats_score = float((evidence or {}).get("ats_readiness", {}).get("score", 0) or 0)
    covered = len({t.get("category", "General") for t in turns})
    target = max(1, len(categories or CATEGORIES))
    category_scores = {}
    for turn in turns:
        cat = turn.get("category", "General")
        category_scores.setdefault(cat, []).append(float(turn.get("feedback", {}).get("overall", 0) or 0))
    category_averages = {k: round(sum(v) / len(v), 1) for k, v in category_scores.items() if v}
    completeness = 0
    if evidence:
        completeness += 35
    if turns:
        completeness += 35
    if all(t.get("feedback") for t in turns) and turns:
        completeness += 20
    if ats_score > 0:
        completeness += 10
    priority = weakest.title() if weakest != "Not available" else "Complete evidence pack first"
    return {
        "overall": overall,
        "ats_readiness": round(ats_score, 1),
        "questions_completed": len(turns),
        "category_coverage": f"{covered}/{target}",
        "weakest_dimension": priority,
        "dimension_scores": dimension_avgs,
        "category_scores": category_averages,
        "score_trend": [round(v, 1) for v in overall_values],
        "report_completeness": min(100, completeness),
        "session_health": "LIVE" if turns else ("EVIDENCE READY" if evidence else "READY"),
        "model": model_label or "Automatic model discovery",
        "report_ready": bool(turns and evidence),
    }


def render_session_snapshot(snapshot: dict):
    st.markdown('<div id="session-insights"></div><h3>📊</h3>', unsafe_allow_html=True)
    cols = st.columns(5)
    cols[0].metric("🎯 Interview", f"{snapshot['overall']}/100")
    cols[1].metric("🧾 ATS", f"{snapshot['ats_readiness']}/100")
    cols[2].metric("❓ Questions", snapshot["questions_completed"])
    cols[3].metric("🧩 Coverage", snapshot["category_coverage"])
    cols[4].metric("🔎 Focus", snapshot["weakest_dimension"])
    status = "REPORT READY" if snapshot["report_ready"] else "REPORT IN PROGRESS"
    st.markdown(f"<div class='uhd-card' style='padding:13px 16px;margin:8px 0 18px'><span class='uhd-pill live'><span class='uhd-pulse'></span>{status}</span><span class='small' style='margin-left:10px'>Health: {escape(snapshot.get('session_health','READY'))} · Completeness: {snapshot.get('report_completeness',0)}% · Engine: {escape(snapshot.get('model','Automatic model discovery'))}</span></div>", unsafe_allow_html=True)
    if snapshot.get("weakest_dimension") and snapshot.get("questions_completed"):
        st.markdown(f"<div class='ix-priority'>💡 <b>Coaching priority:</b> strengthen <b>{escape(snapshot['weakest_dimension'])}</b> in the next practice cycle. This priority is derived from the lowest completed evaluation dimension.</div>", unsafe_allow_html=True)



init_db()

DEFAULT_SESSION_STATE = {
    "session_id": None,
    "evidence": None,
    "research": None,
    "turns": [],
    "question": None,
    "started": False,
    "started_at": None,
    "session_duration": 30,
    "question_mode": "Text Questions",
    "answer_mode": "⌨️ Type Answers",
    "categories": CATEGORIES[:],
    "company": "",
    "company_track": "",
    "camera_enabled": False,
    "groq_model": "",
    "reset_notice": False,
    "cv_filename": "",
    "jd_filename": "",
    "mode_value": "Mixed",
    "speech_language": "English (US)",
    "answer_length": "Standard",
    "degraded_mode": False,
    "question_source": "AI",
    "question_error": "",
}

for key, default in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = uuid.uuid4().hex if key == "session_id" else (default[:] if isinstance(default, list) else default)


def deterministic_first_question(target_role: str, mode: str, categories: list[str] | None) -> dict:
    """Safe local first-question fallback so a transient model issue never leaves the session blank."""
    selected = (categories or CATEGORIES)[0]
    category_key = selected.lower()
    if "behavior" in category_key:
        question = f"Tell me about a relevant {target_role} challenge you handled, what you personally did, and what measurable result followed."
    elif "case" in category_key or "analytical" in category_key:
        question = f"For a {target_role} project, how would you structure your approach to diagnosing a difficult problem and choosing between competing solutions?"
    elif "leadership" in category_key:
        question = f"Describe a situation relevant to {target_role} where you had to align people around a difficult technical decision. What did you do and what was the outcome?"
    elif "hr" in category_key:
        question = f"Why are you interested in this {target_role} opportunity, and which parts of your experience best prepare you for it?"
    else:
        question = f"Walk me through one technically significant project relevant to {target_role}: what problem did you solve, what was your approach, and what was the measurable result?"
    return {"category": selected, "question": question}


def reset_interview_session():
    """Clear only the active interview and its widgets; keep the API key and app configuration intact."""
    dynamic_prefixes = ("answer_input_", "answer_audio_", "camera_", "question_")
    for key in list(st.session_state.keys()):
        if key in {
            "cv", "jd", "target_role_input", "company_input", "mode_input",
            "categories_input", "duration_input", "question_mode_input",
            "answer_mode_input", "research_input", "camera_enabled_input",
            "speech_language_input", "answer_length_input", "company_track_input",
            "jd_text_input", "confirm_reset_input",
        } or key.startswith(dynamic_prefixes):
            del st.session_state[key]

    for key, default in DEFAULT_SESSION_STATE.items():
        if key == "session_id":
            st.session_state[key] = uuid.uuid4().hex
        elif isinstance(default, list):
            st.session_state[key] = default[:]
        elif key == "reset_notice":
            st.session_state[key] = True
        else:
            st.session_state[key] = default


def configured_secret(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default) or "").strip()


with st.sidebar:
    st.markdown("## ◈")
    st.caption("INTERVIA AI · STUDIO")
    api_key = st.text_input("🔐", type="password", value=configured_secret("GROQ_API_KEY"), key="api_key_input", help="Groq API key")
    target_role = st.text_input("🎯", value="Senior Renewable Energy Engineer", disabled=st.session_state.started, key="target_role_input", help="Target role")
    company = st.text_input("🏢", value=st.session_state.company, disabled=st.session_state.started, key="company_input", help="Company / employer (optional)")

    st.markdown("### 🎛️")
    setup_tab, new_tab = st.tabs(["🎛️", "🆕"])
    with setup_tab:
        mode_map = {"🧩": "Mixed", "💻": "Technical", "🎭": "Behavioral", "📊": "Case / Situational", "🤝": "HR / Screening", "👔": "Leadership"}
        mode_icon = st.selectbox(
            "🎛️", list(mode_map),
            index=list(mode_map.values()).index(st.session_state.get("mode_value", "Mixed")),
            disabled=st.session_state.started,
            help="Interview mode", key="mode_input"
        )
        mode = mode_map[mode_icon]

        category_map = {
            "🎭": CATEGORIES[0], "💻": CATEGORIES[1], "🤝": CATEGORIES[2],
            "👔": CATEGORIES[3], "📊": CATEGORIES[4], "🧠": CATEGORIES[5], "🔍": CATEGORIES[6],
        }
        reverse_category = {v: k for k, v in category_map.items()}
        selected_category_icons = st.multiselect(
            "🧩", list(category_map),
            default=[reverse_category.get(c) for c in st.session_state.categories if c in reverse_category],
            disabled=st.session_state.started,
            help="Interview categories", key="categories_input"
        )
        categories = [category_map[i] for i in selected_category_icons]

    with new_tab:
        st.markdown("**🆕**")
        st.caption("Reset the active session without changing the API key or deployment.")
        if st.session_state.started or st.session_state.turns or st.session_state.evidence:
            st.markdown("<div class='card'><b>●</b><br><span class='small'>Active session · reset creates a fresh session ID.</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card'><b>○</b><br><span class='small'>Ready · no active interview.</span></div>", unsafe_allow_html=True)
        confirm_reset = st.checkbox("✓", key="confirm_reset_input", help="Confirm clearing the current interview session")
        if st.button("↻", type="primary", use_container_width=True, disabled=not confirm_reset, key="reset_sidebar_button", help="Reset & start a new interview"):
            reset_interview_session()
            st.rerun()

    duration_options = {"◴ 30′": 30, "◷ 60′": 60, "◶ 120′": 120, "◵ 180′": 180}
    current_duration_icon = next((k for k, v in duration_options.items() if v == st.session_state.session_duration), "◴ 30′")
    duration_icon = st.selectbox("⏱️", list(duration_options), index=list(duration_options).index(current_duration_icon), disabled=st.session_state.started, key="duration_input", help="Session duration")
    duration_minutes = duration_options[duration_icon]
    duration_label = next(k for k, v in DURATIONS.items() if v == duration_minutes)

    question_map = {"📝": "Text Questions", "🔊": "Audio Questions"}
    question_icon = st.radio("🔊", list(question_map), index=0 if st.session_state.question_mode == "Text Questions" else 1, disabled=st.session_state.started, horizontal=True, help="Question format", key="question_mode_input")
    question_mode = question_map[question_icon]

    answer_map = {"⌨️": "⌨️ Type Answers", "🎙️": "🎙️ Speak Answers"}
    answer_icon = st.radio("🎙️", list(answer_map), index=0 if st.session_state.answer_mode.startswith("⌨") else 1, disabled=st.session_state.started, horizontal=True, help="Answer format", key="answer_mode_input")
    answer_mode = answer_map[answer_icon]

    use_research = st.checkbox("🔎", value=False, disabled=st.session_state.started, help="Company / role analysis", key="research_input")
    camera_enabled = st.checkbox("📷", value=st.session_state.camera_enabled, disabled=st.session_state.started, help="Camera presentation snapshot", key="camera_enabled_input")
    language_map = {"🇺🇸": "English (US)", "🇬🇧": "English (UK)"}
    language_icon = st.selectbox("🗣️", list(language_map), index=0 if st.session_state.get("speech_language", "English (US)") == "English (US)" else 1, disabled=st.session_state.started, key="speech_language_input", help="Question voice")
    speech_language = language_map[language_icon]
    speech_locale = "en-US" if speech_language == "English (US)" else "en-GB"

    length_map = {"⚡": "Short", "◼️": "Standard", "🧠": "Detailed"}
    length_icon = st.selectbox("📝", list(length_map), index=list(length_map.values()).index(st.session_state.get("answer_length", "Standard")), disabled=st.session_state.started, key="answer_length_input", help="AI practice-answer length")
    answer_length = length_map[length_icon]

    st.divider()
    st.caption("🔒 Secrets stay in Streamlit Secrets · ⚙️ Session controls lock after start.")

    if not st.session_state.started:
        st.session_state.session_duration = duration_minutes
        st.session_state.question_mode = question_mode
        st.session_state.answer_mode = answer_mode
        st.session_state.categories = categories or CATEGORIES[:]
        st.session_state.company = company
        st.session_state.mode_value = mode
        st.session_state.speech_language = speech_language
        st.session_state.answer_length = answer_length
        st.session_state.company_track = ""
        st.session_state.camera_enabled = camera_enabled

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Intervia AI · Interview Intelligence Platform · Intervia Studio · Ultra HD Cockpit</div>
      <h1>◈</h1>
      <div class="muted">Choose question and answer modalities once, select a session length and interview categories, then Intervia Studio automatically adapts the Q&A pace to the remaining time.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
render_ultra_topbar(st.session_state.get("groq_model") or "AUTO DISCOVERY", st.session_state.started, st.session_state.session_id)
render_ultra_stepper(st.session_state.turns, st.session_state.started, bool(st.session_state.evidence))
render_command_deck()
render_session_telemetry(st.session_state.evidence, st.session_state.turns, st.session_state.started, st.session_state.get("groq_model") or "AUTO DISCOVERY")

status_col, reset_col = st.columns([4, 1])
with status_col:
    if st.session_state.get("reset_notice"):
        st.success("✨ New interview session is ready. Your previous session state has been cleared.")
        st.session_state.reset_notice = False
    elif st.session_state.started:
        st.info("Interview session active · use **New Interview Session** when you want a clean reset.")
    else:
        st.caption("Session workspace ready · your API key is preserved when you start a new interview.")
with reset_col:
    if st.button("↻", use_container_width=True, key="reset_dashboard_button", help="New Interview — clear the current session and return to a fresh workspace."):
        reset_interview_session()
        st.rerun()

if not st.session_state.started:
    st.info("Before starting: configure **Interview categories and Interview mode**, choose **Text or Audio Questions**, **Type or Speak Answers**, and select your practice session duration.")

left, right = st.columns([1.35, 1])
with left:
    st.markdown('<div id="evidence-lab"></div><h3>🧬</h3>', unsafe_allow_html=True)
    cv_file = st.file_uploader("CV / Resume", type=["pdf", "docx", "txt"], key="cv")
    jd_file = st.file_uploader("Job Description", type=["pdf", "docx", "txt"], key="jd")
    jd_text = st.text_area("Or paste the job description", height=150, placeholder="Paste the JD here if you do not have a file.", key="jd_text_input")
    company_track = st.text_area("Optional company-specific question context", height=90, placeholder="Paste publicly sourced interview themes/questions or a company-specific question bank here. Keep it factual and non-confidential.", disabled=st.session_state.started, key="company_track_input")

    if st.button("🧬", type="primary", use_container_width=True, disabled=st.session_state.started):
        if not api_key:
            st.error("Enter a Groq API key first.")
        elif not cv_file:
            st.error("Upload a CV / Resume.")
        elif not (jd_file or jd_text.strip()):
            st.error("Upload or paste the Job Description.")
        else:
            st.session_state.company_track = company_track
            st.session_state.cv_filename = getattr(cv_file, "name", "CV / Resume")
            st.session_state.jd_filename = getattr(jd_file, "name", "Pasted Job Description") if jd_file else "Pasted Job Description"
            cv_text = extract_uploaded_text(cv_file)
            final_jd = extract_uploaded_text(jd_file) if jd_file else jd_text
            st.session_state.evidence = EvidenceAgent().build(
                cv_text=safe_clamp(cv_text, 14000),
                jd_text=safe_clamp(final_jd, 12000),
                target_role=target_role,
                industry="Not specified — grounded in CV/JD and role context",
                cv_filename=st.session_state.cv_filename,
            )
            st.session_state.research = None
            st.session_state.turns = []
            st.session_state.question = None
            st.session_state.started = False
            st.session_state.started_at = None
            if use_research:
                try:
                    gateway = GroqGateway(api_key)
                    st.session_state.research = ResearchAgent(gateway).run(
                        target_role, "Not specified — grounded in CV/JD and role context", safe_clamp(final_jd, 6000), company=company, company_track=company_track
                    )
                except Exception:
                    st.warning("Company / role analysis is temporarily unavailable. The interview will continue using the CV and Job Description.")
            st.success("Evidence pack created. Candidate evidence, JD requirements and role analysis remain separate.")

with right:
    st.markdown("### 🤖")
    for name, status in [
        ("Evidence Intelligence", "READY" if st.session_state.evidence else "WAITING"),
        ("Career & Market Research", "READY" if st.session_state.research else ("OPTIONAL" if not use_research else "WAITING")),
        ("Interview Strategy", "ACTIVE" if st.session_state.started else "READY"),
        ("Intervia Intelligence Engine", "ACTIVE" if st.session_state.question else "READY"),
        ("Performance Coach", "READY"),
    ]:
        st.markdown(f'<div class="agent"><span>{name}</span><span class="status">{status}</span></div>', unsafe_allow_html=True)
    st.markdown("### ⚙️")
    model_label = st.session_state.get("groq_model") or "Automatic model discovery"
    st.markdown(f"<div class='card'><b>{duration_label}</b><br><span class='small'>Mode: {escape(mode)} · Categories: {len(categories or CATEGORIES)}</span><br><span class='small'>Questions: {escape(question_mode)} · Answers: {escape(answer_mode)}</span><br><span class='small'>Groq model: {escape(model_label)}</span><br><span class='small'>Target pacing: approximately {TARGET_QUESTIONS[duration_minutes]} core questions, automatically adjusted for answer speed and remaining time.</span></div>", unsafe_allow_html=True)

if st.session_state.evidence:
    ev = st.session_state.evidence
    ats = ev.get("ats_readiness", {})
    st.markdown("### 🧠")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ATS Readiness", f"{ats.get('score', 0)}/100")
    c2.metric("JD Keyword Match", f"{ats.get('keyword_match_score', 0)}/100")
    c3.metric("Candidate Facts", len(ev.get("candidate_facts", [])))
    c4.metric("Skill Gaps", len(ev.get("gaps", [])))
    st.markdown(
        f"<div class='ats-banner'><div><span class='eyebrow'>ATS RESUME CHECK</span><div class='ats-score'>{ats.get('score', 0)}<span>/100</span></div></div><div><b>{escape(ats.get('label', 'ATS readiness estimate'))}</b><div class='small'>{escape(ats.get('method', 'Deterministic CV/JD readiness estimate.'))}</div></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='uhd-card' style='padding:16px 18px;margin-bottom:16px'><div style='display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap'><div><div class='section-kicker'>Candidate readiness telemetry</div><b style='font-size:16px'>ATS structure · keywords · evidence · measurable impact</b></div><span class='uhd-pill live'><span class='uhd-pulse'></span> ANALYSIS COMPLETE</span></div></div>",
        unsafe_allow_html=True,
    )
    ev_left, ev_right = st.columns(2)
    with ev_left:
        st.markdown("**🟢**")
        for item in ats.get("strengths", [])[:6]:
            st.markdown(f"• {escape(item)}")
        st.markdown("**🔤**")
        st.caption(", ".join(ats.get("detected_headings", [])) or "No conventional headings detected")
    with ev_right:
        st.markdown("**💡**")
        for item in ats.get("improvements", [])[:6]:
            st.markdown(f"• {escape(item)}")
        st.markdown("**🔎**")
        st.caption(", ".join(ats.get("missing_keywords", [])[:30]) or "No major keyword gaps detected")
    with st.expander("View complete grounding data"):
        st.write("**Candidate evidence**", ev.get("candidate_facts", []))
        st.write("**JD requirements**", ev.get("jd_requirements", []))
        st.write("**Matched skills / terms**", ev.get("matches", []))
        st.write("**Gaps / unknowns**", ev.get("gaps", []))
        st.write("**ATS matched keywords**", ats.get("matched_keywords", []))

    if not st.session_state.started:
        if st.button("🚀", type="primary", use_container_width=True, key="start_interview_button", help="Start the interview session"): 
            if not categories:
                st.error("🧩 Select at least one category.")
            elif not api_key:
                st.error("🔐 Groq API key is required.")
            else:
                now = time.time()
                try:
                    gateway = GroqGateway(api_key)
                    selected_model = gateway.selected_model()
                    strategy = StrategyAgent()
                    interviewer = InterviewerAgent(gateway)
                    elapsed, remaining, _ = duration_state(now, duration_minutes)
                    target_count = question_target(duration_minutes, elapsed, 0)
                    plan = strategy.plan([], mode, duration_label, ev, categories=categories, remaining_minutes=round(remaining / 60, 1), target_questions=target_count)
                    q = interviewer.ask_question(
                        ev,
                        st.session_state.research,
                        plan,
                        target_role,
                        "Not specified — grounded in CV/JD and role context",
                        mode,
                        company=company,
                    )
                    if not isinstance(q, str) or not q.strip():
                        raise RuntimeError("The interview engine returned an empty question.")
                    source = "AI"
                    error_message = ""
                except Exception as exc:
                    # Never leave the user on a blank interview screen. Start with a deterministic,
                    # role-grounded question and clearly mark the session as degraded until Groq recovers.
                    selected_model = st.session_state.get("groq_model") or "AUTO DISCOVERY"
                    q = deterministic_first_question(target_role, mode, categories)
                    source = "LOCAL FALLBACK"
                    error_message = GroqGateway.friendly_error(exc)

                st.session_state.groq_model = selected_model
                st.session_state.started_at = now
                st.session_state.question = q
                st.session_state.started = True
                st.session_state.degraded_mode = source != "AI"
                st.session_state.question_source = source
                st.session_state.question_error = error_message
                st.session_state.session_duration = duration_minutes
                st.session_state.question_mode = question_mode
                st.session_state.answer_mode = answer_mode
                st.session_state.categories = categories
                st.session_state.company = company
                st.session_state.camera_enabled = camera_enabled
                st.rerun()

if st.session_state.started and st.session_state.question:
    st.markdown("---")
    st.markdown('<div id="live-studio"></div><h3>🎙️</h3>', unsafe_allow_html=True)
    elapsed, remaining, expired = duration_state(st.session_state.started_at, st.session_state.session_duration)
    turn_no = len(st.session_state.turns) + 1
    target_count = question_target(st.session_state.session_duration, elapsed, len(st.session_state.turns))
    progress = min(1.0, len(st.session_state.turns) / max(1, target_count))
    top1, top2, top3 = st.columns([1.6, 1, 1])
    with top1:
        st.progress(progress, text=f"Question {turn_no} · adaptive target {target_count}")
    with top2:
        st.metric("Elapsed", f"{int(elapsed//60):02d}:{int(elapsed%60):02d}")
    with top3:
        render_timer(st.session_state.started_at, st.session_state.session_duration)

    if expired:
        st.warning("⏱️ Your selected practice session time has ended. Your report is ready below.")
        st.session_state.question = None
    else:
        if st.session_state.get("degraded_mode"):
            st.warning("⚠️ ENGINE FALLBACK · The session is active with a local role-grounded question. Live AI coaching will resume when Groq is available.")
        else:
            st.success("🟢 ENGINE LIVE · Adaptive question generated successfully.")

        q_obj = st.session_state.question if isinstance(st.session_state.question, dict) else {"category": "General", "question": str(st.session_state.question)}
        question_text = q_obj["question"].strip()
        category = q_obj.get("category", "General")
        st.markdown(f"<span class='category'>{escape(category)}</span>", unsafe_allow_html=True)
        st.markdown(f'<div class="question">{escape(question_text)}</div>', unsafe_allow_html=True)
        render_speech_controls(
            question_text,
            f"question_{turn_no}",
            "Generated interview question",
            speech_locale,
            autoplay=(st.session_state.question_mode == "Audio Questions"),
        )
        if st.session_state.question_mode == "Audio Questions":
            st.caption("Audio mode: the question is spoken automatically when available; playback stops automatically when the question finishes. Browser autoplay restrictions may require pressing Play once.")

        st.markdown("#### ✍️")
        st.caption(f"Answer mode locked for this session: **{st.session_state.answer_mode}**")
        if st.session_state.answer_mode == "🎙️ Speak Answers":
            render_ultra_waveform()
            st.caption("Live audio visualization · transcription and coaching are generated after submission.")
        answer = ""
        voice_transcript = ""
        audio = None
        if st.session_state.answer_mode == "⌨️ Type Answers":
            answer = st.text_area("Type your answer", key=f"answer_input_{turn_no}", height=190, placeholder="Answer as if you were in the real interview.")
        else:
            audio = st.audio_input("🎙️ Record your answer", sample_rate=16000, key=f"answer_audio_{turn_no}")
            st.caption("Speak naturally. Submit the recording when you finish; Whisper will transcribe it before coaching.")

        camera = None
        if st.session_state.camera_enabled:
            camera = st.camera_input("Optional camera snapshot for presentation-cue feedback", key=f"camera_{turn_no}")
            st.caption("MVP camera analysis is a snapshot, not continuous video. It evaluates only observable framing/posture/camera cues; it does not infer emotions, personality, health or mental state.")

        submit = st.button("🚀", type="primary", use_container_width=True)
        if submit:
            elapsed_now, remaining_now, expired_now = duration_state(st.session_state.started_at, st.session_state.session_duration)
            if expired_now:
                st.warning("The session time has ended. Finish with the report below.")
                st.session_state.question = None
                st.rerun()
            elif not api_key:
                st.error("Groq API key is required.")
            else:
                gateway = GroqGateway(api_key)
                if st.session_state.answer_mode == "🎙️ Speak Answers" and audio is not None:
                    try:
                        voice_transcript = gateway.transcribe(audio.getvalue(), getattr(audio, "name", "answer.wav")).strip()
                        answer = voice_transcript
                    except Exception as exc:
                        st.error("Voice transcription failed. Please record again or use text.")
                else:
                    answer = (answer or "").strip()

                if not answer:
                    st.error("Provide an answer before submitting.")
                else:
                    coach = CoachAgent(gateway)
                    result = coach.evaluate(
                        question=question_text,
                        answer=answer,
                        evidence=st.session_state.evidence,
                        target_role=target_role,
                        mode=mode,
                        answer_length=answer_length,
                    )
                    metrics = speech_metrics(answer) if voice_transcript else {"words": len(answer.split()), "filler_words": None, "estimated_seconds": None, "words_per_minute": None}
                    camera_feedback = None
                    if camera is not None:
                        try:
                            camera_feedback = gateway.analyze_camera(camera.getvalue(), getattr(camera, "type", "image/jpeg"))
                        except Exception as exc:
                            camera_feedback = {"available": False, "message": "Camera analysis is unavailable for this snapshot."}
                    result["speech_metrics"] = metrics
                    result["presentation_cues"] = camera_feedback
                    st.session_state.turns.append({
                        "question": question_text,
                        "category": category,
                        "answer": answer,
                        "answer_mode": "voice" if voice_transcript else "text",
                        "voice_transcript": voice_transcript,
                        "feedback": result,
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "elapsed_seconds": round(elapsed_now, 1),
                    })
                    save_session(st.session_state.session_id, target_role, "Not specified — grounded in CV/JD and role context", st.session_state.turns)

                    # Generate next question only if time remains.
                    elapsed_after, remaining_after, expired_after = duration_state(st.session_state.started_at, st.session_state.session_duration)
                    if expired_after:
                        st.session_state.question = None
                    else:
                        strategy = StrategyAgent()
                        target_count = question_target(st.session_state.session_duration, elapsed_after, len(st.session_state.turns))
                        plan = strategy.plan(
                            st.session_state.turns,
                            mode,
                            duration_label,
                            st.session_state.evidence,
                            categories=st.session_state.categories,
                            remaining_minutes=round(remaining_after / 60, 1),
                            target_questions=target_count,
                        )
                        interviewer = InterviewerAgent(gateway)
                        try:
                            st.session_state.question = interviewer.ask_question(
                                st.session_state.evidence,
                                st.session_state.research,
                                plan,
                                target_role,
                                "Not specified — grounded in CV/JD and role context",
                                mode,
                                company=company,
                            )
                        except Exception as exc:
                            st.session_state.question = deterministic_first_question(target_role, mode, st.session_state.categories)
                            st.session_state.degraded_mode = True
                            st.session_state.question_source = "LOCAL FALLBACK"
                            st.session_state.question_error = GroqGateway.friendly_error(exc)
                    st.rerun()

    if st.session_state.turns:
        latest = st.session_state.turns[-1]["feedback"]
        st.markdown('<div id="live-coaching"></div><h3>🧠</h3>', unsafe_allow_html=True)
        cols = st.columns(6)
        for col, key, label in zip(cols, ["technical", "relevance", "evidence", "communication", "structure", "confidence"], ["Technical", "Relevance", "Evidence", "Communication", "Structure", "Confidence"]):
            col.metric(label, latest.get("scores", {}).get(key, 0))
        st.metric("Overall", latest.get("overall", 0))
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**Strengths**", latest.get("strengths", []))
        st.write("**Missing / improve**", latest.get("missing_points", []))
        st.write("**Verification notes**", latest.get("verification_notes", []))
        st.write("**Practice answer**", latest.get("practice_answer", ""))
        st.write("**Next improvement**", latest.get("next_improvement", ""))
        sm = latest.get("speech_metrics", {})
        if sm:
            st.write("**Speech analytics**", sm)
        if latest.get("presentation_cues"):
            st.write("**Presentation cues**", latest["presentation_cues"])
        latest_answer = st.session_state.turns[-1].get("answer", "")
        if st.session_state.turns[-1].get("answer_mode") == "voice" and latest_answer:
            st.markdown("**Live transcription highlights**")
            st.markdown(f'<div class="uhd-transcript">{highlight_filler_words(latest_answer)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        render_speech_analytics(st.session_state.turns)

        st.markdown("### 🧩")
        category_scores = defaultdict(list)
        for t in st.session_state.turns:
            category_scores[t.get("category", "General")].append(t.get("feedback", {}).get("overall", 0))
        readiness_cols = st.columns(min(4, max(1, len(category_scores))))
        for idx, (cat, vals) in enumerate(category_scores.items()):
            readiness_cols[idx % len(readiness_cols)].metric(cat.split(" ")[0], round(sum(vals)/len(vals)))

        snapshot = build_session_snapshot(st.session_state.turns, st.session_state.evidence, st.session_state.categories, st.session_state.get("groq_model", ""))
        render_session_snapshot(snapshot)
        render_quality_insights(st.session_state.turns)
        st.markdown("#### 🗺️")
        render_question_map(st.session_state.turns)

        st.markdown('<div id="session-report"></div><h3>📑</h3>', unsafe_allow_html=True)
        report_kwargs = dict(
            session_snapshot=snapshot,
            target_role=target_role,
            industry="Not specified — grounded in CV/JD and role context",
            mode=mode,
            turns=st.session_state.turns,
            evidence=st.session_state.evidence,
            company=company,
            duration_minutes=duration_minutes,
            categories=st.session_state.categories,
            question_mode=question_mode,
            answer_mode=answer_mode,
            use_research=use_research,
            camera_enabled=camera_enabled,
            speech_language=speech_language,
            answer_length=answer_length,
            company_track=st.session_state.company_track,
            session_id=st.session_state.session_id,
            started_at=st.session_state.started_at,
            groq_model=st.session_state.get("groq_model", ""),
            research=st.session_state.research,
            cv_filename=st.session_state.get("cv_filename", ""),
            jd_filename=st.session_state.get("jd_filename", ""),
        )
        md = build_markdown_report(**report_kwargs)
        pdf = build_pdf_report(**report_kwargs)
        st.download_button("⬇️", md, file_name="intervia_report.md", mime="text/markdown")
        st.download_button("📑", pdf, file_name="intervia_report.pdf", mime="application/pdf")


st.markdown(
    "<div class='footer'>Intervia AI · Interview Intelligence Platform · Intervia Studio · Start a new session anytime without changing your deployment or Groq secret.</div>",
    unsafe_allow_html=True,
)
