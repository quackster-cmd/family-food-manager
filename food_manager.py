import streamlit as st
import google.generativeai as genai
from PIL import Image
import datetime
import time
from collections import Counter
from supabase import create_client, Client

# --- KONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🥑", layout="wide")

# --- TRANSLATIONS ---
TRANSLATIONS = {
    "Deutsch": {
        "title_sub": "MANAGER",
        "login_fail": "Fehler:",
        "tab_login": "Anmelden",
        "btn_login": "Einloggen",
        "header_planning": "📅 Zeitplanung",
        "header_community": "🏆 Community Trends (Top 5)",
        "week_curr": "KW {} (Aktuell)",
        "week_next": "KW {} (Nächste)",
        "header_add_recipe": "📚 Rezept hochladen & bearbeiten",
        "input_text": "Text/Link",
        "input_photo": "Foto",
        "rate_label": "Bewertung:",
        "btn_preview": "Vorschau erstellen",
        "btn_save_final": "💾 Rezept jetzt speichern",
        "lbl_edit_preview": "Rezept bearbeiten vor dem Speichern:",
        "save_success": "Erfolgreich gespeichert!",
        "header_plan": "Planung für",
        "lbl_days": "Anzahl Tage",
        "lbl_recipe_select": "⭐ Eigene & 🔥 Trends einplanen",
        "lbl_wishes": "Wünsche (für offene Tage)",
        "btn_start_plan": "🚀 Planung starten",
        "spinner_cooking": "Der digitale Koch plant...",
        "btn_reroll": "🎲 Offene neu würfeln",
        "btn_shopping": "🛒 Einkaufsliste erstellen",
        "toggle_shop": "🛍️ Einkaufs-Modus",
        "btn_clear": "🗑️ Woche löschen",
        "prompt_lang": "Antworte auf DEUTSCH.",
        "rate_0": "Neu / Unbewertet",
        "rate_1": "⭐ (Selten)",
        "rate_2": "⭐⭐ (Lecker)",
        "rate_3": "⭐⭐⭐ (Liebling)",
        "locked": "🔒 Fix",
        "unlocked": "🔓 Offen",
        "msg_inserted": "Rezepte übernommen!"
    },
    "English": {
        "title_sub": "MANAGER",
        "login_fail": "Error:",
        "tab_login": "Login",
        "btn_login": "Log In",
        "header_planning": "📅 Planning",
        "header_community": "🏆 Community Trends (Top 5)",
        "week_curr": "Week {} (Current)",
        "week_next": "Week {} (Next)",
        "header_add_recipe": "📚 Upload & Edit Recipe",
        "input_text": "Text/Link",
        "input_photo": "Photo",
        "rate_label": "Rating:",
        "btn_preview": "Generate Preview",
        "btn_save_final": "💾 Save Recipe Now",
        "lbl_edit_preview": "Edit recipe before saving:",
        "save_success": "Saved successfully!",
        "header_plan": "Planning for",
        "lbl_days": "Days",
        "lbl_recipe_select": "⭐ Own & 🔥 Trends",
        "lbl_wishes": "Wishes (for open slots)",
        "btn_start_plan": "🚀 Start Planning",
        "spinner_cooking": "Chef is planning...",
        "btn_reroll": "🎲 Reroll Open",
        "btn_shopping": "🛒 Create List",
        "toggle_shop": "🛍️ Shopping Mode",
        "btn_clear": "🗑️ Clear Week",
        "prompt_lang": "Answer in ENGLISH.",
        "rate_0": "New / Unrated",
        "rate_1": "⭐ (Rare)",
        "rate_2": "⭐⭐ (Tasty)",
        "rate_3": "⭐⭐⭐ (Fav)",
        "locked": "🔒 Fix",
        "unlocked": "🔓 Open",
        "msg_inserted": "Recipes inserted!"
    }
}

