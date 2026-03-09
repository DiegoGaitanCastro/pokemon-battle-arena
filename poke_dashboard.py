# 1. SETUP & CONFIGURATION

import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import random
import pandas as pd
import plotly.express as px

import base64
import time
import textwrap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging

# Silence verbose HTTP/connection logs that sometimes appear in Streamlit UI during heavy fetches
for logger_name in ("urllib3", "requests", "asyncio"):
    logging.getLogger(logger_name).setLevel(logging.WARNING)
# Also raise Streamlit's logger threshold a bit (optional)
logging.getLogger("streamlit").setLevel(logging.WARNING)

APP_DIR = Path(__file__).resolve().parent  # folder where app.py lives

def load_image(filename: str):
    candidates = [
        APP_DIR / filename,
        APP_DIR / "Images" / filename,
        APP_DIR / "images" / filename,
        Path(filename),  # if user passes an absolute path
    ]

    for p in candidates:
        try:
            if p.is_file():
                return str(p)
        except Exception:
            pass

    return None

def img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    
def get_asset_b64(filename: str) -> str:
    """Loads an image/gif from app folder/Images and returns base64 string (or '')."""
    path = load_image(filename)
    if not path:
        return ""
    try:
        return img_to_base64(path)  # works for PNG/GIF/JPG
    except Exception:
        return ""

def fullscreen_loader_html(pikachu_b64: str, text: str = "Loading…", opaque: bool = False) -> str:
    pikachu_tag = ""
    if pikachu_b64:
        pikachu_tag = f'<img class="loader-pika" src="data:image/gif;base64,{pikachu_b64}" alt="Loading" />'

    # ✅ Opaque only when requested (cold start)
    bg_alpha = 0.94 if opaque else 0.55   # <- tweak warm splash opacity here

    html = f"""
    <style>
      .app-loader {{
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0,0,0,{bg_alpha});
        backdrop-filter: blur(6px);
      }}

      .app-loader-inner {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 18px;
        text-align: center;
        padding: 24px;
      }}

      .loader-pika {{
        width: 220px;
        height: auto;
        image-rendering: pixelated;
        filter: drop-shadow(0 18px 50px rgba(0,0,0,0.65));
      }}

      .loader-text {{
        font-size: 2.4rem;
        font-weight: 1000;
        letter-spacing: 0.06em;
        color: var(--app-text, #fff);
      }}
    </style>

    <div class="app-loader">
      <div class="app-loader-inner">
        {pikachu_tag}
        <div class="loader-text">{text}</div>
      </div>
    </div>
    """
    return textwrap.dedent(html).strip()

def get_backgrounds_b64_jpg_only() -> list[str]:
    """
    Loads ONLY .jpg images from ./Images for the cold loader slideshow.
    Returns a list of base64 strings (no mime prefix).
    """
    img_dir = APP_DIR / "Images"
    if not img_dir.exists():
        return []

    # ONLY .jpg (and .JPG) — nothing else
    files = [
        p for p in img_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".jpg"
    ]

    # Stable order (optional)
    files = sorted(files, key=lambda p: p.name.lower())

    b64s: list[str] = []
    for p in files:
        try:
            b64s.append(img_to_base64(str(p)))
        except Exception:
            pass
    return b64s


def cold_slideshow_loader_html(
    bg_b64_list: list[str],
    footer_text: str = "Caching them all…",
    switch_every_ms: int = 3000,
    fade_ms: int = 1200,
) -> str:
    """
    Fullscreen loader overlay (REAL fullscreen) with CSS-only slideshow.
    Works in Streamlit because it uses st.markdown injection (no iframe),
    and avoids JS entirely.
    """

    if not bg_b64_list:
        pikachu_b64_fallback = get_asset_b64("pikachu-running-loading.gif")
        return fullscreen_loader_html(pikachu_b64_fallback, text="", opaque=True)

    # Build data URLs
    urls = [f"data:image/jpeg;base64,{b}" for b in bg_b64_list]

    # Randomize starting order so it doesn't always begin the same
    start = random.randrange(len(urls))
    urls = urls[start:] + urls[:start]

    n = len(urls)
    total_ms = max(1, n * switch_every_ms)

    # Keyframes tuned for a nice crossfade
    # Each layer fades in, stays, then fades out; offset by animation-delay
    html_layers = []
    for i, u in enumerate(urls):
        delay = i * switch_every_ms
        html_layers.append(
            f"""<div class="cold-bg-layer" style="
                    background-image:url('{u}');
                    animation-delay:{delay}ms;
                "></div>"""
        )

    footer_html = f"""
      <div class="cold-footer">
        <span class="cold-dots">{footer_text}</span>
      </div>
    """ if footer_text.strip() else ""

    html = f"""
    <style>
      .cold-loader {{
        position: fixed;
        inset: 0;
        z-index: 999999;
        overflow: hidden;
        background: #000;
      }}

      .cold-bg-layer {{
        position: absolute;
        inset: 0;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        transform: scale(1.03);
        opacity: 0;
        animation: coldFade {total_ms}ms infinite;
        will-change: opacity, transform;
      }}

      @keyframes coldFade {{
        0%   {{ opacity: 0; }}
        8%   {{ opacity: 1; }}
        30%  {{ opacity: 1; }}
        42%  {{ opacity: 0; }}
        100% {{ opacity: 0; }}
      }}

      .cold-overlay {{
        position: absolute;
        inset: 0;
        background:
          radial-gradient(900px 420px at 50% 38%, rgba(0,0,0,0.10), rgba(0,0,0,0.45)),
          linear-gradient(180deg, rgba(0,0,0,0.10), rgba(0,0,0,0.55));
        backdrop-filter: blur(1px);
      }}

      .cold-footer {{
        position: absolute;
        left: 50%;
        bottom: 42px;
        transform: translateX(-50%);
        font-size: 1.6rem;
        font-weight: 1000;
        letter-spacing: 0.05em;
        color: #fff;
        opacity: 0.98;
        text-shadow: 0 12px 40px rgba(0,0,0,0.7);
        pointer-events: none;
        white-space: nowrap;
      }}

      .cold-dots::after {{
        content: "";
        display: inline-block;
        width: 1.4em;
        text-align: left;
        animation: dots 1.2s steps(4, end) infinite;
      }}

      @keyframes dots {{
        0%   {{ content: ""; }}
        25%  {{ content: "."; }}
        50%  {{ content: ".."; }}
        75%  {{ content: "..."; }}
        100% {{ content: ""; }}
      }}
    </style>

    <div class="cold-loader">
      {''.join(html_layers)}
      <div class="cold-overlay"></div>
      {footer_html}
    </div>
    """
    return textwrap.dedent(html).strip()

TYPE_COLORS = {
    "Normal": "#A8A878", "Fire": "#F08030", "Water": "#6890F0", "Electric": "#F8D030",
    "Grass": "#78C850", "Ice": "#98D8D8", "Fighting": "#C03028", "Poison": "#A040A0",
    "Ground": "#E0C068", "Flying": "#A890F0", "Psychic": "#F85888", "Bug": "#A8B820",
    "Rock": "#B8A038", "Ghost": "#705898", "Dragon": "#7038F8", "Dark": "#705848",
    "Steel": "#B8B8D0", "Fairy": "#EE99AC"
}

# --- Shared constants (avoid duplication) ---
TYPE_OPTIONS = list(TYPE_COLORS.keys())
CLASS_OPTIONS = ["Legendary", "Mythical", "Baby", "Mega", "Battle-only", "Default", "Gmax"]

# Used in multiple places (index building + classification)
BATTLE_ONLY_MARKERS = ["-battle", "-totem", "-school", "-zen", "-mode", "-blade", "-busted", "-hangry"]

def type_chip_html(type_name: str) -> str:
    """Colored chip for a Pokemon type (Fire/Water/etc) with ALWAYS white text."""
    col = TYPE_COLORS.get(type_name, "#808080")
    return (
        f'<span class="micro typechip" '
        f'style="background:{col}; color:#FFFFFF; border: 1px solid rgba(255,255,255,0.18);">'
        f'{type_name}</span>'
    )

st.set_page_config(
    page_title="Pokémon Combat Simulator", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>

/* =========================
   GLOBAL FONT SIZE BOOST
   ========================= */

html, body, [class*="st-"], [data-testid="stAppViewContainer"]{
  font-size: 18px !important;   /* main global size (try 18–20) */
  line-height: 1.35 !important;
}

/* Widget labels (multiselect, selectbox, checkbox, text_input labels, etc.) */
label, label span, div[data-testid="stWidgetLabel"] *{
  font-size: 1.05rem !important;   /* slightly larger than base */
  font-weight: 800 !important;
}

/* Inputs themselves (typed text + selected chips) */
input, textarea, [data-baseweb="select"] *{
  font-size: 1.05rem !important;
}

/* Dropdown menu options (when opened) */
div[role="listbox"] *{
  font-size: 1.05rem !important;
}

/* Checkbox text */
div[data-testid="stCheckbox"] label p{
  font-size: 1.05rem !important;
}

/* Buttons (except your custom epic battle button which already has its own size) */
div[data-testid="stButton"] > button{
  font-size: 1.1rem !important;
}

/* Dataframe/table text */
div[data-testid="stDataFrame"] *{
  font-size: 1.0rem !important;
}

/* Streamlit markdown paragraphs (your st.markdown text) */
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li{
  font-size: 1.05rem !important;
}

/* ====== REAL CARD WRAPPER FOR STREAMLIT BLOCKS ====== */
.card-anchor {
  height: 0px;
  margin: 0;
  padding: 0;
}

/* Style the Streamlit block that comes right after the anchor */
.card-anchor + div[data-testid="stVerticalBlockBorderWrapper"]{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  padding: 14px 16px 16px 16px;
  margin: 14px 0 16px 0;
}

/* Reduce spacing inside that card */
.card-anchor + div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] > div{
  margin-bottom: 0.35rem;
}

/* Header bar inside card */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 12px;
}

.section-header .title {
  font-size: 1.2rem;
  font-weight: 900;
  letter-spacing: 0.02em;
  color: var(--app-text);
}

/* Centered button row helper */
.center-btn-row {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}            

.micro.typechip{
  background: #444;              /* overridden inline */
  border: none;                  /* overridden inline */
  box-shadow: 0 6px 18px rgba(0,0,0,0.25);
}            

/* =========================
   UPGRADED SELECT SECTION UI
   ========================= */

.select-hero {
  border-radius: 20px;
  padding: 18px 18px;
  margin: 12px 0 18px 0;
  border: 1px solid rgba(255,255,255,0.10);
  background:
    radial-gradient(1200px 220px at 15% 0%, rgba(124,77,255,0.18), transparent 55%),
    radial-gradient(900px 240px at 85% 0%, rgba(255,106,106,0.16), transparent 55%),
    rgba(255,255,255,0.03);
  box-shadow: 0 18px 60px rgba(0,0,0,0.35);
}

