"""
NarrativeForge — Universal Story Importer
Supports: .txt, .md, .rtf (basic), .docx, Scrivener .scriv (folder),
          plain pasted text, and FDX / Fountain screenplay import.
Converts any format into NarrativeForge story messages.
"""
import io
import re
import html as _html
import zipfile
import streamlit as st


# ── RTF Stripper ──────────────────────────────────────────────────────────
def _strip_rtf(data: bytes) -> str:
    """Basic RTF to plain text — handles most common RTF files."""
    try:
        text = data.decode("latin-1", errors="replace")
    except Exception:
        text = data.decode("utf-8", errors="replace")

    # Remove RTF control words and groups
    text = re.sub(r'\\[a-z]+[-\d]*\s?', '', text)
    text = re.sub(r'\{[^{}]*\}', '', text)
    text = re.sub(r'[{}\\]', '', text)

    # Common RTF escapes
    text = text.replace("\\'e2\\'80\\'9c", '"').replace("\\'e2\\'80\\'9d", '"')
    text = text.replace("\\'e2\\'80\\'99", "'").replace("\\'e2\\'80\\'98", "'")
    text = text.replace("\\'e2\\'80\\'94", "—").replace("\\'e2\\'80\\'93", "–")

    # Clean up whitespace
    lines = [l.strip() for l in text.split('\n')]
    paragraphs = []
    current = []
    for line in lines:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(' '.join(current))
            current = []
    if current:
        paragraphs.append(' '.join(current))

    return '\n\n'.join(p for p in paragraphs if len(p) > 10)


# ── DOCX Reader ────────────────────────────────────────────────────────────
def _read_docx(data: bytes) -> str:
    """Extract text from .docx using zipfile + XML parsing."""
    try:
        buf = io.BytesIO(data)
        with zipfile.ZipFile(buf) as z:
            with z.open("word/document.xml") as f:
                xml = f.read().decode("utf-8", errors="replace")
        # Extract text from <w:t> tags
        texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml)
        # Detect paragraph breaks from <w:p> tags
        full = xml
        full = re.sub(r'<w:p[ />]', '\n\n', full)
        full = re.sub(r'<w:t[^>]*>([^<]*)</w:t>', r'\1', full)
        full = re.sub(r'<[^>]+>', '', full)
        paragraphs = [p.strip() for p in full.split('\n\n') if len(p.strip()) > 10]
        return '\n\n'.join(paragraphs)
    except Exception as e:
        return ""


# ── Scrivener Folder Parser ────────────────────────────────────────────────
def _read_scrivener(uploaded_files) -> dict:
    """
    Parse a Scrivener project exported as individual files.
    Looks for .txt or .rtf files uploaded together.
    Returns: {title, content, metadata}
    """
    docs = []
    title = "Imported Story"

    for f in uploaded_files:
        name = f.name.lower()
        data = f.read()

        if name.endswith('.txt') or name.endswith('.md'):
            text = data.decode("utf-8", errors="replace").strip()
            if text:
                # Check if it looks like a title file
                if len(text) < 100 and '\n' not in text:
                    title = text[:80]
                else:
                    docs.append({"filename": f.name, "text": text})

        elif name.endswith('.rtf'):
            text = _strip_rtf(data)
            if text:
                docs.append({"filename": f.name, "text": text})

        elif name.endswith('.docx'):
            text = _read_docx(data)
            if text:
                docs.append({"filename": f.name, "text": text})

    # Sort by filename (Scrivener numbers them)
    docs.sort(key=lambda d: d["filename"])

    return {
        "title": title,
        "content": "\n\n---\n\n".join(d["text"] for d in docs),
        "doc_count": len(docs),
        "filenames": [d["filename"] for d in docs],
    }


# ── Fountain / FDX Parser ──────────────────────────────────────────────────
def _read_fountain(text: str) -> str:
    """Convert Fountain screenplay to prose paragraphs."""
    lines = text.split('\n')
    prose_parts = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Scene heading
        if re.match(r'^(INT\.|EXT\.|INT/EXT\.|I/E\.)', line):
            prose_parts.append(f"[Scene: {line}]")
        # Dialogue block: character name line followed by dialogue
        elif re.match(r'^[A-Z][A-Z\s]+$', line) and len(line) < 40 and line:
            char = line.strip()
            i += 1
            dialogue_lines = []
            while i < len(lines) and lines[i].strip():
                dl = lines[i].strip()
                if not dl.startswith('('):  # skip parentheticals
                    dialogue_lines.append(dl)
                i += 1
            if dialogue_lines:
                prose_parts.append(f'"{" ".join(dialogue_lines)}" — {char.title()}')
            continue
        # Action lines
        elif line and not line.startswith('===') and not line.startswith('---'):
            prose_parts.append(line)
        i += 1
    return '\n\n'.join(p for p in prose_parts if p)


