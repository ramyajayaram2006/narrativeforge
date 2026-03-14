"""
NarrativeForge — Premium Reading Mode
5 immersive book themes, bookmarks, font controls, page navigation.
"""
import html as _html
import math
import streamlit as st

# ── Theme definitions ──────────────────────────────────────────────────────
_THEMES = {
    "📜 Parchment": {
        "bg":        "#F5EDD6",
        "text":      "#2C1810",
        "title":     "#6B3A2A",
        "meta":      "#8B6A4A",
        "accent":    "#8B4513",
        "divider":   "#C4A882",
        "border":    "#D4B896",
        "shadow":    "rgba(139,69,19,0.2)",
        "font":      "'Georgia', 'Times New Roman', serif",
        "page_bg":   "#FAF3E0",
    },
    "📘 Hardcover": {
        "bg":        "#F8F4EE",
        "text":      "#1A1A2E",
        "title":     "#16213E",
        "meta":      "#4A4A6A",
        "accent":    "#0F3460",
        "divider":   "#B8C4D8",
        "border":    "#C8D4E8",
        "shadow":    "rgba(15,52,96,0.15)",
        "font":      "'Palatino Linotype', 'Book Antiqua', serif",
        "page_bg":   "#FDFAF6",
    },
    "📖 Fantasy Tome": {
        "bg":        "#0D0F1A",
        "text":      "#C8B89A",
        "title":     "#E8D5A0",
        "meta":      "#8A7A6A",
        "accent":    "#C4973E",
        "divider":   "#3D3020",
        "border":    "#4A3828",
        "shadow":    "rgba(196,151,62,0.25)",
        "font":      "'Palatino Linotype', 'Book Antiqua', serif",
        "page_bg":   "#0A0C14",
    },
    "📓 Paperback": {
        "bg":        "#FFFFFF",
        "text":      "#2D2D2D",
        "title":     "#1A1A1A",
        "meta":      "#666666",
        "accent":    "#4D6BFE",
        "divider":   "#E0E0E0",
        "border":    "#EEEEEE",
        "shadow":    "rgba(0,0,0,0.08)",
        "font":      "'Inter', 'Helvetica Neue', sans-serif",
        "page_bg":   "#FAFAFA",
    },
    "🌙 Night Reading": {
        "bg":        "#0D0E14",
        "text":      "#C8CAD4",
        "title":     "#A8BCFF",
        "meta":      "#5A5E72",
        "accent":    "#4D6BFE",
        "divider":   "#1E2030",
        "border":    "#252840",
        "shadow":    "rgba(77,107,254,0.15)",
        "font":      "'Inter', sans-serif",
        "page_bg":   "#0A0B10",
    },
}

_WORDS_PER_PAGE = 400


def _split_pages(paragraphs):
    """Split paragraphs into pages of ~400 words each."""
    pages, current, word_count = [], [], 0
    for para in paragraphs:
        wc = len(para.split())
        if word_count + wc > _WORDS_PER_PAGE and current:
            pages.append(current)
            current, word_count = [para], wc
        else:
            current.append(para)
            word_count += wc
    if current:
        pages.append(current)
    return pages if pages else [[]]


