"""
NarrativeForge — Director's Cut Mode
Split-screen: prose on the left, live-converted screenplay on the right.
Scroll is synced. Export both views together.
"""
import re
import html as _html
import textwrap
import streamlit as st


# ── Prose → Screenplay Converter ──────────────────────────────────────────
_LOCATION_KW = re.compile(
    r'\b(room|hall|forest|cave|castle|village|city|street|tavern|inn|library|'
    r'garden|dungeon|throne|courtyard|market|church|palace|mansion|house|'
    r'ship|tent|camp|field|road|bridge|tower|shore|beach|mountain|valley|'
    r'office|apartment|kitchen|cellar|attic|barn|stable|harbour|dock)\b',
    re.IGNORECASE)

_DIALOGUE_RE = re.compile(
    r'^["""](.+?)["""][,.]?\s*(?:([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+'
    r'(?:said|replied|whispered|shouted|asked|muttered|snapped|breathed|called|cried|demanded))?',
    re.MULTILINE)

_SAID_RE = re.compile(
    r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+'
    r'(?:said|replied|whispered|shouted|asked|muttered|snapped|breathed|called|cried|demanded)'
    r'[,:]?\s+["""](.+?)["""]',
    re.IGNORECASE)

_TIME_KW = re.compile(
    r'\b(night|midnight|dawn|dusk|evening|morning|afternoon|noon|midday|'
    r'sunrise|sunset|twilight|darkness|daylight)\b', re.IGNORECASE)


def _to_screenplay(prose: str) -> str:
    """Convert prose paragraphs to Fountain-compatible screenplay format."""
    paragraphs = [p.strip() for p in prose.split('\n\n') if p.strip()]
    lines  = []
    sc_num = 1

    for para in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', para)

        # Detect scene heading triggers
        loc_match = _LOCATION_KW.search(para)
        if loc_match and len(para) < 200:
            loc = loc_match.group(0).upper()
            time_match = _TIME_KW.search(para)
            time_of_day = time_match.group(0).upper() if time_match else "DAY"
            lines += ["", f"INT. {loc} — {time_of_day}  (Scene {sc_num})", ""]
            sc_num += 1

        # Collect dialogue from this paragraph
        said_matches = _SAID_RE.findall(para)
        direct_matches = _DIALOGUE_RE.findall(para)

        if said_matches:
            for char, dialogue in said_matches:
                lines += ["", f"                    {char.upper()}", f"          {dialogue}", ""]
            # Action line from remaining text
            action = _SAID_RE.sub('', para).strip()
            if action and len(action) > 10:
                for wrapped in textwrap.wrap(action, 58):
                    lines.append(wrapped)
        elif direct_matches:
            for dialogue, char in direct_matches:
                speaker = char.upper() if char else "CHARACTER"
                lines += ["", f"                    {speaker}", f"          {dialogue}", ""]
        else:
            # Pure action / description
            for sent in sentences:
                sent = sent.strip()
                if sent:
                    for wrapped in textwrap.wrap(sent, 58):
                        lines.append(wrapped)

    lines += ["", "", "FADE OUT.", ""]
    return '\n'.join(lines)


def _prose_from_story(story) -> str:
    msgs = [m for m in story.get("messages", [])
            if m.get("role") == "assistant"
            and not m["content"].startswith("◆")]
    return "\n\n".join(m["content"] for m in msgs)


# ── CSS ────────────────────────────────────────────────────────────────────
_DC_CSS = """
<style>
.dc-panel {
    background: var(--bg-card);
    border: 1px solid var(--primary-border);
    border-radius: 10px;
    padding: 20px 22px;
    height: 70vh;
    overflow-y: auto;
    font-size: 0.88rem;
    line-height: 1.85;
    color: var(--text-primary);
    font-family: 'Georgia', serif;
}
.dc-panel.screenplay {
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.82rem;
    background: #0a0b10;
    color: #d4d8e8;
}
.dc-panel p { margin-bottom: 0.7em; text-indent: 2em; }
.dc-panel p:first-child { text-indent: 0; }
.dc-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6B7080;
    margin-bottom: 8px;
}
.dc-scene-head {
    color: #A8BCFF;
    font-weight: 700;
    margin: 1.2em 0 0.4em;
    font-family: 'Courier New', monospace;
}
.dc-dialogue-char {
    text-align: center;
    font-weight: 700;
    color: #fbbf24;
    margin-top: 1em;
    font-family: 'Courier New', monospace;
}
.dc-dialogue-text {
    margin: 0 3em;
    font-style: italic;
    color: #C5C8D4;
    font-family: 'Courier New', monospace;
}
.dc-action {
    color: #d4d8e8;
    font-family: 'Courier New', monospace;
}
</style>
"""

