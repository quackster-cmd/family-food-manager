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
    with open(PROFILE_FILE, "r") as f:
        return json.load(f)

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

# --- SESSION STATE INITIALISIERUNG ---
# Damit wir nach dem Speichern direkt das neue Profil auswählen können
if 'selected_profile_key' not in st.session_state:
    st.session_state.selected_profile_key = "Neues Profil erstellen"

# --- UI: SEITENLEISTE ---
with st.sidebar:
    st.header("👤 Profil-Verwaltung")
    profiles = load_profiles()
    profile_names = list(profiles.keys())
    
    # Dropdown-Logik: Wir nutzen den Session State, um die Auswahl zu steuern
    optionen = ["Neues Profil erstellen"] + profile_names
    
    # Fallback, falls das gespeicherte Profil gelöscht wurde
    if st.session_state.selected_profile_key not in optionen:
        st.session_state.selected_profile_key = "Neues Profil erstellen"

    selected_profile_name = st.selectbox(
        "Aktives Profil wählen", 
        optionen,
        key="selected_profile_key" # Verbindet Widget mit Session State
    )

    # Lösch-Button (Nur anzeigen, wenn es nicht "Neues Profil" ist)
    if selected_profile_name != "Neues Profil erstellen":
        st.divider()
        if st.button(f"🗑️ Profil '{selected_profile_name}' löschen"):
            delete_profile(selected_profile_name)
            st.session_state.selected_profile_key = "Neues Profil erstellen" # Reset auf Neu
            st.rerun() # Seite neu laden

# --- UI: HAUPTBEREICH ---
st.title("🥦 Food & Family Manager")

# Variablen vorbereiten
current_data = {}
is_new_profile = (selected_profile_name == "Neues Profil erstellen")

# --- PROFIL LOGIK ---
if is_new_profile:
    st.info("🆕 Lege hier dein Basis-Profil an.")
    profile_name_input = st.text_input("Name des Profils", "Meine Familie")
else:
    current_data = profiles[selected_profile_name]
    profile_name_input = selected_profile_name
    # Kleiner Hinweis, welches Profil aktiv ist
    st.success(f"✅ Profil **{selected_profile_name}** ist aktiv.")

# --- DAS PRESET-FORMULAR (EXPANDER) ---
with st.expander("⚙️ Profil-Einstellungen & Presets bearbeiten", expanded=is_new_profile):
    
    with st.form("preset_form"):
        st.write("### 1. Wer isst mit?")
        col1, col2, col3 = st.columns(3)
        p_erwachsene = col1.number_input("Erwachsene", 1, 10, current_data.get("erwachsene", 2))
        p_kinder_ueber3 = col2.number_input("Kinder (>3 Jahre)", 0, 10, current_data.get("kinder_ueber3", 0))
        p_kinder_unter3 = col3.number_input("Kinder (<3 Jahre)", 0, 10, current_data.get("kinder_unter3", 0))

        st.write("### 2. Dauerhafte Besonderheiten")
        st.caption("Infos, die IMMER gelten (z.B. 'Baby 8M isst Brei/BLW', 'Papa macht Keto').")
        default_besonderheiten = current_data.get("besonderheiten", "Baby (8 Monate) bekommt Beikost/Brei.")
        p_besonderheiten = st.text_area("Profil-Details:", default_besonderheiten)

        st.write("### 3. Ernährung & Ausschluss")
        diaet_optionen = ["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier"]
        curr_diaet = current_data.get("diaet", "Ausgewogen (Alles)")
        idx_diaet = diaet_optionen.index(curr_diaet) if curr_diaet in diaet_optionen else 0
        p_diaet = st.selectbox("Ernährungsweise", diaet_optionen, index=idx_diaet)
        
        vermeiden_default = current_data.get("vermeiden", [])
        p_vermeiden = st.multiselect(
            "Zutaten vermeiden:",
            ["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Koriander", "Meeresfrüchte", "Paprika"],
            default=vermeiden_default
        )

        st.write("### 4. Geräte & Ziele")
        geraete_liste = ["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker"]
        p_geraete = st.multiselect("Geräte:", geraete_liste, default=current_data.get("geraete", ["Herd", "Backofen"]))

        ziele_liste = ["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren"]
        p_ziele = st.multiselect("Standard-Ziele:", ziele_liste, default=current_data.get("ziele", ["Geld sparen"]))
        
        supermarkt_liste = ["Aldi", "Lidl", "Rewe", "Edeka", "Marktkauf", "Hit", "Netto", "Penny", "Kaufland"]
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
                
                # TRICK: Wir setzen das neue Profil als "aktiv" im Session State
                st.session_state.selected_profile_key = profile_name_input
                
                st.success(f"Profil '{profile_name_input}' gespeichert!")
                st.rerun() # Erzwingt sofortiges Neuladen der Seite mit den neuen Daten

# --- WOCHENPLANER (NUR SICHTBAR WENN PROFIL GELADEN) ---
if not is_new_profile:
    st.divider()
    st.header(f"📅 Planung für: {selected_profile_name}")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        # ZEIT-SLIDER UPDATE: 0-120 in 5er Schritten
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
            
            # PROMPT BAUEN
            prompt = f"""
            Du bist der 'Food & Family Manager' - ein intelligenter KI-Koch.
            
            1. FESTES PROFIL (immer beachten):
            - Personen: {current_data['erwachsene']} Erw, {current_data['kinder_ueber3']} Kinder (>3), {current_data['kinder_unter3']} Kinder (<3).
            - WICHTIGE BESONDERHEITEN: {current_data.get('besonderheiten', 'Keine')}
            - Ernährung: {current_data['diaet']}
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
            
            # Daten für KI vorbereiten
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
