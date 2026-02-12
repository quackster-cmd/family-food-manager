import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os
import datetime

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

# --- DATEI-MANAGEMENT ---
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

def save_week_plan(profile_name, week_key, plan_text):
    plans = load_json(PLANS_FILE)
    if profile_name not in plans:
        plans[profile_name] = {}
    plans[profile_name][week_key] = plan_text
    save_json(PLANS_FILE, plans)

def get_week_plan(profile_name, week_key):
    plans = load_json(PLANS_FILE)
    return plans.get(profile_name, {}).get(week_key, None)

def delete_week_plan(profile_name, week_key):
    plans = load_json(PLANS_FILE)
    if profile_name in plans and week_key in plans[profile_name]:
        del plans[profile_name][week_key]
        save_json(PLANS_FILE, plans)

# --- HILFSFUNKTIONEN ---
def get_current_week_info():
    today = datetime.date.today()
    year, week, _ = today.isocalendar()
    return year, week

# --- SESSION STATE INITIALISIERUNG ---
if 'selected_profile_key' not in st.session_state:
    st.session_state.selected_profile_key = "Neues Profil erstellen"

if 'profile_to_select' in st.session_state:
    st.session_state.selected_profile_key = st.session_state.profile_to_select
    del st.session_state.profile_to_select

# --- UI: SEITENLEISTE (PROFIL & WOCHE) ---
with st.sidebar:
    st.header("👤 Einstellungen")
    
    # 1. Profilwahl
    profiles = load_json(PROFILE_FILE)
    profile_names = sorted(list(profiles.keys()))
    optionen = ["Neues Profil erstellen"] + profile_names
    
    if st.session_state.selected_profile_key not in optionen:
        st.session_state.selected_profile_key = "Neues Profil erstellen"

    selected_profile_name = st.selectbox(
        "Profil wählen", 
        optionen,
        key="selected_profile_key"
    )

    # 2. Wochenwahl (Nur wenn Profil existiert)
    current_year, current_week = get_current_week_info()
    selected_week_label = "Keine"
    week_key = "none"
    
    if selected_profile_name != "Neues Profil erstellen":
        st.divider()
        st.subheader("📅 Woche auswählen")
        
        # Wir bieten aktuelle und nächste Woche an
        w1_label = f"KW {current_week} (Aktuell)"
        w2_label = f"KW {current_week + 1} (Nächste)"
        w3_label = f"KW {current_week + 2} (Übernächste)"
        
        selected_week_label = st.radio("Für welche Woche planen?", [w1_label, w2_label, w3_label])
        
        # Key generieren z.B. "2024-W07"
        week_num = current_week
        if "Nächste" in selected_week_label: week_num += 1
        if "Übernächste" in selected_week_label: week_num += 2
        
        week_key = f"{current_year}-W{week_num}"
        
        # Profil Löschen Button ganz unten
        st.divider()
        with st.expander("Gefahrenzone"):
            if st.button(f"🗑️ Profil löschen"):
                delete_profile(selected_profile_name)
                st.session_state.profile_to_select = "Neues Profil erstellen"
                st.rerun()

# --- UI: HAUPTBEREICH ---
st.title("🥦 Food & Family Manager")

current_data = {}
is_new_profile = (selected_profile_name == "Neues Profil erstellen")

# === FALL A: NEUES PROFIL ANLEGEN ===
if is_new_profile:
    st.info("🆕 Bitte erstelle zuerst ein Profil, bevor du planen kannst.")
    profile_name_input = st.text_input("Name des Profils", "Meine Familie")
else:
    current_data = profiles[selected_profile_name]
    profile_name_input = selected_profile_name

# === PROFIL BEARBEITEN (EXPANDER) ===
# Wir klappen es automatisch zu, wenn es nicht neu ist
with st.expander("⚙️ Profil-Einstellungen bearbeiten", expanded=is_new_profile):
    with st.form("preset_form"):
        st.write("### 1. Wer isst mit?")
        c1, c2, c3 = st.columns(3)
        p_erw = c1.number_input("Erwachsene", 1, 10, current_data.get("erwachsene", 2))
        p_k3 = c2.number_input("Kinder (>3)", 0, 10, current_data.get("kinder_ueber3", 0))
        p_ku3 = c3.number_input("Kinder (<3)", 0, 10, current_data.get("kinder_unter3", 0))

        st.write("### 2. Besonderheiten & Ernährung")
        p_details = st.text_area("Dauerhafte Infos (z.B. 'Baby isst Brei'):", current_data.get("besonderheiten", ""))
        
        diaet_opts = sorted(["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier", "Low Carb", "Keto"])
        saved_diaet = current_data.get("diaet", ["Ausgewogen (Alles)"])
        if isinstance(saved_diaet, str): saved_diaet = [saved_diaet]
        p_diaet = st.multiselect("Ernährung:", diaet_opts, default=saved_diaet)

        col_av1, col_av2 = st.columns(2)
        verm_opts = sorted(["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Paprika", "Zwiebeln"])
        p_verm_sel = col_av1.multiselect("Vermeiden (Auswahl):", verm_opts, default=current_data.get("vermeiden_select", []))
        p_verm_txt = col_av2.text_input("Vermeiden (Freitext):", value=current_data.get("vermeiden_text", ""))

        st.write("### 3. Haushalt & Vorrat")
        geraete_opts = sorted(["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker", "Grill"])
        p_geraete = st.multiselect("Geräte:", geraete_opts, default=current_data.get("geraete", ["Backofen", "Herd"]))
        
        ziele_opts = sorted(["Geld sparen", "Weniger Fleisch", "Schnelle Küche (<20 Min)", "Proteinreich", "Einkäufe minimieren"])
        p_ziele = st.multiselect("Ziele:", ziele_opts, default=current_data.get("ziele", ["Geld sparen"]))
        
        shop_opts = sorted(["Aldi", "Lidl", "Rewe", "Edeka", "Netto", "Penny", "Kaufland", "DM"])
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

