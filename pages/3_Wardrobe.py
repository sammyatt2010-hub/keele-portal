"""Wardrobe — AI costume breakdown: look-books, stunt multiples, sourcing."""

import io
import re
import xml.etree.ElementTree as ET

import streamlit as st
from fpdf import FPDF

from portal_auth import require_login, portal_header

try:
    from pypdf import PdfReader
except ImportError:                       # pragma: no cover
    from PyPDF2 import PdfReader

try:
    import google.generativeai as genai
    HAS_AI = True
except ImportError:
    HAS_AI = False

try:
    from gtts import gTTS
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

st.set_page_config(page_title="Wardrobe", page_icon="👗", layout="wide")
require_login()
portal_header("👗 Wardrobe",
              "Upload a .pdf or .fdx script to generate costume look-books, "
              "character wardrobe arcs, stunt-multiple advisories and a "
              "sourcing strategy.")

api_key_found = False
if HAS_AI:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            api_key_found = True
    except Exception:
        api_key_found = False


def extract_text(upload) -> str:
    if upload.name.lower().endswith(".pdf"):
        reader = PdfReader(upload)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    tree = ET.parse(upload)
    root = tree.getroot()
    parts = []
    for para in root.findall(".//Paragraph"):
        t = "".join(n.text for n in para.findall(".//Text") if n.text).strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


c1, c2, c3 = st.columns(3)
with c1:
    uploaded = st.file_uploader("1. Script (.pdf or .fdx)", type=["pdf", "fdx"])
with c2:
    budget = st.selectbox("2. Wardrobe budget tier",
                          ["Micro-Budget (Thrift / Pulled)",
                           "Indie (Rentals & Minor Build)",
                           "Studio Feature (Bespoke Tailoring)"])
with c3:
    ip_owner = st.text_input("3. Project / studio name", "STUDENT PROJECT")

if st.button("🚀 Generate wardrobe breakdown", type="primary",
             use_container_width=True):
    if uploaded is None:
        st.error("Upload a script file first.")
    elif not (HAS_AI and api_key_found):
        st.error("AI is not configured. Add a GEMINI_API_KEY in the app's "
                 "Secrets to use this module.")
    else:
        with st.spinner("Analysing character arcs, flagging multiples, "
                        "designing look-books…"):
            name_clean = uploaded.name.replace(".fdx", "").replace(".pdf", "")
            sample = extract_text(uploaded)[:60000]
            prompt = f"""You are an experienced costume designer and wardrobe
supervisor. From the script text, produce a detailed wardrobe and costume
breakdown. Budget tier: {budget} — make the sourcing strategy reflect it.
Use Markdown with these sections:

## 1. Global Aesthetic & Colour Palette
The fashion era, texture and colour palette, and how costume reflects tone.

## 2. Lead Character Wardrobe Arcs (Top 3)
For the three most prominent characters:
- Character name
- Signature look (their default outfit)
- Wardrobe arc: how their clothing changes across their emotional journey

## 3. Stunt & Multiples Advisory
Scan for action, rain, blood or damage. Identify 2 scenes needing "multiples"
(e.g. several identical shirts because one gets bloodied over many takes) and
explain the logistical challenge.

## 4. Sourcing & Fabrication Strategy
Given {budget}, how are these acquired — thrifting and distressing, rental
houses, or bespoke builds?

---
PDF_SUMMARY: a punchy 3-paragraph executive summary (aesthetic, arcs, the
multiples warning).
---
WARDROBE_PROMPTS: three vivid English image-generator prompts for fashion
look-book portraits of the top 3 leads, on one line separated by | .

Script sample:
{sample}"""
            analysis, pdf_summary, prompts, audio = "", "", [], None
            try:
                models = [m.name for m in genai.list_models()
                          if "generateContent" in m.supported_generation_methods]
                order = ["models/gemini-1.5-flash", "models/gemini-1.5-pro",
                         "models/gemini-pro"]
                ordered = [m for m in order if m in models] + \
                          [m for m in models if m not in order]
                text = ""
                for mn in ordered:
                    try:
                        r = genai.GenerativeModel(mn).generate_content(prompt)
                        text = r.text or ""
                        if text:
                            break
                    except Exception:
                        continue
                if not text:
                    raise RuntimeError("No response from the AI models "
                                       "(a very graphic script can be blocked "
                                       "by default safety filters).")

                body = text
                if "WARDROBE_PROMPTS:" in body:
                    body, tail = body.split("WARDROBE_PROMPTS:", 1)
                    prompts = [p.strip() for p in tail.split("|") if p.strip()]
                if "PDF_SUMMARY:" in body:
                    analysis, pdf_summary = [s.strip()
                                             for s in body.split("PDF_SUMMARY:", 1)]
                else:
                    analysis = pdf_summary = body.strip()

                if HAS_TTS:
                    try:
                        clean = re.sub(r"[*_#]", "", pdf_summary)
                        buf = io.BytesIO()
                        gTTS(text=clean, lang="en").write_to_fp(buf)
                        buf.seek(0)
                        audio = buf
                    except Exception:
                        audio = None
            except Exception as e:
                analysis = pdf_summary = f"AI error: {e}"

            st.success(f"Wardrobe breakdown generated for **{name_clean}**.")
            st.caption(f"Project: {ip_owner.upper()} — generated by the "
                       "P.A.C.E. wardrobe engine")
            st.divider()
            if audio:
                st.audio(audio, format="audio/mp3")
            st.markdown(analysis)

            if prompts:
                st.divider()
                st.subheader("🎨 Costume look-book prompts")
                st.caption("Paste into your image generator (4:5 portrait ratio "
                           "appended):")
                for p in prompts:
                    st.code(f"{p} --ar 4:5", language="text")

            # --- PDF export ---
            class WardrobePDF(FPDF):
                def header(self):
                    self.set_fill_color(20, 20, 20)
                    self.rect(0, 0, 210, 297, "F")
                    self.set_text_color(200, 200, 200)
                    self.set_font("Arial", "B", 10)
                    self.cell(0, 10, f"WARDROBE DIRECTIVE | {ip_owner.upper()}",
                              ln=True, align="R")
                    self.ln(4)

            def san(t):
                return (str(t).replace("•", "-").replace("€", "EUR ")
                        .replace("£", "GBP ").replace("’", "'").replace("“", '"')
                        .replace("”", '"').encode("latin-1", "replace")
                        .decode("latin-1"))

            pdf = WardrobePDF()
            pdf.add_page()
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 22)
            pdf.cell(0, 14, san(f"PROJECT: {name_clean.upper()}"), ln=True,
                     align="C")
            pdf.set_font("Arial", "I", 13)
            pdf.set_text_color(0, 229, 255)
            pdf.cell(0, 10, san(f"Wardrobe budget: {budget}"), ln=True,
                     align="C")
            pdf.ln(8)
            pdf.set_font("Arial", "", 11)
            pdf.set_text_color(220, 220, 220)
            clean = pdf_summary.replace("**", "").replace("##", "") \
                               .replace("#", "").replace("---", "")
            pdf.multi_cell(0, 6, san(clean))
            out = pdf.output(dest="S")
            data = out.encode("latin-1") if isinstance(out, str) else bytes(out)

            st.divider()
            st.download_button("📥 Download wardrobe directive (.pdf)", data,
                               file_name=f"Wardrobe_{name_clean}.pdf",
                               mime="application/pdf", use_container_width=True)
