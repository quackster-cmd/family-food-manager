import streamlit as st
import google.generativeai as genai
from PIL import Image
import datetime
import time
import re
from supabase import create_client, Client

# --- KONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🥑", layout="wide")

# --- SPRACH-DATENBANK ---
TRANSLATIONS = {
    "Deutsch": {
        "title_sub": "MANAGER",
        "login_fail": "Anmeldung fehlgeschlagen:",
        "login_success": "Erfolg! Bitte einloggen.",
        "tab_login": "Anmelden",
        "tab_signup": "Registrieren",
        "email": "E-Mail Adresse",
        "password": "Passwort",
        "btn_login": "Einloggen",
        "btn_signup": "Konto erstellen",
        "btn_logout": "Abmelden",
        "header_planning": "📅 Zeitplanung",
        "week_curr": "KW {} (Aktuell)",
        "week_next": "KW {} (Nächste)",
        "header_add_recipe": "📚 Rezept manuell speichern",
        "input_text": "Text/Link",
        "input_photo": "Foto",
        "rate_label": "Bewertung:",
        "btn_save_db": "In Datenbank speichern",
        "save_success": "Gespeichert!",
        "welcome": "👋 Willkommen! Richten wir dein Profil ein.",
        "lbl_adults": "Erwachsene",
        "lbl_kids_large": "Kinder (über 3)",
        "lbl_kids_small": "Kinder (unter 3)",
        "lbl_diet": "Ernährung",
        "lbl_pantry": "Vorrat / Standards",
        "lbl_avoid": "Vermeiden",
        "lbl_devices": "Geräte",
        "lbl_goals": "Ziele",
        "lbl_shops": "Supermärkte",
        "btn_save_profile": "Profil speichern",
        "header_plan": "Planung für",
        "lbl_days": "Anzahl Tage",
        "lbl_time": "Zeit (Min)",
        "lbl_wishes": "Wünsche",
        "btn_start_plan": "🚀 Planung starten",
        "spinner_cooking": "Der digitale Koch brutzelt...",
        "btn_reroll": "🎲 Offene neu würfeln",
        "btn_shopping": "🛒 Einkaufsliste erstellen",
        "spinner_shop": "Filtere Zutaten & sortiere...",
        "header_shopping": "🛒 Deine Einkaufsliste",
        "toggle_shop_mode": "📱 INTERAKTIVER MODUS (ZUM ABHAKEN)",
        "btn_clear_week": "🗑️ Woche löschen",
        "prompt_lang": "Antworte strikt auf DEUTSCH.",
        "rate_0": "Bitte bewerten (Neu)",
        "rate_1": "⭐ (Selten)",
        "rate_2": "⭐⭐ (Lecker)",
        "rate_3": "⭐⭐⭐ (Liebling)",
        "locked": "🔒 Fixiert",
        "unlocked": "🔓 Offen",
        "profile_edit": "⚙️ Profil bearbeiten",
        "history_found": "Bereits {}x gekocht | Letzte Note: {}",
        "history_new": "✨ Neues Rezept"
    },
    "English": {
        "title_sub": "MANAGER",
        "login_fail": "Login failed:",
        "login_success": "Success! Please log in.",
        "tab_login": "Login",
        "tab_signup": "Sign Up",
        "email": "Email",
        "password": "Password",
        "btn_login": "Log In",
        "btn_signup": "Sign Up",
        "btn_logout": "Log Out",
        "header_planning": "📅 Planning",
        "week_curr": "Week {} (Current)",
        "week_next": "Week {} (Next)",
        "header_add_recipe": "📚 Add Manual Recipe",
        "input_text": "Text/Link",
        "input_photo": "Photo",
        "rate_label": "Rating:",
        "btn_save_db": "Save to DB",
        "save_success": "Saved!",
        "welcome": "👋 Welcome! Let's set up your profile.",
        "lbl_adults": "Adults",
        "lbl_kids_large": "Kids (> 3)",
        "lbl_kids_small": "Kids (< 3)",
        "lbl_diet": "Diet",
        "lbl_pantry": "Pantry Staples",
        "lbl_avoid": "Avoid",
        "lbl_devices": "Devices",
        "lbl_goals": "Goals",
        "lbl_shops": "Shops",
        "btn_save_profile": "Save Profile",
        "header_plan": "Planning for",
        "lbl_days": "Days",
        "lbl_time": "Time (Min)",
        "lbl_wishes": "Wishes",
        "btn_start_plan": "🚀 Start Planning",
        "spinner_cooking": "Cooking up ideas...",
        "btn_reroll": "🎲 Reroll Open Slots",
        "btn_shopping": "🛒 Create Shopping List",
        "spinner_shop": "Filtering & Sorting...",
        "header_shopping": "🛒 Shopping List",
        "toggle_shop_mode": "📱 SHOPPING MODE (CHECK-OFF)",
        "btn_clear_week": "🗑️ Clear Week",
        "prompt_lang": "Answer strictly in ENGLISH.",
        "rate_0": "Rate me (New)",
        "rate_1": "⭐ (Rarely)",
        "rate_2": "⭐⭐ (Tasty)",
        "rate_3": "⭐⭐⭐ (Favorite)",
        "locked": "🔒 Locked",
        "unlocked": "🔓 Open",
        "profile_edit": "⚙️ Edit Profile",
        "history_found": "Cooked {}x | Last Rating: {}",
        "history_new": "✨ New Discovery"
    }
}

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
    
    /* EINKAUFSLISTE KATEGORIEN BUNT MACHEN */
    h3 {
        color: #4ECDC4 !important; /* Türkis */
        font-weight: 800 !important;
        margin-top: 20px !important;
    }
    
    /* ABHAKEN STYLING */
    .stCheckbox label {
        font-size: 1.1rem !important;
    }
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
if 'lang' not in st.session_state: st.session_state.lang = "Deutsch"

