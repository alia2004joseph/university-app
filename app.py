"""
app.py — Smart University App entry point.
Secure Authentication Gateway:
- Role selection & departments are hidden from unauthenticated visitors.
- High-contrast, executive SaaS styling with clear sign-out controls.
- Seamless, non-redundant navigation.
"""
import streamlit as st

st.set_page_config(
    page_title="Smart University Portal",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="expanded"
)

from database   import SheetDatabaseManager
from database.avatars import render_avatar_html
from cache     import cached_fetch_roster
from ai_engine  import AISortingEngine, AIStudyAssistant, AIRepAssistant, AIAdminAssistant, MasterSuperAdminAI
from student    import render_student_interface
from class_rep  import render_class_rep_interface, YEARS
from Superadmin import render_superadmin_interface
from config     import get_departments

# ── Shared managers ──────────────────────────────────────────────
db        = SheetDatabaseManager()
ai        = AISortingEngine()
ai_study  = AIStudyAssistant()
ai_rep    = AIRepAssistant()
ai_admin  = AIAdminAssistant()
master_ai = MasterSuperAdminAI()

# ── Global Enhanced CSS ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --bg-app: #f8fafc;
    --primary-blue: #2563eb;
    --primary-dark: #0f172a;
    --slate-border: #e2e8f0;
    color-scheme:light;
}

body, .stApp, p, h1, h2, h3, h4, h5, h6, input, textarea, select, button, label {
    font-family: var(--font-main) !important;
    line-height: 1.55;
    word-break: break-word;
    overflow-wrap: anywhere;
}
input, textarea, select, .stTextInput input, .stTextArea textarea, .stSelectbox select div [data-baseweb="select"] {
color:var(--primary-dark) !important;
background-color:#ffffff !important;
-webkit-text-fill-color: var(--primary-dark) !important;
}
label, div[data-testid= "stwidgetlabel"] p, div[data-testid= "stwidgetlabel"] label {
color:var(--primary-dark) !important;
-webkit-text-fill-color: var(--primary-dark) !important;
opacity: 1 !important;
}

#MainMenu, footer { 
    visibility: hidden !important; 
    height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.5rem !important;
}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
}
.stApp {
    background-color: var(--bg-app) !important;
}

.block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1050px !important;
}

/* Polished Scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* Sidebar Base Styling */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #f8fafc;
}

/* Sidebar General Buttons (Clean dark aesthetic) */
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255, 255, 255, 0.06) !important;
    color: #f1f5f9 !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    padding: 0.55rem 0.9rem !important;
    transition: all 0.18s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255, 255, 255, 0.12) !important;
    border-color: rgba(255, 255, 255, 0.28) !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
}

/* Primary Sidebar Nav Item (Active indicator) */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border: 1px solid #60a5fa !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
}

/* Prominent Sign Out Button */
.logout-btn-container .stButton > button,
[data-testid="stSidebar"] button[key*="logout"],
[data-testid="stSidebar"] button[key*="sign_out"] {
    background: #dc2626 !important;
    color: #ffffff !important;
    border: 1px solid #ef4444 !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 6px rgba(220, 38, 38, 0.3) !important;
}
.logout-btn-container .stButton > button:hover,
[data-testid="stSidebar"] button[key*="logout"]:hover,
[data-testid="stSidebar"] button[key*="sign_out"]:hover {
    background: #b91c1c !important;
    border-color: #f87171 !important;
    box-shadow: 0 4px 10px rgba(220, 38, 38, 0.5) !important;
}

/* Modern Input Controls in Main App */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    border-radius: 10px !important;
    border: 1px solid #cbd5e1 !important;
    background-color: #ffffff !important;
    color: #0f172a !important;
    font-size: 0.92rem !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}