.select-hero-top {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.select-title {
  font-size: 1.8rem;
  font-weight: 1000;
  letter-spacing: 0.04em;
  color: var(--app-text);
  margin: 0;
}

.select-subtitle {
  margin: 4px 0 0 0;
  color: var(--app-text-soft);
  font-size: 1.05rem;
  font-weight: 500;
}

.select-badges {
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.pill {
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.05);
  color: var(--app-text);
  font-weight: 900;
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}

.pill strong { font-weight: 1000; }

.pill.purple {
  background: rgba(124,77,255,0.14);
  border-color: rgba(124,77,255,0.30);
}

.pill.red {
  background: rgba(255,106,106,0.12);
  border-color: rgba(255,106,106,0.28);
}

.pill.green {
  background: rgba(0,230,118,0.11);
  border-color: rgba(0,230,118,0.24);
}

.select-grid-gap-fix div[data-testid="column"] > div {
  height: 100%;
}

.fancy-card-head {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 12px;
  padding: 12px 12px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.10);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  margin-bottom: 12px;
}

.fancy-card-head .left {
  display:flex;
  align-items:center;
  gap: 10px;
}

.fancy-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size: 1.1rem;
  font-weight: 1000;
  border: 1px solid rgba(255,255,255,0.16);
  background: rgba(255,255,255,0.06);
}

.fancy-title {
  font-size: 1.55rem;      /* was 1.15rem */
  font-weight: 1000;
  letter-spacing: 0.02em;
  color: var(--app-text);
  line-height: 1.15;
}

.fancy-hint {
  font-size: 0.95rem;
  font-weight: 400;
  color: var(--app-text-soft);
}

.microchips {
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
  margin-bottom: 10px;
}

.micro {
  display:inline-flex;
  align-items:center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.045);
  color: var(--app-text);
  font-weight: 900;
  font-size: 0.9rem;
}

.micro .dot {
  width: 10px;
  height: 10px;
  border-radius: 99px;
  background: rgba(255,255,255,0.35);
}

.micro .dot.purple { background: rgba(124,77,255,0.75); }
.micro .dot.red    { background: rgba(255,106,106,0.75); }
.micro .dot.green  { background: rgba(0,230,118,0.75); }

.help-tip {
  font-size: 0.95rem;
  color: var(--app-text-soft);
  font-weight: 600;
  margin-top: 4px;
}

/* Make multiselect + text inputs feel more premium */
div[data-testid="stMultiSelect"] > div,
div[data-testid="stTextInput"] > div {
  border-radius: 14px !important;
}            

/* ---------- TYPES + WEAKNESS ROWS (NO OVERLAP) ---------- */
.meta-row{
  display:flex;
  align-items:flex-start;
  justify-content:center;
  gap: 12px;
  flex-wrap: wrap;              /* badges can wrap to next line */
  margin-top: 10px;
  margin-bottom: 6px;
}

.meta-label{
  font-weight: 900;
  font-size: 1.15em;
  color: var(--app-text);
  white-space: nowrap;          /* keep "Types:" together */
}

.meta-badges{
  display:flex;
  justify-content:center;
  gap: 10px;
  flex-wrap: wrap;              /* wrap badges */
  max-width: 90%;
}

.meta-row + .meta-row{
  margin-top: 14px;             /* space between Types and Weak rows */
}

/* -------- THEME-AWARE TEXT COLORS (works in dark + light) -------- */
:root{
  --app-text: var(--text-color);
  --app-text-soft: rgba( var(--text-color-rgb), 0.85);
}

/* Fallback for older Streamlit versions that may not expose text-color-rgb */
@supports not (color: rgba(var(--text-color-rgb), 1)) {
  :root{
    --app-text-soft: var(--text-color);
  }
}            

/* Reserve vertical space so scaled sprites do NOT overlap other elements */
.sprite-wrap {
    text-align: center;
    height: 420px;          /* <<< IMPORTANT: reserve space */
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 10px 0 0 0;
}

.pokemon-sprite {
    image-rendering: pixelated;
    transform: scale(4);    /* <<< sprite size */
    transform-origin: center;
    display: block;
}

.sprite-placeholder {
    font-size: 5em;          /* <<< size of the ??? */
    font-weight: 900;
    color: rgba(255,255,255,0.85);
    letter-spacing: 0.08em;
    line-height: 1;
}
            
.poke-name {
    text-align: center;
    color: var(--app-text);
    font-size: 3em;
    font-weight: 800;
    margin: 0 0 4px 0;
}

.fancy-icon img {
  width: 40px;
  height: 40px;
  image-rendering: pixelated;
  display: block;
}

/* ---------- CARD LAYOUT ---------- */
.card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 20px 20px 16px 20px;
    margin: 18px 0;
}

.card-title {
    font-size: 1.8em;
    font-weight: 800;
    margin-bottom: 0px;
    padding-bottom: 0px;
}
            
/* ---------- MOVE DETAILS ---------- */
.move-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 22px 24px;
    margin-top: 10px;
    min-height: 200px;
}

.move-subtitle {
    font-size: 1.1em;
    font-weight: 800;
    color: var(--app-text-soft);
    margin-bottom: 10px;
}

.move-name {
    font-size: 1.8em;
    font-weight: 900;
    margin-bottom: 14px;
}

.move-row {
    font-size: 1.15em;
    line-height: 1.8;
    margin: 4px 0;
}

.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 800;
    font-size: 0.95em;
    margin-left: 10px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(255,255,255,0.06);
}

.acc-big {
    font-size: 1.25em;
    font-weight: 900;
}
            
/* Fix: prevent pills from ever looking like code blocks */
.select-badges, .pill, .pill * {
  font-family: inherit !important;
  white-space: normal !important;
  letter-spacing: 0.02em !important;
}

.select-badges {
  max-width: 520px;
  text-align: right;
}

/* Make sure no <pre>/<code> styling leaks into the hero */
.select-hero pre, .select-hero code {
  display: none !important;
}

/* ---------- BATTLE BUTTON (GRAPHITE METAL) ---------- */

/* Targets only your primary battle button */
div[data-testid="stButton"] > button[kind="primary"]{
  display: block !important;
  margin: 18px auto 8px auto !important;

  border-radius: 26px !important;
  padding: 26px 78px !important;

  font-size: 2.75rem !important;
  font-weight: 1000 !important;
  letter-spacing: 0.10em !important;
  color: rgba(255,255,255,0.92) !important;

  /* Metallic graphite: subtle gradient + specular top edge */
  background:
    radial-gradient(120px 90px at 18% 22%, rgba(255,255,255,0.16), transparent 60%),
    radial-gradient(380px 220px at 70% 10%, rgba(124,77,255,0.10), transparent 55%),
    linear-gradient(180deg, #3a3f48 0%, #272b33 46%, #1b1f27 100%) !important;

  border: 1px solid rgba(255,255,255,0.14) !important;

  /* Less glow, more depth */
  box-shadow:
    0 18px 50px rgba(0,0,0,0.62),
    inset 0 -10px 18px rgba(0,0,0,0.40) !important;

  position: relative !important;
  overflow: hidden !important;
  transform: translateZ(0);
  transition: transform 140ms ease, filter 140ms ease, box-shadow 140ms ease !important;
}

/* Thin top-edge highlight (feels like metal) */
div[data-testid="stButton"] > button[kind="primary"]::after{
  content:"";
  position:absolute;
  left: 12px;
  right: 12px;
  top: 6px;
  height: 10px;                      /* bigger area */
  border-radius: 999px;
  background: linear-gradient(
    180deg,
    rgba(255,255,255,0.14),
    rgba(255,255,255,0.00)
  );
  opacity: 0.2;                     /* much softer */
  pointer-events:none;
}

/* Diagonal sheen sweep (only visible on hover) */
div[data-testid="stButton"] > button[kind="primary"]::before{
  content:"";
  position:absolute;
  top:-70%;
  left:-65%;
  width: 55%;
  height: 260%;
  transform: rotate(25deg);
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255,255,255,0.20),
    transparent
  );
  filter: blur(1px);
  opacity: 0.0;
  transition: opacity 160ms ease;
  pointer-events:none;
}

/* Hover: tiny lift + brighter metal + subtle cool rim */
div[data-testid="stButton"] > button[kind="primary"]:hover{
  filter: brightness(1.10) contrast(1.04) saturate(1.02) !important;
  transform: translateY(-3px) scale(1.01) !important;

  box-shadow:
    0 22px 70px rgba(0,0,0,0.70),
    0 0 0 1px rgba(124,77,255,0.22),
    inset 0 1px 0 rgba(255,255,255,0.14),
    inset 0 -10px 18px rgba(0,0,0,0.42) !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover::before{
  opacity: 1.0;
  animation: battleSheen 850ms ease forwards;
}

@keyframes battleSheen{
  0%   { left:-65%; opacity:0.0; }
  18%  { opacity:0.85; }
  100% { left:125%; opacity:0.0; }
}

/* Active press */
div[data-testid="stButton"] > button[kind="primary"]:active{
  transform: translateY(1px) scale(0.995) !important;
  filter: brightness(0.98) !important;
}

/* Focus ring: clean + premium */
div[data-testid="stButton"] > button[kind="primary"]:focus{
  outline: none !important;
  box-shadow:
    0 18px 50px rgba(0,0,0,0.62),
    0 0 0 4px rgba(124,77,255,0.22),
    inset 0 1px 0 rgba(255,255,255,0.12),
    inset 0 -10px 18px rgba(0,0,0,0.40) !important;
}

/* ---------- BATTLE + QUICK BUTTONS (GRAPHITE METAL) ---------- */

/* Shared metal look for BOTH buttons (battle + quick) */
.battle-btn div[data-testid="stButton"] > button,
.quick-btn  div[data-testid="stButton"] > button{
  display: block !important;
  margin: 18px auto 8px auto !important;

  border-radius: 26px !important;

  font-weight: 1000 !important;
  letter-spacing: 0.10em !important;
  color: rgba(255,255,255,0.92) !important;

  background:
    radial-gradient(120px 90px at 18% 22%, rgba(255,255,255,0.16), transparent 60%),
    radial-gradient(380px 220px at 70% 10%, rgba(124,77,255,0.10), transparent 55%),
    linear-gradient(180deg, #3a3f48 0%, #272b33 46%, #1b1f27 100%) !important;

  border: 1px solid rgba(255,255,255,0.14) !important;

  box-shadow:
    0 18px 50px rgba(0,0,0,0.62),
    inset 0 -10px 18px rgba(0,0,0,0.40) !important;

  position: relative !important;
  overflow: hidden !important;
  transform: translateZ(0);
  transition: transform 140ms ease, filter 140ms ease, box-shadow 140ms ease !important;
}

/* Top-edge highlight */
.battle-btn div[data-testid="stButton"] > button::after,
.quick-btn  div[data-testid="stButton"] > button::after{
  content:"";
  position:absolute;
  left: 12px;
  right: 12px;
  top: 6px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.00));
  opacity: 0.2;
  pointer-events:none;
}

