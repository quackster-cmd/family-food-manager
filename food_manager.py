import streamlit as st
import google.generativeai as genai
from PIL import Image
import datetime
import time
from supabase import create_client, Client

# --- CONFIGURATION ---
st.set_page_config(page_title="Food & Family Manager", page_icon="🥑", layout="wide")

# --- CSS / DESIGN ---
st.markdown("""
    <style>
    .main-title { text-align: center; padding: 10px; margin-bottom: 20px; }
    .main-title span.brand {
        font-size: 3rem; font-weight: 900;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        display: inline-block;
    }
    .section-title {
        font-size: 2rem; font-weight: 800; margin-top: 30px; margin-bottom: 20px;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        border-bottom: 2px solid rgba(128, 128, 128, 0.2); padding-bottom: 10px;
    }
    .intro-box {
        padding: 15px; background-color: rgba(78, 205, 196, 0.15);
        border-radius: 10px; margin-bottom: 25px; font-style: italic;
        border-left: 5px solid #4ECDC4;
    }
    .recipe-header { font-size: 1.5rem; font-weight: 700; margin-bottom: 0px; }
    .kw-title { font-size: 1.8rem; font-weight: 800; margin-bottom: 15px; color: #4ECDC4; }
    </style>
    """, unsafe_allow_html=True)

# --- SETUP SUPABASE & GOOGLE ---
try:
    # Load secrets
    if "supabase" in st.secrets and "GOOGLE_API_KEY" in st.secrets:
        SUPABASE_URL = st.secrets["supabase"]["url"]
        SUPABASE_KEY = st.secrets["supabase"]["key"]
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 Secrets missing! Please add [supabase] url/key and GOOGLE_API_KEY to secrets.toml")
        st.stop()
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

# --- HELPER FUNCTIONS ---
def split_recipe_content(content):
    if not content: return "Loading...", ""
    lines = content.split('\n')
    title = lines[0].replace('#', '').strip() 
    body = "\n".join(lines[1:])
    return title, body

def get_profile(user_id):
    # Fetch profile from DB
    response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    if response.data: return response.data[0]
    return {}

def save_profile_db(user_id, data):
    # Check if exists, then upsert
    existing = get_profile(user_id)
    payload = {"user_id": user_id, "preferences": data, "pantry": data.get("vorrat", "")}
    if existing: payload["id"] = existing["id"]
    supabase.table("profiles").upsert(payload).execute()

def get_week_plan_db(user_id, week_key):
    response = supabase.table("weekly_plans").select("*").eq("user_id", user_id).eq("week_key", week_key).execute()
    if response.data: return response.data[0]
    return None

def save_week_plan_db(user_id, week_key, plan_data):
    # plan_data needs to be serialized for DB (simplified here, storing JSON in columns)
    # Ideally, we map to columns. For now, we store text blobs or JSONB.
    # Note: Ensure your Supabase 'weekly_plans' table has a 'plan_data' jsonb column OR map fields.
    # We will use 'shopping_list' and 'intro_text' columns, and store recipes as JSON in a new column or simple text workaround.
    # Let's assume we added a 'full_plan_json' column to weekly_plans for simplicity in migration, 
    # OR we follow the schema: shopping_list text, intro_text text. The recipes need a home.
    # FIX: For v6.0, let's assume we store the whole state in a JSONB column 'data' in weekly_plans.
    # (You might need to add `data jsonb` to your weekly_plans table in Supabase SQL Editor: `alter table weekly_plans add column data jsonb;`)
    
    existing = get_week_plan_db(user_id, week_key)
    payload = {
        "user_id": user_id, 
        "week_key": week_key, 
        "shopping_list": plan_data.get('shopping_list'), 
        "intro_text": plan_data.get('intro'),
        "recipe_ids": [] # Placeholder if we don't link IDs yet
    }
    
    # Store the complex recipe list in a 'data' column (JSONB)
    # Ensure you ran: alter table weekly_plans add column if not exists plan_data jsonb;
    payload['plan_data'] = plan_data 
    
    if existing: payload["id"] = existing["id"]
    supabase.table("weekly_plans").upsert(payload).execute()

# --- AUTHENTICATION ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.markdown('<div class="main-title"><span class="brand">Food & Family</span></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In"):
            try:
                auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = auth_resp.user
                st.rerun()
            except Exception as e: st.error(f"Login failed: {e}")
            
    with tab2:
        su_email = st.text_input("Email", key="su_email")
        su_pass = st.text_input("Password", type="password", key="su_pass")
        if st.button("Sign Up"):
            try:
                auth_resp = supabase.auth.sign_up({"email": su_email, "password": su_pass})
                st.success("Account created! Check your email to confirm.")
            except Exception as e: st.error(f"Error: {e}")
    
    st.stop() # Stop here if not logged in

# --- APP LOGIC (LOGGED IN) ---
user_id = st.session_state.user.id
user_email = st.session_state.user.email

