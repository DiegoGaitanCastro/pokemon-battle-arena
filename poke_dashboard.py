# 1. SETUP & CONFIGURATION

import streamlit as st
import requests
import random
import pandas as pd
import plotly.express as px
import os
import base64
from pathlib import Path

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

TYPE_COLORS = {
    "Normal": "#A8A878", "Fire": "#F08030", "Water": "#6890F0", "Electric": "#F8D030",
    "Grass": "#78C850", "Ice": "#98D8D8", "Fighting": "#C03028", "Poison": "#A040A0",
    "Ground": "#E0C068", "Flying": "#A890F0", "Psychic": "#F85888", "Bug": "#A8B820",
    "Rock": "#B8A038", "Ghost": "#705898", "Dragon": "#7038F8", "Dark": "#705848",
    "Steel": "#B8B8D0", "Fairy": "#EE99AC"
}


st.set_page_config(
    page_title="Pokémon Combat Simulator", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>

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

/* ---------- EPIC BATTLE BUTTON (CENTERED + SHINY) ---------- */

div[data-testid="stButton"] > button {
  display: inline-block !important;
  padding: 26px 70px !important;            /* size of button */
  border-radius: 22px !important;

  /* Shiny red gradient */
  background: linear-gradient(180deg, #ff6a6a 0%, #e53935 45%, #b71c1c 100%) !important;

  color: #ffffff !important;
  font-size: 2.8rem !important;             /* BIG text */
  font-weight: 1000 !important;
  letter-spacing: 0.08em !important;

  border: 1px solid rgba(255,255,255,0.28) !important;

  box-shadow:
      0 18px 46px rgba(0,0,0,0.55),
      0 0 30px rgba(255,80,80,0.35) !important;

  position: relative !important;
  overflow: hidden !important;
  transition: transform 0.12s ease, filter 0.12s ease !important;
}

/* Shine sweep */
div[data-testid="stButton"] > button::before{
  content: "";
  position: absolute;
  top: -60%;
  left: -40%;
  width: 55%;
  height: 220%;
  background: rgba(255,255,255,0.22);
  transform: rotate(25deg);
  filter: blur(2px);
}

/* Hover / active */
div[data-testid="stButton"] > button:hover{
  filter: brightness(1.12) saturate(1.10) !important;
  transform: translateY(-3px) scale(1.015) !important;
}

div[data-testid="stButton"] > button:active{
  transform: translateY(1px) scale(0.99) !important;
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

# 2. API FUNCTIONS

@st.cache_data
def fetch_pokemon(name: str):
    url = f"{BASE_URL}/pokemon/{name.lower()}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}

@st.cache_data
def fetch_move(name: str):
    url = f"{BASE_URL}/move/{name.lower().replace(' ', '-')}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}

@st.cache_data
def fetch_type(name: str):
    url = f"{BASE_URL}/type/{name.lower()}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}
    
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

@st.cache_data
def get_moves_with_types(pokemon_moves):
    """Get move types for dropdown coloring (cached)"""
    move_types = {}
    for move_name in pokemon_moves:
        move_data = fetch_move(move_name)
        move_type = (move_data.get("type") or {}).get("name", "").capitalize()
        move_types[move_name] = move_type
    return move_types

# 3. DATA PROCESSING

def extract_pokemon_basic(data: dict):
    if not data:
        return {}

    name = data.get("name", "").capitalize()

    sprite = (data.get("sprites") or {}).get("front_default", "")

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

    damaging_moves = []
    for m in data.get("moves", []):
        move_name = m["move"]["name"]
        move_data = fetch_move(move_name)
        if not move_data:
            continue
        if move_data.get("power") is not None:
            damaging_moves.append(move_name)

    return {
        "name": name,
        "sprite": sprite,
        "types": types,
        "stats": stats,
        "damaging_moves": sorted(set(damaging_moves)),
    }

def display_mystery_pokemon():
    """Display mystery silhouette if no Pokémon selected"""
    return {
        "name": "",
        "sprite": "",
        "types": [],
        "stats": {"hp": 0, "attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0},
        "damaging_moves": []
    }

# 4. POKÉMON SELECTION
st.markdown("<h2 style='text-align: left; margin-bottom: 20px;'>Select Pokémon</h2>", unsafe_allow_html=True)

col_input1, col_input2 = st.columns(2)

with col_input1:
    p1_name = st.text_input("Pokémon 1 name", value="", placeholder="Type a Pokémon name...")
with col_input2:
    p2_name = st.text_input("Pokémon 2 name", value="", placeholder="Type a Pokémon name...")


# Handle empty inputs with mystery Pokémon
if not p1_name.strip():
    p1 = display_mystery_pokemon()
else:
    p1_raw = fetch_pokemon(p1_name.strip())
    if not p1_raw:
        st.error(f"❌ Pokémon 1 not found: '{p1_name}'")
        p1 = display_mystery_pokemon()
    else:
        p1 = extract_pokemon_basic(p1_raw)

if not p2_name.strip():
    p2 = display_mystery_pokemon()
else:
    p2_raw = fetch_pokemon(p2_name.strip())
    if not p2_raw:
        st.error(f"❌ Pokémon 2 not found: '{p2_name}'")
        p2 = display_mystery_pokemon()
    else:
        p2 = extract_pokemon_basic(p2_raw)



# 5. POKÉMON DISPLAY & MOVE SELECTION

col1, col2 = st.columns(2)

with col1:
    if p1["name"]:
        st.markdown(f"<div class='poke-name'>{p1['name']}</div>", unsafe_allow_html=True)
    
    render_sprite(p1["sprite"])
    
       # Bold centered types
    type_badges_p1 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.1em;">{t}</span>'
        for t in p1["types"]
    ])

    st.markdown(f"""
    <div style='text-align: center; font-weight: bold; font-size: 1.2em; color: var(--app-text);'>
        Types: {type_badges_p1 or 'Unknown'}
    </div>
    """, unsafe_allow_html=True)

    # Weaknesses (types that deal >1x damage to this Pokémon)
    weak1 = get_weaknesses(p1["types"])

    weak_badges_p1 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.05em;">{t} x{int(mult)}</span>'
        for t, mult in weak1.items()
    ])

    st.markdown(f"""
    <div style='text-align: center; font-weight: bold; font-size: 1.15em; color: var(--app-text); margin-top: 10px;'>
        Weak against: {weak_badges_p1 if weak_badges_p1 else '—'}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='card-title'>Base Stats</div>", unsafe_allow_html=True)

    stats_df1 = pd.DataFrame({
        "Stat": ["HP","Attack","Defense","Special Attack","Special Defense","Speed"],
        "Value": [
            p1["stats"]["hp"],
            p1["stats"]["attack"],
            p1["stats"]["defense"],
            p1["stats"]["special-attack"],
            p1["stats"]["special-defense"],
            p1["stats"]["speed"],
        ],
    })
    st.dataframe(stats_df1, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='card-title'>Move Selection</div>", unsafe_allow_html=True)

    if p1["damaging_moves"]:
        move_types_p1 = get_moves_with_types(p1["damaging_moves"])

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
        st.markdown(f"<div class='poke-name'>{p2['name']}</div>", unsafe_allow_html=True)
    
    render_sprite(p2["sprite"])
    
        # Bold centered types
    type_badges_p2 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.1em;">{t}</span>'
        for t in p2["types"]
    ])

    st.markdown(f"""
    <div style='text-align: center; font-weight: bold; font-size: 1.2em; color: var(--app-text);'>
        Types: {type_badges_p2 or 'Unknown'}
    </div>
    """, unsafe_allow_html=True)

    # Weaknesses (types that deal >1x damage to this Pokémon)
    weak2 = get_weaknesses(p2["types"])

    weak_badges_p2 = " ".join([
        f'<span style="background-color:{TYPE_COLORS.get(t,"#808080")};color:white;'
        f'padding:6px 12px;border-radius:12px;font-weight:bold;font-size:1.05em;">{t} x{int(mult)}</span>'
        for t, mult in weak2.items()
    ])

    st.markdown(f"""
    <div style='text-align: center; font-weight: bold; font-size: 1.15em; color: var(--app-text); margin-top: 10px;'>
        Weak against: {weak_badges_p2 if weak_badges_p2 else '—'}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='card-title'>Base Stats</div>", unsafe_allow_html=True)

    stats_df2 = pd.DataFrame({
        "Stat": ["HP","Attack","Defense","Special Attack","Special Defense","Speed"],
        "Value": [
            p2["stats"]["hp"],
            p2["stats"]["attack"],
            p2["stats"]["defense"],
            p2["stats"]["special-attack"],
            p2["stats"]["special-defense"],
            p2["stats"]["speed"],
        ],
    })
    st.dataframe(stats_df2, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='card-title'>Move Selection</div>", unsafe_allow_html=True)

    if p2["damaging_moves"]:
        move_types_p2 = get_moves_with_types(p2["damaging_moves"])

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
    data = fetch_move(move_name)
    if not data:
        return {}
    return {
        "name": data.get("name", "").replace("-", " ").title(),
        "power": data.get("power"),
        "accuracy": data.get("accuracy"),
        "type": (data.get("type") or {}).get("name", "").capitalize(),
        "damage_class": (data.get("damage_class") or {}).get("name", ""),
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

    def is_light(hex_color):
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        brightness = (0.299*r + 0.587*g + 0.114*b)
        return brightness > 160

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
    raw = pd.DataFrame([
        {
            "pokemon": p1["name"],
            "hp": p1["stats"]["hp"],
            "attack": p1["stats"]["attack"],
            "defense": p1["stats"]["defense"],
            "special-attack": p1["stats"]["special-attack"],
            "special-defense": p1["stats"]["special-defense"],
            "speed": p1["stats"]["speed"],
        },
        {
            "pokemon": p2["name"],
            "hp": p2["stats"]["hp"],
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

    # Accuracy: if None, treat as 100 (many moves have None)
    accuracy = move_info.get("accuracy")
    if accuracy is None:
        accuracy = 100

    move_type = move_info.get("type", "")
    damage_class = move_info.get("damage_class", "physical")

    # Accuracy check
    if random.random() > (accuracy / 100.0):
        return 0, 1.0, False, 1.0, 1.0

    atk_stat, def_stat = choose_offensive_stats(
        damage_class, attacker["stats"], defender["stats"]
    )

    eff = compute_type_effectiveness(move_type, defender["types"])

    base = ((2 * LEVEL / 5 + 2) * power * atk_stat / max(def_stat, 1)) / 50 + 2
    stab = stab_multiplier(move_type, attacker.get("types", []))
    roll = random_multiplier()

    dmg = int(base * eff * stab * roll)
    if dmg < 0:
        dmg = 0

    return dmg, eff, True, stab, roll

def simulate_battle(p1, p2, move1_info, move2_info):
    hp1 = p1["stats"]["hp"]
    hp2 = p2["stats"]["hp"]
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
                "move": move_info.get("name", "Unknown Move"),
                "damage": dmg if hit else 0,
                "effectiveness": eff,
                "stab": stab,
                "roll": round(roll, 3),
                "note": note,
                "defender": defender["name"],
                "defender_hp_after": defender_hp_after,
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

st.markdown("<div class='card'><div class='card-title'>Combat Simulation</div>", unsafe_allow_html=True)

st.markdown(
    "<div style='text-align: center; margin: 25px 0 10px 0;'>",
    unsafe_allow_html=True,
)
battle_button = st.button("⚔️ BATTLE! ⚔️", key="battle_btn")
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