"""
superadmin.py — Super Admin Dashboard.
Full rep management from the UI — no secrets.toml needed.
Sees all departments and years, can broadcast, manage reps, view all data.
"""
import streamlit as st
import pandas as pd
import json

from database import SheetDatabaseManager

from ai_engine import AIAdminAssistant, MasterSuperAdminAI,MasterAIMemorySystem,MasterAIMonitor
from config import get_departments, YEARS, get_dept_codes, dept_color, dept_light, dept_name, COLOUR_PALETTE, load_departments


ADMIN_PRIMARY = "#0f172a"
ADMIN_ACCENT  = "#6d28d9"
ADMIN_LIGHT   = "#ede9fe"


def inject_admin_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html,body,[class*="css"]{{font-family:'Plus Jakarta Sans',sans-serif;}}
    #MainMenu,footer{{visibility:hidden;}}
    .stApp{{background:#F0F4FF;}}
    .admin-banner{{
        background:linear-gradient(135deg,{ADMIN_PRIMARY} 0%,{ADMIN_ACCENT} 100%);
        border-radius:18px;padding:28px 32px;margin-bottom:24px;color:white;
    }}
    .admin-banner h2{{font-size:1.7rem;font-weight:800;margin:0 0 6px 0;color:white;}}
    .dept-card{{
        background:white;border-radius:14px;padding:20px;
        border:1px solid #e2e8f7;border-top:4px solid var(--dc);
        box-shadow:0 2px 8px rgba(0,0,0,0.05);margin-bottom:8px;
    }}
    .admin-pill{{
        display:inline-block;background:rgba(255,255,255,0.15);
        border:1px solid rgba(255,255,255,0.25);border-radius:20px;
        padding:4px 14px;font-size:0.75rem;font-weight:600;color:white;margin-right:6px;
    }}
    .rep-row{{
        background:white;border-radius:12px;padding:14px 18px;margin-bottom:8px;
        border:1px solid #e2e8f7;border-left:4px solid {ADMIN_ACCENT};
        display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
    }}
    .rep-row .rr-info{{font-size:0.9rem;color:#1e293b;font-weight:600;}}
    .rep-row .rr-meta{{font-size:0.78rem;color:#94a3b8;margin-top:2px;}}
    .pro-divider{{height:1px;background:#e2e8f7;margin:22px 0;}}
    /* Pill-style tabs */
    .stTabs [data-baseweb="tab-list"]{{
        gap:4px;background:white;border-radius:12px;padding:4px;
        border:1px solid #e2e8f7;flex-wrap:wrap;
    }}
    .stTabs [data-baseweb="tab"]{{
        border-radius:8px;padding:8px 16px;font-weight:600;
        font-size:0.82rem;color:#64748b;background:transparent;border:none;
    }}
    .stTabs [aria-selected="true"]{{background:{ADMIN_ACCENT} !important;color:white !important;}}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"]{{display:none;}}
    </style>
    """, unsafe_allow_html=True)


def render_slot_configurator(db):
    """Render the Slot Configurator for dynamic features."""
    st.markdown("####  Slot Configurator")
    st.info(
        "Configure dynamic feature slots for **Students** and **Class Reps**. "
        "Each slot can call any saved Function Library function. "
        "Students/Reps see only active slots for their dept+year."
    )

    SLOT_TYPES = ["button", "form", "display", "table"]
    RESULT_TYPES = ["text", "metric", "table", "json"]
    FIELD_TYPES = ["text", "number", "date", "dropdown", "checkbox", "textarea"]
    ICONS = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
    MAX_SLOTS = 10

    audience_choice = st.radio(
        "Configure slots for:", [" Students", " Class Reps"],
        horizontal=True, key="slot_audience_sel"
    )
    audience = "student" if "Students" in audience_choice else "rep"

    dept_opts = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
    d_label = st.selectbox("Department", list(dept_opts.keys()), key="slot_dept_sel")
    sel_dept = dept_opts[d_label]
    sel_year = st.selectbox("Year Group", YEARS, key="slot_year_sel")

    if st.button(" Load Slots", key="load_slots_btn", use_container_width=True):
        st.session_state["slot_cfg_list"] = db.get_all_slots(audience)

    if "slot_cfg_list" not in st.session_state:
        st.session_state["slot_cfg_list"] = db.get_all_slots(audience)

    all_slots = st.session_state.get("slot_cfg_list", [])

    # Filter to selected dept+year
    scope_slots = [
        s for s in all_slots
        if (s.get("dept", "").upper() in ("ALL", sel_dept.upper()))
        and (s.get("year", "") in ("ALL", sel_year))
    ]
    existing_ids = {s.get("slotid", "") for s in scope_slots}

    st.markdown(f"**{len(scope_slots)}/{MAX_SLOTS} slots configured for {sel_dept} · {sel_year}**")
    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

    #  Existing slots 
    for slot in scope_slots:
        sid = slot.get("slotid", "")
        active = slot.get("active", "false").lower() in ("true", "1", "yes")
        title = slot.get("title", "Untitled")
        icon = slot.get("icon", "")
        stype = slot.get("type", "button")
        rdisplay = slot.get("resultdisplay", "text")
        func = slot.get("function", "")
        fields = slot.get("fields", "[]")
        desc = slot.get("description", "")

        color = ADMIN_ACCENT if active else "#94a3b8"
        with st.expander(f"{'' if active else ''} {icon} {title}  ({stype}) — ID: {sid}"):
            with st.form(f"edit_slot_{sid}", clear_on_submit=False):
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_title = st.text_input("Title", value=title, key=f"et_{sid}")
                    e_icon = st.selectbox("Icon", ICONS,
                                          index=ICONS.index(icon) if icon in ICONS else 0,
                                          key=f"ei_{sid}")
                    e_type = st.selectbox("Slot Type", SLOT_TYPES,
                                          index=SLOT_TYPES.index(stype) if stype in SLOT_TYPES else 0,
                                          key=f"esty_{sid}")
                with ec2:
                    e_rdisplay = st.selectbox("Result Display", RESULT_TYPES,
                                              index=RESULT_TYPES.index(rdisplay) if rdisplay in RESULT_TYPES else 0,
                                              key=f"erd_{sid}")
                    e_func = st.text_input("Function Name", value=func,
                                           placeholder="e.g. markAttendance", key=f"ef_{sid}")
                    e_desc = st.text_input("Description (optional)", value=desc, key=f"ed_{sid}")

                e_active = st.toggle("Active (visible to users)", value=active, key=f"ea_{sid}")

                st.markdown("**Fields (JSON):**")
                st.caption("Format: [{\"name\":\"date\",\"label\":\"Date\",\"type\":\"date\",\"required\":true}]")
                e_fields = st.text_area("", value=fields, height=100, key=f"efi_{sid}")

                # Validate fields JSON
                try:
                    json.loads(e_fields)
                    st.caption(" Valid JSON")
                except:
                    st.error(" Invalid JSON in fields")

                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    if st.form_submit_button(" Save", use_container_width=True):
                        r = db.save_slot({
                            "slotid": sid,
                            "dept": sel_dept,
                            "year": sel_year,
                            "active": str(e_active).lower(),
                            "title": e_title,
                            "icon": e_icon,
                            "type": e_type,
                            "resultdisplay": e_rdisplay,
                            "func": e_func,
                            "fields": e_fields,
                            "description": e_desc,
                        }, audience)
                        if r.get("status") == "success":
                            st.success(" Saved!")
                            st.session_state["slot_cfg_list"] = db.get_all_slots(audience)
                            st.rerun()
                        else:
                            st.error(f" {r.get('message')}")
                with sc2:
                    tog_label = " Deactivate" if active else " Activate"
                    if st.form_submit_button(tog_label, use_container_width=True):
                        db.toggle_slot(sid, not active, audience)
                        st.session_state["slot_cfg_list"] = db.get_all_slots(audience)
                        st.rerun()
                with sc3:
                    if st.form_submit_button(" Delete", use_container_width=True):
                        db.delete_slot(sid, audience)
                        st.session_state["slot_cfg_list"] = db.get_all_slots(audience)
                        st.rerun()

    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

    #  Add new slot 
    if len(scope_slots) >= MAX_SLOTS:
        st.warning(f" Maximum {MAX_SLOTS} slots reached for this dept/year.")
    else:
        st.markdown(f"####  Add New Slot ({len(scope_slots)}/{MAX_SLOTS})")
        with st.form("add_slot_form", clear_on_submit=True):
            nc1, nc2 = st.columns(2)
            with nc1:
                n_id = st.text_input("Slot ID (unique)", placeholder=f"e.g. {sel_dept.lower()}_slot_{len(scope_slots)+1}")
                n_title = st.text_input("Title", placeholder="e.g. Mark Attendance")
                n_icon = st.selectbox("Icon", ICONS, key="new_slot_icon")
                n_type = st.selectbox("Slot Type", SLOT_TYPES, key="new_slot_type",
                                      help="button=click only | form=input fields | display=show data | table=data grid")
            with nc2:
                n_rdisplay = st.selectbox("Result Display", RESULT_TYPES, key="new_slot_rd",
                                          help="How to show the function result")
                n_func = st.text_input("Function Name", placeholder="e.g. markAttendance")
                n_desc = st.text_input("Description (optional)")
                n_active = st.toggle("Active immediately", value=True, key="new_slot_active")

            st.markdown("**Fields JSON** (leave `[]` for button type):")

            # Field builder helper
            st.caption("Quick builder — add fields one by one:")
            fb_name = st.text_input("Field name", placeholder="e.g. date", key="fb_name")
            fb_label = st.text_input("Field label", placeholder="e.g. Date", key="fb_label")
            fb_type = st.selectbox("Field type", FIELD_TYPES, key="fb_type")
            fb_opts = st.text_input("Options (dropdown only, comma separated)",
                                    placeholder="e.g. Present,Absent,Late", key="fb_opts")
            fb_req = st.checkbox("Required", value=True, key="fb_req")

            if "new_slot_fields" not in st.session_state:
                st.session_state["new_slot_fields"] = []

            if st.form_submit_button(" Add Field to List"):
                if fb_name and fb_label:
                    field = {
                        "name": fb_name.strip(),
                        "label": fb_label.strip(),
                        "type": fb_type,
                        "required": fb_req,
                    }
                    if fb_type == "dropdown" and fb_opts:
                        field["options"] = fb_opts.strip()
                    st.session_state["new_slot_fields"].append(field)

            # Show current fields list
            if st.session_state["new_slot_fields"]:
                st.caption(f"Fields so far: {json.dumps(st.session_state['new_slot_fields'])}")

            n_fields_manual = st.text_area(
                "Or paste fields JSON directly:",
                value=json.dumps(st.session_state.get("new_slot_fields", [])),
                height=80,
                key="new_slot_fields_manual"
            )

            if st.form_submit_button(" Create Slot", use_container_width=True):
                if not n_id.strip() or not n_title.strip():
                    st.warning("Slot ID and Title are required.")
                elif n_id.strip() in existing_ids:
                    st.error(f" Slot ID '{n_id}' already exists.")
                else:
                    try:
                        json.loads(n_fields_manual)
                        fields_ok = True
                    except:
                        fields_ok = False
                        st.error(" Invalid JSON in fields.")

                    if fields_ok:
                        r = db.save_slot({
                            "slotid": n_id.strip(),
                            "dept": sel_dept,
                            "year": sel_year,
                            "active": str(n_active).lower(),
                            "title": n_title.strip(),
                            "icon": n_icon,
                            "type": n_type,
                            "resultdisplay": n_rdisplay,
                            "func": n_func.strip(),
                            "fields": n_fields_manual,
                            "description": n_desc.strip(),
                        }, audience)
                        if r.get("status") == "success":
                            st.session_state["new_slot_fields"] = []
                            st.success(f" Slot '{n_id}' created!")
                            st.session_state["slot_cfg_list"] = db.get_all_slots(audience)
                            st.rerun()
                        else:
                            st.error(f" {r.get('message')}")


def render_superadmin_interface(db: SheetDatabaseManager, ai_admin: AIAdminAssistant, master_ai: MasterSuperAdminAI = None):

    #  Session init 
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    st.title(" Super Admin Dashboard")
    st.markdown("---")

    # 
    # LOGIN
    # 
    if not st.session_state.admin_logged_in:
        st.subheader(" Super Admin Login")
        password = st.text_input("Admin Password", type="password")
        if st.button(" Log In", use_container_width=True):
            correct = st.secrets.get("SUPER_ADMIN_PASSWORD", "")
            if not correct:
                st.error(" No admin password set. Add SUPER_ADMIN_PASSWORD to secrets.toml.")
            elif password == correct:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error(" Incorrect password.")
        return

    inject_admin_css()

    #  Fetch all data 
    df_all       = db.fetch_all_roster()
    all_feedback = db.fetch_all_feedback()
    all_anns     = db.fetch_all_announcements()
    reps_list    = db.fetch_reps()

    total_students = len(df_all) if not df_all.empty else 0
    total_feedback = len(all_feedback)
    total_depts    = len(get_departments())

    #  Banner 
    st.markdown(f"""
    <div class="admin-banner">
        <h2> Super Admin — University Overview</h2>
        <p style="opacity:0.75;margin:0 0 12px 0;">
            Manage all departments, year groups and class rep accounts.
        </p>
        <span class="admin-pill"> {total_depts} Departments</span>
        <span class="admin-pill"> {total_students} Students</span>
        <span class="admin-pill"> {total_feedback} Feedback Messages</span>
        <span class="admin-pill"> {len(reps_list)} Rep Accounts</span>
    </div>
    """, unsafe_allow_html=True)

    #  Tabs 
    tabs = st.tabs([
        " Overview", " Departments", " Manage Reps",
        " Broadcast", " All Students",
        " All Feedback", " AI Insights", " Advanced Tools",
        " Master AI"
    ])

    # 
    #  OVERVIEW
    # 
    with tabs[0]:
        st.markdown("###  Department Overview")

        cols = st.columns(len(get_departments()))
        for ci, (code, info) in enumerate(get_departments().items()):
            with cols[ci]:
                dept_count = 0
                if not df_all.empty:
                    for col in ["Department", "department", "dept"]:
                        if col in df_all.columns:
                            dept_count = len(df_all[df_all[col] == code])
                            break
                color = info["color"]
                st.markdown(f"""
                <div class="dept-card" style="--dc:{color};">
                    <div style="font-size:0.78rem;font-weight:700;color:#94a3b8;
                        text-transform:uppercase;letter-spacing:1px;">{code}</div>
                    <div style="font-size:1.4rem;font-weight:900;color:{color};
                        margin:4px 0;">{dept_count}</div>
                    <div style="font-size:0.78rem;color:#1e293b;">{info['name']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # Enrollment pivot table
        st.markdown("###  Enrollment by Department × Year")
        if not df_all.empty:
            dept_col = next((c for c in ["Department","department","dept"]
                             if c in df_all.columns), None)
            year_col = next((c for c in ["Year","year"] if c in df_all.columns), None)
            if dept_col and year_col:
                pivot = df_all.groupby([dept_col, year_col]).size().unstack(fill_value=0)
                st.dataframe(pivot, use_container_width=True)
            else:
                st.info("Department/Year columns not yet populated in the roster.")
        else:
            st.info("No enrollment data yet.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # Rep coverage table
        st.markdown("###  Rep Coverage")
        rep_map = {}
        for r in reps_list:
            d = str(r.get("dept", r.get("department", ""))).strip().upper()
            y = str(r.get("year", "")).strip()
            n = str(r.get("rep_name", r.get("name", ""))).strip()
            rep_map[(d, y)] = n

        coverage_rows = []
        for code in get_dept_codes():
            for year in YEARS:
                rep = rep_map.get((code, year), "")
                coverage_rows.append({
                    "Department": dept_name(code),
                    "Year":       year,
                    "Rep":        rep if rep else " Not assigned",
                    "Status":     "" if rep else ""
                })
        st.dataframe(pd.DataFrame(coverage_rows), use_container_width=True)


    # 
    #  DEPARTMENTS
    # 
    with tabs[1]:
        st.markdown("###  Manage Departments")
        depts = get_departments()

        #  Add / Edit 
        st.markdown("####  Add New Department")
        with st.form("add_dept_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_code = st.text_input("Department Code", placeholder="e.g. CVL",
                    help="Short uppercase code — cannot be changed later")
                new_name = st.text_input("Full Name", placeholder="e.g. Civil Engineering")
            with col2:
                new_courses = st.text_input("Course Codes (comma separated)",
                    placeholder="e.g. BCIV,BSTR,BENV")

            # Colour palette picker
            st.markdown("**Pick a Colour:**")
            palette_cols = st.columns(len(COLOUR_PALETTE))
            selected_color = COLOUR_PALETTE[0]["hex"]
            selected_light = COLOUR_PALETTE[0]["light"]
            for pi, pal in enumerate(COLOUR_PALETTE):
                with palette_cols[pi]:
                    st.markdown(f"""
                    <div style="width:28px;height:28px;border-radius:50%;
                        background:{pal['hex']};margin:0 auto;
                        border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.2);"
                        title="{pal['name']}"></div>
                    <div style="font-size:0.6rem;text-align:center;color:#94a3b8;margin-top:2px;">
                        {pal['name']}
                    </div>
                    """, unsafe_allow_html=True)

            colour_names = [p["name"] for p in COLOUR_PALETTE]
            chosen_colour = st.selectbox("Select Colour", colour_names, key="new_dept_colour")
            chosen_pal    = next(p for p in COLOUR_PALETTE if p["name"] == chosen_colour)

            if st.form_submit_button(" Add Department", use_container_width=True):
                if not new_code or not new_name or not new_courses:
                    st.warning("Please fill in all fields.")
                elif new_code.strip().upper() in depts:
                    st.error(f" Department code '{new_code.upper()}' already exists.")
                else:
                    with st.spinner("Adding..."):
                        ok = db.add_department(
                            new_code, new_name,
                            chosen_pal["hex"], chosen_pal["light"], new_courses
                        )
                    if ok:
                        st.success(f" Department '{new_name}' added!")
                        st.rerun()
                    else:
                        st.error(" Failed. Check your GAS deployment.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        #  Current departments 
        st.markdown("####  Current Departments")
        if not depts:
            st.info("No departments loaded.")
        else:
            for didx, (code, info) in enumerate(depts.items()):
                color   = info.get("color", "#1a56db")
                lcolor  = info.get("light", "#dbeafe")
                dname   = info.get("name",  code)
                courses = ", ".join(info.get("courses", []))

                # Count students in this dept
                student_count = 0
                if not df_all.empty:
                    dcol = next((c for c in ["Department","department","dept"]
                                 if c in df_all.columns), None)
                    if dcol:
                        student_count = len(df_all[df_all[dcol] == code])

                with st.expander(f" {dname} ({code}) — {student_count} students"):
                    # Edit form
                    with st.form(f"edit_dept_{code}"):
                        e_name    = st.text_input("Full Name",    value=dname)
                        e_courses = st.text_input("Course Codes", value=courses,
                            help="Comma separated, e.g. BMEC,BBPE")

                        st.markdown("**Change Colour:**")
                        e_colour_name = st.selectbox(
                            "Colour", [p["name"] for p in COLOUR_PALETTE],
                            index=next((i for i,p in enumerate(COLOUR_PALETTE)
                                        if p["hex"]==color), 0),
                            key=f"edit_col_{code}"
                        )
                        e_pal = next(p for p in COLOUR_PALETTE if p["name"] == e_colour_name)

                        # Preview swatch
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:10px;margin:8px 0;">
                            <div style="width:24px;height:24px;border-radius:50%;
                                background:{e_pal['hex']};border:2px solid white;
                                box-shadow:0 1px 4px rgba(0,0,0,0.2);"></div>
                            <span style="font-size:0.85rem;color:#475569;">
                                Preview: {e_pal['name']}
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                        sc1, sc2 = st.columns(2)
                        with sc1:
                            if st.form_submit_button(" Save Changes", use_container_width=True):
                                with st.spinner("Saving..."):
                                    ok = db.update_department(
                                        code, e_name, e_pal["hex"],
                                        e_pal["light"], e_courses
                                    )
                                if ok:
                                    st.success(" Updated!")
                                    st.rerun()
                                else:
                                    st.error(" Failed.")
                        with sc2:
                            if st.form_submit_button(" Delete", use_container_width=True,
                                                      type="secondary"):
                                st.session_state[f"confirm_del_dept_{code}"] = True
                                st.rerun()

                    # Confirm delete
                    if st.session_state.get(f"confirm_del_dept_{code}"):
                        if student_count > 0:
                            st.error(
                                f" Cannot delete **{dname}** — "
                                f"**{student_count} student(s)** are registered here. "
                                f"Transfer or remove all {code} students first."
                            )
                            if st.button("OK", key=f"ok_block_{code}"):
                                st.session_state[f"confirm_del_dept_{code}"] = False
                                st.rerun()
                        else:
                            st.warning(f" Delete **{dname} ({code})**? This cannot be undone.")
                            da, db_ = st.columns(2)
                            with da:
                                if st.button(" Yes, delete", key=f"yes_dept_{code}"):
                                    with st.spinner("Deleting..."):
                                        result = db.delete_department(code)
                                    if result.get("status") == "success":
                                        st.session_state[f"confirm_del_dept_{code}"] = False
                                        st.success(f" {dname} deleted.")
                                        st.rerun()
                                    else:
                                        st.error(f" {result.get('message','Failed')}")
                            with db_:
                                if st.button(" Cancel", key=f"no_dept_{code}"):
                                    st.session_state[f"confirm_del_dept_{code}"] = False
                                    st.rerun()

    # 
    #  MANAGE REPS
    # 
    with tabs[2]:
        st.markdown("###  Class Rep Accounts")
        st.info(
            "Create or update a rep account here. "
            "The rep uses their department, year and password to log in — "
            "no code changes needed."
        )

        #  Create / Update rep 
        st.markdown("####  Create or Update Rep Account")
        with st.form("assign_rep_form", clear_on_submit=True):
            dept_opts = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
            d_label   = st.selectbox("Department", list(dept_opts.keys()), key="ar_dept")
            sel_dept  = dept_opts[d_label]
            sel_year  = st.selectbox("Year Group", YEARS, key="ar_year")

            rep_name  = st.text_input("Rep Full Name",    placeholder="e.g., Alice Nakamura")
            rep_reg   = st.text_input("Rep Reg Number",   placeholder="e.g., 25/U/0001/PS")
            rep_pw    = st.text_input(
                "Set Password",
                type="password",
                placeholder="Min 6 characters",
                help="The rep will use this to log in. They can change it later."
            )
            rep_pw2   = st.text_input("Confirm Password", type="password")

            submitted = st.form_submit_button(" Save Rep Account", use_container_width=True)

            if submitted:
                if not rep_name or not rep_reg or not rep_pw:
                    st.warning("Please fill in all fields.")
                elif rep_pw != rep_pw2:
                    st.error(" Passwords do not match.")
                elif len(rep_pw) < 6:
                    st.error(" Password must be at least 6 characters.")
                else:
                    with st.spinner("Saving..."):
                        ok = db.assign_rep(sel_dept, sel_year, rep_name, rep_reg, rep_pw)
                    if ok:
                        st.success(
                            f" Rep account saved: **{rep_name}** → "
                            f"{dept_name(sel_dept)} — {sel_year}"
                        )
                        st.rerun()
                    else:
                        st.error(" Failed to save. Check your GAS deployment.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        #  Current rep accounts 
        st.markdown("####  Current Rep Accounts")
        if not reps_list:
            st.info("No rep accounts created yet.")
        else:
            for ridx, rep in enumerate(reps_list):
                r_dept_code = str(rep.get("dept", rep.get("department", ""))).strip().upper()
                r_year      = str(rep.get("year", "")).strip()
                r_name      = str(rep.get("rep_name", rep.get("name", ""))).strip()
                r_reg       = str(rep.get("rep_reg",  rep.get("reg",  ""))).strip()
                r_has_pw    = rep.get("has_password", False)
                color       = dept_color(r_dept_code) if r_dept_code in get_departments() else ADMIN_ACCENT

                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                    <div class="rep-row" style="border-left-color:{color};">
                        <div>
                            <div class="rr-info">
                                 {r_name}
                                <span style="background:{dept_light(r_dept_code) if r_dept_code in get_departments() else ADMIN_LIGHT};
                                    color:{color};font-size:0.7rem;font-weight:700;
                                    padding:2px 8px;border-radius:10px;margin-left:8px;">
                                    {r_dept_code} · {r_year}
                                </span>
                            </div>
                            <div class="rr-meta">
                                {dept_name(r_dept_code)} &nbsp;·&nbsp;
                                Reg: {r_reg} &nbsp;·&nbsp;
                                Password: {' Set' if r_has_pw else ' Not set'}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button(" Remove", key=f"del_rep_{ridx}"):
                        st.session_state[f"confirm_del_rep_{ridx}"] = True
                        st.rerun()

                # Confirm delete
                if st.session_state.get(f"confirm_del_rep_{ridx}"):
                    st.warning(f" Remove **{r_name}** ({r_dept_code} {r_year})? This cannot be undone.")
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button(" Yes, remove", key=f"yes_del_{ridx}"):
                            with st.spinner("Removing..."):
                                ok = db.delete_rep(r_dept_code, r_year)
                            if ok:
                                st.session_state[f"confirm_del_rep_{ridx}"] = False
                                st.success(" Rep account removed.")
                                st.rerun()
                            else:
                                st.error(" Failed.")
                    with cb:
                        if st.button(" Cancel", key=f"no_del_{ridx}"):
                            st.session_state[f"confirm_del_rep_{ridx}"] = False
                            st.rerun()

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        #  Reset a rep's password 
        st.markdown("####  Reset a Rep's Password")
        st.caption("Use this if a rep is locked out and needs their password reset.")

        if reps_list:
            rep_labels = {
                f"{r.get('rep_name','')} — {r.get('dept','')} {r.get('year','')}": r
                for r in reps_list
            }
            sel_rep_label = st.selectbox(
                "Select Rep", ["— Select —"] + list(rep_labels.keys()),
                key="reset_pw_sel"
            )
            if sel_rep_label != "— Select —":
                sel_rep = rep_labels[sel_rep_label]
                with st.form("reset_pw_form", clear_on_submit=True):
                    new_pw  = st.text_input("New Password",      type="password")
                    new_pw2 = st.text_input("Confirm Password",  type="password")
                    if st.form_submit_button(" Reset Password", use_container_width=True):
                        if not new_pw:
                            st.warning("Please enter a new password.")
                        elif new_pw != new_pw2:
                            st.error(" Passwords do not match.")
                        elif len(new_pw) < 6:
                            st.error(" Must be at least 6 characters.")
                        else:
                            # Admin resets by re-assigning with new password
                            # We use assignRep which updates existing record
                            with st.spinner("Resetting..."):
                                ok = db.assign_rep(
                                    dept     = str(sel_rep.get("dept","")).upper(),
                                    year     = str(sel_rep.get("year","")),
                                    rep_name = str(sel_rep.get("rep_name","")),
                                    rep_reg  = str(sel_rep.get("rep_reg","")),
                                    password = new_pw
                                )
                            if ok:
                                st.success(f" Password reset for {sel_rep.get('rep_name','')}.")
                            else:
                                st.error(" Reset failed.")
        else:
            st.info("No rep accounts to reset yet.")

    # 
    #  BROADCAST
    # 
    with tabs[3]:
        st.markdown("###  Broadcast Announcement")
        st.info(
            "Broadcasts appear for **all students** across all departments and years, "
            "marked as  BROADCAST."
        )

        with st.form("broadcast_form", clear_on_submit=True):
            b_text     = st.text_area("Announcement text", height=140)
            b_priority = st.selectbox("Priority", ["Normal", "Urgent"])
            c1, c2     = st.columns(2)
            with c1: post_btn  = st.form_submit_button(" Broadcast Now",  use_container_width=True)
            with c2: draft_btn = st.form_submit_button(" Draft with AI", use_container_width=True)

            if draft_btn and b_text.strip():
                with st.spinner("Drafting..."):
                    st.session_state["admin_draft"] = ai_admin.generate_broadcast(
                        b_text, b_priority
                    )
            if post_btn:
                if b_text.strip():
                    if db.broadcast_announcement(b_text, b_priority):
                        st.success(" Broadcast sent to all departments!")
                        st.rerun()
                    else:
                        st.error(" Failed.")
                else:
                    st.warning("Please enter announcement text.")

        if st.session_state.get("admin_draft"):
            st.markdown("**AI Draft — edit before posting:**")
            edited = st.text_area("", value=st.session_state["admin_draft"], height=150)
            pri2   = st.selectbox("Priority", ["Normal", "Urgent"], key="bc_pri2")
            if st.button(" Post this Broadcast"):
                if db.broadcast_announcement(edited, pri2):
                    st.session_state["admin_draft"] = ""
                    st.success(" Broadcast posted!")
                    st.rerun()

        st.markdown("---")
        st.markdown("####  Recent Broadcasts")
        broadcasts = [
            a for a in all_anns
            if isinstance(a, dict) and a.get("dept", "") == "ALL"
        ]
        if broadcasts:
            for ann in broadcasts[:10]:
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:12px 16px;
                    margin-bottom:8px;border:1px solid #e2e8f7;
                    border-left:4px solid {ADMIN_ACCENT};">
                    <div style="font-size:0.75rem;color:#94a3b8;">
                         {ann.get('timestamp','')} ·  ALL DEPTS
                    </div>
                    <div style="margin-top:4px;">{ann.get('text','')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No broadcasts sent yet.")

    # 
    #  ALL STUDENTS
    # 
    with tabs[4]:
        st.markdown("###  All Registered Students")
        if df_all.empty:
            st.info("No students registered yet.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1: f_dept   = st.selectbox("Dept",   ["ALL"] + get_dept_codes(), key="f_dept")
            with c2: f_year   = st.selectbox("Year",   ["ALL"] + YEARS,      key="f_year")
            with c3: f_search = st.text_input("Search name/reg",              key="f_search")

            df_show = df_all.copy()

            # Normalise column names for filtering
            col_rename = {}
            for c in df_show.columns:
                if c.lower() in ("department", "dept", "dep"):
                    col_rename[c] = "Department"
                elif c.lower() == "year":
                    col_rename[c] = "Year"
            df_show = df_show.rename(columns=col_rename)

            if f_dept != "ALL" and "Department" in df_show.columns:
                df_show = df_show[df_show["Department"] == f_dept]
            if f_year != "ALL" and "Year" in df_show.columns:
                df_show = df_show[df_show["Year"] == f_year]
            if f_search:
                mask = (
                    df_show["Student Name"].str.contains(f_search, case=False, na=False) |
                    df_show["Reg Number"].str.contains(f_search,   case=False, na=False)
                )
                df_show = df_show[mask]

            st.caption(f"Showing {len(df_show)} of {total_students} students")
            st.dataframe(df_show, use_container_width=True)

            csv = df_show.to_csv(index=False)
            st.download_button(
                " Export to CSV", data=csv,
                file_name="students.csv", mime="text/csv"
            )

    # 
    #  ALL FEEDBACK
    # 
    with tabs[5]:
        st.markdown("###  All Student Feedback")
        if not all_feedback:
            st.info("No feedback messages yet.")
        else:
            f_dept2 = st.selectbox("Filter by Dept", ["ALL"] + get_dept_codes(), key="fb_dept")

            filtered_fb = all_feedback
            if f_dept2 != "ALL":
                filtered_fb = [
                    f for f in all_feedback
                    if isinstance(f, list) and len(f) >= 6
                    and str(f[5]).strip().upper() == f_dept2
                ]

            st.caption(f"{len(filtered_fb)} messages")

            for fb in filtered_fb[:50]:
                if not (isinstance(fb, list) and len(fb) >= 5):
                    continue
                ts       = str(fb[0])
                reg      = str(fb[1])
                name     = str(fb[2])
                status   = str(fb[3])
                msg      = str(fb[4])
                dept_fb  = str(fb[5]).strip().upper() if len(fb) > 5 else "?"
                year_fb  = str(fb[6]).strip()         if len(fb) > 6 else "?"
                sc       = "#16a34a" if status.lower() == "reviewed" else "#d4820a"
                color    = dept_color(dept_fb) if dept_fb in get_departments() else ADMIN_ACCENT

                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:12px 16px;
                    margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {color};">
                    <div style="font-size:0.75rem;color:#94a3b8;">
                         <strong>{name}</strong> · {reg}
                        &nbsp;·&nbsp;
                        <span style="background:{dept_color(dept_fb) if dept_fb in get_departments() else '#e2e8f7'};
                            color:white;font-size:0.68rem;font-weight:700;
                            padding:1px 7px;border-radius:8px;">{dept_fb}</span>
                        {year_fb} ·  {ts}
                        &nbsp;<span style="color:{sc};font-weight:600;">{status}</span>
                    </div>
                    <div style="margin-top:6px;font-size:0.9rem;">{msg}</div>
                </div>
                """, unsafe_allow_html=True)

    # 
    #  AI ENGINE
    # 
    with tabs[6]:
        st.markdown("###  AI Engine Control Centre")
        st.markdown(
            f'<div style="background:{ADMIN_LIGHT};border:1px solid {ADMIN_ACCENT}44;'
            f'border-radius:10px;padding:10px 16px;font-size:0.88rem;color:{ADMIN_ACCENT};'
            f'font-weight:600;margin-bottom:16px;">'
            f' Full visibility and control over all AI providers, keys and features.</div>',
            unsafe_allow_html=True
        )

        ai_engine_tabs = st.tabs([
            " Provider Status",
            " Key Management",
            " Feature Controls",
            " Insights",
            " Feedback Summary",
        ])

        # 
        #  PROVIDER STATUS
        # 
        with ai_engine_tabs[0]:
            st.markdown("####  AI Provider Status")
            st.caption("Live status of all configured AI providers and keys.")

            # Load keys from secrets
            gemini_keys = []
            for i in range(1, 20):
                k = st.secrets.get(f"GEMINI_KEY_{i}", "")
                if k:
                    gemini_keys.append((f"Gemini Key {i}", k))

            groq_key      = st.secrets.get("GROQ_API_KEY", "")
            mistral_key   = st.secrets.get("MISTRAL_API_KEY", "")
            hf_token      = st.secrets.get("HUGGINGFACE_TOKEN", "")
            cf_token      = st.secrets.get("CLOUDFLARE_TOKEN", "")
            cf_account    = st.secrets.get("CLOUDFLARE_ACCOUNT_ID", "")

            st.markdown("** Gemini Keys**")
            if gemini_keys:
                for label, key in gemini_keys:
                    masked = key[:8] + "..." + key[-4:]
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:12px 16px;
                        margin-bottom:6px;border:1px solid #e2e8f7;
                        border-left:4px solid #16a34a;
                        display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <span style="font-weight:700;color:#1e293b;"> {label}</span>
                            <span style="font-size:0.78rem;color:#94a3b8;margin-left:10px;">
                                {masked}
                            </span>
                        </div>
                        <span style="background:#dcfce7;color:#16a34a;font-size:0.7rem;
                            font-weight:700;padding:2px 10px;border-radius:10px;">ACTIVE</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error(" No Gemini keys configured in secrets.toml")

            st.markdown("** Fallback Providers**")
            providers = [
                ("Groq",        bool(groq_key),    "GROQ_API_KEY"),
                ("Mistral",     bool(mistral_key),  "MISTRAL_API_KEY"),
                ("HuggingFace", bool(hf_token),     "HUGGINGFACE_TOKEN"),
                ("Cloudflare",  bool(cf_token and cf_account), "CLOUDFLARE_TOKEN + CLOUDFLARE_ACCOUNT_ID"),
            ]
            for pname, is_set, secret_key in providers:
                color  = "#16a34a" if is_set else "#dc2626"
                bg     = "#dcfce7" if is_set else "#fee2e2"
                status = " CONFIGURED" if is_set else " NOT SET"
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:12px 16px;
                    margin-bottom:6px;border:1px solid #e2e8f7;border-left:4px solid {color};
                    display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <span style="font-weight:700;color:#1e293b;">{pname}</span>
                        <span style="font-size:0.75rem;color:#94a3b8;margin-left:8px;">
                            {secret_key}
                        </span>
                    </div>
                    <span style="background:{bg};color:{color};font-size:0.7rem;
                        font-weight:700;padding:2px 10px;border-radius:10px;">{status}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
            st.markdown("** Fallback Chain**")
            chain = ["Gemini (Key Rotation)"]
            if groq_key:    chain.append("Groq")
            if mistral_key: chain.append("Mistral")
            if hf_token:    chain.append("HuggingFace")
            if cf_token:    chain.append("Cloudflare")
            chain_str = " → ".join([f"**{c}**" for c in chain])
            st.markdown(f"When quota is hit: {chain_str}")
            if len(chain) == 1:
                st.warning(" Only Gemini configured — add fallback providers for more resilience.")

        # 
        #  KEY MANAGEMENT
        # 
        with ai_engine_tabs[1]:
            st.markdown("####  Gemini Key Management")
            st.info(
                "Keys are stored in `.streamlit/secrets.toml` on your server. "
                "Add new keys there as `GEMINI_KEY_1`, `GEMINI_KEY_2`, etc. "
                "They will appear here automatically."
            )

            # Show all current keys
            gemini_keys_all = []
            for i in range(1, 20):
                k = st.secrets.get(f"GEMINI_KEY_{i}", "")
                if k: gemini_keys_all.append((i, k))

            if gemini_keys_all:
                st.markdown(f"**{len(gemini_keys_all)} key(s) configured:**")
                for idx, (num, key) in enumerate(gemini_keys_all):
                    masked = key[:12] + "•" * 15 + key[-4:]
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:14px 18px;
                        margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {ADMIN_ACCENT};">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <span style="font-weight:800;color:{ADMIN_ACCENT};">
                                    Key {num}
                                </span>
                                <span style="font-family:monospace;font-size:0.82rem;
                                    color:#475569;margin-left:12px;">{masked}</span>
                            </div>
                            <span style="background:#dcfce7;color:#16a34a;font-size:0.7rem;
                                font-weight:700;padding:2px 10px;border-radius:10px;">
                                GEMINI_KEY_{num}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error(" No Gemini keys found.")

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            st.markdown("####  How to Add a New Key")
            st.code("""# In .streamlit/secrets.toml — add the next key number:
GEMINI_KEY_1 = "AIza...your_key..."
GEMINI_KEY_2 = "AIza...friend_key..."
GEMINI_KEY_3 = "AIza...new_key..."   # ← add new ones like this

# On Streamlit Cloud:
# Go to App Settings → Secrets → paste new key line → Save
# The app reloads automatically.""", language="toml")

            st.markdown("####  Test a Key")
            test_key = st.text_input(
                "Paste a key to test:",
                type="password",
                placeholder="AIza..."
            )
            if st.button(" Test Key", use_container_width=True) and test_key.strip():
                with st.spinner("Testing..."):
                    try:
                        import google as genai
                        client = genai.Client(api_key=test_key.strip())
                        _resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Say: Key works"
            )
                        st.success(f" Key is valid! Response: {_resp.text[:80]}")
                    except Exception as e:
                        st.error(f" Key failed: {str(e)[:120]}")

        # 
        #  FEATURE CONTROLS
        # 
        with ai_engine_tabs[2]:
            st.markdown("####  AI Feature Controls")
            st.info("Configure which AI features are active and their limits.")

            st.markdown("**Student AI Features**")
            c1, c2 = st.columns(2)
            with c1:
                st.toggle(" Class Assistant Chat",   value=True,  disabled=True)
                st.toggle(" Material Summarizer",    value=True,  disabled=True)
                st.toggle(" Revision Questions",     value=True,  disabled=True)
            with c2:
                st.toggle(" Document Q&A",           value=True,  disabled=True)
                st.toggle(" Concept Explainer",      value=True,  disabled=True)

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            st.markdown("**Class Rep AI Features**")
            c3, c4 = st.columns(2)
            with c3:
                st.toggle(" Inbox Analysis",         value=True,  disabled=True)
                st.toggle(" Announcement Drafting",  value=True,  disabled=True)
                st.toggle("⏰ Deadline Reminders",     value=True,  disabled=True)
            with c4:
                st.toggle(" Group Allocation AI",    value=True,  disabled=True)
                st.toggle(" Timetable Generator",    value=True,  disabled=True)
                st.toggle(" Conflict Checker",       value=True,  disabled=True)

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            st.markdown("**⏱ Cooldown Settings**")
            st.caption("Minimum seconds between AI requests per student.")
            cooldown = st.slider("Student cooldown (seconds)", 5, 120, 30)
            st.caption(f"Current: **{cooldown}s** between requests per student")

            st.markdown("** Token Limits**")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.metric("Summary tokens", "6,000")
                st.metric("Chat tokens",    "6,000")
            with col_t2:
                st.metric("Revision Qs",    "6,000")
                st.metric("Rep Analysis",   "6,000")

            st.info(
                " To change cooldowns or token limits, edit `ai_engine.py`. "
                "Dynamic controls coming in a future update."
            )

        # 
        #  ENROLLMENT INSIGHTS
        # 
        with ai_engine_tabs[3]:
            st.markdown("####  AI Enrollment Analysis")
            if st.button(" Analyse Enrollment", use_container_width=True, type="primary"):
                with st.spinner("Analysing..."):
                    result = ai_admin.analyze_enrollment(df_all)
                st.markdown(result)

        # 
        #  FEEDBACK SUMMARY
        # 
        with ai_engine_tabs[4]:
            st.markdown("####  AI Feedback Summary")
            f_dept3 = st.selectbox(
                "Scope", ["ALL"] + get_dept_codes(), key="ai_fb_dept"
            )
            if st.button(" Summarize Feedback", use_container_width=True, type="primary"):
                if f_dept3 == "ALL":
                    fb_scope = all_feedback
                else:
                    fb_scope = [
                        f for f in all_feedback
                        if isinstance(f, list) and len(f) > 5
                        and str(f[5]).strip().upper() == f_dept3
                    ]
                with st.spinner("Analysing..."):
                    result = ai_admin.summarize_all_feedback(fb_scope, f_dept3)
                st.markdown(result)

    # 
    #  ADVANCED TOOLS  (tabs[7])
    # 
    with tabs[7]:
        st.markdown("###  Advanced Tools")
        st.info(
            "Direct access to Sheet Manager, Config, Data Explorer, "
            "Function Library, and Slot Configurator — all powered by your GAS backend."
        )

        adv_tabs = st.tabs([
            " Sheet Manager",
            " Config Manager",
            " Data Explorer",
            " Function Library",
            " Slot Configurator",
        ])

        # 
        #  SHEET MANAGER
        # 
        with adv_tabs[0]:
            st.markdown("####  Sheet Manager")
            st.caption("Create, rename, clear or delete custom sheets in your Google Spreadsheet.")

            # List all sheets
            if st.button(" Refresh Sheet List", key="refresh_sheets"):
                st.session_state["sheets_list"] = db.list_sheets()

            if "sheets_list" not in st.session_state:
                st.session_state["sheets_list"] = db.list_sheets()

            sheets_list = st.session_state.get("sheets_list", [])

            # Defensive: if an older/legacy version of this list (plain
            # strings) is still cached in this browser session, normalise
            # it instead of crashing.
            if sheets_list and not isinstance(sheets_list[0], dict):
                sheets_list = db.list_sheets()
                st.session_state["sheets_list"] = sheets_list

            if sheets_list:
                st.markdown(f"**{len(sheets_list)} sheets found:**")
                for s in sheets_list:
                    if not isinstance(s, dict):
                        continue
                    sname     = s.get("name", "")
                    srows     = s.get("rows", 0)
                    scols     = s.get("cols", 0)
                    protected = s.get("protected", False)
                    badge_col = "#dc2626" if protected else ADMIN_ACCENT
                    badge_txt = "PROTECTED" if protected else "CUSTOM"
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:12px 16px;
                        margin-bottom:6px;border:1px solid #e2e8f7;
                        border-left:4px solid {badge_col};
                        display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <span style="font-weight:700;color:#1e293b;">{sname}</span>
                            <span style="font-size:0.75rem;color:#94a3b8;margin-left:10px;">
                                {srows} rows · {scols} cols
                            </span>
                        </div>
                        <span style="background:{'#fee2e2' if protected else ADMIN_LIGHT};
                            color:{badge_col};font-size:0.68rem;font-weight:700;
                            padding:2px 10px;border-radius:10px;">{badge_txt}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No sheets loaded. Click Refresh.")

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            # Create sheet
            st.markdown("####  Create New Sheet")
            with st.form("create_sheet_form", clear_on_submit=True):
                new_sheet_name = st.text_input("Sheet Name", placeholder="e.g. EventLogs")
                new_headers    = st.text_input(
                    "Headers (comma separated, optional)",
                    placeholder="e.g. Timestamp, Student, Event"
                )
                if st.form_submit_button(" Create Sheet", use_container_width=True):
                    if not new_sheet_name.strip():
                        st.warning("Please enter a sheet name.")
                    else:
                        headers_list = (
                            [h.strip() for h in new_headers.split(",") if h.strip()]
                            if new_headers.strip() else []
                        )
                        with st.spinner("Creating..."):
                            result = db.create_sheet(new_sheet_name.strip(), headers_list)
                        if result.get("status") == "success":
                            st.success(f" Sheet '{new_sheet_name}' created!")
                            st.session_state["sheets_list"] = db.list_sheets()
                            st.rerun()
                        else:
                            st.error(f" {result.get('message', 'Failed')}")

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            # Rename / Clear / Delete
            st.markdown("####  Manage Existing Sheet")
            custom_sheets = [
                s["name"] for s in sheets_list if not s.get("protected", False)
            ]
            if not custom_sheets:
                st.info("No custom (non-protected) sheets to manage yet.")
            else:
                sel_manage = st.selectbox(
                    "Select Sheet", ["— Select —"] + custom_sheets, key="manage_sheet_sel"
                )
                if sel_manage and sel_manage != "— Select —":
                    mc1, mc2, mc3 = st.columns(3)

                    with mc1:
                        with st.form(f"rename_form_{sel_manage}", clear_on_submit=True):
                            new_name_input = st.text_input("New name", placeholder="NewSheetName")
                            if st.form_submit_button(" Rename", use_container_width=True):
                                if new_name_input.strip():
                                    with st.spinner("Renaming..."):
                                        r = db.rename_sheet(sel_manage, new_name_input.strip())
                                    if r.get("status") == "success":
                                        st.success(" Renamed!")
                                        st.session_state["sheets_list"] = db.list_sheets()
                                        st.rerun()
                                    else:
                                        st.error(f" {r.get('message','Failed')}")
                                else:
                                    st.warning("Enter a new name.")

                    with mc2:
                        if st.button(" Clear Data Rows", key=f"clear_{sel_manage}",
                                     use_container_width=True):
                            st.session_state[f"confirm_clear_{sel_manage}"] = True
                            st.rerun()
                        if st.session_state.get(f"confirm_clear_{sel_manage}"):
                            st.warning(f" This will delete all data rows (keeps headers) in **{sel_manage}**.")
                            if st.button(" Yes, clear", key=f"yes_clear_{sel_manage}"):
                                with st.spinner("Clearing..."):
                                    r = db.clear_sheet(sel_manage)
                                st.session_state[f"confirm_clear_{sel_manage}"] = False
                                if r.get("status") == "success":
                                    st.success(f" Cleared {r.get('deleted', 0)} rows.")
                                    st.session_state["sheets_list"] = db.list_sheets()
                                    st.rerun()
                                else:
                                    st.error(f" {r.get('message','Failed')}")
                            if st.button(" Cancel", key=f"no_clear_{sel_manage}"):
                                st.session_state[f"confirm_clear_{sel_manage}"] = False
                                st.rerun()

                    with mc3:
                        if st.button(" Delete Sheet", key=f"del_{sel_manage}",
                                     use_container_width=True, type="secondary"):
                            st.session_state[f"confirm_del_sheet_{sel_manage}"] = True
                            st.rerun()
                        if st.session_state.get(f"confirm_del_sheet_{sel_manage}"):
                            st.warning(f" Permanently delete **{sel_manage}**?")
                            if st.button(" Yes, delete", key=f"yes_del_sheet_{sel_manage}"):
                                with st.spinner("Deleting..."):
                                    r = db.delete_sheet(sel_manage)
                                st.session_state[f"confirm_del_sheet_{sel_manage}"] = False
                                if r.get("status") == "success":
                                    st.success(f" '{sel_manage}' deleted.")
                                    st.session_state["sheets_list"] = db.list_sheets()
                                    st.rerun()
                                else:
                                    st.error(f" {r.get('message','Failed')}")
                            if st.button(" Cancel", key=f"no_del_sheet_{sel_manage}"):
                                st.session_state[f"confirm_del_sheet_{sel_manage}"] = False
                                st.rerun()

        # 
        #  CONFIG MANAGER
        # 
        with adv_tabs[1]:
            st.markdown("####  App Config Manager")
            st.caption(
                "Read and write key-value config stored in the **Config** sheet in your spreadsheet. "
                "Changes take effect on the next app load."
            )

            if st.button(" Load Config", key="load_config", use_container_width=True):
                st.session_state["config_data"] = db.get_all_config()

            if "config_data" not in st.session_state:
                st.session_state["config_data"] = db.get_all_config()

            config_data = st.session_state.get("config_data", {})

            if config_data and isinstance(config_data, dict):
                st.markdown(f"**{len(config_data)} config keys:**")
                for k, v in config_data.items():
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:10px 16px;
                        margin-bottom:6px;border:1px solid #e2e8f7;
                        border-left:4px solid {ADMIN_ACCENT};
                        display:flex;align-items:center;justify-content:space-between;
                        flex-wrap:wrap;gap:6px;">
                        <span style="font-weight:700;color:#1e293b;font-size:0.85rem;">
                            {k}
                        </span>
                        <span style="font-family:monospace;font-size:0.82rem;
                            color:#475569;background:#f1f5f9;
                            padding:2px 8px;border-radius:6px;">{v}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No config keys found. Your GAS Config sheet may be empty.")

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            st.markdown("####  Set / Update Config Key")
            with st.form("set_config_form", clear_on_submit=True):
                cfg_key   = st.text_input("Key",         placeholder="e.g. drive_folder_id")
                cfg_val   = st.text_input("Value",       placeholder="e.g. 1XrmtkYDPD6Kpml...")
                cfg_desc  = st.text_input("Description (optional)", placeholder="What this key does")
                if st.form_submit_button(" Save Config Key", use_container_width=True):
                    if not cfg_key.strip() or not cfg_val.strip():
                        st.warning("Key and Value are required.")
                    else:
                        with st.spinner("Saving..."):
                            r = db.set_config(cfg_key.strip(), cfg_val.strip(), cfg_desc.strip())
                        if r.get("status") == "success":
                            st.success(f" Config '{cfg_key}' saved!")
                            st.session_state["config_data"] = db.get_all_config()
                            st.rerun()
                        else:
                            st.error(f" {r.get('message','Failed')}")

        # 
        #  DATA EXPLORER
        # 
        with adv_tabs[2]:
            st.markdown("####  Data Explorer")
            st.caption(
                "Read any sheet, write rows, or delete rows directly. "
                "Use carefully — no undo for writes/deletes."
            )

            explore_tabs = st.tabs([" Read Sheet", " Write Row", " Delete Row"])

            with explore_tabs[0]:
                st.markdown("**Read any sheet (with optional filter)**")
                with st.form("read_sheet_form"):
                    rs_name    = st.text_input("Sheet Name", placeholder="e.g. EventLogs")
                    rs_fkey    = st.text_input("Filter Column (optional)", placeholder="e.g. Department")
                    rs_fval    = st.text_input("Filter Value (optional)",  placeholder="e.g. CSC")
                    if st.form_submit_button(" Read Sheet", use_container_width=True):
                        if not rs_name.strip():
                            st.warning("Enter a sheet name.")
                        else:
                            with st.spinner("Reading..."):
                                rows = db.read_sheet(rs_name.strip(), rs_fkey.strip(), rs_fval.strip())
                            if isinstance(rows, list) and rows:
                                st.success(f" {len(rows)} rows returned.")
                                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                            elif isinstance(rows, list):
                                st.info("Sheet is empty or no matching rows.")
                            else:
                                st.error(f" {rows.get('message','Failed')}")

            with explore_tabs[1]:
                st.markdown("**Write a row to any sheet**")
                with st.form("write_row_form", clear_on_submit=True):
                    wr_sheet  = st.text_input("Sheet Name",   placeholder="e.g. EventLogs")
                    wr_values = st.text_area(
                        "Row values (one per line, in column order)",
                        placeholder="Alice\nCSC\nYear 1\nPresent",
                        height=120
                    )
                    wr_ts = st.checkbox("Prepend current timestamp", value=True)
                    if st.form_submit_button(" Write Row", use_container_width=True):
                        if not wr_sheet.strip() or not wr_values.strip():
                            st.warning("Sheet name and at least one value are required.")
                        else:
                            row_arr = [v.strip() for v in wr_values.strip().split("\n") if v.strip()]
                            with st.spinner("Writing..."):
                                r = db.write_row(wr_sheet.strip(), row_arr, wr_ts)
                            if r.get("status") == "success":
                                st.success(" Row written!")
                            else:
                                st.error(f" {r.get('message','Failed')}")

            with explore_tabs[2]:
                st.markdown("**Delete row(s) matching a column value**")
                with st.form("delete_row_form", clear_on_submit=True):
                    dr_sheet    = st.text_input("Sheet Name",     placeholder="e.g. EventLogs")
                    dr_col      = st.text_input("Match Column",   placeholder="e.g. Student Name")
                    dr_val      = st.text_input("Match Value",    placeholder="e.g. Alice Nakamura")
                    dr_all      = st.checkbox("Delete ALL matching rows (default: first match only)")
                    if st.form_submit_button(" Delete Row(s)", use_container_width=True,
                                             type="secondary"):
                        if not dr_sheet.strip() or not dr_col.strip() or not dr_val.strip():
                            st.warning("All three fields are required.")
                        else:
                            with st.spinner("Deleting..."):
                                r = db.delete_row(
                                    dr_sheet.strip(), dr_col.strip(),
                                    dr_val.strip(), dr_all
                                )
                            if r.get("status") == "success":
                                st.success(f" Deleted {r.get('deleted', 1)} row(s).")
                            else:
                                st.error(f" {r.get('message','Failed')}")

        # 
        #  FUNCTION LIBRARY
        # 
        with adv_tabs[3]:
            st.markdown("####  GAS Function Library")
            st.info(
                "Save custom Google Apps Script snippets to your **FunctionLibrary** sheet, "
                "then run them on demand via the backend. "
                "Functions receive `params`, `ss`, `nowTs`, `findCol`, `formatTs`, "
                "and `notifyClassWhatsApp` as arguments."
            )

            fl_tabs = st.tabs([" Saved Functions", " Save / Edit", " Run"])

            with fl_tabs[0]:
                if st.button(" Refresh", key="refresh_funcs"):
                    st.session_state["funcs_list"] = db.list_functions()
                if "funcs_list" not in st.session_state:
                    st.session_state["funcs_list"] = db.list_functions()

                funcs = st.session_state.get("funcs_list", [])
                if funcs:
                    for fn in funcs:
                        fname  = fn.get("Name",        fn.get("name", ""))
                        fdesc  = fn.get("Description", fn.get("description", ""))
                        fts    = fn.get("Last Updated", fn.get("last_updated", ""))
                        fscript= fn.get("Script",      fn.get("script", ""))
                        with st.expander(f" {fname}"):
                            if fdesc: st.caption(fdesc)
                            if fts:   st.caption(f"Last updated: {fts}")
                            st.code(fscript, language="javascript")
                else:
                    st.info("No functions saved yet.")

            with fl_tabs[1]:
                st.markdown("**Save or update a function**")
                with st.form("save_func_form", clear_on_submit=True):
                    fn_name   = st.text_input("Function Name", placeholder="e.g. countAttendance")
                    fn_desc   = st.text_input("Description",   placeholder="What this function does")
                    fn_script = st.text_area(
                        "JavaScript body (no function wrapper needed)",
                        height=200,
                        placeholder=(
                            "// Example: count rows in a sheet\n"
                            "var sheet = ss.getSheetByName('Roster');\n"
                            "return sheet ? sheet.getLastRow() - 1 : 0;"
                        )
                    )
                    if st.form_submit_button(" Save Function", use_container_width=True):
                        if not fn_name.strip() or not fn_script.strip():
                            st.warning("Name and script are required.")
                        else:
                            with st.spinner("Saving..."):
                                r = db.save_function(
                                    fn_name.strip(), fn_script.strip(), fn_desc.strip()
                                )
                            if r.get("status") == "success":
                                st.success(f" Function '{fn_name}' saved!")
                                st.session_state["funcs_list"] = db.list_functions()
                                st.rerun()
                            else:
                                st.error(f" {r.get('message','Failed')}")

            with fl_tabs[2]:
                st.markdown("**Run a saved function**")
                funcs = st.session_state.get("funcs_list", [])
                func_names = [f.get("Name", f.get("name", "")) for f in funcs]

                if not func_names:
                    st.info("No saved functions yet. Save one in the 'Save / Edit' tab first.")
                else:
                    sel_func = st.selectbox("Select Function", ["— Select —"] + func_names,
                                             key="run_func_sel")
                    if sel_func and sel_func != "— Select —":
                        params_json = st.text_area(
                            "Params (JSON, optional)",
                            value="{}",
                            height=80,
                            help='e.g. {"dept": "CSC", "year": "Year 1"}'
                        )
                        if st.button(" Run Function", use_container_width=True,
                                     key="run_func_btn", type="primary"):
                            try:
                                params_dict = json.loads(params_json)
                            except Exception:
                                st.error(" Invalid JSON in params.")
                                params_dict = None

                            if params_dict is not None:
                                with st.spinner("Running..."):
                                    r = db.run_function(sel_func, params_dict)
                                if r.get("status") == "success":
                                    st.success(" Function executed.")
                                    result_val = r.get("result", "")
                                    st.markdown("**Result:**")
                                    if isinstance(result_val, (dict, list)):
                                        st.json(result_val)
                                    else:
                                        st.code(str(result_val))
                                else:
                                    st.error(f" {r.get('message','Runtime error')}")

        # 
        #  SLOT CONFIGURATOR
        # 
        with adv_tabs[4]:
            render_slot_configurator(db)

        # 
    #  MASTER SUPER ADMIN AI  (tabs[8])
    # 
    with tabs[8]:
        st.markdown("###  Master Super Admin AI")

        # Init master AI if not passed
        if master_ai is None:
            master_ai = MasterSuperAdminAI()

        # Init chat history in session
        if "master_ai_history" not in st.session_state:
            st.session_state.master_ai_history = []

        #  Greeting on first load only 
        if "master_ai_greeted" not in st.session_state and len(st.session_state.master_ai_history) == 0:
            with st.spinner(" Master AI initializing..."):
                greeting = master_ai.get_greeting(df_all, reps_list)
            st.session_state.master_ai_history.append({
                "role": "assistant",
                "content": greeting
            })
            st.session_state.master_ai_greeted = True
        #  Status bar 
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{ADMIN_PRIMARY} 0%,{ADMIN_ACCENT} 100%);
            border-radius:12px;padding:12px 20px;margin-bottom:16px;
            display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
            <div style="color:white;font-weight:700;font-size:0.95rem;">
                 Master AI — Layer 1 Active
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <span style="background:rgba(255,255,255,0.15);color:white;
                    font-size:0.72rem;font-weight:600;padding:3px 10px;border-radius:10px;">
                     Chat Interface
                </span>
                <span style="background:rgba(255,255,255,0.15);color:white;
                    font-size:0.72rem;font-weight:600;padding:3px 10px;border-radius:10px;">
                     {len([i for i in range(1,20) if st.secrets.get(f"GEMINI_KEY_{i}","")])} Key(s) Active
                </span>
                <span style="background:rgba(255,255,255,0.15);color:white;
                    font-size:0.72rem;font-weight:600;padding:3px 10px;border-radius:10px;">
                     {len(st.session_state.master_ai_history)} Messages
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        #  Chat history display 
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.master_ai_history:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
                        <div style="background:{ADMIN_ACCENT};color:white;border-radius:18px 18px 4px 18px;
                            padding:10px 16px;max-width:80%;font-size:0.88rem;line-height:1.5;">
                            {msg["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="display:flex;justify-content:flex-start;margin-bottom:10px;">
                        <div style="background:white;border:1px solid #e2e8f7;
                            border-radius:18px 18px 18px 4px;
                            padding:10px 16px;max-width:85%;font-size:0.88rem;line-height:1.5;
                            color:#1e293b;box-shadow:0 1px 4px rgba(0,0,0,0.05);">
                            {msg["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        #  Pending Action Forms 
        pending_form = st.session_state.get("master_ai_pending_form")
        if pending_form:
            form_type = pending_form.get("type")

            #  ADD DEPARTMENT 
            if form_type == "add_department":
                st.markdown(f"""
                <div style="background:#f0fdf4;border:2px solid #16a34a;
                    border-radius:14px;padding:16px 20px;margin-bottom:16px;">
                    <div style="font-weight:800;color:#15803d;font-size:1rem;">
                         Add New Department
                    </div>
                    <div style="font-size:0.85rem;color:#166534;margin-top:4px;">
                        Fill in the details below and confirm to add.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                with st.form("master_ai_add_dept_form", clear_on_submit=True):
                    fd1, fd2 = st.columns(2)
                    with fd1:
                        dept_code    = st.text_input("Department Code", placeholder="e.g. CVL")
                        dept_name_in = st.text_input("Full Name", placeholder="e.g. Civil Engineering")
                    with fd2:
                        dept_courses_in = st.text_input("Course Codes (comma separated)", placeholder="e.g. BCIV,BSTR,BENV")
                        colour_names  = [p["name"] for p in COLOUR_PALETTE]
                        chosen_colour = st.selectbox("Colour", colour_names, key="ai_dept_colour")
                        chosen_pal    = next(p for p in COLOUR_PALETTE if p["name"] == chosen_colour)
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        confirm_dept = st.form_submit_button(" Confirm & Add Department", use_container_width=True, type="primary")
                    with fc2:
                        cancel_dept = st.form_submit_button(" Cancel", use_container_width=True)
                    if confirm_dept:
                        if not dept_code.strip() or not dept_name_in.strip() or not dept_courses_in.strip():
                            st.warning("Please fill in all fields.")
                        else:
                            with st.spinner("Adding department..."):
                                ok = db.add_department(
                                    dept_code.strip().upper(),
                                    dept_name_in.strip(),
                                    chosen_pal["hex"],
                                    chosen_pal["light"],
                                    dept_courses_in.strip()
                                )
                            if ok:
                                st.session_state["master_ai_pending_form"] = None
                                st.session_state.master_ai_history.append({
                                    "role": "assistant",
                                    "content": f" Department **{dept_name_in.strip()}** ({dept_code.strip().upper()}) added successfully!"
                                })
                                st.rerun()
                            else:
                                st.error(" Failed to add department. Check your GAS deployment.")
                    if cancel_dept:
                        st.session_state["master_ai_pending_form"] = None
                        st.session_state.master_ai_history.append({"role": "assistant", "content": " Department creation cancelled."})
                        st.rerun()

            #  ASSIGN REP 
            elif form_type == "assign_rep":
                st.markdown(f"""
                <div style="background:#eff6ff;border:2px solid #1a56db;
                    border-radius:14px;padding:16px 20px;margin-bottom:16px;">
                    <div style="font-weight:800;color:#1e40af;font-size:1rem;">
                         Assign Class Rep
                    </div>
                </div>
                """, unsafe_allow_html=True)
                with st.form("master_ai_assign_rep_form", clear_on_submit=True):
                    dept_opts = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
                    fr1, fr2 = st.columns(2)
                    with fr1:
                        r_dept_label = st.selectbox("Department", list(dept_opts.keys()), key="ai_rep_dept")
                        r_dept       = dept_opts[r_dept_label]
                        r_year       = st.selectbox("Year Group", YEARS, key="ai_rep_year")
                        r_name       = st.text_input("Rep Full Name", placeholder="e.g. Alice Nakamura")
                    with fr2:
                        r_reg  = st.text_input("Rep Reg Number", placeholder="e.g. 25/U/0001/PS")
                        r_pw   = st.text_input("Password", type="password", placeholder="Min 6 characters")
                        r_pw2  = st.text_input("Confirm Password", type="password")
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        confirm_rep = st.form_submit_button(" Confirm & Assign Rep", use_container_width=True, type="primary")
                    with fc2:
                        cancel_rep = st.form_submit_button(" Cancel", use_container_width=True)
                    if confirm_rep:
                        if not r_name.strip() or not r_reg.strip() or not r_pw:
                            st.warning("Please fill in all fields.")
                        elif r_pw != r_pw2:
                            st.error(" Passwords do not match.")
                        elif len(r_pw) < 6:
                            st.error(" Password must be at least 6 characters.")
                        else:
                            with st.spinner("Assigning rep..."):
                                ok = db.assign_rep(r_dept, r_year, r_name.strip(), r_reg.strip(), r_pw)
                            if ok:
                                st.session_state["master_ai_pending_form"] = None
                                st.session_state.master_ai_history.append({
                                    "role": "assistant",
                                    "content": f" Class Rep **{r_name.strip()}** assigned to **{r_dept_label} — {r_year}** successfully!"
                                })
                                st.rerun()
                            else:
                                st.error(" Failed to assign rep.")
                    if cancel_rep:
                        st.session_state["master_ai_pending_form"] = None
                        st.rerun()

            #  DELETE DEPARTMENT 
            elif form_type == "delete_department":
                st.error(" Delete Department — This cannot be undone!")
                with st.form("master_ai_del_dept_form"):
                    depts     = get_departments()
                    dept_opts = {f"{v['name']} ({k})": k for k, v in depts.items()}
                    d_label   = st.selectbox("Select Department to Delete", list(dept_opts.keys()), key="ai_del_dept")
                    sel_dept  = dept_opts[d_label]
                    st.warning(f"You are about to permanently delete **{d_label}**.")
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        if st.form_submit_button(" Confirm Delete", use_container_width=True, type="primary"):
                            with st.spinner("Deleting..."):
                                result = db.delete_department(sel_dept)
                            if result.get("status") == "success":
                                st.session_state["master_ai_pending_form"] = None
                                st.session_state.master_ai_history.append({
                                    "role": "assistant",
                                    "content": f" Department **{d_label}** deleted successfully."
                                })
                                st.rerun()
                            else:
                                st.error(f" {result.get('message','Failed')}")
                    with fc2:
                        if st.form_submit_button(" Cancel", use_container_width=True):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  DELETE REP 
            elif form_type == "delete_rep":
                st.error(" Remove Class Rep — This cannot be undone!")
                with st.form("master_ai_del_rep_form"):
                    rep_labels = {
                        f"{r.get('rep_name','')} — {r.get('dept','')} {r.get('year','')}": r
                        for r in reps_list
                    }
                    if rep_labels:
                        sel_rep_label = st.selectbox("Select Rep to Remove", list(rep_labels.keys()), key="ai_del_rep")
                        sel_rep = rep_labels[sel_rep_label]
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            if st.form_submit_button(" Confirm Remove", use_container_width=True, type="primary"):
                                with st.spinner("Removing..."):
                                    ok = db.delete_rep(str(sel_rep.get("dept","")), str(sel_rep.get("year","")))
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": f" Rep **{sel_rep_label}** removed successfully."
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed to remove rep.")
                        with fc2:
                            if st.form_submit_button(" Cancel", use_container_width=True):
                                st.session_state["master_ai_pending_form"] = None
                                st.rerun()
                    else:
                        st.info("No rep accounts found.")
                        if st.form_submit_button(" Close"):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  RESET REP PASSWORD 
            elif form_type == "reset_rep_password":
                st.info(" Reset Rep Password")
                with st.form("master_ai_reset_pw_form"):
                    rep_labels = {
                        f"{r.get('rep_name','')} — {r.get('dept','')} {r.get('year','')}": r
                        for r in reps_list
                    }
                    if rep_labels:
                        sel_label = st.selectbox("Select Rep", list(rep_labels.keys()), key="ai_reset_rep")
                        sel_rep   = rep_labels[sel_label]
                        new_pw    = st.text_input("New Password", type="password")
                        new_pw2   = st.text_input("Confirm Password", type="password")
                        fc1, fc2  = st.columns(2)
                        with fc1:
                            if st.form_submit_button(" Reset Password", use_container_width=True, type="primary"):
                                if not new_pw or new_pw != new_pw2:
                                    st.error(" Passwords don't match.")
                                elif len(new_pw) < 6:
                                    st.error(" Min 6 characters.")
                                else:
                                    with st.spinner("Resetting..."):
                                        ok = db.assign_rep(
                                            dept=str(sel_rep.get("dept","")),
                                            year=str(sel_rep.get("year","")),
                                            rep_name=str(sel_rep.get("rep_name","")),
                                            rep_reg=str(sel_rep.get("rep_reg","")),
                                            password=new_pw
                                        )
                                    if ok:
                                        st.session_state["master_ai_pending_form"] = None
                                        st.session_state.master_ai_history.append({
                                            "role": "assistant",
                                            "content": f" Password reset for **{sel_label}**."
                                        })
                                        st.rerun()
                                    else:
                                        st.error(" Failed.")
                        with fc2:
                            if st.form_submit_button(" Cancel", use_container_width=True):
                                st.session_state["master_ai_pending_form"] = None
                                st.rerun()
                    else:
                        st.info("No rep accounts found.")
                        if st.form_submit_button(" Close"):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  BROADCAST ANNOUNCEMENT 
            elif form_type == "broadcast_announcement":
                st.info(" Broadcast to All Departments")
                with st.form("master_ai_broadcast_form"):
                    b_text     = st.text_area("Announcement", height=120)
                    b_priority = st.selectbox("Priority", ["Normal","Urgent"], key="ai_bc_pri")
                    fc1, fc2   = st.columns(2)
                    with fc1:
                        if st.form_submit_button(" Broadcast Now", use_container_width=True, type="primary"):
                            if not b_text.strip():
                                st.warning("Please enter announcement text.")
                            else:
                                with st.spinner("Broadcasting..."):
                                    ok = db.broadcast_announcement(b_text.strip(), b_priority)
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": " Broadcast sent to all departments successfully!"
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed.")
                    with fc2:
                        if st.form_submit_button(" Cancel", use_container_width=True):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  POST ANNOUNCEMENT 
            elif form_type == "post_announcement":
                st.info(" Post Department Announcement")
                with st.form("master_ai_post_ann_form"):
                    dept_opts  = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
                    fa1, fa2   = st.columns(2)
                    with fa1:
                        a_dept_label = st.selectbox("Department", list(dept_opts.keys()), key="ai_ann_dept")
                        a_dept       = dept_opts[a_dept_label]
                    with fa2:
                        a_year     = st.selectbox("Year Group", ["ALL"] + YEARS, key="ai_ann_year")
                        a_priority = st.selectbox("Priority", ["Normal","Urgent"], key="ai_ann_pri")
                    a_text = st.text_area("Announcement Text", height=120)
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        if st.form_submit_button(" Post Announcement", use_container_width=True, type="primary"):
                            if not a_text.strip():
                                st.warning("Please enter text.")
                            else:
                                with st.spinner("Posting..."):
                                    ok = db.post_announcement(a_text.strip(), a_priority, a_dept, a_year)
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": f" Announcement posted to **{a_dept_label} — {a_year}**!"
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed.")
                    with fc2:
                        if st.form_submit_button(" Cancel", use_container_width=True):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  DELETE STUDENT 
            elif form_type == "delete_student":
                st.error(" Remove Student — This cannot be undone!")
                with st.form("master_ai_del_student_form"):
                    if df_all is not None and not df_all.empty:
                        student_labels = {
                            f"{r.get('Student Name','')} — {r.get('Reg Number','')}": r.get('Reg Number','')
                            for _, r in df_all.iterrows()
                        }
                        sel_s_label = st.selectbox("Select Student", list(student_labels.keys()), key="ai_del_student")
                        sel_s_reg   = student_labels[sel_s_label]
                        st.warning(f"Remove **{sel_s_label}**?")
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            if st.form_submit_button(" Confirm Remove", use_container_width=True, type="primary"):
                                with st.spinner("Removing..."):
                                    ok = db.delete_student(sel_s_reg)
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": f" Student **{sel_s_label}** removed."
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed.")
                        with fc2:
                            if st.form_submit_button(" Cancel", use_container_width=True):
                                st.session_state["master_ai_pending_form"] = None
                                st.rerun()
                    else:
                        st.info("No students registered yet.")
                        if st.form_submit_button(" Close"):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  ASSIGN GROUP 
            elif form_type == "assign_group":
                st.info(" Assign Student to Group")
                with st.form("master_ai_assign_group_form"):
                    if df_all is not None and not df_all.empty:
                        student_labels = {
                            f"{r.get('Student Name','')} — {r.get('Reg Number','')}": r.get('Reg Number','')
                            for _, r in df_all.iterrows()
                        }
                        sel_s_label = st.selectbox("Select Student", list(student_labels.keys()), key="ai_grp_student")
                        sel_s_reg   = student_labels[sel_s_label]
                        group_name  = st.text_input("Group Name", placeholder="e.g. Team Alpha")
                        fc1, fc2    = st.columns(2)
                        with fc1:
                            if st.form_submit_button(" Assign Group", use_container_width=True, type="primary"):
                                if not group_name.strip():
                                    st.warning("Please enter a group name.")
                                else:
                                    with st.spinner("Assigning..."):
                                        ok = db.assign_group(sel_s_reg, group_name.strip())
                                    if ok:
                                        st.session_state["master_ai_pending_form"] = None
                                        st.session_state.master_ai_history.append({
                                            "role": "assistant",
                                            "content": f" **{sel_s_label}** assigned to **{group_name.strip()}**!"
                                        })
                                        st.rerun()
                                    else:
                                        st.error(" Failed.")
                        with fc2:
                            if st.form_submit_button(" Cancel", use_container_width=True):
                                st.session_state["master_ai_pending_form"] = None
                                st.rerun()
                    else:
                        st.info("No students registered yet.")
                        if st.form_submit_button(" Close"):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  POST TIMETABLE 
            elif form_type == "post_timetable":
                st.info(" Add Timetable Entry")
                with st.form("master_ai_post_tt_form"):
                    dept_opts    = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
                    ft1, ft2     = st.columns(2)
                    with ft1:
                        t_dept_label = st.selectbox("Department", list(dept_opts.keys()), key="ai_tt_dept")
                        t_dept       = dept_opts[t_dept_label]
                        t_year       = st.selectbox("Year Group", YEARS, key="ai_tt_year")
                        t_day        = st.selectbox("Day", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], key="ai_tt_day")
                    with ft2:
                        t_time     = st.text_input("Time", placeholder="e.g. 08:00 - 10:00")
                        t_course   = st.text_input("Course", placeholder="e.g. Engineering Mathematics")
                        t_lecturer = st.text_input("Lecturer", placeholder="e.g. Dr. Ouma")
                        t_venue    = st.text_input("Venue", placeholder="e.g. LR 3")
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        if st.form_submit_button(" Add Entry", use_container_width=True, type="primary"):
                            if not t_time.strip() or not t_course.strip():
                                st.warning("Time and Course are required.")
                            else:
                                with st.spinner("Adding..."):
                                    ok = db.add_timetable_entry(
                                        dept=t_dept, year=t_year,
                                        day=t_day, time=t_time.strip(),
                                        course=t_course.strip(),
                                        lecturer=t_lecturer.strip(),
                                        venue=t_venue.strip()
                                    )
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": f" Timetable entry added — **{t_day} {t_time}** | {t_course} for {t_dept_label} {t_year}!"
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed.")
                    with fc2:
                        if st.form_submit_button(" Cancel", use_container_width=True):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  DELETE TIMETABLE 
            elif form_type == "delete_timetable":
                st.error(" Delete Timetable Entry")
                with st.form("master_ai_del_tt_form"):
                    dept_opts    = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
                    dt1, dt2     = st.columns(2)
                    with dt1:
                        dt_dept_label = st.selectbox("Department", list(dept_opts.keys()), key="ai_del_tt_dept")
                        dt_dept       = dept_opts[dt_dept_label]
                    with dt2:
                        dt_year = st.selectbox("Year Group", YEARS, key="ai_del_tt_year")
                        dt_day  = st.selectbox("Day", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], key="ai_del_tt_day")
                    dt_course = st.text_input("Course Name to Delete", placeholder="e.g. Engineering Mathematics")
                    fc1, fc2  = st.columns(2)
                    with fc1:
                        if st.form_submit_button(" Confirm Delete", use_container_width=True, type="primary"):
                            if not dt_course.strip():
                                st.warning("Please enter the course name.")
                            else:
                                with st.spinner("Deleting..."):
                                    ok = db.delete_timetable_entry(dt_dept, dt_year, dt_day, dt_course.strip())
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": f" Timetable entry deleted — {dt_course} on {dt_day} for {dt_dept_label} {dt_year}."
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed.")
                    with fc2:
                        if st.form_submit_button(" Cancel", use_container_width=True):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  NOTIFY CLASS 
            elif form_type == "notify_class":
                st.info(" Send WhatsApp Notification to Class")
                with st.form("master_ai_notify_form"):
                    dept_opts    = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
                    fn1, fn2     = st.columns(2)
                    with fn1:
                        n_dept_label = st.selectbox("Department", ["ALL DEPARTMENTS"] + list(dept_opts.keys()), key="ai_notify_dept")
                        n_dept       = "ALL" if n_dept_label == "ALL DEPARTMENTS" else dept_opts[n_dept_label]
                    with fn2:
                        n_year = st.selectbox("Year Group", ["ALL"] + YEARS, key="ai_notify_year")
                    n_msg = st.text_area("Message", height=120, placeholder="Type your WhatsApp message here...")
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        if st.form_submit_button(" Send Notification", use_container_width=True, type="primary"):
                            if not n_msg.strip():
                                st.warning("Please enter a message.")
                            else:
                                with st.spinner("Sending..."):
                                    ok = db.notify_class_whatsapp(n_dept, n_year, n_msg.strip())
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": f" WhatsApp notification sent to **{n_dept_label} — {n_year}**!"
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed. Check WhatsApp configuration.")
                    with fc2:
                        if st.form_submit_button(" Cancel", use_container_width=True):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()

            #  DELETE ANNOUNCEMENT 
            elif form_type == "delete_announcement":
                st.error(" Delete Announcement")
                with st.form("master_ai_del_ann_form"):
                    if all_anns:
                        ann_labels = {
                            f"[{a.get('timestamp','')[:16]}] {a.get('text','')[:60]}": i
                            for i, a in enumerate(all_anns[:30])
                            if isinstance(a, dict)
                        }
                        sel_ann_label = st.selectbox("Select Announcement", list(ann_labels.keys()), key="ai_del_ann")
                        sel_ann_idx   = ann_labels[sel_ann_label]
                        sel_ann       = all_anns[sel_ann_idx]
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            if st.form_submit_button(" Confirm Delete", use_container_width=True, type="primary"):
                                with st.spinner("Deleting..."):
                                    ok = db.delete_announcement(sel_ann.get("timestamp",""), sel_ann.get("dept",""))
                                if ok:
                                    st.session_state["master_ai_pending_form"] = None
                                    st.session_state.master_ai_history.append({
                                        "role": "assistant",
                                        "content": " Announcement deleted successfully."
                                    })
                                    st.rerun()
                                else:
                                    st.error(" Failed.")
                        with fc2:
                            if st.form_submit_button(" Cancel", use_container_width=True):
                                st.session_state["master_ai_pending_form"] = None
                                st.rerun()
                    else:
                        st.info("No announcements found.")
                        if st.form_submit_button(" Close"):
                            st.session_state["master_ai_pending_form"] = None
                            st.rerun()
        #  Pending code change approval UI 
        pending = st.session_state.get("master_ai_pending_change")
        if pending and pending.get("status") == "pending_approval":
            st.markdown(f"""
            <div style="background:#fefce8;border:2px solid #eab308;
                border-radius:14px;padding:16px 20px;margin-bottom:16px;">
                <div style="font-weight:800;color:#854d0e;font-size:1rem;margin-bottom:6px;">
                     Pending Code Change — Awaiting Your Approval
                </div>
                <div style="font-size:0.85rem;color:#713f12;">
                    File: <strong>{pending['target_file']}</strong><br>
                    Request: {pending['request']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            #  Validation result 
            validation = pending.get("validation", {})
            if validation:
                if validation.get("valid"):
                    st.success(validation["summary"])
                    st.caption(
                        f" Lines: {validation.get('lines_original',0)} → "
                        f"{validation.get('lines_new',0)} | "
                        f" Functions preserved: {validation.get('funcs_preserved',0)}"
                    )
                else:
                    st.error(validation["summary"])
                    for issue in validation.get("issues", []):
                        st.warning(issue)
                    st.info(" The AI attempted to auto-fix these issues. Review the code carefully before approving.")

            with st.expander(" Preview Proposed Code", expanded=False):
                st.code(pending["new_code"], language="python")

            col_local, col_github = st.columns(2)

            #  Step 1: Test Locally 
            with col_local:
                validation = pending.get("validation", {})
                can_proceed = validation.get("valid", True)
                if st.button(" Test Locally First",
                             use_container_width=True,
                             type="primary",
                             key="test_locally",
                             disabled=not can_proceed):
                    if not can_proceed:
                        st.error(" Cannot save — validation failed. Review issues above.")
                    else:
                        with st.spinner(" Saving locally..."):
                            result = master_ai.save_locally(
                            pending["target_file"],
                            pending["new_code"]
                        )
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(result["message"])
                        if result.get("backup_created"):
                            st.info(f" Backup saved: `{result['backup_name']}`")
                        # Mark as locally tested
                        st.session_state["master_ai_pending_change"]["status"] = "locally_tested"
                        st.session_state["master_ai_pending_change"]["backup_name"] = result.get("backup_name")
                        st.session_state.master_ai_history.append({
                            "role"   : "assistant",
                            "content": (
                                f" `{pending['target_file']}` saved locally! "
                                f"Streamlit is reloading with the new code. "
                                f"Test it now — if it looks good, click **Deploy to GitHub** to make it permanent. "
                                f"If something is wrong, click **Rollback** to restore the original instantly."
                            )
                        })
                        st.rerun()

            #  Step 2: Deploy to GitHub 
            with col_github:
                tested = pending.get("status") == "locally_tested"
                is_gas = pending.get("type") == "gas"
                deploy_label = (
                    " Push to Apps Script" if is_gas
                    else " Deploy to GitHub" if tested
                    else " Skip Test & Deploy"
                )
                if st.button(
                    deploy_label,
                    use_container_width=True,
                    type="primary" if (tested or is_gas) else "secondary",
                    key="approve_code_change"
                ):
                    with st.spinner(" Deploying..."):
                        if is_gas:
                            result = master_ai.gas_editor.write_file(
                                pending["target_file"],
                                pending["new_code"]
                            )
                        else:
                            result = master_ai.deploy_code_change(
                                pending["target_file"],
                                pending["new_code"]
                            )
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(result["message"])
                        st.session_state["master_ai_last_backup"] = {
                            "file"   : pending["target_file"],
                            "content": pending["original_code"],
                            "type"   : pending.get("type","python")
                        }
                        st.session_state["master_ai_pending_change"] = None
                        st.session_state.master_ai_history.append({
                            "role"   : "assistant",
                            "content": (
                                f" `{pending['target_file']}` deployed to "
                                f"{'Apps Script' if is_gas else 'GitHub'} successfully!"
                            )
                        })
                        st.rerun()

            #  Reject 
            #  Reject 
            if st.button(" Reject and Restore Original",
                         use_container_width=True,
                         key="reject_code_change"):
                    # If locally tested, restore backup automatically
                    backup_name = pending.get("backup_name")
                    if backup_name:
                        try:
                            import shutil
                            shutil.copy2(backup_name, pending["target_file"])
                            import os
                            os.remove(backup_name)
                            restore_msg = f"↩ Original `{pending['target_file']}` restored automatically."
                        except Exception:
                            restore_msg = " Could not auto-restore — check your backup files."
                    else:
                        restore_msg = "No local changes were made."

                    st.session_state["master_ai_pending_change"] = None
                    st.session_state.master_ai_history.append({
                        "role"   : "assistant",
                        "content": f" Change rejected. {restore_msg}"
                    })
                    st.rerun()

           

            # Rollback option
            backup = st.session_state.get("master_ai_last_backup")
            if backup:
                st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
                st.markdown(f"** Last Backup:** `{backup['file']}`")
                if st.button("↩ Rollback to Previous Version",
                             key="rollback_btn",
                             use_container_width=True):
                    with st.spinner("Rolling back..."):
                        if backup.get("type") == "gas":
                            result = master_ai.gas_editor.write_file(
                                backup["file"],
                                backup["content"]
                            )
                        else:
                            result = master_ai.deploy_code_change(
                                backup["file"],
                                backup["content"]
                            )
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success(f" Rolled back `{backup['file']}` successfully!")
                        st.session_state["master_ai_last_backup"] = None
                        st.rerun()

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

    

        
        #  Input clear trick 
        if "master_ai_input_key" not in st.session_state:
            st.session_state.master_ai_input_key = 0

        col_input, col_send = st.columns([5, 1])
        with col_input:
            user_input = st.text_input(
                "Message",
                placeholder="Ask me anything about the portal...",
                label_visibility="collapsed",
                key=f"master_ai_input_{st.session_state.master_ai_input_key}"
            )
        with col_send:
            send_btn = st.button(" Send", use_container_width=True, type="primary")
        #  Quick action buttons 
        st.markdown("**Quick Actions:**")
        qc1, qc2, qc3, qc4, qc5,qc6 = st.columns(6)
        with qc1:
            if st.button(" Portal Status", use_container_width=True, key="qa_status"):
                user_input = "Give me a full status report of the portal right now."
                send_btn = True
        with qc2:
            if st.button(" Suggest Improvements", use_container_width=True, key="qa_suggest"):
                user_input = "Suggest improvements for the portal."
                send_btn = True
        with qc3:
            if st.button(" Analyze Students", use_container_width=True, key="qa_students"):
                user_input = "Analyze the current student enrollment and tell me what you see."
                send_btn = True
        with qc4:
            if st.button(" Audit Code", use_container_width=True, key="qa_audit"):
                user_input = "Analyze my code and tell me what's wrong and what can be improved."
                send_btn = True
        with qc5:
            if st.button(" Clear Chat", use_container_width=True, key="qa_clear"):
                st.session_state.master_ai_history = []
                st.session_state.master_ai_greeted = False
                st.rerun()
        with qc6:
            if st.button(" View Memory", use_container_width=True, key="qa_memory"):
                user_input = "Show me everything you remember about me and the portal."
                send_btn = True
        #  Memory Manager 
        with st.expander(" Memory Manager", expanded=False):
            st.caption("View and manage what the Master AI remembers about you and your portal.")

            mem_tabs = st.tabs([
                " Preferences", " Decisions",
                " Conversations", " Insights"
            ])

            memory_system = MasterAIMemorySystem(db)

            for tab_idx, mem_type in enumerate(["preference","decision","conversation","insight"]):
                with mem_tabs[tab_idx]:
                    memories = memory_system.load_type(mem_type)
                    if memories:
                        for mem in memories:
                            col_m, col_d = st.columns([5,1])
                            with col_m:
                                st.markdown(f"""
                                <div style="background:white;border-radius:8px;
                                    padding:10px 14px;margin-bottom:6px;
                                    border:1px solid #e2e8f7;
                                    border-left:3px solid {ADMIN_ACCENT};">
                                    <div style="font-size:0.75rem;color:#94a3b8;">
                                        {mem.get('timestamp','')[:16]}
                                    </div>
                                    <div style="font-weight:700;font-size:0.85rem;">
                                        {mem.get('key','')}
                                    </div>
                                    <div style="font-size:0.85rem;color:#475569;">
                                        {mem.get('value','')}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            with col_d:
                                if st.button("", key=f"del_mem_{mem_type}_{mem.get('key','')}"):
                                    db.delete_master_ai_memory(mem_type, mem.get('key',''))
                                    st.rerun()
                    else:
                        st.info(f"No {mem_type} memories yet.")

                    if memories:
                        if st.button(f" Clear All {mem_type.title()} Memories",
                                     key=f"clear_{mem_type}_mem",
                                     use_container_width=True):
                            db.clear_master_ai_memory(mem_type)
                            st.rerun()

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
            if st.button(" Save Current Conversation to Memory",
                         use_container_width=True, key="save_conv_mem"):
                if st.session_state.master_ai_history:
                    with st.spinner("Extracting memories..."):
                        result = memory_system.extract_and_save_memories(
                            st.session_state.master_ai_history, db
                        )
                    if result.get("saved", 0) > 0:
                        st.success(f" Saved {result['saved']} memory item(s)!")
                    else:
                        st.info("Nothing memorable found in this conversation.")
                else:
                    st.info("No conversation to save yet.")
            #  Monitor & Notifications 
        with st.expander(" Portal Monitor & Notifications", expanded=False):
            st.caption("Check portal health and send alerts to your WhatsApp/Telegram.")

            monitor = MasterAIMonitor(db)

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
            st.markdown("** GAS Code Reader:**")
            gas_files = master_ai.gas_editor.get_file_list()
            if gas_files:
                sel_gas_file = st.selectbox(
                    "Select GAS file to read",
                    gas_files,
                    key="gas_file_sel"
                )
                if st.button(" Read File", use_container_width=True, key="read_gas_btn"):
                    content = master_ai.gas_editor.read_file(sel_gas_file)
                    st.code(content, language="javascript")
            else:
                st.warning("GAS Editor not connected. Check credentials.")

            #  Health Check 
            if st.button(" Run Health Check",
                         use_container_width=True,
                         type="primary",
                         key="run_health_check"):
                with st.spinner("Checking portal health..."):
                    health = monitor.check_portal_health(
                        df_all=df_all,
                        reps_list=reps_list,
                        all_feedback=all_feedback,
                        all_anns=all_anns
                    )

                # Display results
                overall = health["overall"]
                if "" in overall:
                    st.error(overall)
                elif "" in overall:
                    st.warning(overall)
                else:
                    st.success(overall)

                if health["issues"]:
                    st.markdown("** Critical Issues:**")
                    for issue in health["issues"]:
                        st.error(issue)

                if health["warnings"]:
                    st.markdown("** Warnings:**")
                    for w in health["warnings"]:
                        st.warning(w)

                if health["healthy"]:
                    st.markdown("** Healthy:**")
                    for h in health["healthy"]:
                        st.success(h)

                # Store for sending
                st.session_state["last_health_check"] = health

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            #  Notification Channel 
            st.markdown("** Send Alert To:**")
            notif_channel = st.radio(
                "Channel",
                ["Both", "WhatsApp Only", "Telegram Only"],
                horizontal=True,
                key="notif_channel",
                label_visibility="collapsed"
            )
            channel_map = {
                "Both"          : "both",
                "WhatsApp Only" : "whatsapp",
                "Telegram Only" : "telegram"
            }
            selected_channel = channel_map[notif_channel]

            #  Send Daily Report 
            if st.button(" Send Daily Report",
                         use_container_width=True,
                         key="send_daily_report"):
                with st.spinner("Generating and sending report..."):
                    report = monitor.generate_daily_report(
                        df_all=df_all,
                        reps_list=reps_list,
                        all_feedback=all_feedback,
                        all_anns=all_anns
                    )
                    result = monitor.send_alert(report, selected_channel)

                st.markdown("** Report sent:**")
                st.code(report)

                for ch, res in result.items():
                    if "error" in res:
                        st.error(f"{ch}: {res['error']}")
                    else:
                        st.success(f" {ch.title()}: Sent successfully!")

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            #  Custom Alert 
            st.markdown("** Send Custom Alert:**")
            custom_msg = st.text_area(
                "Message",
                placeholder="Type your alert message...",
                height=80,
                key="custom_alert_msg",
                label_visibility="collapsed"
            )
            ca1, ca2 = st.columns(2)
            with ca1:
                if st.button(" Send Custom",
                             use_container_width=True,
                             key="send_custom_alert"):
                    if custom_msg.strip():
                        with st.spinner("Sending..."):
                            result = monitor.send_alert(
                                custom_msg.strip(), selected_channel
                            )
                        for ch, res in result.items():
                            if "error" in res:
                                st.error(f"{ch}: {res['error']}")
                            else:
                                st.success(f" {ch.title()}: Sent!")
                    else:
                        st.warning("Please type a message.")
            with ca2:
                if st.button(" AI Generate Alert",
                             use_container_width=True,
                             key="ai_gen_alert"):
                    health = st.session_state.get("last_health_check", {})
                    with st.spinner("AI generating alert..."):
                        ai_msg = monitor.ai_generate_alert(
                            event_type="portal_health_summary",
                            event_data=health.get("counts", {})
                        )
                    st.session_state["ai_generated_alert"] = ai_msg
                    st.rerun()

            if st.session_state.get("ai_generated_alert"):
                st.markdown("** AI Generated Alert — Edit before sending:**")
                edited_alert = st.text_area(
                    "",
                    value=st.session_state["ai_generated_alert"],
                    height=100,
                    key="edited_ai_alert",
                    label_visibility="collapsed"
                )
                if st.button(" Send This Alert",
                             use_container_width=True,
                             key="send_ai_alert"):
                    with st.spinner("Sending..."):
                        result = monitor.send_alert(edited_alert, selected_channel)
                    for ch, res in result.items():
                        if "error" in res:
                            st.error(f"{ch}: {res['error']}")
                        else:
                            st.success(f" {ch.title()}: Sent!")
                    st.session_state["ai_generated_alert"] = ""
                    st.rerun()

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            #  Auto-notify settings 
            st.markdown("** Auto Notification Triggers:**")
            st.caption("These fire automatically when conditions are met.")
            st.toggle(" Alert on critical issues",     value=True,  key="notif_critical",  disabled=True)
            st.toggle(" Alert on 5+ pending feedback", value=True,  key="notif_feedback",  disabled=True)
            st.toggle(" Daily morning report (8AM)",   value=False, key="notif_daily",     disabled=True)
            st.info(" Auto-triggers run via `notifier.py` scheduler. Enable them there.")

        #  Send message 
        if send_btn and user_input.strip():
            captured_input = user_input.strip()
            # Clear the input box by bumping the key
            st.session_state.master_ai_input_key += 1

            # Add user message to history
            st.session_state.master_ai_history.append({
                "role": "user",
                "content": captured_input
            })

            # Get AI response
            with st.spinner(" Master AI thinking..."):
                response = master_ai.chat(
                    user_message=captured_input,
                    chat_history=st.session_state.master_ai_history,
                    db=db,
                    df_all=df_all,
                    reps_list=reps_list,
                    all_feedback=all_feedback,
                    all_anns=all_anns
                )

            # Add response to history
            st.session_state.master_ai_history.append({
                "role": "assistant",
                "content": response
            })

            st.rerun()

    #  Logout 
    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
    if st.button(" Log Out"):
        st.session_state.admin_logged_in = False
        for k in ["admin_draft", "sheets_list", "config_data", "funcs_list", "slot_cfg_list", "new_slot_fields"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()