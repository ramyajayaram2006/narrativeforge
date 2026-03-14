"""
stats_report.py — NarrativeForge Story Statistics PDF Report
════════════════════════════════════════════════════════════

Generates a detailed analytics PDF for a story using reportlab.
Includes: summary card, word count progress, arc completion gauge,
character roster, scene breakdown, emotional arc chart,
top words, reading stats, and a full export of consistency issues.

INTEGRATION (workspace.py _sidebar_settings):
  Replace the current "PDF" download button with:

      try:
          from stats_report import generate_stats_pdf
          stats_pdf = generate_stats_pdf(story, characters, scenes)
          st.download_button(
              "📊 Stats Report PDF",
              data=stats_pdf,
              file_name=f"{safe_title}_Stats.pdf",
              mime="application/pdf",
              use_container_width=True,
              help="Detailed story analytics report")
      except ImportError:
          st.caption("Install reportlab for stats PDF")
"""

import io
import re
import math
import string
from collections import Counter
from datetime import datetime


def generate_stats_pdf(story: dict, characters: list, scenes: list) -> bytes:
    """
    Generate a statistics PDF report. Returns raw PDF bytes.
    Raises ImportError if reportlab is not installed.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     HRFlowable, Table, TableStyle, KeepTogether)
    from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
    from reportlab.graphics import renderPDF

    # ── Colour palette ─────────────────────────────────────────────────────────
    GOLD   = colors.HexColor("#C9A959")
    DARK   = colors.HexColor("#1A1E1A")
    CREAM  = colors.HexColor("#F5F2E9")
    MUTED  = colors.HexColor("#8B8F8B")
    RED    = colors.HexColor("#E57373")
    GREEN  = colors.HexColor("#81C784")
    BLUE   = colors.HexColor("#64B5F6")
    AMBER  = colors.HexColor("#FFD54F")
    BG     = colors.HexColor("#141814")

    # ── Styles ─────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    T_TITLE = S("T_Title", fontSize=26, leading=30, alignment=TA_LEFT,
                 textColor=GOLD, fontName="Times-Bold", spaceAfter=4)
    T_SUB   = S("T_Sub",   fontSize=11, leading=14, alignment=TA_LEFT,
                 textColor=MUTED, fontName="Times-Italic", spaceAfter=20)
    T_H2    = S("T_H2",    fontSize=13, leading=16, alignment=TA_LEFT,
                 textColor=DARK,  fontName="Helvetica-Bold",
                 spaceBefore=14, spaceAfter=6)
    T_LABEL = S("T_Label", fontSize=8,  leading=10, alignment=TA_LEFT,
                 textColor=MUTED, fontName="Helvetica", spaceAfter=2)
    T_VAL   = S("T_Val",   fontSize=11, leading=13, alignment=TA_LEFT,
                 textColor=DARK,  fontName="Helvetica-Bold", spaceAfter=6)
    T_BODY  = S("T_Body",  fontSize=10, leading=14, alignment=TA_JUSTIFY,
                 textColor=DARK,  fontName="Times-Roman", spaceAfter=4)
    T_TAG   = S("T_Tag",   fontSize=8,  leading=10, alignment=TA_CENTER,
                 textColor=colors.HexColor("#6B4F10"),
                 fontName="Helvetica-Bold", spaceAfter=0)
    T_FOOT  = S("T_Foot",  fontSize=8,  leading=10, alignment=TA_CENTER,
                 textColor=MUTED, fontName="Times-Italic")

    # ── Data computation ───────────────────────────────────────────────────────
    STOPWORDS = {
        "the","a","an","and","or","but","in","on","at","to","for","of","with",
        "by","from","as","is","was","are","were","be","been","being","have","has",
        "had","do","does","did","will","would","could","should","may","might",
        "i","you","he","she","it","we","they","me","him","her","us","them",
        "my","your","his","its","our","their","this","that","these","those",
        "which","who","what","when","where","how","not","no","so","if","then",
        "all","some","one","two","back","into","very","over","just","also","said",
    }
    POS_WORDS = {"love","hope","joy","light","smile","laugh","warm","bright","free","peace",
                 "brave","strong","alive","wonder","beautiful","safe","gentle","kind","win",
                 "happy","triumph","glory","dawn","rise","good","soft","dream","grow","heal"}
    NEG_WORDS = {"dark","death","fear","pain","lost","curse","shadow","blood","fall","broken",
                 "cold","hollow","dread","doom","die","hate","scream","trap","evil","void",
                 "despair","rage","cry","wept","shatter","betrayal","grief","wound","sink"}

    # Prose (canonical only)
    all_text = " ".join(
        m["content"] for m in story.get("messages", [])
        if m["role"] == "assistant"
        and not m["content"].startswith("◆")
        and not m["content"].startswith("[Revision")
    )
    words_raw = all_text.split()
    total_words = len(words_raw)
    clean_words = [w.lower().strip(string.punctuation) for w in words_raw]
    sentences = [s.strip() for s in re.split(r'[.!?]+', all_text) if len(s.strip()) > 4]
    freq = Counter(w for w in clean_words if w and w not in STOPWORDS and len(w) > 2)

    avg_sent = round(total_words / len(sentences), 1) if sentences else 0
    syllables = sum(max(1, len(re.findall(r'[aeiouAEIOU]', w))) for w in words_raw)
    fk_grade  = max(1, min(16, round(
        0.39 * (total_words / max(1, len(sentences))) +
        11.8 * (syllables / max(1, total_words)) - 15.59
    )))

    word_goal = story.get("word_goal", 0)
    pct_goal  = min(100, round(total_words / word_goal * 100)) if word_goal else None

    arc   = story.get("plot_arc", {})
    STAGES = ["beginning", "rising_action", "climax", "falling_action", "resolution"]
    STAGE_LABELS = ["Beginning", "Rising Action", "Climax", "Falling Action", "Resolution"]
    arc_done = sum(1 for k in STAGES if arc.get(k))

    # Emotional arc per AI block
    ai_msgs = [m for m in story.get("messages", [])
               if m["role"] == "assistant" and not m["content"].startswith("◆")
               and not m["content"].startswith("[Revision")]
    arc_scores = []
    for msg in ai_msgs:
        ws = re.sub(r'[^\w\s]', '', msg["content"].lower()).split()
        p  = sum(1 for w in ws if w in POS_WORDS)
        n  = sum(1 for w in ws if w in NEG_WORDS)
        tot = max(1, p + n)
        arc_scores.append((p - n) / tot)

    # ── Build PDF ──────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2.2*cm, rightMargin=2.2*cm,
                             topMargin=2.5*cm,  bottomMargin=2.5*cm,
                             title=f"{story['title']} — Statistics Report",
                             author="NarrativeForge")
    elems = []

    def HR(color=GOLD, thickness=0.8, spaceA=6, spaceB=10):
        return HRFlowable(width="100%", thickness=thickness,
                           color=color, spaceAfter=spaceA, spaceBefore=spaceB)

    # ── Cover ──────────────────────────────────────────────────────────────────
    elems.append(Spacer(1, 0.5*cm))
    elems.append(Paragraph(story["title"], T_TITLE))
    elems.append(Paragraph(
        f"Story Statistics Report  ·  Generated {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC",
        T_SUB))
    elems.append(HR())

    # ── Summary grid ──────────────────────────────────────────────────────────
    elems.append(Paragraph("Overview", T_H2))

    def stat_cell(label, value, color=DARK):
        return [
            Paragraph(label, T_LABEL),
            Paragraph(str(value), ParagraphStyle("v", fontSize=14, leading=16,
                       textColor=color, fontName="Helvetica-Bold")),
        ]

    reading_mins = max(1, round(total_words / 200))
    summary_data = [
        ["Genre", story.get("genre","—"), "Tone",  story.get("tone","—")],
        ["Total Words", f"{total_words:,}", "Messages", str(len(story.get("messages",[])))],
        ["Sentences",  str(len(sentences)), "Avg Sentence", f"{avg_sent} words"],
        ["FK Grade",   f"Grade {fk_grade}", "Read Time", f"~{reading_mins} min"],
        ["Characters", str(len(characters)), "Scenes", str(len(scenes))],
    ]
    summary_table = Table(summary_data, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME",   (0,0),(-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0),(-1,-1), 9),
        ("TEXTCOLOR",  (0,0),(-1,-1), MUTED),
        ("FONTNAME",   (1,0),(1,-1),  "Helvetica-Bold"),
        ("FONTNAME",   (3,0),(3,-1),  "Helvetica-Bold"),
        ("TEXTCOLOR",  (1,0),(1,-1),  DARK),
        ("TEXTCOLOR",  (3,0),(3,-1),  DARK),
        ("FONTSIZE",   (1,0),(1,-1),  10),
        ("FONTSIZE",   (3,0),(3,-1),  10),
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [colors.HexColor("#FAFAF8"), colors.HexColor("#F4F1EA")]),
        ("TOPPADDING",  (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    elems.append(summary_table)
    elems.append(Spacer(1, 0.4*cm))

    # ── Word goal progress bar ─────────────────────────────────────────────────
    if word_goal and pct_goal is not None:
        elems.append(HR(thickness=0.3, color=colors.HexColor("#E0D8C8")))
        elems.append(Paragraph("Word Goal Progress", T_H2))

        bar_w     = PAGE_W - 4.4*cm
        filled_w  = bar_w * (pct_goal / 100)
        bar_h     = 14

        d = Drawing(bar_w, bar_h + 20)
        # Background track
        d.add(Rect(0, 10, bar_w, bar_h, fillColor=colors.HexColor("#E8E0CE"),
                    strokeColor=None, rx=6, ry=6))
        # Filled portion
        fill_color = GREEN if pct_goal >= 100 else GOLD
        d.add(Rect(0, 10, min(filled_w, bar_w), bar_h,
                    fillColor=fill_color, strokeColor=None, rx=6, ry=6))
        # Labels
        d.add(String(0, 2, f"{total_words:,} words",
                      fontName="Helvetica", fontSize=8, fillColor=MUTED))
        d.add(String(bar_w, 2, f"Goal: {word_goal:,}",
                      fontName="Helvetica-Bold", fontSize=8,
                      fillColor=DARK, textAnchor="end"))
        d.add(String(bar_w / 2, 14, f"{pct_goal}%",
                      fontName="Helvetica-Bold", fontSize=8,
                      fillColor=DARK, textAnchor="middle"))
        elems.append(d)
        elems.append(Spacer(1, 0.3*cm))

    # ── Plot arc ───────────────────────────────────────────────────────────────
    elems.append(HR(thickness=0.3, color=colors.HexColor("#E0D8C8")))
    elems.append(Paragraph("Plot Arc Completion", T_H2))

    arc_data   = [STAGE_LABELS]
    arc_status = ["✓ Done" if arc.get(k) else "○ Pending" for k in STAGES]
    arc_table  = Table([arc_data[0], arc_status],
                        colWidths=[(PAGE_W - 4.4*cm) / 5] * 5)
    arc_table.setStyle(TableStyle([
        ("FONTNAME",  (0,0),(-1,0),   "Helvetica-Bold"),
        ("FONTNAME",  (0,1),(-1,1),   "Helvetica"),
        ("FONTSIZE",  (0,0),(-1,-1),  8),
        ("ALIGN",     (0,0),(-1,-1),  "CENTER"),
        ("TEXTCOLOR", (0,0),(-1,0),   MUTED),
        ("ROWBACKGROUNDS", (0,0),(-1,-1),
            [colors.HexColor("#F4F1EA"), colors.HexColor("#FAFAF8")]),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ]))
    # Colour done stages green
    for col_idx, key in enumerate(STAGES):
        if arc.get(key):
            arc_table.setStyle(TableStyle([
                ("TEXTCOLOR", (col_idx,1),(col_idx,1), GREEN),
                ("FONTNAME",  (col_idx,1),(col_idx,1), "Helvetica-Bold"),
            ]))
    elems.append(arc_table)
    elems.append(Spacer(1, 0.4*cm))

    # ── Emotional arc chart ────────────────────────────────────────────────────
    if arc_scores:
        elems.append(HR(thickness=0.3, color=colors.HexColor("#E0D8C8")))
        elems.append(Paragraph("Emotional Arc", T_H2))
        elems.append(Paragraph(
            "Each bar represents one AI-generated prose block. "
            "Gold = hopeful, Red = tense, Green = neutral.",
            T_LABEL))

        chart_w = PAGE_W - 4.4*cm
        chart_h = 60
        n       = len(arc_scores)
        bar_gap = 2
        bar_w_each = max(4, (chart_w - bar_gap * n) / n)

        d = Drawing(chart_w, chart_h + 20)
        # Midline
        d.add(Line(0, chart_h/2 + 10, chart_w, chart_h/2 + 10,
                    strokeColor=colors.HexColor("#D0C8B8"), strokeWidth=0.5))

        for i, score in enumerate(arc_scores):
            x     = i * (bar_w_each + bar_gap)
            mid_y = chart_h / 2 + 10
            h     = abs(score) * (chart_h / 2) * 0.9
            y     = mid_y if score >= 0 else mid_y - h

            if   score > 0.2:  color_ = GOLD
            elif score < -0.2: color_ = RED
            else:               color_ = GREEN

            d.add(Rect(x, y, bar_w_each, h,
                        fillColor=color_, strokeColor=None, rx=1, ry=1))

        # Axis labels
        d.add(String(0, chart_h + 14, "Hopeful +",
                      fontName="Helvetica", fontSize=7, fillColor=GOLD))
        d.add(String(0, 0, "Tense −",
                      fontName="Helvetica", fontSize=7, fillColor=RED))
        d.add(String(chart_w, 0, f"{n} blocks",
                      fontName="Helvetica", fontSize=7,
                      fillColor=MUTED, textAnchor="end"))
        elems.append(d)
        elems.append(Spacer(1, 0.4*cm))

    # ── Word frequency ─────────────────────────────────────────────────────────
    if freq:
        elems.append(HR(thickness=0.3, color=colors.HexColor("#E0D8C8")))
        elems.append(Paragraph("Top Words (excluding stopwords)", T_H2))

        top10   = freq.most_common(10)
        max_c   = top10[0][1] if top10 else 1
        chart_w = PAGE_W - 4.4*cm

        wf_data  = []
        wf_data.append(["Word", "Count", "Density", "Frequency Bar"])
        for word, count in top10:
            density = f"{count / max(total_words,1) * 100:.2f}%"
            bar_pct = int(count / max_c * 100)
            wf_data.append([word, str(count), density,
                             "█" * (bar_pct // 5) + "░" * (20 - bar_pct // 5)])

        wf_table = Table(wf_data, colWidths=[3*cm, 2*cm, 2.5*cm,
                                              chart_w - 7.5*cm])
        wf_table.setStyle(TableStyle([
            ("FONTNAME",     (0,0),(-1,0),   "Helvetica-Bold"),
            ("FONTNAME",     (0,1),(-1,-1),  "Helvetica"),
            ("FONTSIZE",     (0,0),(-1,-1),  8),
            ("TEXTCOLOR",    (0,0),(-1,0),   MUTED),
            ("TEXTCOLOR",    (0,1),(-1,-1),  DARK),
            ("FONTNAME",     (3,1),(3,-1),   "Courier"),
            ("TEXTCOLOR",    (3,1),(3,-1),   GOLD),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),
                [colors.HexColor("#FAFAF8"), colors.HexColor("#F4F1EA")]),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("LINEBELOW",    (0,0),(-1,0),   0.5, colors.HexColor("#D0C8B8")),
        ]))
        elems.append(wf_table)
        elems.append(Spacer(1, 0.4*cm))

    # ── Character roster ───────────────────────────────────────────────────────
    if characters:
        elems.append(HR(thickness=0.3, color=colors.HexColor("#E0D8C8")))
        elems.append(Paragraph("Characters", T_H2))

        char_data = [["Name", "Role", "Speaking Style", "Mentions"]]
        for c in characters:
            mention_count = all_text.lower().count(c["name"].lower())
            char_data.append([
                c["name"],
                c.get("role","—"),
                (c.get("speaking_style","—") or "—")[:50],
                str(mention_count),
            ])

        char_table = Table(char_data, colWidths=[3.5*cm, 2.8*cm, 8*cm, 2*cm])
        char_table.setStyle(TableStyle([
            ("FONTNAME",     (0,0),(-1,0),   "Helvetica-Bold"),
            ("FONTNAME",     (0,1),(-1,-1),  "Helvetica"),
            ("FONTSIZE",     (0,0),(-1,-1),  8),
            ("TEXTCOLOR",    (0,0),(-1,0),   MUTED),
            ("TEXTCOLOR",    (0,1),(0,-1),   DARK),
            ("FONTNAME",     (0,1),(0,-1),   "Helvetica-Bold"),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),
                [colors.HexColor("#FAFAF8"), colors.HexColor("#F4F1EA")]),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("LINEBELOW",    (0,0),(-1,0),   0.5, colors.HexColor("#D0C8B8")),
        ]))
        elems.append(char_table)
        elems.append(Spacer(1, 0.4*cm))

    # ── Scenes ─────────────────────────────────────────────────────────────────
    if scenes:
        elems.append(HR(thickness=0.3, color=colors.HexColor("#E0D8C8")))
        elems.append(Paragraph("Scenes", T_H2))

        scene_data = [["#", "Title", "Location", "Characters"]]
        for sc in scenes:
            scene_data.append([
                str(sc["order"]),
                sc["title"] or "—",
                (sc.get("location","—") or "—")[:30],
                ", ".join(sc.get("characters",[])[:3]) or "—",
            ])

        sc_table = Table(scene_data, colWidths=[1*cm, 5*cm, 5*cm, 5.3*cm])
        sc_table.setStyle(TableStyle([
            ("FONTNAME",     (0,0),(-1,0),   "Helvetica-Bold"),
            ("FONTNAME",     (0,1),(-1,-1),  "Helvetica"),
            ("FONTSIZE",     (0,0),(-1,-1),  8),
            ("TEXTCOLOR",    (0,0),(-1,0),   MUTED),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),
                [colors.HexColor("#FAFAF8"), colors.HexColor("#F4F1EA")]),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("LINEBELOW",    (0,0),(-1,0),   0.5, colors.HexColor("#D0C8B8")),
        ]))
        elems.append(sc_table)
        elems.append(Spacer(1, 0.4*cm))

    # ── Footer ─────────────────────────────────────────────────────────────────
    elems.append(HR(color=GOLD, thickness=0.6))
    elems.append(Paragraph(
        f"NarrativeForge  ·  {story['title']}  ·  Stats Report  ·  {datetime.utcnow().strftime('%d %b %Y')}",
        T_FOOT))

    doc.build(elems)
    return buf.getvalue()
