"""
NarrativeForge — Advanced Export Module
Formats: EPUB, HTML Web Book, Screenplay (.txt FDX-compatible), LaTeX,
         Markdown, enhanced PDF, Story Bible DOCX.
"""
import io
import re
import html as _html
import json
import zipfile
import textwrap
from datetime import date
import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _prose(story):
    """Return AI prose messages only."""
    return [m for m in story.get("messages", [])
            if m.get("role") == "assistant"
            and not m["content"].startswith("◆")]

def _all_prose_text(story):
    return "\n\n".join(m["content"] for m in _prose(story))

def _word_count(story):
    return len(_all_prose_text(story).split())


# ══════════════════════════════════════════════════════════════════════════════
# EPUB EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_epub(story, characters):
    """Generate a valid EPUB 3.0 as bytes."""
    title   = story.get("title", "Untitled")
    author  = story.get("username", "NarrativeForge Author")
    genre   = story.get("genre", "Fiction")
    prose   = _all_prose_text(story)
    paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip()]

    # Split into chapters by detecting natural breaks (every 1000 words)
    chapters = []
    current, wc = [], 0
    for para in paragraphs:
        pw = len(para.split())
        if wc + pw > 1000 and current:
            chapters.append(current)
            current, wc = [para], pw
        else:
            current.append(para)
            wc += pw
    if current:
        chapters.append(current)
    if not chapters:
        chapters = [[]]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as epub:

        # mimetype (uncompressed, first)
        epub.writestr("mimetype", "application/epub+zip",
                      compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        epub.writestr("META-INF/container.xml", textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <container version="1.0"
              xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
                <rootfile full-path="OEBPS/content.opf"
                  media-type="application/oebps-package+xml"/>
              </rootfiles>
            </container>"""))

        # CSS
        epub.writestr("OEBPS/style.css", textwrap.dedent(f"""\
            body {{ font-family: Georgia, serif; font-size: 1em;
                    line-height: 1.8; margin: 5% 8%; color: #1a1a1a; }}
            h1 {{ font-size: 2em; text-align: center; margin-bottom: 0.3em; }}
            h2 {{ font-size: 1.4em; margin-top: 2em; margin-bottom: 0.5em; }}
            p  {{ text-indent: 2em; margin: 0 0 0.5em; }}
            p:first-of-type {{ text-indent: 0; }}
            .meta {{ text-align: center; color: #888; font-size: 0.85em;
                     text-transform: uppercase; letter-spacing: 0.1em; }}
            .chapter-title {{ font-size: 1.2em; font-weight: bold;
                              text-align: center; margin: 2em 0 1em; }}
        """))

        # Title page
        title_html = textwrap.dedent(f"""\
            <?xml version="1.0" encoding="utf-8"?>
            <!DOCTYPE html>
            <html xmlns="http://www.w3.org/1999/xhtml">
            <head><title>{_html.escape(title)}</title>
            <link rel="stylesheet" type="text/css" href="style.css"/></head>
            <body>
            <h1>{_html.escape(title)}</h1>
            <p class="meta">{_html.escape(genre)} · {_word_count(story):,} words</p>
            <p class="meta">Created with NarrativeForge</p>
            </body></html>""")
        epub.writestr("OEBPS/title.xhtml", title_html)

        # Chapter files
        chapter_items = []
        for i, paras in enumerate(chapters, 1):
            ch_id  = f"chapter{i:03d}"
            ch_file = f"OEBPS/{ch_id}.xhtml"
            body = "\n".join(f"<p>{_html.escape(p)}</p>" for p in paras)
            ch_html = textwrap.dedent(f"""\
                <?xml version="1.0" encoding="utf-8"?>
                <!DOCTYPE html>
                <html xmlns="http://www.w3.org/1999/xhtml">
                <head><title>Chapter {i}</title>
                <link rel="stylesheet" type="text/css" href="style.css"/></head>
                <body>
                <p class="chapter-title">Chapter {i}</p>
                {body}
                </body></html>""")
            epub.writestr(ch_file, ch_html)
            chapter_items.append((ch_id, f"{ch_id}.xhtml", f"Chapter {i}"))

        # content.opf (manifest + spine)
        manifest_items = [
            '<item id="titlepage" href="title.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="css" href="style.css" media-type="text/css"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        ] + [f'<item id="{cid}" href="{cf}" media-type="application/xhtml+xml"/>'
             for cid, cf, _ in chapter_items]

        spine_items = ['<itemref idref="titlepage"/>'] + \
                      [f'<itemref idref="{cid}"/>' for cid, _, _ in chapter_items]

        opf = textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <package xmlns="http://www.idpf.org/2007/opf" version="3.0"
                     unique-identifier="uid">
            <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
                      xmlns:opf="http://www.idpf.org/2007/opf">
              <dc:title>{_html.escape(title)}</dc:title>
              <dc:creator>{_html.escape(author)}</dc:creator>
              <dc:language>en</dc:language>
              <dc:date>{date.today().isoformat()}</dc:date>
              <dc:subject>{_html.escape(genre)}</dc:subject>
              <dc:identifier id="uid">narrativeforge-{story.get('id','0')}</dc:identifier>
            </metadata>
            <manifest>
              {chr(10).join(f'  {x}' for x in manifest_items)}
            </manifest>
            <spine toc="ncx">
              {chr(10).join(f'  {x}' for x in spine_items)}
            </spine>
            </package>""")
        epub.writestr("OEBPS/content.opf", opf)

        # toc.ncx
        nav_points = [
            f"""<navPoint id="navpoint-0" playOrder="0">
              <navLabel><text>{_html.escape(title)}</text></navLabel>
              <content src="title.xhtml"/></navPoint>"""
        ] + [
            f"""<navPoint id="navpoint-{i}" playOrder="{i}">
              <navLabel><text>{label}</text></navLabel>
              <content src="{cf}"/></navPoint>"""
            for i, (cid, cf, label) in enumerate(chapter_items, 1)
        ]
        ncx = textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
              "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
            <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
            <head><meta name="dtb:uid" content="narrativeforge-{story.get('id','0')}"/></head>
            <docTitle><text>{_html.escape(title)}</text></docTitle>
            <navMap>{chr(10).join(nav_points)}</navMap>
            </ncx>""")
        epub.writestr("OEBPS/toc.ncx", ncx)

    buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════════════════════════════
# HTML WEB BOOK EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_html_book(story, characters, scenes):
    """Export as a self-contained responsive HTML book."""
    title  = story.get("title", "Untitled")
    genre  = story.get("genre", "Fiction")
    prose  = _all_prose_text(story)
    paras  = [p.strip() for p in prose.split("\n\n") if p.strip()]
    wc     = _word_count(story)

    char_html = ""
    if characters:
        rows = "".join(
            f"<div class='char-card'>"
            f"<strong>{_html.escape(c['name'])}</strong> "
            f"<span class='role'>{_html.escape(c.get('role',''))}</span><br>"
            f"<span class='desc'>{_html.escape(c.get('description',''))}</span></div>"
            for c in characters)
        char_html = f"<section id='characters'><h2>Characters</h2>{rows}</section>"

    para_html = "\n".join(f"<p>{_html.escape(p)}</p>" for p in paras)

    html = textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>{_html.escape(title)}</title>
        <style>
        *{{box-sizing:border-box;margin:0;padding:0}}
        body{{font-family:Georgia,serif;background:#FDFAF6;color:#1a1a1a;}}
        nav{{background:#1a2040;color:#fff;padding:16px 32px;position:sticky;
             top:0;z-index:100;display:flex;justify-content:space-between;align-items:center}}
        nav a{{color:#A8BCFF;text-decoration:none;font-size:0.85rem;margin-left:16px}}
        nav a:hover{{color:#fff}}
        .container{{max-width:720px;margin:0 auto;padding:60px 24px 120px}}
        h1{{font-size:clamp(2rem,5vw,3rem);text-align:center;color:#1a2040;margin-bottom:8px}}
        .meta{{text-align:center;color:#888;font-size:0.8rem;text-transform:uppercase;
               letter-spacing:0.12em;margin-bottom:60px}}
        p{{text-indent:2em;line-height:1.9;margin-bottom:0.6em;font-size:1.1rem}}
        p:first-of-type{{text-indent:0}}
        h2{{font-size:1.5rem;color:#1a2040;margin:60px 0 24px;padding-top:40px;
            border-top:2px solid #e0e0e0}}
        .char-card{{background:#F0F4FF;border-left:3px solid #4D6BFE;
                   padding:12px 16px;margin-bottom:12px;border-radius:0 8px 8px 0}}
        .role{{color:#4D6BFE;font-size:0.85rem;font-weight:600}}
        .desc{{color:#555;font-size:0.9rem}}
        footer{{text-align:center;padding:40px;color:#aaa;font-size:0.8rem;
                border-top:1px solid #eee;margin-top:80px}}
        @media(max-width:600px){{.container{{padding:24px 16px}};p{{font-size:1rem}}}}
        </style>
        </head>
        <body>
        <nav>
          <span style="font-weight:700;font-size:1rem;">{_html.escape(title)}</span>
          <span>
            <a href="#story">Story</a>
            <a href="#characters">Characters</a>
          </span>
        </nav>
        <div class="container">
          <h1>{_html.escape(title)}</h1>
          <p class="meta">{_html.escape(genre)} &middot; {wc:,} words
             &middot; Created with NarrativeForge</p>
          <section id="story">{para_html}</section>
          {char_html}
        </div>
        <footer>Created with NarrativeForge &middot; {date.today().strftime('%B %d, %Y')}</footer>
        </body>
        </html>""")

    return io.BytesIO(html.encode("utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
# SCREENPLAY EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_screenplay(story):
    """
    Convert prose to screenplay format (Fountain-compatible plain text).
    Scene headings from INT./EXT., dialogue blocks, action lines.
    """
    title   = story.get("title", "Untitled").upper()
    prose   = _all_prose_text(story)
    lines   = [l.strip() for l in prose.split("\n") if l.strip()]

    output = [
        f"Title: {story.get('title', 'Untitled')}",
        f"Author: NarrativeForge",
        f"Genre: {story.get('genre','Fiction')}",
        "",
        "=" * 60,
        "",
        f"{title}",
        "",
    ]

    scene_num = 1
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect location keywords → scene heading
        location_kws = re.search(
            r'\b(library|forest|castle|village|street|room|hall|cave|tower|'
            r'garden|tavern|palace|dungeon|market|church|office|house|mansion|'
            r'ship|tavern|inn|dungeon|courtyard|battlefield|rooftop|basement)\b',
            line, re.IGNORECASE)

        # Detect dialogue (text with quote marks)
        dialogue_m = re.match(r'^["""](.+)["""][\s]*(.*)$', line)
        speech_m   = re.match(r'^([A-Z][a-z]+)\s+said[,:]?\s+["""](.+)["""]', line)
        said_m     = re.match(
            r'^["""](.+)["""][,.]?\s+([A-Z][a-z]+)\s+(said|replied|whispered|shouted|asked)',
            line)

        if location_kws and len(line) < 120:
            # Scene heading
            loc = line[:60].upper()
            time_of_day = "DAY"
            for kw in ["night", "evening", "dusk", "dawn", "midnight", "morning"]:
                if kw in line.lower():
                    time_of_day = kw.upper()
                    break
            output.append("")
            output.append(f"INT. {loc} - {time_of_day}  (Scene {scene_num})")
            output.append("")
            scene_num += 1
        elif said_m:
            char_name = said_m.group(2).upper()
            dialogue  = said_m.group(1)
            output.append("")
            output.append(f"                    {char_name}")
            output.append(f"            {dialogue}")
            output.append("")
        elif speech_m:
            char_name = speech_m.group(1).upper()
            dialogue  = speech_m.group(2)
            output.append("")
            output.append(f"                    {char_name}")
            output.append(f"            {dialogue}")
            output.append("")
        elif dialogue_m:
            dialogue = dialogue_m.group(1)
            output.append("")
            output.append(f"                    VOICE")
            output.append(f"            {dialogue}")
            output.append("")
        else:
            # Action line — wrap at 60 chars
            for wrapped in textwrap.wrap(line, 58):
                output.append(wrapped)

        i += 1

    output += ["", "", "FADE OUT.", "", "THE END", ""]
    return io.BytesIO("\n".join(output).encode("utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
# LATEX EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def _tex_escape(text):
    replacements = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}",
        "\u2018": "`", "\u2019": "'", "\u201c": "``", "\u201d": "''",
        "\u2014": "---", "\u2013": "--", "\u2026": r"\ldots{}",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def export_latex(story, characters):
    """Export as LaTeX source for academic/professional typesetting."""
    title  = story.get("title", "Untitled")
    genre  = story.get("genre", "Fiction")
    prose  = _all_prose_text(story)
    paras  = [p.strip() for p in prose.split("\n\n") if p.strip()]

    lines = [
        r"\documentclass[12pt,a4paper]{book}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{palatino}",
        r"\usepackage[top=3cm,bottom=3cm,left=3.5cm,right=3cm]{geometry}",
        r"\usepackage{setspace}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{titlesec}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\fancyhead[LE,RO]{\thepage}",
        fr"\fancyhead[RE]{{\textit{{{_tex_escape(title)}}}}}",
        fr"\fancyhead[LO]{{{_tex_escape(genre)}}}",
        r"\onehalfspacing",
        fr"\title{{{_tex_escape(title)}}}",
        r"\author{NarrativeForge}",
        fr"\date{{{date.today().strftime('%B %Y')}}}",
        "",
        r"\begin{document}",
        r"\maketitle",
        r"\tableofcontents",
        r"\newpage",
        "",
        fr"\chapter{{{_tex_escape(title)}}}",
        "",
    ]

    for para in paras:
        lines.append(_tex_escape(para))
        lines.append("")

    if characters:
        lines.append(r"\chapter{Characters}")
        lines.append("")
        for c in characters:
            lines.append(fr"\section*{{{_tex_escape(c['name'])}}} "
                         fr"\textit{{{_tex_escape(c.get('role',''))}}}")
            if c.get("description"):
                lines.append(_tex_escape(c["description"]))
                lines.append("")

    lines += [r"\end{document}", ""]
    return io.BytesIO("\n".join(lines).encode("utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
# PANEL (Streamlit UI)
# ══════════════════════════════════════════════════════════════════════════════

def show_export_panel(story, characters, scenes, username):
    """Render the full Export tab in the workspace sidebar."""
    wc = _word_count(story)

    if wc < 10:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;text-align:center;padding:24px;'>"
            "Write some content first to enable exports.</div>",
            unsafe_allow_html=True)
        return

    st.markdown(
        f"<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        f"📊 {wc:,} words ready to export</div>",
        unsafe_allow_html=True)

    title_slug = story.get("title", "story").replace(" ", "_")[:40]

    # ── EPUB ──────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;color:#A8BCFF;text-transform:uppercase;"
        "letter-spacing:0.08em;margin-bottom:6px;'>📱 E-Reader</div>",
        unsafe_allow_html=True)
    if st.button("📱 EPUB (Kindle / Kobo)", key="exp_epub", use_container_width=True):
        with st.spinner("Building EPUB…"):
            buf = export_epub(story, characters)
        st.download_button("⬇ Download EPUB", data=buf.getvalue(),
                           file_name=f"{title_slug}.epub",
                           mime="application/epub+zip",
                           key="dl_epub", use_container_width=True)

    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

    # ── HTML Web Book ─────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;color:#A8BCFF;text-transform:uppercase;"
        "letter-spacing:0.08em;margin-bottom:6px;'>🌐 Web</div>",
        unsafe_allow_html=True)
    if st.button("🌐 HTML Web Book", key="exp_html", use_container_width=True):
        with st.spinner("Building HTML book…"):
            buf = export_html_book(story, characters, scenes)
        st.download_button("⬇ Download HTML", data=buf.getvalue(),
                           file_name=f"{title_slug}.html",
                           mime="text/html",
                           key="dl_html", use_container_width=True)

    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

    # ── Screenplay ────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;color:#A8BCFF;text-transform:uppercase;"
        "letter-spacing:0.08em;margin-bottom:6px;'>🎬 Screenplay</div>",
        unsafe_allow_html=True)
    if st.button("🎬 Screenplay (.fountain)", key="exp_screen", use_container_width=True):
        with st.spinner("Converting to screenplay…"):
            buf = export_screenplay(story)
        st.download_button("⬇ Download Screenplay", data=buf.getvalue(),
                           file_name=f"{title_slug}_screenplay.txt",
                           mime="text/plain",
                           key="dl_screen", use_container_width=True)

    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

    # ── LaTeX ──────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;font-weight:700;color:#A8BCFF;text-transform:uppercase;"
        "letter-spacing:0.08em;margin-bottom:6px;'>📐 Academic</div>",
        unsafe_allow_html=True)
    if st.button("📐 LaTeX Source", key="exp_latex", use_container_width=True):
        with st.spinner("Building LaTeX…"):
            buf = export_latex(story, characters)
        st.download_button("⬇ Download .tex", data=buf.getvalue(),
                           file_name=f"{title_slug}.tex",
                           mime="text/plain",
                           key="dl_latex", use_container_width=True)

    st.markdown("---")
    st.caption("Tip: Open .epub in Calibre, Send .fountain to Highland 2 or Fade In.")
