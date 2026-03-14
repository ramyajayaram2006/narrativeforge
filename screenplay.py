"""
screenplay.py — Screenplay Converter & Exporter for NarrativeForge
Converts prose to professional screenplay format.
Export: .txt (formatted), .pdf (via reportlab), .fdx structure (Final Draft XML)
"""

import io
import re
import html as _html
import streamlit as st

# ── Screenplay formatting constants ───────────────────────────────────────────
_SCENE_HEADING_WORDS = {
    "int.", "ext.", "interior", "exterior", "int/ext", "ext/int",
    "inside", "outside",
}
_TRANSITIONS = {
    "cut to", "fade in", "fade out", "dissolve to", "smash cut", "match cut",
    "cut back to", "intercut", "jump cut",
}
_DAY_NIGHT = {"day", "night", "morning", "evening", "dusk", "dawn",
              "continuous", "later", "moments later", "same", "afternoon"}


def _is_scene_heading(line):
    low = line.strip().lower()
    return any(low.startswith(w) for w in _SCENE_HEADING_WORDS)

def _is_transition(line):
    low = line.strip().rstrip(":").lower()
    return low in _TRANSITIONS

def _is_dialogue_tag(line):
    """Heuristic: all-caps word(s) on their own line = character name before dialogue."""
    stripped = line.strip()
    return (stripped.isupper() and 2 <= len(stripped.split()) <= 4
            and not _is_transition(stripped))

def _classify_line(line):
    if not line.strip():
        return "blank"
    if _is_scene_heading(line):
        return "scene"
    if _is_transition(line):
        return "transition"
    if _is_dialogue_tag(line):
        return "character"
    return "action"


def ai_prose_to_screenplay(prose, characters=None, story=None):
    """
    Convert raw prose to a best-effort screenplay structure.
    Returns list of (type, text) tuples.
    """
    char_names = set()
    if characters:
        for c in characters:
            char_names.add(c["name"].upper())

    lines = prose.split("\n")
    result = []
    i = 0

    # Pre-process: identify spoken dialogue patterns "Elena said, '...'"
    # Heuristic: lines containing known character names followed by said/asked/whispered
    _said_re = re.compile(
        r'^\s*"(.+?)"\s*[,.]?\s*(' + '|'.join(['said', 'asked', 'whispered',
        'shouted', 'replied', 'muttered', 'called', 'yelled', 'cried',
        'laughed', 'responded', 'insisted', 'declared']) + r')\b',
        re.IGNORECASE)

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            result.append(("blank", ""))
            i += 1
            continue

        # Quoted speech → dialogue
        m = _said_re.match(line)
        if m:
            spoken = m.group(1)
            # Try to find speaker from context
            speaker = "CHARACTER"
            for name in char_names:
                if name.lower() in line.lower():
                    speaker = name
                    break
            result.append(("character", speaker))
            result.append(("dialogue", spoken))
            i += 1
            continue

        # Explicit scene heading patterns
        if _is_scene_heading(line):
            heading = line.upper()
            if not any(d in heading for d in [w.upper() for w in _DAY_NIGHT]):
                heading += " - DAY"
            result.append(("scene", heading))
            i += 1
            continue

        # Transition
        if _is_transition(line):
            t = line.strip().upper()
            if not t.endswith(":"):
                t += ":"
            result.append(("transition", t))
            i += 1
            continue

        # Default: action/description
        result.append(("action", line))
        i += 1

    return result