if st.session_state.session:
    try: supabase.postgrest.auth(st.session_state.session.access_token)
    except: st.session_state.session = None

def get_txt(key): return TRANSLATIONS[st.session_state.lang][key]

# --- HELPER ---
def split_recipe_content(content):
    if not content: return "...", ""
    lines = content.split('\n')
    title = lines[0].replace('#', '').strip() 
    body = "\n".join(lines[1:])
    return title, body

def get_recipe_stats(title):
    try:
        clean_title = title.replace('#', '').strip()
        res = supabase.table("recipe_database").select("*").ilike("title", f"%{clean_title}%").execute()
        data = res.data
        if data:
            return len(data), data[0].get('rating', 0)
        return 0, 0
    except: return 0, 0

def get_profile(user_id):
    try:
        response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else {}
    except: return {}

def save_profile_db(user_id, data):
    existing = get_profile(user_id)
    payload = {"user_id": user_id, "preferences": data, "pantry": data.get("vorrat", "")}
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

# --- LOGIN ---
if not st.session_state.session:
    st.markdown(f'<div class="main-title"><span class="brand">Food & Family</span><span class="subtitle">{get_txt("title_sub")}</span></div>', unsafe_allow_html=True)
    st.session_state.lang = st.radio("Sprache / Language", ["Deutsch", "English"], horizontal=True)
    
    tab1, tab2 = st.tabs([get_txt("tab_login"), get_txt("tab_signup")])
    with tab1:
        email = st.text_input(get_txt("email"), key="l_em")
        password = st.text_input(get_txt("password"), type="password", key="l_pw")
        if st.button(get_txt("btn_login")):
            try:
                auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.session = auth_resp.session
                st.rerun()
            except Exception as e: st.error(f"{get_txt('login_fail')} {e}")
    with tab2:
        su_email = st.text_input(get_txt("email"), key="s_em")
        su_pass = st.text_input(get_txt("password"), type="password", key="s_pw")
        if st.button(get_txt("btn_signup")):
            try:
                supabase.auth.sign_up({"email": su_email, "password": su_pass})
                st.success(get_txt("login_success"))
            except Exception as e: st.error(f"Error: {e}")
    st.stop()

# --- APP ---
user_id = st.session_state.session.user.id
user_email = st.session_state.session.user.email

