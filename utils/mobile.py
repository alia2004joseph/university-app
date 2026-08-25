"""
mobile.py — Mobile device detection and responsive helpers.
"""
import streamlit as st
import re

def is_mobile():
    """
    Detect if user is on a mobile device.
    Uses User-Agent from the request if available.
    Falls back to session state toggle for testing.
    """
    # Check if user manually set a view mode
    if "view_mode" in st.session_state:
        if st.session_state.view_mode == "mobile":
            return True
        elif st.session_state.view_mode == "desktop":
            return False
    
    # Try to detect from User-Agent
    try:
        # Streamlit 1.32+ has request headers
        ctx = st.runtime.scriptrunner.script_run_context.get_script_run_ctx()
        if ctx and hasattr(ctx, 'user_agent'):
            user_agent = ctx.user_agent
            if user_agent:
                mobile_patterns = [
                    r"Mobile", r"Android", r"iPhone", r"iPad", 
                    r"iPod", r"BlackBerry", r"Windows Phone"
                ]
                return any(re.search(p, user_agent, re.I) for p in mobile_patterns)
    except:
        pass
    
    # Default to desktop
    return False

def get_view_mode_toggle():
    """Return a small toggle in sidebar for manual view mode override."""
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "auto"
    
    view_mode = st.radio(
        "📱 View Mode",
        ["Auto", "Mobile", "Desktop"],
        index=["auto", "mobile", "desktop"].index(st.session_state.view_mode),
        horizontal=True,
        key="view_mode_radio"
    )
    
    if view_mode.lower() != st.session_state.view_mode:
        st.session_state.view_mode = view_mode.lower()
        st.rerun()
    
    return is_mobile()