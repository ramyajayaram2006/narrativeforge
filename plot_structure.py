"""
plot_structure.py — NarrativeForge Plot Structure Overlays
══════════════════════════════════════════════════════════
Three frameworks: 3-Act Structure, Save the Cat, Hero's Journey.
Renders an interactive beat sheet that shows where the story currently sits
on the framework and lets the writer mark beats as done.

INTEGRATION (workspace.py):
    In the "Plot Arc" tab, add:
        from plot_structure import show_plot_structure_panel
        show_plot_structure_panel(story, username)
"""

import html as _html
import streamlit as st
from database import save_story

# ── Framework definitions ─────────────────────────────────────────────────────

_THREE_ACT = {
    "name": "3-Act Structure",
    "desc": "The classical dramatic structure: Setup, Confrontation, Resolution.",
    "beats": [
        {"id": "3a_setup",        "label": "Act 1 — Setup",         "pct": 0,   "desc": "Introduce the world, protagonist, and the status quo."},
        {"id": "3a_inciting",     "label": "Inciting Incident",      "pct": 10,  "desc": "The event that disrupts the ordinary world and kicks off the story."},
        {"id": "3a_plot1",        "label": "Plot Point 1",           "pct": 25,  "desc": "The protagonist commits to the journey; no going back."},
        {"id": "3a_mid1",         "label": "Rising Action",          "pct": 37,  "desc": "Obstacles increase. Stakes rise. Protagonist is reactive."},
        {"id": "3a_midpoint",     "label": "Midpoint",               "pct": 50,  "desc": "A major revelation or reversal. Protagonist shifts from reactive to proactive."},
        {"id": "3a_mid2",         "label": "Complications",          "pct": 63,  "desc": "All hell breaks loose. Things get worse."},
        {"id": "3a_plot2",        "label": "Plot Point 2 / Dark Night","pct": 75, "desc": "All seems lost. The lowest point. Everything the protagonist built crumbles."},
        {"id": "3a_climax",       "label": "Climax",                 "pct": 88,  "desc": "The final confrontation. The protagonist must use everything they've learned."},
        {"id": "3a_resolution",   "label": "Resolution",             "pct": 100, "desc": "The new normal. Loose ends tied. Emotional landing."},
    ],
}

_SAVE_THE_CAT = {
    "name": "Save the Cat",
    "desc": "Blake Snyder's 15-beat screenplay structure adapted for prose.",
    "beats": [
        {"id": "stc_opening",     "label": "Opening Image",          "pct": 1,   "desc": "A snapshot of the hero's world before the adventure begins."},
        {"id": "stc_theme",       "label": "Theme Stated",           "pct": 5,   "desc": "Someone (not the hero) states what the story is really about."},
        {"id": "stc_setup",       "label": "Set-Up",                 "pct": 10,  "desc": "Expand on hero's world. Plant seeds of theme."},
        {"id": "stc_catalyst",    "label": "Catalyst",               "pct": 12,  "desc": "Life-changing event. The call to action."},
        {"id": "stc_debate",      "label": "Debate",                 "pct": 18,  "desc": "Should I go? Fear. Hesitation. The last chance to turn back."},
        {"id": "stc_act2",        "label": "Break into Act 2",       "pct": 25,  "desc": "The hero commits. Leaves the old world behind."},
        {"id": "stc_bsub",        "label": "B Story",                "pct": 30,  "desc": "Love story or subplot that carries the theme."},
        {"id": "stc_fun",         "label": "Fun and Games",          "pct": 37,  "desc": "The promise of the premise. Why you came to this movie."},
        {"id": "stc_midpoint",    "label": "Midpoint",               "pct": 50,  "desc": "False victory or false defeat. Stakes raised."},
        {"id": "stc_baddies",     "label": "Bad Guys Close In",      "pct": 60,  "desc": "Antagonist forces regroup and counterattack."},
        {"id": "stc_alllost",     "label": "All Is Lost",            "pct": 75,  "desc": "Whiff of death. The lowest point."},
        {"id": "stc_dark",        "label": "Dark Night of the Soul", "pct": 78,  "desc": "The hero wallows in misery. How did it come to this?"},
        {"id": "stc_act3",        "label": "Break into Act 3",       "pct": 80,  "desc": "A new idea, inspired by the B story, gives the hero the final push."},
        {"id": "stc_finale",      "label": "Finale",                 "pct": 88,  "desc": "The hero executes the plan. Antagonist vanquished. New world order."},
        {"id": "stc_final_img",   "label": "Final Image",            "pct": 100, "desc": "Mirror of the opening. Shows how much the world/hero has changed."},
    ],
}