with st.sidebar:
    st.session_state.lang = st.selectbox("🌐 Sprache", ["Deutsch", "English"])
    st.caption(f"User: {user_email}")
    if st.button(get_txt("btn_logout")):
        supabase.auth.sign_out(); st.session_state.session = None; st.rerun()
        
    st.divider(); st.subheader(get_txt("header_planning"))
    today = datetime.date.today(); year, week, _ = today.isocalendar()
    w1 = get_txt("week_curr").format(week); w2 = get_txt("week_next").format(week+1)
    
    if 'sel_week_opt' not in st.session_state: st.session_state.sel_week_opt = w1
    sel_week_opt = st.radio("Woche:", [w1, w2], index=0 if w1 == st.session_state.sel_week_opt else 1)
    st.session_state.sel_week_opt = sel_week_opt
    
    sel_week_num = week if str(week) in sel_week_opt else week + 1
    if sel_week_num > 52: sel_week_num = 1; year += 1
    week_key = f"{year}-W{sel_week_num}"
    
    if 'curr_wk' not in st.session_state: st.session_state.curr_wk = ""
    if st.session_state.curr_wk != week_key:
        st.session_state.recipe_slots = []; st.session_state.intro_text = ""; st.session_state.generated_list_draft = None; st.session_state.checked_items = {}; st.session_state.curr_wk = week_key; st.rerun()

    st.divider(); 
    with st.expander(get_txt("header_add_recipe")):
        up_mode = st.radio("Modus:", [get_txt("input_text"), get_txt("input_photo")], horizontal=True)
        new_rec = None
        if get_txt("input_photo") in up_mode:
            up_img = st.file_uploader("Img", type=["jpg","png"])
            if up_img: new_rec = [Image.open(up_img), f"Analysiere: Titel, Zutaten, Anleitung. {get_txt('prompt_lang')}"]
        else:
            txt_in = st.text_area("Txt")
            if txt_in: new_rec = [f"Formatiere als Rezept: {txt_in}. {get_txt('prompt_lang')}"]
        
        rating_opts = [get_txt("rate_0"), get_txt("rate_1"), get_txt("rate_2"), get_txt("rate_3")]
        r_sel = st.selectbox(get_txt("rate_label"), rating_opts, index=2)
        
        if new_rec and st.button(get_txt("btn_save_db")):
            with st.spinner("..."):
                try:
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    res = m.generate_content(["Formatiere Rezept: Zeile 1 Emoji+Titel. Dann Zutaten/Anleitung.", new_rec[0]] if isinstance(new_rec, list) else [new_rec[0]])
                    t, b = split_recipe_content(res.text)
                    save_recipe_to_db(t, res.text, rating=rating_opts.index(r_sel), source="User")
                    st.success(get_txt("save_success"))
                except Exception as e: st.error(f"Error: {e}")

# --- MAIN ---
st.markdown(f'<div class="main-title"><span class="brand">Food & Family</span><span class="subtitle">{get_txt("title_sub")}</span></div>', unsafe_allow_html=True)

db_profile = get_profile(user_id)
pref = db_profile.get("preferences", {})
is_new = not pref

if is_new:
    st.info(get_txt("welcome"))
    with st.form("setup"):
        c1,c2,c3 = st.columns(3)
        p_erw = c1.number_input(get_txt("lbl_adults"),1,10,2)
        p_k3 = c2.number_input(get_txt("lbl_kids_large"),0,10,0)
        p_ku3 = c3.number_input(get_txt("lbl_kids_small"),0,10,0)
        p_dia = st.multiselect(get_txt("lbl_diet"), ["Alles","Vegetarisch","Vegan"], default=["Alles"])
        p_vor = st.text_area(get_txt("lbl_pantry"), "Nudeln, Reis, Salz, Öl")
        if st.form_submit_button(get_txt("btn_save_profile")):
            d = {"erwachsene":p_erw,"kinder_ueber3":p_k3,"kinder_unter3":p_ku3,"diaet":p_dia,"vorrat":p_vor}
            save_profile_db(user_id, d); st.rerun()
