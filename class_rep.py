"""
class_rep.py — Class Representative Dashboard with Mobile-First Design.
"""
import streamlit as st
import re
import json as _json
import pandas as pd
from database import SheetDatabaseManager
from database.avatars import render_avatar_html
from ai_engine import AISortingEngine, AIRepAssistant
from config import get_departments, YEARS, dept_color, dept_light, dept_name, dept_courses
from utils.mobile import is_mobile, get_view_mode_toggle


def inject_rep_css(primary: str, light: str):
    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, .stApp {{
        color-scheme: light !important;
        background-color: #f8fafc !important;
        color: #0f172a;
    }}
    
    body, .stApp, p, h1, h2, h3, h4, h5, h6, label {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        line-height: 1.55;
    }}
    
    input, textarea, select {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }}
    
    /* Password Toggle and Input Enhancer */
    div[data-baseweb="input"] button,
    .stTextInput button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 8px !important;
        color: #64748b !important;
        min-width: auto !important;
    }}
    
    #MainMenu, footer {{ visibility: hidden !important; }}
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 2.5rem !important;
    }}
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {{
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
    }}
    .stApp {{ background-color: #f8fafc !important; }}
    
    /* Rep Banner with Dark Executive Contrast */
    .rep-banner div, .rep-banner p, .rep-banner span, .rep-banner h2 {{
        color: #ffffff !important;
    }}
    .rep-banner {{
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, {primary} 100%);
        border-radius: 16px;
        padding: 22px 24px;
        margin-bottom: 18px;
        color: #ffffff;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.12);
        position: relative;
        overflow: hidden;
    }}
    .rep-banner h2 {{
        font-size: 1.45rem;
        font-weight: 800;
        margin: 0 0 4px 0;
        color: #ffffff !important;
        letter-spacing: -0.3px;
    }}
    .rep-banner p {{
        color: #cbd5e1 !important;
        margin: 2px 0 0 0;
        font-size: 0.90rem;
    }}
    
    /* Badges & Chips */
    .rep-badge-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 10px;
    }}
    .rep-badge {{
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.14);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.74rem;
        font-weight: 600;
        color: white;
    }}
    
    .scope-badge {{
        background: {light};
        color: {primary};
        border: 1px solid {primary}33;
        border-radius: 10px;
        padding: 6px 14px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        margin-bottom: 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }}
    
    /* Feedback Cards */
    .fb-card {{
        background: white;
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 10px;
        border: 1px solid #e2e8f0;
        border-left: 4px solid {primary};
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }}
    .fb-card:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }}
    .fb-card.reviewed {{
        border-left-color: #16a34a;
        background: #fcfdfc;
    }}
    
    .pro-divider {{
        height: 1px;
        background: #e2e8f0;
        margin: 18px 0;
    }}
    
    /* Horizontal Touch-Friendly Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: white;
        border-radius: 12px;
        padding: 5px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
        scrollbar-width: none;
    }}
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {{
        display: none;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 600;
        font-size: 0.82rem;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 1 !important;
        border: none;
        background: transparent;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
        min-width: fit-content !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
        transition: all 0.15s ease;
    }}
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] div {{
        white-space: nowrap !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: {primary} !important;
        color: white !important;
        -webkit-text-fill-color: white !important;
        opacity: 1 !important;
        box-shadow: 0 2px 8px {primary}44;
    }}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {{
        display: none !important;
    }}

    /* Horizontal Radio Scroll & Card Styling for AI Tools */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        gap: 8px !important;
        padding: 4px 2px 10px 2px !important;
        scrollbar-width: none !important;
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"]::-webkit-scrollbar {{
        display: none !important;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"] {{
        flex-shrink: 0 !important;
        white-space: nowrap !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 7px 12px !important;
        margin-right: 0 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        transition: all 0.15s ease !important;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {{
        border-color: #cbd5e1 !important;
        background: #f8fafc !important;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"] p {{
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
        margin: 0 !important;
    }}
    
    /* ─────────────────────────────────────────────
       📱 MOBILE PHONE OPTIMIZATIONS (<768px)
    ───────────────────────────────────────────── */
    @media (max-width: 768px) {{
        .block-container {{
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-top: 1rem !important;
        }}
        .rep-banner {{
            padding: 16px 14px !important;
            border-radius: 12px !important;
        }}
        .rep-banner h2 {{
            font-size: 1.25rem !important;
        }}
        .stButton > button {{
            width: 100% !important;
            min-height: 42px !important;
            font-size: 0.88rem !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 0.76rem !important;
            padding: 6px 10px !important;
        }}
        .fb-card {{
            padding: 12px 14px !important;
        }}
        .scope-badge {{
            font-size: 0.74rem !important;
            padding: 5px 10px !important;
        }}
        /* Stack columns cleanly */
        div[data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 0.6rem !important;
        }}
        div[data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            gap: 0.5rem !important;
        }}
    }}
    """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_rep_roster_mobile(df, total_students):
    """Render class roster as cards for mobile."""
    st.caption(f" Showing {len(df)} of {total_students} students (mobile view)")
    if df.empty:
        st.info("No students found.")
        return
    for _, row in df.iterrows():
        name = row.get("Student Name", "")
        reg = row.get("Reg Number", "")
        course = row.get("Course Code", "")
        group = row.get("Assigned Group", "")
        avatar_url = row.get("Avatar", row.get("avatar_url", ""))
        av_html = render_avatar_html(avatar_url, name, size=38, color="#1a56db", light="#dbeafe")
        st.markdown(f"""
        <div style="background:white;border-radius:10px;padding:12px 14px;margin-bottom:8px;
            border:1px solid #e2e8f7;display:flex;align-items:center;gap:12px;">
            {av_html}
            <div style="flex:1;min-width:0;">
                <div style="font-weight:700;font-size:0.92rem;color:#0f172a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
                <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">
                    {reg} · {course} · Group: {group or 'Unassigned'}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_rep_slot_result_mobile(result, rdisplay, primary, light, is_mob):
    """Render rep slot result with mobile awareness."""
    if not result:
        return
    if result.get("status") == "error":
        st.error(f"{result.get('message','Error')}")
        return
    data = result.get("result", result)
    if rdisplay == "metric":
        if isinstance(data, dict):
            cols = st.columns(min(len(data), 2 if is_mob else 4))
            for ci, (k, v) in enumerate(list(data.items())[:(2 if is_mob else 4)]):
                with cols[ci]:
                    st.metric(k.replace("_", " ").title(), v)
        else:
            st.metric("Result", str(data))
    elif rdisplay == "table":
        if isinstance(data, list) and data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        elif isinstance(data, dict):
            if all(isinstance(v, dict) for v in data.values()):
                rows = [{"key": k, **v} for k, v in data.items()]
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.dataframe(pd.DataFrame([data]), use_container_width=True)
        else:
            st.info(str(data))
    elif rdisplay == "json":
        st.json(data)
    else:
        if isinstance(data, (dict, list)):
            st.json(data)
        else:
            st.success(str(data))