# Sidebar
with st.sidebar:
    st.write(f"👤 {user_email}")
    if st.button("Log Out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.divider()
    st.subheader("📅 Planning")
    today = datetime.date.today(); year, week, _ = today.isocalendar()
    w1_label = f"KW {week} (Current)"; w2_label = f"KW {week + 1} (Next)"
    if 'selected_week_opt' not in st.session_state: st.session_state.selected_week_opt = w1_label
    selected_week_opt = st.radio("Select Week:", [w1_label, w2_label])
    
    sel_week_num = week if "Current" in selected_week_opt else week + 1
    sel_year = year
    if sel_week_num > 52: sel_week_num = 1; sel_year += 1
    week_key = f"{sel_year}-W{sel_week_num}"
    
    # State Management for Data
    if 'current_week_key' not in st.session_state: st.session_state.current_week_key = ""
    if st.session_state.current_week_key != week_key:
        st.session_state.recipe_slots = []
        st.session_state.intro_text = ""
        st.session_state.generated_list_draft = None
        st.session_state.current_week_key = week_key
        st.rerun()

# Main Area
st.markdown('<div class="main-title"><span class="brand">Food & Family</span></div>', unsafe_allow_html=True)

# 1. Load Profile
db_profile = get_profile(user_id)
profile_data = db_profile.get("preferences", {})
is_new_profile = not profile_data

if is_new_profile:
    st.info("👋 Welcome! Let's set up your family profile.")
    with st.form("profile_setup"):
        c1,c2,c3 = st.columns(3)
        p_erw = c1.number_input("Adults",1,10,2); p_k3 = c2.number_input("Kids>3",0,10,0); p_ku3=c3.number_input("Kids<3",0,10,0)
        p_dia = st.multiselect("Diet", ["Everything","Vegetarian","Vegan"], default=["Everything"])
        p_vor = st.text_area("Pantry Staples", "Pasta, Rice, Salt, Oil")
        if st.form_submit_button("Save Profile"):
            d = {"erwachsene":p_erw,"kinder_ueber3":p_k3,"kinder_unter3":p_ku3,"diaet":p_dia,"vorrat":p_vor}
            save_profile_db(user_id, d)
            st.rerun()
else:
    # 2. Load Week Plan
    db_plan = get_week_plan_db(user_id, week_key)
    if db_plan and not st.session_state.recipe_slots:
        # Load data from 'plan_data' JSONB column if using that strategy
        loaded_data = db_plan.get('plan_data', {})
        st.session_state.recipe_slots = loaded_data.get('recipes', [])
        st.session_state.intro_text = loaded_data.get('intro', "")
        st.session_state.generated_list_draft = loaded_data.get('shopping_list', "")

    st.markdown(f'<div class="kw-title">Planning for {selected_week_opt}</div>', unsafe_allow_html=True)
    
    # ... (Here we paste the same logic for Generation/Display as before, but saving to DB) ...
    # Simplified Logic Hook for Database Saving:
    
    def save_current_state():
        state_payload = {
            "recipes": st.session_state.recipe_slots,
            "intro": st.session_state.intro_text,
            "shopping_list": st.session_state.generated_list_draft
        }
        save_week_plan_db(user_id, week_key, state_payload)

    # --- UI Logic (Condensed for brevity, same features as v5.1) ---
    if not st.session_state.recipe_slots:
        with st.expander("📝 Options"):
            days = st.slider("Days", 1, 7, 4)
            wishes = st.text_area("Wishes")
            if st.button("🚀 Start"):
                st.session_state.recipe_slots = [{'day': i+1, 'content': None, 'locked': False, 'rating': 0} for i in range(days)]
                st.rerun()
    
    if st.session_state.recipe_slots:
        # Check for empty slots
        slots_to_fill = [i for i, s in enumerate(st.session_state.recipe_slots) if s['content'] is None]
        if slots_to_fill:
            with st.spinner("Cooking up ideas..."):
                # ... GenAI Logic ...
                # Use st.secrets["GOOGLE_API_KEY"] implicitly configured above
                # Assuming prompt logic remains same
                try:
                    prompt = f"Create {len(slots_to_fill)} recipes. Profile: {profile_data}. Wishes: {wishes if 'wishes' in locals() else ''}"
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    res = m.generate_content(prompt)
                    # Fake parser for demo (replace with robust split logic)
                    st.session_state.recipe_slots[slots_to_fill[0]]['content'] = res.text # Simple fill
                    save_current_state()
                    st.rerun()
                except Exception as e: st.error(f"AI Error: {e}")

        # Display Slots
        for i, slot in enumerate(st.session_state.recipe_slots):
            if slot.get('content'):
                st.info(slot['content'][:100] + "...") # Preview
                if st.button(f"Toggle Lock {i}"):
                    slot['locked'] = not slot['locked']
                    save_current_state()
                    st.rerun()

        if st.button("Clear Week"):
            # Delete from DB
            supabase.table("weekly_plans").delete().eq("user_id", user_id).eq("week_key", week_key).execute()
            st.session_state.recipe_slots = []
            st.rerun()
