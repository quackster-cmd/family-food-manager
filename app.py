import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="Family Food Manager", page_icon="🥦")

st.title("🥦 Family Food Manager")
st.write("Lade ein Foto deines Kühlschranks hoch. Ich plane das Essen für: Papa (Kraftsport), Mama, Kind (3J) und Baby (8M).")

# --- API KEY LADEN (Sicher aus den Secrets) ---
try:
    # Wir holen den Key aus den sicheren Einstellungen von Streamlit
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.warning("⚠️ Warte auf API Key... (Bitte in Streamlit Secrets eintragen)")
    st.stop()

# --- EINGABE ---
col1, col2 = st.columns(2)
with col1:
    zeit_minuten = st.slider("Zeitlimit (Minuten)", 10, 90, 30)
with col2:
    besonderheit = st.text_input("Besonderheit heute?", "Muss schnell gehen")

uploaded_file = st.file_uploader("📸 Foto hochladen (Kühlschrank/Zutaten)", type=["jpg", "jpeg", "png"])

# --- KI LOGIK ---
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Dein Bild', use_container_width=True)

    if st.button("🍳 Rezept zaubern"):
        with st.spinner('Der KI-Koch analysiert das Bild...'):
            try:
                # Wir nutzen das schnelle Flash-Modell
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                prompt = f"""
                Du bist der Familien-Koch-Agent.
                
                AUFGABE:
                Analysiere das Bild (Zutaten). Erstelle EIN Rezept für:
                - Vater (Kraftsportler, 95kg, braucht Protein)
                - Kind (3J, wählerisch)
                - Baby (8M, Beikost)
                
                Rahmenbedingungen:
                - Zeit: {zeit_minuten} Minuten
                - Besonderheit: {besonderheit}
                
                STRUKTUR:
                1. 📝 Erkannte Zutaten
                2. 🍳 Das Rezept (Name & Anleitung)
                3. 👨‍👩‍👧‍👦 WICHTIG: Anpassungen für Papa, Kind (3J) und Baby (8M).
                """
                
                response = model.generate_content([prompt, image])
                st.markdown(response.text)
                st.success("Guten Appetit! 🍽️")
                
            except Exception as e:
                st.error(f"Fehler: {e}")
