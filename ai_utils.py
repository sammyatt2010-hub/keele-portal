"""
Shared Gemini helper for the portal.

Why this exists: model names change often (the gemini-1.5 family is already
retired), and all three modules need the same behaviour. Centralising it here
means switching model, tier or settings later is a ONE-FILE change.

Model choice is by preference tag (flash-lite → flash → pro) matched against
whatever models the key can actually access, so it keeps working on the free
tier and survives Google renaming models. Rate-limit errors (common on the
free tier when a whole class hits it at once) are retried briefly, then turned
into a friendly "try again in a minute" message.
"""

import time

import streamlit as st

try:
    import google.generativeai as genai
    HAS_AI = True
except ImportError:                       # pragma: no cover
    HAS_AI = False

# Cheapest / most free-tier-friendly first. Substring match, so we don't have
# to chase exact version numbers as Google releases them.
_PREFERENCE = ["flash-lite", "flash", "pro"]


def ai_ready() -> bool:
    """True if the AI is importable and a key is configured."""
    if not HAS_AI:
        return False
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    except Exception:
        return False


def _rank(name: str) -> int:
    n = name.lower()
    for i, tag in enumerate(_PREFERENCE):
        if tag in n:
            return i
    return len(_PREFERENCE)


def _ordered_models() -> list[str]:
    names = [m.name for m in genai.list_models()
             if "generateContent" in m.supported_generation_methods]
    return sorted(names, key=_rank)   # stable: keeps API order within a tier


def _is_rate_limit(err) -> bool:
    return any(k in str(err).lower()
               for k in ("429", "quota", "rate", "exhaust", "resource"))


def generate_content(prompt: str, max_retries: int = 2) -> str:
    """Return the model's text, or raise RuntimeError with a friendly message.
    Prefers the cheapest available model; retries briefly on rate limits."""
    last_err = None
    for name in _ordered_models():
        for attempt in range(max_retries + 1):
            try:
                resp = genai.GenerativeModel(name).generate_content(prompt)
                if getattr(resp, "text", ""):
                    return resp.text
                break  # empty response — move to the next model
            except Exception as e:
                last_err = e
                if _is_rate_limit(e):
                    time.sleep(1.5 * (attempt + 1))   # brief back-off
                    continue
                break  # different error — try the next model
    if last_err and _is_rate_limit(last_err):
        raise RuntimeError("The free AI tier is busy right now (too many "
                           "requests at once). Please wait a minute and try "
                           "again.")
    raise RuntimeError(f"AI request failed: {last_err}" if last_err
                       else "No AI models are available for this key.")
