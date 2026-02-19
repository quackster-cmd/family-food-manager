import streamlit as st
import google.generativeai as genai
from PIL import Image
import datetime
import time
from collections import Counter
from supabase import create_client, Client

# --- KONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🥑", layout="wide", initial_sidebar_state="collapsed")

# --- OPTIONEN LISTEN (KOMPLETT) ---
OPTS_DIET = sorted(["Alles", "Vegetarisch", "Vegan", "Ohne Schwein", "Glutenfrei", "Laktosefrei", "Pescatarier", "Low Carb", "Keto"])
OPTS_AVOID = sorted(["Nüsse", "Eier", "Soja", "Pilze", "Oliven", "Fisch", "Tomaten", "Paprika", "Zwiebeln", "Knoblauch", "Koriander"])
OPTS_DEVICES = sorted(["Backofen", "Mikrowelle", "Mixer", "Herd", "Air Fryer", "Thermomix", "Slow Cooker", "Grill", "Dampfgarer"])
OPTS_GOALS = sorted(["Geld sparen", "Weniger Fleisch", "Leichte Küche", "Neue Rezepte entdecken", "Proteinreich (Sport)", "Einkäufe minimieren", "Schnelle Küche (<20 Min)", "Bio / Nachhaltig", "Meal Prep geeignet"])
OPTS_SHOPS = sorted(["Aldi", "Lidl", "Rewe", "Edeka", "Netto", "Penny", "Kaufland", "DM", "Rossmann", "Marktkauf", "Hit", "Globus"])

