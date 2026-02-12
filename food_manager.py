import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os
import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🍽️", layout="wide")

# Custom CSS für zentrierten Titel auf Mobile
st.markdown("""
    <style>
    .title-box {
        text-align: center;
        padding: 20px;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .title-text {
        color: #2e7bcf;
        font-size: 40px;
        font-weight: bold;
        line-height: 1.2;
    }
    .subtitle-text {
        color: #555;
        font-size: 20px;
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
PLANS_FILE = "weekly_plans.json"

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

# --- STATE MANAGEMENT (Rezept-Logik) ---
if 'selected_profile_key' not in st.session_state:
    st.session_state.selected_profile_key = "Neues Profil erstellen"

if 'profile_to_select' in st.session_state:
    st.session_state.selected_profile_key = st.session_state.profile_to_select
    del st.session_state.profile_to_select

# Hier speichern wir die generierten Rezepte
# Struktur: [{'day': 1, 'content': 'Pasta...', 'locked': False}, ...]
if 'recipe_slots' not in st.session_state:
    st.session_state.recipe_slots = []

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

# --- UI: TITEL (ZENTRIERT) ---
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
        
        # WIEDERHERGESTELLTE ZIELE-LISTE
        ziele_opts = sorted(["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren", "Schnelle Küche (<20 Min)", "Bio / Nachhaltig", "Meal Prep geeignet"])
        p_ziele = st.multiselect("Ziele:", ziele_opts, default=current_data.get("ziele", ["Geld sparen"]))
        
        # WIEDERHERGESTELLTE SUPERMÄRKTE
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
    
    # 1. INPUT BEREICH
    with st.container():
        st.subheader("📅 Planungsvorgaben")
        col_in1, col_in2 = st.columns(2)
        
        # TAGE SLIDER (NEU)
        days_to_plan = col_in1.slider("Anzahl Tage planen:", 1, 7, 4)
        zeit_input = col_in1.slider("Zeit pro Tag (Min)?", 0, 120, 30, step=5)
        
        # Wünsche (Umbemannt)
        manuelle_reste = col_in2.text_area("Wünsche / Reste:", "Alles offen", height=100)
        
        with st.expander("📸 Uploads (Kühlschrank/Prospekte)"):
            c_up1, c_up2 = st.columns(2)
            kuehlschrank_img = c_up1.file_uploader("Kühlschrank", type=["jpg", "png", "jpeg"])
            prospekt_files = c_up2.file_uploader("Werbeprospekte", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

    # 2. GENERIERUNGS-LOGIK
    # Wir brauchen einen Button, der "Nicht fixierte" neu generiert
    if st.button("🎲 Planung starten / Neue Vorschläge würfeln"):
        
        # Liste anpassen falls Slider geändert wurde
        current_slots = st.session_state.recipe_slots
        
        # Wenn wir mehr Tage wollen als wir haben -> auffüllen
        if len(current_slots) < days_to_plan:
            for i in range(days_to_plan - len(current_slots)):
                current_slots.append({'day': len(current_slots)+1, 'content': None, 'locked': False})
        
        # Wenn wir weniger Tage wollen -> abschneiden (aber vorsichtig)
        if len(current_slots) > days_to_plan:
            st.session_state.recipe_slots = current_slots[:days_to_plan]
            current_slots = st.session_state.recipe_slots

        # Welche Slots müssen generiert werden? (Die nicht gelockten)
        slots_to_fill = [i for i, slot in enumerate(current_slots) if not slot['locked']]
        locked_recipes = [slot['content'] for slot in current_slots if slot['locked'] and slot['content']]
        
        if not slots_to_fill:
            st.warning("Alle Tage sind fixiert! Bitte Sperre lösen, um neue zu generieren.")
        else:
            with st.spinner(f"Generiere {len(slots_to_fill)} neue Rezepte..."):
                
                # Prompt zusammenbauen
                diaet_str = ", ".join(current_data['diaet']) if isinstance(current_data['diaet'], list) else current_data['diaet']
                vermeiden_str = ", ".join(current_data.get('vermeiden_select', [])) + " " + current_data.get('vermeiden_text', "")
                
                prompt = f"""
                Du bist der Food Manager.
                
                PROFIL:
                - {current_data['erwachsene']} Erw, {current_data['kinder_ueber3']} Kind(>3), {current_data['kinder_unter3']} Kind(<3).
                - Ernährung: {diaet_str} (No-Gos: {vermeiden_str})
                - Besonderheit: {current_data.get('besonderheiten', '')}
                - Geräte: {', '.join(current_data['geraete'])}
                - Vorrat: {current_data['vorrat']}
                - Ziele: {', '.join(current_data['ziele'])}
                
                AUFGABE:
                Generiere {len(slots_to_fill)} UNTERSCHIEDLICHE Rezepte.
                
                BEREITS FIXIERTE GERICHTE (Dazu passend kochen, keine Dopplungen!):
                {json.dumps(locked_recipes)}
                
                SITUATION:
                - Zeit: {zeit_input} Min
                - Wünsche: {manuelle_reste}
                
                FORMATIERUNG (EXTREM WICHTIG):
                - Gib mir NUR die Rezepte.
                - Trenne jedes Rezept exakt mit diesem Trenner: "---TRENNER---"
                - Nutze Markdown für das Rezept (Name fett, Zutatenliste, kurze Zubereitung).
                - KEIN Einleitungstext, KEINE Einkaufsliste (die mache ich später).
                """
                
                content = [prompt]
                if kuehlschrank_img:
                    content.append(Image.open(kuehlschrank_img))
                    content.append("Kühlschrank-Inhalt")
                if prospekt_files:
                    for p in prospekt_files:
                        content.append(Image.open(p))
                        content.append("Prospekt-Angebote")

                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(content)
                    
                    # Antwort splitten am Trenner
                    new_recipes_text = response.text.split("---TRENNER---")
                    
                    # Slots füllen
                    fill_idx = 0
                    for slot_idx in slots_to_fill:
                        if fill_idx < len(new_recipes_text):
                            # Text säubern und zuweisen
                            clean_text = new_recipes_text[fill_idx].strip()
                            if clean_text:
                                st.session_state.recipe_slots[slot_idx]['content'] = clean_text
                            fill_idx += 1
                            
                except Exception as e:
                    st.error(f"Fehler bei KI: {e}")

    # 3. ANZEIGE DER REZEPTE (Karten-Ansicht)
    if st.session_state.recipe_slots:
        st.divider()
        st.subheader(f"🍳 Deine Gerichte für {len(st.session_state.recipe_slots)} Tage")
        
        # Wir gehen durch die Slots
        for i, slot in enumerate(st.session_state.recipe_slots):
            if slot['content']:
                # Optik: Fixierte Rezepte kriegen einen grünen Rahmen/Hintergrund (via Success)
                # Offene Rezepte sind normal
                
                col_card, col_lock = st.columns([5, 1])
                
                with col_card:
                    if slot['locked']:
                        st.success(f"🔒 **TAG {i+1} (FIXIERT)**\n\n" + slot['content'])
                    else:
                        st.info(f"✨ **TAG {i+1} (Vorschlag)**\n\n" + slot['content'])
                
                with col_lock:
                    # Der Lock-Switch
                    is_locked = st.checkbox("🔒 Fixieren", value=slot['locked'], key=f"lock_{i}")
                    # State sofort updaten
                    st.session_state.recipe_slots[i]['locked'] = is_locked

        st.markdown("---")
        
        # 4. FINALE EINKAUFSLISTE GENERIEREN
        if st.button("🛒 Einkaufsliste für diese Auswahl erstellen"):
            
            # Wir sammeln alle aktuellen Rezepte (egal ob gelockt oder neu)
            all_recipes_text = ""
            for i, slot in enumerate(st.session_state.recipe_slots):
                status = "FIXIERT (Zutaten Grün markieren 🟢)" if slot['locked'] else "NEU (Zutaten Gelb markieren 🟡)"
                all_recipes_text += f"REZEPT {i+1} ({status}):\n{slot['content']}\n\n"
            
            with st.spinner("Erstelle smarte Einkaufsliste..."):
                prompt_list = f"""
                Erstelle eine Einkaufsliste basierend auf diesen Rezepten.
                
                INPUT REZEPTE:
                {all_recipes_text}
                
                REGELN:
                1. Sortiere nach Kategorien (🥦 Obst/Gemüse, 🥛 Kühlregal, 🥩 Fleisch, etc.).
                2. Nutze Emojis für die Kategorien.
                3. FARB-CODIERUNG (WICHTIG):
                   - Wenn eine Zutat zu einem 'FIXIERTEN' Rezept gehört, setze ein 🟢 davor.
                   - Wenn eine Zutat zu einem 'NEUEN' Rezept gehört, setze ein 🟡 davor.
                   - Wenn sie in beiden vorkommt, nimm 🟢.
                4. Ignoriere Dinge aus dem Vorrat: {current_data['vorrat']}
                
                Ausgabe als saubere Markdown-Liste.
                """
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response_list = model.generate_content(prompt_list)
                    st.session_state.final_shopping_list = response_list.text
                except Exception as e:
                    st.error(f"Fehler Liste: {e}")

        # ANZEIGE LISTE
        if 'final_shopping_list' in st.session_state:
            st.header("🛒 Einkaufsliste")
            st.markdown(st.session_state.final_shopping_list)
