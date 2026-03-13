# 🏟️ Pokémon Battle Arena

⚠️ **Recommended Settings for the Best Experience**

For optimal visuals and layout:

• Click the **( ⋮ )** in the top-right corner of the Streamlit app  
• Select **Settings**  
• Change **Theme → Dark**  

Additionally, we recommend using a **70–80% browser zoom level** for the best dashboard proportions and layout balance.

---

An interactive Pokémon combat simulator built with Streamlit using real-time data from the PokeAPI.

This application allows users to:
- Select two Pokémon (manual input or randomizer)
- Apply type and class filters
- Choose damaging moves
- Simulate a full turn-based battle
- View battle logs and HP-over-time charts
- Compare base stats visually

The system is designed for performance using intelligent caching and prebuilt indices so that all interactions are instant after initial warmup.

---

## 🌐 Live App

🔗 https://pokemon-battle-arena.streamlit.app/

---

# 🚀 How to Run Locally

1. Install dependencies:

pip install -r requirements.txt

2. Run the app:

streamlit run poke_dashboard.py

---

# 🌐 Data Source

All Pokémon, move, type, and species data are retrieved from:

https://pokeapi.co/

API requests are cached to ensure responsiveness and avoid excessive calls.

---

# 📦 Application Structure

The entire application logic is contained in:

poke_dashboard.py

The file is structured into the following sections:

1. Setup & configuration  
2. Asset utilities & loader system  
3. API request layer  
4. Performance indices (type, class, move)  
5. Boot warmup gate (cold vs warm start)  
6. Data extraction helpers  
7. Pokémon selection UI  
8. Move details UI  
9. Charts  
10. Combat mechanics  
11. Simulation output  

---

# ⚡ Performance & Caching Architecture

To ensure fast performance, the application uses:

- st.cache_data for API responses  
- st.cache_resource for heavy global indices  
- Retry-enabled HTTP session  
- Concurrent fetching with ThreadPoolExecutor  

Heavy indices built at cold start:

• Type index (Pokémon per type)  
• Class index (Legendary, Mythical, etc.)  
• Global move index (power, type, accuracy, damage class)  

These are built once per server lifecycle and reused across sessions.

After warmup, all filtering operations use O(1) set membership lookups.

---

# 🖼️ Loader System

The app implements two loading states:

COLD START (Server boot)
- Fullscreen overlay  
- Optional slideshow using Images/*.jpg  
- Builds all heavy indices  
- Reruns when ready  

WARM START (New session / refresh)
- Short 1-second splash screen  
- Only shown once per session  

The slideshow is CSS-based and does not rely on JavaScript.

---

# 🎲 Pokémon Selection System

Users can:

• Manually input Pokémon names  
• Randomize both Pokémon at once  
• Randomize Pokémon individually  
• Apply filters:
  - Type filter (AND logic: must include all selected types)  
  - Class filter (Legendary, Mythical, Baby, Mega, Gmax, Battle-only, Default)  
• Toggle shiny sprites per Pokémon  

If no Pokémon matches selected filters, a graceful error message is shown.

---

# 📊 Pokémon Display

Each selected Pokémon shows:

• Sprite (with fallback placeholder if missing)  
• Type badges  
• Calculated weaknesses  
• Base stats table  
• Move selection dropdown (damaging moves only)  

Gmax forms:
- HP is doubled in battle  
- HP is visually highlighted in the stats table  

---

# 🧠 Move System

Only moves where power != None are selectable.

Move details panel displays:

• Type badge  
• Damage class badge (Physical / Special)  
• Power (color gradient)  
• Accuracy (color gradient)  

Move information is retrieved from a prebuilt global move index.

---

# ⚔️ Combat Mechanics

LEVEL is fixed at 50.

Each round:

1. Faster Pokémon attacks first  
2. If speed tie → random order  
3. Accuracy check determines hit or miss  
4. Damage formula includes:
   - Base power  
   - Attack vs Defense (physical or special)  
   - Type effectiveness  
   - STAB (1.5x if move matches attacker type)  
   - Random multiplier between 0.85 and 1.00  

Rules:
- If immune → 0 damage  
- If hit and not immune → minimum 1 damage  
- Maximum 100 rounds to prevent infinite loops  

Outputs:
- Battle log dataframe  
- HP-over-time dataframe  
- Winner (or draw)  

---

# 📈 Visualizations

After pressing BATTLE:

1. Battle log table (round-by-round breakdown)  
2. Winner announcement + celebration animation  
3. HP-over-time line chart (Plotly)  
4. Base stat comparison grouped bar chart (Plotly)  

Charts include bold labels and clean styling.

---

# 🏗️ Technical Highlights

• Retry-enabled HTTP session  
• Concurrent API fetching  
• Prebuilt type/class/move indices  
• Intelligent fallback for forms without moves  
• CSS-enhanced UI styling  
• Metallic animated battle button  
• Fullscreen loader system  
• Clean separation of data, UI, and simulation logic  

---

# 📁 Optional Assets

For enhanced visuals, include:

In root or Images/:
- pikachu-running-loading.gif  
- pokeball_pixel_icon.png  

In Images/:
- Any .jpg files (used for cold-start slideshow)  

Only .jpg files are used for the slideshow.

---

# 🧪 Notes

• First server load may take longer due to index warmup.  
• After warmup, the app runs instantly.  
• Invalid Pokémon names display a placeholder.  
• Forms without damaging moves fall back to default variety.  

---

# 👥 Contributions

This project was developed collaboratively by five team members with equal contribution across design, implementation, testing, and documentation.

### Diego Gaitán
- Dashboard layout and UI structure  
- Plotly visualizations (stat comparison & HP chart)  
- Battle log formatting and result display  
- Winner celebration UI  

### Juan José Rincón
- API integration (Pokémon, Move, Type endpoints)  
- Retry-enabled HTTP session implementation  
- Data extraction helpers and error handling logic  
- Battle damage formula implementation  

### Luka Tcheisvili
- Performance optimization and caching architecture  
- Global type, class, and move indices  
- Boot warmup gate (cold vs warm start logic)  
- Concurrency implementation with ThreadPoolExecutor  

### Cecile Tambey
- Pokémon selection system (filters, randomizers, quick reset)  
- Session state management  
- Move filtering and fallback logic  
- Edge case handling (invalid names, empty filters)  

### Romain Gelin
- CSS styling and interface design  
- Loader system (fullscreen + slideshow)  
- Custom battle and quick action buttons  
- README documentation and deployment setup  

All members participated in:
- Feature planning and architecture decisions  
- Debugging and testing  
- Code review and performance validation  
- Final deployment to Streamlit Cloud  

---

# 🏁 Summary

Pokémon Battle Arena combines:

• Real API data  
• Performance-optimized caching  
• Turn-based battle simulation  
• Styled Streamlit interface  
• Interactive data visualization  

All implemented inside a single Streamlit application.