/* Refined Main Page Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid #cbd5e1 !important;
    background-color: #ffffff !important;
    color: #1e293b !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
}
.stButton > button:hover {
    border-color: #94a3b8 !important;
    background-color: #f8fafc !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 12px rgba(37, 99, 235, 0.3) !important;
    transform: translateY(-1px) !important;
}

/* Segmented Dark Slate Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #ffffff !important;
    border-radius: 12px !important;
    padding: 4px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
    flex-wrap: wrap !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
    background: transparent !important;
    border: none !important;
    transition: all 0.15s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #0f172a !important;
    background: #f1f5f9 !important;
}
.stTabs [aria-selected="true"] {
    background: #0f172a !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    opacity: 1 !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* Modern Header Card */
.app-header-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #1e40af 100%);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    color: white;
    box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.08);
    position: relative;
    overflow: hidden;
}
.app-header-card::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 250px;
    height: 250px;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, rgba(0,0,0,0) 70%);
    pointer-events: none;
}
.app-header-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #93c5fd;
    margin-bottom: 8px;
}

/* User Card in Sidebar */
.user-sidebar-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 14px;

}
div[data-testid="stAlert"] p, div[data-testid="stAlert"] div{
color: var(--primary-dark) !important;
-webkit-text-fill-color: var(--primary-dark) !important;
opacity: 1 !important;

div[data-basweb="tab"]{
overflow-x: auto !important;
-webkit-overflow-scrolling: touch ;
scrollbar-width: thin;}

div[data-basweb="tab"]{
font-size: 0.85rem !important;
padding: 8px 10px !important;
white-space: nowrap !important;
}





</style>
""", unsafe_allow_html=True)

# ── Session State Check ───────────────────────────────────────────
student_id = st.session_state.get("student_logged_in")
rep_logged = st.session_state.get("rep_logged_in", False)
admin_logged = st.session_state.get("admin_logged_in", False)

is_authenticated = bool(student_id or rep_logged or admin_logged)

# Fetch roster for profile lookup
df_profiles = cached_fetch_roster(dept="ALL", year="ALL")

# ── Global Logout Handler ────────────────────────────────────────
def handle_logout():
    clear_keys = [
        "student_logged_in", "rep_logged_in", "admin_logged_in",
        "rep_dept", "rep_year", "rep_name", "rep_reg", "rep_avatar",
        "student_screen", "rep_screen", "admin_screen",
        "show_reg_form", "show_forgot_pin", "show_set_pin", "pending_reg",
        "read_announcements", "open_expanders", "show_ai_tab", "ai_chat_history",
        "ai_pdf_text", "ai_selected_file", "ai_summary_shown", "ai_draft",
        "admin_draft", "sheets_list", "config_data", "funcs_list", "slot_cfg_list"
    ]
    for k in clear_keys:
        if k in st.session_state:
            del st.session_state[k]
    for k in [k for k in st.session_state if k.startswith("ai_last_request_")]:
        del st.session_state[k]
    st.rerun()

# ── Sidebar Rendering ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:14px 0 10px 0;">
        <div style="font-size:2rem;line-height:1;">🏛️</div>
        <div style="font-size:1.1rem;font-weight:800;color:#f8fafc;margin-top:6px;letter-spacing:-0.3px;">Smart University</div>
        <div style="font-size:0.72rem;color:#94a3b8;margin-top:2px;font-weight:500;">Academic Portal · 2025/2026</div>
    </div>
    <hr style="border-color:rgba(255,255,255,0.08);margin:6px 0 14px 0;">
    """, unsafe_allow_html=True)

    if is_authenticated:
        # Show Logged-in User Profile in Sidebar
        if student_id and not df_profiles.empty:
            s_row = df_profiles[df_profiles["Reg Number"] == student_id]
            s_name = s_row.iloc[0]["Student Name"] if not s_row.empty else "Student"
            s_dept = s_row.iloc[0].get("Department", "") if not s_row.empty else ""
            s_year = s_row.iloc[0].get("Year", "") if not s_row.empty else ""
            s_avatar = s_row.iloc[0].get("Avatar", "") if not s_row.empty else ""
            av_html = render_avatar_html(s_avatar, s_name, size=44, color="#60a5fa", light="rgba(96,165,250,0.15)")
            
            st.markdown(f"""
            <div class="user-sidebar-card">
                <div style="display:flex;align-items:center;gap:12px;">
                    {av_html}
                    <div style="flex:1;min-width:0;">
                        <div style="font-size:0.88rem;font-weight:700;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{s_name}</div>
                        <div style="font-size:0.72rem;color:#93c5fd;font-weight:600;margin-top:1px;">🎓 Student</div>
                        <div style="font-size:0.70rem;color:#94a3b8;margin-top:2px;">{student_id}</div>
                    </div>
                </div>
                <div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.08);font-size:0.72rem;color:#cbd5e1;">
                    Dept: <b>{s_dept}</b> · Year: <b>{s_year}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        elif rep_logged:
            r_name = st.session_state.get("rep_name", "Class Representative")
            r_dept = st.session_state.get("rep_dept", "")
            r_year = st.session_state.get("rep_year", "")
            r_avatar = st.session_state.get("rep_avatar", "")
            if not r_avatar:
                try:
                    reps_data = db.fetch_reps()
                    for r in reps_data:
                        if r.get("department_code") == r_dept and str(r.get("year")) == str(r_year):
                            r_avatar = r.get("avatar_url", "")
                            st.session_state.rep_avatar = r_avatar
                            break
                except Exception:
                    pass
            av_html = render_avatar_html(r_avatar, r_name, size=44, color="#34d399", light="rgba(52,211,153,0.15)")
            
            st.markdown(f"""
            <div class="user-sidebar-card">
                <div style="display:flex;align-items:center;gap:12px;">
                    {av_html}
                    <div style="flex:1;min-width:0;">
                        <div style="font-size:0.88rem;font-weight:700;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{r_name}</div>
                        <div style="font-size:0.72rem;color:#6ee7b7;font-weight:600;margin-top:1px;">📋 Class Representative</div>
                    </div>
                </div>
                <div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.08);font-size:0.72rem;color:#cbd5e1;">
                    Dept: <b>{r_dept}</b> · Year: <b>{r_year}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        elif admin_logged:
            a_avatar = ""
            try:
                a_avatar = db.get_admin_avatar()
            except Exception:
                pass
            av_html = render_avatar_html(a_avatar, "Super Admin", size=44, color="#f59e0b", light="rgba(245,158,11,0.15)")
            
            st.markdown(f"""
            <div class="user-sidebar-card">
                <div style="display:flex;align-items:center;gap:12px;">
                    {av_html}
                    <div style="flex:1;min-width:0;">
                        <div style="font-size:0.88rem;font-weight:700;color:#f8fafc;">University Super Admin</div>
                        <div style="font-size:0.72rem;color:#fbbf24;font-weight:600;margin-top:1px;">⚡ Executive Console</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # High-visibility Log Out Button
        st.markdown('<div class="logout-btn-container">', unsafe_allow_html=True)
        if st.button("🚪 Sign Out", use_container_width=True, key="app_sign_out_btn"):
            handle_logout()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color:rgba(255,255,255,0.08);margin:14px 0 10px 0;">', unsafe_allow_html=True)

    else:
        # Unauthenticated Sidebar (Clean & Secure - NO departments list)
        st.markdown("""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:14px;margin-bottom:14px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <span style="font-size:1.1rem;">🔒</span>
                <span style="font-size:0.85rem;font-weight:700;color:#f8fafc;">Secure Gateway</span>
            </div>
            <div style="font-size:0.78rem;color:#94a3b8;line-height:1.45;">
                Authorized portal for registered students, appointed class representatives, and faculty administration.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:0.68rem;color:#64748b;text-align:center;line-height:1.4;margin-top:8px;">
        Smart University System v2.5<br><span style="color:#475569;">Academic Operations Hub</span>
    </div>
    """, unsafe_allow_html=True)

# ── Main Content Router ─────────────────────────────────────────
if student_id:
    # 🎓 STUDENT DASHBOARD
    render_student_interface(db, ai_study, df_profiles)

elif rep_logged:
    # 📋 CLASS REP DASHBOARD
    render_class_rep_interface(db, ai, ai_rep)

elif admin_logged:
    # ⚡ SUPER ADMIN CONSOLE
    render_superadmin_interface(db, ai_admin, master_ai)

else:
    # 🔒 UNIFIED AUTHENTICATION GATEWAY
    st.markdown("""
    <div class="app-header-card">
        <div class="app-header-badge">
            <span>🏛️</span> Academic Network Access
        </div>
        <div style="font-size:1.65rem;font-weight:800;margin-bottom:4px;letter-spacing:-0.5px;line-height:1.2;">
            Smart University Portal
        </div>
        <div style="font-size:0.86rem;color:#cbd5e1;font-weight:400;">
            Centralized Academic Portal · Single Sign-On Access Control
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_student, tab_rep, tab_admin = st.tabs([
        "🎓 Student Portal",
        "📋 Class Representative",
        "⚡ University Admin"
    ])

    # 1. Student Sign In / Registration
    with tab_student:
        render_student_interface(db, ai_study, df_profiles)

    # 2. Class Rep Sign In
    with tab_rep:
        st.markdown("""
        <div style="font-size:1.05rem;font-weight:700;color:#1e293b;margin-bottom:6px;">
            📋 Class Representative Authentication
        </div>
        <div style="font-size:0.82rem;color:#64748b;margin-bottom:16px;">
            Sign in with your appointed representative credentials to access your course noticeboard, timetable publisher, and student feedback console.
        </div>
        """, unsafe_allow_html=True)
        
        rep_identifier = st.text_input(
            "Representative ID or Email",
            key="gate_rep_identifier",
            placeholder="e.g. Reg Number (25/U/0000/PS) or rep@university.ac.ug"
        )
        rep_pw = st.text_input(
            "Representative Password",
            type="password",
            key="gate_rep_pw",
            placeholder="Enter your representative access key"
        )
        
        if st.button("Sign In as Class Rep", use_container_width=True, type="primary", key="gate_rep_submit"):
            if not rep_identifier or not rep_pw:
                st.warning("Please enter both your Representative ID / Email and password.")
            else:
                with st.spinner("Authenticating representative..."):
                    res = db.authenticate_rep(rep_identifier, rep_pw)
                if res.get("status") == "success":
                    st.session_state.rep_logged_in = True
                    st.session_state.rep_dept = res.get("dept", "MEC")
                    st.session_state.rep_year = res.get("year", "Year 1")
                    st.session_state.rep_name = res.get("rep_name", "Class Rep")
                    st.session_state.rep_reg = res.get("rep_reg", "")
                    st.session_state.rep_email = res.get("email", "")
                    st.session_state.rep_avatar = res.get("avatar_url", "")
                    st.success(f"Welcome, {res.get('rep_name')}! Loading dashboard...")
                    st.rerun()
                else:
                    msg = res.get("message", "Invalid credentials")
                    st.error(f"⚠️ {msg}")

    # 3. Super Admin Sign In
    with tab_admin:
        st.markdown("""
        <div style="font-size:1.05rem;font-weight:700;color:#1e293b;margin-bottom:6px;">
            ⚡ University Administrative Console
        </div>
        <div style="font-size:0.82rem;color:#64748b;margin-bottom:16px;">
            Restricted university-wide management and class representative provisioning portal.
        </div>
        """, unsafe_allow_html=True)
        
        admin_pw = st.text_input("Super Admin Password", type="password", key="gate_admin_pw", placeholder="Enter administrative password")
        
        if st.button("Unlock Admin Console", use_container_width=True, type="primary", key="gate_admin_submit"):
            correct_pw = st.secrets.get("SUPER_ADMIN_PASSWORD", "")
            if not correct_pw:
                st.error("No admin password configured in environment secrets.")
            elif admin_pw == correct_pw:
                st.session_state.admin_logged_in = True
                st.success("Admin credentials verified! Loading console...")
                st.rerun()
            else:
                st.error("⚠️ Invalid administrative password.")