/* Sheen sweep */
.battle-btn div[data-testid="stButton"] > button::before,
.quick-btn  div[data-testid="stButton"] > button::before{
  content:"";
  position:absolute;
  top:-70%;
  left:-65%;
  width: 55%;
  height: 260%;
  transform: rotate(25deg);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.20), transparent);
  filter: blur(1px);
  opacity: 0.0;
  transition: opacity 160ms ease;
  pointer-events:none;
}

/* Hover */
.battle-btn div[data-testid="stButton"] > button:hover,
.quick-btn  div[data-testid="stButton"] > button:hover{
  filter: brightness(1.10) contrast(1.04) saturate(1.02) !important;
  transform: translateY(-3px) scale(1.01) !important;

  box-shadow:
    0 22px 70px rgba(0,0,0,0.70),
    0 0 0 1px rgba(124,77,255,0.22),
    inset 0 1px 0 rgba(255,255,255,0.14),
    inset 0 -10px 18px rgba(0,0,0,0.42) !important;
}

.battle-btn div[data-testid="stButton"] > button:hover::before,
.quick-btn  div[data-testid="stButton"] > button:hover::before{
  opacity: 1.0;
  animation: battleSheen 850ms ease forwards;
}

/* Active */
.battle-btn div[data-testid="stButton"] > button:active,
.quick-btn  div[data-testid="stButton"] > button:active{
  transform: translateY(1px) scale(0.995) !important;
  filter: brightness(0.98) !important;
}

/* Focus */
.battle-btn div[data-testid="stButton"] > button:focus,
.quick-btn  div[data-testid="stButton"] > button:focus{
  outline: none !important;
  box-shadow:
    0 18px 50px rgba(0,0,0,0.62),
    0 0 0 4px rgba(124,77,255,0.22),
    inset 0 1px 0 rgba(255,255,255,0.12),
    inset 0 -10px 18px rgba(0,0,0,0.40) !important;
}

/* Sizes: Battle stays huge, Quick matches look but is smaller */
.battle-btn div[data-testid="stButton"] > button{
  padding: 26px 78px !important;
  font-size: 2.75rem !important;
}

.quick-btn div[data-testid="stButton"] > button{
  padding: 18px 44px !important;
  font-size: 1.55rem !important;
}  

/* --- QUICK ROW: lock both buttons to identical height --- */
:root{
  --quick-row-btn-minh: 72px;   /* adjust once if you ever tweak quick button size */
}

/* ---------- QUICK ROW ALIGNMENT FIX ---------- */

