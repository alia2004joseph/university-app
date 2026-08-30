"""
engagement_ui.py — UI components for Class Representatives and Admins
to inspect student engagement, read receipts, and material check/download details.
"""
import streamlit as st
import pandas as pd
from database.avatars import render_avatar_html


def _clean_phone_for_wa(phone: str) -> str:
    """Format phone number for direct WhatsApp links."""
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        # Ugandan format 07... -> 2567...
        return "256" + digits[1:]
    return digits


def _render_student_card(s: dict, badge_text: str = "", badge_color: str = "#16a34a", badge_bg: str = "#dcfce7", primary: str = "#1e40af", light: str = "#eff6ff"):
    """Renders a single student profile row with contacts, group, and status."""
    name = s.get("name", "Unknown")
    reg = s.get("reg_number", "")
    email = s.get("email", "")
    phone = s.get("contact", "") or s.get("whatsapp_phone", "")
    course = s.get("course_code", "N/A")
    group = s.get("group", "Unassigned")
    avatar = s.get("avatar", "")
    avatar_html = render_avatar_html(avatar, name, size=42, color=primary, light=light)

    wa_phone = _clean_phone_for_wa(phone)
    wa_link = f"https://wa.me/{wa_phone}" if wa_phone else ""
    mail_link = f"mailto:{email}" if email else ""

    contact_parts = []
    if email:
        contact_parts.append(f'<a href="{mail_link}" style="color:{primary};text-decoration:none;font-weight:600;font-size:0.75rem;">✉️ {email}</a>')
    if phone:
        if wa_link:
            contact_parts.append(f'<a href="{wa_link}" target="_blank" style="color:#16a34a;text-decoration:none;font-weight:600;font-size:0.75rem;">📱 {phone} (WhatsApp)</a>')
        else:
            contact_parts.append(f'<span style="color:#475569;font-size:0.75rem;">📞 {phone}</span>')
    contact_html = " &nbsp;·&nbsp; ".join(contact_parts) if contact_parts else '<span style="color:#94a3b8;font-size:0.75rem;">No contact details provided</span>'

    badge_html = ""
    if badge_text:
        badge_html = f'<span style="background:{badge_bg};color:{badge_color};font-size:0.70rem;font-weight:700;padding:2px 8px;border-radius:12px;display:inline-block;margin-left:auto;">{badge_text}</span>'

    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin-bottom:8px;box-shadow:0 1px 2px rgba(0,0,0,0.02);display:flex;align-items:center;gap:12px;">
        <div style="flex-shrink:0;">{avatar_html}</div>
        <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-size:0.90rem;font-weight:700;color:#0f172a;">{name}</span>
                <span style="font-size:0.75rem;color:#64748b;font-weight:600;background:#f1f5f9;padding:1px 6px;border-radius:4px;">{reg}</span>
                {badge_html}
            </div>
            <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">
                <span>📚 <strong>{course}</strong></span> &nbsp;·&nbsp; <span>👥 Group: <strong>{group}</strong></span>
            </div>
            <div style="margin-top:4px;">{contact_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_announcement_engagement(db, ann: dict, dept: str, year: str, primary: str, light: str, key_prefix: str = "ann_eng"):
    """
    Renders the engagement bar and expandable student read/unread breakdown for an announcement.
    """
    ann_id = str(ann.get("id", "")) if isinstance(ann, dict) else ""
    ann_text = ann.get("text", "") if isinstance(ann, dict) else str(ann)
    
    analytics = db.get_announcement_read_analytics(announcement_id=ann_id, dept=dept, year=year, ann_text=ann_text)
    
    total = analytics.get("total_students", 0)
    read_count = analytics.get("read_count", 0)
    unread_count = analytics.get("unread_count", 0)
    pct = analytics.get("read_percentage", 0.0)
    read_students = analytics.get("read_students", [])
    unread_students = analytics.get("unread_students", [])

    # Visual progress bar
    fill_width = max(0, min(100, int(pct)))
    
    st.markdown(f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;margin:8px 0 10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:0.80rem;margin-bottom:6px;font-weight:600;">
            <span style="color:#0f172a;">📊 <strong>Student Read Engagement</strong></span>
            <span style="color:{'#16a34a' if pct >= 70 else primary};font-weight:800;">{read_count}/{total} Students ({pct}%)</span>
        </div>
        <div style="background:#e2e8f0;border-radius:6px;height:8px;overflow:hidden;width:100%;margin-bottom:6px;">
            <div style="background:{'#16a34a' if pct >= 70 else primary};width:{fill_width}%;height:100%;border-radius:6px;transition:width 0.3s ease;"></div>
        </div>
        <div style="display:flex;gap:12px;font-size:0.74rem;color:#64748b;">
            <span style="color:#16a34a;font-weight:700;">✅ {read_count} Read</span>
            <span style="color:#dc2626;font-weight:700;">⏳ {unread_count} Unread</span>
            <span style="margin-left:auto;color:#64748b;">Total Audience: {total}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"👥 View Read Receipts ({read_count} Read · {unread_count} Unread)", expanded=False):
        tab_read, tab_unread = st.tabs([
            f"✅ Read Students ({read_count})",
            f"⏳ Unread Students ({unread_count})"
        ])

        with tab_read:
            if not read_students:
                st.info("No students have read this announcement yet.")
            else:
                s_search = st.text_input("🔍 Search read students", placeholder="Name, reg, or group...", key=f"{key_prefix}_search_read")
                filtered_read = read_students
                if s_search:
                    q = s_search.lower()
                    filtered_read = [
                        s for s in read_students
                        if q in s.get("name", "").lower() or q in s.get("reg_number", "").lower() or q in s.get("group", "").lower()
                    ]
                st.caption(f"Showing {len(filtered_read)} of {len(read_students)} students who read this")
                for s in filtered_read:
                    time_label = f"Read: {s.get('read_at', '')}" if s.get("read_at") else "Read"
                    _render_student_card(s, badge_text=time_label, badge_color="#16a34a", badge_bg="#dcfce7", primary=primary, light=light)

        with tab_unread:
            if not unread_students:
                st.success("🎉 All registered students in this class have read this announcement!")
            else:
                s_search_u = st.text_input("🔍 Search unread students", placeholder="Name, reg, or group...", key=f"{key_prefix}_search_unread")
                filtered_unread = unread_students
                if s_search_u:
                    q = s_search_u.lower()
                    filtered_unread = [
                        s for s in unread_students
                        if q in s.get("name", "").lower() or q in s.get("reg_number", "").lower() or q in s.get("group", "").lower()
                    ]
                st.caption(f"Showing {len(filtered_unread)} of {len(unread_students)} students who haven't read yet")
                for s in filtered_unread:
                    _render_student_card(s, badge_text="Pending", badge_color="#b45309", badge_bg="#fef3c7", primary=primary, light=light)


def render_material_engagement(db, mat: dict, dept: str, year: str, primary: str, light: str, key_prefix: str = "mat_eng"):
    """
    Renders the access bar and expandable student access/download details for course material.
    """
    mat_id = str(mat.get("id", "")) if isinstance(mat, dict) else ""
    file_name = mat.get("name", "Unnamed") if isinstance(mat, dict) else str(mat)
    
    analytics = db.get_material_access_analytics(material_id=mat_id, dept=dept, year=year, file_name=file_name)

    total = analytics.get("total_students", 0)
    acc_count = analytics.get("accessed_count", 0)
    unacc_count = analytics.get("unaccessed_count", 0)
    pct = analytics.get("accessed_percentage", 0.0)
    acc_students = analytics.get("accessed_students", [])
    unacc_students = analytics.get("unaccessed_students", [])

    fill_width = max(0, min(100, int(pct)))

    st.markdown(f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;margin:8px 0 10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:0.80rem;margin-bottom:6px;font-weight:600;">
            <span style="color:#0f172a;">📊 <strong>Material Access & Downloads</strong></span>
            <span style="color:{primary};font-weight:800;">{acc_count}/{total} Students ({pct}%)</span>
        </div>
        <div style="background:#e2e8f0;border-radius:6px;height:8px;overflow:hidden;width:100%;margin-bottom:6px;">
            <div style="background:{primary};width:{fill_width}%;height:100%;border-radius:6px;transition:width 0.3s ease;"></div>
        </div>
        <div style="display:flex;gap:12px;font-size:0.74rem;color:#64748b;">
            <span style="color:{primary};font-weight:700;">📥 {acc_count} Checked</span>
            <span style="color:#dc2626;font-weight:700;">⏳ {unacc_count} Not Checked</span>
            <span style="margin-left:auto;color:#64748b;">Total Students: {total}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"👥 View Access Details ({acc_count} Checked · {unacc_count} Not Checked)", expanded=False):
        tab_acc, tab_unacc = st.tabs([
            f"📥 Checked ({acc_count})",
            f"⏳ Not Checked ({unacc_count})"
        ])

        with tab_acc:
            if not acc_students:
                st.info("No students have opened or downloaded this material yet.")
            else:
                m_search = st.text_input("🔍 Search checked students", placeholder="Name, reg, or group...", key=f"{key_prefix}_search_acc")
                filtered_acc = acc_students
                if m_search:
                    q = m_search.lower()
                    filtered_acc = [
                        s for s in acc_students
                        if q in s.get("name", "").lower() or q in s.get("reg_number", "").lower() or q in s.get("group", "").lower()
                    ]
                st.caption(f"Showing {len(filtered_acc)} of {len(acc_students)} students who checked this file")
                for s in filtered_acc:
                    action_tag = s.get("action", "Viewed")
                    time_val = s.get("accessed_at", "")
                    badge_label = f"{action_tag} · {time_val}" if time_val else action_tag
                    _render_student_card(s, badge_text=badge_label, badge_color="#1d4ed8", badge_bg="#dbeafe", primary=primary, light=light)

        with tab_unacc:
            if not unacc_students:
                st.success("🎉 All registered students have accessed this course material!")
            else:
                m_search_u = st.text_input("🔍 Search students who haven't checked", placeholder="Name, reg, or group...", key=f"{key_prefix}_search_unacc")
                filtered_unacc = unacc_students
                if m_search_u:
                    q = m_search_u.lower()
                    filtered_unacc = [
                        s for s in unacc_students
                        if q in s.get("name", "").lower() or q in s.get("reg_number", "").lower() or q in s.get("group", "").lower()
                    ]
                st.caption(f"Showing {len(filtered_unacc)} of {len(unacc_students)} students pending")
                for s in filtered_unacc:
                    _render_student_card(s, badge_text="Not Checked", badge_color="#b45309", badge_bg="#fef3c7", primary=primary, light=light)


def render_class_engagement_overview(db, dept: str, year: str, primary: str, light: str, announcements: list, materials: list, total_students: int):
    """
    Renders high-level class participation dashboard for the Class Rep.
    """
    st.markdown("### 📊 Class Engagement & Participation")
    st.info(f"Engagement intelligence across all notices and materials for **{dept} — {year}**.")

    # 1. Metric highlights
    c1, c2, c3 = st.columns(3)
    
    total_ann_reads = 0
    total_ann_targets = 0
    for ann in announcements:
        ann_id = str(ann.get("id", "")) if isinstance(ann, dict) else ""
        ann_text = ann.get("text", "") if isinstance(ann, dict) else str(ann)
        stat = db.get_announcement_read_analytics(announcement_id=ann_id, dept=dept, year=year, ann_text=ann_text)
        total_ann_reads += stat.get("read_count", 0)
        total_ann_targets += stat.get("total_students", 0)

    avg_ann_pct = round((total_ann_reads / total_ann_targets * 100), 1) if total_ann_targets > 0 else 0.0

    total_mat_checks = 0
    total_mat_targets = 0
    for mat in materials:
        mat_id = str(mat.get("id", "")) if isinstance(mat, dict) else ""
        file_name = mat.get("name", "") if isinstance(mat, dict) else str(mat)
        m_stat = db.get_material_access_analytics(material_id=mat_id, dept=dept, year=year, file_name=file_name)
        total_mat_checks += m_stat.get("accessed_count", 0)
        total_mat_targets += m_stat.get("total_students", 0)

    avg_mat_pct = round((total_mat_checks / total_mat_targets * 100), 1) if total_mat_targets > 0 else 0.0

    with c1:
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:1.4rem;">👥</div>
            <div style="font-size:1.3rem;font-weight:800;color:#0f172a;">{total_students}</div>
            <div style="font-size:0.74rem;color:#64748b;font-weight:600;">Registered Students</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:1.4rem;">📢</div>
            <div style="font-size:1.3rem;font-weight:800;color:{'#16a34a' if avg_ann_pct >= 70 else primary};">{avg_ann_pct}%</div>
            <div style="font-size:0.74rem;color:#64748b;font-weight:600;">Avg Notice Read Rate</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:1.4rem;">📁</div>
            <div style="font-size:1.3rem;font-weight:800;color:{primary};">{avg_mat_pct}%</div>
            <div style="font-size:0.74rem;color:#64748b;font-weight:600;">Avg Material Check Rate</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

    # 2. Detailed Summary Table for Announcements
    st.markdown("#### 📢 Announcement Read Receipts Summary")
    if not announcements:
        st.info("No announcements posted yet.")
    else:
        ann_summary_data = []
        for a in announcements:
            a_id = str(a.get("id", "")) if isinstance(a, dict) else ""
            a_text = a.get("text", "") if isinstance(a, dict) else str(a)
            a_pri = a.get("priority", "Normal") if isinstance(a, dict) else "Normal"
            a_ts = a.get("timestamp", "") if isinstance(a, dict) else ""
            st_data = db.get_announcement_read_analytics(announcement_id=a_id, dept=dept, year=year, ann_text=a_text)
            ann_summary_data.append({
                "Announcement": a_text[:50] + ("..." if len(a_text) > 50 else ""),
                "Priority": a_pri.upper(),
                "Posted At": a_ts,
                "Read": f"{st_data.get('read_count', 0)} / {st_data.get('total_students', 0)}",
                "Read Rate (%)": f"{st_data.get('read_percentage', 0.0)}%",
                "Unread": st_data.get("unread_count", 0),
            })
        st.dataframe(pd.DataFrame(ann_summary_data), use_container_width=True, hide_index=True)

    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

    # 3. Detailed Summary Table for Materials
    st.markdown("#### 📁 Course Material Access Summary")
    if not materials:
        st.info("No course materials uploaded yet.")
    else:
        mat_summary_data = []
        for m in materials:
            m_id = str(m.get("id", "")) if isinstance(m, dict) else ""
            m_name = m.get("name", "Unnamed") if isinstance(m, dict) else str(m)
            m_stat = db.get_material_access_analytics(material_id=m_id, dept=dept, year=year, file_name=m_name)
            mat_summary_data.append({
                "Material File": m_name,
                "Checked / Downloaded": f"{m_stat.get('accessed_count', 0)} / {m_stat.get('total_students', 0)}",
                "Access Rate (%)": f"{m_stat.get('accessed_percentage', 0.0)}%",
                "Pending Students": m_stat.get("unaccessed_count", 0),
            })
        st.dataframe(pd.DataFrame(mat_summary_data), use_container_width=True, hide_index=True)
