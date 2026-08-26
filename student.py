"""
student.py — Student Portal UI with Profile Picture Attachments & Robust PDF Generation.
Read receipts removed. Dept+year scoped. Coloured themes per department.
"""
import json as _json
import re as _re
from datetime import datetime
import streamlit as st
import pandas as pd
from database import SheetDatabaseManager
from database.avatars import render_avatar_html
from cache import (
    cached_fetch_roster, cached_fetch_announcements, cached_fetch_materials,
    cached_fetch_feedback, cached_fetch_rep_replies, cached_fetch_timetable
)
from config import (
    get_departments, YEARS,
    dept_color, dept_light, dept_name, dept_courses
)
from utils.mobile import is_mobile, get_view_mode_toggle
from notifications_ui import render_notification_bell
from database.students import is_valid_email


def inject_css(primary: str = "#1e40af", light: str = "#eff6ff"):
    is_mob = is_mobile()
    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    body, .stApp, p, h1, h2, h3, h4, h5, h6, input, textarea, select, button, label {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        line-height: 1.55;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    
    #MainMenu, footer, header[data-testid="stHeader"], [data-testid="stHeader"] {{ 
        visibility: hidden !important; 
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    .stApp {{ background-color: #f8fafc !important; }}
    .block-container {{
        padding-top: 1.25rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1050px !important;
    }}
    
    /*  Welcome Banner  */
    .welcome-banner {{
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #1e40af 100%) !important;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 20px;
        color: #ffffff !important;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.16);
        border: 1px solid rgba(255, 255, 255, 0.12);
        position: relative;
        overflow: hidden;
    }}
    .welcome-banner h2 {{
        font-size: 1.55rem;
        font-weight: 800;
        margin: 0 0 4px 0;
        color: #ffffff !important;
        letter-spacing: -0.3px;
    }}
    .welcome-banner p {{
        font-size: 0.88rem;
        opacity: 0.9;
        color: #cbd5e1 !important;
        margin: 0 0 12px 0;
    }}
    
    /*  Pill Chips  */
    .pill-strip {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 6px;
    }}
    .pill {{
        background: rgba(255, 255, 255, 0.14);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 20px;
        padding: 4px 13px;
        font-size: 0.74rem;
        font-weight: 600;
        color: #ffffff !important;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }}
    
    /*  Cards & Containers  */
    .stat-card {{
        background: white;
        border-radius: 14px;
        padding: 18px 14px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .stat-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.06);
    }}
    .stat-card .s-val {{
        font-size: 1.5rem;
        font-weight: 800;
        color: #1e40af;
    }}
    .stat-card .s-label {{
        font-size: 0.72rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    
    .metric-card {{
        background: white;
        border-radius: 14px;
        padding: 18px 14px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 10px;
        transition: transform 0.2s ease;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
    }}
    
    /*  Announcements  */
    .ann-card {{
        background: white;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        border-left: 4px solid {primary};
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }}
    .ann-card:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }}
    .ann-card.urgent {{
        border-left-color: #ef4444;
        background: #fffafa;
    }}
    .ann-card.read {{
        border-left-color: #cbd5e1;
        opacity: 0.75;
    }}
    .ann-badge {{
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        margin-bottom: 8px;
    }}
    .badge-normal {{ background: {light}; color: {primary}; }}
    .badge-urgent {{ background: #fee2e2; color: #dc2626; }}
    .badge-read   {{ background: #f1f5f9; color: #64748b; }}
    
    /*  Materials  */
    .mat-row {{
        background: white;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        display: flex;
        align-items: center;
        gap: 16px;
        transition: all 0.2s ease;
    }}
    .mat-row:hover {{
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }}
    .mat-icon {{
        width: 46px;
        height: 46px;
        border-radius: 12px;
        background: {light};
        color: {primary};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 800;
        flex-shrink: 0;
    }}
    .mat-icon.pdf {{ background: #fee2e2; color: #dc2626; }}
    
    /*  Group / Members  */
    .member-card {{
        background: white;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 8px;
        border: 1px solid #e2e8f0;
        display: flex;
        align-items: center;
        gap: 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }}
    .group-banner {{
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #1e40af 100%);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 16px;
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }}
    
    /*  Profile  */
    .profile-card {{
        background: white;
        border-radius: 16px;
        padding: 26px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    .profile-avatar-wrap {{
        display: flex;
        align-items: center;
        gap: 18px;
        margin-bottom: 18px;
    }}
    
    /*  Misc  */
    .msg-info-card {{
        background: {light};
        border: 1px solid {primary}33;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 16px;
        font-size: 0.88rem;
        color: {primary};
    }}
    .pro-divider {{
        height: 1px;
        background: #e2e8f0;
        margin: 20px 0;
    }}
    .activity-strip {{
        background: white;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 18px;
        border-left: 4px solid #1e40af;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }}
    
    /*  Segmented Pill Tabs  */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: white;
        border-radius: 12px;
        padding: 4px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        flex-wrap: wrap;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 0.84rem;
        color: #64748b;
        background: transparent;
        border: none;
        transition: all 0.15s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: #0f172a;
        background: #f1f5f9;
    }}
    .stTabs [aria-selected="true"] {{
        background: #0f172a !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15) !important;
    }}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {{ display: none; }}
    
    /*  Buttons (desktop)  */
    .stButton > button {{
        border-radius: 10px;
        font-weight: 600;
        min-height: 40px;
        transition: all 0.2s ease;
    }}
    """
    if is_mob:
        css += f"""
        /* MOBILE OVERRIDES */
        body, .stApp {{
            font-size: 15px !important;
            line-height: 1.55;
        }}
        .stApp {{
            padding: 0 !important;
        }}
        .block-container {{
            padding: 12px 12px 40px 12px !important;
            max-width: 100% !important;
        }}
        h1 {{ font-size: 1.35rem !important; margin-bottom: 8px !important; }}
        h2 {{ font-size: 1.15rem !important; }}
        h3 {{ font-size: 1.0rem !important; }}
        .welcome-banner {{
            padding: 18px 16px !important;
            border-radius: 14px !important;
            margin-bottom: 16px !important;
        }}
        .welcome-banner h2 {{ font-size: 1.25rem !important; margin-bottom: 4px !important; }}
        .welcome-banner p {{ font-size: 0.8rem !important; margin-bottom: 10px !important; }}
        .pill {{ font-size: 0.68rem !important; padding: 3px 10px !important; }}
        .stButton > button {{
            width: 100% !important;
            min-height: 48px !important;
            font-size: 0.92rem !important;
            padding: 10px 14px !important;
            border-radius: 10px !important;
            margin-bottom: 6px !important;
        }}
        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox select {{
            font-size: 1rem !important;
            min-height: 48px !important;
            border-radius: 10px !important;
            padding: 10px 14px !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: none !important;
            padding: 4px 4px !important;
            gap: 4px !important;
            border-radius: 10px !important;
        }}
        .metric-card {{
            padding: 14px 10px !important;
            border-radius: 12px !important;
            margin-bottom: 8px !important;
        }}
        .ann-card {{
            padding: 14px 14px !important;
            border-radius: 10px !important;
            margin-bottom: 8px !important;
        }}
        .mat-row {{
            padding: 12px 14px !important;
            flex-wrap: nowrap !important;
            gap: 10px !important;
        }}
        .member-card {{
            padding: 10px 12px !important;
            gap: 10px !important;
        }}
        .profile-card {{
            padding: 18px 16px !important;
            border-radius: 14px !important;
        }}
        .pro-divider {{
            margin: 14px 0 !important;
        }}
        """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def metric_card(title, value, icon, color="#0f172a"):
    st.markdown(f"""
    <div class="metric-card" style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:16px 12px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <div style="font-size:1.5rem;margin-bottom:4px;">{icon}</div>
        <div style="font-size:1.35rem;font-weight:800;color:#0f172a;margin-bottom:2px;">{value}</div>
        <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;">{title}</div>
    </div>
    """, unsafe_allow_html=True)
def render_student_roster_mobile(df, total_students):
    """Render student roster as cards with avatars on mobile."""
    st.caption(f"Showing {len(df)} of {total_students} students (mobile view)")
    if df.empty:
        st.info("No students found.")
        return
    for _, row in df.iterrows():
        name = row.get("Student Name", "")
        reg = row.get("Reg Number", "")
        course = row.get("Course Code", "")
        group = row.get("Assigned Group", "")
        avatar_url = row.get("Avatar", row.get("avatar_url", ""))
        dept = row.get("Department", row.get("department", row.get("dept", "")))
        color = dept_color(dept) if dept else "#6d28d9"
        avatar_html = render_avatar_html(avatar_url, name, size=40, color=color, light=dept_light(dept))

        st.markdown(f"""
        <div style="background:white;border-radius:10px;padding:12px 14px;margin-bottom:8px;
            border:1px solid #e2e8f7;border-left:3px solid {color};display:flex;align-items:center;gap:12px;">
            {avatar_html}
            <div style="flex:1;">
                <div style="font-weight:700;font-size:0.95rem;">{name}</div>
                <div style="font-size:0.75rem;color:#94a3b8;">{reg} · {course}</div>
                <div style="font-size:0.7rem;color:#64748b;margin-top:4px;">
                    <span style="background:#f1f5f9;padding:1px 8px;border-radius:8px;">{dept}</span>
                    <span style="background:#f1f5f9;padding:1px 8px;border-radius:8px;margin-left:4px;">{group}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_slot_result_mobile(result, rdisplay, primary, light, is_mob):
    """Render slot result with mobile awareness."""
    if not result:
        return
    if result.get("status") == "error":
        st.error(f"⚠️ {result.get('message','Error')}")
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


def render_student_slots(db, s_reg, s_name, s_dept, s_year, primary, light):
    """Render dynamic feature slots for the student portal."""
    is_mob = is_mobile()
    st.markdown("### 🧩 Features")
    with st.spinner("Loading features..."):
        slots = db.get_active_slots(s_dept, s_year, "student")
    if not slots:
        st.info("No additional features have been enabled for your class yet. Check back later.")
        return
    for slot in slots:
        sid = slot.get("slotid", "")
        title = slot.get("title", "Feature")
        icon = slot.get("icon", "")
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
            <div style="font-size:{'1.0rem' if is_mob else '1.1rem'};font-weight:800;color:#1e293b;">
                {icon} {title}
            </div>
            {"<div style='font-size:0.82rem;color:#94a3b8;margin-top:3px;'>" + desc + "</div>" if desc else ""}
        </div>
        """, unsafe_allow_html=True)
        result_key = f"slot_result_{sid}"
        if stype == "button":
            if st.button(f"{icon} {title}", key=f"slot_btn_{sid}", use_container_width=True):
                with st.spinner("Running..."):
                    r = db.call_function(func, {
                        "reg": s_reg,
                        "name": s_name,
                        "dept": s_dept,
                        "year": s_year,
                    })
                st.session_state[result_key] = r
            _render_slot_result_mobile(st.session_state.get(result_key), rdisplay, primary, light, is_mob)
        elif stype == "form":
            with st.form(f"slot_form_{sid}", clear_on_submit=True):
                params = {
                    "reg": s_reg,
                    "name": s_name,
                    "dept": s_dept,
                    "year": s_year,
                }
                valid = True
                for field in fields:
                    fname = field.get("name", "")
                    flabel = field.get("label", fname)
                    ftype = field.get("type", "text")
                    fopts = field.get("options", "").split(",") if field.get("options") else []
                    if ftype == "text":
                        val = st.text_input(flabel, key=f"sf_{sid}_{fname}")
                    elif ftype == "textarea":
                        val = st.text_area(flabel, key=f"sf_{sid}_{fname}", height=100 if is_mob else 80)
                    elif ftype == "number":
                        val = st.number_input(flabel, key=f"sf_{sid}_{fname}")
                    elif ftype == "date":
                        val = str(st.date_input(flabel, key=f"sf_{sid}_{fname}"))
                    elif ftype == "dropdown":
                        val = st.selectbox(flabel, fopts if fopts else ["Option 1"], key=f"sf_{sid}_{fname}")
                    elif ftype == "checkbox":
                        val = str(st.checkbox(flabel, key=f"sf_{sid}_{fname}"))
                    else:
                        val = st.text_input(flabel, key=f"sf_{sid}_{fname}")
                    params[fname] = val
                if st.form_submit_button("Submit", use_container_width=True):
                    for field in fields:
                        if field.get("required") and not params.get(field["name"], ""):
                            st.error(f"⚠️ {field.get('label', field['name'])} is required.")
                            valid = False
                            break
                    if valid:
                        with st.spinner("Submitting..."):
                            r = db.call_function(func, params)
                        st.session_state[result_key] = r
            _render_slot_result_mobile(st.session_state.get(result_key), rdisplay, primary, light, is_mob)
        elif stype in ("display", "table"):
            if st.button(f"Load {title}", key=f"slot_load_{sid}", use_container_width=True):
                with st.spinner("Loading..."):
                    r = db.call_function(func, {
                        "reg": s_reg,
                        "name": s_name,
                        "dept": s_dept,
                        "year": s_year,
                    })
                st.session_state[result_key] = r
            _render_slot_result_mobile(st.session_state.get(result_key), rdisplay, primary, light, is_mob)
        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)


def render_student_interface(db: SheetDatabaseManager, ai_study, df_profiles):
    is_mob = is_mobile()

    defaults = {
        "student_logged_in": None,
        "show_reg_form": False,
        "read_announcements": [],
        "show_ai_tab": False,
        "open_expanders": {},
        "confirm_clear_all": False,
        "ai_chat_history": [],
        "ai_pdf_text": "",
        "ai_selected_file": "",
        "ai_summary_shown": False,
        "ai_summary_text": "",
        "ai_quick_q": "",
        "ai_draft": "",
        "reg_success_msg": "",
        "fb_success_msg": "",
        "show_forgot_pin": False,
        "show_set_pin": False,
        "pending_reg": "",
        "show_change_pin": False,
        "show_update_contact": False,
        "show_ai_history": False,
        "show_upload_avatar": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    primary = "#1a56db"
    light   = "#dbeafe"

    if st.session_state.student_logged_in and not df_profiles.empty:
        row = df_profiles[df_profiles["Reg Number"] == st.session_state.student_logged_in]
        if not row.empty:
            d_col = next((c for c in ["Department", "department", "dept"] if c in row.columns), None)
            if d_col:
                d = str(row.iloc[0][d_col])
                primary = dept_color(d)
                light   = dept_light(d)

    inject_css(primary, light)

    if st.session_state.student_logged_in:
        with st.sidebar:
            get_view_mode_toggle()
            st.markdown("---")

    if not st.session_state.student_logged_in:
        st.markdown("""
<div style="margin:0 0 14px 0;padding-bottom:10px;border-bottom:1px solid #e2e8f7;">
    <div style="font-size:0.68rem;letter-spacing:2px;text-transform:uppercase;
        color:#94a3b8;font-weight:700;margin-bottom:2px;">Sign in to</div>
    <div style="font-size:1.3rem;font-weight:800;color:#0f172a;">
        Student Portal
    </div>
</div>
""", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # LOGIN FLOW
    # -------------------------------------------------------------
    if not st.session_state.student_logged_in and not st.session_state.show_reg_form:
        if st.session_state.show_forgot_pin:
            st.subheader("🔑 Reset Your PIN")
            st.info("Enter your Registration Number and the Contact Number you registered with.")

            with st.form("reset_pin_form", clear_on_submit=True):
                reset_reg     = st.text_input("Registration Number", placeholder="25/U/0000/PS").strip().upper()
                reset_contact = st.text_input("Contact Number",      placeholder="e.g. 0741234567")
                reset_pin1    = st.text_input("New PIN (4 digits)",   type="password", max_chars=6)
                reset_pin2    = st.text_input("Confirm New PIN",      type="password", max_chars=6)
                c1, c2        = st.columns(2)
                with c1: reset_btn  = st.form_submit_button("Reset PIN",  use_container_width=True)
                with c2: cancel_btn = st.form_submit_button("← Back",     use_container_width=True)

                if cancel_btn:
                    st.session_state.show_forgot_pin = False
                    st.rerun()

                if reset_btn:
                    if not reset_reg or not reset_contact or not reset_pin1:
                        st.warning("Please fill in all fields.")
                    elif not reset_pin1.isdigit() or len(reset_pin1) < 4:
                        st.error("⚠️ PIN must be at least 4 digits.")
                    elif reset_pin1 != reset_pin2:
                        st.error("⚠️ PINs do not match.")
                    else:
                        with st.spinner("Verifying..."):
                            result = db.reset_pin(reset_reg, reset_contact, reset_pin1)
                        if result.get("status") == "success":
                            st.success("✅ PIN reset successfully! You can now log in.")
                            st.session_state.show_forgot_pin = False
                            st.rerun()
                        else:
                            st.error(f"⚠️ {result.get('message','Failed')}")

        elif st.session_state.show_set_pin:
            st.subheader("🔐 Set Your PIN")
            st.info("Welcome! This is your first login. Please set a 4-digit PIN for future logins.")
            with st.form("set_pin_form", clear_on_submit=True):
                pin1 = st.text_input("Choose a PIN (4 digits)", type="password", max_chars=6)
                pin2 = st.text_input("Confirm PIN",              type="password", max_chars=6)
                if st.form_submit_button("Set PIN & Log In", use_container_width=True):
                    if not pin1:
                        st.warning("Please enter a PIN.")
                    elif not pin1.isdigit() or len(pin1) < 4:
                        st.error("⚠️ PIN must be at least 4 digits (numbers only).")
                    elif pin1 != pin2:
                        st.error("⚠️ PINs do not match.")
                    else:
                        with st.spinner("Saving PIN..."):
                            ok = db.set_pin(st.session_state.pending_reg, pin1)
                        if ok:
                            st.session_state.student_logged_in = st.session_state.pending_reg
                            st.session_state.show_set_pin      = False
                            st.session_state.pending_reg       = ""
                            st.rerun()
                        else:
                            st.error("⚠️ Could not save PIN. Please try again.")
        else:
            if st.session_state.reg_success_msg:
                st.success(st.session_state.reg_success_msg)
                st.session_state.reg_success_msg = ""

            st.subheader("🎓 Student Login")
            login_reg = st.text_input("Registration Number", placeholder="e.g., 25/U/0000/PS").strip().upper()
            login_pin = st.text_input("PIN", type="password", max_chars=6, placeholder="Enter your 4-digit PIN")
            c1, c2 = st.columns(2)
            with c1: login_btn = st.button("Log In",              use_container_width=True)
            with c2: reg_btn   = st.button("Register New Account", use_container_width=True)

            if st.button("Forgot PIN?", type="secondary"):
                st.session_state.show_forgot_pin = True
                st.rerun()

            if reg_btn:
                st.session_state.show_reg_form = True
                st.rerun()

            if login_btn:
                if not login_reg:
                    st.warning("Please enter your Registration Number.")
                elif not login_pin:
                    st.warning("Please enter your PIN.")
                else:
                    with st.spinner("Verifying..."):
                        result = db.verify_student(login_reg, login_pin)

                    if result.get("status") == "success":
                        if not result.get("pin_set", True):
                            st.session_state.pending_reg  = login_reg
                            st.session_state.show_set_pin = True
                            st.rerun()
                        else:
                            st.session_state.student_logged_in = login_reg
                            with st.spinner("Loading your session..."):
                                try:
                                    history = db.get_chat_history(login_reg, limit=20)
                                    st.session_state.ai_chat_history = [
                                        {"role": h["role"], "content": h["message"]}
                                        for h in history
                                    ]
                                except Exception as e:
                                    print(f"[student.py] Could not load chat history: {e}")
                                    st.session_state.ai_chat_history = []
                            st.rerun()
                    else:
                        msg = result.get("message", "Login failed")
                        st.error(f"⚠️ {msg}")
                        if "PIN" in msg or "not found" in msg:
                            st.caption("Forgot your PIN? Click 'Forgot PIN?' above to reset it.")

    # -------------------------------------------------------------
    # REGISTRATION FLOW
    # -------------------------------------------------------------
    if st.session_state.show_reg_form:
        st.subheader("📝 Create New Student Account")

        try:
            dept_options = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
        except Exception as e:
            st.error(f"Could not load departments: {e}")
            dept_options = {"Mechanical Engineering (MEC)": "MEC", "Electrical Engineering (ELE)": "ELE"}

        dept_label    = st.selectbox("Department", list(dept_options.keys()), key="reg_dept_select")
        selected_dept = dept_options[dept_label]
        year          = st.selectbox("Year of Study", YEARS, key="reg_year_select")

        try:
            courses = dept_courses(selected_dept)
        except:
            courses = ["BMEC", "BBPE", "BWIE"]

        code = st.selectbox("Course Code", courses, key="reg_course_select")

        with st.form("register_form", clear_on_submit=False):
            name     = st.text_input("Full Name", placeholder="e.g., Obema Kelly")
            reg      = st.text_input("Registration Number", placeholder="25/U/0000/PS").strip().upper()
            contact  = st.text_input("Contact Info", placeholder="e.g., 0744215379 or +256744215379",
                                     help="Used to verify your identity if you forget your PIN.")
            email    = st.text_input("Email Address", placeholder="e.g., obema.kelly@gmail.com",
                                     help="Required for notice alerts.")
            reg_photo = st.file_uploader("Profile Photo (optional)", type=["png", "jpg", "jpeg", "webp"],
                                        help="Attach a clear passport or portrait photo")
            pin1     = st.text_input("Set a PIN (4 digits)", type="password", max_chars=6,
                                     placeholder="e.g. 1234")
            pin2     = st.text_input("Confirm PIN",           type="password", max_chars=6)
            st.caption("ℹ️ You can change your profile picture anytime in your Profile tab.")
            submit   = st.form_submit_button("Register", use_container_width=True, type="primary")

            if submit:
                def normalize_ug_phone(raw: str) -> str:
                    if not raw:
                        return ""
                    raw = raw.strip()
                    digits = "".join(c for c in raw if c.isdigit())
                    if raw.startswith("+256") and len(digits) == 12:
                        return "+" + digits
                    if digits.startswith("256") and len(digits) == 12:
                        return "+" + digits
                    if digits.startswith("0") and len(digits) == 10:
                        return "+256" + digits[1:]
                    return raw

                contact_clean = normalize_ug_phone(contact)

                contact_invalid = not contact_clean.startswith("+256") or len(contact_clean) != 13

                errors = []
                if not name or not reg:
                    errors.append("Name and Registration Number are required.")
                if not email or not email.strip():
                    errors.append("Email Address is required.")
                elif not is_valid_email(email.strip()):
                    errors.append("Please enter a valid email address.")
                if contact_invalid:
                    errors.append("Contact number must be a valid Ugandan number (e.g. 0744215379 or +256744215379).")
                if not pin1:
                    errors.append("Please set a PIN.")
                if pin1 and (not pin1.isdigit() or len(pin1) < 4):
                    errors.append("PIN must be at least 4 digits (numbers only).")
                if pin1 and pin1 != pin2:
                    errors.append("PINs do not match.")

                if errors:
                    for err in errors:
                        st.error(f"⚠️ {err}")
                else:
                    try:
                        with st.spinner("Registering..."):
                            avatar_bytes = reg_photo.getvalue() if reg_photo else None
                            avatar_mime = reg_photo.type if reg_photo else "image/jpeg"
                            result = db.register_student(
                                name=name,
                                reg=reg,
                                code=code,
                                contact=contact_clean,
                                dept=selected_dept,
                                year=year,
                                email=email.strip(),
                                avatar_bytes=avatar_bytes,
                                avatar_mime=avatar_mime
                            )

                            if isinstance(result, dict) and result.get("status") == "success":
                                db.set_pin(reg, pin1)
                                cached_fetch_roster.clear()
                                st.session_state.show_reg_form = False
                                st.session_state.reg_success_msg = "✅ Account created! Please log in."
                                st.success(st.session_state.reg_success_msg)
                                st.rerun()
                            else:
                                error_msg = result.get("message", "Registration failed. Please try again.")
                                st.error(f"⚠️ {error_msg}")
                    except Exception as e:
                        st.error(f"⚠️ Registration error: {str(e)}")

        if st.button("← Back to Login"):
            st.session_state.show_reg_form = False
            st.rerun()

    # -------------------------------------------------------------
    # LOGGED-IN VIEW
    # -------------------------------------------------------------
    if not st.session_state.student_logged_in:
        return

    if df_profiles.empty or st.session_state.student_logged_in not in df_profiles["Reg Number"].values:
        cached_fetch_roster.clear()
        st.error("⚠️ Could not load your profile. Please refresh or try logging in again.")
        st.stop()

    student_data = df_profiles[df_profiles["Reg Number"] == st.session_state.student_logged_in].iloc[0]

    s_name   = student_data["Student Name"]
    s_reg    = st.session_state.student_logged_in
    s_course = student_data.get("Course Code", "N/A")
    s_group  = student_data.get("Assigned Group", "Not Assigned")
    s_avatar = str(student_data.get("Avatar", student_data.get("avatar_url", "")))

    s_dept = str(next((student_data.get(c) for c in ["Department", "department", "dept"] if student_data.get(c)), "MEC"))
    s_year = str(next((student_data.get(c) for c in ["Year", "year"] if student_data.get(c)), "Year 1"))
    s_dept_name = dept_name(s_dept)
    primary     = dept_color(s_dept)
    light       = dept_light(s_dept)

    dept_anns   = cached_fetch_announcements(dept=s_dept, year=s_year)
    global_anns = cached_fetch_announcements(dept="ALL",  year="ALL")
    all_anns    = dept_anns + [a for a in global_anns if a not in dept_anns]

    materials_list   = cached_fetch_materials(dept=s_dept, year=s_year)
    my_rep_replies   = cached_fetch_rep_replies(reg_number=s_reg, dept=s_dept, year=s_year)
    unread_rep_count = sum(1 for r in my_rep_replies if r.get("read_status", "Unread").lower() == "unread")

    unread        = []
    urgent_unread = []
    for ann in all_anns:
        ann_id = (ann.get("id", ann.get("text", ""))[:20] if isinstance(ann, dict) else str(ann)[:20])
        if ann_id not in st.session_state.read_announcements:
            unread.append(ann)
            if isinstance(ann, dict) and ann.get("priority", "").lower() == "urgent":
                urgent_unread.append(ann)
    unread_count = len(unread)

    # Welcome Banner with Profile Photo
    banner_avatar_html = render_avatar_html(s_avatar, s_name, size=52, color="white", light="rgba(255,255,255,0.25)")
    st.markdown(f"""
    <div class="welcome-banner">
        <div style="display:flex;align-items:center;gap:16px;">
            {banner_avatar_html}
            <div style="flex:1;">
                <div style="font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;
                    opacity:0.85;margin-bottom:2px;">{s_dept_name} · {s_year}</div>
                <h2 style="margin:0;">👋 Welcome, {s_name}!</h2>
            </div>
        </div>
        <div class="pill-strip" style="margin-top:12px;">
            <span class="pill">🆔 {s_reg}</span>
            <span class="pill">📚 {s_course}</span>
            <span class="pill">👥 {s_group}</span>
            <span class="pill">🏛️ {s_dept}</span>
            <span class="pill">🎓 {s_year}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_notification_bell(s_reg, primary=primary)

    # Activity Strip
    items = ""
    if unread_count:
        items += f'<div style="font-size:0.88rem;color:#475569;padding:3px 0;">• &nbsp;{unread_count} unread announcement(s)</div>'
    if materials_list:
        items += f'<div style="font-size:0.88rem;color:#475569;padding:3px 0;">• &nbsp;{len(materials_list)} material(s) available</div>'
    if unread_rep_count:
        items += f'<div style="font-size:0.88rem;color:#475569;padding:3px 0;">• &nbsp;{unread_rep_count} new reply from Class Rep</div>'

    if items:
        st.markdown(f"""
        <div class="activity-strip">
            <div style="font-size:0.75rem;font-weight:700;letter-spacing:1px;
                text-transform:uppercase;color:{primary};margin-bottom:8px;">📌 Recent Activity</div>
            {items}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ Everything is up to date.")

    notices_label = f"📢 Notices ({unread_count})" if unread_count else "📢 Notices"
    replies_label = f"💬 Replies ({unread_rep_count})" if unread_rep_count else "💬 Replies"

    notices_total_unread = (unread_count + unread_rep_count)
    notices_hub_label = f"💬 Notices & Chat ({notices_total_unread})" if notices_total_unread else "💬 Notices & Chat"

    
    # Screen state default
    if "student_screen" not in st.session_state:
        st.session_state.student_screen = "dashboard"

    # Sidebar Navigation Menu
    with st.sidebar:
        st.markdown('<div style="font-size:0.68rem;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;font-weight:700;margin:12px 0 8px 0;">STUDENT WORKSPACE</div>', unsafe_allow_html=True)
        nav_options = [
            ("dashboard", "🏠 Dashboard"),
            ("ai_tutor",   "🤖 AI Study Tutor"),
            ("materials",  f"📁 Course Materials ({len(materials_list)})"),
            ("timetable",  "📅 Class Timetable"),
            ("notices",    f"📢 Noticeboard ({unread_count})" if unread_count else "📢 Noticeboard"),
            ("messages",   f"💬 Rep Inquiries ({unread_rep_count})" if unread_rep_count else "✉️ Messages & Chat"),
            ("group",      f"👥 My Group ({s_group})"),
            ("profile",    "👤 Profile & Security"),
            ("features",   "🧩 Slot Features"),
        ]
        for n_key, n_label in nav_options:
            is_active = (st.session_state.student_screen == n_key)
            if st.button(n_label, key=f"s_nav_btn_{n_key}", use_container_width=True, type="primary" if is_active else "secondary"):
                if st.session_state.student_screen != n_key:
                    st.session_state.student_screen = n_key
                    st.rerun()

    # -------------------------------------------------------------
    # SCREEN ROUTING & RENDERING
    # -------------------------------------------------------------
    screen = st.session_state.student_screen

    # Render Sub-Screen Header if not on Dashboard
    if screen != "dashboard":
        screen_titles = {
            "ai_tutor":   ("🤖", "AI Study Tutor", "Interactive AI Assistant & Lecture Research"),
            "materials":  ("📁", "Course Materials", "Lecture notes, slides, handouts and past papers"),
            "timetable":  ("📅", "Class Timetable", "Weekly schedule, lecture halls and instructor details"),
            "notices":    ("📢", "Class Noticeboard", "Official class announcements and university notices"),
            "messages":   ("✉️", "Class Rep Inquiries & Replies", "Direct communication with your class representative"),
            "group":      ("👥", "My Study Group", "Assigned project group and peer contact information"),
            "profile":    ("👤", "Profile & Security Settings", "Manage contact info, password PIN, and portrait photo"),
            "features":   ("🧩", "Class Custom Features", "Interactive department modules and custom tools"),
        }
        s_icon, s_title, s_desc = screen_titles.get(screen, ("📌", "Student View", ""))
        
        top_c1, top_c2 = st.columns([1, 4])
        with top_c1:
            if st.button("← Back to Dashboard", use_container_width=True, key=f"back_btn_{screen}"):
                st.session_state.student_screen = "dashboard"
                st.rerun()
        with top_c2:
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;background:white;border:1px solid #e2e8f0;border-radius:12px;padding:8px 16px;box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.3rem;">{s_icon}</span>
                    <div>
                        <div style="font-size:1.05rem;font-weight:800;color:#0f172a;line-height:1.2;">{s_title}</div>
                        <div style="font-size:0.72rem;color:#64748b;">{s_desc}</div>
                    </div>
                </div>
                <div style="background:#ecfdf5;color:#059669;border:1px solid #a7f3d0;border-radius:20px;padding:2px 10px;font-size:0.72rem;font-weight:700;">
                    ● Full Screen
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('<div style="margin-bottom:14px;"></div>', unsafe_allow_html=True)

    # 1. DASHBOARD SCREEN
    if screen == "dashboard":
        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_card("Unread Notices", unread_count,        "📢")
        with c2: metric_card("Course Materials", len(materials_list), "📚")
        with c3: metric_card("Study Group",     s_group,             "👥")
        with c4: metric_card("Academic Year",   s_year,              "🎓")

        st.markdown('<div style="margin:16px 0 8px 0;font-size:0.8rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#64748b;">⚡ QUICK LAUNCH WORKSPACE</div>', unsafe_allow_html=True)
        
        # Modern Streamlined Action Grid
        grid_col1, grid_col2 = st.columns(2)
        with grid_col1:
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:6px;box-shadow:0 1px 3px rgba(15,23,42,0.03);">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">🤖</div>
                    <div>
                        <div style="font-size:0.92rem;font-weight:700;color:#0f172a;">AI Study Tutor</div>
                        <div style="font-size:0.74rem;color:#64748b;">Interactive lecture Q&A & lab report writer</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open AI Study Tutor →", key="dash_open_ai", use_container_width=True, type="primary"):
                st.session_state.student_screen = "ai_tutor"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:6px;margin-top:10px;box-shadow:0 1px 3px rgba(15,23,42,0.03);">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">📁</div>
                    <div>
                        <div style="font-size:0.92rem;font-weight:700;color:#0f172a;">Course Materials</div>
                        <div style="font-size:0.74rem;color:#64748b;">{len(materials_list)} lecture notes & past papers</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Course Materials →", key="dash_open_mat", use_container_width=True):
                st.session_state.student_screen = "materials"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:6px;margin-top:10px;box-shadow:0 1px 3px rgba(15,23,42,0.03);">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">📢</div>
                    <div>
                        <div style="font-size:0.92rem;font-weight:700;color:#0f172a;">Noticeboard</div>
                        <div style="font-size:0.74rem;color:#64748b;">{unread_count} unread announcement(s)</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Noticeboard →", key="dash_open_notices", use_container_width=True):
                st.session_state.student_screen = "notices"
                st.rerun()

        with grid_col2:
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:6px;box-shadow:0 1px 3px rgba(15,23,42,0.03);">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">📅</div>
                    <div>
                        <div style="font-size:0.92rem;font-weight:700;color:#0f172a;">Class Timetable</div>
                        <div style="font-size:0.74rem;color:#64748b;">Weekly lecture schedule & room locations</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Timetable →", key="dash_open_tt", use_container_width=True):
                st.session_state.student_screen = "timetable"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:6px;margin-top:10px;box-shadow:0 1px 3px rgba(15,23,42,0.03);">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">💬</div>
                    <div>
                        <div style="font-size:0.92rem;font-weight:700;color:#0f172a;">Message Class Rep</div>
                        <div style="font-size:0.74rem;color:#64748b;">Inquiries & responses ({unread_rep_count} new reply)</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Rep Messages →", key="dash_open_msg", use_container_width=True):
                st.session_state.student_screen = "messages"
                st.rerun()

            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:6px;margin-top:10px;box-shadow:0 1px 3px rgba(15,23,42,0.03);">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">👥</div>
                    <div>
                        <div style="font-size:0.92rem;font-weight:700;color:#0f172a;">My Study Group</div>
                        <div style="font-size:0.74rem;color:#64748b;">Assigned Group: {s_group}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("View Study Group →", key="dash_open_grp", use_container_width=True):
                st.session_state.student_screen = "group"
                st.rerun()

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        if urgent_unread:
            st.markdown("### 🚨 Urgent — Action Required")
            for uidx, ann in enumerate(urgent_unread):
                ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
                ann_id   = ann.get("id", ann_text[:20]) if isinstance(ann, dict) else ann_text[:20]
                st.markdown(f'<div class="ann-card urgent"><span class="ann-badge badge-urgent">🚨 URGENT</span><div>{ann_text}</div></div>', unsafe_allow_html=True)
                if st.button("Mark as Read", key=f"home_read_{uidx}"):
                    st.session_state.read_announcements.append(ann_id)
                    st.rerun()
        normal_unread = [a for a in unread if a not in urgent_unread]
        if normal_unread:
            st.markdown("### 📢 Latest Notice")
            ann      = normal_unread[0]
            ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
            st.markdown(f'<div class="ann-card"><span class="ann-badge badge-normal">NOTICE</span><div>{ann_text}</div></div>', unsafe_allow_html=True)
            if len(normal_unread) > 1:
                st.caption(f"+ {len(normal_unread)-1} more in Noticeboard")

    # 2. AI STUDY TUTOR (FULL SCREEN)
    elif screen == "ai_tutor":

        from ai_engine import extract_pdf_text, generate_image
        
        # History & Action controls
        col_h1, col_h2, col_h3 = st.columns([5, 2, 2])
        with col_h1:
            st.markdown("""
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="font-size:1.4rem;">🤖</div>
                <div>
                    <div style="font-size:1.15rem;font-weight:800;color:#0f172a;line-height:1.2;">AI Study Assistant</div>
                    <div style="font-size:0.75rem;color:#64748b;">Powered by Gemini & Course Database</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_h2:
            if st.button("📜 History", use_container_width=True, help="View your chat history"):
                st.session_state["show_ai_history"] = not st.session_state.get("show_ai_history", False)
                st.rerun()
        with col_h3:
            if st.button("🗑️ Clear Chat", use_container_width=True, help="Clear active conversation"):
                st.session_state.ai_chat_history = []
                st.session_state.ai_summary_shown = False
                st.session_state.ai_summary_text = ""
                try:
                    db.clear_chat_history(s_reg)
                except Exception:
                    pass
                st.success("Chat cleared!")
                st.rerun()

        if st.session_state.get("show_ai_history", False):
            with st.expander("📜 Your Chat History", expanded=True):
                history = db.get_chat_history(s_reg, limit=30)
                if history:
                    st.caption(f"Showing last {len(history)} messages")
                    col_exp1, col_exp2 = st.columns([1, 3])
                    with col_exp1:
                        df_hist = pd.DataFrame(history)
                        st.download_button(
                            label="⬇️ Export CSV",
                            data=df_hist.to_csv(index=False),
                            file_name=f"chat_history_{s_reg}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with col_exp2:
                        if st.button("🗑️ Delete Server History", use_container_width=True, type="secondary"):
                            if db.clear_chat_history(s_reg):
                                st.session_state.ai_chat_history = []
                                st.session_state["show_ai_history"] = False
                                st.success("Chat history deleted from server!")
                                st.rerun()
                    for msg in history:
                        timestamp = msg.get("timestamp", "")
                        role = msg.get("role", "")
                        message = msg.get("message", "")
                        if role == "user":
                            st.markdown(f'<div style="background:#eff6ff;border-radius:10px;padding:8px 12px;margin-bottom:4px;border:1px solid #bfdbfe;"><div style="font-size:0.65rem;color:#1e40af;font-weight:700;">👤 You · {timestamp}</div><div style="font-size:0.88rem;color:#1e293b;margin-top:2px;">{message}</div></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="background:#ffffff;border-radius:10px;padding:8px 12px;margin-bottom:4px;margin-left:15px;border-left:3px solid {primary};border:1px solid #e2e8f0;"><div style="font-size:0.65rem;color:#64748b;font-weight:700;">🤖 AI · {timestamp}</div><div style="font-size:0.88rem;color:#0f172a;margin-top:2px;">{message}</div></div>', unsafe_allow_html=True)
                else:
                    st.info("No chat history yet.")
                if st.button("Close History Drawer", use_container_width=True):
                    st.session_state["show_ai_history"] = False
                    st.rerun()

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        def build_student_context():
            today     = datetime.now().strftime("%A, %d %B %Y")
            tomorrow  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][(datetime.now().weekday() + 1) % 7]
            ann_lines = "".join([f"  [{ann.get('priority','Normal')}] {ann.get('timestamp','')} — {ann.get('text','')[:200]}\n" for ann in all_anns[:15] if isinstance(ann, dict)])
            mat_lines = "".join([f"  - {m.get('name','')} (URL: {m.get('url','')})\n" for m in materials_list[:20]])
            return f"""=== TODAY ===
{today}
Tomorrow: {tomorrow}

=== STUDENT PROFILE ===
Name: {s_name}
Reg Number: {s_reg}
Department: {s_dept_name} ({s_dept})
Year: {s_year}
Course Code: {s_course}
Group: {s_group}

=== CLASS ANNOUNCEMENTS ===
{ann_lines if ann_lines else "  No announcements yet."}

=== AVAILABLE MATERIALS ===
{mat_lines if mat_lines else "  No materials uploaded yet."}"""

        ai_mode = st.radio(
            "Mode:", ["💬 Class Assistant", "📚 Study Material", "🖼️ Image Q&A", "📄 Report Writer"],
            horizontal=True, key="ai_mode_select"
        )



        # Study Material Mode
        if ai_mode == "📚 Study Material":
            st.markdown(f'<div class="msg-info-card">📚 Select a course material for AI-powered help.</div>', unsafe_allow_html=True)
            mat_names     = ["— No material (general Q&A) —"] + [m.get("name", "") for m in materials_list]
            selected_name = st.selectbox("Select a course material:", mat_names)

            if selected_name != "— No material (general Q&A) —":
                sel_mat = next((m for m in materials_list if m.get("name") == selected_name), None)
                if sel_mat:
                    file_url  = sel_mat.get("url", "")
                    file_name = sel_mat.get("name", "")
                    if st.session_state.ai_selected_file != file_name:
                        st.session_state.ai_selected_file = file_name
                        st.session_state.ai_summary_shown = False
                        st.session_state.ai_summary_text  = ""
                        st.session_state.ai_chat_history  = []
                        with st.spinner("📖 Reading material..."):
                            st.session_state.ai_pdf_text = extract_pdf_text(file_url, file_name)
                    if not st.session_state.ai_summary_shown:
                        with st.spinner("Generating summary..."):
                            summary = ai_study.summarize_material(st.session_state.ai_pdf_text, file_name, student_reg=s_reg)
                        st.session_state.ai_summary_text  = summary
                        st.session_state.ai_summary_shown = True

                    if st.session_state.get("ai_summary_text"):
                        st.markdown(f'<div class="ann-card"><span class="ann-badge badge-normal">SUMMARY</span><div>{st.session_state.ai_summary_text}</div></div>', unsafe_allow_html=True)

        # Image Q&A Mode
        elif ai_mode == "🖼️ Image Q&A":
            st.markdown('''<div class="msg-info-card">
                📸 Upload a photo — diagram, circuit schematic, textbook page, or handwritten problem — and ask the AI Tutor for a full step-by-step breakdown.
            </div>''', unsafe_allow_html=True)

            uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "webp"], key="vision_qa_upload")
            if uploaded_image:
                col_img1, col_img2 = st.columns([1, 2])
                with col_img1:
                    st.image(uploaded_image, caption=uploaded_image.name, use_container_width=True)
                with col_img2:
                    image_question = st.text_area(
                        "What do you want to know about this image? (optional)",
                        placeholder="e.g. Explain this diagram, solve this equation, or summarize these notes...",
                        height=100,
                        key="vision_qa_question"
                    )
                    if st.button("🔍 Analyze Image with AI Tutor", use_container_width=True, type="primary"):
                        q = image_question.strip() if image_question.strip() else "Analyze and explain this image in detail."
                        with st.spinner("AI Tutor is analyzing the image and working through solutions..."):
                            answer = ai_study.ask_about_image(
                                image_bytes=uploaded_image.getvalue(),
                                mime_type=uploaded_image.type or "image/png",
                                question=q,
                                chat_history=st.session_state.ai_chat_history,
                                student_reg=s_reg
                            )
                        st.session_state.ai_chat_history.append({"role": "user", "content": f"🖼️ [Image: {uploaded_image.name}] {q}"})
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": answer})
                        st.session_state["last_image_analysis"] = answer
                        st.rerun()

            if st.session_state.get("last_image_analysis"):
                st.markdown(f'''<div class="ann-card" style="border-left-color:#1e40af;margin-top:16px;">
                    <span class="ann-badge badge-normal">LATEST IMAGE ANALYSIS</span>
                    <div style="margin-top:10px;line-height:1.6;">''' + st.session_state["last_image_analysis"] + '''</div>
                </div>''', unsafe_allow_html=True)

        # Report Writer Mode
        elif ai_mode == "📄 Report Writer":
            st.markdown('''<div class="msg-info-card">
                📝 Describe your report and AI will write it for you with proper university formatting.
            </div>''', unsafe_allow_html=True)

            report_mode = st.radio("How would you like to start?", ["✍️ Write from scratch", "📤 Upload my draft"], horizontal=True, key="report_mode_select")
            draft_text = ""
            if report_mode == "📤 Upload my draft":
                uploaded_draft = st.file_uploader("Upload your draft (PDF or TXT)", type=["pdf", "txt"], key="report_draft_upload")
                if uploaded_draft:
                    if uploaded_draft.type == "application/pdf":
                        import tempfile, os
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(uploaded_draft.read())
                            tmp_path = tmp.name
                        try:
                            draft_text = extract_pdf_text(f"file://{tmp_path}", uploaded_draft.name)
                        except:
                            draft_text = ""
                        os.unlink(tmp_path)
                    else:
                        draft_text = uploaded_draft.read().decode("utf-8", errors="ignore")
                    if draft_text:
                        st.success(f"Draft loaded — {len(draft_text.split())} words detected.")

            include_images = st.checkbox("Generate and include illustrative images in this report", value=False)
            num_images  = 0
            image_style = "Clean 2D Engineering Drawing"
            if include_images:
                num_images = st.slider("How many images to generate?", 1, 4, 2)
                image_style = st.selectbox(
                    "Image style",
                    ["Clean 2D Engineering Drawing", "Technical Pencil Sketch", "3D Realistic Render", "Blueprint Schematic"]
                )

            with st.form("report_writer_form", clear_on_submit=False):
                report_topic = st.text_input("Report title / topic", placeholder="e.g. Effect of Temperature on Viscosity of Engine Oil")
                report_type = st.selectbox("Report type", ["Lab Report", "Research Report", "Technical Report", "Assignment Essay", "Case Study", "Project Proposal"])
                extra_instructions = st.text_area("Additional instructions (optional)", height=80)
                word_count = st.select_slider("Approximate word count", options=[500, 800, 1000, 1500, 2000, 2500, 3000], value=1000)
                generate_btn = st.form_submit_button("Generate Report", use_container_width=True, type="primary")

                if generate_btn:
                    if not report_topic.strip():
                        st.warning("Please enter a report topic.")
                    else:
                        image_instructions = (
                            f"- MANDATORY: Insert exactly {num_images} tags formatted like [IMAGE: detailed technical schematic description] between paragraphs.\n"
                            if (include_images and num_images > 0) else "- Do NOT include [IMAGE: ...] tags. Text-only report."
                        )
                        prompt = f"""You are an expert academic writer for a {s_dept} engineering student at Makerere University.
Write a complete, well-structured {report_type} on:
TOPIC: {report_topic}

Requirements:
- Word count: ~{word_count} words
- Department: {s_dept} | Year: {s_year}
- Date: {datetime.now().strftime("%B %d, %Y")}
- Standard sections: Abstract, Introduction, Methodology, Results/Analysis, Discussion, Conclusion.
{f"- Extra instructions: {extra_instructions}" if extra_instructions.strip() else ""}
{image_instructions}"""

                        with st.spinner("Writing report..."):
                            report_content = ai_study.ask_ai(question=prompt, chat_history=[], student_reg=s_reg)

                        if include_images and num_images > 0:
                            image_markers = _re.findall(r"\[IMAGE:\s*(.+?)\]", report_content)[:num_images]
                        else:
                            report_content = _re.sub(r"\[IMAGE:\s*.+?\]\n?", "", report_content)
                            image_markers = []

                        generated_images = {}
                        if image_markers:
                            with st.spinner(f"Generating {len(image_markers)} image(s)..."):
                                for marker_prompt in image_markers:
                                    img_bytes = generate_image(prompt=f"{marker_prompt}, {image_style}", width=900, height=600)
                                    if img_bytes:
                                        generated_images[marker_prompt] = img_bytes

                        st.session_state["generated_report"]        = report_content
                        st.session_state["generated_report_title"]  = report_topic
                        st.session_state["generated_report_images"] = generated_images
                        st.rerun()

            # Display and export generated report
            if st.session_state.get("generated_report"):
                report_content = st.session_state["generated_report"]
                report_title   = st.session_state.get("generated_report_title", "Report")
                report_images  = st.session_state.get("generated_report_images", {})

                st.markdown("---")
                st.markdown(f"### 📄 {report_title}")

                parts = _re.split(r"(\[IMAGE:\s*.+?\])", report_content)
                for part in parts:
                    m = _re.match(r"\[IMAGE:\s*(.+?)\]", part)
                    if m and m.group(1) in report_images:
                        st.image(report_images[m.group(1)], caption=m.group(1))
                    elif part.strip():
                        st.markdown(part)

                # ---------------------------------------------------------
                # ROBUST, CRASH-PROOF PDF EXPORTER
                # ---------------------------------------------------------
                def _pdf_safe(text: str) -> str:
                    """Sanitize unicode to latin-1 / ASCII safe characters."""
                    replacements = {
                        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                        "\u2013": "-", "\u2014": "--", "\u2026": "...", "\u2022": "*",
                        "\u00b0": " deg", "\u00b1": "+/-", "\u00d7": "x", "\u00f7": "/",
                        "\u03bc": "u", "\u03a9": "Ohm", "\u0394": "Delta", "\u03c0": "pi",
                        "\u2192": "->", "\u2190": "<-", "\u2264": "<=", "\u2265": ">=",
                        "\u2248": "~", "\u2260": "!=", "\u2070": "^0", "\u00b9": "^1",
                        "\u00b2": "^2", "\u00b3": "^3", "\u2074": "^4", "\u00a9": "(c)",
                    }
                    for k, v in replacements.items():
                        text = text.replace(k, v)

                    clean_chars = []
                    for ch in text:
                        code = ord(ch)
                        if code < 256 and code not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 14, 15):
                            clean_chars.append(ch)
                        elif code > 0x1F000:
                            continue
                        else:
                            clean_chars.append("?")
                    return "".join(clean_chars)

                def _build_report_pdf(title, content, images, student_name, reg_no, dept, year):
                    from fpdf import FPDF
                    from io import BytesIO

                    pdf = FPDF(format="A4")
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.set_margins(left=15, top=15, right=15)
                    pdf.add_page()

                    # Effective usable page width (safely prevents "Not enough horizontal space" errors)
                    page_width = pdf.epw if hasattr(pdf, 'epw') else (pdf.w - pdf.l_margin - pdf.r_margin)

                    # Title
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(page_width, 8, _pdf_safe(title), align="L")
                    pdf.ln(2)

                    # Metadata
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(90, 90, 90)
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(page_width, 6, _pdf_safe(f"{student_name} | {reg_no} | {dept} - {year}"), align="L")
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(page_width, 6, _pdf_safe(f"Generated: {datetime.now().strftime('%B %d, %Y')}"), align="L")
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(4)

                    parts = _re.split(r"(\[IMAGE:\s*.+?\])", content)
                    for part in parts:
                        m = _re.match(r"\[IMAGE:\s*(.+?)\]", part)
                        if m:
                            img_prompt = m.group(1)
                            img_bytes = images.get(img_prompt)
                            if img_bytes:
                                try:
                                    pdf.set_x(pdf.l_margin)
                                    pdf.image(BytesIO(img_bytes), w=min(160, page_width))
                                    pdf.ln(3)
                                    pdf.set_font("Helvetica", "I", 9)
                                    pdf.set_text_color(100, 100, 100)
                                    pdf.set_x(pdf.l_margin)
                                    pdf.multi_cell(page_width, 5, _pdf_safe(f"Figure: {img_prompt}"), align="C")
                                    pdf.set_text_color(0, 0, 0)
                                    pdf.ln(4)
                                except Exception as img_err:
                                    print(f"[report_pdf] image embed error: {img_err}")
                            continue

                        for raw_line in part.split("\n"):
                            line = raw_line.strip()
                            if not line:
                                pdf.ln(2)
                                continue

                            line = line.replace("|", "  ").strip()
                            if not line or set(line) <= {"-", " ", "="}:
                                continue

                            if line.startswith("### "):
                                pdf.set_font("Helvetica", "B", 12)
                                text = line[4:]
                                h = 7
                            elif line.startswith("## "):
                                pdf.set_font("Helvetica", "B", 13)
                                text = line[3:]
                                h = 8
                            elif line.startswith("# "):
                                pdf.set_font("Helvetica", "B", 15)
                                text = line[2:]
                                h = 9
                            else:
                                pdf.set_font("Helvetica", "", 10)
                                text = line
                                h = 5.5

                            clean_text = _pdf_safe(text)
                            if clean_text.strip():
                                try:
                                    pdf.set_x(pdf.l_margin)
                                    pdf.multi_cell(page_width, h, clean_text, align="L")
                                except Exception as line_err:
                                    print(f"[report_pdf] skipped problematic line: {line_err}")

                    return bytes(pdf.output())

                pdf_cache_key = f"{report_title}_{len(report_content)}_{len(report_images)}"
                if st.session_state.get("generated_report_pdf_key") != pdf_cache_key:
                    try:
                        st.session_state["generated_report_pdf"] = _build_report_pdf(
                            report_title, report_content, report_images,
                            s_name, s_reg, s_dept, s_year
                        )
                        st.session_state["generated_report_pdf_key"] = pdf_cache_key
                    except Exception as e:
                        st.session_state["generated_report_pdf"] = None
                        st.error(f"⚠️ Could not prepare PDF: {e}")

                pdf_bytes = st.session_state.get("generated_report_pdf")
                safe_filename = _re.sub(r"[^A-Za-z0-9_\-]", "_", report_title.strip())[:60] or "report"
                st.download_button(
                    "⬇️ Download Report as PDF",
                    data=pdf_bytes if pdf_bytes else b"",
                    file_name=f"{safe_filename}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    disabled=not pdf_bytes,
                    key="dl_ai_report"
                )

        # Chat input form for Class Assistant & Study Material modes
        if ai_mode in ("💬 Class Assistant", "📚 Study Material"):
            for turn in st.session_state.ai_chat_history:
                if turn["role"] == "user":
                    st.markdown(f'<div style="background:{light};border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-left:20%;text-align:right;"><div style="font-size:0.78rem;color:{primary};font-weight:600;">You</div><div style="font-size:0.9rem;">{turn["content"]}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background:white;border:1px solid #e2e8f7;border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-right:20%;"><div style="font-size:0.78rem;color:{primary};font-weight:600;">🤖 AI</div><div style="font-size:0.9rem;">{turn["content"]}</div></div>', unsafe_allow_html=True)

            if st.session_state.get("ai_quick_q"):
                quick_q = st.session_state.ai_quick_q
                st.session_state.ai_quick_q = ""
                with st.spinner("Thinking..."):
                    ctx = build_student_context()
                    answer = ai_study.chat_with_context(
                        question=quick_q,
                        chat_history=st.session_state.ai_chat_history,
                        student_context=ctx,
                        pdf_text=st.session_state.ai_pdf_text,
                        file_name=st.session_state.ai_selected_file,
                        student_reg=s_reg
                    )
                st.session_state.ai_chat_history.append({"role": "user", "content": quick_q})
                st.session_state.ai_chat_history.append({"role": "assistant", "content": answer})
                try:
                    db.save_chat_message(s_reg, "user", quick_q)
                    db.save_chat_message(s_reg, "assistant", answer)
                except Exception:
                    pass
                st.rerun()

            with st.form("ai_chat_form", clear_on_submit=True):
                user_question = st.text_area(
                    "Your question:", height=90, label_visibility="collapsed",
                    placeholder="Ask about your timetable, announcements, materials..."
                )
                c1, c2 = st.columns([3, 1])
                with c1: send_btn  = st.form_submit_button("Ask AI", use_container_width=True)
                with c2: clear_btn = st.form_submit_button("Clear",  use_container_width=True)

                if send_btn and user_question.strip():
                    with st.spinner("Thinking..."):
                        if ai_mode == "💬 Class Assistant":
                            ctx = build_student_context()
                            answer = ai_study.chat_with_context(
                                question=user_question.strip(),
                                chat_history=st.session_state.ai_chat_history,
                                student_context=ctx,
                                pdf_text=st.session_state.ai_pdf_text,
                                file_name=st.session_state.ai_selected_file,
                                student_reg=s_reg
                            )
                        else:
                            answer = ai_study.ask_ai(
                                question=user_question.strip(),
                                chat_history=st.session_state.ai_chat_history,
                                pdf_text=st.session_state.ai_pdf_text,
                                file_name=st.session_state.ai_selected_file,
                                student_reg=s_reg
                            )
                    st.session_state.ai_chat_history.append({"role": "user", "content": user_question.strip()})
                    st.session_state.ai_chat_history.append({"role": "assistant", "content": answer})
                    try:
                        db.save_chat_message(s_reg, "user", user_question.strip())
                        db.save_chat_message(s_reg, "assistant", answer)
                    except Exception:
                        pass
                    st.rerun()

                if clear_btn:
                    st.session_state.ai_chat_history  = []
                    st.session_state.ai_summary_shown = False
                    st.session_state.ai_summary_text  = ""
                    try:
                        db.clear_chat_history(s_reg)
                    except Exception:
                        pass
                    st.rerun()

# -------------------------------------------------------------
# TAB 10: FEATURES
# -------------------------------------------------------------

# -------------------------------------------------------------


    # 3. COURSE MATERIALS (FULL SCREEN)
    elif screen == "materials":

        st.markdown("### 📁 Course Materials")
        search   = st.text_input("🔍 Search", placeholder="Search by file name...")
        filtered = [i for i in materials_list if search.lower() in (i.get("name", "") if isinstance(i, dict) else str(i)).lower()]
        if filtered:
            for idx, item in enumerate(filtered):
                file_name = item.get("name", "Unnamed") if isinstance(item, dict) else str(item)
                file_url  = item.get("url", "#") if isinstance(item, dict) else "#"
                ext       = file_name.split(".")[-1].upper() if "." in file_name else "FILE"

                with st.container():
                    c1, c2 = st.columns([6, 1])
                    with c1:
                        st.markdown(
                            f'<div class="mat-row">' +
                            f'<div class="mat-icon {"pdf" if ext=="PDF" else ""}">{ext}</div>' +
                            f'<div><strong>{file_name}</strong></div></div>',
                            unsafe_allow_html=True
                        )
                    with c2:
                        preview_key = f"preview_{idx}_{file_name}"
                        if preview_key not in st.session_state:
                            st.session_state[preview_key] = False
                        if st.button(
                            "👁️ Preview" if not st.session_state[preview_key] else "✖ Close",
                            key=f"prev_btn_{idx}",
                            use_container_width=True
                        ):
                            st.session_state[preview_key] = not st.session_state[preview_key]
                            st.rerun()

                if st.session_state.get(f"preview_{idx}_{file_name}", False):
                    with st.expander(f"Preview: {file_name}", expanded=True):
                        with st.spinner("Loading preview..."):
                            file_data = db.fetch_file_bytes(file_url)

                        if not file_data:
                            st.warning("⚠️ Could not load file for preview.")
                        else:
                            if ext == "PDF":
                                try:
                                    import fitz
                                    doc  = fitz.open(stream=file_data, filetype="pdf")
                                    pages = len(doc)
                                    st.caption(f"📄 {pages} page(s) — PDF document")
                                    page = doc[0]
                                    mat  = fitz.Matrix(1.5, 1.5)
                                    pix  = page.get_pixmap(matrix=mat)
                                    st.image(pix.tobytes("png"), caption="Page 1 preview")
                                    if pages > 1:
                                        st.caption(f"Showing page 1 of {pages}. Download to view all pages.")
                                    doc.close()
                                except Exception:
                                    st.info("Download PDF to view complete document.")
                            elif ext in ("DOCX", "DOC"):
                                try:
                                    from docx import Document
                                    import io
                                    doc = Document(io.BytesIO(file_data))
                                    paras = [p.text for p in doc.paragraphs if p.text.strip()]
                                    st.text_area("Document preview (first 15 paragraphs):", "\n\n".join(paras[:15]), height=250, disabled=True)
                                except Exception:
                                    st.info("Download document to view.")
                            elif ext in ("PNG", "JPG", "JPEG", "GIF", "WEBP"):
                                st.image(file_data, caption=file_name)
                            else:
                                st.info(f"Preview not available for {ext} files. Download to view.")

                        st.markdown("---")
                        st.download_button(
                            label=f"⬇️ Download {file_name}",
                            data=file_data if file_data else b"",
                            file_name=file_name,
                            mime="application/octet-stream",
                            key=f"dl_{idx}_{file_name}",
                            use_container_width=True,
                            type="primary",
                            disabled=not file_data
                        )
                else:
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        file_data_quick = db.fetch_file_bytes(file_url)
                        st.download_button(
                            "⬇️ Download",
                            data=file_data_quick if file_data_quick else b"",
                            file_name=file_name,
                            mime="application/octet-stream",
                            key=f"dl_quick_{idx}_{file_name}",
                            disabled=not file_data_quick
                        )
                st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        else:
            st.info("No materials available for your class yet.")

    # -------------------------------------------------------------
    # TAB 4: MY GROUP
    # -------------------------------------------------------------



    # 4. TIMETABLE (FULL SCREEN)
    elif screen == "timetable":

        st.markdown("### 📅 Class Timetable")
        TT_PALETTE = ["#1a56db","#16a34a","#ea580c","#7c3aed","#dc2626","#db2777","#0d9488","#b45309"]
        TT_LIGHTS = ["#dbeafe","#dcfce7","#ffedd5","#ede9fe","#fee2e2","#fce7f3","#ccfbf1","#fef3c7"]
        def auto_color_s(course_name):
            idx = sum(ord(c) for c in course_name.upper()) % len(TT_PALETTE)
            return TT_PALETTE[idx], TT_LIGHTS[idx]

        timetable = cached_fetch_timetable(dept=s_dept, year=s_year)
        if not timetable:
            st.info("Your Class Rep has not posted a timetable yet.")
        else:
            day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            by_day = {}
            for entry in timetable:
                d = entry.get("day","Other")
                by_day.setdefault(d, []).append(entry)

            view_mode = st.radio("View", ["📋 List", "🔲 Grid"], horizontal=True, label_visibility="collapsed", key="tt_view_mode")
            if view_mode == "📋 List":
                for day in day_order:
                    if day not in by_day or not by_day[day]:
                        continue
                    st.markdown(f'<div style="background:{primary};color:white;border-radius:10px;padding:8px 16px;margin:12px 0 6px 0;font-weight:700;font-size:0.9rem;">📅 {day}</div>', unsafe_allow_html=True)
                    entries = sorted(by_day[day], key=lambda x: x.get("time", ""))
                    for entry in entries:
                        e_color = entry.get("color", "") or auto_color_s(entry.get("course", ""))[0]
                        lect = entry.get("lecturer", "")
                        lect_part = f'<div style="font-size:0.82rem;color:#475569;font-weight:600;margin-top:4px;">👨‍🏫 {lect.title()}</div>' if lect else ""
                        st.markdown(f'<div style="background:white;border-radius:10px;padding:12px 18px;margin-bottom:6px;border:1px solid #e2e8f7;border-left:4px solid {e_color};"><span style="font-weight:800;color:{e_color};min-width:90px;">{entry.get("time","")}</span> <span style="color:#1e293b;font-weight:600;">{entry.get("course","")}</span>{lect_part}</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 8: PROFILE & ATTACH PHOTO
    # -------------------------------------------------------------



    # 5. STUDY GROUP (FULL SCREEN)
    elif screen == "group":

        st.markdown("### 👥 My Course Groups")
        course_groups = db.fetch_course_unit_groups(s_name, dept=s_dept, year=s_year)

        with st.expander("🤖 AI Group Assistant", expanded=False):
            group_query = st.text_input(
                "What would you like to know?",
                placeholder="e.g., What is my thermodynamics group? Which group am I in for mathematics?",
                key="ai_group_query"
            )
            if st.button("Ask AI", key="ai_group_query_btn"):
                if group_query.strip():
                    if course_groups:
                        with st.spinner("Checking your groups..."):
                            answer = ai_study.answer_group_query(s_name, group_query, course_groups)
                            st.info(answer)
                    else:
                        st.warning("No course unit groups assigned yet.")
                else:
                    st.warning("Please enter a question.")

        if course_groups:
            st.markdown("**Your Course Unit Groups:**")
            cols = st.columns(min(3, len(course_groups)) if len(course_groups) > 0 else 1)
            for idx, (course, group) in enumerate(course_groups.items()):
                with cols[idx % len(cols)] if len(cols) > 0 else st.container():
                    st.markdown(f"""
                    <div style="background:{light};border-radius:12px;padding:16px;
                        border:2px solid {primary};text-align:center;margin-bottom:8px;">
                        <div style="font-size:0.75rem;color:{primary};font-weight:700;
                            text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">
                            {course}
                        </div>
                        <div style="font-size:1.5rem;font-weight:900;color:{primary};">
                            {group}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No course unit groups assigned yet.")

        st.markdown("---")
        if s_group and s_group.strip() not in ("", "Unassigned"):
            dept_col = next((c for c in ["Department", "department", "dept"] if c in df_profiles.columns), None)
            year_col = next((c for c in ["Year", "year"] if c in df_profiles.columns), None)
            df_class = df_profiles[(df_profiles[dept_col] == s_dept) & (df_profiles[year_col] == s_year)] if (dept_col and year_col) else df_profiles
            group_members = df_class[df_class["Assigned Group"] == s_group]

            st.markdown(f'<div class="group-banner"><div style="font-size:0.7rem;opacity:0.7;text-transform:uppercase;letter-spacing:2px;">General Project Group</div><div style="font-size:1.5rem;font-weight:900;">{s_group}</div><div style="font-size:0.82rem;opacity:0.85;">{len(group_members)} member(s)</div></div>', unsafe_allow_html=True)

            for _, member in group_members.iterrows():
                m_name   = member["Student Name"]
                m_reg    = member["Reg Number"]
                m_course = member.get("Course Code", "")
                m_avatar = str(member.get("Avatar", member.get("avatar_url", "")))
                is_you   = (m_reg == s_reg)
                you_html = '<span style="background:#dbeafe;color:#1a56db;font-size:0.65rem;font-weight:700;padding:1px 8px;border-radius:10px;margin-left:6px;">You</span>' if is_you else ""

                m_avatar_html = render_avatar_html(m_avatar, m_name, size=42, color=primary, light=light)

                st.markdown(f"""
                <div class="member-card">
                    {m_avatar_html}
                    <div>
                        <div style="font-weight:700;">{m_name}{you_html}</div>
                        <div style="font-size:0.75rem;color:#94a3b8;">{m_course} · {m_reg}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 5: MESSAGE
    # -------------------------------------------------------------

# -------------------------------------------------------------


    # 6. NOTICES (FULL SCREEN)
    elif screen == "notices":

        st.markdown("### 📢 Noticeboard")
        if unread_count:
            st.warning(f"You have **{unread_count} unread** announcement(s)")

        col_s, col_f = st.columns([3, 1])
        with col_s:
            ann_search = st.text_input("🔍 Search notices", placeholder="Search by keyword...", key="ann_search_input")
        with col_f:
            ann_filter = st.selectbox("Filter", ["All", "Unread", "Urgent", "Broadcast"], key="ann_filter_sel")

        display_anns = all_anns
        if ann_search:
            display_anns = [a for a in display_anns if ann_search.lower() in (a.get("text", "") if isinstance(a, dict) else str(a)).lower()]
        if ann_filter == "Unread":
            display_anns = [a for a in display_anns if (a.get("id", a.get("text", ""))[:20] if isinstance(a, dict) else str(a)[:20]) not in st.session_state.read_announcements]
        elif ann_filter == "Urgent":
            display_anns = [a for a in display_anns if isinstance(a, dict) and a.get("priority", "").lower() == "urgent"]
        elif ann_filter == "Broadcast":
            display_anns = [a for a in display_anns if isinstance(a, dict) and a.get("dept", "") == "ALL"]

        st.caption(f"Showing {len(display_anns)} of {len(all_anns)} notices")

        if display_anns:
            for idx, ann in enumerate(display_anns):
                ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
                ann_id   = ann.get("id", ann_text[:20]) if isinstance(ann, dict) else ann_text[:20]
                priority = ann.get("priority", "normal").lower() if isinstance(ann, dict) else "normal"
                is_read  = ann_id in st.session_state.read_announcements
                is_global = isinstance(ann, dict) and ann.get("dept", "") == "ALL"

                badge = "🌍 BROADCAST" if is_global else ("🚨 URGENT" if priority == "urgent" else "NOTICE")
                card_cls = "urgent" if priority == "urgent" and not is_read else ("read" if is_read else "")
                badge_cls = "badge-urgent" if priority == "urgent" else ("badge-read" if is_read else "badge-normal")

                with st.expander(f"{'✅ ' if is_read else '🚨 ' if priority=='urgent' else '📌 '} {ann_text[:60]}..."):
                    st.markdown(f'<div class="ann-card {card_cls}" style="margin:0;"><span class="ann-badge {badge_cls}">{badge}</span><div>{ann_text}</div></div>', unsafe_allow_html=True)
                    if not is_read:
                        if st.checkbox("Mark as Read", key=f"notice_{idx}_{ann_id}"):
                            st.session_state.read_announcements.append(ann_id)
                            st.rerun()
                    else:
                        st.caption("✅ Read")
        else:
            st.info("No announcements yet.")

    # -------------------------------------------------------------
    # TAB 3: MATERIALS
    # -------------------------------------------------------------



    # 7. MESSAGES & REPLIES (FULL SCREEN)
    elif screen == "messages":
        sub_msg_tab, sub_rep_tab = st.tabs([
            "✉️ Message Class Rep",
            f"💬 Rep Replies ({unread_rep_count})" if unread_rep_count else "💬 Rep Replies"
        ])
        with sub_msg_tab:

            st.markdown("### ✉️ Message Class Rep")
            st.markdown(f'<div class="msg-info-card">🔒 <strong>Private & Confidential</strong> — Only your {s_year} Class Rep can see your message.</div>', unsafe_allow_html=True)

            all_feedback = cached_fetch_feedback(dept=s_dept, year=s_year)
            my_messages  = [
                m for m in all_feedback
                if isinstance(m, list) and len(m) >= 5 and str(m[1]).strip().lower() == s_reg.strip().lower()
            ]

            if my_messages:
                st.markdown("#### 📤 Sent Messages")
                for midx, msg in enumerate(my_messages):
                    ts     = str(msg[0])
                    status = str(msg[3])
                    text   = str(msg[4])
                    sc     = "#16a34a" if status.lower() == "reviewed" else "#d4820a"
                    st.markdown(f'<div style="background:white;border-radius:10px;padding:14px;margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {primary};"><div style="font-size:0.78rem;color:#94a3b8;">🕒 {ts} · <span style="color:{sc};font-weight:600;">{status}</span></div><div style="font-size:0.9rem;margin-top:4px;">{text}</div></div>', unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_msg_{midx}"):
                        if db.delete_feedback(ts, s_reg):
                            st.rerun()

            st.markdown("#### ✍️ New Message")
            if st.session_state.get("fb_success_msg"):
                st.success(st.session_state.fb_success_msg)
                st.session_state.fb_success_msg = ""

            with st.expander("🤖 AI Message Assistant", expanded=False):
                ai_topic = st.text_input("What do you need help with?", placeholder="e.g., Workshop attendance, Course materials...", key="msg_ai_topic")
                ai_tone  = st.selectbox("Message tone:", ["Professional", "Friendly", "Urgent", "Inquiry"], key="msg_ai_tone")
                if st.button("Generate Draft with AI", key="ai_draft_msg_btn"):
                    if ai_topic.strip():
                        with st.spinner("Drafting message..."):
                            draft = ai_study.ask_ai(
                                question=f"Draft a {ai_tone.lower()} student message to their Class Rep about: {ai_topic}. Keep it 3-4 sentences, professional, and clear.",
                                chat_history=[],
                                student_reg=s_reg
                            )
                            if draft and not draft.startswith("⚠️"):
                                st.session_state.ai_draft = draft
                                st.success("Draft created! Copied into the message box below.")
                            else:
                                st.error("Could not generate draft.")

            with st.form("student_feedback_form", clear_on_submit=True):
                default_msg = st.session_state.get("ai_draft", "")
                user_msg = st.text_area("Type your message:", value=default_msg, height=140)
                col1, col2 = st.columns([1, 1])
                with col1:
                    submit_fb = st.form_submit_button("Send Private Message", use_container_width=True)
                with col2:
                    if st.form_submit_button("Clear Draft", use_container_width=True):
                        st.session_state.ai_draft = ""
                        st.rerun()

                if submit_fb:
                    if user_msg.strip():
                        if db.submit_feedback(s_reg, s_name, user_msg, dept=s_dept, year=s_year):
                            cached_fetch_feedback.clear()
                            st.session_state.fb_success_msg = "✅ Message delivered to your Class Rep!"
                            st.rerun()
                        else:
                            st.error("⚠️ Submission failed. Please try again.")
                    else:
                        st.warning("Please type a message.")

        # -------------------------------------------------------------
        # TAB 6: REP REPLIES
        # -------------------------------------------------------------


        with sub_rep_tab:

            st.markdown("### 💬 Messages from Class Rep")
            if unread_rep_count:
                st.info(f"🔔 You have **{unread_rep_count} unread** message(s).")
            elif my_rep_replies:
                st.success("✅ All messages read.")

            if my_rep_replies:
                for ridx, reply in enumerate(my_rep_replies):
                    r_time  = reply.get("timestamp",  "N/A")
                    r_rep   = reply.get("rep_name",   "Class Rep")
                    r_msg   = reply.get("message",    "")
                    is_read = reply.get("read_status", "Unread").lower() == "read"

                    with st.container(border=True):
                        st.write(f"**{r_rep}** • {r_time} {'🔴 *NEW*' if not is_read else ''}")
                        st.divider()
                        st.write(r_msg)

                    if not is_read:
                        if st.button("Mark as Read", key=f"rep_read_{ridx}"):
                            if db.mark_rep_reply_read(r_time, s_reg):
                                cached_fetch_rep_replies.clear()
                                st.rerun()
            else:
                st.info("No messages from your Class Rep yet.")

        # -------------------------------------------------------------
        # TAB 7: TIMETABLE
        # -------------------------------------------------------------

    # -------------------------------------------------------------


    # 8. PROFILE & SECURITY (FULL SCREEN)
    elif screen == "profile":

        st.markdown("### 👤 Student Profile")
        s_contact = str(student_data.get("Contact", student_data.get("contact", "")))
        profile_avatar_html = render_avatar_html(s_avatar, s_name, size=76, color=primary, light=light)

        st.markdown(f"""
        <div class="profile-card">
            <div class="profile-avatar-wrap">
                {profile_avatar_html}
                <div>
                    <div style="font-size:1.3rem;font-weight:800;color:#1e293b;">{s_name}</div>
                    <div style="font-size:0.82rem;color:#94a3b8;">{s_reg}</div>
                    <div style="font-size:0.75rem;color:#16a34a;font-weight:700;margin-top:2px;">● Active Student</div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Department</span><span style="font-weight:700;">{s_dept_name}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Year</span><span style="font-weight:700;">{s_year}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Course Code</span><span style="font-weight:700;">{s_course}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Assigned Group</span><span style="font-weight:700;">{s_group}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;font-size:0.88rem;"><span style="color:#94a3b8;">Contact</span><span style="font-weight:700;">{s_contact if s_contact else "Not set"}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 📸 Profile Picture")
        with st.expander("Update Profile Photo", expanded=bool(not s_avatar)):
            new_avatar = st.file_uploader(
                "Upload a portrait or selfie",
                type=["png", "jpg", "jpeg", "webp"],
                key="student_avatar_uploader",
                help="Recommended: Square photo, JPG or PNG format"
            )
            col_av1, col_av2 = st.columns(2)
            with col_av1:
                if st.button("Save Profile Picture", use_container_width=True, type="primary"):
                    if new_avatar:
                        with st.spinner("Uploading and updating photo..."):
                            url = db.upload_student_avatar(
                                s_reg,
                                new_avatar.getvalue(),
                                new_avatar.type or "image/jpeg"
                            )
                        if url:
                            cached_fetch_roster.clear()
                            st.success("✅ Profile picture updated successfully!")
                            st.rerun()
                        else:
                            st.error("⚠️ Failed to upload image. Please try another file.")
                    else:
                        st.warning("Please choose an image file first.")
            with col_av2:
                if s_avatar and st.button("🗑️ Remove Photo", use_container_width=True):
                    with st.spinner("Removing photo..."):
                        db.delete_student_avatar(s_reg)
                    cached_fetch_roster.clear()
                    st.success("Profile photo removed.")
                    st.rerun()

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 🔒 Change PIN")
        if not st.session_state.show_change_pin:
            if st.button("Change My PIN", use_container_width=True):
                st.session_state.show_change_pin = True
                st.rerun()
        else:
            with st.form("change_pin_form", clear_on_submit=True):
                old_pin  = st.text_input("Current PIN",     type="password", max_chars=6)
                new_pin1 = st.text_input("New PIN",         type="password", max_chars=6)
                new_pin2 = st.text_input("Confirm New PIN", type="password", max_chars=6)
                cp1, cp2 = st.columns(2)
                with cp1: save_pin   = st.form_submit_button("Save", use_container_width=True)
                with cp2: cancel_pin = st.form_submit_button("Cancel", use_container_width=True)

                if cancel_pin:
                    st.session_state.show_change_pin = False
                    st.rerun()
                if save_pin:
                    if not old_pin or not new_pin1:
                        st.warning("Please fill in all fields.")
                    elif not new_pin1.isdigit() or len(new_pin1) < 4:
                        st.error("⚠️ PIN must be at least 4 digits.")
                    elif new_pin1 != new_pin2:
                        st.error("⚠️ New PINs do not match.")
                    else:
                        with st.spinner("Verifying..."):
                            check = db.verify_student(s_reg, old_pin)
                        if check.get("status") != "success":
                            st.error("⚠️ Current PIN is incorrect.")
                        else:
                            with st.spinner("Updating..."):
                                ok = db.set_pin(s_reg, new_pin1)
                            if ok:
                                st.success("✅ PIN changed successfully!")
                                st.session_state.show_change_pin = False
                                st.rerun()
                            else:
                                st.error("⚠️ Could not update PIN.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 📱 Update Contact Info")
        if not st.session_state.show_update_contact:
            if st.button("Update My Contact Number", use_container_width=True):
                st.session_state.show_update_contact = True
                st.rerun()
        else:
            with st.form("update_contact_form", clear_on_submit=True):
                new_contact = st.text_input("New Contact Number", placeholder="e.g. 0741234567", value=s_contact)
                c1, c2 = st.columns(2)
                with c1: save_c = st.form_submit_button("Save", use_container_width=True)
                with c2: canc_c = st.form_submit_button("Cancel", use_container_width=True)

                if canc_c:
                    st.session_state.show_update_contact = False
                    st.rerun()

                if save_c:
                    if not new_contact.strip():
                        st.warning("Please enter a contact number.")
                    else:
                        with st.spinner("Updating..."):
                            ok = db.update_contact(s_reg, new_contact.strip())
                        if ok:
                            st.success("✅ Contact updated!")
                            st.session_state.show_update_contact = False
                            cached_fetch_roster.clear()
                            st.rerun()
                        else:
                            st.error("⚠️ Update failed.")

    # -------------------------------------------------------------
    # TAB 9: AI ASSISTANT
    # -------------------------------------------------------------



    # 9. FEATURES (FULL SCREEN)
    elif screen == "features":

        render_student_slots(db, s_reg, s_name, s_dept, s_year, primary, light)

    # -------------------------------------------------------------
    # LOGOUT
    # -------------------------------------------------------------
    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
    if st.button("🚪 Log Out"):
        keys = [
            "student_logged_in", "read_announcements", "open_expanders",
            "show_ai_tab", "ai_chat_history", "ai_pdf_text",
            "ai_selected_file", "ai_summary_shown",
            "confirm_clear_all", "go_to_home"
        ]
        for k in keys:
            if k in st.session_state:
                del st.session_state[k]
        for k in [k for k in st.session_state if k.startswith("ai_last_request_")]:
            del st.session_state[k]
        st.rerun()