/* Make the whole quick row a flex container */
.quick-btn {
  display: flex !important;
  align-items: center !important;   /* vertically center both buttons */
  gap: 12px !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

/* Streamlit column wrappers must also center content */
.quick-btn > div[data-testid="column"],
.quick-btn > div[data-testid="column"] > div {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 !important;
  box-sizing: border-box !important;
}

/* Left column grows, right stays natural width */
.quick-btn > div[data-testid="column"]:first-child {
  flex: 1 1 auto !important;
}

/* Remove vertical margins so alignment is controlled by flex */
.quick-btn div[data-testid="stButton"] > button,
.quick-reset div[data-testid="stButton"] > button {
  margin: 0 !important;
}            

/* Force the quick randomize button height */
.quick-btn div[data-testid="stButton"] > button{
  min-height: var(--quick-row-btn-minh) !important;
  line-height: 1 !important; /* prevents font metrics from changing height */
}

/* ---------- QUICK ROW (reliable alignment fix) ---------- */
.quick-row-anchor {
  height: 0;
  margin: 0;
  padding: 0;
}

/* Target the Streamlit horizontal block right after the anchor */
.quick-row-anchor + div[data-testid="stHorizontalBlock"] {
  align-items: center !important;  /* vertical align columns */
}

/* Make both buttons identical height + remove auto margins */
.quick-row-anchor + div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {
  margin: 0 !important;
  min-height: 72px !important;
  height: 72px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}            

/* RESET button: full width, same height as quick randomize (fixed) */
.quick-reset div[data-testid="stButton"] > button{
  display: flex !important;                 /* center contents vertically */
  align-items: center !important;
  justify-content: center !important;

  margin: 18px 0px 8px 0px !important;
  border-radius: 26px !important;

  /* Keep the same visual padding / font-size as quick button */
  padding: 18px 44px !important;
  font-size: 1.55rem !important;
  font-weight: 1000 !important;
  letter-spacing: 0.10em !important;
  color: rgba(255,255,255,0.92) !important;

  width: 100% !important;
  min-width: 0 !important;
  max-width: none !important;

  background:
    radial-gradient(120px 90px at 18% 22%, rgba(255,255,255,0.10), transparent 60%),
    radial-gradient(380px 220px at 70% 10%, rgba(124,77,255,0.06), transparent 55%),
    linear-gradient(180deg, #2b2f37 0%, #1a1d23 60%, #111317 100%) !important;

  border: 1px solid rgba(255,255,255,0.14) !important;
  box-shadow:
    0 18px 50px rgba(0,0,0,0.62),
    inset 0 -10px 18px rgba(0,0,0,0.40) !important;

  min-height: var(--quick-row-btn-minh) !important;
  height: var(--quick-row-btn-minh) !important;
  line-height: 1 !important;                 /* rely on flex centering instead of line-height */
  box-sizing: border-box !important;

  position: relative !important;
  overflow: hidden !important;
  transform: translateZ(0);
  transition: transform 140ms ease, filter 140ms ease, box-shadow 140ms ease !important;
}

/* Hover */
.quick-reset div[data-testid="stButton"] > button:hover{
  filter: brightness(1.10) contrast(1.04) saturate(1.02) !important;
  transform: translateY(-3px) scale(1.01) !important;
  box-shadow:
    0 22px 70px rgba(0,0,0,0.70),
    0 0 0 1px rgba(124,77,255,0.22),
    inset 0 1px 0 rgba(255,255,255,0.14),
    inset 0 -10px 18px rgba(0,0,0,0.42) !important;
}

/* Active */
.quick-reset div[data-testid="stButton"] > button:active{
  transform: translateY(1px) scale(0.995) !important;
  filter: brightness(0.98) !important;
}

/* Make ALL wrapper divs stretch to fill the column — this is the key fix */
.quick-reset {
  width: 100% !important;
  display: block !important;
}
.quick-reset > div,
.quick-reset div[data-testid="stButton"] {
  width: 100% !important;
  display: block !important;
}          

/* ---------- WINNER CELEBRATION ---------- */
.winner-card {
    margin-top: 14px;
    padding: 22px 22px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(0, 0, 0, 0.25);
    text-align: center;
}

.winner-title {
    margin: 0 0 14px 0;
    font-size: 2.0rem;
    font-weight: 1000;
    letter-spacing: 0.02em;
    color: var(--app-text);
}

.winner-sprite-wrap {
    display: flex;
    justify-content: center;
    align-items: center;

    min-height: 260px;   /* allow enough room */
    padding-top: 10px;
    padding-bottom: 6px;
    overflow: visible;   /* IMPORTANT: stop cropping */
}

/* Scale is smaller than before but not clipped */
.winner-sprite {
    image-rendering: pixelated;
    transform: scale(3.4);
    transform-origin: center;
    display: block;
}

/* ---------- COMPACT DROPDOWN HEADER ROW (title + button) ---------- */
.dropdown-head {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 14px;
  padding: 12px 12px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.10);
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  margin: 14px 0 8px 0;
}

.dropdown-left{
  display:flex;
  align-items:center;
  gap: 10px;
}

.dropdown-title{
  font-size: 1.35rem;
  font-weight: 1000;
  color: var(--app-text);
  line-height: 1.15;
}

.dropdown-sub{
  font-size: 0.95rem;
  color: var(--app-text-soft);
  font-weight: 500;
}

/* slightly smaller randomize button in dropdown headers */
.dd-btn-anchor + div[data-testid="stButton"] > button{
  padding: 10px 14px !important;
  border-radius: 14px !important;
  font-size: 1.0rem !important;
}            

/* Big bold labels for the manual name inputs (LEFT aligned) */
.name-label{
  width: 100%;
  text-align: left;        /* <-- change from center to left */
  font-size: 1.6rem;
  font-weight: 1000;
  margin: 0 0 8px 0;
  padding-left: 2px;       /* optional: subtle alignment with input */
  color: var(--app-text);
}                       

/* ---------- SECTION SPACERS ---------- */
.section-spacer-sm { height: 12px; }
.section-spacer-md { height: 20px; }
.section-spacer-lg { height: 28px; }            

</style>
""", unsafe_allow_html=True)

def render_sprite(url: str):
    # If no URL, show a big ??? placeholder instead of broken image icon
    if not url:
        st.markdown(
            """
            <div class="sprite-wrap">
                <div style="font-size: 5rem; font-weight: 900; color: var(--app-text); opacity: 0.85;">???</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    st.markdown(
        f"""
        <div class="sprite-wrap">
            <img class="pokemon-sprite" src="{url}">
        </div>
        """,
        unsafe_allow_html=True
    )

# --- HERO HEADER (logo + centered title + subtitle) ---
logo_path = load_image("pokeball_pixel_icon.png")

if logo_path:
    status_ball_b64 = img_to_base64(logo_path)
    css = """
    <style>
      div[data-testid="stStatusWidget"] {{
        width: 34px !important;
        height: 34px !important;
        border-radius: 999px !important;
        background: url("data:image/png;base64,{B64}") center/contain no-repeat !important;
        animation: pokeSpin 0.9s linear infinite;
        box-shadow: 0 10px 26px rgba(0,0,0,0.45);
        opacity: 0.95;
      }}

      div[data-testid="stStatusWidget"] * {{
        display: none !important;
      }}

      @keyframes pokeSpin {{
        from {{ transform: rotate(0deg); }}
        to   {{ transform: rotate(360deg); }}
      }}
    </style>
    """.format(B64=status_ball_b64)

    st.markdown(css, unsafe_allow_html=True)


# Small Pokéball for section headers
small_ball_html = ""
if logo_path:
    small_b64 = img_to_base64(logo_path)
    small_ball_html = f'<img src="data:image/png;base64,{small_b64}" alt="Pokeball" />'

if logo_path:
    b64 = img_to_base64(logo_path)
    img_tag = f'<img src="data:image/png;base64,{b64}" class="hero-logo" alt="Pokeball logo" />'
else:
    img_tag = ""

st.markdown(
    f"""
    <style>
      /* Make sure hero always centers inside Streamlit's actual main container */
      div[data-testid="stAppViewContainer"] .hero-full {{
        width: 100%;
        display: flex;
        justify-content: center;  /* centers horizontally */
        padding: 10px 0 18px 0;
      }}

      .hero-wrap {{
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        max-width: 1100px;
        width: 100%;
        padding: 0 1rem;
        color: var(--app-text);
      }}

      .hero-logo {{
        width: 110px;
        image-rendering: pixelated;
        margin: 0 0 10px 0;
        display: block;
      }}

      .hero-title {{
        margin: 0;
        font-weight: 900;
        letter-spacing: 0.06em;
        text-align: center;
        width: 100%;
        color: var(--app-text);
      }}

      .hero-subtitle {{
        margin-top: 6px;
        margin-bottom: 0px;
        font-size: 1.05rem;
        color: var(--app-text-soft);
        text-align: center;
        width: 100%;
      }}
    </style>

    <div class="hero-full">
      <div class="hero-wrap">
        {img_tag}
        <h1 class="hero-title">POKÉMON BATTLE ARENA</h1>
        <p class="hero-subtitle">
          Select two Pokémon, choose their moves, and simulate a battle using real data from the PokeAPI.
        </p>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)
# --- END HERO HEADER ---

BASE_URL = "https://pokeapi.co/api/v2"

# -------------------------
# SHARED REQUESTS SESSION (RETRY + TIMEOUT)
# -------------------------
DEFAULT_TIMEOUT = 12  # seconds

SESSION = requests.Session()
_retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.35,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET",),
    raise_on_status=False,
)
SESSION.mount("https://", HTTPAdapter(max_retries=_retry))

def get_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Centralized GET -> JSON with retry + timeout + safe failure."""
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}

# 2. API FUNCTIONS

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pokemon(name: str):
    url = f"{BASE_URL}/pokemon/{name.strip().lower()}"
    return get_json(url, timeout=DEFAULT_TIMEOUT)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_move(name: str):
    url = f"{BASE_URL}/move/{name.strip().lower().replace(' ', '-')}"
    return get_json(url, timeout=DEFAULT_TIMEOUT)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_type(name: str):
    url = f"{BASE_URL}/type/{name.strip().lower()}"
    return get_json(url, timeout=DEFAULT_TIMEOUT)
    
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_all_pokemon_names():
    url = f"{BASE_URL}/pokemon?limit=100000&offset=0"
    data = get_json(url, timeout=20)
    return [p["name"] for p in data.get("results", [])] if data else []

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_species_by_url(species_url: str):
    """Fetch a pokemon-species resource using its URL (cached)."""
    return get_json(species_url, timeout=DEFAULT_TIMEOUT)

def get_default_variety_name(pokemon_data: dict) -> str:
    """
    Given a pokemon endpoint response, resolve the default/base variety name
    via pokemon-species.varieties where is_default = True.
    """
    if not pokemon_data:
        return ""

    species = pokemon_data.get("species") or {}
    species_url = species.get("url", "")
    if not species_url:
        return ""

    species_data = fetch_species_by_url(species_url)
    if not species_data:
        return ""

    for v in species_data.get("varieties", []):
        if v.get("is_default"):
            p = v.get("pokemon") or {}
            return p.get("name", "")

    return ""

def get_damaging_moves_from_pokemon_data(pokemon_data: dict) -> list[str]:
    """
    Return unique damaging moves (power != None) from THIS pokemon's moves list.
    Uses global move index so it's instant.
    """
    if not pokemon_data:
        return []

    move_idx = get_move_index()
    moves = []

    for m in pokemon_data.get("moves", []) or []:
        move_name = (m.get("move") or {}).get("name", "")
        if not move_name:
            continue

        info = move_idx.get(move_name)
        if info and info.get("power") is not None:
            moves.append(move_name)

    return sorted(set(moves))

def get_damaging_moves_with_fallback(pokemon_data: dict) -> list[str]:
    """
    If a form has no damaging moves, fallback to the default/base variety's moveset.
    Example: charizard-gmax -> charizard.
    """
    moves = get_damaging_moves_from_pokemon_data(pokemon_data)
    if moves:
        return moves

    base_name = get_default_variety_name(pokemon_data)
    if not base_name:
        return []

    base_data = fetch_pokemon(base_name)
    return get_damaging_moves_from_pokemon_data(base_data)

def get_weaknesses(defender_types):
    if not defender_types:
        return {}

    mult = {t: 1.0 for t in TYPE_COLORS.keys()}

    for d in defender_types:
        data = fetch_type(d)
        if not data:
            continue

        dr = data.get("damage_relations", {})
        double_from = [t["name"].capitalize() for t in dr.get("double_damage_from", [])]
        half_from   = [t["name"].capitalize() for t in dr.get("half_damage_from", [])]
        no_from     = [t["name"].capitalize() for t in dr.get("no_damage_from", [])]

        for atk in double_from:
            if atk in mult:
                mult[atk] *= 2.0
        for atk in half_from:
            if atk in mult:
                mult[atk] *= 0.5
        for atk in no_from:
            if atk in mult:
                mult[atk] *= 0.0

    weak = {k: v for k, v in mult.items() if v > 1.0}
    weak = dict(sorted(weak.items(), key=lambda x: (-x[1], x[0])))
    return weak

@st.cache_data(show_spinner=False)
def get_weaknesses_cached(defender_types: tuple[str, ...]) -> dict[str, float]:
    # Type safety: cached function must only ever receive a tuple
    if not isinstance(defender_types, tuple):
        raise TypeError(
            f"get_weaknesses_cached() expects tuple[str, ...], got {type(defender_types).__name__}"
        )

    # No need to convert to list; get_weaknesses can iterate tuples fine
    return get_weaknesses(defender_types)

@st.cache_data(show_spinner=False)
def get_moves_with_types(pokemon_moves: tuple[str, ...]):
    """Get move types for dropdown coloring (instant via move index)."""
    move_idx = get_move_index()
    move_types = {}

    for move_name in pokemon_moves or ():
        info = move_idx.get(move_name) or {}
        move_types[move_name] = (info.get("type") or "")

    return move_types

def is_gmax_form(pokemon_data: dict) -> bool:
    """True if pokemon name ends with -gmax (e.g., gengar-gmax)."""
    if not pokemon_data:
        return False
    name = (pokemon_data.get("name") or "").lower()
    return name.endswith("-gmax")

# =========================
# FAST FILTERED RANDOMIZER (NO GLOBAL INDEX)
# =========================

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_species_by_name(name: str) -> dict:
    url = f"{BASE_URL}/pokemon-species/{name.strip().lower()}"
    return get_json(url, timeout=DEFAULT_TIMEOUT)

# =========================
# SUPER FAST INDICES (TYPE + CLASS)
# Streamlit Cloud friendly: cache in memory (no disk)
# =========================

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_all_species_names() -> list[str]:
    url = f"{BASE_URL}/pokemon-species?limit=100000&offset=0"
    data = get_json(url, timeout=25)
    return [s["name"] for s in data.get("results", [])] if data else []

def _safe_get_json(url: str, timeout: int = 20) -> dict:
    return get_json(url, timeout=timeout)

@st.cache_resource(show_spinner=False)
def get_class_index() -> dict:
    """
    Builds sets for each class so filtering is O(1) and requires NO API calls later.
    This is the key fix for "class filters take forever".
    """
    species_names = fetch_all_species_names()

    legendary = set()
    mythical = set()
    baby = set()
    default_forms = set()

    mega = set()
    gmax = set()
    battle_only = set()

    # Fetch species concurrently to reduce initial build time
    def fetch_one_species(sname: str) -> dict:
        return fetch_species_by_name(sname)

    with ThreadPoolExecutor(max_workers=24) as ex:
        futures = {ex.submit(fetch_one_species, s): s for s in species_names}
        for fut in as_completed(futures):
            sd = fut.result()
            if not sd:
                continue

            is_leg = bool(sd.get("is_legendary", False))
            is_myth = bool(sd.get("is_mythical", False))
            is_baby = bool(sd.get("is_baby", False))

            for v in sd.get("varieties", []) or []:
                p = (v.get("pokemon") or {}).get("name", "")
                if not p:
                    continue

                # species-based classes
                if is_leg:
                    legendary.add(p)
                if is_myth:
                    mythical.add(p)
                if is_baby:
                    baby.add(p)
                if v.get("is_default") is True:
                    default_forms.add(p)

                # name-based classes
                pn = p.lower()
                if pn.endswith("-gmax"):
                    gmax.add(p)
                if "-mega" in pn:
                    mega.add(p)
                if any(m in pn for m in BATTLE_ONLY_MARKERS):
                    battle_only.add(p)

    return {
        "Legendary": legendary,
        "Mythical": mythical,
        "Baby": baby,
        "Default": default_forms,
        "Mega": mega,
        "Gmax": gmax,
        "Battle-only": battle_only,
    }

@st.cache_resource(show_spinner=False)
def get_type_index() -> dict:
    """
    Builds sets for each type using /type/{type}.
    After this, type filtering is also O(1) and requires NO API calls later.
    """
    idx = {t: set() for t in TYPE_COLORS.keys()}

    def fetch_one_type(tname: str) -> dict:
        return fetch_type(tname)

    with ThreadPoolExecutor(max_workers=18) as ex:
        futures = {ex.submit(fetch_one_type, t): t for t in TYPE_COLORS.keys()}
        for fut in as_completed(futures):
            tname = futures[fut]
            td = fut.result()
            if not td:
                continue
            # /type returns a list of pokemon entries
            for entry in td.get("pokemon", []) or []:
                p = (entry.get("pokemon") or {}).get("name", "")
                if p:
                    # store names in lowercase (your pokemon_names_all are lowercase)
                    idx[tname].add(p.lower())

    return idx

# =========================
# SUPER FAST MOVE INDEX (POWER / TYPE / CLASS / ACCURACY)
# One-time warmup -> instant move filtering + move display
# =========================

@st.cache_resource(show_spinner=False)
def get_move_index() -> dict:
    """
    Global move dictionary: move_name -> {power, accuracy, type, damage_class}
    Used to filter damaging moves instantly WITHOUT fetching each move per Pokémon.
    """
    # Pull list of all moves
    data = _safe_get_json(f"{BASE_URL}/move?limit=100000&offset=0", timeout=25)
    move_names = [m["name"] for m in (data.get("results") or []) if m.get("name")]

    idx: dict[str, dict] = {}

    def fetch_one(mname: str):
        md = fetch_move(mname)  # cached
        if not md:
            return None

        return (mname, {
            "power": md.get("power"),
            "accuracy": md.get("accuracy"),
            "type": ((md.get("type") or {}).get("name") or "").capitalize(),
            "damage_class": ((md.get("damage_class") or {}).get("name") or ""),
        })

    # Moderate concurrency to avoid throttling
    with ThreadPoolExecutor(max_workers=16) as ex:
        for item in ex.map(fetch_one, move_names):
            if item:
                k, v = item
                idx[k] = v

    return idx

def pokemon_matches_filters(pokemon_name: str, type_filters: list[str], class_filters: list[str]) -> bool:
    if not pokemon_name:
        return False

    name = pokemon_name.lower()

    # ---- CLASS FILTERS: O(1) set membership ----
    if class_filters:
        class_idx = get_class_index()
        for c in class_filters:
            if name not in class_idx.get(c, set()):
                return False

    # ---- TYPE FILTERS: O(1) set membership ----
    if type_filters:
        type_idx = get_type_index()

        # ✅ AND logic for types (must include ALL selected)
        if not all(name in type_idx.get(t, set()) for t in type_filters):
            return False

    return True

@st.cache_data(show_spinner=False)
def build_pool_for_filters(all_names: list[str], type_filters: tuple, class_filters: tuple) -> list[str]:
    tf = list(type_filters or ())
    cf = list(class_filters or ())
    return [n for n in all_names if pokemon_matches_filters(n, tf, cf)]

def pick_random_pokemon_name(all_names: list[str], type_filters: list[str], class_filters: list[str]) -> str:
    pool = build_pool_for_filters(all_names, tuple(type_filters or []), tuple(class_filters or []))
    return random.choice(pool) if pool else ""

# =========================
# BOOT LOADING / WARMUP GATE (BLOCK UI UNTIL READY)
# Cold start: show loader until EVERYTHING is loaded
# Warm start (refresh/new session): show loader for 1s only
# =========================

@st.cache_resource(show_spinner=False)
def get_boot_state():
    """
    Global (server-wide) boot state that persists across sessions.
    - ready=False means the server hasn't warmed up caches yet.
    - We store names here too so every session can reuse instantly.
    """
    return {"ready": False, "names": None, "lock": threading.Lock()}

def warmup_everything_global() -> list[str]:
    """
    Warm up ALL heavy caches that you want to be instant afterward.
    This runs only once per server lifetime (guarded by boot_state.ready).
    """
    names = fetch_all_pokemon_names()
    _ = get_type_index()
    _ = get_class_index()
    _ = get_move_index()   # IMPORTANT: include moves too (you want everything instant)
    return names

# --- Loader asset (keep your existing gif file) ---
pikachu_b64 = get_asset_b64("pikachu-running-loading.gif")

boot = get_boot_state()

# Per-session flag: ensures the 1s splash happens only once per session (not every widget rerun)
st.session_state.setdefault("refresh_splash_shown", False)

# -------------------------
# 1) COLD START: loader stays until ALL caches are built
# -------------------------
if not boot["ready"]:
    loader = st.empty()

    # 1) Instant loader first
    loader.markdown(
        fullscreen_loader_html(pikachu_b64, text="", opaque=True),
        unsafe_allow_html=True
    )

    # 2) Load backgrounds
    bg_b64s = get_backgrounds_b64_jpg_only()

    # 3) Switch to slideshow (CSS-only, so it works in st.markdown)
    loader.markdown(
        cold_slideshow_loader_html(
            bg_b64_list=bg_b64s,
            footer_text="Gotta cache them all…",
            switch_every_ms=3000,  # test fast; raise later
            fade_ms=1200,
        ),
        unsafe_allow_html=True
    )

    # 4) Warm up caches
    with boot["lock"]:
        if not boot["ready"]:
            boot["names"] = warmup_everything_global()
            boot["ready"] = True

    st.session_state["pokemon_names_all_cached"] = boot["names"]
    st.session_state["refresh_splash_shown"] = True

    loader.empty()
    st.rerun()

# -------------------------
# 2) WARM START: show 1s splash ONCE per session (refresh/new session)
# -------------------------
if not st.session_state["refresh_splash_shown"]:
    splash = st.empty()
    splash.markdown(fullscreen_loader_html(pikachu_b64, "Loading…", opaque=False), unsafe_allow_html=True)
    time.sleep(1.0)
    splash.empty()
    st.session_state["refresh_splash_shown"] = True

# Ensure names are available for this session instantly
if boot.get("names"):
    st.session_state["pokemon_names_all_cached"] = boot["names"]

# 3. DATA PROCESSING

def extract_pokemon_basic(data: dict, use_shiny: bool = False):
    if not data:
        return {}

    name = data.get("name", "").capitalize()

    sprites = data.get("sprites") or {}
    sprite = sprites.get("front_shiny") if use_shiny else sprites.get("front_default")
    sprite = sprite or sprites.get("front_default") or sprites.get("front_shiny") or ""

    types = [t["type"]["name"].capitalize() for t in data.get("types", [])]

    stats_map = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}
    stats = {
        "hp": stats_map.get("hp", 0),
        "attack": stats_map.get("attack", 0),
        "defense": stats_map.get("defense", 0),
        "special-attack": stats_map.get("special-attack", 0),
        "special-defense": stats_map.get("special-defense", 0),
        "speed": stats_map.get("speed", 0),
    }

    # Damaging moves (with fallback to base/default variety if empty)
    damaging_moves = get_damaging_moves_with_fallback(data)

    return {
        "name": name,
        "sprite": sprite,
        "types": types,
        "stats": stats,
        "damaging_moves": damaging_moves,
        "is_gmax": is_gmax_form(data),
    }