# --- CSS ---
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
    .shop-header { color: #4ECDC4; font-weight: 800; font-size: 1.2rem; margin-top: 15px; }
    
    /* TREND BOX */
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
    else: st.error("🚨 Secrets missing!"); st.stop()
except Exception as e: st.error(f"🚨 Init Error: {e}"); st.stop()

# --- AUTH RESTORE ---
if 'session' not in st.session_state: st.session_state.session = None
if 'lang' not in st.session_state: st.session_state.lang = "Deutsch"
if st.session_state.session:
    try: supabase.postgrest.auth(st.session_state.session.access_token)
    except: st.session_state.session = None

def get_txt(key): return TRANSLATIONS[st.session_state.lang].get(key, key)

# --- DB FUNCTIONS ---
def get_profile(user_id):
    try:
        res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else {}
    except: return {}

def save_profile_db(user_id, data):
    existing = get_profile(user_id)
    payload = {"user_id": user_id, "preferences": data, "pantry": data.get("vorrat",""), "username": data.get("username","")}
    if existing: payload["id"] = existing["id"]
    try: supabase.table("profiles").upsert(payload).execute()
    except Exception as e: st.error(f"DB Error: {e}")

def get_week_plan_db(user_id, week_key):
    try:
        res = supabase.table("weekly_plans").select("*").eq("user_id", user_id).eq("week_key", week_key).execute()
        return res.data[0] if res.data else None
    except: return None

def save_week_plan_db(user_id, week_key, plan_data):
    existing = get_week_plan_db(user_id, week_key)
    payload = {"user_id": user_id, "week_key": week_key, "plan_data": plan_data}
    if existing: payload["id"] = existing["id"]
    try: supabase.table("weekly_plans").upsert(payload).execute()
    except: pass

# --- COMMUNITY FEATURES ---
def get_community_trends():
    # Holt alle Rezepte mit Rating >= 2 (Lecker/Liebling)
    try:
        res = supabase.table("recipe_database").select("title, content").gte("rating", 2).execute()
        if not res.data: return []
        
        # Zähle Titel-Häufigkeit
        titles = [r['title'] for r in res.data]
        counts = Counter(titles)
        top_5 = counts.most_common(5)
        
        # Hole Content für die Top 5 (einfach den ersten Treffer nehmen)
        trends = []
        for title, count in top_5:
            # Suche Content für diesen Titel
            content = next((r['content'] for r in res.data if r['title'] == title), "")
            trends.append({"title": title, "count": count, "content": content})
        return trends
    except: return []

def get_all_recipes_for_selection():
    try:
        # Holt Eigene + Community (unterschieden im UI)
        res = supabase.table("recipe_database").select("title, content, rating").execute()
        return res.data if res.data else []
    except: return []

def save_recipe_to_db(title, content, rating=0, source="AI"):
    clean_title = title.split('\n')[0].replace('#','').strip()
    db_entry = {"title": clean_title, "content": content, "rating": rating, "source": source, "added_date": str(datetime.date.today())}
    try: supabase.table("recipe_database").insert(db_entry).execute()
    except: pass

def split_recipe_content(content):
    if not content: return "...", ""
    lines = content.split('\n')
    title = lines[0].replace('#', '').strip() 
    body = "\n".join(lines[1:])
    return title, body

def get_recipe_stats(title):
    try:
        clean = title.replace('#','').strip()
        res = supabase.table("recipe_database").select("*").ilike("title", f"%{clean}%").execute()
        if res.data: return len(res.data), res.data[0].get('rating',0)
        return 0, 0
    except: return 0, 0

# --- LOGIN ---
if not st.session_state.session:
    st.markdown(f'<div class="main-title"><span class="brand">Food & Family</span><span class="subtitle">{get_txt("title_sub")}</span></div>', unsafe_allow_html=True)
    st.session_state.lang = st.radio("Language", ["Deutsch", "English"], horizontal=True)
    email = st.text_input("Email", key="l_em"); password = st.text_input("Pass", type="password", key="l_pw")
    c1, c2 = st.columns(2)
    if c1.button("Login"):
        try:
            auth = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.session = auth.session; st.rerun()
        except Exception as e: st.error(f"{get_txt('login_fail')} {e}")
    if c2.button("Register"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("Check Email!")
        except Exception as e: st.error(f"Error: {e}")
    st.stop()

# --- APP ---
user_id = st.session_state.session.user.id
user_email = st.session_state.session.user.email

if 'upload_preview' not in st.session_state: st.session_state.upload_preview = ""

with st.sidebar:
    st.session_state.lang = st.selectbox("🌐", ["Deutsch", "English"])
    st.caption(f"{user_email}")
    if st.button("Logout"): supabase.auth.sign_out(); st.session_state.session = None; st.rerun()
        
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

    # --- COMMUNITY TRENDS REITER ---
    st.divider()
    st.subheader(get_txt("header_community"))
    trends = get_community_trends()
    if trends:
        for idx, t in enumerate(trends):
            st.markdown(f"""
            <div class="trend-box">
                <span class="trend-rank">#{idx+1}</span> {t['title']} <br>
                <small>🔥 {t['count']}x gekocht</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Noch keine Trends verfügbar.")

    # --- UPLOAD SECTION ---
    st.divider()
    with st.expander(get_txt("header_add_recipe")):
        up_mode = st.radio("Modus:", [get_txt("input_text"), get_txt("input_photo")], horizontal=True)
        new_rec_raw = None
        if get_txt("input_photo") in up_mode:
            up_img = st.file_uploader("Img", type=["jpg","png"])
            if up_img: new_rec_raw = [Image.open(up_img), f"Analysiere: Titel, Zutaten, Anleitung. {get_txt('prompt_lang')}"]
        else:
            txt_in = st.text_area("Text")
            if txt_in: new_rec_raw = [f"Formatiere als Rezept: {txt_in}. {get_txt('prompt_lang')}"]
        
        if new_rec_raw and st.button(get_txt("btn_preview")):
            with st.spinner("..."):
                try:
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    res = m.generate_content(["Formatiere Rezept sauber: Zeile 1 Emoji+Titel. Dann Zutaten/Anleitung.", new_rec_raw[0]] if isinstance(new_rec_raw, list) else [new_rec_raw[0]])
                    st.session_state.upload_preview = res.text
                except Exception as e: st.error(f"Error: {e}")

        if st.session_state.upload_preview:
            st.markdown("---")
            st.caption(get_txt("lbl_edit_preview"))
            edited_text = st.text_area("Editor", st.session_state.upload_preview, height=300)
            st.session_state.upload_preview = edited_text
            rating_opts = [get_txt("rate_0"), get_txt("rate_1"), get_txt("rate_2"), get_txt("rate_3")]
            r_sel = st.selectbox(get_txt("rate_label"), rating_opts, index=2, key="up_rate")
            if st.button(get_txt("btn_save_final")):
                t, b = split_recipe_content(edited_text)
                save_recipe_to_db(t, edited_text, rating=rating_opts.index(r_sel), source="User")
                st.success(get_txt("save_success"))
                st.session_state.upload_preview = ""; time.sleep(1); st.rerun()

# --- MAIN ---
st.markdown(f'<div class="main-title"><span class="brand">Food & Family</span><span class="subtitle">{get_txt("title_sub")}</span></div>', unsafe_allow_html=True)

db_profile = get_profile(user_id)
pref = db_profile.get("preferences", {})
is_new = not pref

if is_new:
    st.info(get_txt("welcome"))
    with st.form("setup"):
        p_name = st.text_input("Name", "Chefkoch")
        c1,c2,c3 = st.columns(3)
        p_erw = c1.number_input(get_txt("lbl_adults"),1,10,2)
        p_k3 = c2.number_input("Kids > 3",0,10,0)
        p_ku3 = c3.number_input("Kids < 3",0,10,0)
        p_dia = st.multiselect("Diet", ["Alles","Vegetarisch"], default=["Alles"])
        p_vor = st.text_area("Pantry", "...")
        if st.form_submit_button("Save"):
            d = {"username": p_name, "erwachsene":p_erw,"kinder_ueber3":p_k3,"kinder_unter3":p_ku3,"diaet":p_dia,"vorrat":p_vor}
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
            current_name = pref.get("username"); 
            if not current_name: current_name = "Chefkoch"
            p_name = st.text_input(get_txt("lbl_name"), current_name)
            
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
                d = {"username": p_name, "erwachsene":p_erw,"kinder_ueber3":p_k3,"kinder_unter3":p_ku3,"diaet":p_dia,"vermeiden_select":p_verm_sel,"vermeiden_text":p_verm_txt,"geraete":p_geraete,"ziele":p_ziele,"shops":p_shops,"vorrat":p_vor}
                save_profile_db(user_id, d); st.success(get_txt("save_success")); st.rerun()

    empty = len(st.session_state.recipe_slots) == 0
    with st.expander(f"📝 {get_txt('header_plan')} {sel_week_opt}", expanded=empty):
        c_i1, c_i2 = st.columns(2)
        
        # --- COMMUNITY & OWN RECIPES SELECTION ---
        all_recs = get_all_recipes_for_selection()
        # Mix aus "Titel (Rating Sterne)"
        # Trennen in "Eigene" und "Trends" ist hier im Dropdown schwierig, wir machen eine Liste
        # Mit einem kleinen Trick: Wir hängen 🔥 an, wenn es oft gekocht wurde
        select_options = []
        rec_map = {} # Titel -> Content Mapping
        
        # Trends analysieren für Badges
        trend_titles = [t['title'] for t in trends]
        
        for r in all_recs:
            tit = r['title']; rt = r['rating']
            badge = "🔥 " if tit in trend_titles else "⭐ "
            label = f"{badge}{tit} ({rt}*)"
            select_options.append(label)
            rec_map[label] = {"content": r['content'], "rating": rt}
            
        selected_mix = c_i1.multiselect(get_txt("lbl_recipe_select"), select_options)
        
        slots_needed = max(len(selected_mix), 4)
        d_def = st.session_state.get('days_slider_val', slots_needed)
        days = c_i1.slider(get_txt("lbl_days"), 1, 7, d_def, key="ds")
        if days != d_def: st.session_state.days_slider_val = days
        
        wishes = c_i2.text_area(get_txt("lbl_wishes"))
        
        if not st.session_state.recipe_slots and st.button(get_txt("btn_start_plan"), type="primary"):
            slots = [{'day': i+1, 'content': None, 'locked': False, 'rating': 0} for i in range(days)]
            
            # Fülle Auswahl ein
            for idx, lbl in enumerate(selected_mix):
                if idx < days:
                    dat = rec_map[lbl]
                    slots[idx]['content'] = dat['content']
                    slots[idx]['locked'] = True
                    slots[idx]['rating'] = dat['rating']
            
            st.session_state.recipe_slots = slots
            if len(selected_mix) > 0: st.success(get_txt("msg_inserted"))
            st.rerun()

    # --- GENERATION ---
    if st.session_state.recipe_slots:
        slots = st.session_state.recipe_slots
        if len(slots) < days:
             for i in range(len(slots), days): slots.append({'day': i+1, 'content': None, 'locked': False, 'rating': 0})
        
        to_fill = [i for i, s in enumerate(slots) if s['content'] is None]
        if to_fill:
            with st.spinner(get_txt("spinner_cooking")):
                locked = [s['content'] for s in slots if s['locked'] and s['content']]
                username = pref.get('username')
                if not username: username = "Chefkoch"
                
                p_text = f"Rolle: Food Manager. Kunde: {username}. Profil: {pref.get('erwachsene')} Erw, {pref.get('kinder_ueber3')} Kind>3. Ernährung: {','.join(pref.get('diaet',[]))}. Wünsche: {wishes}. Fixiert: {' '.join(locked)}. AUFGABE: {len(to_fill)} Rezepte. FORMAT: 1. Intro (Sprich den Kunden mit {username} an) -> '---INTRO_ENDE---'. 2. Rezepte getrennt '---TRENNER---'. 3. Titel mit Emoji. 4. Nährwerte (Kcal/E/K/F) am Ende. {get_txt('prompt_lang')}"
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
                    for line in s['content'].split('\n'):
                        if line.strip().startswith(('-','*')): ingredients_only += line.strip() + "\n"
            
            if len(ingredients_only) < 10: ingredients_only = "\n".join([s['content'] for s in st.session_state.recipe_slots if s['content']])

            p = f"Erstelle Einkaufsliste für:\n{ingredients_only}\nVorrat ignorieren: {pref.get('vorrat','')}. Sortiere sinnvoll nach Kategorien. Nutze Emojis für Kategorien (z.B. 🥦 Obst). Kategorien als Markdown-Überschriften (###). Zutaten als Liste mit Bindestrich (-). {get_txt('prompt_lang')}"
            
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
                status.update(label="Fehler", state="error"); st.error("Limit erreicht.")

        if st.session_state.get('generated_list_draft'):
            st.divider(); st.markdown(f'<div class="section-title">{get_txt("header_shopping")}</div>', unsafe_allow_html=True)
            sm = st.toggle(get_txt("toggle_shop"))
            if sm:
                for ln in st.session_state.generated_list_draft.split('\n'):
                    cl = ln.strip()
                    if cl.startswith('###'): st.markdown(f"<div class='shop-header'>{cl.replace('#','').strip()}</div>", unsafe_allow_html=True)
                    elif cl.startswith(('-','*')):
                        it = cl.replace('-','').replace('*','').strip()
                        ch = st.session_state.checked_items.get(it, False)
                        c_cb, c_txt = st.columns([0.1, 0.9])
                        if c_cb.checkbox("d", value=ch, key=f"c_{it}", label_visibility="collapsed"):
                            st.session_state.checked_items[it] = True
                            c_txt.markdown(f"~~{it}~~")
                        else: st.session_state.checked_items[it] = False; c_txt.write(it)
            else: st.markdown(st.session_state.generated_list_draft)
            
            if st.button(get_txt("btn_clear")):
                supabase.table("weekly_plans").delete().eq("user_id", user_id).eq("week_key", week_key).execute()
                st.session_state.recipe_slots=[]; st.session_state.generated_list_draft=None; st.rerun()