_HEROS_JOURNEY = {
    "name": "Hero's Journey",
    "desc": "Joseph Campbell's monomyth — the 12 stages of the universal hero story.",
    "beats": [
        {"id": "hj_ordinary",     "label": "Ordinary World",         "pct": 0,   "desc": "We see the hero's normal world before the adventure begins."},
        {"id": "hj_call",         "label": "Call to Adventure",      "pct": 8,   "desc": "The hero is presented with a problem, challenge, or adventure."},
        {"id": "hj_refusal",      "label": "Refusal of the Call",    "pct": 14,  "desc": "The hero hesitates. Fear, doubt, or obligation hold them back."},
        {"id": "hj_mentor",       "label": "Meeting the Mentor",     "pct": 20,  "desc": "The hero meets a mentor who gives advice, tools, or a push."},
        {"id": "hj_threshold",    "label": "Crossing the Threshold", "pct": 27,  "desc": "The hero commits to the adventure. Leaves the ordinary world."},
        {"id": "hj_tests",        "label": "Tests, Allies, Enemies", "pct": 36,  "desc": "The hero faces challenges and learns who can be trusted."},
        {"id": "hj_approach",     "label": "Approach to Inmost Cave","pct": 46,  "desc": "The hero approaches the dangerous place at the heart of the story."},
        {"id": "hj_ordeal",       "label": "The Ordeal",             "pct": 54,  "desc": "The hero faces the greatest challenge yet. Near-death experience."},
        {"id": "hj_reward",       "label": "Reward (Seizing the Sword)","pct": 63,"desc": "Having survived, the hero takes possession of the treasure."},
        {"id": "hj_road_back",    "label": "The Road Back",          "pct": 73,  "desc": "The hero begins the journey back to the ordinary world."},
        {"id": "hj_resurrection", "label": "The Resurrection",       "pct": 84,  "desc": "Final and most dangerous encounter with death. Purification."},
        {"id": "hj_return",       "label": "Return with the Elixir", "pct": 100, "desc": "The hero returns home, changed, bearing something to improve the world."},
    ],
}

FRAMEWORKS = {
    "3-Act Structure":  _THREE_ACT,
    "Save the Cat":     _SAVE_THE_CAT,
    "Hero's Journey":   _HEROS_JOURNEY,
}


# ── Colour helpers ────────────────────────────────────────────────────────────

def _beat_color(done: bool, active: bool) -> str:
    if done:   return "#4ade80"
    if active: return "#4D6BFE"
    return "#4A4D60"

def _progress_pct(beats: list, done_ids: set) -> int:
    done_beats = [b for b in beats if b["id"] in done_ids]
    if not done_beats:
        return 0
    # Progress = position of the last completed beat
    last_done = max(done_beats, key=lambda b: b["pct"])
    return last_done["pct"]


# ── Main panel ────────────────────────────────────────────────────────────────