def display_mystery_pokemon():
    """Display mystery silhouette if no Pokémon selected"""
    return {
        "name": "",
        "sprite": "",
        "types": [],
        "stats": {"hp": 0, "attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0},
        "damaging_moves": [],
        "is_gmax": False,
    }

def render_base_stats_table(pokemon: dict):
    """Full-width base stats table. If Gmax: HP displayed doubled and styled red+bold."""
    is_gmax = pokemon.get("is_gmax", False)

    hp_value = int(pokemon["stats"]["hp"] * (2 if is_gmax else 1))

    df = pd.DataFrame({
        "Stat": ["HP", "Attack", "Defense", "Special Attack", "Special Defense", "Speed"],
        "Value": [
            hp_value,
            pokemon["stats"]["attack"],
            pokemon["stats"]["defense"],
            pokemon["stats"]["special-attack"],
            pokemon["stats"]["special-defense"],
            pokemon["stats"]["speed"],
        ],
    })

    def style_row(row):
        if is_gmax and row["Stat"] == "HP":
            return ["", "color:#00e676; font-weight:900;"]  # vibrant green
        return ["", ""]

    styled = df.style.apply(style_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

# --- Session state defaults (prevents Streamlit "default value + session_state" warning) ---
st.session_state.setdefault("p1_name", "")
st.session_state.setdefault("p2_name", "")
st.session_state.setdefault("p1_move", "")
st.session_state.setdefault("p2_move", "")
st.session_state.setdefault("shiny_p1", False)
st.session_state.setdefault("shiny_p2", False)

# 4. POKÉMON SELECTION (UPGRADED UI)

pokemon_names_all = st.session_state.get("pokemon_names_all_cached") or fetch_all_pokemon_names()

# --- Session state defaults for filters ---
st.session_state.setdefault("global_type_filters", [])
st.session_state.setdefault("global_class_filters", [])

st.session_state.setdefault("p1_type_filters", [])
st.session_state.setdefault("p1_class_filters", [])

st.session_state.setdefault("p2_type_filters", [])
st.session_state.setdefault("p2_class_filters", [])

# --- Session state defaults for multiselect widget keys (prevents warning) ---
st.session_state.setdefault("global_type_filters_widget", [])
st.session_state.setdefault("global_class_filters_widget", [])
st.session_state.setdefault("p1_type_filters_widget", [])
st.session_state.setdefault("p1_class_filters_widget", [])
st.session_state.setdefault("p2_type_filters_widget", [])
st.session_state.setdefault("p2_class_filters_widget", [])

# --- Pretty header + live state pills ---
p1_preview = (st.session_state.get("p1_name") or "").strip() or "—"
p2_preview = (st.session_state.get("p2_name") or "").strip() or "—"
gt = st.session_state.get("global_type_filters", [])
gc = st.session_state.get("global_class_filters", [])

hero_html = """
<div class="select-hero">
  <div class="select-hero-top">
    <div>
      <div class="select-title">Select Pokémon</div>
      <div class="select-subtitle">Filter, randomize, and set up your match like a real arena draft.</div>
    </div>

    <div class="select-badges">
      <div class="pill purple">👤 <strong>P1:</strong> __P1__</div>
      <div class="pill red">👤 <strong>P2:</strong> __P2__</div>
      <div class="pill green">🎯 <strong>Global:</strong> __GT__ types • __GC__ classes</div>
    </div>
  </div>
</div>
"""

hero_html = (hero_html
             .replace("__P1__", p1_preview)
             .replace("__P2__", p2_preview)
             .replace("__GT__", str(len(gt)))
             .replace("__GC__", str(len(gc))))

st.markdown(hero_html, unsafe_allow_html=True)

# ---------- COLLAPSIBLE FILTERS / RANDOMIZERS (COMPACT) ----------

st.session_state.setdefault("open_global", False)
st.session_state.setdefault("open_p1", False)
st.session_state.setdefault("open_p2", False)

# Helper to make the compact header row
def dropdown_header(title: str, button_label: str, button_key: str, subtitle=None):
    subtitle_html = f'<div class="dropdown-sub">{subtitle}</div>' if subtitle else ""

    html = f"""
<div class="dropdown-head">
  <div class="dropdown-left">
    <div class="fancy-icon">{small_ball_html}</div>
    <div>
      <div class="dropdown-title">{title}</div>{subtitle_html}
    </div>
  </div>
  <div class="dd-btn-anchor"></div>
</div>
""".strip()

    st.markdown(html, unsafe_allow_html=True)
    return st.button(button_label, key=button_key)

def render_filter_chips(type_list, class_list, empty_text="No filters selected"):
    chips = []
    for t in type_list or []:
        chips.append(type_chip_html(t))
    for c in class_list or []:
        chips.append(f'<span class="micro"><span class="dot purple"></span>{c}</span>')

    st.markdown(
        f"""
        <div class="microchips">
          {("".join(chips) if chips else f'<span class="micro"><span class="dot"></span>{empty_text}</span>')}
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# QUICK RANDOMIZE (NO FILTERS) — OUTSIDE RANDOMIZER DROPDOWN
# =========================================================

def _quick_randomize_both():
    # 1) HARD RESET widget keys (best way to instantly clear multiselects)
    for k in (
        "global_type_filters_widget", "global_class_filters_widget",
        "p1_type_filters_widget", "p1_class_filters_widget",
        "p2_type_filters_widget", "p2_class_filters_widget",
    ):
        st.session_state.pop(k, None)  # <-- important (prevents “one-run-late” visual updates)

    # 2) Reset derived filter lists
    for k in (
        "global_type_filters", "global_class_filters",
        "p1_type_filters", "p1_class_filters",
        "p2_type_filters", "p2_class_filters",
    ):
        st.session_state[k] = []

    # 3) Use already-cached full list
    names = st.session_state.get("pokemon_names_all_cached") or fetch_all_pokemon_names()

    if not names:
        st.session_state["p1_name"] = ""
        st.session_state["p2_name"] = ""
        st.session_state["p1_move"] = ""
        st.session_state["p2_move"] = ""
        return

    # Pick two different Pokémon
    a = random.choice(names)
    b = random.choice(names)
    tries = 0
    while b == a and tries < 30:
        b = random.choice(names)
        tries += 1

    st.session_state["p1_name"] = a
    st.session_state["p2_name"] = b

    # Pick random damaging moves
    p1_raw = fetch_pokemon(a)
    p2_raw = fetch_pokemon(b)

    p1_moves = get_damaging_moves_with_fallback(p1_raw)
    p2_moves = get_damaging_moves_with_fallback(p2_raw)

    st.session_state["p1_move"] = random.choice(p1_moves) if p1_moves else ""
    st.session_state["p2_move"] = random.choice(p2_moves) if p2_moves else ""

def _quick_reset():
    # 1) HARD RESET widget keys (instantly clears multiselect UI)
    for k in (
        "global_type_filters_widget", "global_class_filters_widget",
        "p1_type_filters_widget", "p1_class_filters_widget",
        "p2_type_filters_widget", "p2_class_filters_widget",
    ):
        st.session_state.pop(k, None)

    # 2) Reset derived filter lists
    for k in (
        "global_type_filters", "global_class_filters",
        "p1_type_filters", "p1_class_filters",
        "p2_type_filters", "p2_class_filters",
    ):
        st.session_state[k] = []

    # 3) Reset selections
    st.session_state["p1_name"] = ""
    st.session_state["p2_name"] = ""
    st.session_state["p1_move"] = ""
    st.session_state["p2_move"] = ""

    # 4) Optional: reset shinies too (recommended for a true reset)
    st.session_state["shiny_p1"] = False
    st.session_state["shiny_p2"] = False

# ---------- QUICK RANDOMIZE (NO FILTERS) + RESET (ALIGNED) ----------
st.markdown('<div class="quick-row-anchor"></div>', unsafe_allow_html=True)

q1, q2 = st.columns([5, 1], gap="small", vertical_alignment="center")

with q1:
    st.button(
        "⚡🎲 QUICK RANDOMIZE BOTH POKÉMON (NO FILTERS)",
        key="quick_rand_both",
        type="primary",
        on_click=_quick_randomize_both,
        use_container_width=True,
    )

with q2:
    st.button(
        "↻ RESET",
        key="quick_reset",
        type="primary",
        on_click=_quick_reset,
        use_container_width=True,
    )

# ---------- SINGLE DROPDOWN WRAPPER (EVERYTHING INSIDE) ----------
with st.expander("🎲 POKÉMON RANDOMIZER OPTIONS", expanded=False):

    # --- 1) GLOBAL: Pokémon Randomizer (header + button) ---
    clicked_global_randomize = dropdown_header(
        title="Pokémon Randomizer",
        subtitle="Randomize two Pokémon instantly (filters optional).",
        button_label="🎲 RANDOMIZE BOTH POKÉMONS",
        button_key="dd_randomize_both",
    )

    # Button works even if inner expanders are closed (still INSIDE main dropdown)
    if clicked_global_randomize:
        # 🔥 CLEAR INDIVIDUAL FILTERS (P1 & P2)
        st.session_state["p1_type_filters_widget"] = []
        st.session_state["p1_class_filters_widget"] = []
        st.session_state["p2_type_filters_widget"] = []
        st.session_state["p2_class_filters_widget"] = []

        st.session_state["p1_type_filters"] = []
        st.session_state["p1_class_filters"] = []
        st.session_state["p2_type_filters"] = []
        st.session_state["p2_class_filters"] = []

        a = pick_random_pokemon_name(
            pokemon_names_all,
            st.session_state.get("global_type_filters", []),
            st.session_state.get("global_class_filters", []),
        )
        b = pick_random_pokemon_name(
            pokemon_names_all,
            st.session_state.get("global_type_filters", []),
            st.session_state.get("global_class_filters", []),
        )

        tries = 0
        while b and a and b == a and tries < 30:
            b = pick_random_pokemon_name(
                pokemon_names_all,
                st.session_state.get("global_type_filters", []),
                st.session_state.get("global_class_filters", []),
            )
            tries += 1

        if not a or not b:
            st.error("❌ No Pokémon found matching the global filters. Try loosening filters.")
        else:
            st.session_state["p1_name"] = a
            st.session_state["p2_name"] = b

            p1_raw_rand = fetch_pokemon(a)
            p2_raw_rand = fetch_pokemon(b)

            p1_moves = get_damaging_moves_with_fallback(p1_raw_rand)
            p2_moves = get_damaging_moves_with_fallback(p2_raw_rand)

            st.session_state["p1_move"] = random.choice(p1_moves) if p1_moves else ""
            st.session_state["p2_move"] = random.choice(p2_moves) if p2_moves else ""

    # --- Global filters expander (still inside main dropdown) ---
    with st.expander("Open Pokémon Randomizer filters", expanded=False):
        gcol1, gcol2 = st.columns(2)
        with gcol1:
            st.multiselect(
                "Type filter (optional)",
                options=TYPE_OPTIONS,
                key="global_type_filters_widget",
            )
            st.session_state["global_type_filters"] = st.session_state["global_type_filters_widget"]

        with gcol2:
            st.multiselect(
                "Class filter (optional)",
                options=CLASS_OPTIONS,
                key="global_class_filters_widget",
            )
            st.session_state["global_class_filters"] = st.session_state["global_class_filters_widget"]

        render_filter_chips(
            st.session_state["global_type_filters"],
            st.session_state["global_class_filters"],
            empty_text="No global filters selected"
        )

    # --- 2) P1 & P2 cards (still inside main dropdown) ---
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        clicked_p1_randomize = dropdown_header(
            title="Pokémon 1 Filters",
            button_label="🎲 RANDOMIZE POKÉMON 1",
            button_key="dd_rand_p1",
        )

        if clicked_p1_randomize:
            a = pick_random_pokemon_name(
                pokemon_names_all,
                st.session_state.get("p1_type_filters", []),
                st.session_state.get("p1_class_filters", []),
            )
            if not a:
                st.error("❌ No Pokémon found for Pokémon 1 filters. Try loosening filters.")
            else:
                st.session_state["p1_name"] = a
                p1_raw_rand = fetch_pokemon(a)
                p1_moves = get_damaging_moves_with_fallback(p1_raw_rand)
                st.session_state["p1_move"] = random.choice(p1_moves) if p1_moves else ""

        with st.expander("Open Pokémon 1 filters", expanded=False):
            st.checkbox(
                "✨ Shiny (Pokémon 1)",
                value=st.session_state.get("shiny_p1", False),
                key="shiny_p1"
            )

            st.multiselect(
                "Type filter (optional)",
                options=TYPE_OPTIONS,
                key="p1_type_filters_widget",
            )
            st.session_state["p1_type_filters"] = st.session_state["p1_type_filters_widget"]

            st.multiselect(
                "Class filter (optional)",
                options=CLASS_OPTIONS,
                key="p1_class_filters_widget",
            )
            st.session_state["p1_class_filters"] = st.session_state["p1_class_filters_widget"]

            render_filter_chips(
                st.session_state["p1_type_filters"],
                st.session_state["p1_class_filters"],
                empty_text="No filters selected"
            )

    with col_right:
        clicked_p2_randomize = dropdown_header(
            title="Pokémon 2 Filters",
            button_label="🎲 RANDOMIZE POKÉMON 2",
            button_key="dd_rand_p2",
        )

        if clicked_p2_randomize:
            b = pick_random_pokemon_name(
                pokemon_names_all,
                st.session_state.get("p2_type_filters", []),
                st.session_state.get("p2_class_filters", []),
            )
            if not b:
                st.error("❌ No Pokémon found for Pokémon 2 filters. Try loosening filters.")
            else:
                st.session_state["p2_name"] = b
                p2_raw_rand = fetch_pokemon(b)
                p2_moves = get_damaging_moves_with_fallback(p2_raw_rand)
                st.session_state["p2_move"] = random.choice(p2_moves) if p2_moves else ""

        with st.expander("Open Pokémon 2 filters", expanded=False):
            st.checkbox(
                "✨ Shiny (Pokémon 2)",
                value=st.session_state.get("shiny_p2", False),
                key="shiny_p2"
            )

            st.multiselect(
                "Type filter (optional)",
                options=TYPE_OPTIONS,
                key="p2_type_filters_widget",
            )
            st.session_state["p2_type_filters"] = st.session_state["p2_type_filters_widget"]

            st.multiselect(
                "Class filter (optional)",
                options=CLASS_OPTIONS,
                key="p2_class_filters_widget",
            )
            st.session_state["p2_class_filters"] = st.session_state["p2_class_filters_widget"]

            render_filter_chips(
                st.session_state["p2_type_filters"],
                st.session_state["p2_class_filters"],
                empty_text="No filters selected"
            )

st.markdown("<div class='section-spacer-lg'></div>", unsafe_allow_html=True)

# ---------- MANUAL POKÉMON INPUTS (OUTSIDE MAIN DROPDOWN) ----------
manual_left, manual_right = st.columns(2, gap="large")

with manual_left:
    st.markdown('<div class="name-label">Pokémon 1 Name</div>', unsafe_allow_html=True)
    st.text_input(
        label="",
        placeholder="Type a Pokémon name...",
        key="p1_name",
        label_visibility="collapsed",
    )

with manual_right:
    st.markdown('<div class="name-label">Pokémon 2 Name</div>', unsafe_allow_html=True)
    st.text_input(
        label="",
        placeholder="Type a Pokémon name...",
        key="p2_name",
        label_visibility="collapsed",
    )

# Always safe even if dropdown stayed closed
use_shiny_p1 = st.session_state.get("shiny_p1", False)
use_shiny_p2 = st.session_state.get("shiny_p2", False)

# ---------- FETCH POKÉMON AFTER INPUTS ----------
if not st.session_state.get("p1_name", "").strip():
    p1 = display_mystery_pokemon()
else:
    p1_raw = fetch_pokemon(st.session_state["p1_name"].strip())
    if not p1_raw:
        st.error(f"❌ Pokémon 1 not found: '{st.session_state['p1_name']}'")
        p1 = display_mystery_pokemon()
    else:
        p1 = extract_pokemon_basic(p1_raw, use_shiny=use_shiny_p1)

if not st.session_state.get("p2_name", "").strip():
    p2 = display_mystery_pokemon()
else:
    p2_raw = fetch_pokemon(st.session_state["p2_name"].strip())
    if not p2_raw:
        st.error(f"❌ Pokémon 2 not found: '{st.session_state['p2_name']}'")
        p2 = display_mystery_pokemon()
    else:
        p2 = extract_pokemon_basic(p2_raw, use_shiny=use_shiny_p2)


# 5. POKÉMON DISPLAY & MOVE SELECTION

col1, col2 = st.columns(2)

with col1:
    if p1["name"]:
        p1_badge = " ✨" if (p1.get("name") and use_shiny_p1) else ""
        st.markdown(f"<div class='poke-name'>{p1['name']}{p1_badge}</div>", unsafe_allow_html=True)
    
    render_sprite(p1["sprite"])
    
       # Bold centered types
    type_badges_p1 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.1em;">{t}</span>'
        for t in p1["types"]
    ])

    # Weaknesses (types that deal >1x damage to this Pokémon)
    weak1 = get_weaknesses_cached(tuple(p1["types"]))

    weak_badges_p1 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.05em;">{t} x{int(mult)}</span>'
        for t, mult in weak1.items()
    ])

    # ✅ NEW: Types + Weak against (no overlap, wraps cleanly)
    st.markdown(
        f"""
        <div class="meta-row">
        <div class="meta-label">Types:</div>
        <div class="meta-badges">{type_badges_p1 or 'Unknown'}</div>
        </div>

        <div class="meta-row">
        <div class="meta-label">Weak against:</div>
        <div class="meta-badges">{weak_badges_p1 if weak_badges_p1 else '—'}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='card'><div class='card-title'>Base Stats</div>", unsafe_allow_html=True)
    render_base_stats_table(p1)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='card-title'>Move Selection</div>", unsafe_allow_html=True)

    if p1["damaging_moves"]:
        move_types_p1 = get_moves_with_types(tuple(p1["damaging_moves"]))

        move1_choice = st.selectbox(
            "Move for Pokémon 1",
            options=p1["damaging_moves"],
            format_func=lambda x: x.replace("-", " ").title(),
            key="p1_move",
        )

        if move1_choice:
            selected_type = move_types_p1.get(move1_choice, "")
            selected_color = TYPE_COLORS.get(selected_type, "#808080")
            st.markdown(
                f"**Selected: <span style='color:{selected_color}'>{move1_choice.replace('-', ' ').title()}</span>**",
                unsafe_allow_html=True
            )
    else:
        move1_choice = ""
        st.error("Please select a Pokémon.")

    st.markdown("</div>", unsafe_allow_html=True)


with col2:
    if p2["name"]:
        p2_badge = " ✨" if (p2.get("name") and use_shiny_p2) else ""
        st.markdown(f"<div class='poke-name'>{p2['name']}{p2_badge}</div>", unsafe_allow_html=True)
    
    render_sprite(p2["sprite"])
    
        # Bold centered types
    type_badges_p2 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.1em;">{t}</span>'
        for t in p2["types"]
    ])

    # Weaknesses (types that deal >1x damage to this Pokémon)
    weak2 = get_weaknesses_cached(tuple(p2["types"]))

    weak_badges_p2 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.05em;">{t} x{int(mult)}</span>'
        for t, mult in weak2.items()
    ])

    # ✅ NEW: Types + Weak against (no overlap, wraps cleanly)
    st.markdown(
        f"""
        <div class="meta-row">
        <div class="meta-label">Types:</div>
        <div class="meta-badges">{type_badges_p2 or 'Unknown'}</div>
        </div>

        <div class="meta-row">
        <div class="meta-label">Weak against:</div>
        <div class="meta-badges">{weak_badges_p2 if weak_badges_p2 else '—'}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='card'><div class='card-title'>Base Stats</div>", unsafe_allow_html=True)
    render_base_stats_table(p2)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='card-title'>Move Selection</div>", unsafe_allow_html=True)

    if p2["damaging_moves"]:
        move_types_p2 = get_moves_with_types(tuple(p2["damaging_moves"]))

        move2_choice = st.selectbox(
            "Move for Pokémon 2",
            options=p2["damaging_moves"],
            format_func=lambda x: x.replace("-", " ").title(),
            key="p2_move",
        )

        if move2_choice:
            selected_type = move_types_p2.get(move2_choice, "")
            selected_color = TYPE_COLORS.get(selected_type, "#808080")
            st.markdown(
                f"**Selected: <span style='color:{selected_color}'>{move2_choice.replace('-', ' ').title()}</span>**",
                unsafe_allow_html=True
            )
    else:
        move2_choice = ""
        st.error("Please select a Pokémon.")

    st.markdown("</div>", unsafe_allow_html=True)


def get_move_summary(move_name: str):
    if not move_name:
        return {}

    info = get_move_index().get(move_name)
    if not info:
        return {}

    return {
        "name": move_name.replace("-", " ").title(),
        "power": info.get("power"),
        "accuracy": info.get("accuracy"),
        "type": info.get("type") or "",
        "damage_class": info.get("damage_class") or "",
    }

def accuracy_color(acc):
    """
    Gradient:
    30%  -> red
    65%  -> light gray
    100% -> dark green
    """

    if acc is None:
        return "#FFFFFF"

    acc = float(acc)

    # Clamp between 30 and 100
    acc = max(30, min(100, acc))

    # Normalize to 0–1 range based on 30–100
    t = (acc - 30) / (100 - 30)

    # Define colors
    r_low, g_low, b_low = (220, 53, 69)      # red
    r_mid, g_mid, b_mid = (220, 220, 220)    # light gray
    r_high, g_high, b_high = (0, 120, 60)    # dark green

    if t <= 0.5:
        # Interpolate red -> gray
        local_t = t / 0.5
        r = int(r_low + (r_mid - r_low) * local_t)
        g = int(g_low + (g_mid - g_low) * local_t)
        b = int(b_low + (b_mid - b_low) * local_t)
    else:
        # Interpolate gray -> green
        local_t = (t - 0.5) / 0.5
        r = int(r_mid + (r_high - r_mid) * local_t)
        g = int(g_mid + (g_high - g_mid) * local_t)
        b = int(b_mid + (b_high - b_mid) * local_t)

    return f"rgb({r},{g},{b})"

def power_color(power):
    """
    Gradient:
    10  -> light gray
    100 -> orange
    250 -> deep red
    """

    if power is None:
        return "#FFFFFF"

    power = float(power)

    # Clamp between 10 and 250
    power = max(10, min(250, power))

    # Normalize 10–250 → 0–1
    t = (power - 10) / (250 - 10)

    # Colors
    r_low, g_low, b_low = (200, 200, 200)    # light gray
    r_mid, g_mid, b_mid = (255, 140, 0)      # orange
    r_high, g_high, b_high = (180, 0, 0)     # deep red

    if t <= 0.5:
        # gray -> orange
        local_t = t / 0.5
        r = int(r_low + (r_mid - r_low) * local_t)
        g = int(g_low + (g_mid - g_low) * local_t)
        b = int(b_low + (b_mid - b_low) * local_t)
    else:
        # orange -> red
        local_t = (t - 0.5) / 0.5
        r = int(r_mid + (r_high - r_mid) * local_t)
        g = int(g_mid + (g_high - g_mid) * local_t)
        b = int(b_mid + (b_high - b_mid) * local_t)

    return f"rgb({r},{g},{b})"

def render_move_box(title, move_info):

    if not move_info:
        return (
            f'<div class="move-box">'
            f'  <div class="move-subtitle">{title}</div>'
            f'  <div class="move-row">No move selected</div>'
            f'</div>'
        )

    acc = move_info.get("accuracy")
    acc_text = f"{acc}%" if acc is not None else "—"
    acc_col = accuracy_color(acc)

    move_type = move_info["type"]
    type_color = TYPE_COLORS.get(move_type, "#808080")

    type_badge = (
    f'<span class="badge" '
    f'style="background:{type_color}; color:#FFFFFF; border:none;">'
    f'{move_type}</span>'
    )

    damage_class = move_info["damage_class"].capitalize()

    if damage_class == "Physical":
        class_badge = (
            '<span class="badge" '
            'style="background:#C62828; color:#FFD54F; border:none;">'
            'Physical</span>'
        )
    else:  # Special
        class_badge = (
            '<span class="badge" '
            'style="background:#1565C0; color:#111111; border:none;">'
            'Special</span>'
        )
    

    power = move_info["power"]
    power_text = power if power is not None else "—"
    power_col = power_color(power)

    return (
        f'<div class="move-box">'
        f'  <div class="move-subtitle">{title}</div>'
        f'  <div class="move-name">{move_info["name"]}</div>'
        f'  <div class="move-row"><span style="font-weight:800;">Type:</span> {type_badge}</div>'
        f'  <div class="move-row"><span style="font-weight:800;">Damage class:</span> {class_badge}</div>'
        f'  <div class="move-row"><span style="font-weight:800;">Power:</span> '
        f'    <span class="acc-big" style="color:{power_col};">{power_text}</span>'
        f'  </div>'
        f'  <div class="move-row"><span style="font-weight:800;">Accuracy:</span> '
        f'    <span class="acc-big" style="color:{acc_col};">{acc_text}</span>'
        f'  </div>'
        f'</div>'
    )

move1_info = get_move_summary(move1_choice) if move1_choice else {}
move2_info = get_move_summary(move2_choice) if move2_choice else {}

st.markdown("<div class='card'><div class='card-title'>Selected Moves Details</div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    title_left = f"{p1['name']}'s move" if p1.get("name") else "Pokémon 1 move"
    st.markdown(render_move_box(title_left, move1_info), unsafe_allow_html=True)

with c2:
    title_right = f"{p2['name']}'s move" if p2.get("name") else "Pokémon 2 move"
    st.markdown(render_move_box(title_right, move2_info), unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# 6. STAT COMPARISON CHART

def build_stat_comparison_df(p1, p2):
    def hp_for_chart(p):
        base_hp = p["stats"]["hp"]
        return int(base_hp * (2 if p.get("is_gmax") else 1))

    raw = pd.DataFrame([
        {
            "pokemon": p1["name"],
            "hp": hp_for_chart(p1),
            "attack": p1["stats"]["attack"],
            "defense": p1["stats"]["defense"],
            "special-attack": p1["stats"]["special-attack"],
            "special-defense": p1["stats"]["special-defense"],
            "speed": p1["stats"]["speed"],
        },
        {
            "pokemon": p2["name"],
            "hp": hp_for_chart(p2),
            "attack": p2["stats"]["attack"],
            "defense": p2["stats"]["defense"],
            "special-attack": p2["stats"]["special-attack"],
            "special-defense": p2["stats"]["special-defense"],
            "speed": p2["stats"]["speed"],
        },
    ])
    melted = raw.melt(id_vars="pokemon", var_name="stat", value_name="value")
    return melted

st.markdown("<div class='card'><div class='card-title'>Base Stat Comparison</div>", unsafe_allow_html=True)

stat_df = build_stat_comparison_df(p1, p2)

# Stat labels
stat_df["stat"] = stat_df["stat"].str.replace("-", " ").str.title()

# Dark color tones
dark_colors = ["#4DA3FF", "#0057B8"]  # light-dark blue pair but both darker than before

fig_stats = px.bar(
    stat_df,
    x="stat",
    y="value",
    color="pokemon",
    barmode="group",
    text="value",
    color_discrete_sequence=dark_colors,
)

# Bigger + bold data labels inside bars
fig_stats.update_traces(
    texttemplate="<b>%{text}</b>",
    textposition="inside",
    textfont=dict(size=18, color="white"),
)

# Bigger + bold axis titles + tick labels
fig_stats.update_xaxes(
    title="<b>Stat</b>",
    title_font=dict(size=22, color="white"),
    tickfont=dict(size=16, color="white"),
)

fig_stats.update_yaxes(
    title="<b>Value</b>",
    title_font=dict(size=22, color="white"),
    tickfont=dict(size=16, color="white"),
    showticklabels=False,  # keep y-axis numbers hidden
)

# Gridlines
fig_stats.update_xaxes(showgrid=False, zeroline=False)
fig_stats.update_yaxes(showgrid=False, zeroline=False)

# Bigger + bold legend title + legend items (Pokémon)
fig_stats.update_layout(
    legend_title_text="<b>Pokémon</b>",
    legend=dict(
        title_font=dict(size=22, color="white"),
        font=dict(size=16, color="white"),
    ),
    margin=dict(t=60, b=40, l=20, r=20),
)

st.plotly_chart(fig_stats, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# 7. COMBAT MECHANICS

LEVEL = 50  # fixed

def compute_type_effectiveness(move_type: str, defender_types):
    if not move_type:
        return 1.0

    data = fetch_type(move_type)
    if not data:
        return 1.0

    dr = data.get("damage_relations", {})
    double_to = [t["name"].capitalize() for t in dr.get("double_damage_to", [])]
    half_to = [t["name"].capitalize() for t in dr.get("half_damage_to", [])]
    no_to = [t["name"].capitalize() for t in dr.get("no_damage_to", [])]

    eff = 1.0
    for d in defender_types:
        if d in double_to:
            eff *= 2.0
        elif d in half_to:
            eff *= 0.5
        elif d in no_to:
            eff *= 0.0
    return eff

def choose_offensive_stats(damage_class, attacker_stats, defender_stats):
    if damage_class == "physical":
        atk = attacker_stats.get("attack", 0)
        df = defender_stats.get("defense", 0)
    else:
        atk = attacker_stats.get("special-attack", 0)
        df = defender_stats.get("special-defense", 0)
    return atk, df

def stab_multiplier(move_type: str, attacker_types: list[str]) -> float:
    """Same-Type Attack Bonus: 1.5x if move type matches any attacker type."""
    if not move_type or not attacker_types:
        return 1.0
    return 1.5 if move_type in attacker_types else 1.0

def random_multiplier() -> float:
    """Pokemon-like damage randomness: 0.85 to 1.00"""
    return random.uniform(0.85, 1.00)

def compute_damage(attacker, defender, move_info):
    # Power: if None, treat as 0
    power = move_info.get("power")
    if power is None:
        power = 0

    # Accuracy: if None, treat as 100
    accuracy = move_info.get("accuracy")
    if accuracy is None:
        accuracy = 100

    move_type = move_info.get("type", "")
    damage_class = move_info.get("damage_class", "physical")

    # Accuracy check (use randint for more intuitive probability)
    if random.randint(1, 100) > int(accuracy):
        # miss
        return 0, 1.0, False, 1.0, 1.0

    atk_stat, def_stat = choose_offensive_stats(
        damage_class, attacker["stats"], defender["stats"]
    )

    eff = compute_type_effectiveness(move_type, defender["types"])

    # If immune, do 0 damage
    if eff == 0.0:
        return 0, eff, True, 1.0, 1.0

    base = ((2 * LEVEL / 5 + 2) * power * atk_stat / max(def_stat, 1)) / 50 + 2
    stab = stab_multiplier(move_type, attacker.get("types", []))
    roll = random_multiplier()

    dmg = int(base * eff * stab * roll)

    # Clamp: if the move hits and it's not immune, damage should be at least 1
    dmg = max(1, dmg)

    return dmg, eff, True, stab, roll

def simulate_battle(p1, p2, move1_info, move2_info):
    # Gmax HP rule: double HP in battle
    hp1 = int(p1["stats"]["hp"] * (2 if p1.get("is_gmax") else 1))
    hp2 = int(p2["stats"]["hp"] * (2 if p2.get("is_gmax") else 1))
    speed1 = p1["stats"]["speed"]
    speed2 = p2["stats"]["speed"]

    battle_log = []
    hp_history = [
        {"round": 0, "pokemon": p1["name"], "hp": hp1},
        {"round": 0, "pokemon": p2["name"], "hp": hp2},
    ]

    winner = "Draw"
    max_rounds = 100

    for rnd in range(1, max_rounds + 1):
        # Turn order
        if speed1 > speed2:
            order = [(p1, p2, "p1"), (p2, p1, "p2")]
        elif speed2 > speed1:
            order = [(p2, p1, "p2"), (p1, p2, "p1")]
        else:
            order = [(p1, p2, "p1"), (p2, p1, "p2")] if random.random() < 0.5 else [(p2, p1, "p2"), (p1, p2, "p1")]

        for attacker, defender, tag in order:
            if hp1 <= 0 or hp2 <= 0:
                break

            move_info = move1_info if tag == "p1" else move2_info
            dmg, eff, hit, stab, roll = compute_damage(attacker, defender, move_info)

            if tag == "p1":
                hp2 -= dmg
                defender_hp_after = max(hp2, 0)
            else:
                hp1 -= dmg
                defender_hp_after = max(hp1, 0)

            if not hit:
                note = "Missed!"
            else:
                if eff == 0:
                    note = "No effect."
                elif eff > 1.0:
                    note = "Super effective!"
                elif eff < 1.0:
                    note = "Not very effective."
                else:
                    note = ""

            battle_log.append({
                "round": rnd,
                "attacker": attacker["name"],
                "defender": defender["name"],
                "move": move_info.get("name", "Unknown Move"),
                "hit": hit,
                "damage": int(dmg) if hit else 0,
                "type_effectiveness": float(eff),
                "stab": float(stab),
                "random_roll": round(float(roll), 3),
                "total_multiplier": round(float(eff * stab * roll), 3) if hit else 0.0,
                "note": note,
                "defender_hp_after": int(defender_hp_after),
            })

            if hp1 <= 0 or hp2 <= 0:
                break

        hp_history.append({"round": rnd, "pokemon": p1["name"], "hp": max(hp1, 0)})
        hp_history.append({"round": rnd, "pokemon": p2["name"], "hp": max(hp2, 0)})

        if hp1 <= 0 and hp2 <= 0:
            winner = "Draw"
            break
        elif hp1 <= 0:
            winner = p2["name"]
            break
        elif hp2 <= 0:
            winner = p1["name"]
            break

    log_df = pd.DataFrame(battle_log)
    hp_df = pd.DataFrame(hp_history)
    return log_df, hp_df, winner

# 8. COMBAT SIMULATION UI

st.markdown(
    """
    <div class="select-hero">
      <div class="select-hero-top">
        <div>
          <div class="select-title">Combat Simulation</div>
          <div class="select-subtitle">
            Simulate a turn-based battle using real stats, type effectiveness, STAB, and damage rolls.
          </div>
        </div>
      </div>
    """,
    unsafe_allow_html=True
)

## --- BATTLE BUTTON (styled via wrapper + CSS) ---
st.markdown("<div class='battle-btn'>", unsafe_allow_html=True)
battle_button = st.button("⚔️ BATTLE! ⚔️", key="battle_btn", type="primary")
st.markdown("</div>", unsafe_allow_html=True)

if battle_button:
    if not move1_info or not move2_info:
        st.error("Both Pokémon need a valid damaging move.")
    else:
        log_df, hp_df, winner = simulate_battle(p1, p2, move1_info, move2_info)

        st.subheader("Battle Log")
        log_df_display = log_df.copy()
        log_df_display.columns = [
            c.replace("_", " ").title().replace("Hp", "HP")
            for c in log_df_display.columns
        ]
        st.dataframe(log_df_display, use_container_width=True, hide_index=True)

        st.subheader("Result")

        if winner == "Draw":
            st.info("The battle ended in a draw.")
        else:
            # Celebration animation
            st.balloons()

            # Pick the correct winner sprite
            winner_sprite = ""
            if winner == p1.get("name"):
                winner_sprite = p1.get("sprite", "")
            elif winner == p2.get("name"):
                winner_sprite = p2.get("sprite", "")

            # Show winner card with sprite + text
            st.markdown(
                f"""
                <div class="winner-card">
                    <div class="winner-title">{winner} wins the battle!</div>
                    <div class="winner-sprite-wrap">
                        <img class="winner-sprite" src="{winner_sprite}">
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div class='card'><div class='card-title'>HP Over Battle Rounds</div>", unsafe_allow_html=True)

        # Column names
        hp_df["pokemon"] = hp_df["pokemon"].str.title()

        dark_colors = ["#4DA3FF", "#0057B8"]  # same darker blue tones

        fig_hp = px.line(
            hp_df,
            x="round",
            y="hp",
            color="pokemon",
            markers=True,
            text="hp",
            color_discrete_sequence=dark_colors,
        )

        # Bigger + bold data labels
        fig_hp.update_traces(
            texttemplate="<b>%{text}</b>",
            textposition="top center",
            textfont=dict(size=16, color="white"),
            line=dict(width=3),
            marker=dict(size=8),
        )

        # Axis styling
        fig_hp.update_xaxes(
            title="<b>Round</b>",
            title_font=dict(size=22, color="white"),
            tickfont=dict(size=16, color="white"),
            showgrid=False,
            zeroline=False,
        )

        fig_hp.update_yaxes(
            title="<b>HP</b>",
            title_font=dict(size=22, color="white"),
            tickfont=dict(size=16, color="white"),
            showgrid=False,
            zeroline=False,
        )

        # Legend styling
        fig_hp.update_layout(
            legend_title_text="<b>Pokémon</b>",
            legend=dict(
                title_font=dict(size=22, color="white"),
                font=dict(size=16, color="white"),
            ),
            margin=dict(t=40, b=40, l=20, r=20),
        )

        st.plotly_chart(fig_hp, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Press the **BATTLE!** button to run the combat simulation.")

st.markdown("</div>", unsafe_allow_html=True)