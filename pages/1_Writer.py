"""P.A.C.E. Writer — screenplay editor, AI co-writer and industry PDF export."""

import streamlit as st
from fpdf import FPDF

from portal_auth import require_login, portal_header

try:
    import google.generativeai as genai
    HAS_AI = True
except ImportError:
    HAS_AI = False

st.set_page_config(page_title="P.A.C.E. Writer", page_icon="✍️", layout="wide")
require_login()
portal_header("✍️ P.A.C.E. Writer",
              "Write in plain text — ALL CAPS for characters, INT/EXT for "
              "scene headings — and we format the rest.")

# --- optional AI ---
api_key_found = False
if HAS_AI:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            api_key_found = True
    except Exception:
        api_key_found = False


# ==========================================================================
# Fountain parsing (pure, state-driven — no fragile line lookups)
# ==========================================================================
def parse_fountain(text: str):
    """Return a list of (kind, line) where kind is one of:
    scene, character, paren, dialogue, transition, action, blank."""
    out = []
    prev = None
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            out.append(("blank", ""))
            prev = None
            continue
        u = line.upper()
        if u.startswith(("INT.", "EXT.", "INT ", "EXT ", "INT/", "EXT/",
                         "I/E", "EST.")):
            kind = "scene"
        elif line.startswith("(") and line.endswith(")"):
            kind = "paren"
        elif line.isupper() and line.endswith("TO:"):
            kind = "transition"
        elif line.isupper() and len(line) <= 35 and prev in (None, "action",
                                                             "scene"):
            kind = "character"
        elif prev in ("character", "paren", "dialogue"):
            kind = "dialogue"
        else:
            kind = "action"
        out.append((kind, line))
        prev = kind
    return out


def _sanitize(text: str) -> str:
    return (str(text).replace("’", "'").replace("‘", "'")
            .replace("“", '"').replace("”", '"').replace("—", "-")
            .encode("latin-1", "replace").decode("latin-1"))


def build_pdf(script_text: str) -> bytes:
    pdf = FPDF(unit="in", format="Letter")
    pdf.add_page()
    pdf.set_font("Courier", "", 12)
    ACTION_L, CHAR_L, PAREN_L, DIAL_L = 1.5, 3.5, 3.0, 2.5
    LH = 0.16
    for kind, line in parse_fountain(script_text):
        line = _sanitize(line)
        if kind == "blank":
            pdf.ln(LH)
        elif kind == "scene":
            pdf.set_font("Courier", "B", 12); pdf.set_x(ACTION_L)
            pdf.multi_cell(6.0, LH, line.upper())
            pdf.set_font("Courier", "", 12)
        elif kind == "transition":
            pdf.set_x(ACTION_L); pdf.multi_cell(6.0, LH, line.upper(), align="R")
        elif kind == "character":
            pdf.set_x(CHAR_L); pdf.multi_cell(3.0, LH, line)
        elif kind == "paren":
            pdf.set_x(PAREN_L); pdf.multi_cell(2.0, LH, line)
        elif kind == "dialogue":
            pdf.set_x(DIAL_L); pdf.multi_cell(3.5, LH, line)
        else:  # action
            pdf.set_x(ACTION_L); pdf.multi_cell(6.0, LH, line)
    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)


# ==========================================================================
# UI
# ==========================================================================
DEFAULT = ("INT. WAREHOUSE - NIGHT\n\nRain lashes against the skylight. "
           "Shadows stretch across the concrete floor.\n\nJOHN\n(panting)\n"
           "We shouldn't be here.\n\nSARAH\nWe don't have a choice.")
st.session_state.setdefault("writer_text", DEFAULT)

editor_col, tools_col = st.columns([2.5, 1])

with tools_col:
    st.subheader("🗄️ Your script")
    name = st.text_input("Script name", value="My_Script")

    st.download_button(
        "💾 Download (.txt)", st.session_state["writer_text"],
        file_name=f"{name.replace(' ', '_')}.txt", use_container_width=True,
        help="Save your work — download it, and re-upload to carry on later.")

    up = st.file_uploader("📂 Open a .txt script", type=["txt"])
    if up is not None and st.button("Load uploaded script",
                                    use_container_width=True):
        st.session_state["writer_text"] = up.read().decode("utf-8",
                                                            errors="ignore")
        st.rerun()

    if st.button("📄 New (blank)", use_container_width=True):
        st.session_state["writer_text"] = ""
        st.rerun()

    st.caption("⚠️ Nothing is stored on the server — download to keep your work.")
    st.divider()

    st.subheader("🤖 AI co-writer")
    if not (HAS_AI and api_key_found):
        st.info("AI help is off. Add a GEMINI_API_KEY in the app's Secrets to "
                "enable it.")
    ai_request = st.text_area(
        "What should happen next?", height=100,
        placeholder="e.g. A tense exchange where John confronts Sarah about "
                    "the missing money.")
    if st.button("🧠 Suggest", type="primary", use_container_width=True):
        if not (HAS_AI and api_key_found):
            st.error("AI is not configured.")
        elif not ai_request.strip():
            st.warning("Tell the AI what you need first.")
        else:
            with st.spinner("Brainstorming…"):
                context = st.session_state["writer_text"][-2000:]
                prompt = ("You are an experienced screenwriter. Continue the "
                          "user's script in standard Fountain syntax (ALL CAPS "
                          "characters, INT/EXT scene headings).\n\n"
                          f"Request: {ai_request}\n\nRecent context:\n{context}")
                try:
                    models = [m.name for m in genai.list_models()
                              if "generateContent" in m.supported_generation_methods]
                    order = ["models/gemini-1.5-flash", "models/gemini-1.5-pro",
                             "models/gemini-pro"]
                    ordered = [m for m in order if m in models] + \
                              [m for m in models if m not in order]
                    for mn in ordered:
                        try:
                            r = genai.GenerativeModel(mn).generate_content(prompt)
                            if r.text:
                                st.session_state["ai_suggestion"] = r.text
                                break
                        except Exception:
                            continue
                except Exception as e:
                    st.error(f"AI error: {e}")

    if st.session_state.get("ai_suggestion"):
        st.markdown("**Suggestion:**")
        st.code(st.session_state["ai_suggestion"], language="text")
        if st.button("➕ Append to my script", use_container_width=True):
            st.session_state["writer_text"] = (
                st.session_state["writer_text"].rstrip()
                + "\n\n" + st.session_state["ai_suggestion"].strip())
            del st.session_state["ai_suggestion"]
            st.rerun()

with editor_col:
    st.text_area("The canvas (Fountain syntax)", height=560, key="writer_text")
    if st.button("🖨️ Compile & export industry PDF", type="primary",
                 use_container_width=True):
        with st.spinner("Setting to standard screenplay margins…"):
            try:
                data = build_pdf(st.session_state["writer_text"])
                st.success("Compiled.")
                st.download_button(
                    "📥 Download screenplay PDF", data,
                    file_name=f"{name.replace(' ', '_')}.pdf",
                    mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Couldn't build the PDF: {e}")
