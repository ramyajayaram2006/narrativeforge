"""
analytics_enhanced.py — NarrativeForge Enhanced Analytics
══════════════════════════════════════════════════════════
Two new analytics panels:
  1. Character Screen Time — who gets the most page time
  2. Scene Length Distribution — bar chart of word counts per scene

INTEGRATION (workspace.py, "Story Health" or "Analytics" tab):
    from analytics_enhanced import show_character_screen_time, show_scene_distribution
    show_character_screen_time(story, characters)
    show_scene_distribution(story, scenes)
"""

import re
import html as _html
import streamlit as st


# ── Colour palette ────────────────────────────────────────────────────────────
_COLOURS = [
    "#4D6BFE", "#f87171", "#fbbf24", "#34d399", "#a78bfa",
    "#fb923c", "#60a5fa", "#f472b6", "#2dd4bf", "#818cf8",
]


# ── 1. Character Screen Time ──────────────────────────────────────────────────

def _count_mentions(prose: str, name: str) -> int:
    """Count how many times a character name appears in prose (case-insensitive)."""
    if not name or not prose:
        return 0
    return len(re.findall(r'\b' + re.escape(name) + r'\b', prose, re.IGNORECASE))

def _count_dialogue_lines(prose: str, name: str) -> int:
    """Count dialogue attributed to a character: lines starting with 'Name:' or 'Name said'."""
    if not name or not prose:
        return 0
    pattern = r'(?i)\b' + re.escape(name) + r'\b.*?[":]\s*["\']'
    return len(re.findall(pattern, prose))


def show_character_screen_time(story: dict, characters: list):
    """Render character screen-time analytics panel."""
    if not characters:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;text-align:center;padding:20px;'>"
            "Add characters to see screen time analytics.</div>",
            unsafe_allow_html=True)
        return

    # Collect all prose
    prose = " ".join(
        m["content"] for m in story.get("messages", [])
        if m.get("role") == "assistant" and not m["content"].startswith("◆")
    )
    total_words = len(prose.split()) or 1

    if total_words < 50:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;'>Write more story to see character analytics.</div>",
            unsafe_allow_html=True)
        return

    # Count mentions per character
    data = []
    for char in characters:
        name      = char.get("name", "")
        mentions  = _count_mentions(prose, name)
        dialogues = _count_dialogue_lines(prose, name)
        # Approximate "page time" as mentions / total_words * 100
        pct       = round(mentions / total_words * 1000, 1)  # per-thousand words
        data.append({
            "name":      name,
            "role":      char.get("role", ""),
            "mentions":  mentions,
            "dialogues": dialogues,
            "pct":       pct,
        })

    # Sort by mentions descending
    data.sort(key=lambda x: x["mentions"], reverse=True)

    total_mentions = sum(d["mentions"] for d in data) or 1

    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:10px;'>🎭 Character Screen Time</div>",
        unsafe_allow_html=True)

    # Horizontal bar chart (pure HTML/CSS — no extra deps)
    bars_html = ["<div style='display:flex;flex-direction:column;gap:6px;margin-bottom:14px;'>"]
    for i, d in enumerate(data):
        colour  = _COLOURS[i % len(_COLOURS)]
        bar_pct = int(d["mentions"] / total_mentions * 100)
        role_badge = (
            f"<span style='font-size:0.60rem;color:#8B8FA8;background:rgba(77,107,254,0.1);"
            f"border-radius:4px;padding:1px 5px;margin-left:5px;'>{_html.escape(d['role'])}</span>"
            if d["role"] else ""
        )
        bars_html.append(
            f"<div>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;margin-bottom:3px;'>"
            f"<div style='font-size:0.78rem;font-weight:600;color:{colour};'>"
            f"{_html.escape(d['name'])}{role_badge}</div>"
            f"<div style='font-size:0.68rem;color:#6B7080;font-family:monospace;'>"
            f"{d['mentions']} mentions · {d['pct']}/1k words</div></div>"
            f"<div style='background:rgba(77,107,254,0.1);border-radius:4px;height:10px;'>"
            f"<div style='background:{colour};width:{bar_pct}%;"
            f"height:10px;border-radius:4px;'></div></div></div>"
        )
    bars_html.append("</div>")
    st.markdown("".join(bars_html), unsafe_allow_html=True)

    # Table: mentions + dialogue
    rows_html = [
        "<table style='width:100%;border-collapse:collapse;font-size:0.74rem;'>",
        "<thead><tr style='border-bottom:1px solid rgba(77,107,254,0.2);'>",
        "<th style='text-align:left;padding:4px 8px;color:#6B7080;'>Character</th>",
        "<th style='text-align:right;padding:4px 8px;color:#6B7080;'>Mentions</th>",
        "<th style='text-align:right;padding:4px 8px;color:#6B7080;'>Share</th>",
        "</tr></thead><tbody>",
    ]
    for i, d in enumerate(data):
        colour  = _COLOURS[i % len(_COLOURS)]
        share   = f"{d['mentions'] / total_mentions * 100:.0f}%"
        rows_html.append(
            f"<tr style='border-bottom:1px solid rgba(77,107,254,0.07);'>"
            f"<td style='padding:4px 8px;color:{colour};font-weight:600;'>"
            f"{_html.escape(d['name'])}</td>"
            f"<td style='padding:4px 8px;text-align:right;color:#C5C8D4;'>{d['mentions']}</td>"
            f"<td style='padding:4px 8px;text-align:right;color:#8B8FA8;'>{share}</td>"
            f"</tr>"
        )
    rows_html.append("</tbody></table>")
    st.markdown("".join(rows_html), unsafe_allow_html=True)

    # Warning: absent characters
    absent = [d["name"] for d in data if d["mentions"] == 0]
    if absent:
        st.markdown(
            f"<div style='font-size:0.72rem;color:#fbbf24;margin-top:8px;'>"
            f"⚠️ Characters with 0 mentions: {', '.join(_html.escape(n) for n in absent)}"
            f"</div>",
            unsafe_allow_html=True)

    # Dominant character warning
    if data and data[0]["mentions"] / total_mentions > 0.6:
        st.markdown(
            f"<div style='font-size:0.72rem;color:#fbbf24;margin-top:4px;'>"
            f"⚠️ <strong>{_html.escape(data[0]['name'])}</strong> dominates "
            f"{data[0]['mentions'] / total_mentions * 100:.0f}% of mentions — "
            f"consider giving other characters more page time.</div>",
            unsafe_allow_html=True)


