import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os
import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🍽️", layout="wide")

# --- CSS / DESIGN ---
# Wir definieren KEINE festen Hintergrundfarben für Container.
# Wir stylen nur den Titel schick. Der Rest passt sich dem System (Hell/Dunkel) an.
st.markdown("""
    <style>
    .title-box {
        text-align: center;
        padding: 15px;
        margin-bottom: 25px;
    }
    .title-text {
        font-size: 2.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        /* Fallback für Browser die Text-Fill nicht können */
        color: #FF6B6B; 
    }
    /* Intro-Box Styling (Dezent) */
    .intro-box {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        font-style: italic;
        border-left: 5px solid #4ECDC4;
    }
    </style>
    """, unsafe_allow_html=True)

# --- API KEY SETUP ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        st.error("🚨 FEHLER: Der API Key fehlt in den Streamlit Secrets!")
        st.stop()
except Exception as e:
    st.error(f"🚨 Fehler beim Laden des Keys: {e}")
    st.stop()

# --- DATEN-MANAGEMENT ---
PROFILE_FILE = "user_profiles.json"

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def save_profile(name, data):
    profiles = load_json(PROFILE_FILE)
    profiles[name] = data
    save_json(PROFILE_FILE, profiles)

def delete_profile(name):
    profiles = load_json(PROFILE_FILE)
    if name in profiles:
        del profiles[name]
        save_json(PROFILE_FILE, profiles)

# --- STATE MANAGEMENT ---
if 'selected_profile_key' not in st.session_state:
    st.session_state.selected_profile_key = "Neues Profil erstellen"

if 'profile_to_select' in st.session_state:
    st.session_state.selected_profile_key = st.session_state.profile_to_select
    del st.session_state.profile_to_select

# Struktur: [{'day': 1, 'content': 'Pasta...', 'locked': False}, ...]
if 'recipe_slots' not in st.session_state:
    st.session_state.recipe_slots = []

# Hier speichern wir die Begrüßung separat
if 'intro_text' not in st.session_state:
    st.session_state.intro_text = ""

# --- UI: SEITENLEISTE ---
with st.sidebar:
    st.header("👤 Einstellungen")
    profiles = load_json(PROFILE_FILE)
    profile_names = sorted(list(profiles.keys()))
    optionen = ["Neues Profil erstellen"] + profile_names
    
    if st.session_state.selected_profile_key not in optionen:
        st.session_state.selected_profile_key = "Neues Profil erstellen"

    selected_profile_name = st.selectbox("Profil wählen", optionen, key="selected_profile_key")

    if selected_profile_name != "Neues Profil erstellen":
        st.divider()
        with st.expander("Gefahrenzone"):
            if st.button(f"🗑️ Profil löschen"):
                delete_profile(selected_profile_name)
                st.session_state.profile_to_select = "Neues Profil erstellen"
                st.rerun()

# --- UI: TITEL ---
st.markdown("""
<div class="title-box">
    <div class="title-text">🍽️ Food & Family<br>Manager</div>
</div>
""", unsafe_allow_html=True)

current_data = {}
is_new_profile = (selected_profile_name == "Neues Profil erstellen")

if is_new_profile:
    st.info("🆕 Bitte erstelle zuerst ein Profil.")
    profile_name_input = st.text_input("Profilname", "Meine Familie")
else:
    current_data = profiles[selected_profile_name]
    profile_name_input = selected_profile_name

