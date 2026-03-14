"""
analytics.py — Writing Tracker & Deep Story Analytics for NarrativeForge
Daily word tracking, calendar heatmap, streaks, milestones,
character appearance counts, readability over time, pacing charts.
"""

import re
import json
import time
import html as _html
import streamlit as st
from datetime import datetime, timedelta, date
from collections import Counter, defaultdict

# ── Writing session tracking (session state based) ────────────────────────────
def record_session_words(story_id, word_delta):
    """Record words written in current session."""
    if word_delta <= 0:
        return
    today = date.today().isoformat()
    key   = "_writing_log"
    log   = st.session_state.get(key, {})
    day   = log.get(today, {})
    day[story_id] = day.get(story_id, 0) + word_delta
    log[today]    = day
    st.session_state[key] = log


def get_writing_log():
    return st.session_state.get("_writing_log", {})


def _day_total(log, day_str):
    return sum(log.get(day_str, {}).values())


def _streak_count(log):
    """Count current consecutive writing days."""
    today = date.today()
    streak = 0
    for i in range(365):
        d = (today - timedelta(days=i)).isoformat()
        if _day_total(log, d) > 0:
            streak += 1
        elif streak > 0:
            break
    return streak


def _longest_streak(log):
    if not log:
        return 0
    all_days = sorted(log.keys())
    best = cur = 0
    prev = None
    for day_str in all_days:
        if _day_total(log, day_str) == 0:
            cur = 0
            prev = None
            continue
        if prev is None:
            cur = 1
        else:
            prev_date = datetime.fromisoformat(prev).date()
            this_date = datetime.fromisoformat(day_str).date()
            if (this_date - prev_date).days == 1:
                cur += 1
            else:
                cur = 1
        best = max(best, cur)
        prev = day_str
    return best


# ── Calendar Heatmap ──────────────────────────────────────────────────────────
def show_calendar_heatmap(log, weeks=12):
    """Render a GitHub-style contribution calendar."""
    today = date.today()
    start = today - timedelta(weeks=weeks)

    # Build day grid
    days = []
    d = start
    while d <= today:
        wc = _day_total(log, d.isoformat())
        days.append((d, wc))
        d += timedelta(days=1)

    if not days:
        return

    max_wc = max((wc for _, wc in days), default=1) or 1

    def _intensity(wc):
        if wc == 0:  return "#1A1C26"
        if wc < 100: return "#1A3A2A"
        if wc < 300: return "#1E5C3A"
        if wc < 600: return "#26894E"
        return "#4ADE80"

    # Build week columns
    # Start from Monday of the start week
    weekday_start = start.weekday()  # 0=Mon
    leading = weekday_start
    grid_days = [None] * leading + days

    weeks_cols = []
    for i in range(0, len(grid_days), 7):
        weeks_cols.append(grid_days[i:i+7])

    # Build SVG heatmap
    cell = 14
    gap  = 3
    label_h = 18

    svg_w = len(weeks_cols) * (cell + gap) + 30
    svg_h = 7 * (cell + gap) + label_h + 8

    month_labels = {}
    for i, col in enumerate(weeks_cols):
        for cell_day in col:
            if cell_day and cell_day[0].day <= 7:
                x = i * (cell + gap) + 30
                month_labels[x] = cell_day[0].strftime("%b")
                break

    cells_svg = []
    for col_i, col in enumerate(weeks_cols):
        for row_i, item in enumerate(col):
            x = col_i * (cell + gap) + 30
            y = row_i * (cell + gap) + label_h
            if item is None:
                continue
            d_obj, wc = item
            color = _intensity(wc)
            tip = f"{d_obj.strftime('%b %d')}: {wc:,} words"
            cells_svg.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'rx="2" fill="{color}"><title>{tip}</title></rect>')

    # Day labels (Mon/Wed/Fri)
    day_labels = {0: "Mon", 2: "Wed", 4: "Fri"}
    for row_i, dlabel in day_labels.items():
        y = row_i * (cell + gap) + label_h + cell // 2 + 4
        cells_svg.append(
            f'<text x="0" y="{y}" font-size="8" fill="#6B7080" '
            f'font-family="monospace">{dlabel}</text>')

    # Month labels
    for x, mlabel in month_labels.items():
        cells_svg.append(
            f'<text x="{x}" y="{label_h - 4}" font-size="9" fill="#6B7080" '
            f'font-family="monospace">{mlabel}</text>')

    svg = (f'<svg width="{svg_w}" height="{svg_h}" '
           f'xmlns="http://www.w3.org/2000/svg">'
           + "".join(cells_svg) + "</svg>")

    st.markdown(svg, unsafe_allow_html=True)


# ── Milestones ────────────────────────────────────────────────────────────────
MILESTONES = [
    (1_000,   "📝 First 1K",      "1,000 words written!"),
    (5_000,   "✍️ Short Story",    "5,000 words — short story length!"),
    (10_000,  "🏅 Novelette",     "10,000 words — novelette territory!"),
    (25_000,  "📖 Quarter Novel", "25,000 words — a quarter of a novel!"),
    (50_000,  "🏆 NaNoWriMo",     "50,000 words — NaNoWriMo champion!"),
    (80_000,  "📚 Full Novel",    "80,000 words — full novel length!"),
    (100_000, "🌟 Epic Writer",   "100,000 words — epic achievement!"),
]