def show_plot_structure_panel(story: dict, username: str):
    """
    Render the plot structure overlay tab.
    Stores beat completion in story["plot_arc"] under a namespaced key.
    """
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>"
        "📐 Plot Structure Frameworks</div>",
        unsafe_allow_html=True)

    framework_name = st.selectbox(
        "Framework", list(FRAMEWORKS.keys()),
        key=f"ps_framework_{story['id']}",
        label_visibility="collapsed")

    fw = FRAMEWORKS[framework_name]

    st.markdown(
        f"<div style='font-size:0.78rem;color:#8B8FA8;font-style:italic;"
        f"margin-bottom:12px;'>{fw['desc']}</div>",
        unsafe_allow_html=True)

    # Load done beats from story's plot_arc dict (keyed by framework)
    arc = story.get("plot_arc", {})
    fw_key   = f"_ps_{fw['name'].replace(' ','_').lower()}"
    done_ids = set(arc.get(fw_key, []))

    beats    = fw["beats"]
    pct_done = _progress_pct(beats, done_ids)
    n_done   = len([b for b in beats if b["id"] in done_ids])
    n_total  = len(beats)

    # Progress bar
    bar_color = "#4ade80" if pct_done == 100 else "#4D6BFE"
    st.markdown(
        f"<div style='margin-bottom:14px;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:0.72rem;color:#6B7080;margin-bottom:4px;'>"
        f"<span>{framework_name}</span>"
        f"<span>{n_done}/{n_total} beats · ~{pct_done}% through story</span></div>"
        f"<div style='background:rgba(77,107,254,0.12);border-radius:6px;height:8px;'>"
        f"<div style='background:{bar_color};width:{pct_done}%;"
        f"height:8px;border-radius:6px;transition:width 0.3s;'></div></div></div>",
        unsafe_allow_html=True)

    # Beat checklist
    changed = False
    for i, beat in enumerate(beats):
        is_done   = beat["id"] in done_ids
        is_active = (not is_done) and (i == 0 or beats[i-1]["id"] in done_ids)
        dot_color = _beat_color(is_done, is_active)
        pct_label = f"{beat['pct']}%" if beat["pct"] > 0 else "Start"

        col_check, col_label = st.columns([0.5, 6])
        with col_check:
            checked = st.checkbox("", value=is_done,
                                  key=f"ps_beat_{story['id']}_{beat['id']}",
                                  label_visibility="collapsed")
            if checked != is_done:
                if checked:
                    done_ids.add(beat["id"])
                else:
                    done_ids.discard(beat["id"])
                changed = True
        with col_label:
            status_dot = "✅" if is_done else ("▶" if is_active else "○")
            st.markdown(
                f"<div style='display:flex;align-items:baseline;gap:8px;padding:3px 0;'>"
                f"<span style='font-size:0.80rem;font-weight:600;color:{dot_color};'>"
                f"{status_dot} {_html.escape(beat['label'])}</span>"
                f"<span style='font-size:0.62rem;color:#4A4D60;font-family:monospace;'>"
                f"~{pct_label}</span></div>"
                f"<div style='font-size:0.70rem;color:#6B7080;padding-left:2px;"
                f"margin-bottom:4px;line-height:1.4;'>{_html.escape(beat['desc'])}</div>",
                unsafe_allow_html=True)

    # Save changes
    if changed:
        arc[fw_key] = list(done_ids)
        story["plot_arc"] = arc
        save_story(username, story)
        st.rerun()

    # AI suggestion for next beat
    st.markdown("---")
    next_beat = next((b for b in beats if b["id"] not in done_ids), None)
    if next_beat:
        st.markdown(
            f"<div style='background:rgba(77,107,254,0.06);"
            f"border:1px solid rgba(77,107,254,0.18);"
            f"border-radius:8px;padding:10px 14px;'>"
            f"<div style='font-size:0.68rem;color:#4D6BFE;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;'>"
            f"📍 Next Beat</div>"
            f"<div style='font-size:0.82rem;font-weight:600;color:#A8BCFF;'>"
            f"{_html.escape(next_beat['label'])}</div>"
            f"<div style='font-size:0.76rem;color:#8B8FA8;margin-top:3px;'>"
            f"{_html.escape(next_beat['desc'])}</div></div>",
            unsafe_allow_html=True)

        if st.button("✨ Suggest how to write this beat", key=f"ps_suggest_{story['id']}",
                     use_container_width=True):
            _suggest_beat(story, next_beat, framework_name)

    if pct_done == 100:
        st.success(f"🎉 All {framework_name} beats complete!")


def _suggest_beat(story: dict, beat: dict, fw_name: str):
    """Call AI to suggest how to write the next beat."""
    try:
        import os, requests
        host  = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        model = os.environ.get("NARRATIVEFORGE_MODEL", "llama3.2")
        prose = " ".join(
            m["content"] for m in story.get("messages", [])[-6:]
            if m.get("role") == "assistant"
        )[:800]
        prompt = (
            f"I'm writing a {story.get('genre','Fiction')} story "
            f"({story.get('tone','').lower()} tone) using the {fw_name} framework.\n"
            f"I need to write the '{beat['label']}' beat: {beat['desc']}\n\n"
            f"Recent story context:\n{prose}\n\n"
            f"Give me 3 specific, concrete suggestions for how to execute this beat "
            f"in MY story. Keep each suggestion to 2 sentences. Number them 1, 2, 3."
        )
        with st.spinner(f"Generating ideas for '{beat['label']}'…"):
            r = requests.post(f"{host}/api/generate",
                json={"model": model, "prompt": prompt,
                      "stream": False, "options": {"num_predict": 300, "temperature": 0.85}},
                timeout=45)
            result = r.json().get("response", "").strip() if r.status_code == 200 else ""
        if result:
            st.markdown(
                f"<div style='background:rgba(77,107,254,0.08);"
                f"border:1px solid rgba(77,107,254,0.25);"
                f"border-radius:8px;padding:12px;font-size:0.82rem;"
                f"color:var(--text-primary);line-height:1.7;"
                f"white-space:pre-line;'>{_html.escape(result)}</div>",
                unsafe_allow_html=True)
        else:
            st.error("AI unavailable — is Ollama running?")
    except Exception as e:
        st.error(f"Error: {e}")
