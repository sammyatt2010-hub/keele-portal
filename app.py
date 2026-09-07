"""
Green Eye Productions — Keele University Portal.
Landing page. Deploy this file as the Streamlit 'Main file path'.
"""

import streamlit as st
from portal_auth import require_login, BRAND, PORTAL, ACCENT

st.set_page_config(page_title=f"{BRAND} — {PORTAL}",
                   page_icon="🎬", layout="wide")

require_login()

st.markdown(
    f"<div style='text-align:center'>"
    f"<h1 style='margin-bottom:0'>🎬 {BRAND}</h1>"
    f"<p style='color:{ACCENT};font-weight:700;font-size:20px;margin-top:4px'>"
    f"{PORTAL}</p>"
    f"<p style='color:#9aa0a6'>A hands-on toolkit for Film Studies students — "
    f"write it, sell it, dress it.</p></div>",
    unsafe_allow_html=True,
)
st.divider()

MODULES = [
    ("✍️", "P.A.C.E. Writer",
     "Draft screenplays in simple Fountain syntax, get AI co-writing help, and "
     "export a clean, industry-formatted PDF.",
     "pages/1_Writer.py"),
    ("📈", "Sales & Marketing",
     "Turn a script into a pitch deck: logline, target audience, budget-aware "
     "comparables and franchise angles.",
     "pages/2_Sales_and_Marketing.py"),
    ("👗", "Wardrobe",
     "Turn a script into a costume breakdown: character wardrobe arcs, "
     "stunt-multiple advisories, sourcing strategy and look-book prompts.",
     "pages/3_Wardrobe.py"),
]

cols = st.columns(3)
for col, (icon, title, blurb, path) in zip(cols, MODULES):
    with col:
        st.markdown(
            f"<div style='border:1px solid #2a2f36;border-radius:12px;"
            f"padding:18px;min-height:190px'>"
            f"<div style='font-size:30px'>{icon}</div>"
            f"<h3 style='margin:6px 0'>{title}</h3>"
            f"<p style='color:#9aa0a6;font-size:14px'>{blurb}</p></div>",
            unsafe_allow_html=True,
        )
        st.page_link(path, label=f"Open {title}  →", use_container_width=True)

st.divider()
st.caption(
    f"© {BRAND}. Provided to Keele University for educational use. "
    "Built on the P.A.C.E. Studio Suite."
)
