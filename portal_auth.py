"""
Shared authentication and branding for the Green Eye Productions — Keele
University Portal.

Every page calls require_login() straight after its st.set_page_config(...).
Students enter the access code once on the landing page; because Streamlit
shares session state across pages, they won't be asked again while the
session lasts. Deep-linking to a page still prompts, so nothing is exposed.

The access code lives in Streamlit secrets (PORTAL_PASSWORD) so it isn't sat
in the public repo. If no secret is set it falls back to the pilot code, but
for anything real, set it in Settings -> Secrets.
"""

import streamlit as st

BRAND = "Green Eye Productions"
PORTAL = "Keele University Portal"
ACCENT = "#2e9e5b"
_FALLBACK_CODE = "Keele2026!"


def _expected_code() -> str:
    try:
        return st.secrets["PORTAL_PASSWORD"]
    except Exception:
        return _FALLBACK_CODE


def require_login() -> None:
    """Render the access gate and stop the page unless already signed in."""
    if st.session_state.get("portal_authed"):
        return

    st.markdown(
        f"<h1 style='text-align:center;margin-bottom:0'>🎬 {BRAND}</h1>"
        f"<p style='text-align:center;color:{ACCENT};font-weight:600;"
        f"margin-top:4px'>{PORTAL}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#9aa0a6'>Enter your access code to "
        "open the student portal.</p>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pwd = st.text_input("Access code", type="password",
                            label_visibility="collapsed",
                            placeholder="Access code")
        if st.button("Unlock portal", use_container_width=True, type="primary"):
            if pwd == _expected_code():
                st.session_state.portal_authed = True
                st.rerun()
            else:
                st.error("Incorrect access code. Please try again.")
    st.stop()


def portal_header(module_title: str, tagline: str = "") -> None:
    """Consistent branded strip at the top of each module page."""
    left, right = st.columns([3, 1])
    with left:
        st.markdown(
            f"<div style='font-size:13px;color:{ACCENT};font-weight:700'>"
            f"{BRAND} · {PORTAL}</div>"
            f"<h1 style='margin:2px 0 0 0'>{module_title}</h1>",
            unsafe_allow_html=True,
        )
    with right:
        st.write("")
        if st.button("🔒 Lock", use_container_width=True,
                     help="Sign out of the portal"):
            st.session_state.portal_authed = False
            st.rerun()
    if tagline:
        st.caption(tagline)
    st.divider()