# --- PROFIL BEARBEITEN ---
with st.expander("⚙️ Profil bearbeiten", expanded=is_new_profile):
    with st.form("preset_form"):
        st.write("### 1. Wer isst mit?")
        c1, c2, c3 = st.columns(3)
        p_erw = c1.number_input("Erwachsene", 1, 10, current_data.get("erwachsene", 2))
        p_k3 = c2.number_input("Kinder (>3)", 0, 10, current_data.get("kinder_ueber3", 0))
        p_ku3 = c3.number_input("Kinder (<3)", 0, 10, current_data.get("kinder_unter3", 0))

        st.write("### 2. Besonderheiten & Ernährung")
        p_details = st.text_area("Dauerhafte Infos:", current_data.get("besonderheiten", ""))
        
        diaet_opts = sorted(["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier", "Low Carb", "Keto"])
        saved_diaet = current_data.get("diaet", ["Ausgewogen (Alles)"])
        if isinstance(saved_diaet, str): saved_diaet = [saved_diaet]
        p_diaet = st.multiselect("Ernährung:", diaet_opts, default=saved_diaet)

        col_av1, col_av2 = st.columns(2)
        verm_opts = sorted(["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Paprika", "Zwiebeln", "Knoblauch", "Koriander"])
        p_verm_sel = col_av1.multiselect("Vermeiden (Auswahl):", verm_opts, default=current_data.get("vermeiden_select", []))
        p_verm_txt = col_av2.text_input("Vermeiden (Freitext):", value=current_data.get("vermeiden_text", ""))

        st.write("### 3. Haushalt & Vorrat")
        geraete_opts = sorted(["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker", "Grill", "Dampfgarer"])
        p_geraete = st.multiselect("Geräte im Haushalt:", geraete_opts, default=current_data.get("geraete", ["Backofen", "Herd"]))
        
        ziele_opts = sorted(["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren", "Schnelle Küche (<20 Min)", "Bio / Nachhaltig", "Meal Prep geeignet"])
        p_ziele = st.multiselect("Ziele:", ziele_opts, default=current_data.get("ziele", ["Geld sparen"]))
        
        shop_opts = sorted(["Aldi", "Lidl", "Rewe", "Edeka", "Netto", "Penny", "Kaufland", "DM", "Rossmann", "Marktkauf", "Hit", "Globus"])
        p_shops = st.multiselect("Supermärkte:", shop_opts, default=current_data.get("shops", ["Aldi", "Rewe"]))
        
        p_vorrat = st.text_area("Ständiger Vorrat:", current_data.get("vorrat", "Nudeln, Reis, Salz, Pfeffer, Öl, Mehl, Zucker"))

        if st.form_submit_button("💾 Profil Speichern"):
            if not profile_name_input:
                st.error("Name fehlt!")
            else:
                new_data = {
                    "erwachsene": p_erw, "kinder_ueber3": p_k3, "kinder_unter3": p_ku3,
                    "besonderheiten": p_details, "diaet": p_diaet,
                    "vermeiden_select": p_verm_sel, "vermeiden_text": p_verm_txt,
                    "geraete": p_geraete, "ziele": p_ziele, "shops": p_shops, "vorrat": p_vorrat
                }
                save_profile(profile_name_input, new_data)
                st.session_state.profile_to_select = profile_name_input
                st.rerun()