def _render_screenplay_html(screenplay_text: str) -> str:
    """Convert plain Fountain text to styled HTML for the right panel."""
    parts = []
    lines = screenplay_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Scene heading: starts with INT. or EXT.
        if re.match(r'^(INT\.|EXT\.)', stripped):
            parts.append(f'<div class="dc-scene-head">🎬 {_html.escape(stripped)}</div>')

        # Character name (all-caps, roughly centered)
        elif re.match(r'^\s{18,}[A-Z][A-Z\s]+$', line) and len(stripped) < 40 and stripped:
            parts.append(f'<div class="dc-dialogue-char">{_html.escape(stripped)}</div>')

        # Dialogue (indented ~10 spaces)
        elif re.match(r'^\s{8,}[^A-Z\s]', line) and stripped:
            parts.append(f'<div class="dc-dialogue-text">{_html.escape(stripped)}</div>')

        # Action lines
        elif stripped and not stripped.startswith('---'):
            parts.append(f'<div class="dc-action">{_html.escape(stripped)}</div>')

        elif not stripped:
            parts.append('<div style="height:0.6em;"></div>')

        i += 1
    return '\n'.join(parts)


# ── Main Panel ─────────────────────────────────────────────────────────────
def show_directors_cut(story, ctx=""):
    """Render the full Director's Cut split-screen view."""
    st.markdown(_DC_CSS, unsafe_allow_html=True)

    prose = _prose_from_story(story)

    if not prose or len(prose.split()) < 20:
        st.markdown(
            "<div style='text-align:center;color:#6B7080;padding:60px;font-size:0.84rem;'>"
            "Write at least a few paragraphs to use Director's Cut mode.</div>",
            unsafe_allow_html=True)
        return

    # Controls
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])
    with ctrl1:
        chunk = st.selectbox("Show",
            ["Full story", "Last 500 words", "Last 1000 words", "First 500 words"],
            key=f"dc_chunk_{ctx}")
    with ctrl2:
        sync_scroll = st.checkbox("Highlight scene breaks", value=True, key=f"dc_sync_{ctx}")
    with ctrl3:
        if st.button("⬇ Export Screenplay (.txt)", key=f"dc_export_{ctx}",
                     use_container_width=True):
            full_screenplay = _to_screenplay(prose)
            title_slug = story.get("title", "story").replace(" ", "_")[:40]
            st.download_button(
                "⬇ Download", data=full_screenplay.encode("utf-8"),
                file_name=f"{title_slug}_directors_cut.txt",
                mime="text/plain", key=f"dc_dl_{ctx}")

    # Slice prose
    words = prose.split()
    if chunk == "Last 500 words":
        prose_view = " ".join(words[-500:])
    elif chunk == "Last 1000 words":
        prose_view = " ".join(words[-1000:])
    elif chunk == "First 500 words":
        prose_view = " ".join(words[:500])
    else:
        prose_view = prose

    # Convert to screenplay
    screenplay = _to_screenplay(prose_view)

    # Build HTML for prose panel
    prose_paras = [p.strip() for p in prose_view.split('\n\n') if p.strip()]
    prose_html_parts = []
    for para in prose_paras:
        if sync_scroll and _LOCATION_KW.search(para):
            prose_html_parts.append(
                f"<div style='margin:12px 0 4px;padding:4px 8px;"
                f"background:rgba(77,107,254,0.1);border-left:3px solid #4D6BFE;"
                f"font-size:0.72rem;color:#A8BCFF;font-family:monospace;'>"
                f"📍 Scene break</div>")
        prose_html_parts.append(f"<p>{_html.escape(para)}</p>")
    prose_html = "\n".join(prose_html_parts)

    screenplay_html = _render_screenplay_html(screenplay)

    # Stats row
    wc = len(words)
    sc = screenplay.count("INT.") + screenplay.count("EXT.")
    chars_found = set(re.findall(r'\n\s{18,}([A-Z][A-Z\s]+)\n', screenplay))
    st.markdown(
        f"<div style='display:flex;gap:16px;margin-bottom:10px;'>"
        f"<span style='font-size:0.72rem;color:#6B7080;'>📝 {wc:,} words</span>"
        f"<span style='font-size:0.72rem;color:#6B7080;'>🎬 {sc} scenes</span>"
        f"<span style='font-size:0.72rem;color:#6B7080;'>🎭 {len(chars_found)} speaking characters</span>"
        f"</div>",
        unsafe_allow_html=True)

    # Split-screen
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='dc-label'>📖 Novel Prose</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='dc-panel'>{prose_html}</div>",
            unsafe_allow_html=True)
    with col_r:
        st.markdown("<div class='dc-label'>🎬 Screenplay Format</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='dc-panel screenplay'>{screenplay_html}</div>",
            unsafe_allow_html=True)