# ── 2. Scene Length Distribution ─────────────────────────────────────────────

def show_scene_distribution(story: dict, scenes: list):
    """
    Render scene length distribution.
    Estimates word count per scene by dividing total prose proportionally
    by scene order (a heuristic — actual content isn't tagged per scene).
    """
    if not scenes:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;text-align:center;padding:16px;'>"
            "Add scenes to see scene length distribution.</div>",
            unsafe_allow_html=True)
        return

    prose_msgs = [
        m["content"] for m in story.get("messages", [])
        if m.get("role") == "assistant" and not m["content"].startswith("◆")
    ]
    all_prose = " ".join(prose_msgs)
    import re as _re
    sentences = [s.strip() for s in _re.split(r'(?<=[.!?])\s+', all_prose) if s.strip()]
    total_sents = len(sentences) or 1
    n_scenes    = len(scenes)
    chunk       = max(1, total_sents // n_scenes)

    scene_word_counts = []
    for idx, scene in enumerate(scenes):
        start = idx * chunk
        end   = start + chunk if idx < n_scenes - 1 else total_sents
        slice_text = " ".join(sentences[start:end])
        wc = len(slice_text.split())
        scene_word_counts.append({
            "title": scene.get("title", f"Scene {idx+1}"),
            "words": wc,
            "location": scene.get("location", ""),
        })

    total_words = sum(d["words"] for d in scene_word_counts) or 1
    max_words   = max(d["words"] for d in scene_word_counts) or 1
    avg_words   = total_words // n_scenes

    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:10px;'>🎬 Scene Length Distribution</div>",
        unsafe_allow_html=True)

    # Summary stats
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("Scenes", n_scenes)
    with sc2:
        st.metric("Avg Words/Scene", f"{avg_words:,}")
    with sc3:
        longest = max(scene_word_counts, key=lambda x: x["words"])
        st.metric("Longest Scene", f"{longest['words']:,}")

    # Bar chart
    bars_html = ["<div style='display:flex;flex-direction:column;gap:6px;margin-top:10px;'>"]
    for i, d in enumerate(scene_word_counts):
        colour  = _COLOURS[i % len(_COLOURS)]
        bar_pct = int(d["words"] / max_words * 100)
        pct_of_total = d["words"] / total_words * 100

        # Short/long warnings
        warn = ""
        if d["words"] < avg_words * 0.4:
            warn = " <span style='color:#fbbf24;font-size:0.62rem;'>⚠ short</span>"
        elif d["words"] > avg_words * 2.0:
            warn = " <span style='color:#f87171;font-size:0.62rem;'>⚠ long</span>"

        loc_text = (f" <span style='color:#6B7080;'>📍 {_html.escape(d['location'][:25])}</span>"
                    if d["location"] else "")
        bars_html.append(
            f"<div>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;margin-bottom:3px;'>"
            f"<div style='font-size:0.76rem;font-weight:600;color:{colour};'>"
            f"{_html.escape(d['title'][:30])}{loc_text}{warn}</div>"
            f"<div style='font-size:0.68rem;color:#6B7080;font-family:monospace;'>"
            f"{d['words']:,} words · {pct_of_total:.0f}%</div></div>"
            f"<div style='background:rgba(77,107,254,0.1);border-radius:4px;height:12px;'>"
            f"<div style='background:{colour};width:{bar_pct}%;"
            f"height:12px;border-radius:4px;'></div></div></div>"
        )
    bars_html.append("</div>")
    st.markdown("".join(bars_html), unsafe_allow_html=True)

    # Pacing advice
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    short_scenes = [d for d in scene_word_counts if d["words"] < avg_words * 0.4]
    long_scenes  = [d for d in scene_word_counts if d["words"] > avg_words * 2.0]

    if short_scenes:
        names = ", ".join(f'"{_html.escape(d["title"])}"' for d in short_scenes[:3])
        st.markdown(
            f"<div style='font-size:0.72rem;color:#fbbf24;'>"
            f"⚠️ Short scenes (may feel rushed): {names}</div>",
            unsafe_allow_html=True)
    if long_scenes:
        names = ", ".join(f'"{_html.escape(d["title"])}"' for d in long_scenes[:3])
        st.markdown(
            f"<div style='font-size:0.72rem;color:#f87171;margin-top:3px;'>"
            f"⚠️ Very long scenes (consider splitting): {names}</div>",
            unsafe_allow_html=True)
    if not short_scenes and not long_scenes:
        st.markdown(
            "<div style='font-size:0.72rem;color:#4ade80;'>"
            "✅ Scene lengths look well-balanced.</div>",
            unsafe_allow_html=True)
