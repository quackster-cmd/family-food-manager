import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="Food Manager Pro", page_icon="🥗", layout="wide")

# --- API KEY SETUP (SICHER & ROBUST) ---
try:
    # 1. Versuche, den Key aus den Secrets zu laden
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        # 2. Falls der Key fehlt, zeige Fehler ANSTATT abzustürzen
        st.error("🚨 FEHLER: Der API Key fehlt in den Streamlit Secrets!")
        st.info("Bitte gehe zu: Manage App -> Settings -> Secrets und trage 'GOOGLE_API_KEY' ein.")
        st.stop() # Stoppt die App hier sauber
except Exception as e:
    st.error(f"🚨 Ein unerwarteter Fehler ist aufgetreten: {e}")
    st.stop()

# --- DATEN-MANAGEMENT (PRESETS) ---
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

# --- UI: SEITENLEISTE (PROFIL-WAHL) ---
with st.sidebar:
    st.header("👤 Profil-Verwaltung")
    profiles = load_profiles()
    profile_names = list(profiles.keys())
    
    selected_profile_name = st.selectbox(
        "Aktives Profil wählen", 
        ["Neues Profil erstellen"] + profile_names
    )

# --- UI: HAUPTBEREICH ---
st.title("🥗 Food Manager AI")

# Container für Profil-Daten (wird gefüllt)
current_data = {}

# --- FALL 1: NEUES PROFIL ODER BEARBEITEN ---
if selected_profile_name == "Neues Profil erstellen":
    st.info("Bitte konfiguriere dein Basis-Profil. Dies musst du nur einmal tun!")
    profile_name_input = st.text_input("Profil-Name (z.B. 'Familie Müller')", "Mein Profil")
else:
    st.success(f"Profil geladen: **{selected_profile_name}**")
    profile_name_input = selected_profile_name
    current_data = profiles[selected_profile_name]

# --- DAS GROSSE FORMULAR (PRESETS) ---
with st.form("preset_form"):
    st.subheader("1. Wer isst mit?")
    col1, col2, col3 = st.columns(3)
    p_erwachsene = col1.number_input("Erwachsene", 1, 10, current_data.get("erwachsene", 2))
    p_kinder_ueber3 = col2.number_input("Kinder (>3 Jahre)", 0, 10, current_data.get("kinder_ueber3", 0))
    p_kinder_unter3 = col3.number_input("Kinder (<3 Jahre)", 0, 10, current_data.get("kinder_unter3", 0))

    st.subheader("2. Ernährung & Ausschluss")
    diaet_optionen = ["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier"]
    p_diaet = st.selectbox("Ernährungsweise", diaet_optionen, index=diaet_optionen.index(current_data.get("diaet", "Ausgewogen (Alles)")))
    
    vermeiden_default = current_data.get("vermeiden", [])
    p_vermeiden = st.multiselect(
        "Was soll vermieden werden? (Zutaten)",
        ["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Koriander", "Meeresfrüchte", "Paprika"],
        default=vermeiden_default
    )

    st.subheader("3. Küche & Geräte")
    geraete_liste = ["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker"]
    p_geraete = st.multiselect("Welche Geräte hast du?", geraete_liste, default=current_data.get("geraete", ["Herd", "Backofen"]))

    st.subheader("4. Ziele & Einkaufen")
    ziele_liste = ["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren"]
    p_ziele = st.multiselect("Was ist das Ziel für diese Woche?", ziele_liste, default=current_data.get("ziele", ["Geld sparen"]))
    
    supermarkt_liste = ["Aldi", "Lidl", "Rewe", "Edeka", "Marktkauf", "Hit", "Netto", "Penny", "Kaufland"]
    p_shops = st.multiselect("Wo kaufst du ein?", supermarkt_liste, default=current_data.get("shops", ["Aldi", "Rewe"]))

    st.subheader("5. Der Eiserne Vorrat")
    st.caption("Dinge, die du IMMER da hast (KI wird diese nicht auf die Einkaufsliste setzen, außer du sagst es explizit).")
    vorrat_default = "Nudeln, Reis, Salz, Pfeffer, Öl, Mehl, Zucker, Gewürze"
    p_vorrat = st.text_area("Vorrat (durch Komma getrennt)", current_data.get("vorrat", vorrat_default))

    # Speichern Button
    submitted = st.form_submit_button("Profil Speichern & Laden")
    
    if submitted:
        new_profile_data = {
            "erwachsene": p_erwachsene,
            "kinder_ueber3": p_kinder_ueber3,
            "kinder_unter3": p_kinder_unter3,
            "diaet": p_diaet,
            "vermeiden": p_vermeiden,
            "geraete": p_geraete,
            "ziele": p_ziele,
            "shops": p_shops,
            "vorrat": p_vorrat
        }
        save_profile(profile_name_input, new_profile_data)
        st.success(f"Profil '{profile_name_input}' gespeichert! Bitte Seite neu laden oder Profil links auswählen.")