def show_milestones(total_words):
    earned = [(wc, badge, desc) for wc, badge, desc in MILESTONES if total_words >= wc]
    next_m = next(((wc, badge, desc) for wc, badge, desc in MILESTONES if total_words < wc), None)

    if earned:
        st.markdown("**🏅 Milestones Earned**")
        for wc, badge, desc in earned[-3:]:  # show last 3
            st.markdown(
                f"<div style='background:rgba(77,107,254,0.08);border:1px solid rgba(77,107,254,0.2);"
                f"border-radius:10px;padding:8px 14px;margin-bottom:6px;font-size:0.82rem;'>"
                f"<b style='font-size:1.1rem;'>{badge}</b>&nbsp; {desc}</div>",
                unsafe_allow_html=True)

    if next_m:
        wc, badge, desc = next_m
        remaining = wc - total_words
        pct = total_words / wc
        st.markdown(
            f"<div style='margin-top:8px;'><div style='font-size:0.72rem;color:#6B7080;'>"
            f"Next milestone: <b style='color:#A8BCFF;'>{badge}</b> — {remaining:,} words to go</div>"
            f"<div style='background:rgba(77,107,254,0.12);border-radius:4px;height:6px;margin-top:4px;'>"
            f"<div style='background:#4D6BFE;width:{pct*100:.1f}%;height:6px;border-radius:4px;'></div>"
            f"</div></div>",
            unsafe_allow_html=True)


# ── Character Appearance Analytics ───────────────────────────────────────────
def character_appearance_chart(story, characters):
    """Count how many AI messages each character name appears in."""
    if not characters:
        return

    ai_msgs = [m["content"] for m in story.get("messages", [])
               if m["role"] == "assistant"]

    counts = {}
    for c in characters:
        name = c["name"]
        count = sum(1 for msg in ai_msgs if name.lower() in msg.lower())
        if count > 0:
            counts[name] = count

    if not counts:
        st.caption("No character appearances found in prose.")
        return

    sorted_counts = sorted(counts.items(), key=lambda x: -x[1])
    max_count = sorted_counts[0][1] or 1

    st.markdown("**👤 Character Screen Time**")
    html_parts = ["<div style='margin-top:4px;'>"]
    colors = ["#4D6BFE", "#A8BCFF", "#7B96FF", "#6B7080", "#4ADE80"]
    for i, (name, count) in enumerate(sorted_counts[:8]):
        pct = count / max_count * 100
        color = colors[i % len(colors)]
        html_parts.append(
            f"<div style='margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;"
            f"margin-bottom:3px;'><span style='color:var(--text-primary);font-weight:600;'>"
            f"{_html.escape(name)}</span><span style='color:#6B7080;'>{count} scenes</span></div>"
            f"<div style='background:rgba(77,107,254,0.12);border-radius:4px;height:8px;'>"
            f"<div style='background:{color};width:{pct:.0f}%;height:8px;border-radius:4px;'>"
            f"</div></div></div>")
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


# ── Readability Over Time ─────────────────────────────────────────────────────
def readability_over_time(story):
    """Show how reading level changes through the story."""
    ai_msgs = [m["content"] for m in story.get("messages", [])
               if m["role"] == "assistant"]
    if len(ai_msgs) < 3:
        st.caption("Need at least 3 AI messages for trend analysis.")
        return

    def _ease(text):
        words = text.split()
        sentences = max(1, text.count(".") + text.count("!") + text.count("?"))
        syllables = sum(_count_syllables(w) for w in words)
        if not words:
            return 50
        return max(0, min(100,
            206.835 - 1.015 * (len(words) / sentences)
            - 84.6 * (syllables / len(words))))

    def _count_syllables(word):
        word = word.lower().strip(".,!?;:")
        if len(word) <= 3:
            return 1
        count = len(re.findall(r'[aeiou]+', word))
        if word.endswith('e') and count > 1:
            count -= 1
        return max(1, count)

    scores = [_ease(m) for m in ai_msgs]
    labels = [f"#{i+1}" for i in range(len(scores))]

    # SVG spark line
    w, h = 300, 60
    pad  = 10
    if len(scores) < 2:
        return
    min_s, max_s = min(scores), max(scores)
    rng = max_s - min_s or 1

    pts = []
    for i, s in enumerate(scores):
        x = pad + i * (w - 2*pad) / (len(scores) - 1)
        y = h - pad - (s - min_s) / rng * (h - 2*pad)
        pts.append((x, y))

    path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#4D6BFE"/>'
        for x, y in pts)

    svg = (
        f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{path}" stroke="#4D6BFE" stroke-width="2" fill="none" opacity="0.8"/>'
        f'{dots}</svg>')

    avg_ease = sum(scores) / len(scores)
    trend    = "📈 Getting more complex" if scores[-1] < scores[0] - 5 else (
               "📉 Getting more readable" if scores[-1] > scores[0] + 5 else "➡️ Consistent")

    st.markdown(
        f"<div style='font-size:0.72rem;color:#6B7080;margin-bottom:4px;'>"
        f"Flesch Reading Ease over {len(scores)} passages · Avg: {avg_ease:.0f} · {trend}</div>",
        unsafe_allow_html=True)
    st.markdown(svg, unsafe_allow_html=True)