def render_rep_slots(db, r_reg, r_name, r_dept, r_year, primary, light, df_class):
    """Render dynamic feature slots for the class rep dashboard — mobile-friendly."""
    is_mob = is_mobile()
    st.markdown("### Rep Features")
    with st.spinner("Loading features..."):
        slots = db.get_active_slots(r_dept, r_year, "rep")
    if not slots:
        st.info("No additional features configured for reps yet. Ask your Super Admin to add some.")
        return
    for slot in slots:
        sid = slot.get("slotid", "")
        title = slot.get("title", "Feature")
        icon = slot.get("icon", "•")
        stype = slot.get("type", "button")
        rdisplay = slot.get("resultdisplay", "text")
        func = slot.get("function", slot.get("func", ""))
        desc = slot.get("description", "")
        fields_raw = slot.get("fields", "[]")
        try:
            fields = _json.loads(fields_raw) if fields_raw else []
        except:
            fields = []
        padding = "14px 18px" if is_mob else "16px 20px"
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:{padding};
            margin-bottom:12px;border:1px solid #e2e8f7;border-left:4px solid {primary};">
            <div style="font-size:{'0.95rem' if is_mob else '1.05rem'};font-weight:800;color:#1e293b;">
                {icon} {title}
            </div>
            {"<div style='font-size:0.78rem;color:#94a3b8;margin-top:3px;'>" + desc + "</div>" if desc else ""}
        </div>
        """, unsafe_allow_html=True)
        result_key = f"rep_slot_result_{sid}"
        base_params = {
            "reg": r_reg,
            "name": r_name,
            "dept": r_dept,
            "year": r_year,
        }
        if stype == "button":
            if st.button(f"{icon} {title}", key=f"rslot_btn_{sid}", use_container_width=True):
                with st.spinner("Running..."):
                    r = db.call_function(func, base_params)
                st.session_state[result_key] = r
            _render_rep_slot_result_mobile(st.session_state.get(result_key), rdisplay, primary, light, is_mob)
        elif stype == "form":
            with st.form(f"rslot_form_{sid}", clear_on_submit=True):
                params = base_params.copy()
                valid = True
                for field in fields:
                    fname = field.get("name", "")
                    flabel = field.get("label", fname)
                    ftype = field.get("type", "text")
                    fopts = field.get("options", "").split(",") if field.get("options") else []
                    if ftype == "text":
                        val = st.text_input(flabel, key=f"rsf_{sid}_{fname}")
                    elif ftype == "textarea":
                        val = st.text_area(flabel, key=f"rsf_{sid}_{fname}", height=100 if is_mob else 80)
                    elif ftype == "number":
                        val = st.number_input(flabel, key=f"rsf_{sid}_{fname}")
                    elif ftype == "date":
                        val = str(st.date_input(flabel, key=f"rsf_{sid}_{fname}"))
                    elif ftype == "dropdown":
                        if fname in ("student", "reg", "student_reg"):
                            roster_opts = list(df_class["Student Name"].values) if not df_class.empty else []
                            val = st.selectbox(flabel, roster_opts, key=f"rsf_{sid}_{fname}")
                            if not df_class.empty and val:
                                reg_row = df_class[df_class["Student Name"] == val]
                                if not reg_row.empty:
                                    params["student_reg"] = reg_row.iloc[0]["Reg Number"]
                        else:
                            val = st.selectbox(flabel, fopts if fopts else ["Option 1"],
                                               key=f"rsf_{sid}_{fname}")
                    elif ftype == "checkbox":
                        val = str(st.checkbox(flabel, key=f"rsf_{sid}_{fname}"))
                    else:
                        val = st.text_input(flabel, key=f"rsf_{sid}_{fname}")
                    params[fname] = val
                if st.form_submit_button("Submit", use_container_width=True):
                    for field in fields:
                        if field.get("required") and not params.get(field["name"], ""):
                            st.error(f"{field.get('label', field['name'])} is required.")
                            valid = False
                            break
                    if valid:
                        with st.spinner("Submitting..."):
                            r = db.call_function(func, params)
                        st.session_state[result_key] = r
            _render_rep_slot_result_mobile(st.session_state.get(result_key), rdisplay, primary, light, is_mob)
        elif stype in ("display", "table"):
            col_l, col_r = st.columns([3, 1])
            with col_l:
                if st.button(f"Load {title}", key=f"rslot_load_{sid}", use_container_width=True):
                    with st.spinner("Loading..."):
                        r = db.call_function(func, base_params)
                    st.session_state[result_key] = r
            with col_r:
                if rdisplay == "table" and st.session_state.get(result_key):
                    res = st.session_state[result_key].get("result", {})
                    if isinstance(res, list) and res:
                        csv = pd.DataFrame(res).to_csv(index=False)
                        st.download_button(
                            "CSV", data=csv,
                            file_name=f"{sid}_{r_dept}_{r_year}.csv",
                            mime="text/csv",
                            key=f"rslot_csv_{sid}",
                            use_container_width=True
                        )
            _render_rep_slot_result_mobile(st.session_state.get(result_key), rdisplay, primary, light, is_mob)
        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)


def render_class_rep_interface(
    db: SheetDatabaseManager,
    ai: AISortingEngine,
    ai_rep: AIRepAssistant,
):
    is_mob = is_mobile()
    # Session init 
    defaults = {
        "rep_logged_in":       False,
        "rep_dept":            None,
        "rep_year":            None,
        "rep_name":            "",
        "rep_reg":             "",
        "rep_ai_draft":        "",
        "rep_ai_reply":        "",
        "rep_confirm_delete":  None,
        "rep_show_change_pw":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.markdown("""
<div style="margin:0 0 10px 0;padding-bottom:10px;border-bottom:1px solid #e2e8f7;">
    <div style="font-size:0.65rem;letter-spacing:2px;text-transform:uppercase;
        color:#94a3b8;font-weight:600;margin-bottom:2px;">Welcome to</div>
    <div style="font-size:1.2rem;font-weight:800;color:#1e293b;">
        Class Rep Dashboard
    </div>
</div>
""", unsafe_allow_html=True)

    # 
    # LOGIN
    # 
    if not st.session_state.rep_logged_in:
        st.markdown("""
<div style="font-size:1rem;font-weight:700;color:#1e293b;margin-bottom:12px;">
    Class Representative Login