# --- DER WOCHENPLANER (NUR SICHTBAR WENN PROFIL GELADEN) ---
if selected_profile_name != "Neues Profil erstellen":
    st.divider()
    st.header(f"📅 Wochenplanung für {selected_profile_name}")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        zeit_input = st.slider("Wie viel Zeit hast du pro Tag (Min)?", 15, 120, 30)
        besonderheit_input = st.text_input("Besonderheit diese Woche?", "Besuch am Wochenende, Samstag Grillen")
    with col_input2:
        manuelle_zutaten = st.text_area("Zutaten, die weg müssen (oder spezielle Wünsche)", "Paprika die weg muss, Lust auf Lasagne")

    st.subheader("📸 Uploads (Optional)")
    upload_cols = st.columns(2)
    kuehlschrank_img = upload_cols[0].file_uploader("1. Kühlschrank Foto", type=["jpg", "png"])
    prospekt_files = upload_cols[1].file_uploader("2. Werbeblättchen (Bilder/PDF)", type=["jpg", "png", "pdf"], accept_multiple_files=True)

    generate_btn = st.button("🚀 Plan erstellen (Magic Start)")

    if generate_btn:
        with st.spinner("KI analysiert Profil, Vorrat, Prospekte und Wünsche..."):
            
            # 1. Prompt bauen (Hier fließt alles zusammen)
            prompt = f"""
            Du bist der ultimative Food Manager.
            
            BASIS-PROFIL (Nicht veränderbar):
            - Personen: {current_data['erwachsene']} Erw, {current_data['kinder_ueber3']} Kinder (>3), {current_data['kinder_unter3']} Kinder (<3).
            - Ernährung: {current_data['diaet']}
            - VERMEIDEN: {', '.join(current_data['vermeiden'])}
            - Geräte vorhanden: {', '.join(current_data['geraete'])}
            - Supermärkte: {', '.join(current_data['shops'])}
            - VORRAT (NICHT KAUFEN): {current_data['vorrat']}
            
            AKTUELLE ZIELE: {', '.join(current_data['ziele'])}
            
            SITUATION DIESE WOCHE:
            - Zeit pro Tag: {zeit_input} Min
            - Besonderheit: {besonderheit_input}
            - Wünsche/Reste: {manuelle_zutaten}
            
            AUFGABE:
            1. Analysiere (falls vorhanden) das Kühlschrankbild und die Werbeblättchen.
            2. Erstelle einen Essensplan für 3-4 Tage.
            3. Berücksichtige DRINGEND die Ziele (z.B. wenn "Sparen": Nutze Angebote aus den Prospekten).
            4. Wenn Kinder <3 dabei sind: Gib Hinweise, wie man das Essen für sie anpasst.
            
            OUTPUT:
            Erstelle eine Tabelle mit Gerichten + eine Einkaufsliste sortiert nach Supermarkt-Abteilungen.
            """
            
            # Bildverarbeitung
            content_parts = [prompt]
            if kuehlschrank_img:
                img = Image.open(kuehlschrank_img)
                content_parts.append(img)
                content_parts.append("Das ist das Foto vom Kühlschrank.")
            
            if prospekt_files:
                for p_file in prospekt_files:
                    # Hinweis: PDF Handling ist komplexer, hier nehmen wir an es sind Bilder
                    # Für echte PDFs bräuchte man eine Konvertierung.
                    try:
                        p_img = Image.open(p_file)
                        content_parts.append(p_img)
                        content_parts.append("Das ist ein Werbeblättchen mit Angeboten.")
                    except:
                        content_parts.append(f"Datei {p_file.name} konnte nicht als Bild gelesen werden (PDF Support in Arbeit).")

            try:
                model = genai.GenerativeModel('gemini-1.5-flash') # Flash für Geschwindigkeit, Pro für Analyse
                response = model.generate_content(content_parts)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Fehler bei der KI-Anfrage: {e}")
