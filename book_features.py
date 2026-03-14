"""
book_features.py — NarrativeForge Premium Book Features
• Book PDF export  (real typeset book with chapters, fonts, page numbers)
• Message editing  (click any bubble to edit or delete)
• Book writing mode (clean manuscript / Scrivener-style view)
"""
import io
import re
import html as _html
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# HELPER — extract clean prose paragraphs from messages
# ──────────────────────────────────────────────────────────────────────────────
def _get_prose_paragraphs(story):
    """Return list of (speaker, text) tuples. speaker='user' or 'ai'."""
    paras = []
    for m in story.get("messages", []):
        role = m.get("role", "")
        text = m.get("content", "").strip()
        if not text:
            continue
        paras.append((role, text))
    return paras


def _ai_prose_only(story):
    """All AI-generated prose joined as one string."""
    return "\n\n".join(
        m["content"] for m in story.get("messages", [])
        if m.get("role") == "assistant" and m.get("content", "").strip()
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1.  BOOK PDF EXPORT
# ──────────────────────────────────────────────────────────────────────────────
def export_book_pdf(story, characters=None, author=""):
    """
    Generate a properly typeset book PDF using reportlab.
    Returns BytesIO or None if reportlab missing.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            PageBreak, HRFlowable, KeepTogether
        )
        from reportlab.platypus.tableofcontents import TableOfContents
        from reportlab.pdfgen import canvas as rl_canvas
    except ImportError:
        return None

    title  = story.get("title", "Untitled")
    genre  = story.get("genre", "")
    tone   = story.get("tone", "")
    msgs   = story.get("messages", [])
    chars  = characters or []
    buf    = io.BytesIO()

    # ── Page layout ───────────────────────────────────────────────────────────
    PAGE_W, PAGE_H = A4
    MARGIN_OUTER   = 2.5 * cm
    MARGIN_INNER   = 3.0 * cm   # gutter
    MARGIN_TOP     = 2.5 * cm
    MARGIN_BOTTOM  = 2.5 * cm

    # ── Styles ────────────────────────────────────────────────────────────────
    SERIF  = "Times-Roman"
    SERIFI = "Times-Italic"
    SERIFB = "Times-Bold"

    def sty(name, **kw):
        defaults = dict(fontName=SERIF, fontSize=11, leading=16,
                        textColor=colors.HexColor("#1a1a1a"))
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    S = {
        "title":      sty("title",   fontName=SERIFB, fontSize=32, leading=38,
                          alignment=TA_CENTER, spaceAfter=8),
        "subtitle":   sty("subtitle",fontName=SERIFI, fontSize=14, leading=20,
                          alignment=TA_CENTER, spaceAfter=4, textColor=colors.HexColor("#555")),
        "author":     sty("author",  fontName=SERIF, fontSize=13, leading=18,
                          alignment=TA_CENTER, spaceAfter=6, textColor=colors.HexColor("#333")),
        "chapter_num":sty("chnum",   fontName=SERIF, fontSize=10, leading=14,
                          alignment=TA_CENTER, textColor=colors.HexColor("#888"),
                          spaceBefore=20, spaceAfter=4),
        "chapter_hd": sty("chd",     fontName=SERIFB, fontSize=20, leading=26,
                          alignment=TA_CENTER, spaceAfter=24),
        "body":       sty("body",    alignment=TA_JUSTIFY, firstLineIndent=18,
                          spaceAfter=8),
        "body_first": sty("bfirst",  alignment=TA_JUSTIFY, spaceAfter=8),
        "scene_break":sty("sb",      alignment=TA_CENTER, fontSize=14,
                          leading=20, spaceAfter=12, spaceBefore=12,
                          textColor=colors.HexColor("#888")),
        "char_list":  sty("cl",      fontName=SERIFI, fontSize=10, leading=14,
                          textColor=colors.HexColor("#555"), spaceAfter=2),
        "prompt_lbl": sty("plbl",    fontName=SERIFI, fontSize=9, leading=12,
                          textColor=colors.HexColor("#aaa"), spaceAfter=4,
                          leftIndent=10),
    }

    # ── Page number callback ──────────────────────────────────────────────────
    class _BookDoc(SimpleDocTemplate):
        def __init__(self, *a, **kw):
            self._title = kw.pop("book_title", "")
            super().__init__(*a, **kw)

        def handle_pageEnd(self):
            super().handle_pageEnd()

        def afterPage(self):
            c = self.canv
            pn = c.getPageNumber()
            if pn <= 2:   # skip title + cast pages
                return
            c.saveState()
            c.setFont(SERIF, 9)
            c.setFillColor(colors.HexColor("#888"))
            # Running header
            c.drawCentredString(PAGE_W / 2, PAGE_H - 1.5*cm,
                                self._title.upper())
            # Page number — left on even, right on odd
            if pn % 2 == 0:
                c.drawString(MARGIN_OUTER, 1.5*cm, str(pn))
            else:
                c.drawRightString(PAGE_W - MARGIN_OUTER, 1.5*cm, str(pn))
            c.restoreState()

    doc = _BookDoc(
        buf,
        pagesize=A4,
        leftMargin=MARGIN_INNER,
        rightMargin=MARGIN_OUTER,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        book_title=title,
    )

    story_el = []

    # ── TITLE PAGE ────────────────────────────────────────────────────────────
    story_el.append(Spacer(1, 4*cm))
    story_el.append(Paragraph(_html.escape(title), S["title"]))
    story_el.append(Spacer(1, 0.5*cm))
    if genre or tone:
        story_el.append(Paragraph(
            _html.escape(f"{genre} · {tone}"), S["subtitle"]))
    story_el.append(Spacer(1, 0.8*cm))
    if author:
        story_el.append(Paragraph(
            f"By {_html.escape(author)}", S["author"]))
    story_el.append(PageBreak())

    # ── CAST OF CHARACTERS ────────────────────────────────────────────────────
    if chars:
        story_el.append(Spacer(1, 2*cm))
        story_el.append(Paragraph("CAST OF CHARACTERS", S["chapter_hd"]))
        story_el.append(HRFlowable(width="60%", thickness=0.5,
                                   color=colors.HexColor("#ccc"),
                                   hAlign="CENTER", spaceAfter=16))
        for ch in chars:
            name = _html.escape(ch.get("name", ""))
            role = _html.escape(ch.get("role", ""))
            desc = _html.escape(ch.get("description", "")[:120])
            story_el.append(Paragraph(
                f"<b>{name}</b> — <i>{role}</i>", S["body_first"]))
            if desc:
                story_el.append(Paragraph(desc, S["char_list"]))
            story_el.append(Spacer(1, 4))
        story_el.append(PageBreak())

    # ── CHAPTERS / STORY BODY ─────────────────────────────────────────────────
    # Split AI prose into chapters by "Chapter" headings or every ~1500 words
    ai_msgs = [m for m in msgs if m.get("role") == "assistant"]
    user_msgs = [m for m in msgs if m.get("role") == "user"]

    # Group messages into conversational pairs (user prompt → AI response)
    pairs = []
    i = 0
    while i < len(msgs):
        if msgs[i].get("role") == "user":
            prompt = msgs[i]["content"]
            response = msgs[i+1]["content"] if i+1 < len(msgs) and msgs[i+1].get("role") == "assistant" else ""
            pairs.append((prompt, response))
            i += 2
        else:
            pairs.append(("", msgs[i]["content"]))
            i += 1

    # Build chapters — each AI response becomes a section
    chapter_num = 0
    for prompt, response in pairs:
        if not response.strip():
            continue
        chapter_num += 1

        # Chapter heading
        story_el.append(Spacer(1, 1.5*cm))
        story_el.append(Paragraph(f"— {chapter_num} —", S["chapter_num"]))

        # If prompt looks like a chapter title, use it
        first_line = prompt.strip().split("\n")[0][:60] if prompt.strip() else ""
        if first_line and len(first_line) > 3 and len(first_line) < 50:
            story_el.append(Paragraph(_html.escape(first_line), S["chapter_hd"]))
        story_el.append(Spacer(1, 0.8*cm))

        # Body paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n{2,}', response) if p.strip()]
        for j, para in enumerate(paragraphs):
            safe = _html.escape(para)
            style = S["body_first"] if j == 0 else S["body"]
            # Scene break marker
            if para in ("* * *", "---", "***", "* * * *"):
                story_el.append(Paragraph("✦ ✦ ✦", S["scene_break"]))
            else:
                story_el.append(Paragraph(safe, style))

        story_el.append(PageBreak())

    # ── THE END ───────────────────────────────────────────────────────────────
    story_el.append(Spacer(1, 4*cm))
    story_el.append(Paragraph("— THE END —", S["chapter_num"]))

    try:
        doc.build(story_el)
    except Exception as e:
        return None

    buf.seek(0)
    return buf


# ──────────────────────────────────────────────────────────────────────────────
# 2.  MESSAGE EDITOR  (edit / delete any chat bubble)
# ──────────────────────────────────────────────────────────────────────────────
def show_message_editor(story, username, save_fn):
    """
    Renders the full chat history with Edit / Delete buttons on each bubble.
    Call this from workspace instead of the normal chat render when edit mode is on.
    Returns True if a save was triggered (caller should st.rerun()).
    """
    msgs = story.get("messages", [])
    if not msgs:
        st.info("No messages yet. Start writing below!")
        return False

    saved = False
    to_delete = None

    st.markdown("""
        <div style='background:rgba(255,165,0,0.08);border:1px solid rgba(255,165,0,0.3);
        border-radius:10px;padding:8px 14px;margin-bottom:12px;font-size:0.8rem;color:#FFA500;'>
        ✏️ <b>Edit Mode</b> — click Edit on any message to change it.
        Changes are saved immediately.
        </div>
    """, unsafe_allow_html=True)

    for i, msg in enumerate(msgs):
        role    = msg.get("role", "user")
        content = msg.get("content", "")
        edit_key = f"_edit_active_{i}"
        text_key = f"_edit_text_{i}"

        # Bubble HTML
        if role == "user":
            bubble_html = f"""
            <div style='background:rgba(77,107,254,0.08);border:1px solid rgba(77,107,254,0.2);
            border-radius:12px;padding:12px 16px;margin:6px 0;'>
            <div style='font-size:0.72rem;color:#6B7080;margin-bottom:4px;'>🧑‍💻 You</div>
            <div style='font-size:0.9rem;color:#E2E8F0;white-space:pre-wrap;'>{_html.escape(content)}</div>
            </div>"""
        else:
            bubble_html = f"""
            <div style='background:rgba(30,32,42,0.8);border:1px solid rgba(77,107,254,0.15);
            border-radius:12px;padding:12px 16px;margin:6px 0;'>
            <div style='font-size:0.72rem;color:#4D6BFE;margin-bottom:4px;'>◆ NarrativeForge</div>
            <div style='font-size:0.9rem;color:#E2E8F0;white-space:pre-wrap;'>{_html.escape(content)}</div>
            </div>"""

        if not st.session_state.get(edit_key):
            st.markdown(bubble_html, unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 1, 8])
            with c1:
                if st.button("✏️", key=f"edit_btn_{i}", help="Edit this message"):
                    st.session_state[edit_key] = True
                    st.session_state[text_key] = content
                    st.rerun()
            with c2:
                if st.button("🗑", key=f"del_btn_{i}", help="Delete this message"):
                    to_delete = i
        else:
            # Edit mode for this bubble
            st.markdown(f"<div style='font-size:0.75rem;color:#FFA500;margin-bottom:4px;'>✏️ Editing message {i+1}</div>",
                        unsafe_allow_html=True)
            new_text = st.text_area(
                "Edit content",
                value=st.session_state.get(text_key, content),
                key=f"edit_area_{i}",
                height=150,
                label_visibility="collapsed"
            )
            s1, s2 = st.columns(2)
            with s1:
                if st.button("💾 Save", key=f"save_edit_{i}", use_container_width=True, type="primary"):
                    story["messages"][i]["content"] = new_text
                    save_fn(username, story)
                    st.session_state.pop(edit_key, None)
                    st.session_state.pop(text_key, None)
                    saved = True
                    st.rerun()
            with s2:
                if st.button("✕ Cancel", key=f"cancel_edit_{i}", use_container_width=True):
                    st.session_state.pop(edit_key, None)
                    st.session_state.pop(text_key, None)
                    st.rerun()

    # Handle delete
    if to_delete is not None:
        story["messages"].pop(to_delete)
        save_fn(username, story)
        saved = True
        st.rerun()

    return saved


# ──────────────────────────────────────────────────────────────────────────────
# 3.  BOOK WRITING MODE  (clean manuscript / Scrivener-style)
# ──────────────────────────────────────────────────────────────────────────────
_BOOK_MODE_CSS = """
<style>
.book-page {
    background: #FEFEF9;
    color: #1a1a1a;
    font-family: 'Georgia', 'Times New Roman', serif;
    font-size: 1.05rem;
    line-height: 1.9;
    max-width: 680px;
    margin: 0 auto;
    padding: 48px 56px;
    border-radius: 4px;
    box-shadow: 0 4px 32px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.1);
    min-height: 80vh;
}
.book-title {
    font-size: 1.6rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 6px;
    letter-spacing: 0.04em;
}
.book-meta {
    text-align: center;
    font-style: italic;
    color: #888;
    font-size: 0.88rem;
    margin-bottom: 36px;
}
.book-divider {
    text-align: center;
    color: #bbb;
    margin: 28px 0;
    letter-spacing: 0.5em;
    font-size: 0.9rem;
}
.book-para {
    text-indent: 2em;
    margin: 0 0 0 0;
}
.book-para-first {
    margin-top: 0;
}
.book-user-prompt {
    color: #888;
    font-style: italic;
    font-size: 0.85rem;
    border-left: 2px solid #ddd;
    padding-left: 12px;
    margin: 20px 0 8px 0;
    display: none;
}
.book-chapter-num {
    text-align: center;
    font-size: 0.8rem;
    letter-spacing: 0.2em;
    color: #aaa;
    margin: 32px 0 8px 0;
    text-transform: uppercase;
}
.book-chapter-title {
    text-align: center;
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 24px;
}
/* Dark wrapper stays dark, book page is light */
.book-wrapper {
    background: #1a1a2e;
    padding: 32px 16px 64px;
    border-radius: 12px;
    margin-top: 8px;
}
</style>
"""

def show_book_mode(story, username, save_fn, characters=None):
    """
    Full-screen book writing / reading mode.
    Shows clean typeset prose + inline editing + book PDF download.
    """
    st.markdown(_BOOK_MODE_CSS, unsafe_allow_html=True)

    title  = story.get("title", "Untitled")
    genre  = story.get("genre", "")
    tone   = story.get("tone", "")
    msgs   = story.get("messages", [])

    # ── Top bar ───────────────────────────────────────────────────────────────
    col_back, col_dl, col_edit, col_title = st.columns([1, 1.2, 1.2, 4])
    with col_back:
        if st.button("← Exit", key="bm_exit", use_container_width=True):
            st.session_state.pop("book_mode", None)
            st.rerun()

    with col_dl:
        buf = export_book_pdf(story, characters or [], author=username)
        if buf:
            slug = re.sub(r"[^\w]", "_", title)[:40]
            st.download_button(
                "📥 Book PDF",
                data=buf,
                file_name=f"{slug}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="bm_dl_pdf"
            )
        else:
            st.warning("Install reportlab for PDF")

    with col_edit:
        edit_mode = st.session_state.get("bm_edit_mode", False)
        label = "✅ Done Editing" if edit_mode else "✏️ Edit Mode"
        if st.button(label, key="bm_edit_toggle", use_container_width=True):
            st.session_state["bm_edit_mode"] = not edit_mode
            st.rerun()

    with col_title:
        st.markdown(f"<div style='padding-top:6px;font-size:1rem;font-weight:600;"
                    f"color:#4D6BFE;'>📖 {_html.escape(title)}</div>",
                    unsafe_allow_html=True)

    st.markdown("---")

    # ── Edit Mode ─────────────────────────────────────────────────────────────
    if st.session_state.get("bm_edit_mode"):
        show_message_editor(story, username, save_fn)
        return

    # ── Book render ───────────────────────────────────────────────────────────
    # Build HTML for the book page
    parts = [f"""
    <div class='book-wrapper'>
    <div class='book-page'>
        <div class='book-title'>{_html.escape(title)}</div>
        <div class='book-meta'>{_html.escape(genre)} · {_html.escape(tone)}</div>
    """]

    chapter_num = 0
    for i, msg in enumerate(msgs):
        role    = msg.get("role", "user")
        content = msg.get("content", "").strip()
        if not content:
            continue

        if role == "user":
            # Show as a subtle chapter prompt / direction (optional, hidden by default)
            first_line = content.split("\n")[0][:80]
            chapter_num += 1
            parts.append(f"<div class='book-chapter-num'>— {chapter_num} —</div>")
            if len(first_line) < 60 and len(first_line) > 4:
                parts.append(f"<div class='book-chapter-title'>{_html.escape(first_line)}</div>")
        else:
            # AI prose — typeset as book paragraphs
            paragraphs = [p.strip() for p in re.split(r'\n{2,}|\n', content) if p.strip()]
            for j, para in enumerate(paragraphs):
                if para in ("* * *", "---", "***"):
                    parts.append("<div class='book-divider'>✦ &nbsp; ✦ &nbsp; ✦</div>")
                else:
                    css_class = "book-para-first" if j == 0 else "book-para"
                    parts.append(f"<div class='{css_class}'>{_html.escape(para)}</div>")
            parts.append("<div style='margin-bottom:20px'></div>")

    parts.append("<div class='book-divider' style='margin-top:40px'>— THE END —</div>")
    parts.append("</div></div>")  # close book-page + book-wrapper

    st.markdown("".join(parts), unsafe_allow_html=True)

    # ── Write more — inline chat input ───────────────────────────────────────
    st.markdown("<div style='max-width:680px;margin:24px auto 0;'>", unsafe_allow_html=True)
    new_input = st.chat_input("Continue your story…", key="bm_chat_input")
    st.markdown("</div>", unsafe_allow_html=True)

    if new_input:
        story["messages"].append({"role": "user", "content": new_input})
        save_fn(username, story)
        st.session_state["bm_pending"] = new_input
        st.rerun()

    # ── Stream AI response if pending ────────────────────────────────────────
    if st.session_state.get("bm_pending"):
        try:
            import llm
            pending = st.session_state.pop("bm_pending")
            chars_list = characters or []
            prompt = (
                f"Story: {title}\nGenre: {genre}\nTone: {tone}\n\n"
                f"Continue this story based on: {pending}\n\n"
                f"Write 2-3 vivid paragraphs of prose. No dialogue tags. Pure narrative."
            )
            slot = st.empty()
            tokens = []
            for token in llm.stream(prompt):
                tokens.append(token)
                slot.markdown(
                    f"<div class='book-wrapper'><div class='book-page' style='min-height:auto'>"
                    f"{''.join(tokens)}</div></div>",
                    unsafe_allow_html=True
                )
            ai_text = "".join(tokens).strip()
            if ai_text:
                story["messages"].append({"role": "assistant", "content": ai_text})
                save_fn(username, story)
            st.rerun()
        except Exception:
            st.error("AI unavailable")
