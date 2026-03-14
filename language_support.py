"""
language_support.py — NarrativeForge Multi-Language Support
════════════════════════════════════════════════════════════

Supports Hindi, Tamil, Telugu, Bengali, Marathi, French, Spanish, German,
Japanese, Korean, Portuguese, Arabic, Mandarin and more.

HOW IT WORKS:
  - Writer picks a language in Story Settings (sidebar)
  - Language is stored in story["language"] (new field, defaults to "English")
  - _build_prompt() in workspace.py picks up the language block
  - AI writes story content AND all AI-generated UI labels in that language
  - UI chrome (buttons, nav) stays in English — only story content changes

INTEGRATION (workspace.py):
  1. Import: from language_support import LANGUAGES, get_language_block, render_language_selector
  2. In _sidebar_settings(story): call render_language_selector(story)
  3. In _build_prompt(): add get_language_block(story) to the base prompt string

INTEGRATION (database.py):
  - Add migration:  "ALTER TABLE stories ADD COLUMN language TEXT DEFAULT 'English'"
  - save_story() already serialises story dict — language key will be saved automatically
    once you add it to the INSERT/UPDATE column list (see patch below)
"""

import streamlit as st

# ── Supported languages ───────────────────────────────────────────────────────
LANGUAGES = {
    # Indian
    "English":    {"code": "en", "native": "English",    "rtl": False},
    "Hindi":      {"code": "hi", "native": "हिन्दी",       "rtl": False},
    "Tamil":      {"code": "ta", "native": "தமிழ்",        "rtl": False},
    "Telugu":     {"code": "te", "native": "తెలుగు",       "rtl": False},
    "Bengali":    {"code": "bn", "native": "বাংলা",        "rtl": False},
    "Marathi":    {"code": "mr", "native": "मराठी",        "rtl": False},
    "Kannada":    {"code": "kn", "native": "ಕನ್ನಡ",        "rtl": False},
    "Malayalam":  {"code": "ml", "native": "മലയാളം",      "rtl": False},
    "Gujarati":   {"code": "gu", "native": "ગુજરાતી",      "rtl": False},
    "Punjabi":    {"code": "pa", "native": "ਪੰਜਾਬੀ",       "rtl": False},
    # European
    "French":     {"code": "fr", "native": "Français",   "rtl": False},
    "Spanish":    {"code": "es", "native": "Español",    "rtl": False},
    "German":     {"code": "de", "native": "Deutsch",    "rtl": False},
    "Portuguese": {"code": "pt", "native": "Português",  "rtl": False},
    "Italian":    {"code": "it", "native": "Italiano",   "rtl": False},
    "Russian":    {"code": "ru", "native": "Русский",    "rtl": False},
    # Asian
    "Japanese":   {"code": "ja", "native": "日本語",      "rtl": False},
    "Korean":     {"code": "ko", "native": "한국어",       "rtl": False},
    "Mandarin":   {"code": "zh", "native": "普通话",      "rtl": False},
    # RTL
    "Arabic":     {"code": "ar", "native": "العربية",    "rtl": True},
    "Urdu":       {"code": "ur", "native": "اردو",       "rtl": True},
}

LANGUAGE_NAMES = list(LANGUAGES.keys())

# ── Grouped for the UI selectbox ──────────────────────────────────────────────
LANGUAGE_GROUPS = {
    "🇮🇳 Indian Languages": [
        "Hindi", "Tamil", "Telugu", "Bengali", "Marathi",
        "Kannada", "Malayalam", "Gujarati", "Punjabi",
    ],
    "🌍 European": ["English", "French", "Spanish", "German", "Portuguese", "Italian", "Russian"],
    "🌏 Asian":    ["Japanese", "Korean", "Mandarin"],
    "🌐 RTL":      ["Arabic", "Urdu"],
}

# Flat ordered list for selectbox (English first)
LANGUAGE_LIST = ["English"] + [
    lang for group in list(LANGUAGE_GROUPS.values())
    for lang in group
    if lang != "English"
]


def get_language_block(story: dict) -> str:
    """
    Returns the language instruction to inject into the AI prompt.
    Empty string for English (no change to existing prompts).
    """
    lang = story.get("language", "English")
    if not lang or lang == "English":
        return ""

    info = LANGUAGES.get(lang, {})
    native = info.get("native", lang)
    rtl_note = " Write right-to-left as required by the script." if info.get("rtl") else ""

    return (
        f"\nLANGUAGE INSTRUCTION: Write ALL story content, dialogue, narration, and "
        f"character names entirely in {lang} ({native}).{rtl_note} "
        f"Use natural, literary {lang} appropriate for the {story.get('genre','Fantasy')} genre. "
        f"Do NOT translate or mix languages — write purely in {lang}.\n"
    )


def render_language_selector(story: dict):
    """
    Renders the language selector in the workspace sidebar settings panel.
    Saves the selection to story dict and persists to DB immediately.

    Call this from _sidebar_settings(story) in workspace.py, after genre/tone selectors.
    """
    from database import save_story  # local import to avoid circular

    current = story.get("language", "English")

    st.markdown(
        "<div style='font-size:0.72rem;color:#8B8F8B;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.08em;margin:10px 0 4px;'>"
        "🌐 Story Language</div>",
        unsafe_allow_html=True
    )

    # Find current index
    idx = LANGUAGE_LIST.index(current) if current in LANGUAGE_LIST else 0

    selected = st.selectbox(
        "Language",
        LANGUAGE_LIST,
        index=idx,
        key="ws_language",
        label_visibility="collapsed",
        format_func=lambda l: f"{l}  ·  {LANGUAGES[l]['native']}" if l in LANGUAGES else l
    )

    if selected != current:
        story["language"] = selected
        save_story(st.session_state.username, story)
        st.rerun()

    # Visual indicator when non-English is active
    if selected != "English":
        info = LANGUAGES.get(selected, {})
        rtl_badge = "  ·  RTL" if info.get("rtl") else ""
        st.markdown(
            f"<div style='background:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.2);"
            f"border-radius:6px;padding:4px 10px;font-size:0.7rem;color:#4ade80;"
            f"font-family:JetBrains Mono,monospace;margin-top:4px;'>"
            f"✓ AI will write in {selected} ({info.get('native','')}{rtl_badge})</div>",
            unsafe_allow_html=True
        )


# ── database.py patch ─────────────────────────────────────────────────────────
"""
Add to init_db() migrations list in database.py:
    "ALTER TABLE stories ADD COLUMN language TEXT DEFAULT 'English'"

Add 'language' to save_story() INSERT and UPDATE:
  INSERT columns: (..., style_dna, language, updated_at)
  INSERT values:  (..., story.get("style_dna",""), story.get("language","English"), ...)
  UPDATE SET:     ..., language=excluded.language/EXCLUDED.language, ...

Add to _row_to_story():
  "language": r["language"] or "English"   (PG)
  "language": r[9] or "English"             (SQLite, adjust index if needed)

Add to load_stories() SELECT:
  ..., style_dna, language FROM stories ...
"""

# ── workspace.py patch ────────────────────────────────────────────────────────
"""
1. At top of workspace.py, add import:
   from language_support import get_language_block, render_language_selector

2. In _build_prompt(), in the 'base' string, add after style_block:
   + get_language_block(story) \

3. In _sidebar_settings(story), after the tone selector, add:
   render_language_selector(story)
"""