# ── Pacing Analyser ───────────────────────────────────────────────────────────
def pacing_analysis(story):
    """Classify each AI message as fast/medium/slow paced based on sentence length."""
    ai_msgs = [m["content"] for m in story.get("messages", [])
               if m["role"] == "assistant"]
    if not ai_msgs:
        return

    def _avg_sentence_len(text):
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if not sentences:
            return 0
        return sum(len(s.split()) for s in sentences) / len(sentences)

    paces = []
    for msg in ai_msgs:
        asl = _avg_sentence_len(msg)
        if asl < 12:
            pace, color, label = "fast",   "#f87171", "⚡ Fast"
        elif asl < 22:
            pace, color, label = "medium", "#fbbf24", "⚖ Medium"
        else:
            pace, color, label = "slow",   "#4D6BFE", "🌊 Slow"
        paces.append((pace, color, label, asl))

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:8px;'>"
        "Pacing is measured by average sentence length per passage. "
        "Vary pacing for rhythm and impact.</div>",
        unsafe_allow_html=True)

    html_parts = ["<div style='display:flex;gap:3px;flex-wrap:wrap;margin-bottom:8px;'>"]
    for i, (pace, color, label, asl) in enumerate(paces):
        html_parts.append(
            f"<div title='Passage {i+1}: {label} ({asl:.1f} words/sentence)' "
            f"style='width:24px;height:24px;border-radius:4px;background:{color};"
            f"opacity:0.85;cursor:pointer;'></div>")
    html_parts.append("</div>")

    fast_n   = sum(1 for p, _, _, _ in paces if p == "fast")
    med_n    = sum(1 for p, _, _, _ in paces if p == "medium")
    slow_n   = sum(1 for p, _, _, _ in paces if p == "slow")
    html_parts.append(
        f"<div style='font-size:0.75rem;color:#6B7080;display:flex;gap:14px;'>"
        f"<span><b style='color:#f87171;'>⚡</b> {fast_n} fast</span>"
        f"<span><b style='color:#fbbf24;'>⚖</b> {med_n} medium</span>"
        f"<span><b style='color:#4D6BFE;'>🌊</b> {slow_n} slow</span></div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)


# ── Subplot Tracker ───────────────────────────────────────────────────────────
def show_subplot_tracker(story):
    """Let users define subplots and track which messages advance them."""
    story_id = story["id"]
    sp_key   = f"_subplots_{story_id}"
    subplots = st.session_state.get(sp_key, [])

    st.markdown(
        "<div style='font-size:0.75rem;color:#6B7080;margin-bottom:8px;'>"
        "Track parallel storylines alongside your main plot.</div>",
        unsafe_allow_html=True)

    with st.expander("➕ Add Subplot", expanded=not subplots):
        sp_title = st.text_input("Subplot title", key="sp_new_title",
                                  placeholder="e.g. Elena's romance subplot", max_chars=80)
        sp_status = st.selectbox("Status", ["Active", "Resolved", "Abandoned"],
                                  key="sp_new_status")
        sp_notes  = st.text_area("Notes", key="sp_new_notes", height=60, max_chars=300)
        if st.button("Add Subplot", key="sp_add_btn"):
            if sp_title:
                subplots.append({
                    "id":     len(subplots),
                    "title":  sp_title,
                    "status": sp_status,
                    "notes":  sp_notes,
                })
                st.session_state[sp_key] = subplots
                st.rerun()

    status_colors = {
        "Active":    "#4D6BFE",
        "Resolved":  "#4ADE80",
        "Abandoned": "#f87171",
    }

    for i, sp in enumerate(subplots):
        color = status_colors.get(sp["status"], "#6B7080")
        with st.container():
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                st.markdown(
                    f"<div style='font-size:0.84rem;font-weight:600;"
                    f"color:var(--text-primary);'>{_html.escape(sp['title'])}</div>"
                    f"<div style='font-size:0.72rem;color:#6B7080;'>{sp.get('notes','')[:60]}</div>",
                    unsafe_allow_html=True)
            with c2:
                new_status = st.selectbox(
                    "Status", ["Active", "Resolved", "Abandoned"],
                    index=["Active", "Resolved", "Abandoned"].index(sp["status"]),
                    key=f"sp_status_{i}", label_visibility="collapsed")
                if new_status != sp["status"]:
                    subplots[i]["status"] = new_status
                    st.session_state[sp_key] = subplots
                    st.rerun()
            with c3:
                if st.button("🗑", key=f"sp_del_{i}"):
                    subplots.pop(i)
                    st.session_state[sp_key] = subplots
                    st.rerun()
            st.markdown(
                f"<div style='border-left:3px solid {color};height:2px;margin-bottom:8px;'></div>",
                unsafe_allow_html=True)


# ── Full Analytics Dashboard ──────────────────────────────────────────────────
def show_analytics_dashboard(story, characters):
    """Complete analytics dashboard — all metrics in one place."""
    log        = get_writing_log()
    total_wc   = sum(len(m["content"].split()) for m in story.get("messages", [])
                     if m["role"] == "assistant")
    streak     = _streak_count(log)
    longest    = _longest_streak(log)
    today_wc   = _day_total(log, date.today().isoformat())
    total_days = sum(1 for d in log if _day_total(log, d) > 0)

    # ── Stats row ─────────────────────────────────────────────────────────────
    a1, a2, a3, a4 = st.columns(4)
    for col, icon, label, val in [
        (a1, "🔥", "Current Streak", f"{streak} days"),
        (a2, "🏆", "Longest Streak",  f"{longest} days"),
        (a3, "📅", "Days Written",    f"{total_days} days"),
        (a4, "📝", "Words Today",     f"{today_wc:,}"),
    ]:
        with col:
            st.markdown(
                f"<div style='background:var(--bg-card);border:1px solid rgba(77,107,254,0.15);"
                f"border-radius:10px;padding:12px;text-align:center;'>"
                f"<div style='font-size:1.4rem;'>{icon}</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:var(--primary);'>{val}</div>"
                f"<div style='font-size:0.68rem;color:#6B7080;'>{label}</div></div>",
                unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── Calendar + Milestones ─────────────────────────────────────────────────
    cal_col, ms_col = st.columns([3, 2])
    with cal_col:
        st.markdown("**📅 Writing Calendar (last 12 weeks)**")
        show_calendar_heatmap(log)
        st.markdown(
            "<div style='font-size:0.66rem;color:#6B7080;margin-top:4px;'>"
            "🟩 Darker = more words written that day</div>", unsafe_allow_html=True)
    with ms_col:
        show_milestones(total_wc)

    st.markdown("---")

    # ── Character + Pacing ────────────────────────────────────────────────────
    char_col, pace_col = st.columns([1, 1])
    with char_col:
        character_appearance_chart(story, characters)
    with pace_col:
        st.markdown("**⚡ Pacing Map**")
        pacing_analysis(story)

    st.markdown("---")

    # ── Readability trend ─────────────────────────────────────────────────────
    st.markdown("**📈 Readability Trend**")
    readability_over_time(story)

    st.markdown("---")

    # ── Subplot tracker ───────────────────────────────────────────────────────
    st.markdown("**🕸 Subplot Tracker**")
    show_subplot_tracker(story)



# ═══════════════════════════════════════════════════════════════════════════
# ENHANCED ANALYTICS — Deeper Stats, Charts, Writing DNA
# ═══════════════════════════════════════════════════════════════════════════

def _sparkline_svg(values, color="#4D6BFE", width=200, height=40):
    """Render a tiny SVG sparkline."""
    if len(values) < 2:
        return ""
    pad = 4
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    pts = []
    for i, v in enumerate(values):
        x = pad + i * (width - 2*pad) / (len(values)-1)
        y = height - pad - (v - mn) / rng * (height - 2*pad)
        pts.append((x, y))
    path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    last_x, last_y = pts[-1]
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.0"/>'
        f'</linearGradient></defs>'
        f'<path d="{path} L {pts[-1][0]:.1f},{height} L {pts[0][0]:.1f},{height} Z"'
        f' fill="url(#sg)"/>'
        f'<path d="{path}" stroke="{color}" stroke-width="2" fill="none"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3" fill="{color}"/>'
        f'</svg>'
    )


def show_writing_dna(story):
    """Detailed breakdown of writing style metrics."""
    msgs = [m["content"] for m in story.get("messages", [])
            if m.get("role") == "assistant"]
    if not msgs:
        st.caption("No story content yet.")
        return

    text = " ".join(msgs)
    words = text.split()
    if not words:
        return

    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 4]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Core metrics
    total_words  = len(words)
    unique_words = len(set(w.lower().strip(".,!?;:\"'") for w in words))
    vocab_rich   = round(unique_words / max(total_words, 1) * 100, 1)
    avg_word_len = round(sum(len(w.strip(".,!?;:")) for w in words) / max(total_words, 1), 1)
    avg_sent_len = round(sum(len(s.split()) for s in sentences) / max(len(sentences), 1), 1)
    avg_para_len = round(total_words / max(len(paragraphs), 1))

    # Dialogue ratio
    dialogue_words = len(re.findall(r'["""](.*?)["""]', text))
    dialogue_pct   = round(dialogue_words / max(total_words, 1) * 100, 1)

    # Exclamation / question density
    exclamations = text.count("!")
    questions    = text.count("?")
    punct_density = round((exclamations + questions) / max(len(sentences), 1) * 100, 1)

    # Adverb count (words ending in -ly)
    adverbs = [w for w in words if w.lower().endswith("ly") and len(w) > 3]
    adverb_pct = round(len(adverbs) / max(total_words, 1) * 100, 1)

    # Passive voice indicators
    passive_markers = re.findall(
        r'\b(was|were|is|are|been|being)\s+(\w+ed|\w+en)\b', text, re.IGNORECASE)
    passive_density = round(len(passive_markers) / max(len(sentences), 1) * 100, 1)

    # Render DNA cards
    metrics = [
        ("Total Words",    f"{total_words:,}",  "📝", "#4D6BFE",  ""),
        ("Unique Words",   f"{unique_words:,}",  "🧠", "#a78bfa",  ""),
        ("Vocab Richness", f"{vocab_rich}%",     "💎", "#fbbf24" if vocab_rich < 40 else "#34d399",
         "< 40% = repetitive" if vocab_rich < 40 else ""),
        ("Avg Word Len",   f"{avg_word_len} ch", "🔤", "#60a5fa",  "> 5.5 = complex" if avg_word_len > 5.5 else ""),
        ("Avg Sent Len",   f"{avg_sent_len} w",  "📏", "#34d399" if 12 <= avg_sent_len <= 22 else "#fbbf24",
         "ideal: 12-22w"),
        ("Avg Para Len",   f"{avg_para_len} w",  "📄", "#6B7080",  ""),
        ("Dialogue",       f"{dialogue_pct}%",   "💬", "#f472b6",
         "low dialogue" if dialogue_pct < 10 else ""),
        ("Adverbs",        f"{adverb_pct}%",     "⚠️", "#f87171" if adverb_pct > 2 else "#34d399",
         "cut -ly words" if adverb_pct > 2 else "✓ good"),
        ("Passive Voice",  f"{passive_density}%","🔄", "#f87171" if passive_density > 15 else "#34d399",
         "too much" if passive_density > 15 else "✓ good"),
        ("Punctuation",    f"{punct_density}%",  "❕", "#6B7080",  ""),
    ]

    # Render 5-col grid
    for row_start in range(0, len(metrics), 5):
        row = metrics[row_start:row_start+5]
        cols = st.columns(len(row))
        for i, (label, val, icon, color, hint) in enumerate(row):
            with cols[i]:
                st.markdown(
                    f"<div style='background:var(--bg-card);border:1px solid rgba(77,107,254,0.12);"
                    f"border-radius:8px;padding:10px;text-align:center;margin-bottom:8px;'>"
                    f"<div style='font-size:1.1rem;'>{icon}</div>"
                    f"<div style='font-size:1.0rem;font-weight:800;color:{color};'>{val}</div>"
                    f"<div style='font-size:0.60rem;color:#6B7080;margin-top:1px;'>{label}</div>"
                    f"{'<div style=\'font-size:0.58rem;color:' + color + ';margin-top:2px;\'>' + hint + '</div>' if hint else ''}"
                    f"</div>",
                    unsafe_allow_html=True)