</div>
""", unsafe_allow_html=True)
        st.info("Sign in with your appointed representative credentials (ID/Email & Password).")

        rep_identifier = st.text_input(
            "Representative ID or Email",
            key="rep_login_identifier",
            placeholder="e.g. Reg Number (25/U/0000/PS) or rep@university.ac.ug"
        )
        password_input = st.text_input(
            "Password",
            type="password",
            key="rep_login_pw",
            placeholder="Enter your representative access password"
        )

        if st.button("Log In", use_container_width=True, type="primary", key="rep_login_submit_btn"):
            if not rep_identifier or not password_input:
                st.warning("Please enter both your Representative ID / Email and password.")
            else:
                with st.spinner("Verifying credentials..."):
                    result = db.authenticate_rep(rep_identifier, password_input)

                if result.get("status") == "success":
                    st.session_state.rep_logged_in = True
                    st.session_state.rep_dept = result.get("dept", "MEC")
                    st.session_state.rep_year = result.get("year", "Year 1")
                    st.session_state.rep_name = result.get("rep_name", "Class Rep")
                    st.session_state.rep_reg = result.get("rep_reg", "")
                    st.session_state.rep_email = result.get("email", "")
                    st.session_state.rep_avatar = result.get("avatar_url", "")
                    st.rerun()
                else:
                    msg = result.get("message", "Invalid credentials")
                    st.error(f"⚠️ {msg}")
        return

    # Logged in 
    r_dept = st.session_state.rep_dept
    r_year = st.session_state.rep_year
    r_name = st.session_state.rep_name
    r_reg = st.session_state.rep_reg
    primary = dept_color(r_dept)
    light = dept_light(r_dept)
    d_name = dept_name(r_dept)

    inject_rep_css(primary, light)

    st.markdown(f'<div class="scope-badge">{d_name} &nbsp;·&nbsp; {r_year} &nbsp;·&nbsp; {r_name}</div>', unsafe_allow_html=True)

    # Fetch scoped data 
    raw_roster = db.fetch_roster(dept=r_dept, year=r_year)
    df_class = pd.DataFrame(raw_roster) if isinstance(raw_roster, list) else raw_roster
    announcements = db.fetch_announcements(dept=r_dept, year=r_year)
    materials = db.fetch_materials(dept=r_dept, year=r_year)
    feedback_list = db.fetch_feedback(dept=r_dept, year=r_year)
    rep_replies = db.fetch_rep_replies(dept=r_dept, year=r_year)

    r_avatar = st.session_state.get("rep_avatar", "")
    if not r_avatar:
        try:
            reps_data = db.fetch_reps()
            for rp in reps_data:
                if rp.get("dept") == r_dept and rp.get("year") == r_year:
                    r_avatar = rp.get("avatar_url", "") or ""
                    st.session_state.rep_avatar = r_avatar
                    break
        except Exception:
            pass

    rep_avatar_html = render_avatar_html(r_avatar, r_name, size=52, color="white", light="rgba(255,255,255,0.25)")

    total_students = len(df_class) if not df_class.empty else 0
    pending_feedback = sum(1 for f in feedback_list
                           if isinstance(f, list) and len(f) >= 4
                           and str(f[3]).lower() == "pending")
    unread_replies = sum(1 for r in rep_replies
                         if r.get("read_status", "Unread").lower() == "unread")

    # Banner 
    st.markdown(f"""
    <div class="rep-banner">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;">
            {rep_avatar_html}
            <div style="min-width:0;flex:1;">
                <h2 style="margin:0;font-size:1.35rem;font-weight:800;color:white;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{r_name}'s Dashboard</h2>
                <p style="opacity:0.85;margin:2px 0 0 0;font-size:0.84rem;">{d_name} — {r_year}</p>
            </div>
        </div>
        <div class="rep-badge-container">
            <span class="rep-badge">👥 {total_students} Students</span>
            <span class="rep-badge">⏳ {pending_feedback} Pending</span>
            <span class="rep-badge">💬 {unread_replies} Unread Replies</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Rep screen default
    if "rep_screen" not in st.session_state:
        st.session_state.rep_screen = "dashboard"

    # Sidebar Navigation Menu
    with st.sidebar:
        st.markdown('<div style="font-size:0.68rem;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;font-weight:700;margin:12px 0 8px 0;">CLASS REP WORKSPACE</div>', unsafe_allow_html=True)
        nav_options = [
            ("dashboard", "🏠 Dashboard"),
            ("students",  f"👥 Students ({total_students})"),
            ("notices",   "📢 Notices & Files"),
            ("timetable", "📅 Timetable"),
            ("feedback",  f"💬 Feedback ({pending_feedback})" if pending_feedback else "💬 Feedback"),
            ("ai_rep",    "🤖 Rep AI Suite"),
            ("profile",   "👤 Profile & PIN"),
            ("features",  "🧩 Slot Features"),
        ]
        for n_key, n_label in nav_options:
            is_active = (st.session_state.rep_screen == n_key)
            if st.button(n_label, key=f"rep_nav_btn_{n_key}", use_container_width=True, type="primary" if is_active else "secondary"):
                if st.session_state.rep_screen != n_key:
                    st.session_state.rep_screen = n_key
                    st.rerun()

    screen = st.session_state.rep_screen

    # Render Sub-Screen Header if not on Dashboard
    if screen != "dashboard":
        screen_titles = {
            "students":   ("👥", "Students & Groups", f"{total_students} registered students"),
            "notices":    ("📢", "Notices & Materials", "Publish announcements and lecture files"),
            "timetable":  ("📅", "Class Timetable", "Weekly lecture schedule and rooms"),
            "feedback":   ("💬", "Student Inquiries", f"{pending_feedback} pending inquiries"),
            "ai_rep":     ("🤖", "Rep AI Suite", "Inbox analysis and timetable generation"),
            "profile":    ("👤", "Rep Profile", "Manage credentials and PIN"),
            "features":   ("🧩", "Slot Features", "Custom class extensions"),
        }
        s_icon, s_title, s_desc = screen_titles.get(screen, ("📌", "Class Rep View", ""))
        top_c1, top_c2 = st.columns([1, 3])
        with top_c1:
            if st.button("← Dashboard", use_container_width=True, key=f"rep_back_btn_{screen}"):
                st.session_state.rep_screen = "dashboard"
                st.rerun()
        with top_c2:
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;background:white;border:1px solid #e2e8f0;border-radius:10px;padding:6px 12px;box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:1.1rem;">{s_icon}</span>
                    <div>
                        <div style="font-size:0.92rem;font-weight:800;color:#0f172a;line-height:1.2;">{s_title}</div>
                        <div style="font-size:0.70rem;color:#64748b;">{s_desc}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

    # 1. DASHBOARD
    if screen == "dashboard":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="metric-card" style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:12px 10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.04);margin-bottom:8px;">
                <div style="font-size:1.3rem;">👥</div>
                <div style="font-size:1.2rem;font-weight:800;color:#0f172a;">{total_students}</div>
                <div style="font-size:0.68rem;color:#64748b;font-weight:700;">Students</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card" style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:12px 10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.04);margin-bottom:8px;">
                <div style="font-size:1.3rem;">📥</div>
                <div style="font-size:1.2rem;font-weight:800;color:#0f172a;">{pending_feedback}</div>
                <div style="font-size:0.68rem;color:#64748b;font-weight:700;">Pending Inquiries</div>
            </div>
            """, unsafe_allow_html=True)
            
        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f"""
            <div class="metric-card" style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:12px 10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.04);margin-bottom:8px;">
                <div style="font-size:1.3rem;">📢</div>
                <div style="font-size:1.2rem;font-weight:800;color:#0f172a;">{len(announcements)}</div>
                <div style="font-size:0.68rem;color:#64748b;font-weight:700;">Announcements</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="metric-card" style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:12px 10px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.04);margin-bottom:8px;">
                <div style="font-size:1.3rem;">📁</div>
                <div style="font-size:1.2rem;font-weight:800;color:#0f172a;">{len(materials)}</div>
                <div style="font-size:0.68rem;color:#64748b;font-weight:700;">Materials</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="margin:16px 0 8px 0;font-size:0.75rem;font-weight:800;letter-spacing:0.8px;text-transform:uppercase;color:#64748b;">⚡ QUICK LAUNCH</div>', unsafe_allow_html=True)
        
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:4px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.2rem;">👥</span>
                    <div>
                        <div style="font-size:0.88rem;font-weight:700;color:#0f172a;">Students & Groups</div>
                        <div style="font-size:0.70rem;color:#64748b;">{total_students} enrolled students</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Students →", key="rep_dash_open_students", use_container_width=True, type="primary"):
                st.session_state.rep_screen = "students"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:4px;margin-top:8px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.2rem;">📢</span>
                    <div>
                        <div style="font-size:0.88rem;font-weight:700;color:#0f172a;">Notices & Files</div>
                        <div style="font-size:0.70rem;color:#64748b;">Post announcements</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Notices →", key="rep_dash_open_notices", use_container_width=True):
                st.session_state.rep_screen = "notices"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:4px;margin-top:8px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.2rem;">🤖</span>
                    <div>
                        <div style="font-size:0.88rem;font-weight:700;color:#0f172a;">Rep AI Suite</div>
                        <div style="font-size:0.70rem;color:#64748b;">Smart analysis & drafts</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Launch AI Suite →", key="rep_dash_open_ai", use_container_width=True):
                st.session_state.rep_screen = "ai_rep"
                st.rerun()

        with g2:
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:4px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.2rem;">📥</span>
                    <div>
                        <div style="font-size:0.88rem;font-weight:700;color:#0f172a;">Feedback Inbox</div>
                        <div style="font-size:0.70rem;color:#64748b;">{pending_feedback} pending inquiries</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Feedback →", key="rep_dash_open_feed", use_container_width=True, type="primary"):
                st.session_state.rep_screen = "feedback"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:4px;margin-top:8px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.2rem;">📅</span>
                    <div>
                        <div style="font-size:0.88rem;font-weight:700;color:#0f172a;">Timetable</div>
                        <div style="font-size:0.70rem;color:#64748b;">Weekly lecture schedule</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Timetable →", key="rep_dash_open_tt", use_container_width=True):
                st.session_state.rep_screen = "timetable"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:4px;margin-top:8px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.2rem;">⚙️</span>
                    <div>
                        <div style="font-size:0.88rem;font-weight:700;color:#0f172a;">Profile & Security</div>
                        <div style="font-size:0.70rem;color:#64748b;">Account & password PIN</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Profile →", key="rep_dash_open_prof", use_container_width=True):
                st.session_state.rep_screen = "profile"
                st.rerun()

    # 2. STUDENTS & GROUPS
    elif screen == "students":
        sub_roster, sub_groups = st.tabs([
            f"📋 Roster ({total_students})",
            "👥 Group Allocations"
        ])
        with sub_roster:
            st.markdown(f"### {d_name} — {r_year} Students")
            if df_class.empty:
                st.info("No students registered for your class yet.")
            else:
                search = st.text_input("Search", placeholder="Name or reg number...")
                df_show = df_class.copy()
                if search:
                    mask = (
                        df_show["Student Name"].str.contains(search, case=False, na=False) |
                        df_show["Reg Number"].str.contains(search, case=False, na=False)
                    )
                    df_show = df_show[mask]
                
                # Mobile card rendering
                if is_mob:
                    render_rep_roster_mobile(df_show, total_students)
                else:
                    st.dataframe(df_show, use_container_width=True)
                    st.caption(f"Showing {len(df_show)} of {total_students} students")

                # Export to CSV
                csv = df_show.to_csv(index=False)
                st.download_button(
                    "Export Class List to CSV",
                    data=csv,
                    file_name=f"{r_dept}_{r_year.replace(' ','_')}_students.csv",
                    mime="text/csv",
                    use_container_width=True
                )

                st.markdown("---")
                st.markdown("#### Delete Student")
                del_name = st.selectbox(
                    "Select student",
                    ["— Select —"] + list(df_class["Student Name"].values),
                    key="del_student_sel"
                )
                if del_name != "— Select —":
                    if st.button(f"Delete {del_name}", type="secondary", use_container_width=True):
                        result = db.delete_student(del_name)
                        if result.get("status") == "success":
                            st.success(f"{del_name} deleted.")
                            st.rerun()
                        else:
                            st.error(f"{result.get('message', 'Error')}")

                st.markdown("---")
                st.markdown("#### Reset Student PIN")
                st.caption("Use this if a student is locked out and cannot reset their PIN.")
                reset_sel = st.selectbox(
                    "Select student to reset PIN",
                    ["— Select —"] + list(df_class["Student Name"].values),
                    key="reset_pin_sel"
                )
                if reset_sel != "— Select —":
                    new_pin_rep = st.text_input(
                        "New PIN for student", type="password",
                        max_chars=6, key="rep_reset_pin_input",
                        placeholder="4-digit PIN"
                    )
                    if st.button("Reset PIN", key="rep_reset_pin_btn", use_container_width=True, type="primary"):
                        if not new_pin_rep or not new_pin_rep.isdigit() or len(new_pin_rep) < 4:
                            st.error("PIN must be at least 4 digits.")
                        else:
                            reg_row = df_class[df_class["Student Name"] == reset_sel]
                            if not reg_row.empty:
                                reg = reg_row.iloc[0]["Reg Number"]
                                with st.spinner("Resetting..."):
                                    ok = db.set_pin(reg, new_pin_rep)
                                if ok:
                                    st.success(f"PIN reset for {reset_sel}. Share the new PIN with them securely.")
                                else:
                                    st.error("Reset failed.")

        with sub_groups:
            st.markdown("### Group Allocation")
            if df_class.empty:
                st.warning("No students to allocate.")
            else:
                st.markdown("#### AI Auto-Allocation")
                team_size = st.slider("Students per group", 2, 10, 4)
                instructions = st.text_area(
                    "Custom instructions (optional)",
                    placeholder="e.g., Mix course codes, keep students with same contact apart..."
                )
                if st.button("Auto-Allocate with AI", use_container_width=True, type="primary"):
                    with st.spinner("Generating groups..."):
                        result = ai.generate_teams(df_class, team_size, instructions)
                    if "error" in result:
                        st.error(f"{result['error']}")
                    else:
                        st.session_state["pending_allocations"] = result
                        st.success(f"{len(set(result.values()))} groups for {len(result)} students.")

                if "pending_allocations" in st.session_state:
                    alloc = st.session_state["pending_allocations"]
                    preview = {}
                    for reg, grp in alloc.items():
                        preview.setdefault(grp, []).append(reg)
                    st.markdown("**Preview:**")
                    for grp, members in preview.items():
                        st.markdown(f"**{grp}** — {', '.join(members)}")
                    if st.button("Save Groups", use_container_width=True, type="primary"):
                        with st.spinner("Saving..."):
                            res = db.save_group_allocations(alloc)
                        if res.get("status") == "success":
                            del st.session_state["pending_allocations"]
                            st.success("Groups saved!")
                            st.rerun()
                        else:
                            st.error("Failed to save.")

                st.markdown("---")
                st.markdown("#### Manual Assignment")
                with st.form("manual_group_form"):
                    student_sel = st.selectbox("Student", df_class["Student Name"].values)
                    group_name = st.text_input("Group Name", placeholder="e.g., Team Alpha")
                    if st.form_submit_button("Assign", use_container_width=True):
                        reg = df_class[df_class["Student Name"] == student_sel]["Reg Number"].values
                        if len(reg):
                            res = db.save_group_allocations({reg[0]: group_name})
                            if res.get("status") == "success":
                                st.success(f"{student_sel} → {group_name}")
                                st.rerun()

                st.markdown("---")
                st.markdown("#### Course Unit Groups (with AI)")
                st.info("Create course unit groups (e.g. Thermodynamics, Mathematics).")

                with st.expander("Create Course Unit Groups", expanded=False):
                    course_units_input = st.text_area(
                        "Course Units (one per line)",
                        placeholder="Thermodynamics\nMathematics\nPhysics",
                        height=100
                    )
                    ai_instruction = st.text_area(
                        "AI Grouping Instruction",
                        placeholder="Create 3-4 student groups per course.",
                        height=100
                    )

                    if st.button("Generate Groups with AI", use_container_width=True, type="primary"):
                        if course_units_input.strip() and ai_instruction.strip():
                            with st.spinner("Creating groups with AI..."):
                                course_units = [c.strip() for c in course_units_input.split("\n") if c.strip()]
                                student_names = df_class["Student Name"].tolist() if not df_class.empty else []

                                result = ai_rep.create_course_unit_groups(
                                    instruction=ai_instruction,
                                    course_units=course_units,
                                    student_list=student_names
                                )

                                if result.get("status") == "success":
                                    st.session_state["pending_course_groups"] = result.get("groups", {})
                                    st.success("Course unit groups created! Preview below:")
                                else:
                                    st.error(f"Could not create groups: {result.get('message', 'Unknown error')}")
                        else:
                            st.warning("Please provide both course units and grouping instructions.")

                    if "pending_course_groups" in st.session_state:
                        course_groups = st.session_state["pending_course_groups"]
                        st.markdown("**Preview:**")
                        for course, groups in course_groups.items():
                            with st.expander(f"{course}"):
                                for group_name, students in groups.items():
                                    st.write(f"**{group_name}:** {', '.join(students[:10])}")

                        if st.button("Save Course Unit Groups", use_container_width=True, type="primary"):
                            with st.spinner("Saving..."):
                                student_groups = {}
                                for course, groups in course_groups.items():
                                    for group_name, students in groups.items():
                                        for student in students:
                                            if student not in student_groups:
                                                student_groups[student] = {}
                                            student_groups[student][course] = group_name

                                res = db.save_course_unit_groups(r_dept, r_year, student_groups)
                                if res.get("status") == "success":
                                    del st.session_state["pending_course_groups"]
                                    st.success("Course unit groups saved!")
                                    st.rerun()
                                else:
                                    st.error("Failed to save groups.")

    # 3. NOTICES & MATERIALS
    elif screen == "notices":
        sub_ann, sub_mat = st.tabs([
            "📢 Announcements",
            "📁 Course Materials"
        ])
        with sub_ann:
            st.markdown("### Announcements")
            st.info(f"Visible only to **{d_name} — {r_year}** students.")

            with st.form("post_ann_form", clear_on_submit=True):
                ann_text = st.text_area("Announcement text", height=100)
                priority = st.selectbox("Priority", ["Normal", "Urgent"])
                
                c1, c2 = st.columns(2)
                with c1:
                    post_btn = st.form_submit_button("Post", use_container_width=True)
                with c2:
                    draft_btn = st.form_submit_button("Draft with AI", use_container_width=True)

                if draft_btn and ann_text.strip():
                    with st.spinner("Drafting..."):
                        st.session_state.rep_ai_draft = ai_rep.draft_announcement(ann_text, priority)
                if post_btn:
                    if ann_text.strip():
                        if db.post_announcement(ann_text, priority, dept=r_dept, year=r_year):
                            st.success("Announcement posted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to post.")
                    else:
                        st.warning("Please enter text.")

            if st.session_state.rep_ai_draft:
                st.markdown("**AI Draft — edit before posting:**")
                edited = st.text_area("", value=st.session_state.rep_ai_draft, height=130, key="draft_edit")
                pri2 = st.selectbox("Priority", ["Normal", "Urgent"], key="draft_pri")
                if st.button("Post this Draft", use_container_width=True, type="primary"):
                    if db.post_announcement(edited, pri2, dept=r_dept, year=r_year):
                        st.session_state.rep_ai_draft = ""
                        st.success("Draft posted!")
                        st.rerun()

            st.markdown("---")
            st.markdown("#### Posted Announcements")
            if announcements:
                for aidx, ann in enumerate(announcements):
                    ann_text_val = ann.get("text", "") if isinstance(ann, dict) else str(ann)
                    priority_val = ann.get("priority", "Normal") if isinstance(ann, dict) else "Normal"
                    ts_val = ann.get("timestamp", "") if isinstance(ann, dict) else ""
                    is_urgent = priority_val.lower() == "urgent"
                    left_col = "#ef4444" if is_urgent else primary

                    st.markdown(f"""
                    <div style="background:white;border-radius:12px;padding:12px 14px;
                        margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {left_col};">
                        <div style="font-size:0.72rem;color:#94a3b8;margin-bottom:4px;">{ts_val}</div>
                        <span style="background:{'#fee2e2' if is_urgent else light};
                            color:{left_col};font-size:0.68rem;font-weight:700;
                            padding:2px 8px;border-radius:10px;margin-right:8px;">
                            {priority_val.upper()}
                        </span>
                        <span style="font-size:0.88rem;color:#0f172a;">{ann_text_val}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("🗑️ Delete", key=f"del_ann_{aidx}", use_container_width=True):
                        if db.delete_announcement(ann_text_val):
                            st.rerun()
            else:
                st.info("No announcements posted yet.")

        with sub_mat:
            st.markdown("### Course Materials")
            st.info(f"Visible only to **{d_name} — {r_year}** students.")

            uploaded = st.file_uploader(
                "Upload a file", type=["pdf", "docx", "pptx", "xlsx", "txt"]
            )
            
            if uploaded and st.button("Upload Material", use_container_width=True, type="primary"):
                with st.spinner("Uploading to Google Drive..."):
                    ok = db.upload_material(
                        uploaded.read(), uploaded.name, uploaded.type,
                        dept=r_dept, year=r_year,
                    )
                if ok:
                    st.success(f"'{uploaded.name}' uploaded!")
                    st.rerun()
                else:
                    st.error("Upload failed.")

            st.markdown("---")
            if materials:
                for midx, mat in enumerate(materials):
                    m_name = mat.get("name", "Unnamed") if isinstance(mat, dict) else str(mat)
                    ext = m_name.split(".")[-1].upper() if "." in m_name else "FILE"
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"""
                        <div style="background:white;border-radius:10px;padding:10px 12px;
                            border:1px solid #e2e8f7;word-break:break-all;">
                            <span style="background:{light};color:{primary};font-size:0.68rem;
                                font-weight:800;padding:2px 6px;border-radius:4px;margin-right:6px;">
                                {ext}
                            </span>{m_name}
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"del_mat_{midx}", use_container_width=True):
                            if db.delete_material(m_name):
                                st.success(f"Deleted '{m_name}'.")
                                st.rerun()
                            else:
                                st.error("Delete failed.")
            else:
                st.info("No materials uploaded yet.")

    # 4. TIMETABLE
    elif screen == "timetable":
        st.markdown("### Class Timetable")
        st.info(f"Timetable for **{d_name} — {r_year}**.")

        TT_PALETTE = [
            "#1a56db", "#16a34a", "#ea580c", "#7c3aed",
            "#dc2626", "#db2777", "#0d9488", "#b45309",
            "#0284c7", "#4338ca", "#e11d48", "#475569"
        ]
        TT_LIGHTS = [
            "#dbeafe", "#dcfce7", "#ffedd5", "#ede9fe",
            "#fee2e2", "#fce7f3", "#ccfbf1", "#fef3c7",
            "#e0f2fe", "#e0e7ff", "#ffe4e6", "#f1f5f9"
        ]

        def auto_color(course_name):
            idx = sum(ord(c) for c in course_name.upper()) % len(TT_PALETTE)
            return TT_PALETTE[idx], TT_LIGHTS[idx]

        timetable = db.fetch_timetable(dept=r_dept, year=r_year)

        st.markdown("#### Add Entry")
        with st.form("add_tt_form", clear_on_submit=True):
            tt_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday",
                                          "Thursday", "Friday", "Saturday", "Sunday"])
            tt_time = st.text_input("Time", placeholder="e.g. 8:00 AM - 10:00 AM")
            tt_course = st.text_input("Course Code / Name", placeholder="e.g. BMEC 2101")
            tt_lecturer = st.text_input("Lecturer Name", placeholder="e.g. Dr. Okello")
            tt_type = st.radio("Session Type", ["Weekly", "One-off"], horizontal=True)

            if st.form_submit_button("Add Entry", use_container_width=True, type="primary"):
                if not tt_time or not tt_course:
                    st.warning("Please fill in Day, Time and Course at minimum.")
                else:
                    c_hex, c_light = auto_color(tt_course)
                    with st.spinner("Saving..."):
                        ok = db.add_timetable_entry(
                            r_dept, r_year, tt_day,
                            tt_time, tt_course, tt_lecturer,
                            color=c_hex, entry_type=tt_type
                        )
                    if ok:
                        st.success(f"Added: {tt_day} {tt_time} — {tt_course}")
                        st.rerun()
                    else:
                        st.error("Failed to add entry.")

        st.markdown("---")
        with st.expander("Import Timetable from Raw Text (AI)"):
            raw_tt = st.text_area("Paste timetable text:", height=120,
                                  placeholder="e.g. Monday 8am BMEC, Tuesday 10am BBPE...")
            if st.button("Parse & Import with AI", key="parse_tt_btn", use_container_width=True, type="primary"):
                if not raw_tt.strip():
                    st.warning("Please paste some timetable text.")
                else:
                    with st.spinner("Parsing..."):
                        from ai_engine import _call_with_retry
                        from google.genai import types as _types
                        prompt = (
                            "Parse this timetable text into a JSON array. "
                            "Each item must have: day, time, course, lecturer, type. "
                            "Days must be full names (Monday, Tuesday etc). "
                            "type must be Weekly or One-off. "
                            "lecturer can be empty string if not mentioned. "
                            "Return ONLY raw JSON array, no markdown.\n\n"
                            "Timetable: " + raw_tt
                        )
                        config = _types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                        result = _call_with_retry("models/gemini-2.5-flash", prompt, config)
                        try:
                            entries = _json.loads(result)
                            added = 0
                            for entry in entries:
                                day = entry.get("day", "").strip()
                                time = entry.get("time", "").strip()
                                course = entry.get("course", "").strip()
                                if day and time and course:
                                    lecturer = entry.get("lecturer", "").strip()
                                    entry_type = entry.get("type", "Weekly").strip()
                                    c_hex, _ = auto_color(course)
                                    if db.add_timetable_entry(
                                        r_dept, r_year, day, time,
                                        course, lecturer, c_hex, entry_type
                                    ):
                                        added += 1
                            st.success(f"Imported {added} entries!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not parse: {e}")

        st.markdown("---")
        st.markdown("#### Current Timetable")

        if not timetable:
            st.info("No timetable entries yet.")
        else:
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            by_day = {}
            for entry in timetable:
                d = entry.get("day", "Other")
                by_day.setdefault(d, []).append(entry)

            for day in day_order:
                if day not in by_day:
                    continue
                st.markdown(f"**{day}**")
                entries = sorted(by_day[day], key=lambda x: x.get("time", ""))
                for eidx, entry in enumerate(entries):
                    e_color = entry.get('color', '') or primary
                    e_lcolor, _ = auto_color(entry.get('course', ''))
                    e_color = e_color if e_color else e_lcolor
                    lect_str = f'<div style="color:#64748b;font-size:0.75rem;margin-top:2px;">👨‍🏫 {entry.get("lecturer","").title()}</div>' if entry.get("lecturer") else ""
                    
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:10px 14px;
                        margin-bottom:6px;border:1px solid #e2e8f7;border-left:4px solid {e_color};">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-weight:800;color:{e_color};font-size:0.85rem;">{entry.get('time', '')}</span>
                            <span style="background:#f1f5f9;color:#64748b;font-size:0.65rem;font-weight:700;padding:1px 6px;border-radius:6px;">{entry.get('type', 'Weekly')}</span>
                        </div>
                        <div style="color:#1e293b;font-weight:700;font-size:0.90rem;margin-top:2px;">{entry.get('course', '')}</div>
                        {lect_str}
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"🗑️ Delete Entry ({entry.get('course','')})", key=f"del_tt_{day}_{eidx}", use_container_width=True):
                        with st.spinner("Deleting..."):
                            ok = db.delete_timetable_entry(r_dept, r_year, day, entry.get("time", ""))
                        if ok:
                            st.rerun()

            st.markdown("---")
            if st.button("Clear Entire Timetable", type="secondary", use_container_width=True):
                st.session_state["confirm_clear_tt"] = True
                st.rerun()

            if st.session_state.get("confirm_clear_tt"):
                st.warning("Delete ALL timetable entries for this class?")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("Yes, clear all", key="yes_clear_tt", use_container_width=True, type="primary"):
                        with st.spinner("Clearing..."):
                            db.clear_timetable(r_dept, r_year)
                        st.session_state["confirm_clear_tt"] = False
                        st.rerun()
                with cb:
                    if st.button("Cancel", key="no_clear_tt", use_container_width=True):
                        st.session_state["confirm_clear_tt"] = False
                        st.rerun()

    # 5. FEEDBACK & REPLIES
    elif screen == "feedback":
        sub_fb, sub_rep = st.tabs([
            f"📥 Inquiries ({pending_feedback})" if pending_feedback else "📥 Inquiries",
            f"💬 Replies ({unread_replies})" if unread_replies else "💬 Replies"
        ])
        with sub_fb:
            st.markdown("### Student Feedback Inbox")
            if not feedback_list:
                st.info("No feedback messages yet.")
            else:
                pending = [f for f in feedback_list
                           if isinstance(f, list) and len(f) >= 4
                           and str(f[3]).lower() == "pending"]
                reviewed = [f for f in feedback_list if f not in pending]
                st.caption(f"{len(pending)} pending · {len(reviewed)} reviewed")

                if st.button("Summarize All with AI", use_container_width=True, type="primary"):
                    with st.spinner("Analyzing..."):
                        summary = ai_rep.summarize_feedback(feedback_list)
                    st.markdown(summary)
                    st.markdown("---")

                for fidx, fb in enumerate(feedback_list):
                    if not (isinstance(fb, list) and len(fb) >= 5):
                        continue
                    ts, reg, name, status, msg = (
                        str(fb[0]), str(fb[1]), str(fb[2]), str(fb[3]), str(fb[4])
                    )
                    is_rev = status.lower() == "reviewed"
                    sc = "#16a34a" if is_rev else "#d4820a"
                    card_cls = "fb-card reviewed" if is_rev else "fb-card"

                    st.markdown(f"""
                    <div class="{card_cls}">
                        <div style="font-size:0.75rem;color:#94a3b8;">
                            <strong>{name}</strong> · {reg} · {ts}
                            &nbsp;<span style="color:{sc};font-weight:700;">{status}</span>
                        </div>
                        <div style="margin-top:6px;font-size:0.88rem;color:#0f172a;">{msg}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if not is_rev and st.button("Mark Read", key=f"rev_{fidx}", use_container_width=True):
                            if db.update_feedback_status(ts, reg):
                                st.rerun()
                    with c2:
                        if st.button("AI Reply", key=f"ai_rep_{fidx}", use_container_width=True):
                            with st.spinner("Drafting..."):
                                st.session_state.rep_ai_reply = ai_rep.suggest_reply(name, msg)
                                st.session_state[f"reply_target_{fidx}"] = {
                                    "reg": reg, "name": name, "ts": ts
                                }
                    with c3:
                        if st.button("Delete", key=f"del_fb_{fidx}", use_container_width=True):
                            if db.delete_feedback(ts, reg):
                                st.rerun()

                    if st.session_state.get(f"reply_target_{fidx}"):
                        reply_text = st.text_area(
                            "Reply:", value=st.session_state.rep_ai_reply,
                            key=f"reply_ta_{fidx}", height=100
                        )
                        
                        if st.button("Send Reply", key=f"send_rep_{fidx}", use_container_width=True, type="primary"):
                            target = st.session_state[f"reply_target_{fidx}"]
                            reply_clean = re.sub(r'<[^>]+>', '', reply_text).replace('&nbsp;', ' ').strip()

                            ok = db.post_rep_reply(
                                reg_number=target["reg"],
                                student_name=target["name"],
                                message=reply_clean,
                                rep_name=r_name,
                                dept=r_dept,
                                year=r_year
                            )
                            if ok:
                                db.update_feedback_status(target["ts"], target["reg"])
                                st.session_state[f"reply_target_{fidx}"] = None
                                st.session_state.rep_ai_reply = ""
                                st.success("Reply sent successfully!")
                                st.rerun()

        with sub_rep:
            st.markdown("### Sent Replies Overview")
            if not rep_replies:
                st.info("No replies sent yet.")
            else:
                for reply in rep_replies:
                    r_time = reply.get("timestamp", "")
                    r_student = reply.get("student_name", "")
                    r_msg = reply.get("message", "")
                    r_status = reply.get("read_status", "Unread")
                    is_read = r_status.lower() == "read"
                    sc = "#16a34a" if is_read else primary

                    st.markdown(f"""
                    <div style="background:white;border-radius:12px;padding:12px 14px;
                        margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {sc};">
                        <div style="font-size:0.74rem;color:#94a3b8;">
                            To: <strong>{r_student}</strong> · {r_time}
                            &nbsp;<span style="color:{sc};font-weight:600;">
                                {'Read' if is_read else 'Unread'}
                            </span>
                        </div>
                        <div style="margin-top:4px;font-size:0.86rem;color:#0f172a;">{r_msg}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # 6. REP AI INTELLIGENCE
    elif screen == "ai_rep":
        st.markdown("### 🤖 AI Class Manager")
        st.markdown(f'<div class="scope-badge">Powered by AI · {d_name} — {r_year}</div>', unsafe_allow_html=True)

        ai_tabs = st.tabs([
            "📊 Inbox Analysis",
            "📢 Announcements",
            "⏰ Reminders",
            "👥 Groups",
            "✨ Generate TT",
            "🧹 Format TT",
            "⚠️ Conflicts",
            "💬 TT Q&A"
        ])

        with ai_tabs[0]:
            st.markdown("#### 📊 Full Class Inbox Analysis")
            st.info("AI reads all feedback, announcements and timetable to give you a complete intelligence report.")

            if st.button("Run Full Analysis", use_container_width=True, type="primary", key="btn_run_full_analysis"):
                with st.spinner("Analyzing your entire class inbox..."):
                    timetable_data = db.fetch_timetable(dept=r_dept, year=r_year)
                    analysis = ai_rep.analyze_feedback_inbox(
                        feedback_list, announcements, timetable_data
                    )

                if "error" in analysis:
                    st.error(f"{analysis['error']}")
                else:
                    sentiment = analysis.get("sentiment", "Neutral")
                    s_color = {"Positive": "#16a34a", "Neutral": "#0284c7",
                               "Stressed": "#ea580c", "Concerned": "#dc2626"}.get(sentiment, primary)
                    st.markdown(f"""
                    <div style="background:white;border-radius:14px;padding:16px 18px;
                        border:1px solid #e2e8f7;margin-bottom:16px;border-left:5px solid {s_color};">
                        <div style="font-size:0.72rem;color:#94a3b8;font-weight:700;
                            text-transform:uppercase;margin-bottom:4px;">Class Sentiment</div>
                        <div style="font-size:0.95rem;font-weight:700;color:{s_color};margin-bottom:6px;">
                            {sentiment} Class Atmosphere
                        </div>
                        <div style="font-size:0.86rem;color:#334155;">{analysis.get("summary", "")}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with ai_tabs[1]:
            st.markdown("#### 📢 AI Announcement Suggestions")
            rough = st.text_area(
                "Announcement concept:",
                placeholder="e.g. remind students about the test next week...",
                height=90,
                key="sugg_ann_rough"
            )
            priority = st.selectbox("Priority", ["Normal", "Urgent"], key="sugg_ann_pri")
            if st.button("Draft with AI", use_container_width=True, type="primary", key="btn_draft_ann") and rough.strip():
                with st.spinner("Drafting..."):
                    draft = ai_rep.draft_announcement(rough, priority)
                st.session_state.rep_ai_draft = draft

            if st.session_state.get("rep_ai_draft"):
                st.markdown("**AI Draft:**")
                edited = st.text_area("", value=st.session_state.rep_ai_draft, height=130, key="manager_draft_edit")
                pri2 = st.selectbox("Priority", ["Normal", "Urgent"], key="manager_draft_pri")
                if st.button("Post This Draft", use_container_width=True, type="primary", key="btn_post_draft"):
                    if db.post_announcement(edited, pri2, dept=r_dept, year=r_year):
                        st.session_state.rep_ai_draft = ""
                        st.success("Posted!")
                        st.rerun()

        with ai_tabs[2]:
            st.markdown("#### ⏰ Deadline Detection & Reminders")
            if st.button("Scan for Deadlines", use_container_width=True, type="primary", key="btn_scan_deadlines"):
                with st.spinner("Scanning announcements..."):
                    result = ai_rep.suggest_deadline_reminders(announcements)
                st.markdown(result)

        with ai_tabs[3]:
            st.markdown("#### 👥 AI Group Allocation Advice")
            constraints = st.text_area(
                "Any special constraints? (optional)",
                placeholder="e.g. mix course codes...",
                height=80,
                key="group_alloc_constraints"
            )
            if st.button("Get Recommendations", use_container_width=True, type="primary", key="btn_group_alloc"):
                with st.spinner("Analyzing class..."):
                    result = ai_rep.suggest_group_allocation(df_class, constraints)
                st.markdown(result)

        with ai_tabs[4]:
            st.markdown("#### ✨ AI Timetable Generator")
            courses_input = st.text_area(
                "Enter courses (one per line):",
                placeholder="Thermodynamics\nMathematics\nFluid Mechanics",
                height=120,
                key="tt_gen_courses"
            )
            constraints_tt = st.text_area(
                "Constraints (optional):",
                placeholder="e.g. No classes before 9am...",
                height=80,
                key="tt_gen_constraints"
            )
            if st.button("Generate Timetable", use_container_width=True, type="primary", key="btn_gen_tt") and courses_input.strip():
                courses_list = [c.strip() for c in courses_input.strip().split("\n") if c.strip()]
                with st.spinner("Generating timetable..."):
                    result = ai_rep.generate_timetable_suggestion(courses_list, constraints_tt)
                st.markdown(result)

        with ai_tabs[5]:
            st.markdown("#### 🧹 Format Raw Timetable")
            raw = st.text_area("Paste raw timetable:", height=150, key="fmt_raw_tt")
            if st.button("Format with AI", use_container_width=True, type="primary", key="btn_fmt_tt") and raw.strip():
                with st.spinner("Formatting..."):
                    result = ai_rep.format_timetable(raw)
                st.markdown(result)

        with ai_tabs[6]:
            st.markdown("#### ⚠️ Timetable Conflict Checker")
            raw_c = st.text_area("Paste timetable to check:", height=150, key="conflict_raw_tt")
            if st.button("Check for Conflicts", use_container_width=True, type="primary", key="btn_conflict_tt") and raw_c.strip():
                with st.spinner("Checking..."):
                    result = ai_rep.check_timetable_conflicts(raw_c)
                st.markdown(result)

        with ai_tabs[7]:
            st.markdown("#### 💬 Ask About the Timetable")
            timetable_qa = st.text_area("Paste timetable:", height=120, key="qa_tt_content")
            question_qa = st.text_input("Your question:", placeholder="When is the Engineering Maths lecture?", key="qa_tt_question")
            if st.button("Ask AI", use_container_width=True, type="primary", key="btn_qa_tt") and question_qa.strip() and timetable_qa.strip():
                with st.spinner("Answering..."):
                    result = ai_rep.answer_timetable_question(question_qa, timetable_qa)
                st.info(result)

    # 7. REP PROFILE & SECURITY
    elif screen == "profile":
        st.markdown("### Account Settings")
        rep_prof_av = render_avatar_html(r_avatar, r_name, size=64, color=primary, light=light)
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:16px 18px;
            border:1px solid #e2e8f7;margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
                {rep_prof_av}
                <div>
                    <div style="font-size:1.1rem;font-weight:800;color:#1e293b;">{r_name}</div>
                    <div style="font-size:0.78rem;color:#94a3b8;">Class Representative · {r_year}</div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5f9;font-size:0.84rem;">
                <span style="color:#64748b;font-weight:600;">Reg Number</span>
                <span style="font-weight:700;color:#0f172a;">{r_reg}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5f9;font-size:0.84rem;">
                <span style="color:#64748b;font-weight:600;">Department</span>
                <span style="font-weight:700;color:#0f172a;">{d_name}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:0.84rem;">
                <span style="color:#64748b;font-weight:600;">Year</span>
                <span style="font-weight:700;color:#0f172a;">{r_year}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📸 Profile Photo")
        with st.expander("Update Rep Photo", expanded=bool(not r_avatar)):
            new_rep_pic = st.file_uploader("Upload photo", type=["png", "jpg", "jpeg", "webp"], key="rep_av_up")
            if st.button("💾 Save Photo", key="save_rep_pic_btn", use_container_width=True, type="primary"):
                if new_rep_pic:
                    with st.spinner("Uploading photo..."):
                        url = db.upload_rep_avatar(r_dept, r_year, new_rep_pic.getvalue(), new_rep_pic.type or "image/jpeg")
                    if url:
                        st.session_state.rep_avatar = url
                        st.success("✅ Profile photo updated!")
                        st.rerun()
                    else:
                        st.error("Failed to upload photo.")
                else:
                    st.warning("Please select an image first.")

        st.markdown("#### Change Password")
        if not st.session_state.rep_show_change_pw:
            if st.button("Change My Password", use_container_width=True):
                st.session_state.rep_show_change_pw = True
                st.rerun()
        else:
            with st.form("change_pw_form", clear_on_submit=True):
                old_pw = st.text_input("Current Password", type="password")
                new_pw = st.text_input("New Password", type="password")
                new_pw2 = st.text_input("Confirm New Password", type="password")
                save_btn = st.form_submit_button("Save New Password", use_container_width=True)
                cancel_btn = st.form_submit_button("Cancel", use_container_width=True)

                if cancel_btn:
                    st.session_state.rep_show_change_pw = False
                    st.rerun()

                if save_btn:
                    if not old_pw or not new_pw:
                        st.warning("Please fill in all fields.")
                    elif new_pw != new_pw2:
                        st.error("New passwords do not match.")
                    elif len(new_pw) < 6:
                        st.error("New password must be at least 6 characters.")
                    else:
                        with st.spinner("Updating..."):
                            result = db.change_rep_password(r_dept, r_year, old_pw, new_pw)
                        if result.get("status") == "success":
                            st.success("Password changed successfully!")
                            st.session_state.rep_show_change_pw = False
                            st.rerun()
                        else:
                            st.error(f"{result.get('message', 'Failed')}")

    # 8. SLOT FEATURES
    elif screen == "features":
        render_rep_slots(db, r_reg, r_name, r_dept, r_year, primary, light, df_class)

    # Logout 
    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
    if st.button("🚪 Sign Out", use_container_width=True):
        for k in ["rep_logged_in", "rep_dept", "rep_year", "rep_name",
                  "rep_reg", "rep_ai_draft", "rep_ai_reply",
                  "pending_allocations", "rep_show_change_pw"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()