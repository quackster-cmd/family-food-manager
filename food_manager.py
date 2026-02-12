import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🥦", layout="wide")

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

def load_profiles():
    if not os.path.exists(PROFILE_FILE):
        return {}
    try:
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_profile(name, data):
    profiles = load_profiles()
    profiles[name] = data
    with open(PROFILE_FILE, "w") as f:
        json.dump(profiles, f, indent=4)
    return profiles

def delete_profile(name):
    profiles = load_profiles()
    if name in profiles:
        del profiles[name]
        with open(PROFILE_FILE, "w") as f:
            json.dump(profiles, f, indent=4)
    return profiles

# --- SESSION STATE LOGIK (DER FIX) ---
if 'selected_profile_key' not in st.session_state:
    st.session_state.selected_profile_key = "Neues Profil erstellen"

# HIER IST DER FIX: Wir prüfen VOR dem Zeichnen der Sidebar, ob wir wechseln müssen
if 'profile_to_select' in st.session_state:
    st.session_state.selected_profile_key = st.session_state.profile_to_select
    del st.session_state.profile_to_select # "Zwischenablage" löschen

# --- UI: SEITENLEISTE ---
with st.sidebar:
    st.header("👤 Profil-Verwaltung")
    profiles = load_profiles()
    # Alphabetisch sortieren
    profile_names = sorted(list(profiles.keys()))
    
    optionen = ["Neues Profil erstellen"] + profile_names
    
    # Fallback, falls gelöschtes Profil noch ausgewählt war
    if st.session_state.selected_profile_key not in optionen:
        st.session_state.selected_profile_key = "Neues Profil erstellen"

    selected_profile_name = st.selectbox(
        "Aktives Profil wählen", 
        optionen,
        key="selected_profile_key"
    )

    if selected_profile_name != "Neues Profil erstellen":
        st.divider()
        if st.button(f"🗑️ Profil '{selected_profile_name}' löschen"):
            delete_profile(selected_profile_name)
            # Auch beim Löschen nutzen wir den Trick:
            st.session_state.profile_to_select = "Neues Profil erstellen"
            st.rerun()

# --- UI: HAUPTBEREICH ---
st.title("🥦 Food & Family Manager")

current_data = {}
is_new_profile = (selected_profile_name == "Neues Profil erstellen")

if is_new_profile:
    st.info("🆕 Lege hier dein Basis-Profil an.")
    profile_name_input = st.text_input("Name des Profils", "Meine Familie")
else:
    current_data = profiles[selected_profile_name]
    profile_name_input = selected_profile_name
    st.success(f"✅ Profil **{selected_profile_name}** ist aktiv.")

# --- PRESET-FORMULAR ---
with st.expander("⚙️ Profil-Einstellungen & Presets bearbeiten", expanded=is_new_profile):
    
    with st.form("preset_form"):
        st.write("### 1. Wer isst mit?")
        col1, col2, col3 = st.columns(3)
        p_erwachsene = col1.number_input("Erwachsene", 1, 10, current_data.get("erwachsene", 2))
        p_kinder_ueber3 = col2.number_input("Kinder (>3 Jahre)", 0, 10, current_data.get("kinder_ueber3", 0))
        p_kinder_unter3 = col3.number_input("Kinder (<3 Jahre)", 0, 10, current_data.get("kinder_unter3", 0))

        st.write("### 2. Dauerhafte Besonderheiten")
        st.caption("Infos, die IMMER gelten (z.B. 'Baby 8M isst Brei', 'Papa Keto').")
        default_besonderheiten = current_data.get("besonderheiten", "Baby (8 Monate) bekommt Beikost/Brei.")
        p_besonderheiten = st.text_area("Profil-Details:", default_besonderheiten)

        st.write("### 3. Ernährung & Ausschluss")
        
        diaet_optionen = sorted(["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier", "Low Carb", "Keto"])
        vermeiden_optionen = sorted(["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Koriander", "Meeresfrüchte", "Paprika", "Zwiebeln", "Knoblauch"])
        
        # Mehrfachauswahl Logik (Repair)
        saved_diaet = current_data.get("diaet", ["Ausgewogen (Alles)"])
        if isinstance(saved_diaet, str): 
            saved_diaet = [saved_diaet]
            
        p_diaet = st.multiselect("Ernährungsweise (Mehrfachwahl):", diaet_optionen, default=saved_diaet)
        
        p_vermeiden = st.multiselect(
            "Zutaten vermeiden:",
            vermeiden_optionen,
            default=current_data.get("vermeiden", [])
        )

        st.write("### 4. Geräte & Ziele")
        geraete_liste = sorted(["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker", "Dampfgarer", "Grill"])
        p_geraete = st.multiselect("Geräte:", geraete_liste, default=current_data.get("geraete", ["Backofen", "Herd"]))

        ziele_liste = sorted(["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren", "Schnelle Küche (<20 Min)"])
        p_ziele = st.multiselect("Standard-Ziele:", ziele_liste, default=current_data.get("ziele", ["Geld sparen"]))
        
        supermarkt_liste = sorted(["Aldi", "Lidl", "Rewe", "Edeka", "Marktkauf", "Hit", "Netto", "Penny", "Kaufland", "DM/Rossmann"])
        p_shops = st.multiselect("Supermärkte:", supermarkt_liste, default=current_data.get("shops", ["Aldi", "Rewe"]))

        st.write("### 5. Vorrat (Immer da)")
        vorrat_default = "Nudeln, Reis, Salz, Pfeffer, Öl, Mehl, Zucker, Gewürze"
        p_vorrat = st.text_area("Eiserner Vorrat:", current_data.get("vorrat", vorrat_default))

        # Speichern Button
        submitted = st.form_submit_button("💾 Profil Speichern")
        
        if submitted:
            if not profile_name_input:
                st.error("Bitte gib dem Profil einen Namen!")
            else:
                new_profile_data = {
                    "erwachsene": p_erwachsene,
                    "kinder_ueber3": p_kinder_ueber3,
                    "kinder_unter3": p_kinder_unter3,
                    "besonderheiten": p_besonderheiten,
                    "diaet": p_diaet,
                    "vermeiden": p_vermeiden,
                    "geraete": p_geraete,
                    "ziele": p_ziele,
                    "shops": p_shops,
                    "vorrat": p_vorrat
                }
                save_profile(profile_name_input, new_profile_data)
                
                # DER FIX: Wir schreiben in die Zwischenablage und laden neu
                st.session_state.profile_to_select = profile_name_input
                st.success(f"Profil '{profile_name_input}' gespeichert!")
                st.rerun()