def show_premium_reading_mode(story):
    """Full immersive reading mode with 5 themes, bookmarks, paging."""
    username  = st.session_state.get("username", "reader")
    story_id  = story["id"]

    # ── State keys ────────────────────────────────────────────────────────
    theme_key     = f"rm_theme_{story_id}"
    page_key      = f"rm_page_{story_id}"
    font_key      = f"rm_fontsize_{story_id}"
    bookmark_key  = f"rm_bookmarks_{story_id}"
    spacing_key   = f"rm_spacing_{story_id}"

    theme_name  = st.session_state.get(theme_key, "🌙 Night Reading")
    page_idx    = st.session_state.get(page_key, 0)
    font_size   = st.session_state.get(font_key, 18)
    bookmarks   = st.session_state.get(bookmark_key, set())
    line_spacing = st.session_state.get(spacing_key, 1.9)

    theme = _THEMES.get(theme_name, _THEMES["🌙 Night Reading"])

    # ── Prose assembly ─────────────────────────────────────────────────────
    ai_msgs = [m for m in story.get("messages", [])
               if m["role"] == "assistant" and not m["content"].startswith("◆")]
    full_prose = "\n\n".join(m["content"] for m in ai_msgs)
    paragraphs = [p.strip() for p in full_prose.split("\n\n") if p.strip()]
    pages      = _split_pages(paragraphs)
    total_pages = len(pages)
    page_idx    = max(0, min(page_idx, total_pages - 1))

    wc      = sum(len(p.split()) for p in paragraphs)
    read_min = max(1, wc // 200)

    # ── Full page CSS ──────────────────────────────────────────────────────
    st.markdown(f"""
        <style>
        /* Reading mode overrides */
        .main .block-container {{ padding: 0 !important; max-width: 100% !important; }}
        [data-testid="stSidebar"] {{ display: none !important; }}
        .reading-page {{
            min-height: 100vh;
            background: {theme['page_bg']};
            padding: 0;
        }}
        .reading-toolbar {{
            background: {theme['bg']};
            border-bottom: 1px solid {theme['border']};
            padding: 10px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 8px {theme['shadow']};
        }}
        .reading-book {{
            max-width: 680px;
            margin: 0 auto;
            padding: 60px 48px 80px;
            background: {theme['bg']};
            box-shadow: 0 4px 40px {theme['shadow']}, 0 0 0 1px {theme['border']};
            min-height: 80vh;
        }}
        .reading-title {{
            font-size: clamp(1.8rem, 4vw, 2.6rem);
            font-weight: 700;
            color: {theme['title']};
            font-family: {theme['font']};
            text-align: center;
            margin-bottom: 8px;
            letter-spacing: -0.01em;
        }}
        .reading-meta {{
            text-align: center;
            color: {theme['meta']};
            font-size: 0.78rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 48px;
            font-family: {theme['font']};
        }}
        .reading-para {{
            color: {theme['text']};
            font-family: {theme['font']};
            font-size: {font_size}px;
            line-height: {line_spacing};
            text-align: justify;
            text-indent: 2.2em;
            margin-bottom: 0.8em;
            hyphens: auto;
        }}
        .reading-para:first-of-type {{ text-indent: 0; }}
        .reading-divider {{
            text-align: center;
            color: {theme['divider']};
            margin: 40px 0;
            font-size: 1.1rem;
            letter-spacing: 0.5em;
        }}
        .reading-page-info {{
            text-align: center;
            color: {theme['meta']};
            font-size: 0.72rem;
            font-family: {theme['font']};
            letter-spacing: 0.1em;
            margin-top: 40px;
            padding-top: 24px;
            border-top: 1px solid {theme['border']};
        }}
        .bookmark-active {{ color: {theme['accent']} !important; }}
        </style>
    """, unsafe_allow_html=True)

    # ── Controls bar (Streamlit widgets, outside HTML) ──────────────────
    ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns([2, 2, 2, 2, 2])
    with ctrl1:
        if st.button("← Exit Reading", key="rm_back", use_container_width=True):
            st.session_state["reading_mode"] = False
            st.rerun()
    with ctrl2:
        new_theme = st.selectbox("Theme", list(_THEMES.keys()),
            index=list(_THEMES.keys()).index(theme_name),
            key="rm_theme_sel", label_visibility="collapsed")
        if new_theme != theme_name:
            st.session_state[theme_key] = new_theme
            st.rerun()
    with ctrl3:
        new_font = st.slider("Font", 14, 26, font_size, key="rm_font_sl",
                             label_visibility="collapsed")
        if new_font != font_size:
            st.session_state[font_key] = new_font
            st.rerun()
    with ctrl4:
        bm_label = "🔖 Bookmarked" if page_idx in bookmarks else "🔖 Bookmark"
        if st.button(bm_label, key="rm_bm", use_container_width=True):
            new_bm = set(bookmarks)
            if page_idx in new_bm: new_bm.discard(page_idx)
            else: new_bm.add(page_idx)
            st.session_state[bookmark_key] = new_bm
            st.rerun()
    with ctrl5:
        st.markdown(
            f"<div style='text-align:right;font-size:0.72rem;color:{theme['meta']};padding-top:8px;'>"
            f"{wc:,} words · ~{read_min}m read</div>",
            unsafe_allow_html=True)

    # ── Bookmarks jump list ─────────────────────────────────────────────
    if bookmarks:
        bm_cols = st.columns(min(len(bookmarks), 6))
        for i, bm_page in enumerate(sorted(bookmarks)):
            with bm_cols[i % 6]:
                if st.button(f"🔖 p.{bm_page+1}", key=f"rm_goto_{bm_page}",
                             use_container_width=True):
                    st.session_state[page_key] = bm_page
                    st.rerun()

    # ── Page content ───────────────────────────────────────────────────
    if not paragraphs:
        st.markdown(
            f"<div style='text-align:center;color:{theme['meta']};padding:80px;"
            f"font-family:{theme['font']};font-style:italic;'>"
            "Nothing written yet. Return and start your story.</div>",
            unsafe_allow_html=True)
        return

    # Build page HTML
    html_parts = [
        f"<div class='reading-book'>",
        f"<div class='reading-title'>{_html.escape(story['title'])}</div>",
        f"<div class='reading-meta'>{_html.escape(story['genre'])} · "
        f"{_html.escape(story['tone'])} · {wc:,} words</div>",
    ]
    for para in pages[page_idx]:
        html_parts.append(f"<p class='reading-para'>{_html.escape(para)}</p>")

    bm_indicator = "🔖 " if page_idx in bookmarks else ""
    html_parts.append(
        f"<div class='reading-page-info'>{bm_indicator}"
        f"Page {page_idx + 1} of {total_pages}</div>")
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

    # ── Page navigation ─────────────────────────────────────────────────
    nav_l, nav_m, nav_r = st.columns([1, 3, 1])
    with nav_l:
        if page_idx > 0:
            if st.button("← Prev", key="rm_prev", use_container_width=True):
                st.session_state[page_key] = page_idx - 1
                st.rerun()
    with nav_m:
        prog = int((page_idx + 1) / total_pages * 100) if total_pages > 1 else 100
        st.markdown(
            f"<div style='background:{theme['border']};border-radius:4px;height:4px;margin-top:14px;'>"
            f"<div style='width:{prog}%;background:{theme['accent']};height:4px;border-radius:4px;'></div></div>",
            unsafe_allow_html=True)
    with nav_r:
        if page_idx < total_pages - 1:
            if st.button("Next →", key="rm_next", use_container_width=True):
                st.session_state[page_key] = page_idx + 1
                st.rerun()