def screenplay_to_txt(elements, title="UNTITLED", author=""):
    """
    Format screenplay elements into standard plain-text screenplay format.
    Margins: Scene 0, Action 0, Character 35, Dialogue 25, Transition right-justified.
    """
    lines = []

    def center(text, width=60):
        return text.center(width)

    def pad_left(text, spaces):
        return " " * spaces + text

    def wrap(text, width, indent=0):
        words = text.split()
        result, current = [], []
        for w in words:
            current.append(w)
            if sum(len(x) + 1 for x in current) > width:
                lines_out = " ".join(current[:-1])
                result.append(" " * indent + lines_out)
                current = [w]
        if current:
            result.append(" " * indent + " ".join(current))
        return "\n".join(result)

    # Title page
    lines += ["\n" * 3, center(title.upper()), ""]
    if author:
        lines += [center(f"Written by {author}"), ""]
    lines += ["\n" * 2]

    prev_type = None
    for typ, text in elements:
        if typ == "blank":
            if prev_type not in ("blank", None):
                lines.append("")
        elif typ == "scene":
            lines.append("")
            lines.append(text.upper())
            lines.append("")
        elif typ == "action":
            lines.append(wrap(text, 65, 0))
        elif typ == "character":
            lines.append("")
            lines.append(pad_left(text.upper(), 35))
        elif typ == "dialogue":
            wrapped = wrap(text, 35, 25)
            lines.append(wrapped)
        elif typ == "transition":
            lines.append("")
            # Right-justify transitions
            t = text.upper()
            lines.append(t.rjust(65))
            lines.append("")
        prev_type = typ

    lines.append("\n\n\nFADE OUT.\n\n                                         THE END")
    return "\n".join(lines)


def screenplay_to_fdx(elements, title="UNTITLED", author=""):
    """Generate Final Draft XML (.fdx) format."""
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    type_map = {
        "scene":      "Scene Heading",
        "action":     "Action",
        "character":  "Character",
        "dialogue":   "Dialogue",
        "transition": "Transition",
        "blank":      "General",
    }

    paras = []
    for typ, text in elements:
        ft = type_map.get(typ, "Action")
        paras.append(
            f'    <Paragraph Type="{ft}">\n'
            f'      <Text>{esc(text)}</Text>\n'
            f'    </Paragraph>')

    fdx = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<FinalDraft DocumentType="Script" Template="No" Version="1">\n'
        f'  <Content>\n'
        + "\n".join(paras) +
        '\n  </Content>\n'
        '</FinalDraft>'
    )
    return fdx