def show_sentence_length_chart(story):
    """Bar chart of sentence lengths across the whole story."""
    msgs = [m["content"] for m in story.get("messages", [])
            if m.get("role") == "assistant"]
    if not msgs:
        return

    text = " ".join(msgs)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 4]
    if len(sentences) < 5:
        return

    lengths = [len(s.split()) for s in sentences]

    # Bucket into ranges
    buckets = {"1-5": 0, "6-10": 0, "11-15": 0, "16-20": 0, "21-30": 0, "31+": 0}
    for l in lengths:
        if l <= 5:    buckets["1-5"] += 1
        elif l <= 10: buckets["6-10"] += 1
        elif l <= 15: buckets["11-15"] += 1
        elif l <= 20: buckets["16-20"] += 1
        elif l <= 30: buckets["21-30"] += 1
        else:         buckets["31+"] += 1

    total = len(lengths)
    max_count = max(buckets.values()) or 1

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>"
        "📊 Sentence Length Distribution</div>",
        unsafe_allow_html=True)

    for label, count in buckets.items():
        pct   = round(count / total * 100, 1)
        bar_w = int(count / max_count * 100)
        # Ideal zone = 11-20 words
        color = "#34d399" if label in ("11-15", "16-20") else (
                "#f87171" if label == "31+" else "#4D6BFE")
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
            f"<div style='width:36px;font-size:0.68rem;color:#6B7080;'>{label}w</div>"
            f"<div style='flex:1;background:rgba(77,107,254,0.08);border-radius:3px;height:14px;'>"
            f"<div style='width:{bar_w}%;background:{color};height:14px;border-radius:3px;'></div></div>"
            f"<div style='width:50px;font-size:0.68rem;color:#6B7080;text-align:right;'>"
            f"{count} ({pct}%)</div></div>",
            unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.62rem;color:#6B7080;margin-top:4px;'>"
        "🟢 Ideal zone: 11–20 words per sentence</div>",
        unsafe_allow_html=True)