else:
    db_plan = get_week_plan_db(user_id, week_key)
    if db_plan and not st.session_state.recipe_slots:
        data = db_plan.get('plan_data', {})
        st.session_state.recipe_slots = data.get('recipes', [])
        st.session_state.intro_text = data.get('intro', "")
        st.session_state.generated_list_draft = data.get('shopping_list', "")
        st.session_state.days_slider_val = len(st.session_state.recipe_slots)

    st.markdown(f'<div class="section-title">{get_txt("header_plan")} {sel_week_opt}</div>', unsafe_allow_html=True)

    with st.expander(get_txt("profile_edit"), expanded=False):
        with st.form("edit"):
            c1,c2,c3 = st.columns(3)
            p_erw = c1.number_input(get_txt("lbl_adults"),1,10,pref.get("erwachsene",2))
            p_k3 = c2.number_input(get_txt("lbl_kids_large"),0,10,pref.get("kinder_ueber3",0))
            p_ku3 = c3.number_input(get_txt("lbl_kids_small"),0,10,pref.get("kinder_unter3",0))
            
            dia_def = pref.get("diaet", ["Alles"])
            if isinstance(dia_def, str): dia_def = [dia_def]
            p_dia = st.multiselect(get_txt("lbl_diet"), ["Alles","Vegetarisch","Vegan"], default=dia_def)
            
            c_a, c_b = st.columns(2)
            av_def = pref.get("vermeiden_select", [])
            p_verm_sel = c_a.multiselect(get_txt("lbl_avoid"), ["Nüsse","Pilze","Tomaten","Fisch","Schwein"], default=av_def)
            p_verm_txt = c_b.text_input("Sonstiges", pref.get("vermeiden_text",""))
            
            p_geraete = st.multiselect(get_txt("lbl_devices"), ["Backofen","Mikrowelle","Mixer","Herd","Air Fryer","Thermomix"], default=pref.get("geraete", ["Backofen","Herd"]))
            p_ziele = st.multiselect(get_txt("lbl_goals"), ["Geld sparen","Schnell","Gesund","Neue Rezepte"], default=pref.get("ziele", ["Geld sparen"]))
            p_shops = st.multiselect(get_txt("lbl_shops"), ["Aldi","Lidl","Rewe","Edeka","DM"], default=pref.get("shops", ["Aldi","Rewe"]))
            
            p_vor = st.text_area(get_txt("lbl_pantry"), pref.get("vorrat",""))
            
            if st.form_submit_button(get_txt("btn_save_profile")):
                d = {"erwachsene":p_erw,"kinder_ueber3":p_k3,"kinder_unter3":p_ku3,"diaet":p_dia,"vermeiden_select":p_verm_sel,"vermeiden_text":p_verm_txt,"geraete":p_geraete,"ziele":p_ziele,"shops":p_shops,"vorrat":p_vor}
                save_profile_db(user_id, d); st.success(get_txt("save_success")); st.rerun()

    empty = len(st.session_state.recipe_slots) == 0
    with st.expander("📝 " + get_txt("header_plan"), expanded=empty):
        c_i1, c_i2 = st.columns(2)
        d_def = st.session_state.get('days_slider_val', 4)
        days = c_i1.slider(get_txt("lbl_days"), 1, 7, d_def, key="ds")
        if days != d_def: st.session_state.days_slider_val = days
        mins = c_i1.slider(get_txt("lbl_time"), 0, 120, 30, step=5)
        wishes = c_i2.text_area(get_txt("lbl_wishes"))
        
        if not st.session_state.recipe_slots and st.button(get_txt("btn_start_plan"), type="primary"):
            st.session_state.recipe_slots = [{'day': i+1, 'content': None, 'locked': False, 'rating': 0} for i in range(days)]; st.rerun()

    if st.session_state.recipe_slots:
        slots = st.session_state.recipe_slots
        if len(slots) < days:
             for i in range(len(slots), days): slots.append({'day': i+1, 'content': None, 'locked': False, 'rating': 0})
        
        to_fill = [i for i, s in enumerate(slots) if s['content'] is None]
        if to_fill:
            with st.spinner(get_txt("spinner_cooking")):
                locked = [s['content'] for s in slots if s['locked'] and s['content']]
                # PROMPT UPDATE: Emojis & Nährwerte
                p_text = f"Rolle: Food Manager. Profil: {pref.get('erwachsene')} Erw, {pref.get('kinder_ueber3')} Kind>3. Ernährung: {','.join(pref.get('diaet',[]))}. Wünsche: {wishes}. Fixiert: {' '.join(locked)}. AUFGABE: {len(to_fill)} Rezepte. FORMAT: 1. Intro -> '---INTRO_ENDE---'. 2. Rezepte getrennt '---TRENNER---'. 3. Titel mit Emoji. 4. Nährwerte (Kcal/E/K/F) am Ende. {get_txt('prompt_lang')}"
                try:
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    res = m.generate_content(p_text)
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
                if hist_count > 0: st.markdown(f'<span class="history-badge">{get_txt("history_found").format(hist_count, "⭐"*hist_rating)}</span>', unsafe_allow_html=True)
                else: st.markdown(f'<span class="history-badge">{get_txt("history_new")}</span>', unsafe_allow_html=True)

                c1, c2 = st.columns([0.7, 0.3])
                lck = s.get('locked', False); rat = s.get('rating', 0)
                with c1:
                    st.markdown(f"<div class='recipe-header'>{tit}</div>", unsafe_allow_html=True)
                    r_opts = [get_txt("rate_0"), get_txt("rate_1"), get_txt("rate_2"), get_txt("rate_3")]
                    new_r = st.selectbox(get_txt("rate_label"), r_opts, index=min(3, rat), key=f"rr_{i}", label_visibility="collapsed")
                    if r_opts.index(new_r) != rat:
                        new_val = r_opts.index(new_r)
                        st.session_state.recipe_slots[i]['rating'] = new_val
                        save_week_plan_db(user_id, week_key, {"recipes": st.session_state.recipe_slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.get('generated_list_draft')})
                        if new_val > 0: save_recipe_to_db(tit, cnt, rating=new_val, source="AI-Plan")
                        st.rerun()
                with c2:
                    btn_txt = get_txt("locked") if lck else get_txt("unlocked")
                    if st.button(btn_txt, key=f"lock_{i}", use_container_width=True):
                        st.session_state.recipe_slots[i]['locked'] = not lck
                        save_week_plan_db(user_id, week_key, {"recipes": st.session_state.recipe_slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.get('generated_list_draft')}); st.rerun()
                if cnt:
                    with st.expander("📖 Details"): st.markdown(bod)

        st.divider(); c1, c2 = st.columns(2)
        if c1.button(get_txt("btn_reroll"), use_container_width=True):
            for s in st.session_state.recipe_slots:
                if not s['locked']: s['content'] = None
            st.rerun()

        if c2.button(get_txt("btn_shopping"), type="primary", use_container_width=True):
            status = st.status(get_txt("spinner_shop"), expanded=True)
            for s in st.session_state.recipe_slots: s['locked'] = True
            save_week_plan_db(user_id, week_key, {"recipes": st.session_state.recipe_slots, "intro": st.session_state.intro_text, "shopping_list": st.session_state.get('generated_list_draft')})
            
            ingredients_only = ""
            for s in st.session_state.recipe_slots:
                if s['content']:
                    lines = s['content'].split('\n')
                    for line in lines:
                        clean = line.strip()
                        if clean.startswith('-') or clean.startswith('*'):
                            ingredients_only += clean + "\n"
            
            if len(ingredients_only) < 10: 
                ingredients_only = "\n".join([s['content'] for s in st.session_state.recipe_slots if s['content']])

            # PROMPT UPDATE: Emojis + Überschriften
            p = f"Erstelle Einkaufsliste für:\n{ingredients_only}\nVorrat ignorieren: {pref.get('vorrat','')}. Sortiere sinnvoll nach Kategorien. Nutze Emojis für Kategorien (z.B. 🥦 Obst). Kategorien als Markdown-Überschriften (###). {get_txt('prompt_lang')}"
            
            success = False
            model_list = ['gemini-1.5-flash', 'gemini-2.0-flash-exp', 'gemini-2.5-flash']
            
            for model_name in model_list:
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
            st.divider(); st.markdown(f'<div class="section-title">{get_txt("header_shopping")}</div>', unsafe_allow_html=True)
            sm = st.toggle(get_txt("toggle_shop_mode"))
            if sm:
                # ABHAKEN MODUS (MIT STRIKETHROUGH)
                st.info("💡 Tipp: Erledigtes wird durchgestrichen.")
                for ln in st.session_state.generated_list_draft.split('\n'):
                    cl = ln.strip()
                    if cl.startswith('-') or cl.startswith('*'):
                        it = cl.replace('-','').replace('*','').strip()
                        ch = st.session_state.checked_items.get(it, False)
                        
                        # Trick: Zwei Spalten, damit der Text schön aussieht
                        c_cb, c_txt = st.columns([0.1, 0.9])
                        if c_cb.checkbox("done", value=ch, key=f"c_{it}", label_visibility="collapsed"):
                            st.session_state.checked_items[it] = True
                            c_txt.markdown(f"~~{it}~~") # Durchstreichen
                        else:
                            st.session_state.checked_items[it] = False
                            c_txt.write(it)
                    else: st.markdown(cl) # Überschriften bunt durch CSS
            else: st.markdown(st.session_state.generated_list_draft)
            
            if st.button(get_txt("btn_clear_week")):
                supabase.table("weekly_plans").delete().eq("user_id", user_id).eq("week_key", week_key).execute()
                st.session_state.recipe_slots=[]; st.session_state.generated_list_draft=None; st.rerun()