# ── Text Splitter → Messages ───────────────────────────────────────────────
def _text_to_messages(text: str, chunk_words: int = 300) -> list:
    """Split long text into assistant messages of ~chunk_words each."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    messages   = []
    current    = []
    word_count = 0

    for para in paragraphs:
        wc = len(para.split())
        if word_count + wc > chunk_words and current:
            messages.append({
                "role": "assistant",
                "content": '\n\n'.join(current)
            })
            current, word_count = [para], wc
        else:
            current.append(para)
            word_count += wc

    if current:
        messages.append({
            "role": "assistant",
            "content": '\n\n'.join(current)
        })

    return messages


# ── Main Panel ─────────────────────────────────────────────────────────────
def show_scrivener_import(story, username):
    """Full import panel — upload any supported format and import into story."""
    from database import save_story

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Import any existing writing into this story. Supported formats: "
        "<strong>.txt · .md · .rtf · .docx · .fountain</strong> — "
        "or paste text directly. For Scrivener projects, export as individual "
        "text files and upload them all at once.</div>",
        unsafe_allow_html=True)

    method = st.radio("Import method",
        ["📁 Upload files", "📋 Paste text"],
        horizontal=True, key="imp_method", label_visibility="collapsed")

    imported_text = ""
    suggested_title = story.get("title", "")

    if method == "📁 Upload files":
        uploaded = st.file_uploader(
            "Upload files",
            accept_multiple_files=True,
            type=["txt", "md", "rtf", "docx", "fountain", "fdx"],
            key="imp_upload",
            label_visibility="collapsed")

        if uploaded:
            # Single docx
            if len(uploaded) == 1 and uploaded[0].name.lower().endswith('.docx'):
                imported_text = _read_docx(uploaded[0].read())
                suggested_title = uploaded[0].name.replace(".docx", "").replace("_", " ")

            # Single RTF
            elif len(uploaded) == 1 and uploaded[0].name.lower().endswith('.rtf'):
                imported_text = _strip_rtf(uploaded[0].read())
                suggested_title = uploaded[0].name.replace(".rtf", "").replace("_", " ")

            # Fountain / FDX
            elif len(uploaded) == 1 and uploaded[0].name.lower().endswith(('.fountain', '.fdx')):
                raw = uploaded[0].read().decode("utf-8", errors="replace")
                imported_text = _read_fountain(raw)
                suggested_title = uploaded[0].name.split(".")[0].replace("_", " ")

            # Single txt / md
            elif len(uploaded) == 1:
                imported_text = uploaded[0].read().decode("utf-8", errors="replace").strip()
                suggested_title = uploaded[0].name.split(".")[0].replace("_", " ")

            # Multiple files → Scrivener mode
            else:
                result = _read_scrivener(uploaded)
                imported_text   = result["content"]
                suggested_title = result["title"]
                st.info(
                    f"📁 Found {result['doc_count']} document(s): "
                    f"{', '.join(result['filenames'][:5])}"
                    f"{'…' if len(result['filenames']) > 5 else ''}")

    else:
        imported_text = st.text_area(
            "Paste your text here",
            height=200,
            key="imp_paste",
            placeholder="Paste any text — chapters, scenes, notes — up to 50,000 words…",
            label_visibility="collapsed")

    if not imported_text:
        return

    # Preview
    preview = imported_text[:400] + ("…" if len(imported_text) > 400 else "")
    word_count = len(imported_text.split())
    st.markdown(
        f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
        f"border-radius:8px;padding:12px;margin-bottom:12px;'>"
        f"<div style='font-size:0.68rem;color:#6B7080;margin-bottom:6px;'>"
        f"Preview · {word_count:,} words detected</div>"
        f"<div style='font-size:0.78rem;color:#C5C8D4;line-height:1.6;'>"
        f"{_html.escape(preview)}</div></div>",
        unsafe_allow_html=True)

    # Options
    c1, c2 = st.columns(2)
    with c1:
        chunk_size = st.selectbox("Split into chunks of",
            [200, 300, 500, 800, 1500],
            index=1,
            format_func=lambda x: f"~{x} words",
            key="imp_chunk")
    with c2:
        import_mode = st.selectbox("Import mode",
            ["Append to story", "Replace story", "New story"],
            key="imp_mode")

    new_title = st.text_input("Story title",
        value=suggested_title if suggested_title else story.get("title", ""),
        key="imp_title", max_chars=100)

    st.markdown(
        "<div style='font-size:0.72rem;color:#fbbf24;margin-bottom:10px;'>"
        "⚠️ This will modify your story. Save a snapshot first if needed.</div>",
        unsafe_allow_html=True)

    if st.button("📥 Import Now", key="imp_run", use_container_width=True):
        new_messages = _text_to_messages(imported_text, chunk_size)
        n_msgs = len(new_messages)

        if import_mode == "Replace story":
            story["messages"] = new_messages
            if new_title.strip():
                story["title"] = new_title.strip()

        elif import_mode == "Append to story":
            story["messages"] = story.get("messages", []) + new_messages
            if new_title.strip():
                story["title"] = new_title.strip()

        else:  # "New story" — handled by just telling user to create one
            st.warning(
                "To import as a new story, go back to the Dashboard, "
                "create a new story, then use Import there.")
            return

        save_story(username, story)
        st.success(
            f"✅ Imported {word_count:,} words as {n_msgs} message(s) into '{story['title']}'.")
        st.session_state["stories"] = None  # invalidate cache
        st.rerun()