# --- CSS / DESIGN ---
st.markdown("""
    <style>
    .main-title { text-align: center; padding: 10px; margin-bottom: 20px; }
    .main-title span.brand {
        font-size: 3rem; font-weight: 900;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        display: block;
    }
    .main-title span.subtitle {
        font-size: 1.2rem; font-weight: 700; color: #888;
        display: block; margin-top: -5px; letter-spacing: 3px; text-transform: uppercase;
    }
    @media (prefers-color-scheme: dark) { .main-title span.subtitle { color: #ccc; } }
    
    .section-title {
        font-size: 1.8rem; font-weight: 800; margin-top: 30px; margin-bottom: 20px;
        color: #4ECDC4; border-bottom: 1px solid rgba(128, 128, 128, 0.2); padding-bottom: 10px;
    }
    .intro-box {
        padding: 15px; background-color: rgba(78, 205, 196, 0.15);
        border-radius: 10px; margin-bottom: 25px; font-style: italic; border-left: 5px solid #4ECDC4;
    }
    .recipe-header { font-size: 1.4rem; font-weight: 700; margin-bottom: 0px; }
    
    .history-badge {
        font-size: 0.8rem; background-color: rgba(255, 255, 255, 0.1); 
        padding: 2px 8px; border-radius: 10px; color: #888; margin-bottom: 5px; display: inline-block;
    }
    
    .shop-cat {
        color: #4ECDC4 !important; font-weight: 800 !important; font-size: 1.2rem;
        margin-top: 25px !important; margin-bottom: 5px !important;
        border-bottom: 1px solid #333;
    }
    div[data-testid="stCheckbox"] { margin-bottom: -15px !important; } 
    div[data-testid="stCheckbox"] label input:checked + div {
        text-decoration: line-through; color: #888;
    }
    
    .trend-box {
        background-color: rgba(255, 107, 107, 0.1); 
        padding: 10px; border-radius: 8px; margin-bottom: 10px;
        border-left: 3px solid #FF6B6B;
    }
    .trend-rank { font-weight: bold; color: #FF6B6B; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SETUP ---
try:
    if "supabase" in st.secrets and "GOOGLE_API_KEY" in st.secrets:
        SUPABASE_URL = st.secrets["supabase"]["url"]
        SUPABASE_KEY = st.secrets["supabase"]["key"]
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 Secrets missing!")
        st.stop()
except Exception as e:
    st.error(f"🚨 Error: {e}")
    st.stop()

# --- AUTH RESTORE ---
if 'session' not in st.session_state: st.session_state.session = None

if st.session_state.session:
    try: supabase.postgrest.auth(st.session_state.session.access_token)
    except: st.session_state.session = None

# --- HELPER FUNCTIONS ---
def split_recipe_content(content):
    if not content: return "...", ""
    lines = content.split('\n')
    title = lines[0].replace('#', '').strip() if lines else "..."
    body = "\n".join(lines[1:])
    return title, body

def get_recipe_stats(title):
    try:
        clean_title = title.replace('#', '').strip()
        res = supabase.table("recipe_database").select("*").ilike("title", f"%{clean_title}%").execute()
        if res.data: return len(res.data), res.data[0].get('rating', 0)
        return 0, 0
    except: return 0, 0

def get_community_trends():
    try:
        res = supabase.table("recipe_database").select("title").gte("rating", 2).execute()
        if not res.data: return []
        titles = [r['title'] for r in res.data]
        return Counter(titles).most_common(5)
    except: return []

def get_profile(user_id):
    try:
        response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else {}
    except: return {}

def save_profile_db(user_id, data):
    existing = get_profile(user_id)
    payload = {"user_id": user_id, "preferences": data, "pantry": data.get("vorrat", ""), "username": data.get("username", "")}
    if existing: payload["id"] = existing["id"]
    try: supabase.table("profiles").upsert(payload).execute()
    except Exception as e: st.error(f"DB Error: {e}")

def get_week_plan_db(user_id, week_key):
    try:
        response = supabase.table("weekly_plans").select("*").eq("user_id", user_id).eq("week_key", week_key).execute()
        return response.data[0] if response.data else None
    except: return None

def save_week_plan_db(user_id, week_key, plan_data):
    existing = get_week_plan_db(user_id, week_key)
    payload = {"user_id": user_id, "week_key": week_key, "plan_data": plan_data}
    if existing: payload["id"] = existing["id"]
    try: supabase.table("weekly_plans").upsert(payload).execute()
    except: pass

def save_recipe_to_db(title, content, rating=0, source="AI"):
    db_entry = {"title": title, "content": content, "rating": rating, "source": source, "added_date": str(datetime.date.today())}
    try: supabase.table("recipe_database").insert(db_entry).execute()
    except: pass

# --- LOGIN SCREEN ---
if not st.session_state.session:
    st.markdown(f'<div class="main-title"><span class="brand">Food & Family</span><span class="subtitle">MANAGER</span></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Anmelden", "Registrieren"])
    with tab1:
        email = st.text_input("E-Mail Adresse", key="l_em")
        password = st.text_input("Passwort", type="password", key="l_pw")
        c_l1, c_l2 = st.columns([1,1])
        if c_l1.button("Einloggen", use_container_width=True):
            try:
                auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.session = auth_resp.session
                st.rerun()
            except Exception as e: st.error(f"Fehler: {e}")
        if c_l2.button("Passwort vergessen?", use_container_width=True):
            if not email: st.error("Bitte E-Mail eingeben.")
            else:
                try: supabase.auth.reset_password_for_email(email); st.success(f"Reset-Mail an {email} gesendet.")
                except: st.error("Fehler beim Reset.")

    with tab2:
        su_email = st.text_input("E-Mail Adresse", key="s_em")
        su_pass = st.text_input("Passwort", type="password", key="s_pw")
        if st.button("Konto erstellen", use_container_width=True):
            try: supabase.auth.sign_up({"email": su_email, "password": su_pass}); st.success("Erfolg! Bitte E-Mail bestätigen.")
            except Exception as e: st.error(f"Error: {e}")
    st.stop()

# --- APP LOGIC (EINGELOGGT) ---
user_id = st.session_state.session.user.id
user_email = st.session_state.session.user.email

# SIDEBAR
with st.sidebar:
    st.markdown("### 👤 Profil")
    st.caption(f"Angemeldet: {user_email}")
    if st.button("Abmelden"):
        supabase.auth.sign_out(); st.session_state.session = None; st.rerun()
        
    st.divider(); st.subheader("📅 Zeitplanung")
    today = datetime.date.today(); year, week, _ = today.isocalendar()
    w1 = f"KW {week} (Aktuell)"; w2 = f"KW {week + 1} (Nächste)"
    
    if 'sel_week_opt' not in st.session_state: st.session_state.sel_week_opt = w1
    sel_week_opt = st.radio("Woche:", [w1, w2], index=0 if w1 == st.session_state.sel_week_opt else 1)
    st.session_state.sel_week_opt = sel_week_opt
    
    sel_week_num = week if str(week) in sel_week_opt else week + 1
    if sel_week_num > 52: sel_week_num = 1; year += 1
    week_key = f"{year}-W{sel_week_num}"
    
    if 'curr_wk' not in st.session_state: st.session_state.curr_wk = ""
    if st.session_state.curr_wk != week_key:
        st.session_state.recipe_slots = []; st.session_state.intro_text = ""; st.session_state.generated_list_draft = None; st.session_state.checked_items = {}; st.session_state.curr_wk = week_key; st.rerun()

    st.divider(); st.subheader("🏆 Community Top 5")
    trends = get_community_trends()
    if trends:
        for idx, (title, count) in enumerate(trends):
            st.markdown(f"""<div class="trend-box"><span class="trend-rank">#{idx+1}</span> {title} <br><small>🔥 {count}x gekocht</small></div>""", unsafe_allow_html=True)
    else: st.caption("Noch keine Daten.")

    st.divider()
    with st.expander("📚 Rezept manuell hochladen"):
        up_mode = st.radio("Eingabe:", ["Text/Link", "Foto"], horizontal=True)
        new_rec = None
        if up_mode == "Foto":
            up_img = st.file_uploader("Bild hochladen", type=["jpg","png"])
            if up_img: new_rec = [Image.open(up_img), "Analysiere: Titel, Zutaten, Anleitung. Antworte auf DEUTSCH."]
        else:
            txt_in = st.text_area("Text oder Link einfügen")
            if txt_in: new_rec = [f"Formatiere als Rezept: {txt_in}. Antworte auf DEUTSCH."]
        
        rating_opts = ["0 (Neu)", "1 (Selten)", "2 (Lecker)", "3 (Liebling)"]
        r_sel = st.selectbox("Bewertung:", rating_opts, index=2)
        
        if new_rec and st.button("🔍 Rezept analysieren"):
            with st.spinner("Lese Rezept..."):
                try:
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    res = m.generate_content(["Formatiere Rezept: Zeile 1 Emoji+Titel. Dann Zutaten/Anleitung.", new_rec[0]] if isinstance(new_rec, list) else [new_rec[0]])
                    st.session_state.draft_recipe = res.text
                except Exception as e: st.error(f"Fehler: {e}")
        
        if 'draft_recipe' in st.session_state and st.session_state.draft_recipe:
            st.markdown("---")
            st.markdown("**📝 Rezept überprüfen & bearbeiten:**")
            edited_recipe = st.text_area("Pass den Text bei Bedarf an:", value=st.session_state.draft_recipe, height=300)
            
            if st.button("✅ Jetzt in Datenbank speichern", type="primary"):
                t, b = split_recipe_content(edited_recipe)
                save_recipe_to_db(t, edited_recipe, rating=rating_opts.index(r_sel), source="User")
                st.success("Erfolgreich gespeichert!")
                st.session_state.draft_recipe = None
                time.sleep(1)
                st.rerun()

# --- MAIN PAGE ---
st.markdown(f'<div class="main-title"><span class="brand">Food & Family</span><span class="subtitle">MANAGER</span></div>', unsafe_allow_html=True)

db_profile = get_profile(user_id)
pref = db_profile.get("preferences", {})
is_new = not pref

if is_new:
    st.info("👋 Willkommen! Richten wir dein Profil ein.")
    with st.form("setup"):
        p_name = st.text_input("Dein Name (oder 'Chefkoch')", "Chefkoch")
        c1,c2,c3 = st.columns(3)
        p_erw = c1.number_input("Erwachsene",1,10,2)
        p_k3 = c2.number_input("Kinder (>3)",0,10,0)
        p_ku3 = c3.number_input("Kinder (<3)",0,10,0)
        p_dia = st.multiselect("Ernährung", OPTS_DIET, default=["Alles"])
        p_geraete = st.multiselect("Geräte", OPTS_DEVICES, default=["Herd", "Backofen"])
        p_ziele = st.multiselect("Ziele", OPTS_GOALS, default=["Geld sparen"])
        p_shops = st.multiselect("Supermärkte", OPTS_SHOPS, default=["Aldi", "Rewe"])
        p_vor = st.text_area("Vorrat", "Nudeln, Reis, Salz, Öl")
        
        if st.form_submit_button("Profil speichern"):
            d = {"username": p_name, "erwachsene":p_erw,"kinder_ueber3":p_k3,"kinder_unter3":p_ku3,"diaet":p_dia,"geraete":p_geraete,"ziele":p_ziele,"shops":p_shops,"vorrat":p_vor}
            save_profile_db(user_id, d); st.rerun()
else:
    db_plan = get_week_plan_db(user_id, week_key)
    if db_plan and not st.session_state.recipe_slots:
        data = db_plan.get('plan_data', {})
        st.session_state.recipe_slots = data.get('recipes', [])
        st.session_state.intro_text = data.get('intro', "")
        st.session_state.generated_list_draft = data.get('shopping_list', "")
        st.session_state.days_slider_val = len(st.session_state.recipe_slots)

    st.markdown(f'<div class="section-title">Planung für {sel_week_opt}</div>', unsafe_allow_html=True)

    if 'show_profile_form' not in st.session_state: st.session_state.show_profile_form = False

    if st.button("⚙️ Profil / Einstellungen bearbeiten"):
        st.session_state.show_profile_form = not st.session_state.show_profile_form

    if st.session_state.show_profile_form:
        with st.container(border=True):
            with st.form("edit"):
                current_name = pref.get("username", "Chefkoch")
                p_name = st.text_input("Dein Name", current_name)
                c1,c2,c3 = st.columns(3)
                p_erw = c1.number_input("Erwachsene",1,10,pref.get("erwachsene",2))
                p_k3 = c2.number_input("Kinder (>3)",0,10,pref.get("kinder_ueber3",0))
                p_ku3 = c3.number_input("Kinder (<3)",0,10,pref.get("kinder_unter3",0))
                
                p_dia = st.multiselect("Ernährung", OPTS_DIET, default=pref.get("diaet", ["Alles"]))
                c_a, c_b = st.columns(2)
                p_verm_sel = c_a.multiselect("Vermeiden", OPTS_AVOID, default=pref.get("vermeiden_select", []))
                p_verm_txt = c_b.text_input("Sonstiges", pref.get("vermeiden_text",""))
                
                p_geraete = st.multiselect("Geräte", OPTS_DEVICES, default=pref.get("geraete", ["Herd"]))
                p_ziele = st.multiselect("Ziele", OPTS_GOALS, default=pref.get("ziele", ["Geld sparen"]))
                p_shops = st.multiselect("Supermärkte", OPTS_SHOPS, default=pref.get("shops", ["Aldi"]))
                p_vor = st.text_area("Vorrat", pref.get("vorrat",""))
                
                if st.form_submit_button("Profil speichern"):
                    d = {
                        "username": p_name, "erwachsene":p_erw,"kinder_ueber3":p_k3,"kinder_unter3":p_ku3,
                        "diaet":p_dia,"vermeiden_select":p_verm_sel,"vermeiden_text":p_verm_txt,
                        "geraete":p_geraete,"ziele":p_ziele,"shops":p_shops,"vorrat":p_vor
                    }
                    save_profile_db(user_id, d)
                    st.session_state.show_profile_form = False 
                    st.success("Gespeichert!")
                    time.sleep(0.5); st.rerun()

    empty = len(st.session_state.recipe_slots) == 0
    with st.expander(f"📝 Planung starten", expanded=empty):
        c_i1, c_i2 = st.columns(2)
        d_def = st.session_state.get('days_slider_val', 4)
        days = c_i1.slider("Anzahl Tage", 1, 7, d_def, key="ds")
        if days != d_def: st.session_state.days_slider_val = days
        mins = c_i1.slider("Zeit (Min)", 0, 120, 30, step=5)
        wishes = c_i2.text_area("Wünsche für die Woche")
        c_up1, c_up2 = st.columns(2)
        kuehlschrank_img = c_up1.file_uploader("📸 Kühlschrank Foto", type=["jpg","png"])
        prospekt_files = c_up2.file_uploader("📰 Prospekte (beliebig viele)", type=["jpg","png"], accept_multiple_files=True)
        
        if not st.session_state.recipe_slots and st.button("🚀 Planung starten", type="primary"):
            st.session_state.recipe_slots = [{'day': i+1, 'content': None, 'locked': False, 'rating': 0} for i in range(days)]; st.rerun()

    if st.session_state.recipe_slots:
        slots = st.session_state.recipe_slots
        if len(slots) < days:
             for i in range(len(slots), days): slots.append({'day': i+1, 'content': None, 'locked': False, 'rating': 0})
        
        to_fill = [i for i, s in enumerate(slots) if s['content'] is None]
        if to_fill:
            with st.spinner("Der digitale Koch brutzelt... Lese Bilder & analysiere Angebote..."):
                locked = [s['content'] for s in slots if s['locked'] and s['content']]
                username = pref.get('username', 'Chefkoch')
                
                content_prompt = []
                # NEU: Prompt mit strikter Regel für neutrale Titel
                p_text = f"Rolle: Food Manager. Kunde: {username}. Profil: {pref.get('erwachsene')} Erw, {pref.get('kinder_ueber3')} Kind>3. Ernährung: {','.join(pref.get('diaet',[]))}. Wünsche: {wishes}. Fixiert: {' '.join(locked)}. AUFGABE: {len(to_fill)} Rezepte. WICHTIG: Erstelle AUSSCHLIESSLICH vollwertige Hauptmahlzeiten. Ignoriere Snacks. REGELN FÜR REZEPTE: 1. Titel MÜSSEN absolut neutral und allgemein gültig sein (z.B. '🍝 Spaghetti Bolognese'). Verwende NIEMALS den Namen des Nutzers im Rezepttitel! 2. Intro (Sprich den Kunden mit {username} an) -> '---INTRO_ENDE---'. 3. Rezepte getrennt '---TRENNER---'. 4. Titel mit Emoji. 5. Nährwerte (Kcal/E/K/F) am Ende. Antworte auf DEUTSCH."
                content_prompt.append(p_text)
                
                if kuehlschrank_img: 
                    k_img = Image.open(kuehlschrank_img)
                    k_img.thumbnail((800, 800)) # Komprimierung
                    content_prompt.extend([k_img, "Nutze Zutaten aus dem Kühlschrank!"])
                
                # NEU: Effiziente Einzelkomprimierung aller Prospekte statt Fehleranfälligem Riesen-Grid
                if prospekt_files: 
                    for p in prospekt_files:
                        p_img = Image.open(p)
                        if p_img.mode != 'RGB': p_img = p_img.convert('RGB')
                        p_img.thumbnail((1000, 1000)) # Schrumpft das Bild auf max. 1000px Kantenlänge, behält Proportionen
                        content_prompt.append(p_img)
                    content_prompt.append("Lese diese komprimierten Prospektseiten und nutze die Angebote für die Rezeptplanung!")

                try:
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    res = m.generate_content(content_prompt)
                    raw = res.text
                    if "---INTRO_ENDE---" in raw: ip, rp = raw.split("---INTRO_ENDE---"); st.session_state.intro_text = ip.strip()
                    else: rp = raw
                    parts = [p.strip() for p in rp.split("---TRENNER---") if len(p.strip()) > 20]
                    idx = 0
                    for p in parts:
                        if idx < len(to_fill): slots[to_fill[idx]]['content'] = p; idx += 1
                    save_week_plan_db(user_id, week_key, {"recipes": slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.get('generated_list_draft')}); st.rerun()
                except Exception: st.error("Fehler bei KI. Bitte neu versuchen.")

    if st.session_state.recipe_slots:
        if st.session_state.intro_text: st.markdown(f'<div class="intro-box">{st.session_state.intro_text}</div>', unsafe_allow_html=True)
        
        for i, s in enumerate(st.session_state.recipe_slots[:days]):
            cnt = s.get('content'); tit, bod = split_recipe_content(cnt) if cnt else ("...", "")
            hist_count, hist_rating = get_recipe_stats(tit)
            
            with st.container(border=True):
                if hist_count > 0: st.markdown(f'<span class="history-badge">Bereits {hist_count}x gekocht | Note: {"⭐"*hist_rating}</span>', unsafe_allow_html=True)
                else: st.markdown(f'<span class="history-badge">✨ Neues Rezept</span>', unsafe_allow_html=True)

                c1, c2 = st.columns([0.7, 0.3])
                lck = s.get('locked', False); rat = s.get('rating', 0)
                with c1:
                    st.markdown(f"<div class='recipe-header'>{tit}</div>", unsafe_allow_html=True)
                    r_opts = ["Bewerten (Neu)", "1 Stern (Selten)", "2 Sterne (Lecker)", "3 Sterne (Liebling)"]
                    new_r = st.selectbox("Note:", r_opts, index=min(3, rat), key=f"rr_{i}", label_visibility="collapsed")
                    if r_opts.index(new_r) != rat:
                        new_val = r_opts.index(new_r)
                        st.session_state.recipe_slots[i]['rating'] = new_val
                        save_week_plan_db(user_id, week_key, {"recipes": st.session_state.recipe_slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.get('generated_list_draft')})
                        if new_val > 0: save_recipe_to_db(tit, cnt, rating=new_val, source="AI-Plan")
                        st.rerun()
                with c2:
                    btn_txt = "🔒 Fixiert" if lck else "🔓 Offen"
                    if st.button(btn_txt, key=f"lock_{i}", use_container_width=True):
                        st.session_state.recipe_slots[i]['locked'] = not lck
                        save_week_plan_db(user_id, week_key, {"recipes": st.session_state.recipe_slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.get('generated_list_draft')}); st.rerun()
                if cnt:
                    with st.expander("📖 Details"): st.markdown(bod)

        st.divider(); c1, c2 = st.columns(2)
        if c1.button("🎲 Offene neu würfeln", use_container_width=True):
            for s in st.session_state.recipe_slots:
                if not s['locked']: s['content'] = None
            st.rerun()

        if c2.button("🛒 Einkaufsliste erstellen", type="primary", use_container_width=True):
            status = st.status("Filtere Zutaten & sortiere...", expanded=True)
            for s in st.session_state.recipe_slots: s['locked'] = True
            save_week_plan_db(user_id, week_key, {"recipes": st.session_state.recipe_slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.get('generated_list_draft')})
            
            ingredients_only = ""
            for s in st.session_state.recipe_slots:
                if s['content']:
                    for line in s['content'].split('\n'):
                        if line.strip().startswith(('-','*')): ingredients_only += line.strip() + "\n"
            
            if len(ingredients_only) < 10: ingredients_only = "\n".join([s['content'] for s in st.session_state.recipe_slots if s['content']])

            p = f"Erstelle Einkaufsliste für:\n{ingredients_only}\nVorrat ignorieren: {pref.get('vorrat','')}. Sortiere sinnvoll nach Kategorien. Nutze Emojis für Kategorien. Kategorien als Markdown-Überschriften (###). Zutaten als Liste mit Bindestrich (-). Antworte auf DEUTSCH."
            
            success = False
            for model_name in ['gemini-1.5-flash', 'gemini-2.5-flash']:
                if success: break
                try:
                    ml = genai.GenerativeModel(model_name)
                    rl = ml.generate_content(p)
                    st.session_state.generated_list_draft = rl.text
                    success = True
                except: time.sleep(1)

            if success:
                save_week_plan_db(user_id, week_key, {"recipes": st.session_state.recipe_slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.generated_list_draft})
                status.update(label="Fertig!", state="complete", expanded=False); time.sleep(0.5); st.rerun()
            else:
                status.update(label="Fehler (Google überlastet)", state="error")
                st.error("Konnte Liste nicht erstellen.")

        if st.session_state.get('generated_list_draft'):
            st.divider(); st.markdown('<div class="section-title">🛒 Deine Einkaufsliste</div>', unsafe_allow_html=True)
            sm = st.toggle("🛍️ Einkaufs-Modus starten (Abhaken)")
            if sm:
                st.info("💡 Tipp: Erledigtes wird durchgestrichen.")
                lines = st.session_state.generated_list_draft.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("###") or (line.startswith("**") and not line.startswith("-")):
                        clean_header = line.replace("#", "").replace("*", "").strip()
                        st.markdown(f"<div class='shop-cat'>{clean_header}</div>", unsafe_allow_html=True)
                    elif line.startswith("-") or line.startswith("*"):
                        item = line.replace("-", "").replace("*", "").strip()
                        checked = st.session_state.checked_items.get(item, False)
                        
                        if st.checkbox(item, value=checked, key=f"shop_{item}"):
                            st.session_state.checked_items[item] = True
                        else:
                            st.session_state.checked_items[item] = False
                    else: st.write(line)
            else: 
                st.markdown(st.session_state.generated_list_draft)
            
            if st.button("🗑️ Woche löschen"):
                supabase.table("weekly_plans").delete().eq("user_id", user_id).eq("week_key", week_key).execute()
                st.session_state.recipe_slots=[]; st.session_state.generated_list_draft=None; st.rerun()
