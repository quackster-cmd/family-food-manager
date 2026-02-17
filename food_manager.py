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
        color: inherit; opacity: 0.7;
        display: block; margin-top: 5px;
    }
    
    /* 2. REZEPT TITEL */
    .recipe-header {
        font-size: 1.5rem; font-weight: 700; margin-bottom: 0px; color: inherit; 
    }

    /* 3. ABSCHNITTS-TITEL (Türkis/Pink) */
    .section-title {
        font-size: 2rem; font-weight: 800; margin-top: 30px; margin-bottom: 20px;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        border-bottom: 2px solid rgba(128, 128, 128, 0.2);
        padding-bottom: 10px;
    }
    
    /* 4. KW TITEL (Türkis) */
    .kw-title {
        font-size: 1.8rem; font-weight: 800; margin-bottom: 15px;
        color: #4ECDC4; 
    }

    /* 5. BOXEN */
    .intro-box {
        padding: 15px; background-color: rgba(78, 205, 196, 0.15);
        border-radius: 10px; margin-bottom: 25px; font-style: italic;
        color: inherit; border-left: 5px solid #4ECDC4;
    }
    </style>
    """, unsafe_allow_html=True)

# --- API KEY ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 API Key fehlt!")
        st.stop()
except Exception as e:
    st.error(f"🚨 Fehler: {e}")
    st.stop()

# --- DATEN-MANAGEMENT ---
PROFILE_FILE = "user_profiles.json"
PLANS_FILE = "weekly_plans.json"
RECIPE_DB_FILE = "recipe_database.json"

def load_json(filename):
    if not os.path.exists(filename): return {}
    try:
        with open(filename, "r") as f: return json.load(f)
    except: return {}

def save_json(filename, data):
    with open(filename, "w") as f: json.dump(data, f, indent=4)

# Profil Manager
def save_profile(name, data):
    profiles = load_json(PROFILE_FILE)
    profiles[name] = data
    save_json(PROFILE_FILE, profiles)
def delete_profile(name):
    profiles = load_json(PROFILE_FILE)
    if name in profiles: del profiles[name]; save_json(PROFILE_FILE, profiles)

# Wochenplan Manager
def save_week_plan(profile, week_key, plan_data):
    plans = load_json(PLANS_FILE)
    if profile not in plans: plans[profile] = {}
    plans[profile][week_key] = plan_data
    save_json(PLANS_FILE, plans)
def get_week_plan(profile, week_key):
    return load_json(PLANS_FILE).get(profile, {}).get(week_key, None)
def delete_week_plan(profile, week_key):
    plans = load_json(PLANS_FILE)
    if profile in plans and week_key in plans[profile]:
        del plans[profile][week_key]
        save_json(PLANS_FILE, plans)

# Rezept Datenbank Manager
def save_recipe_to_db(title, content, rating=0, source="AI"):
    db = load_json(RECIPE_DB_FILE)
    clean_title = title.split("\n")[0].replace("#", "").strip()
    if len(clean_title) > 50: clean_title = clean_title[:50] + "..."
    
    db[clean_title] = {
        "content": content,
        "rating": rating,
        "source": source,
        "added_date": str(datetime.date.today())
    }
    save_json(RECIPE_DB_FILE, db)

# --- HELPER ---
def split_recipe_content(content):
    if not content: return "Lade...", ""
    lines = content.split('\n')
    title = lines[0].replace('#', '').strip() 
    body = "\n".join(lines[1:])
    return title, body

# --- STATE MANAGEMENT ---
if 'selected_profile_key' not in st.session_state: st.session_state.selected_profile_key = "Neues Profil erstellen"
if 'profile_to_select' in st.session_state:
    st.session_state.selected_profile_key = st.session_state.profile_to_select
    del st.session_state.profile_to_select

# Session Init
if 'recipe_slots' not in st.session_state: st.session_state.recipe_slots = []
if 'intro_text' not in st.session_state: st.session_state.intro_text = ""
if 'last_week_key' not in st.session_state: st.session_state.last_week_key = ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Einstellungen")
    profiles = load_json(PROFILE_FILE)
    optionen = ["Neues Profil erstellen"] + sorted(list(profiles.keys()))
    
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
        if sel_week_num > 52: sel_week_num = 1; sel_year += 1
            
        week_key = f"{sel_year}-W{sel_week_num}"
        selected_week_label = selected_week_opt

        # Wochenwechsel Reset
        if st.session_state.last_week_key != week_key:
            st.session_state.recipe_slots = []
            st.session_state.intro_text = ""
            st.session_state.generated_list_draft = None
            st.session_state.last_week_key = week_key
            st.rerun()

        # REZEPT UPLOAD
        st.divider()
        with st.expander("📚 Rezept hinzufügen"):
            st.write("Lade ein Foto oder Text hoch.")
            up_mode = st.radio("Eingabe:", ["Text/Link", "Foto"], horizontal=True)
            
            new_rec_content = None
            if up_mode == "Foto":
                up_img = st.file_uploader("Foto hochladen", type=["jpg","png"])
                if up_img: new_rec_content = [Image.open(up_img), "Analysiere dieses Rezept. Extrahiere Titel, Zutaten und Anleitung."]
            else:
                new_rec_text = st.text_area("Rezept-Text oder Link einfügen")
                if new_rec_text: new_rec_content = [f"Formatiere dies sauber als Rezept: {new_rec_text}"]
            
            up_rating_opts = ["0 Sterne (Nicht wiederholen)", "1 Stern (Selten)", "2 Sterne (Lecker)", "3 Sterne (Lieblingsessen)"]
            up_rating_str = st.selectbox("Bewertung:", up_rating_opts, index=2)
            up_rating_val = up_rating_opts.index(up_rating_str)

            if new_rec_content and st.button("💾 In Datenbank speichern"):
                with st.spinner("Analysiere & Speichere..."):
                    try:
                        # Upload sicherheitshalber auch mit flash-latest
                        m = genai.GenerativeModel('gemini-flash-latest')
                        p = ["Formatiere das Rezept strikt: Zeile 1: Emoji + Titel. Dann Zutaten, Dann Anleitung.", new_rec_content[0]] if isinstance(new_rec_content, list) else [new_rec_content[0]]
                        res = m.generate_content(p)
                        title, body = split_recipe_content(res.text)
                        
                        save_recipe_to_db(title, res.text, rating=up_rating_val, source="Upload")
                        st.success(f"'{title}' gespeichert!")
                    except Exception as e:
                        st.error(f"Fehler: {e}")

# --- MAIN PAGE ---
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
            st.write("### 1. Wer isst mit?")
            c1, c2, c3 = st.columns(3)
            p_erw = c1.number_input("Erw.", 1, 10, 2)
            p_k3 = c2.number_input("Kind (>3)", 0, 10, 0)
            p_ku3 = c3.number_input("Kind (<3)", 0, 10, 0)

            st.write("### 2. Ernährung & Besonderheiten")
            p_details = st.text_area("Dauerhafte Infos / Allergien:", "")
            diaet_opts = sorted(["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier", "Low Carb", "Keto"])
            p_diaet = st.multiselect("Ernährung:", diaet_opts, default=["Ausgewogen (Alles)"])

            col_av1, col_av2 = st.columns(2)
            verm_opts = sorted(["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Paprika", "Zwiebeln", "Knoblauch", "Koriander"])
            p_verm_sel = col_av1.multiselect("Vermeiden (Auswahl):", verm_opts)
            p_verm_txt = col_av2.text_input("Vermeiden (Freitext):")

            st.write("### 3. Haushalt, Ziele & Shops")
            geraete_opts = sorted(["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker", "Grill", "Dampfgarer"])
            p_geraete = st.multiselect("Geräte:", geraete_opts, default=["Backofen", "Herd"])
            
            ziele_opts = sorted(["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren", "Schnelle Küche (<20 Min)", "Bio / Nachhaltig", "Meal Prep geeignet"])
            p_ziele = st.multiselect("Ziele:", ziele_opts, default=["Geld sparen"])
            
            shop_opts = sorted(["Aldi", "Lidl", "Rewe", "Edeka", "Netto", "Penny", "Kaufland", "DM", "Rossmann", "Marktkauf", "Hit", "Globus"])
            p_shops = st.multiselect("Supermärkte:", shop_opts, default=["Aldi", "Rewe"])
            
            p_vorrat = st.text_area("Ständiger Vorrat:", "Nudeln, Reis, Salz, Pfeffer, Öl, Mehl, Zucker")

            if st.form_submit_button("💾 Profil Speichern"):
                if not profile_name_input: st.error("Name fehlt")
                else:
                    d = {
                        "erwachsene": p_erw, "kinder_ueber3": p_k3, "kinder_unter3": p_ku3,
                        "besonderheiten": p_details, "diaet": p_diaet,
                        "vermeiden_select": p_verm_sel, "vermeiden_text": p_verm_txt,
                        "geraete": p_geraete, "ziele": p_ziele, "shops": p_shops, "vorrat": p_vorrat
                    }
                    save_profile(profile_name_input, d)
                    st.session_state.profile_to_select = profile_name_input
                    st.rerun()

# === FALL 2: PROFIL VORHANDEN ===
else:
    current_data = profiles[selected_profile_name]
    saved_plan = get_week_plan(selected_profile_name, week_key)
    
    # Laden wenn Daten da sind und Session leer
    if saved_plan and not st.session_state.recipe_slots:
        st.session_state.recipe_slots = saved_plan.get('recipes', [])
        st.session_state.intro_text = saved_plan.get('intro', "")
        if 'shopping_list' in saved_plan: st.session_state.generated_list_draft = saved_plan['shopping_list']
        # Slider synchronisieren
        st.session_state.days_slider_val = len(st.session_state.recipe_slots)

    # --- PROFIL EDITIEREN ---
    with st.expander("⚙️ Profil / Einstellungen bearbeiten", expanded=False):
        with st.form("edit_form_full"):
            st.write("### 1. Wer isst mit?")
            c1, c2, c3 = st.columns(3)
            p_erw = c1.number_input("Erw.", 1, 10, current_data.get("erwachsene", 2))
            p_k3 = c2.number_input("Kind (>3)", 0, 10, current_data.get("kinder_ueber3", 0))
            p_ku3 = c3.number_input("Kind (<3)", 0, 10, current_data.get("kinder_unter3", 0))

            st.write("### 2. Ernährung")
            p_details = st.text_area("Infos:", current_data.get("besonderheiten", ""))
            diaet_opts = sorted(["Ausgewogen (Alles)", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier", "Low Carb", "Keto"])
            saved_diaet = current_data.get("diaet", ["Ausgewogen (Alles)"])
            if isinstance(saved_diaet, str): saved_diaet = [saved_diaet]
            p_diaet = st.multiselect("Ernährung:", diaet_opts, default=saved_diaet)

            col_av1, col_av2 = st.columns(2)
            verm_opts = sorted(["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Paprika", "Zwiebeln", "Knoblauch", "Koriander"])
            p_verm_sel = col_av1.multiselect("Vermeiden:", verm_opts, default=current_data.get("vermeiden_select", []))
            p_verm_txt = col_av2.text_input("Vermeiden (Freitext):", value=current_data.get("vermeiden_text", ""))

            st.write("### 3. Haushalt")
            geraete_opts = sorted(["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker", "Grill", "Dampfgarer"])
            p_geraete = st.multiselect("Geräte:", geraete_opts, default=current_data.get("geraete", ["Backofen", "Herd"]))
            
            ziele_opts = sorted(["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren", "Schnelle Küche (<20 Min)", "Bio / Nachhaltig", "Meal Prep geeignet"])
            p_ziele = st.multiselect("Ziele:", ziele_opts, default=current_data.get("ziele", ["Geld sparen"]))
            
            shop_opts = sorted(["Aldi", "Lidl", "Rewe", "Edeka", "Netto", "Penny", "Kaufland", "DM", "Rossmann", "Marktkauf", "Hit", "Globus"])
            p_shops = st.multiselect("Supermärkte:", shop_opts, default=current_data.get("shops", ["Aldi", "Rewe"]))
            
            p_vorrat = st.text_area("Vorrat:", current_data.get("vorrat", ""))

            if st.form_submit_button("Update speichern"):
                d = {
                    "erwachsene": p_erw, "kinder_ueber3": p_k3, "kinder_unter3": p_ku3,
                    "besonderheiten": p_details, "diaet": p_diaet,
                    "vermeiden_select": p_verm_sel, "vermeiden_text": p_verm_txt,
                    "geraete": p_geraete, "ziele": p_ziele, "shops": p_shops, "vorrat": p_vorrat
                }
                save_profile(selected_profile_name, d)
                st.success("Gespeichert!")
                st.rerun()
        
        st.markdown("---")
        if st.button("🗑️ Profil löschen"):
            delete_profile(selected_profile_name); st.session_state.profile_to_select = "Neues Profil erstellen"; st.rerun()

    st.divider()
    st.markdown(f'<div class="kw-title">Planung für {selected_week_label}</div>', unsafe_allow_html=True)
    
    # --- INPUT ---
    slots_empty = len(st.session_state.recipe_slots) == 0
    with st.expander("📝 Planungsvorgaben & Uploads", expanded=slots_empty):
        col_in1, col_in2 = st.columns(2)
        
        default_days = st.session_state.get('days_slider_val', 4)
        days_to_plan = col_in1.slider("Tage:", 1, 7, default_days, key="day_slider")
        if days_to_plan != default_days: st.session_state.days_slider_val = days_to_plan

        zeit_input = col_in1.slider("Zeit (Min):", 0, 120, 30, step=5)
        manuelle_reste = col_in2.text_area("Wünsche:", "Alles offen", height=100)
        c_up1, c_up2 = st.columns(2)
        kuehlschrank_img = c_up1.file_uploader("Kühlschrank", type=["jpg","png"])
        prospekt_files = c_up2.file_uploader("Prospekte", type=["jpg","png"], accept_multiple_files=True)

        if not st.session_state.recipe_slots:
            if st.button("🚀 Erste Planung starten", type="primary"):
                # Initial Rating = 0 (Bitte bewerten)
                st.session_state.recipe_slots = [{'day': i+1, 'content': None, 'locked': False, 'rating': 0} for i in range(days_to_plan)]
                st.rerun()

    # --- KI GENERIERUNG ---
    if st.session_state.recipe_slots:
        current_slots = st.session_state.recipe_slots
        if len(current_slots) < days_to_plan:
             for i in range(len(current_slots), days_to_plan):
                 current_slots.append({'day': i+1, 'content': None, 'locked': False, 'rating': 0})
        
        slots_to_fill = [i for i, slot in enumerate(current_slots) if slot['content'] is None]
        
        if slots_to_fill:
            with st.spinner(f"Der digitale Koch brutzelt {len(slots_to_fill)} neue Ideen... 🥘"):
                locked_c = [s['content'] for s in current_slots if s['locked'] and s['content']]
                locked_blk = "\n---\n".join(locked_c) if locked_c else "Keine."
                
                diaet_str = ", ".join(current_data.get('diaet', []))
                vermeiden_str = ", ".join(current_data.get('vermeiden_select', [])) + " " + current_data.get('vermeiden_text', "")
                geraete_str = ", ".join(current_data.get('geraete', []))
                ziele_str = ", ".join(current_data.get('ziele', []))
                shops_str = ", ".join(current_data.get('shops', []))

                prompt = f"""
                Du bist der Food Manager.
                PROFIL: {current_data.get('erwachsene')} Erw, {current_data.get('kinder_ueber3')} Kind>3.
                Ernährung: {diaet_str} (No-Gos: {vermeiden_str}).
                Geräte vorhanden: {geraete_str}.
                Ziele: {ziele_str}.
                Bevorzugte Supermärkte: {shops_str}.
                VORRAT: {current_data.get('vorrat', '')}.
                
                USER WÜNSCHE: "{manuelle_reste}" (Gehe darauf ein!).
                
                FIXIERT (Nicht wiederholen): {locked_blk}
                
                AUFGABE: Generiere {len(slots_to_fill)} NEUE Rezepte.
                FORMAT:
                1. Intro (kurz, persönlich).
                2. "---INTRO_ENDE---"
                3. Rezepte getrennt mit "---TRENNER---".
                4. TITEL: Muss mit Emoji starten.
                """
                content = [prompt]
                if kuehlschrank_img: content.extend([Image.open(kuehlschrank_img), "Kühlschrank"])
                if prospekt_files: 
                    for p in prospekt_files: content.extend([Image.open(p), "Prospekt"])
                
                try:
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    res = m.generate_content(content)
                    raw = res.text
                    
                    if "---INTRO_ENDE---" in raw:
                        ip, rp = raw.split("---INTRO_ENDE---")
                        st.session_state.intro_text = ip.strip()
                    else: rp = raw
                    
                    parts = [p.strip() for p in rp.split("---TRENNER---") if len(p.strip()) > 20]
                    
                    idx = 0
                    for p in parts:
                        if idx < len(slots_to_fill):
                            target = slots_to_fill[idx]
                            st.session_state.recipe_slots[target]['content'] = p
                            if 'rating' not in st.session_state.recipe_slots[target]:
                                st.session_state.recipe_slots[target]['rating'] = 0
                            idx += 1
                    
                    save_week_plan(selected_profile_name, week_key, {
                        "recipes": st.session_state.recipe_slots,
                        "intro": st.session_state.intro_text,
                        "shopping_list": st.session_state.get('generated_list_draft')
                    })
                    st.rerun()
                except Exception as e: 
                    st.error(f"Fehler: {e}")

    # --- ANZEIGE ---
    if st.session_state.recipe_slots:
        if st.session_state.intro_text:
            st.markdown(f'<div class="intro-box">{st.session_state.intro_text}</div>', unsafe_allow_html=True)
            
        st.markdown(f'<div class="section-title">🍳 Dein Menü</div>', unsafe_allow_html=True)
        
        display_slots = st.session_state.recipe_slots[:days_to_plan]
        
        for i, slot in enumerate(display_slots):
            content = slot.get('content')
            title, body = split_recipe_content(content) if content else ("Lädt...", "")
            
            with st.container(border=True):
                c1, c2 = st.columns([0.7, 0.3])
                is_locked = slot.get('locked', False)
                rating_val = slot.get('rating', 0)
                
                with c1:
                    st.markdown(f"<div class='recipe-header'>{title}</div>", unsafe_allow_html=True)
                    
                    rating_opts = [
                        "0 Sterne (Nicht wiederholen)", 
                        "1 Stern (Selten)", 
                        "2 Sterne (Lecker)", 
                        "3 Sterne (Lieblingsessen)"
                    ]
                    sel_idx = max(0, min(3, rating_val))
                    
                    new_rating_str = st.selectbox(
                        "Bewertung:", 
                        rating_opts, 
                        index=sel_idx, 
                        key=f"rate_{i}_{week_key}", 
                        label_visibility="collapsed"
                    )
                    
                    new_val = rating_opts.index(new_rating_str)
                    if new_val != rating_val:
                        st.session_state.recipe_slots[i]['rating'] = new_val
                        save_week_plan(selected_profile_name, week_key, {
                            "recipes": st.session_state.recipe_slots,
                            "intro": st.session_state.intro_text,
                            "shopping_list": st.session_state.get('generated_list_draft')
                        })
                        save_recipe_to_db(title, content, new_val, "Weekly Plan")
                        st.toast(f"Bewertung gespeichert!", icon="⭐")

                with c2:
                    toggle_key = f"fix_{i}_{week_key}_{is_locked}"
                    if st.button(f"{'🔒 Fixiert' if is_locked else '🔓 Offen'}", key=toggle_key, use_container_width=True):
                         st.session_state.recipe_slots[i]['locked'] = not is_locked
                         save_week_plan(selected_profile_name, week_key, {
                            "recipes": st.session_state.recipe_slots,
                            "intro": st.session_state.intro_text,
                            "shopping_list": st.session_state.get('generated_list_draft')
                        })
                         st.rerun()

                if content:
                    with st.expander("📖 Zubereitung & Zutaten"):
                        st.markdown(body)
        
        st.divider()
        c1, c2 = st.columns(2)
        
        if c1.button("🎲 Offene Gerichte neu würfeln", use_container_width=True):
            for slot in st.session_state.recipe_slots:
                if not slot['locked']: slot['content'] = None
            st.rerun()

        if c2.button("🛒 Einkaufsliste erstellen", type="primary", use_container_width=True):
            status = st.status("🛒 Verarbeite...", expanded=True)
            status.write("Fixiere Gerichte...")
            
            for slot in st.session_state.recipe_slots:
                slot['locked'] = True
            
            status.write("Schreibe Liste...")
            all_txt = "\n".join([s['content'] for s in st.session_state.recipe_slots if s['content']])
            
            prompt_list = f"""
            Erstelle eine Einkaufsliste für diese Rezepte:
            {all_txt}
            
            Regeln:
            1. Sortiere nach Supermarkt-Bereichen.
            2. Fasse Mengen zusammen.
            3. Benutze Emojis bei den Zutaten.
            4. Ignoriere diesen Vorrat: {current_data.get('vorrat','')}
            """
            
            try:
                # FIX: flash-latest nutzen
                ml = genai.GenerativeModel('gemini-flash-latest')
                rl = ml.generate_content(prompt_list)
                st.session_state.generated_list_draft = rl.text
                
                save_week_plan(selected_profile_name, week_key, {
                    "recipes": st.session_state.recipe_slots,
                    "intro": st.session_state.intro_text,
                    "shopping_list": rl.text
                })
                status.update(label="Fertig!", state="complete", expanded=False)
                time.sleep(0.5); st.rerun()
            except Exception as e:
                status.update(label="Fehler!", state="error")
                st.error(f"Fehler: {e}")

        if st.session_state.get('generated_list_draft'):
            st.divider()
            st.markdown('<div class="section-title">🛒 Deine Einkaufsliste</div>', unsafe_allow_html=True)
            st.markdown(st.session_state.generated_list_draft)
            
            st.write("")
            if st.button("🗑️ Woche löschen"):
                delete_week_plan(selected_profile_name, week_key)
                st.session_state.recipe_slots = []
                st.session_state.generated_list_draft = None
                st.rerun()