# === PLANER ===
if not is_new_profile:
    st.divider()
    
    # --- INPUT BEREICH (EINKLAPPBAR) ---
    inputs_expanded = not bool(st.session_state.recipe_slots)
    
    with st.expander("📝 Planungsvorgaben & Uploads", expanded=inputs_expanded):
        col_in1, col_in2 = st.columns(2)
        days_to_plan = col_in1.slider("Anzahl Tage planen:", 1, 7, 4)
        zeit_input = col_in1.slider("Zeit pro Tag (Min)?", 0, 120, 30, step=5)
        manuelle_reste = col_in2.text_area("Wünsche / Reste:", "Alles offen", height=100)
        
        c_up1, c_up2 = st.columns(2)
        kuehlschrank_img = c_up1.file_uploader("Kühlschrank", type=["jpg", "png", "jpeg"])
        prospekt_files = c_up2.file_uploader("Werbeprospekte", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

        # INITIALER START BUTTON
        if not st.session_state.recipe_slots:
            if st.button("🚀 Erste Planung starten", type="primary"):
                st.session_state.recipe_slots = [{'day': i+1, 'content': None, 'locked': False} for i in range(days_to_plan)]
                st.rerun()

    # --- ANZEIGE & LOGIK ---
    if st.session_state.recipe_slots:
        
        # 1. GENERIERUNG
        current_slots = st.session_state.recipe_slots
        
        # Slider Anpassung
        if len(current_slots) < days_to_plan:
            for i in range(days_to_plan - len(current_slots)):
                current_slots.append({'day': len(current_slots)+1, 'content': None, 'locked': False})
        elif len(current_slots) > days_to_plan:
            st.session_state.recipe_slots = current_slots[:days_to_plan]
            current_slots = st.session_state.recipe_slots
            
        slots_to_fill = [i for i, slot in enumerate(current_slots) if not slot['content']]
        
        if slots_to_fill:
            with st.spinner(f"Der KI-Koch brutzelt {len(slots_to_fill)} neue Ideen..."):
                locked_recipes = [slot['content'] for slot in current_slots if slot['locked'] and slot['content']]
                
                diaet_str = ", ".join(current_data['diaet']) if isinstance(current_data['diaet'], list) else current_data['diaet']
                vermeiden_str = ", ".join(current_data.get('vermeiden_select', [])) + " " + current_data.get('vermeiden_text', "")
                
                # --- PROMPT MIT BEGRÜSSUNG ---
                prompt = f"""
                Du bist der Food Manager.
                PROFIL: {current_data['erwachsene']} Erw, {current_data['kinder_ueber3']} Kind(>3), {current_data['kinder_unter3']} Kind(<3).
                Ernährung: {diaet_str} (No-Gos: {vermeiden_str}). Vorrat: {current_data['vorrat']}.
                Ziele: {', '.join(current_data['ziele'])}.
                
                AUFGABE:
                1. Schreibe ZUERST eine kurze, nette Begrüßung und erkläre, wie du die Wünsche berücksichtigt hast (Max 2-3 Sätze).
                2. Mache dann den Trenner: "---TRENNER---"
                3. Generiere dann EXAKT {len(slots_to_fill)} UNTERSCHIEDLICHE Rezepte.
                
                SITUATION: Zeit: {zeit_input} Min. Wünsche: {manuelle_reste}.
                
                FORMATIERUNG DER REZEPTE (NACH DEM ERSTEN TRENNER):
                - Trenne jedes Rezept mit: "---TRENNER---"
                - Inhalt: Markdown.
                - TITEL: Mit passendem Emoji am Anfang (z.B. "🍝 Spaghetti Bolognese").
                - STRUKTUR: Titel fett, kurze Beschreibung, Zutatenliste, Zubereitungsschritte.
                """
                
                content = [prompt]
                if kuehlschrank_img:
                    content.append(Image.open(kuehlschrank_img))
                    content.append("Kühlschrank")
                if prospekt_files:
                    for p in prospekt_files:
                        content.append(Image.open(p))
                        content.append("Prospekt")

                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(content)
                    
                    # --- SPLITTEN ---
                    # Teil 0 = Begrüßung
                    # Teil 1 bis N = Rezepte
                    parts = response.text.split("---TRENNER---")
                    
                    # Begrüßung speichern (Nur wenn wir sie noch nicht haben oder neu würfeln)
                    if len(parts) > 0:
                        st.session_state.intro_text = parts[0].strip()
                    
                    # Rezepte extrahieren (ab Index 1)
                    new_recipes = [p.strip() for p in parts[1:] if p.strip()]
                    
                    fill_idx = 0
                    for slot_idx in slots_to_fill:
                        if fill_idx < len(new_recipes):
                            st.session_state.recipe_slots[slot_idx]['content'] = new_recipes[fill_idx]
                            fill_idx += 1
                        else:
                            # Fallback
                            if not st.session_state.recipe_slots[slot_idx]['content']:
                                st.session_state.recipe_slots[slot_idx]['content'] = "⚠️ Bitte nochmal würfeln."
                    
                    st.rerun() 
                except Exception as e:
                    st.error(f"Fehler: {e}")

        # 2. ANZEIGE BEGRÜSSUNG (Separat!)
        if st.session_state.intro_text:
            st.markdown(f'<div class="intro-box">{st.session_state.intro_text}</div>', unsafe_allow_html=True)

        # 3. ANZEIGE DER KARTEN (Native Streamlit Container)
        st.subheader(f"🍳 Dein Menü ({days_to_plan} Gerichte)")
        
        for i, slot in enumerate(st.session_state.recipe_slots):
            if slot['content']:
                
                # Container passt sich automatisch dem Dark Mode an (kein weißer Hintergrundzwang)
                with st.container(border=True):
                    
                    c_head1, c_head2 = st.columns([5, 1])
                    is_locked = slot['locked']
                    
                    with c_head1:
                        if is_locked:
                            st.success(f"✅ **Tag {i+1}**: FIXIERT")
                        else:
                            st.caption(f"Vorschlag für Tag {i+1}")
                    
                    with c_head2:
                        lock_state = st.toggle("Lock", value=is_locked, key=f"lock_{i}", label_visibility="collapsed")
                        if lock_state != is_locked:
                            st.session_state.recipe_slots[i]['locked'] = lock_state
                            st.rerun()

                    # Rezeptinhalt
                    st.markdown(slot['content'])

        # 4. ACTION BUTTONS
        st.divider()
        col_act1, col_act2 = st.columns(2)
        
        with col_act1:
            if st.button("🎲 Offene Gerichte neu würfeln", use_container_width=True):
                # Intro löschen, damit es neu generiert wird
                st.session_state.intro_text = ""
                for slot in st.session_state.recipe_slots:
                    if not slot['locked']:
                        slot['content'] = None
                st.rerun()

        with col_act2:
            if st.button("🛒 Einkaufsliste (Alles Einloggen)", type="primary", use_container_width=True):
                for slot in st.session_state.recipe_slots:
                    slot['locked'] = True
                
                with st.spinner("Erstelle finale Liste..."):
                    all_text = "\n".join([s['content'] for s in st.session_state.recipe_slots if s['content']])
                    p_list = f"""
                    Erstelle Einkaufsliste für diese Rezepte:
                    {all_text}
                    Regeln: Sortiert nach Supermarkt-Bereich. Emojis nutzen.
                    Vorrat ignorieren: {current_data['vorrat']}
                    """
                    try:
                        m = genai.GenerativeModel('gemini-2.5-flash')
                        res = m.generate_content(p_list)
                        st.session_state.final_shopping_list = res.text
                    except:
                        pass
                st.rerun()

    # 5. FINALE LISTE
    if 'final_shopping_list' in st.session_state:
        st.divider()
        st.success("🛒 Deine Einkaufsliste ist fertig!")
        st.markdown(st.session_state.final_shopping_list)
        
        if st.button("🔄 Liste schließen / Neu anfangen"):
            del st.session_state.final_shopping_list
            st.rerun()