def screenplay_to_pdf(elements, title="UNTITLED", author=""):
    """Generate PDF screenplay using reportlab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    except ImportError:
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=1.5*inch, rightMargin=1.0*inch,
        topMargin=1.0*inch, bottomMargin=1.0*inch,
        title=title, author=author)

    styles = getSampleStyleSheet()
    courier = "Courier"

    def sty(name, parent="Normal", **kw):
        return ParagraphStyle(name, parent=styles[parent],
                              fontName=courier, fontSize=12,
                              leading=14.4, **kw)

    scene_sty  = sty("Scene",  spaceAfter=6, spaceBefore=12, textColor=colors.black)
    action_sty = sty("Action", spaceAfter=6)
    char_sty   = sty("Char",   leftIndent=2.1*inch, spaceAfter=0)
    dial_sty   = sty("Dial",   leftIndent=1.4*inch, rightIndent=1.1*inch, spaceAfter=6)
    trans_sty  = sty("Trans",  alignment=TA_RIGHT, spaceAfter=12, spaceBefore=6)

    story_el = []
    # Title page
    story_el.append(Spacer(1, 2*inch))
    story_el.append(Paragraph(f"<b>{title.upper()}</b>",
                               sty("T", alignment=TA_CENTER, fontSize=18)))
    if author:
        story_el.append(Spacer(1, 0.3*inch))
        story_el.append(Paragraph(f"Written by {author}",
                                   sty("Au", alignment=TA_CENTER)))
    story_el.append(Spacer(1, 2*inch))

    for typ, text in elements:
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if typ == "blank":
            story_el.append(Spacer(1, 0.1*inch))
        elif typ == "scene":
            story_el.append(Paragraph(f"<b>{safe}</b>", scene_sty))
        elif typ == "action":
            story_el.append(Paragraph(safe, action_sty))
        elif typ == "character":
            story_el.append(Paragraph(safe.upper(), char_sty))
        elif typ == "dialogue":
            story_el.append(Paragraph(safe, dial_sty))
        elif typ == "transition":
            story_el.append(Paragraph(f"<b>{safe}</b>", trans_sty))

    try:
        doc.build(story_el)
    except Exception:
        return None
    buf.seek(0)
    return buf


# ── Streamlit UI ───────────────────────────────────────────────────────────────
def show_screenplay_tab(story, characters=None, ctx=""):
    """Renders the screenplay converter tab inside workspace."""
    st.markdown(
        "<div style='font-size:0.75rem;color:#6B7080;margin-bottom:12px;'>"
        "Converts your prose to professional screenplay format. "
        "Best results with stories containing dialogue and scene descriptions.</div>",
        unsafe_allow_html=True)

    if not story.get("messages"):
        st.info("Write some story first to convert to screenplay.")
        return

    # ── Collect AI prose ──────────────────────────────────────────────────────
    ai_msgs = [m for m in story["messages"]
               if m["role"] == "assistant" and not m["content"].startswith("◆")]
    prose = "\n\n".join(m["content"] for m in ai_msgs)

    col_settings, col_preview = st.columns([1, 2])

    with col_settings:
        st.markdown("**⚙️ Settings**")
        author = st.text_input("Author name", value=st.session_state.get("username", ""),
                                key=f"sp_author_{ctx}", max_chars=80)
        add_scene_per_para = st.toggle("Add scene heading per section",
                                        value=False, key=f"sp_scene_per_para_{ctx}")

        st.markdown("**📥 Export**")
        do_convert = st.button("🎬 Convert to Screenplay", key=f"sp_convert_{ctx}",
                                use_container_width=True)

    # ── Conversion ────────────────────────────────────────────────────────────
    cache_key = f"_screenplay_{story['id']}"
    if do_convert or st.session_state.get(cache_key):
        if do_convert:
            # Add opening scene if enabled
            raw = prose
            if add_scene_per_para:
                # Insert INT. scene headings at paragraph breaks > 100 words
                paras = raw.split("\n\n")
                new_paras = []
                for j, p in enumerate(paras):
                    if j > 0 and len(p.split()) > 40:
                        genre = story.get("genre", "Story")
                        new_paras.append(f"INT. {genre.upper()} LOCATION - CONTINUOUS")
                    new_paras.append(p)
                raw = "\n\n".join(new_paras)
            elements = ai_prose_to_screenplay(raw, characters, story)
            st.session_state[cache_key] = elements
        else:
            elements = st.session_state.get(cache_key, [])

        title = story.get("title", "Untitled")
        txt_script = screenplay_to_txt(elements, title, author)

        with col_preview:
            st.markdown("**📜 Preview**")
            with st.expander("Script preview (first 60 lines)", expanded=True):
                preview_lines = txt_script.split("\n")[:60]
                st.code("\n".join(preview_lines), language=None)

        # ── Downloads ─────────────────────────────────────────────────────────
        dl1, dl2, dl3 = st.columns(3)
        fname_base = title.replace(" ", "_")

        with dl1:
            st.download_button(
                "📄 Download .txt",
                data=txt_script.encode("utf-8"),
                file_name=f"{fname_base}.txt",
                mime="text/plain",
                use_container_width=True, key=f"sp_dl_txt_{ctx}")

        with dl2:
            fdx_content = screenplay_to_fdx(elements, title, author)
            st.download_button(
                "🎬 Download .fdx",
                data=fdx_content.encode("utf-8"),
                file_name=f"{fname_base}.fdx",
                mime="application/xml",
                use_container_width=True, key=f"sp_dl_fdx_{ctx}")

        with dl3:
            pdf_buf = screenplay_to_pdf(elements, title, author)
            if pdf_buf:
                st.download_button(
                    "📕 Download .pdf",
                    data=pdf_buf.getvalue(),
                    file_name=f"{fname_base}_screenplay.pdf",
                    mime="application/pdf",
                    use_container_width=True, key=f"sp_dl_pdf_{ctx}")
            else:
                st.caption("PDF needs reportlab")

        # ── Stats ─────────────────────────────────────────────────────────────
        type_counts = {}
        for t, _ in elements:
            type_counts[t] = type_counts.get(t, 0) + 1

        st.markdown("**📊 Screenplay Stats**")
        sc1, sc2, sc3, sc4 = st.columns(4)
        for col, label, key in [
            (sc1, "🎬 Scenes",    "scene"),
            (sc2, "💬 Dialogues", "dialogue"),
            (sc3, "🎭 Characters","character"),
            (sc4, "📝 Actions",   "action"),
        ]:
            with col:
                n = type_counts.get(key, 0)
                st.metric(label, n)
