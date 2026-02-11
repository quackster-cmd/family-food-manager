import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="Family Food Manager", page_icon="🥦")

st.title("🥦 Family Food Manager")
st.write("Plane das Essen für: Papa (Kraftsport), Mama, Kind (3J) und Baby (8M).")

# --- API KEY LADEN ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.warning("⚠️ API Key fehlt in den Secrets.")
    st.stop()

# --- EINGABE ---
col1, col2 = st.columns(2)
with col1:
    zeit_minuten = st.slider("Zeitlimit (Minuten)", 10, 90, 30)
with col2:
    besonderheit = st.text_input("Besonderheit heute?", "Muss schnell gehen")

# NEU: Textfeld für Zutaten
zutaten_text = st.text_area("✍️ Zutaten manuell eingeben (optional)", placeholder="z.B. Nudeln, Tomaten, Hackfleisch...")

# Upload-Button
uploaded_file = st.file_uploader("📸 Oder Foto hochladen (optional)", type=["jpg", "jpeg", "png"])

# Bild anzeigen, falls vorhanden
image = None
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Dein Bild', use_container_width=True)

# --- KI LOGIK ---
if st.button("🍳 Rezept zaubern"):
    # Check: Haben wir überhaupt Input?
    if not zutaten_text and not uploaded_file:
        st.error("Bitte gib Zutaten ein oder lade ein Foto hoch!")
    else:
        with st.spinner('Der KI-Koch überlegt...'):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # Der Prompt wird dynamisch angepasst
                prompt = f"""
                Du bist der Familien-Koch-Agent.
                
                SITUATION:
                - Manuelle Zutaten: {zutaten_text}
                - Bild vorhanden: {"JA" if uploaded_file else "NEIN"}
                
                AUFGABE:
                Erstelle EIN Rezept basierend auf den Zutaten (Text und/oder Bild) für:
                - Vater (Kraftsportler, 95kg, braucht Protein)
                - Kind (3J, wählerisch)
                - Baby (8M, Beikost)
                
                Rahmenbedingungen:
                - Zeit: {zeit_minuten} Minuten
                - Besonderheit: {besonderheit}
                
                STRUKTUR:
                1. 📝 Zusammenfassung der Zutaten (die du nutzen wirst)
                2. 🍳 Das Rezept (Name & Anleitung)
                3. 👨‍👩‍👧‍👦 WICHTIG: Anpassungen für Papa, Kind (3J) und Baby (8M).
                """
                
                # Wir entscheiden: Bild mitschicken oder nur Text?
                if image:
                    response = model.generate_content([prompt, image])
                else:
                    response = model.generate_content(prompt)
                    
                st.markdown(response.text)
                st.success("Guten Appetit! 🍽️")
                
            except Exception as e:
                st.error(f"Fehler: {e}")