# --- PLANER ---
if not is_new_profile:
    st.divider()
    st.header(f"📅 Planung für: {selected_profile_name}")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        zeit_input = st.slider("Zeit pro Tag (Min)?", 0, 120, 30, step=5)
        wochen_besonderheit = st.text_input("Was steht diese Woche an?", "Samstag Grillen, Sonntag Oma zu Besuch")
    with col_input2:
        manuelle_reste = st.text_area("Reste / Aktuelle Gelüste:", "Paprika muss weg, Lust auf Nudeln")

    st.subheader("📸 Uploads (Optional)")
    upload_cols = st.columns(2)
    kuehlschrank_img = upload_cols[0].file_uploader("Kühlschrank Foto", type=["jpg", "png", "jpeg"])
    prospekt_files = upload_cols[1].file_uploader("Prospekte (Bilder)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

    generate_btn = st.button("🚀 Plan erstellen")

    if generate_btn:
        with st.spinner("KI analysiert Profil, Vorrat, Prospekte und Wünsche..."):
            
            diaet_str = ", ".join(current_data['diaet']) if isinstance(current_data['diaet'], list) else current_data['diaet']
            
            prompt = f"""
            Du bist der 'Food & Family Manager' - ein intelligenter KI-Koch.
            
            1. FESTES PROFIL (immer beachten):
            - Personen: {current_data['erwachsene']} Erw, {current_data['kinder_ueber3']} Kinder (>3), {current_data['kinder_unter3']} Kinder (<3).
            - WICHTIGE BESONDERHEITEN: {current_data.get('besonderheiten', 'Keine')}
            - Ernährung: {diaet_str}
            - No-Gos: {', '.join(current_data['vermeiden'])}
            - Geräte: {', '.join(current_data['geraete'])}
            - Supermärkte: {', '.join(current_data['shops'])}
            - VORRAT (NICHT KAUFEN): {current_data['vorrat']}
            - Standard-Ziele: {', '.join(current_data['ziele'])}
            
            2. AKTUELLE WOCHE:
            - Zeitlimit: {zeit_input} Min
            - Events/Besonderheit: {wochen_besonderheit}
            - Reste/Wünsche: {manuelle_reste}
            
            AUFGABE:
            1. Analysiere Bilder (falls vorhanden: Kühlschrank & Prospekte).
            2. Erstelle einen Essensplan (3-4 Gerichte).
            3. Berücksichtige die "WICHTIGE BESONDERHEITEN" (z.B. Brei für Baby, Diät für Papa).
            4. Erstelle Einkaufsliste (sortiert nach Supermarkt-Regal).
            
            Output bitte schön formatiert mit Markdown. Nutze Emojis.
            """
            
            content_parts = [prompt]
            
            if kuehlschrank_img:
                img = Image.open(kuehlschrank_img)
                content_parts.append(img)
                content_parts.append("Kühlschrank-Foto")
            
            if prospekt_files:
                for p_file in prospekt_files:
                    try:
                        p_img = Image.open(p_file)
                        content_parts.append(p_img)
                        content_parts.append("Supermarkt-Angebot")
                    except:
                        pass 

            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(content_parts)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Fehler: {e}")
