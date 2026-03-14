"""
NarrativeForge — Daily Writing Tracker
Calendar heatmap, streak counter, milestone badges, word-per-day chart.
"""
import html as _html
from datetime import date, timedelta
import streamlit as st
from database import load_writing_sessions, get_writing_streak, log_writing_session

_MILESTONES = [
    (1,    "✏️ First Day"),
    (7,    "⚡ One Week"),
    (30,   "🌟 One Month"),
    (100,  "👑 100 Days"),
    (365,  "🌍 One Year"),
]


def _heat_color(words):
    if words == 0:     return "#1E2030"
    if words < 200:    return "#1e3a5f"
    if words < 500:    return "#1d4ed8"
    if words < 1000:   return "#3b82f6"
    if words < 2000:   return "#60a5fa"
    return "#93c5fd"


def show_daily_tracker(username):
    """Render the full daily writing tracker."""
    sessions   = load_writing_sessions(username, 365)
    streak     = get_writing_streak(username)
    today      = date.today()

    date_map   = {s["date"]: s["words"] for s in sessions}
    total_days = len(date_map)
    total_words = sum(s["words"] for s in sessions)
    best_day   = max(date_map.values(), default=0)

    # ── Stats row ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🔥 Streak",    f"{streak}d")
    with c2:
        st.metric("📅 Days",      f"{total_days}")
    with c3:
        st.metric("📝 Words",     f"{total_words:,}")
    with c4:
        st.metric("🏆 Best Day",  f"{best_day:,}")

    # ── Milestone badges ──────────────────────────────────────────────────
    earned = [label for target, label in _MILESTONES if streak >= target]
    if earned:
        st.markdown(
            "<div style='display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;'>" +
            "".join(
                f"<span style='background:rgba(77,107,254,0.12);border:1px solid rgba(77,107,254,0.3);"
                f"border-radius:20px;padding:3px 10px;font-size:0.72rem;color:#A8BCFF;"
                f"font-weight:600;'>{_html.escape(badge)}</span>"
                for badge in earned) +
            "</div>",
            unsafe_allow_html=True)

    st.markdown("---")

    # ── Calendar heatmap (last 12 weeks) ──────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.08em;margin-bottom:10px;'>📅 Last 12 Weeks</div>",
        unsafe_allow_html=True)

    # Build 84-day grid (12 weeks × 7 days)
    start = today - timedelta(days=83)
    weeks = []
    for week in range(12):
        row = []
        for day_offset in range(7):
            d = start + timedelta(days=week * 7 + day_offset)
            words = date_map.get(d.isoformat(), 0)
            is_today = (d == today)
            row.append((d, words, is_today))
        weeks.append(row)

    # Day labels
    day_labels = ["M", "T", "W", "T", "F", "S", "S"]
    label_html  = "".join(
        f"<div style='width:14px;height:14px;font-size:9px;color:#6B7080;"
        f"text-align:center;line-height:14px;'>{dl}</div>"
        for dl in day_labels)

    # Grid cells
    grid_cols = []
    for week in weeks:
        col_html = ""
        for d, words, is_today in week:
            bg      = _heat_color(words)
            border  = "2px solid #4D6BFE" if is_today else "1px solid rgba(255,255,255,0.05)"
            title   = f"{d.isoformat()}: {words:,} words"
            col_html += (
                f"<div title='{title}' style='width:14px;height:14px;border-radius:3px;"
                f"background:{bg};border:{border};'></div>")
        grid_cols.append(col_html)

    grid_html = (
        f"<div style='display:flex;gap:2px;align-items:flex-start;'>"
        f"<div style='display:flex;flex-direction:column;gap:2px;margin-right:4px;'>{label_html}</div>"
        + "".join(
            f"<div style='display:flex;flex-direction:column;gap:2px;'>{col}</div>"
            for col in grid_cols)
        + "</div>")

    # Legend
    legend_html = (
        "<div style='display:flex;align-items:center;gap:6px;margin-top:8px;'>"
        "<span style='font-size:0.68rem;color:#6B7080;'>Less</span>"
        + "".join(
            f"<div style='width:12px;height:12px;border-radius:2px;background:{_heat_color(w)};'></div>"
            for w in [0, 150, 400, 800, 1500, 2500])
        + "<span style='font-size:0.68rem;color:#6B7080;'>More</span></div>")

    st.markdown(grid_html + legend_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── Recent writing days bar chart ─────────────────────────────────────
    if sessions:
        recent = sorted(sessions, key=lambda x: x["date"])[-14:]
        st.markdown(
            "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.08em;margin-bottom:8px;'>📊 Last 14 Days</div>",
            unsafe_allow_html=True)
        max_words = max(s["words"] for s in recent) or 1
        bars = ""
        for s in recent:
            pct = int(s["words"] / max_words * 100)
            short_date = s["date"][5:]  # MM-DD
            bars += (
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
                f"<div style='font-size:0.68rem;color:#6B7080;width:32px;'>{short_date}</div>"
                f"<div style='flex:1;background:var(--primary-dim);border-radius:3px;height:8px;'>"
                f"<div style='width:{pct}%;background:#4D6BFE;height:8px;border-radius:3px;'></div></div>"
                f"<div style='font-size:0.68rem;color:#6B7080;width:38px;text-align:right;'>{s['words']:,}</div>"
                f"</div>")
        st.markdown(bars, unsafe_allow_html=True)