# === FALL B: PLANUNG (NUR WENN PROFIL GEWÄHLT) ===
if not is_new_profile:
    st.divider()
    
    # Prüfen: Gibt es schon einen Plan für diese Woche?
    existing_plan = get_week_plan(selected_profile_name, week_key)
    
    if existing_plan:
        # --- ANSICHT: PLAN IST EINGELOGGT ---
        st.success(f"🔒 Plan für **{selected_week_label}** ist eingeloggt!")
        
        col_btn1, col_btn2 = st.columns([1, 4])
        if col_btn1.button("🗑️ Plan löschen"):
            delete_week_plan(selected_profile_name, week_key)
            st.rerun()
        
        st.markdown("---")
        st.markdown(existing_plan)
        
    else:
        # --- ANSICHT: PLANER (NOCH NICHTS GESPEICHERT) ---
        st.header(f"🧑‍🍳 Planung erstellen: {selected_week_label}")
        
        with st.expander("📝 Planungsvorgaben (Hier klicken zum Ändern)", expanded=True):
            col_in1, col_in2 = st.columns(2)
            zeit_input = col_in1.slider("Zeit pro Tag (Min)?", 0, 120, 30, step=5)
            wochen_besonderheit = col_in1.text_input("Events diese Woche?", "Keine besonderen Events")
            manuelle_reste = col_in2.text_area("Reste / Wünsche:", "Alles offen")
            
            st.write("📸 Uploads (Optional)")
            c_up1, c_up2 = st.columns(2)
            kuehlschrank_img = c_up1.file_uploader("Kühlschrank", type=["jpg", "png", "jpeg"])
            prospekt_files = c_up2.file_uploader("Prospekte", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

        generate_btn = st.button("🚀 Plan generieren (Vorschau)")

        # Logik: Wenn Button gedrückt ODER wir schon ein Ergebnis im Session State haben (aber noch nicht gespeichert)
        if generate_btn:
            with st.spinner("KI plant die Woche..."):
                # PROMPT BAUEN
                diaet_str = ", ".join(current_data['diaet']) if isinstance(current_data['diaet'], list) else current_data['diaet']
                vermeiden_str = ", ".join(current_data.get('vermeiden_select', [])) + " " + current_data.get('vermeiden_text', "")

                prompt = f"""
                Du bist der Food Manager. Erstelle einen Wochenplan für {selected_week_label}.
                
                PROFIL:
                - {current_data['erwachsene']} Erw, {current_data['kinder_ueber3']} Kind(>3), {current_data['kinder_unter3']} Kind(<3).
                - Ernährung: {diaet_str} (No-Gos: {vermeiden_str})
                - Besonderheit: {current_data.get('besonderheiten', '')}
                - Geräte: {', '.join(current_data['geraete'])}
                - Vorrat: {current_data['vorrat']}
                
                SITUATION DIESE WOCHE:
                - Zeit: {zeit_input} Min
                - Events: {wochen_besonderheit}
                - Wünsche: {manuelle_reste}
                
                AUFGABE:
                Erstelle einen Plan mit 4-5 Gerichten.
                
                FORMATIERUNG (WICHTIG):
                Nutze Markdown.
                
                1. Zuerst eine **Übersicht** der Gerichte (Kurz: Name + Dauer + Key-Ingredients).
                2. Dann für JEDES Gericht einen Abschnitt, den man später aufklappen könnte (Nutze Überschriften wie '### Rezept 1: Name').
                   - Darunter: Zubereitung und Zutatenliste.
                3. Am Ende eine **Einkaufsliste** sortiert nach Supermarkt-Kategorien.
                
                Sprich den Nutzer direkt an.
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
                    st.session_state['temp_plan'] = response.text
                except Exception as e:
                    st.error(f"Fehler: {e}")

        # ANZEIGE DER VORSCHAU (Wenn generiert wurde)
        if 'temp_plan' in st.session_state:
            st.divider()
            st.subheader("Vorschau des Plans:")
            st.markdown(st.session_state['temp_plan'])
            
            st.success("Gefällt dir der Plan?")
            col_s1, col_s2 = st.columns(2)
            
            if col_s1.button("💾 Ja, Plan einloggen/speichern"):
                save_week_plan(selected_profile_name, week_key, st.session_state['temp_plan'])
                del st.session_state['temp_plan'] # Temp löschen
                st.rerun() # Seite neu laden -> Springt in "Eingeloggt"-Ansicht
            
            if col_s2.button("🔄 Nein, neu generieren"):
                del st.session_state['temp_plan']
                st.rerun()