def show_word_frequency_chart(story, top_n=20):
    """Visual word cloud style frequency chart."""
    from collections import Counter
    msgs = [m["content"] for m in story.get("messages", [])
            if m.get("role") == "assistant"]
    if not msgs:
        return

    _STOP = {
        "the","a","an","and","or","but","in","on","at","to","for","of","with","by",
        "from","as","is","was","are","were","be","been","have","has","had","do","will",
        "would","could","should","i","you","he","she","it","we","they","me","him","her",
        "us","them","my","your","his","its","our","their","this","that","these","those",
        "said","just","also","up","out","back","more","so","not","no","very","all","one",
        "then","than","into","over","there","here","some","what","when","where","how","if",
        "they","their","which","who","about","like","her","his","him","her","been","also",
        "can","an","two","three","its","it","new","now","only","even","still","much","well",
    }

    text  = " ".join(msgs).lower()
    words = re.findall(r'[a-z]{4,}', text)
    freq  = Counter(w for w in words if w not in _STOP)
    top   = freq.most_common(top_n)

    if not top:
        return

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>"
        f"🔤 Top {top_n} Words</div>",
        unsafe_allow_html=True)

    max_count = top[0][1]
    COLORS = ["#4D6BFE","#a78bfa","#60a5fa","#34d399","#fbbf24",
              "#f472b6","#fb923c","#2dd4bf","#818cf8","#f87171"]

    for i, (word, count) in enumerate(top):
        pct   = int(count / max_count * 100)
        color = COLORS[i % len(COLORS)]
        over  = count / max(len(words), 1) * 100 > 2.5
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
            f"<div style='width:80px;font-size:0.76rem;color:{color};font-weight:600;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{word}</div>"
            f"<div style='flex:1;background:rgba(77,107,254,0.07);border-radius:3px;height:10px;'>"
            f"<div style='width:{pct}%;background:{color};height:10px;border-radius:3px;"
            f"opacity:0.85;'></div></div>"
            f"<div style='width:28px;font-size:0.68rem;color:#6B7080;text-align:right;'>"
            f"{count}</div>"
            f"{'<div style=\'font-size:0.60rem;color:#f87171;margin-left:2px;\'>⚠</div>' if over else ''}"
            f"</div>",
            unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.62rem;color:#6B7080;margin-top:4px;'>"
        "⚠ = overused (>2.5% density)</div>",
        unsafe_allow_html=True)


