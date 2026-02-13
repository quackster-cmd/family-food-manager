import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os
import datetime
import time 

# --- KONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🥑", layout="wide")

# --- CSS / DESIGN ---
st.markdown("""
    <style>
    /* 1. HAUPTTITEL */
    .main-title {
        text-align: center;
        padding: 10px;
        margin-bottom: 20px;
        line-height: 1.2;
    }
    .main-title span.brand {
        font-size: 3rem;
        font-weight: 900;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        white-space: nowrap;
        display: inline-block;
    }
    .main-title span.subtitle {
        font-size: 1.5rem;
        font-weight: 700;
        color: inherit; 
        opacity: 0.7;
        display: block;
        margin-top: 5px;
    }
    
    /* 2. REZEPT TITEL */
    .recipe-header {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0px;
        color: inherit; 
    }

    /* 3. ABSCHNITTS-TITEL */
    .section-title {
        font-size: 2rem;
        font-weight: 800;
        margin-top: 30px;
        margin-bottom: 20px;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        border-bottom: 2px solid rgba(128, 128, 128, 0.2);
        padding-bottom: 10px;
    }

    /* 4. INTRO BOX */
    .intro-box {
        padding: 15px;
        background-color: rgba(78, 205, 196, 0.15);
        border-radius: 10px;
        margin-bottom: 25px;
        font-style: italic;
        color: inherit;
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
PLANS_FILE = "weekly_plans.json"

def load_json(filename):
    if not os.path.exists(filename): return {}
    try:
        with open(filename, "r") as f: return json.load(f)
    except json.JSONDecodeError: return {}

def save_json(filename, data):
    with open(filename, "w") as f: json.dump(data, f, indent=4)

def save_profile(name, data):
    profiles = load_json(PROFILE_FILE)
    profiles[name] = data
    save_json(PROFILE_FILE, profiles)

def delete_profile(name):
    profiles = load_json(PROFILE_FILE)
    if name in profiles:
        del profiles[name]
        save_json(PROFILE_FILE, profiles)

def save_week_plan(profile, week_key, plan_data):
    plans = load_json(PLANS_FILE)
    if profile not in plans: plans[profile] = {}
    plans[profile][week_key] = plan_data
    save_json(PLANS_FILE, plans)

def get_week_plan(profile, week_key):
    plans = load_json(PLANS_FILE)
    return plans.get(profile, {}).get(week_key, None)

def delete_week_plan(profile, week_key):
    plans = load_json(PLANS_FILE)
    if profile in plans and week_key in plans[profile]:
        del plans[profile][week_key]
        save_json(PLANS_FILE, plans)

# --- HELPER ---
def split_recipe_content(content):
    if not content: return "Rezept lädt...", ""
    lines = content.split('\n')
    title = lines[0].replace('#', '').strip() 
    body = "\n".join(lines[1:])
    return title, body

# --- STATE MANAGEMENT ---
if 'selected_profile_key' not in st.session_state:
    st.session_state.selected_profile_key = "Neues Profil erstellen"

if 'profile_to_select' in st.session_state:
    st.session_state.selected_profile_key = st.session_state.profile_to_select
    del st.session_state.profile_to_select

if 'recipe_slots' not in st.session_state:
    st.session_state.recipe_slots = []

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

    week_key = None
    selected_week_label = ""
    
    if selected_profile_name != "Neues Profil erstellen":
        st.divider()
        st.subheader("📅 Zeitplanung")
        
        today = datetime.date.today()
        year, week, _ = today.isocalendar()
        
        w1_label = f"Kalenderwoche {week} (Aktuell)"
        w2_label = f"Kalenderwoche {week + 1} (Nächste)"
        
        if 'selected_week_opt' not in st.session_state:
            st.session_state.selected_week_opt = w1_label
            
        selected_week_opt = st.radio("Woche wählen:", [w1_label, w2_label], key="week_radio")
        
        sel_week_num = week if "Aktuell" in selected_week_opt else week + 1
        sel_year = year
        if sel_week_num > 52: 
            sel_week_num = 1
            sel_year += 1
            
        week_key = f"{sel_year}-W{sel_week_num}"
        selected_week_label = selected_week_opt

# --- UI: HAUPTBEREICH ---
st.markdown("""
<div class="main-title">
    <span class="brand">Food & Family</span>
    <span class="subtitle">Manager</span>
</div>
""", unsafe_allow_html=True)

current_data = {}
is_new_profile = (selected_profile_name == "Neues Profil erstellen")

# === FALL 1: NEUES PROFIL ===
if is_new_profile:
    st.info("🆕 Bitte erstelle zuerst ein Profil.")
    profile_name_input = st.text_input("Profilname", "Meine Familie")

    with st.expander("⚙️ Profil erstellen", expanded=True):
        with st.form("preset_form"):
            c1, c2, c3 = st.columns(3)
            p_erw = c1.number_input("Erwachsene", 1, 10, 2)
            p_k3 = c2.number_input("Kinder (>3)", 0, 10, 0)
            p_ku3 = c3.number_input("Kinder (<3)", 0, 10, 0)

            st.write("### Besonderheiten & Vorrat")
            p_details = st.text_area("Infos / Allergien:", "")
            diaet_opts = sorted(["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier", "Low Carb", "Keto"])
            p_diaet = st.multiselect("Ernährung:", diaet_opts, default=["Ausgewogen (Alles)"])
            
            p_vorrat = st.text_area("Ständiger Vorrat:", "Nudeln, Reis, Salz, Pfeffer, Öl, Mehl, Zucker")

            # Dummy Felder für Kompatibilität
            p_verm_sel = []
            p_verm_txt = ""
            p_geraete = ["Backofen", "Herd"]
            p_ziele = ["Geld sparen"]
            p_shops = ["Aldi"]

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
                    st.session_state.recipe_slots = [] 
                    st.session_state.intro_text = ""
                    st.session_state.profile_to_select = profile_name_input
                    st.rerun()

# === FALL 2: PROFIL VORHANDEN ===
else:
    current_data = profiles[selected_profile_name]
    
    # DATEN LADEN (Robust)
    saved_plan = get_week_plan(selected_profile_name, week_key)
    
    # Initiales Laden nur wenn Session leer
    if saved_plan:
        if not st.session_state.recipe_slots:
            st.session_state.recipe_slots = saved_plan.get('recipes', [])
            st.session_state.intro_text = saved_plan.get('intro', "")
            if 'shopping_list' in saved_plan and saved_plan['shopping_list']:
                 st.session_state.generated_list_draft = saved_plan['shopping_list']
    
    # --- PROFIL SETTINGS ---
    with st.expander("⚙️ Profil / Einstellungen", expanded=False):
        with st.form("preset_form_edit"):
             c1, c2, c3 = st.columns(3)
             p_erw = c1.number_input("Erwachsene", 1, 10, current_data.get("erwachsene", 2))
             p_k3 = c2.number_input("Kinder (>3)", 0, 10, current_data.get("kinder_ueber3", 0))
             p_ku3 = c3.number_input("Kinder (<3)", 0, 10, current_data.get("kinder_unter3", 0))
             
             p_vorrat = st.text_area("Vorrat ändern:", current_data.get("vorrat", ""))
             
             if st.form_submit_button("Update speichern"):
                  current_data['erwachsene'] = p_erw
                  current_data['vorrat'] = p_vorrat
                  save_profile(selected_profile_name, current_data)
                  st.success("Gespeichert!")
                  st.rerun()

        st.markdown("---")
        st.write("**Gefahrenzone**")
        if st.button(f"🗑️ Profil löschen"):
            delete_profile(selected_profile_name)
            st.session_state.profile_to_select = "Neues Profil erstellen"
            st.rerun()

    st.divider()
    st.subheader(f"Planung für {selected_week_label}")
    
    # --- INPUT ---
    # Zeigen wenn noch gar keine Slots da sind ODER alle Slots leer sind
    slots_empty = len(st.session_state.recipe_slots) == 0
    
    with st.expander("📝 Planungsvorgaben & Uploads", expanded=slots_empty):
        col_in1, col_in2 = st.columns(2)
        days_to_plan = col_in1.slider("Anzahl Tage planen:", 1, 7, 4)
        zeit_input = col_in1.slider("Zeit pro Tag (Min)?", 0, 120, 30, step=5)
        manuelle_reste = col_in2.text_area("Wünsche:", "Alles offen", height=100)
        
        c_up1, c_up2 = st.columns(2)
        kuehlschrank_img = c_up1.file_uploader("Kühlschrank", type=["jpg", "png", "jpeg"])
        prospekt_files = c_up2.file_uploader("Werbeprospekte", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

        if not st.session_state.recipe_slots:
            if st.button("🚀 Erste Planung starten", type="primary"):
                st.session_state.recipe_slots = [{'day': i+1, 'content': None, 'locked': False} for i in range(days_to_plan)]
                st.rerun()

    # --- KI GENERIERUNG ---
    if st.session_state.recipe_slots:
        current_slots = st.session_state.recipe_slots
        
        # Slots auffüllen falls Slider erhöht wurde
        if len(current_slots) < days_to_plan:
             for i in range(len(current_slots), days_to_plan):
                 current_slots.append({'day': i+1, 'content': None, 'locked': False})
        
        # Leere Slots finden
        slots_to_fill = [i for i, slot in enumerate(current_slots) if slot['content'] is None]
        
        if slots_to_fill:
            # STATUS ANZEIGE STATT POPUP
            status = st.status("👨‍🍳 Der digitale Koch arbeitet...", expanded=True)
            status.write("Suche passende Rezepte...")
            
            locked_content = [slot['content'] for slot in current_slots if slot['locked'] and slot['content']]
            locked_text_block = "\n---\n".join(locked_content) if locked_content else "Keine."
            
            diaet_str = ", ".join(current_data.get('diaet', []))
            
            prompt = f"""
            Du bist der Food Manager.
            PROFIL: {current_data.get('erwachsene', 2)} Erw, {current_data.get('kinder_ueber3', 0)} Kind(>3), {current_data.get('kinder_unter3', 0)} Kind(<3).
            Ernährung: {diaet_str}. Vorrat: {current_data.get('vorrat', '')}.
            
            FIXIERTE REZEPTE (NICHT WIEDERHOLEN):
            {locked_text_block}
            
            AUFGABE:
            Generiere EXAKT {len(slots_to_fill)} NEUE Rezepte für die leeren Tage.
            
            FORMAT (STRIKT!):
            1. Schreibe GANZ AM ANFANG eine kurze Begrüßung (max 2 Sätze) als Intro.
            2. Schreibe DANACH exakt: "---INTRO_ENDE---"
            3. DANN kommen die Rezepte, getrennt mit: "---TRENNER---"
            4. REZEPT-TITEL-ZEILE: Muss IMMER mit einem passenden EMOJI beginnen.
            5. REZEPT-TITEL-MARKER: Die erste Zeile jedes Rezepts muss der Titel sein.
            
            SITUATION: Zeit: {zeit_input} Min. Wünsche: {manuelle_reste}.
            """
            
            content = [prompt]
            if kuehlschrank_img: content.extend([Image.open(kuehlschrank_img), "Kühlschrank"])
            if prospekt_files: 
                for p in prospekt_files: content.extend([Image.open(p), "Prospekt"])

            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(content)
                raw_text = response.text
                
                # Parsing
                if "---INTRO_ENDE---" in raw_text:
                    intro_part, recipes_part = raw_text.split("---INTRO_ENDE---")
                    st.session_state.intro_text = intro_part.strip()
                else:
                    recipes_part = raw_text
                
                parts = recipes_part.split("---TRENNER---")
                valid_parts = [p.strip() for p in parts if p.strip()]
                
                fill_idx = 0
                for part in valid_parts:
                    if len(part) < 20: continue
                    if fill_idx < len(slots_to_fill):
                        target_slot_idx = slots_to_fill[fill_idx]
                        st.session_state.recipe_slots[target_slot_idx]['content'] = part
                        fill_idx += 1
                
                status.update(label="Fertig! Speichere...", state="complete", expanded=False)
                
                # SPEICHERN
                save_week_plan(selected_profile_name, week_key, {
                    "recipes": st.session_state.recipe_slots,
                    "intro": st.session_state.intro_text,
                    "shopping_list": st.session_state.get('generated_list_draft')
                })
                
                time.sleep(0.5) # Kurz warten damit Speichern durch ist
                st.rerun()
                
            except Exception as e:
                status.update(label="Fehler aufgetreten!", state="error")
                st.error(f"Fehler bei der KI: {e}")

    # --- ANZEIGE ---
    if st.session_state.recipe_slots:
        
        if st.session_state.intro_text:
            st.markdown(f'<div class="intro-box">{st.session_state.intro_text}</div>', unsafe_allow_html=True)
            
        st.markdown(f'<div class="section-title">🍳 Dein Menü ({len(st.session_state.recipe_slots)} Gerichte)</div>', unsafe_allow_html=True)
        
        # Nur so viele Slots anzeigen wie im Slider gewählt (falls Datenmüll drin ist)
        display_slots = st.session_state.recipe_slots[:days_to_plan]
        
        for i, slot in enumerate(display_slots):
            # Zeige auch Slots an die noch laden (None), damit Struktur bleibt
            content = slot.get('content')
            title_only, body_text = split_recipe_content(content) if content else ("Planung läuft...", "Bitte warten...")
            
            with st.container(border=True):
                # Layout für Toggle Label fixen
                c1, c2 = st.columns([0.7, 0.3])
                is_locked = slot['locked']
                
                with c1:
                    st.markdown(f"<div class='recipe-header'>{title_only}</div>", unsafe_allow_html=True)
                    if is_locked: 
                        st.caption("🔒 Fixiert")

                with c2:
                    # HIER IST DER FIX: Label anzeigen!
                    if st.toggle("Fixieren", value=is_locked, key=f"fix_{i}_{week_key}"): # Key unique machen
                        if not is_locked: # War vorher False, jetzt True -> Speichern
                            st.session_state.recipe_slots[i]['locked'] = True
                            save_week_plan(selected_profile_name, week_key, {
                                "recipes": st.session_state.recipe_slots,
                                "intro": st.session_state.intro_text,
                                "shopping_list": st.session_state.get('generated_list_draft')
                            })
                            st.rerun()
                    else:
                        if is_locked: # War vorher True, jetzt False -> Speichern
                            st.session_state.recipe_slots[i]['locked'] = False
                            save_week_plan(selected_profile_name, week_key, {
                                "recipes": st.session_state.recipe_slots,
                                "intro": st.session_state.intro_text,
                                "shopping_list": st.session_state.get('generated_list_draft')
                            })
                            st.rerun()

                if content:
                    with st.expander("📖 Zubereitung & Zutaten"):
                        st.markdown(body_text)
        
        st.divider()
        c1, c2 = st.columns(2)
        
        if c1.button("🎲 Offene Gerichte neu würfeln", use_container_width=True):
            for slot in st.session_state.recipe_slots:
                if not slot['locked']:
                    slot['content'] = None
            st.rerun()

        if c2.button("🛒 Einkaufsliste erstellen", type="primary", use_container_width=True):
            # Status Monitor
            status_list = st.status("🛒 Einkaufsliste wird erstellt...", expanded=True)
            status_list.write("Sammle Zutaten...")
            
            # Alle locken
            for slot in st.session_state.recipe_slots:
                slot['locked'] = True
            
            all_text = "\n".join([s['content'] for s in st.session_state.recipe_slots if s['content']])
            
            if not all_text:
                status_list.update(label="Fehler: Keine Rezepte gefunden!", state="error")
                st.error("Keine Rezepte zum Umwandeln da.")
            else:
                status_list.write("Rufe KI an...")
                p_list = f"""Erstelle Einkaufsliste für:\n{all_text}\nSortiert nach Supermarkt-Bereich. Emojis. Vorrat ignorieren: {current_data.get('vorrat', '')}"""
                try:
                    # Wir nutzen hier 2.0 Flash weil es oft stabiler ist für reine Listen
                    m = genai.GenerativeModel('gemini-2.0-flash') 
                    res = m.generate_content(p_list)
                    final_list = res.text
                    
                    st.session_state.generated_list_draft = final_list
                    status_list.write("Speichere...")
                    
                    save_week_plan(selected_profile_name, week_key, {
                        "recipes": st.session_state.recipe_slots,
                        "intro": st.session_state.intro_text,
                        "shopping_list": final_list
                    })
                    
                    status_list.update(label="Fertig!", state="complete", expanded=False)
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    status_list.update(label="Fehler!", state="error")
                    st.error(f"Fehler: {e}")

        # EINKAUFSLISTE ANZEIGEN
        if 'generated_list_draft' in st.session_state and st.session_state.generated_list_draft:
            st.divider()
            st.markdown('<div class="section-title">🛒 Deine Einkaufsliste</div>', unsafe_allow_html=True)
            st.markdown(st.session_state.generated_list_draft)
            
            st.write("")
            if st.button("🗑️ Woche komplett löschen"):
                delete_week_plan(selected_profile_name, week_key)
                st.session_state.recipe_slots = []
                st.session_state.intro_text = ""
                st.session_state.generated_list_draft = None
                st.rerun()
