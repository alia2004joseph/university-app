"""
app.py — Smart University App entry point.
Roles: Student | Class Rep | Super Admin
"""
import streamlit as st

st.set_page_config(
    page_title="Smart University Portal",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="expanded"
)

from database   import SheetDatabaseManager
from cache     import cached_fetch_roster
from ai_engine  import AISortingEngine, AIStudyAssistant, AIRepAssistant, AIAdminAssistant, MasterSuperAdminAI
from student    import render_student_interface
from class_rep  import render_class_rep_interface
from Superadmin import render_superadmin_interface
from config     import get_departments

#  Shared managers 
db       = SheetDatabaseManager()
ai       = AISortingEngine()
ai_study = AIStudyAssistant()
ai_rep   = AIRepAssistant()
ai_admin = AIAdminAssistant()
master_ai = MasterSuperAdminAI()

#  Global Enhanced CSS (Executive SaaS Typography & Widget Styling)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --bg-app: #f8fafc;
    --primary-blue: #2563eb;
    --primary-dark: #0f172a;
    --slate-border: #e2e8f0;
}

html, body, [class*="css"], .stMarkdown, .stText, p, span, div {
    font-family: var(--font-main) !important;
}

#MainMenu, footer { visibility: hidden !important; }

.stApp {
    background-color: var(--bg-app) !important;
}

/* Polished Scrollbars */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

/* Sidebar Custom Styling */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
[data-testid="stSidebar"] * {
    color: #f8fafc !important;
}
[data-testid="stSidebar"] .stRadio > div {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 6px;
    gap: 4px;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 8px 14px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255, 255, 255, 0.08) !important;
}

/* Modern Input Controls */
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

/* Refined Buttons */
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

/* Clean Alert Boxes */
.stAlert {
    border-radius: 12px !important;
    border: 1px solid transparent !important;
    padding: 12px 16px !important;
}

/* Clean Expanders */
.streamlit-expanderHeader {
    border-radius: 10px !important;
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    font-weight: 600 !important;
    color: #1e293b !important;
    padding: 10px 14px !important;
}
.streamlit-expanderContent {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
    padding: 16px !important;
}

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
</style>
""", unsafe_allow_html=True)

#  Session defaults 
if "role" not in st.session_state:
    st.session_state.role = "Student"

#  Sidebar 
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 12px 0;">
        <div style="font-size:2.2rem;line-height:1;">🏛️</div>
        <div style="font-size:1.15rem;font-weight:800;color:#f8fafc;margin-top:8px;letter-spacing:-0.3px;">Smart University</div>
        <div style="font-size:0.75rem;color:#94a3b8;margin-top:2px;font-weight:500;">Academic Portal · 2025/2026</div>
    </div>
    <hr style="border-color:rgba(255,255,255,0.08);margin:8px 0 16px 0;">
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.68rem;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;font-weight:700;margin-bottom:8px;">PORTAL ROLE</div>', unsafe_allow_html=True)
    st.session_state.role = st.radio(
        "Role", ["Student", "Class Rep", "Super Admin"],
        label_visibility="collapsed"
    )

    role_info = {
        "Student":     ("🎓", "Student Portal", "Access class announcements, lecture materials, weekly timetable, rep feedback, and AI study tutor."),
        "Class Rep":   ("📋", "Class Rep Dashboard", "Manage class roster, publish notices, distribute course files, manage timetables, and answer inquiries."),
        "Super Admin": ("⚡", "Super Admin Console", "Oversee university departments, provision class representative accounts, broadcast notices, and inspect AI analytics."),
    }
    icon, title, desc = role_info[st.session_state.role]

    st.markdown(f"""
    <hr style="border-color:rgba(255,255,255,0.08);margin:16px 0;">
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:14px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:1.1rem;">{icon}</span>
            <span style="font-size:0.85rem;font-weight:700;color:#f8fafc;">{title}</span>
        </div>
        <div style="font-size:0.78rem;color:#94a3b8;line-height:1.45;">{desc}</div>
    </div>
    <hr style="border-color:rgba(255,255,255,0.08);margin:16px 0 12px 0;">
    <div style="font-size:0.68rem;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;font-weight:700;margin-bottom:10px;">DEPARTMENTS</div>
    """, unsafe_allow_html=True)

    for code, info in get_departments().items():
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;padding:4px 6px;border-radius:6px;">
            <div style="width:9px;height:9px;border-radius:50%;background:{info['color']};flex-shrink:0;box-shadow:0 0 6px {info['color']}88;"></div>
            <div style="font-size:0.78rem;color:#cbd5e1;font-weight:500;">{info['name']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <hr style="border-color:rgba(255,255,255,0.08);margin:16px 0 10px 0;">
    <div style="font-size:0.68rem;color:#64748b;text-align:center;line-height:1.4;">
        Smart University System v2.5<br><span style="color:#475569;">Engineered for Academic Excellence</span>
    </div>
    """, unsafe_allow_html=True)

#  Page Header 
st.markdown("""
<div class="app-header-card">
    <div class="app-header-badge">
        <span>🏛️</span> University Academic Network
    </div>
    <div style="font-size:1.65rem;font-weight:800;margin-bottom:4px;letter-spacing:-0.5px;line-height:1.2;">
        Smart University Portal
    </div>
    <div style="font-size:0.86rem;color:#cbd5e1;font-weight:400;">
        Centralized Class Management · Real-time Notices · Collaborative Study Hub
    </div>
</div>
""", unsafe_allow_html=True)

#  Fetch full roster for student login lookup (CACHED for performance)
df_profiles = cached_fetch_roster(dept="ALL", year="ALL")

#  Route by role 
if st.session_state.role == "Student":
    render_student_interface(db, ai_study, df_profiles)
elif st.session_state.role == "Class Rep":
    render_class_rep_interface(db, ai, ai_rep)
elif st.session_state.role == "Super Admin":
    render_superadmin_interface(db, ai_admin, master_ai)