def show_chapter_word_counts(story, chapters, scenes):
    """Bar chart of word count per chapter."""
    if not chapters:
        st.caption("No chapters defined yet.")
        return

    # Estimate by splitting prose into equal chunks per chapter
    msgs = [m["content"] for m in story.get("messages", [])
            if m.get("role") == "assistant"]
    if not msgs:
        return

    chunk_size = max(1, len(msgs) // len(chapters))
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>"
        "📖 Word Count per Chapter</div>",
        unsafe_allow_html=True)

    max_wc = 1
    wcs = []
    for i, chap in enumerate(chapters):
        chunk = msgs[i*chunk_size:(i+1)*chunk_size]
        wc    = sum(len(m.split()) for m in chunk)
        wcs.append(wc)
        max_wc = max(max_wc, wc)

    COLORS = ["#4D6BFE","#a78bfa","#60a5fa","#34d399","#fbbf24",
              "#f472b6","#fb923c"]
    for i, (chap, wc) in enumerate(zip(chapters, wcs)):
        pct   = int(wc / max_wc * 100)
        color = COLORS[i % len(COLORS)]
        title = chap.get("title", f"Chapter {i+1}")[:28]
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
            f"<div style='width:100px;font-size:0.70rem;color:#C5C8D4;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{_html.escape(title)}</div>"
            f"<div style='flex:1;background:rgba(77,107,254,0.07);border-radius:3px;height:12px;'>"
            f"<div style='width:{pct}%;background:{color};height:12px;border-radius:3px;'></div></div>"
            f"<div style='width:40px;font-size:0.68rem;color:#6B7080;text-align:right;'>"
            f"{wc:,}</div></div>",
            unsafe_allow_html=True)




# ═══════════════════════════════════════════════════════════════════════════
# DAILY WORD GOAL SETTER
# ═══════════════════════════════════════════════════════════════════════════

_GOAL_PRESETS = {
    "🌱 Casual (200/day)"  : 200,
    "✍️ Regular (500/day)" : 500,
    "🏃 Committed (1K/day)": 1000,
    "🔥 NaNo mode (1667/day)": 1667,
    "🚀 Sprint (3K/day)"   : 3000,
}

def show_daily_goal(story_id=None):
    """Daily word count goal tracker with progress ring."""
    goal_key    = "_daily_goal"
    log         = get_writing_log()
    today       = date.today().isoformat()
    today_words = _day_total(log, today)

    st.markdown("**🎯 Daily Writing Goal**")

    # Goal selection
    goal_preset = st.selectbox(
        "Goal preset",
        list(_GOAL_PRESETS.keys()),
        key="goal_preset_select",
        label_visibility="collapsed")
    preset_val = _GOAL_PRESETS[goal_preset]

    custom = st.number_input(
        "Or set custom goal (words/day)",
        min_value=50, max_value=10000,
        value=st.session_state.get(goal_key, preset_val),
        step=50, key="goal_custom_input")

    goal = custom
    st.session_state[goal_key] = goal

    # Progress ring SVG
    import math
    pct      = min(1.0, today_words / max(goal, 1))
    pct_disp = int(pct * 100)
    r, cx, cy = 42, 55, 55
    circumference = 2 * math.pi * r
    offset   = circumference * (1 - pct)
    color    = "#34d399" if pct >= 1.0 else ("#fbbf24" if pct >= 0.5 else "#4D6BFE")
    label    = "🎉 Goal reached!" if pct >= 1.0 else f"{goal - today_words:,} to go"

    ring_svg = (
        f'<svg width="110" height="110" viewBox="0 0 110 110" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(77,107,254,0.1)" stroke-width="9"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="9"'
        f' stroke-linecap="round" stroke-dasharray="{circumference:.1f}"'
        f' stroke-dashoffset="{offset:.1f}" transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="16" font-weight="800"'
        f' fill="{color}" font-family="Inter,sans-serif" dy="0.35em">{pct_disp}%</text>'
        f'</svg>')

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(ring_svg, unsafe_allow_html=True)
    with col2:
        streak = _streak_count(log)
        st.markdown(
            f"<div style='padding-top:14px;'>"
            f"<div style='font-size:1.1rem;font-weight:700;color:{color};'>"
            f"{today_words:,} / {goal:,}</div>"
            f"<div style='font-size:0.72rem;color:#6B7080;margin-top:2px;'>{label}</div>"
            f"<div style='font-size:0.72rem;color:#A8BCFF;margin-top:8px;'>🔥 {streak} day streak</div>"
            f"</div>",
            unsafe_allow_html=True)

    # Weekly summary bar
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin:10px 0 6px;'>"
        "Last 7 Days</div>",
        unsafe_allow_html=True)

    today_d = date.today()
    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    week_html = ["<div style='display:flex;gap:4px;align-items:flex-end;height:48px;'>"]
    for i in range(6, -1, -1):
        d     = today_d - timedelta(days=i)
        wc    = _day_total(log, d.isoformat())
        pct_d = min(1.0, wc / max(goal, 1))
        bar_h = max(4, int(pct_d * 40))
        color = "#34d399" if pct_d >= 1.0 else ("#fbbf24" if pct_d >= 0.5 else "#4D6BFE")
        is_today = d == today_d
        week_html.append(
            f"<div style='flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;'>"
            f"<div style='width:100%;background:{color};height:{bar_h}px;border-radius:3px;"
            f"{'box-shadow:0 0 6px ' + color + '80;' if is_today else ''}'></div>"
            f"<div style='font-size:0.60rem;color:{'#A8BCFF' if is_today else '#6B7080'};'>"
            f"{day_names[d.weekday()]}</div></div>")
    week_html.append("</div>")
    st.markdown("".join(week_html), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# GENRE BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════

_GENRE_BENCHMARKS = {
    "Fantasy":         {"words": (90000, 120000), "avg_sent": 18, "dialogue_pct": 35, "vocab": 45},
    "Romance":         {"words": (60000, 90000),  "avg_sent": 14, "dialogue_pct": 50, "vocab": 38},
    "Thriller":        {"words": (70000, 90000),  "avg_sent": 12, "dialogue_pct": 40, "vocab": 40},
    "Literary Fiction":{"words": (70000, 100000), "avg_sent": 22, "dialogue_pct": 25, "vocab": 55},
    "Science Fiction": {"words": (80000, 110000), "avg_sent": 16, "dialogue_pct": 35, "vocab": 48},
    "Mystery":         {"words": (60000, 80000),  "avg_sent": 13, "dialogue_pct": 45, "vocab": 40},
    "Horror":          {"words": (60000, 90000),  "avg_sent": 13, "dialogue_pct": 30, "vocab": 42},
    "Historical":      {"words": (90000, 130000), "avg_sent": 20, "dialogue_pct": 30, "vocab": 50},
    "Young Adult":     {"words": (60000, 90000),  "avg_sent": 13, "dialogue_pct": 45, "vocab": 35},
    "General Fiction": {"words": (70000, 100000), "avg_sent": 16, "dialogue_pct": 38, "vocab": 42},
}

def show_genre_benchmarks(story, characters):
    """Compare story stats against published genre averages."""
    genre = story.get("genre", "General Fiction")
    bench = _GENRE_BENCHMARKS.get(genre, _GENRE_BENCHMARKS["General Fiction"])

    msgs = [m["content"] for m in story.get("messages", [])
            if m.get("role") == "assistant"]
    if not msgs:
        st.caption("Add some story content to see genre comparisons.")
        return

    text  = " ".join(msgs)
    words = text.split()
    total = len(words)

    # Calculate user's stats
    import re as _re
    sentences    = [s.strip() for s in _re.split(r'[.!?]+', text) if len(s.strip()) > 4]
    avg_sent     = round(sum(len(s.split()) for s in sentences) / max(len(sentences), 1), 1)
    unique       = len(set(w.lower().strip(".,!?;:\"'") for w in words))
    vocab_rich   = round(unique / max(total, 1) * 100, 1)
    dialogue_wds = len(_re.findall(r'[""\"](.*?)[""\"]\s', text))
    dialogue_pct = round(dialogue_wds / max(total, 1) * 100, 1)

    target_lo, target_hi = bench["words"]

    st.markdown(
        f"<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        f"Comparing your <b style='color:#A8BCFF;'>{genre}</b> story against "
        f"published {genre} novels.</div>",
        unsafe_allow_html=True)

    def _bar_compare(label, yours, lo, hi, unit="", higher_is_better=True):
        target_mid = (lo + hi) / 2
        in_range = lo <= yours <= hi
        pct_yours = min(100, int(yours / max(hi * 1.3, 1) * 100))
        pct_lo    = int(lo / max(hi * 1.3, 1) * 100)
        pct_hi    = int(hi / max(hi * 1.3, 1) * 100)
        status    = "✅" if in_range else ("📈" if yours < lo else "📉")
        color     = "#34d399" if in_range else "#fbbf24"

        st.markdown(
            f"<div style='margin-bottom:10px;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.76rem;margin-bottom:3px;'>"
            f"<span style='color:var(--text-primary);font-weight:600;'>{label}</span>"
            f"<span style='color:{color};'>{status} {yours:,}{unit} "
            f"<span style='color:#6B7080;font-size:0.68rem;'>"
            f"(target: {lo:,}–{hi:,}{unit})</span></span></div>"
            f"<div style='position:relative;background:rgba(77,107,254,0.08);border-radius:4px;height:10px;'>"
            f"<div style='position:absolute;left:{pct_lo}%;width:{pct_hi-pct_lo}%;height:10px;"
            f"background:rgba(77,107,254,0.2);border-radius:4px;'></div>"
            f"<div style='position:absolute;left:{min(pct_yours, 99)}%;top:-2px;width:3px;height:14px;"
            f"background:{color};border-radius:2px;'></div>"
            f"</div></div>",
            unsafe_allow_html=True)

    _bar_compare("Total Words",          total,        target_lo, target_hi)
    _bar_compare("Avg Sentence Length",  avg_sent,     bench["avg_sent"]-3, bench["avg_sent"]+3, "w")
    _bar_compare("Dialogue %",           dialogue_pct, bench["dialogue_pct"]-10, bench["dialogue_pct"]+10, "%")
    _bar_compare("Vocab Richness",       vocab_rich,   bench["vocab"]-5, bench["vocab"]+10, "%")

    # Overall score
    in_range_count = sum([
        target_lo <= total <= target_hi,
        bench["avg_sent"]-3 <= avg_sent <= bench["avg_sent"]+3,
        bench["dialogue_pct"]-10 <= dialogue_pct <= bench["dialogue_pct"]+10,
        bench["vocab"]-5 <= vocab_rich <= bench["vocab"]+10,
    ])
    score = int(in_range_count / 4 * 100)
    score_color = "#34d399" if score >= 75 else ("#fbbf24" if score >= 50 else "#f87171")

    st.markdown(
        f"<div style='background:rgba(77,107,254,0.06);border:1px solid rgba(77,107,254,0.15);"
        f"border-radius:8px;padding:10px 14px;margin-top:8px;display:flex;align-items:center;gap:12px;'>"
        f"<div style='font-size:1.8rem;font-weight:900;color:{score_color};'>{score}%</div>"
        f"<div><div style='font-size:0.80rem;font-weight:700;color:#A8BCFF;'>Genre Match Score</div>"
        f"<div style='font-size:0.70rem;color:#6B7080;'>{in_range_count}/4 metrics in published range</div>"
        f"</div></div>",
        unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SCENE LENGTH DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def show_scene_length_distribution(story, scenes):
    """Visualise word count distribution across scenes."""
    if not scenes:
        st.caption("Add scenes to see length distribution.")
        return

    # Estimate scene word counts from scene content field
    scene_wcs = []
    for sc in scenes:
        content = sc.get("content", "") or sc.get("summary", "") or ""
        wc = len(content.split()) if content else 0
        scene_wcs.append((sc.get("title", f"Scene {sc.get('order','')}"), wc))

    # Filter scenes with content
    scene_wcs = [(t, wc) for t, wc in scene_wcs if wc > 0]
    if not scene_wcs:
        st.caption("Scenes don't have content yet — word counts unavailable.")
        return

    total_sc  = len(scene_wcs)
    avg_sc_wc = int(sum(wc for _, wc in scene_wcs) / total_sc)
    max_sc_wc = max(wc for _, wc in scene_wcs)
    min_sc_wc = min(wc for _, wc in scene_wcs)

    st.markdown(
        f"<div style='display:flex;gap:16px;margin-bottom:10px;font-size:0.78rem;'>"
        f"<span>📊 <b style='color:#A8BCFF;'>{total_sc}</b> scenes</span>"
        f"<span>⌀ <b style='color:#A8BCFF;'>{avg_sc_wc:,}</b> avg words</span>"
        f"<span>↕ <b style='color:#6B7080;'>{min_sc_wc}–{max_sc_wc:,}</b> range</span>"
        f"</div>",
        unsafe_allow_html=True)

    # Bar per scene
    COLORS = ["#4D6BFE","#a78bfa","#60a5fa","#34d399","#fbbf24","#f472b6","#fb923c"]
    for i, (title, wc) in enumerate(scene_wcs[:15]):  # cap at 15
        pct = int(wc / max(max_sc_wc, 1) * 100)
        color = COLORS[i % len(COLORS)]
        flag = ""
        if wc < 100:    flag = " <span style='color:#fbbf24;font-size:0.60rem;'>⚠ very short</span>"
        elif wc > 3000: flag = " <span style='color:#f87171;font-size:0.60rem;'>⚠ very long</span>"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
            f"<div style='width:90px;font-size:0.68rem;color:#C5C8D4;"
            f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{title[:14]}</div>"
            f"<div style='flex:1;background:rgba(77,107,254,0.07);border-radius:3px;height:12px;'>"
            f"<div style='width:{pct}%;background:{color};height:12px;border-radius:3px;opacity:0.85;'></div></div>"
            f"<div style='width:40px;font-size:0.68rem;color:#6B7080;text-align:right;'>"
            f"{wc:,}</div>{flag}</div>",
            unsafe_allow_html=True)

    if len(scene_wcs) > 15:
        st.caption(f"Showing 15 of {len(scene_wcs)} scenes.")

    # Consistency score
    import statistics as _stats
    if len(scene_wcs) > 2:
        wcs_only = [wc for _, wc in scene_wcs]
        cv = _stats.stdev(wcs_only) / max(avg_sc_wc, 1) * 100
        if cv < 40:
            msg, color = "✅ Consistent scene lengths", "#34d399"
        elif cv < 80:
            msg, color = "⚖️ Moderate variation — generally fine", "#fbbf24"
        else:
            msg, color = "⚠️ High variation — some scenes may feel rushed or bloated", "#f87171"
        st.markdown(
            f"<div style='font-size:0.73rem;color:{color};margin-top:6px;'>{msg}</div>",
            unsafe_allow_html=True)


def show_full_analytics(story, characters, chapters=None, scenes=None):
    """Enhanced analytics dashboard with all charts."""
    tabs = st.tabs([
        "📊 Overview", "🎯 Daily Goal", "🧬 Writing DNA", "📏 Sentences",
        "🔤 Vocabulary", "📖 Chapters", "🎭 Scenes", "🌍 Genre Fit",
        "📈 Readability", "⚡ Pacing"
    ])

    with tabs[0]:
        show_analytics_dashboard(story, characters)
    with tabs[1]:
        show_daily_goal(story.get("id"))
    with tabs[2]:
        st.markdown("**🧬 Writing DNA — Style Fingerprint**")
        show_writing_dna(story)
    with tabs[3]:
        show_sentence_length_chart(story)
    with tabs[4]:
        show_word_frequency_chart(story)
    with tabs[5]:
        show_chapter_word_counts(story, chapters or [], scenes or [])
    with tabs[6]:
        st.markdown("**🎭 Scene Length Distribution**")
        show_scene_length_distribution(story, scenes or [])
    with tabs[7]:
        st.markdown("**🌍 Genre Benchmark Comparison**")
        show_genre_benchmarks(story, characters)
    with tabs[8]:
        st.markdown("**📈 Readability Over Time**")
        readability_over_time(story)
    with tabs[9]:
        st.markdown("**⚡ Pacing Map**")
        pacing_analysis(story)
