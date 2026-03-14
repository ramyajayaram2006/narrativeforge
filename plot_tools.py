"""
NarrativeForge — Plot Development Tools
Three-Act Structure, Hero's Journey (12 stages), Save the Cat Beat Sheet (15 beats),
Scene Kanban Board, Foreshadowing Tracker, Subplot Manager.
"""
import os
import html as _html
import json
import requests
import streamlit as st
import llm
from database import save_story, load_scenes, load_chapters

llm.AI_UNAVAILABLE = "_llm.AI_UNAVAILABLE__"



def _prose(story):
    return " ".join(m["content"] for m in story.get("messages", [])
                    if m.get("role") == "assistant"
                    and not m["content"].startswith("◆"))[:800]


# ══════════════════════════════════════════════════════════════════════════════
# THREE-ACT STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

_THREE_ACT = [
    ("act1_setup",        "Act 1 — Setup",       "25%",
     "Introduce protagonist, world, and ordinary life. End with the Inciting Incident."),
    ("act1_incident",     "↳ Inciting Incident", "12%",
     "The event that disrupts the protagonist's ordinary world and forces a choice."),
    ("act2a_rising",      "Act 2A — Rising",     "25%",
     "Protagonist pursues new goal, faces obstacles, learns rules of new world."),
    ("act2_midpoint",     "↳ Midpoint",          "50%",
     "False victory or false defeat. Stakes raise. Protagonist fully committed."),
    ("act2b_darkmoment",  "Act 2B — Dark Night", "25%",
     "All seems lost. Protagonist hits rock bottom. Dark night of the soul."),
    ("act3_climax",       "Act 3 — Climax",      "90%",
     "Final confrontation. Protagonist uses everything learned. Do or die moment."),
    ("act3_resolution",   "↳ Resolution",        "95%",
     "New equilibrium. Show how protagonist and world have changed."),
]

def _show_three_act(story, username):
    arc = story.get("plot_arc", {})

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Classic Hollywood structure. Tick stages as you complete them, "
        "or use AI to suggest what belongs in each beat.</div>",
        unsafe_allow_html=True)

    changed = False
    for key, label, pct, desc in _THREE_ACT:
        col1, col2 = st.columns([5, 1])
        with col1:
            val = st.checkbox(
                f"**{label}** _{pct}_",
                value=arc.get(key, False),
                key=f"ta_{story['id']}_{key}",
                help=desc)
            if val != arc.get(key, False):
                arc[key] = val; changed = True
            # Notes field
            note_key = f"{key}_note"
            note = st.text_input("",
                value=arc.get(note_key, ""),
                placeholder=desc,
                key=f"tan_{story['id']}_{key}",
                label_visibility="collapsed")
            if note != arc.get(note_key, ""):
                arc[note_key] = note; changed = True
        with col2:
            if st.button("✨", key=f"ta_ai_{story['id']}_{key}",
                         help="AI suggest", use_container_width=True):
                with st.spinner(""):
                    result = llm.call(
                        f"For a {story.get('genre','Fiction')} story titled '{story.get('title','')}', "
                        f"suggest 2 sentences of specific content for: {label} — {desc}\n"
                        f"Story context: {_prose(story)}\n"
                        f"Be concrete and specific to THIS story. No generic advice.", 150)
                if result != llm.AI_UNAVAILABLE:
                    arc[note_key] = result; changed = True
                    st.rerun()

    if changed:
        story["plot_arc"] = arc
        save_story(username, story)

    # Visual progress bar
    done = sum(1 for key, *_ in _THREE_ACT if arc.get(key))
    pct  = int(done / len(_THREE_ACT) * 100)
    st.markdown(
        f"<div style='margin-top:12px;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.68rem;color:#6B7080;margin-bottom:4px;'>"
        f"<span>Structure progress</span><span>{done}/{len(_THREE_ACT)} beats</span></div>"
        f"<div style='background:var(--primary-dim);border-radius:4px;height:8px;'>"
        f"<div style='width:{pct}%;background:{'#34d399' if pct==100 else '#4D6BFE'};"
        f"height:8px;border-radius:4px;transition:width 0.3s;'></div></div></div>",
        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HERO'S JOURNEY (12 STAGES)
# ══════════════════════════════════════════════════════════════════════════════

_HEROS_JOURNEY = [
    ("hj_ordinary",    "1. Ordinary World",         "Hero shown in their everyday life."),
    ("hj_call",        "2. Call to Adventure",       "A problem or challenge appears."),
    ("hj_refusal",     "3. Refusal of the Call",     "Hero hesitates or is afraid."),
    ("hj_mentor",      "4. Meeting the Mentor",      "Hero gains guidance or a gift."),
    ("hj_threshold",   "5. Crossing the Threshold",  "Hero commits to the adventure."),
    ("hj_tests",       "6. Tests, Allies, Enemies",  "Hero learns rules of new world."),
    ("hj_approach",    "7. Approach to Inmost Cave", "Hero prepares for major challenge."),
    ("hj_ordeal",      "8. The Ordeal",              "Hero faces greatest fear. Death/rebirth."),
    ("hj_reward",      "9. Reward (Seizing the Sword)","Hero survives and earns reward."),
    ("hj_road_back",   "10. The Road Back",           "Hero begins journey back. New danger."),
    ("hj_resurrection","11. The Resurrection",        "Final test. Hero is transformed."),
    ("hj_return",      "12. Return with Elixir",      "Hero returns, changed, with a gift."),
]

def _show_heros_journey(story, username):
    arc = story.get("plot_arc", {})

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Joseph Campbell's monomyth — 12 universal stages of the hero's story.</div>",
        unsafe_allow_html=True)

    changed = False

    # Circular progress display
    done = sum(1 for key, *_ in _HEROS_JOURNEY if arc.get(key))
    pct  = int(done / len(_HEROS_JOURNEY) * 100)
    r, cx, cy = 38, 50, 50
    import math
    circumference = 2 * math.pi * r
    offset = circumference * (1 - pct / 100)
    color  = "#34d399" if pct == 100 else "#4D6BFE"
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:16px;margin-bottom:12px;'>"
        f"<svg width='100' height='100' viewBox='0 0 100 100'>"
        f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='rgba(77,107,254,0.1)' stroke-width='8'/>"
        f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{color}' stroke-width='8'"
        f" stroke-linecap='round' stroke-dasharray='{circumference:.1f}'"
        f" stroke-dashoffset='{offset:.1f}' transform='rotate(-90 {cx} {cy})'/>"
        f"<text x='{cx}' y='{cy+2}' text-anchor='middle' font-size='14' font-weight='800'"
        f" fill='{color}' font-family='Inter,sans-serif'>{pct}%</text>"
        f"<text x='{cx}' y='{cy+14}' text-anchor='middle' font-size='7'"
        f" fill='#6B7080' font-family='Inter,sans-serif'>complete</text>"
        f"</svg>"
        f"<div style='font-size:0.78rem;color:#6B7080;'>"
        f"{done} of {len(_HEROS_JOURNEY)} stages · "
        f"<span style='color:{color};font-weight:700;'>"
        f"{'Journey complete! 🎉' if pct==100 else f'{len(_HEROS_JOURNEY)-done} remaining'}"
        f"</span></div></div>",
        unsafe_allow_html=True)

    for key, label, desc in _HEROS_JOURNEY:
        is_done = arc.get(key, False)
        col1, col2 = st.columns([5, 1])
        with col1:
            val = st.checkbox(
                f"{'~~' if is_done else ''}**{label}**{'~~' if is_done else ''}",
                value=is_done, key=f"hj_{story['id']}_{key}", help=desc)
            if val != is_done:
                arc[key] = val; changed = True
            note_key = f"{key}_note"
            note = st.text_input("",
                value=arc.get(note_key, ""),
                placeholder=desc,
                key=f"hjn_{story['id']}_{key}",
                label_visibility="collapsed")
            if note != arc.get(note_key, ""):
                arc[note_key] = note; changed = True
        with col2:
            if st.button("✨", key=f"hj_ai_{story['id']}_{key}",
                         help="AI suggest", use_container_width=True):
                with st.spinner(""):
                    result = llm.call(
                        f"For '{story.get('title','')}' ({story.get('genre','Fiction')}), "
                        f"write 2 concrete sentences for stage: {label} — {desc}\n"
                        f"Context: {_prose(story)}\nBe specific to this story.", 140)
                if result != llm.AI_UNAVAILABLE:
                    arc[f"{key}_note"] = result; changed = True
                    st.rerun()

    if changed:
        story["plot_arc"] = arc
        save_story(username, story)


# ══════════════════════════════════════════════════════════════════════════════
# SAVE THE CAT BEAT SHEET (15 BEATS)
# ══════════════════════════════════════════════════════════════════════════════

_SAVE_THE_CAT = [
    ("stc_opening",      "Opening Image",         "1%",   "A snapshot of the hero's world before the journey."),
    ("stc_theme",        "Theme Stated",          "5%",   "Someone states (perhaps obliquely) the theme of the film."),
    ("stc_setup",        "Set-Up",                "1-10%","Introduce hero, show their flaws, plant subplots."),
    ("stc_catalyst",     "Catalyst",              "10%",  "Life-changing event. The moment the adventure begins."),
    ("stc_debate",       "Debate",                "10-20%","Hero debates whether to take the journey."),
    ("stc_break2",       "Break into Two",        "20%",  "Hero makes a choice and enters Act Two."),
    ("stc_bfun",         "B Story",               "22%",  "New character introduces the theme more personally."),
    ("stc_fun",          "Fun and Games",         "20-50%","The 'trailer moments'. Hero explores the new world."),
    ("stc_midpoint",     "Midpoint",              "50%",  "False victory or false defeat. Stakes double."),
    ("stc_bad",          "Bad Guys Close In",     "50-75%","Doubts, dissent, the enemy regroups."),
    ("stc_allis",        "All Is Lost",           "75%",  "Opposite of the opening image. Whiff of death."),
    ("stc_dark",         "Dark Night of the Soul","75-80%","Hero hits rock bottom. Darkest moment."),
    ("stc_break3",       "Break into Three",      "80%",  "A-story and B-story combine. Solution found."),
    ("stc_finale",       "Finale",                "80-99%","Hero storms the castle. Old world is defeated."),
    ("stc_final_image",  "Final Image",           "99%",  "Opposite of opening image. Change is confirmed."),
]

def _show_save_the_cat(story, username):
    arc = story.get("plot_arc", {})

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Blake Snyder's professional beat sheet — used by Hollywood screenwriters and novelists alike.</div>",
        unsafe_allow_html=True)

    changed = False
    done = sum(1 for key, *_ in _SAVE_THE_CAT if arc.get(key))

    # Progress
    pct = int(done / len(_SAVE_THE_CAT) * 100)
    st.markdown(
        f"<div style='background:var(--primary-dim);border-radius:4px;height:6px;margin-bottom:12px;'>"
        f"<div style='width:{pct}%;background:{'#34d399' if pct==100 else '#4D6BFE'};"
        f"height:6px;border-radius:4px;'></div></div>"
        f"<div style='font-size:0.68rem;color:#6B7080;margin-bottom:10px;'>"
        f"{done}/{len(_SAVE_THE_CAT)} beats · {pct}% complete</div>",
        unsafe_allow_html=True)

    for key, label, pct_pos, desc in _SAVE_THE_CAT:
        is_done = arc.get(key, False)
        col1, col2 = st.columns([5, 1])
        with col1:
            val = st.checkbox(
                f"**{label}** `{pct_pos}`",
                value=is_done, key=f"stc_{story['id']}_{key}", help=desc)
            if val != is_done:
                arc[key] = val; changed = True
            note_key = f"{key}_note"
            note = st.text_input("",
                value=arc.get(note_key, ""),
                placeholder=desc,
                key=f"stcn_{story['id']}_{key}",
                label_visibility="collapsed")
            if note != arc.get(note_key, ""):
                arc[note_key] = note; changed = True
        with col2:
            if st.button("✨", key=f"stc_ai_{story['id']}_{key}",
                         help="AI suggest", use_container_width=True):
                with st.spinner(""):
                    result = llm.call(
                        f"For '{story.get('title','')}' ({story.get('genre','Fiction')}), "
                        f"suggest specific content for Save the Cat beat: {label} — {desc}\n"
                        f"Story context: {_prose(story)}\n"
                        f"Write 2 concrete sentences. Be specific to THIS story.", 140)
                if result != llm.AI_UNAVAILABLE:
                    arc[f"{key}_note"] = result; changed = True
                    st.rerun()

    if changed:
        story["plot_arc"] = arc
        save_story(username, story)


# ══════════════════════════════════════════════════════════════════════════════
# SCENE KANBAN BOARD
# ══════════════════════════════════════════════════════════════════════════════

_KANBAN_COLS = ["💡 Idea", "📝 Drafted", "✏️ Revising", "✅ Done"]

def _show_kanban(story, username):
    """Drag-free kanban board — move scenes between status columns."""
    scenes   = load_scenes(username, story["id"])
    arc      = story.get("plot_arc", {})
    kb_state = arc.get("kanban", {})  # {scene_id: status}

    if not scenes:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;text-align:center;padding:24px;'>"
            "Add scenes in the Scenes tab to use the Kanban board.</div>",
            unsafe_allow_html=True)
        return

    # Render columns
    cols = st.columns(4)
    for col_idx, col_label in enumerate(_KANBAN_COLS):
        with cols[col_idx]:
            col_scenes = [s for s in scenes
                          if kb_state.get(str(s["id"]), "💡 Idea") == col_label]
            st.markdown(
                f"<div style='font-size:0.72rem;font-weight:700;color:#A8BCFF;"
                f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;"
                f"padding-bottom:6px;border-bottom:2px solid rgba(77,107,254,0.3);'>"
                f"{col_label} ({len(col_scenes)})</div>",
                unsafe_allow_html=True)

            for sc in col_scenes:
                sc_id   = str(sc["id"])
                chapter = f"Ch.{sc.get('chapter_id','?')}" if sc.get("chapter_id") else ""
                st.markdown(
                    f"<div style='background:var(--bg-card);"
                    f"border:1px solid rgba(77,107,254,0.2);border-radius:6px;"
                    f"padding:8px 10px;margin-bottom:6px;'>"
                    f"<div style='font-size:0.78rem;font-weight:600;color:var(--text-primary);'>"
                    f"Sc.{sc.get('order','')} {_html.escape(sc.get('title','')[:30])}</div>"
                    f"<div style='font-size:0.65rem;color:#6B7080;margin-top:2px;'>"
                    f"{_html.escape(sc.get('location','')[:25])} {chapter}</div></div>",
                    unsafe_allow_html=True)

                # Move buttons
                btn_row = st.columns(2)
                if col_idx > 0:
                    with btn_row[0]:
                        if st.button("←", key=f"kb_back_{sc_id}",
                                     help=f"Move to {_KANBAN_COLS[col_idx-1]}",
                                     use_container_width=True):
                            kb_state[sc_id] = _KANBAN_COLS[col_idx - 1]
                            arc["kanban"] = kb_state
                            story["plot_arc"] = arc
                            save_story(username, story)
                            st.rerun()
                if col_idx < 3:
                    with btn_row[1 if col_idx > 0 else 0]:
                        if st.button("→", key=f"kb_fwd_{sc_id}",
                                     help=f"Move to {_KANBAN_COLS[col_idx+1]}",
                                     use_container_width=True):
                            kb_state[sc_id] = _KANBAN_COLS[col_idx + 1]
                            arc["kanban"] = kb_state
                            story["plot_arc"] = arc
                            save_story(username, story)
                            st.rerun()

    # Stats
    done_count = sum(1 for s in scenes
                     if kb_state.get(str(s["id"]), "💡 Idea") == "✅ Done")
    pct = int(done_count / len(scenes) * 100) if scenes else 0
    st.markdown(
        f"<div style='margin-top:12px;font-size:0.72rem;color:#6B7080;'>"
        f"📊 {done_count}/{len(scenes)} scenes done · {pct}% complete</div>",
        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FORESHADOWING TRACKER
# ══════════════════════════════════════════════════════════════════════════════

def _show_foreshadowing(story, username):
    """Track planted foreshadowing seeds and whether they've paid off."""
    arc        = story.get("plot_arc", {})
    seeds      = arc.get("foreshadowing", [])
    changed    = False

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Track hints, clues, and setups planted in your story. "
        "Mark them paid off when the payoff appears.</div>",
        unsafe_allow_html=True)

    # Add new seed
    with st.expander("➕ Plant a new seed", expanded=len(seeds) == 0):
        seed_hint  = st.text_input("What's hinted / foreshadowed",
            placeholder="e.g. The locked drawer in father's study",
            key=f"fs_hint_{story['id']}")
        seed_where = st.text_input("Where it appears (chapter/scene)",
            placeholder="e.g. Chapter 2, when Elara arrives home",
            key=f"fs_where_{story['id']}")
        seed_payoff = st.text_input("Planned payoff (optional)",
            placeholder="e.g. Revealed to contain the forged will in Ch.12",
            key=f"fs_payoff_{story['id']}")
        seed_type = st.selectbox("Type",
            ["Chekhov's Gun", "Symbolic", "Dialogue hint", "Character behaviour",
             "Visual motif", "False clue / red herring", "Thematic echo", "Other"],
            key=f"fs_type_{story['id']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Seed", key=f"fs_add_{story['id']}",
                         use_container_width=True):
                if seed_hint.strip():
                    seeds.append({
                        "hint": seed_hint.strip(),
                        "where": seed_where.strip(),
                        "payoff": seed_payoff.strip(),
                        "type": seed_type,
                        "paid_off": False,
                    })
                    arc["foreshadowing"] = seeds
                    story["plot_arc"] = arc
                    save_story(username, story)
                    st.rerun()
        with col2:
            if st.button("✨ AI Suggest Seeds", key=f"fs_ai_{story['id']}",
                         use_container_width=True):
                with st.spinner("Generating foreshadowing ideas…"):
                    result = llm.call(
                        f"Suggest 4 specific foreshadowing seeds for this {story.get('genre','Fiction')} story.\n"
                        f"Story context: {_prose(story)}\n\n"
                        f"For each seed format as:\n"
                        f"SEED: [what to hint]\nWHERE: [when to plant it]\nPAYOFF: [planned reveal]\nTYPE: [type]\n---",
                        400)
                if result != llm.AI_UNAVAILABLE:
                    st.session_state[f"fs_ai_result_{story['id']}"] = result

    if r := st.session_state.get(f"fs_ai_result_{story['id']}"):
        st.markdown(
            f"<div style='background:var(--primary-dim);border-radius:8px;padding:12px;"
            f"font-size:0.80rem;white-space:pre-line;color:var(--text-primary);margin-bottom:10px;'>"
            f"{_html.escape(r)}</div>",
            unsafe_allow_html=True)
        if st.button("✖ Clear AI suggestions", key=f"fs_ai_clear_{story['id']}"):
            st.session_state.pop(f"fs_ai_result_{story['id']}", None)
            st.rerun()

    if not seeds:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.78rem;text-align:center;padding:16px;'>"
            "No foreshadowing seeds yet.</div>",
            unsafe_allow_html=True)
        return

    # Display seeds
    st.markdown("---")
    paid   = [s for s in seeds if s.get("paid_off")]
    unpaid = [s for s in seeds if not s.get("paid_off")]

    st.markdown(
        f"<div style='font-size:0.72rem;color:#6B7080;margin-bottom:8px;'>"
        f"🌱 {len(unpaid)} active · ✅ {len(paid)} paid off · "
        f"{len(seeds)} total</div>",
        unsafe_allow_html=True)

    for i, seed in enumerate(seeds):
        paid_off = seed.get("paid_off", False)
        border   = "rgba(52,211,153,0.35)" if paid_off else "rgba(77,107,254,0.25)"
        bg       = "rgba(52,211,153,0.05)" if paid_off else "rgba(77,107,254,0.03)"
        opacity  = "0.6" if paid_off else "1"

        st.markdown(
            f"<div style='border:1px solid {border};background:{bg};"
            f"border-radius:8px;padding:10px 12px;margin-bottom:6px;opacity:{opacity};'>"
            f"<div style='display:flex;justify-content:space-between;align-items:start;'>"
            f"<div style='font-size:0.82rem;font-weight:600;color:var(--text-primary);'>"
            f"{'✅ ' if paid_off else '🌱 '}{_html.escape(seed['hint'])}</div>"
            f"<span style='font-size:0.65rem;color:#6B7080;background:rgba(77,107,254,0.1);"
            f"border-radius:10px;padding:2px 7px;'>{_html.escape(seed.get('type',''))}</span></div>"
            f"<div style='font-size:0.72rem;color:#6B7080;margin-top:4px;line-height:1.6;'>"
            f"{'📍 ' + _html.escape(seed['where']) + '<br>' if seed.get('where') else ''}"
            f"{'💡 ' + _html.escape(seed['payoff']) if seed.get('payoff') else ''}"
            f"</div></div>",
            unsafe_allow_html=True)

        bc1, bc2 = st.columns(2)
        with bc1:
            toggle_label = "↩ Unmark" if paid_off else "✅ Mark Paid Off"
            if st.button(toggle_label, key=f"fs_toggle_{i}", use_container_width=True):
                seeds[i]["paid_off"] = not paid_off
                arc["foreshadowing"] = seeds
                story["plot_arc"] = arc
                save_story(username, story)
                st.rerun()
        with bc2:
            if st.button("🗑 Remove", key=f"fs_del_{i}", use_container_width=True):
                seeds.pop(i)
                arc["foreshadowing"] = seeds
                story["plot_arc"] = arc
                save_story(username, story)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SUBPLOT MANAGER
# ══════════════════════════════════════════════════════════════════════════════

def _show_subplots(story, username):
    arc      = story.get("plot_arc", {})
    subplots = arc.get("subplots", [])

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Track parallel storylines and their resolution status.</div>",
        unsafe_allow_html=True)

    with st.expander("➕ Add Subplot", expanded=len(subplots) == 0):
        sp_name  = st.text_input("Subplot name", key=f"sp_name_{story['id']}",
                                  placeholder="e.g. The love triangle, The missing letter")
        sp_chars = st.text_input("Characters involved", key=f"sp_chars_{story['id']}",
                                  placeholder="e.g. Elara, Daven, Lord Mors")
        sp_goal  = st.text_input("Subplot goal / tension", key=f"sp_goal_{story['id']}",
                                  placeholder="e.g. Will Elara discover the truth before the wedding?")
        sp_link  = st.text_input("How it links to main plot", key=f"sp_link_{story['id']}",
                                  placeholder="e.g. Resolves when protagonist makes Act 3 choice")
        sp_status = st.selectbox("Status",
            ["🌱 Not started", "📝 In progress", "⚡ Rising", "💥 Climax", "✅ Resolved"],
            key=f"sp_status_{story['id']}")
        if st.button("➕ Add Subplot", key=f"sp_add_{story['id']}", use_container_width=True):
            if sp_name.strip():
                subplots.append({
                    "name": sp_name.strip(),
                    "characters": sp_chars.strip(),
                    "goal": sp_goal.strip(),
                    "link": sp_link.strip(),
                    "status": sp_status,
                })
                arc["subplots"] = subplots
                story["plot_arc"] = arc
                save_story(username, story)
                st.rerun()

    status_colors = {
        "🌱 Not started": "#6B7080",
        "📝 In progress": "#60a5fa",
        "⚡ Rising":       "#fbbf24",
        "💥 Climax":       "#f87171",
        "✅ Resolved":     "#34d399",
    }

    for i, sp in enumerate(subplots):
        color = status_colors.get(sp.get("status",""), "#6B7080")
        st.markdown(
            f"<div style='border:1px solid {color}33;border-left:3px solid {color};"
            f"border-radius:0 8px 8px 0;padding:10px 12px;margin-bottom:8px;"
            f"background:rgba(0,0,0,0.1);'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div style='font-size:0.84rem;font-weight:700;color:var(--text-primary);'>"
            f"{_html.escape(sp['name'])}</div>"
            f"<span style='font-size:0.68rem;color:{color};font-weight:600;'>"
            f"{sp.get('status','')}</span></div>"
            f"<div style='font-size:0.74rem;color:#6B7080;margin-top:4px;line-height:1.6;'>"
            f"{'👥 ' + _html.escape(sp['characters']) + '<br>' if sp.get('characters') else ''}"
            f"{'🎯 ' + _html.escape(sp['goal']) + '<br>' if sp.get('goal') else ''}"
            f"{'🔗 ' + _html.escape(sp['link']) if sp.get('link') else ''}"
            f"</div></div>",
            unsafe_allow_html=True)

        bc1, bc2, bc3 = st.columns(3)
        new_statuses = list(status_colors.keys())
        cur_idx = new_statuses.index(sp["status"]) if sp["status"] in new_statuses else 0
        with bc1:
            if cur_idx < len(new_statuses) - 1:
                if st.button("→ Advance", key=f"sp_adv_{i}", use_container_width=True):
                    subplots[i]["status"] = new_statuses[cur_idx + 1]
                    arc["subplots"] = subplots
                    story["plot_arc"] = arc
                    save_story(username, story)
                    st.rerun()
        with bc2:
            new_status = st.selectbox("", new_statuses,
                index=cur_idx, key=f"sp_sel_{i}",
                label_visibility="collapsed")
            if new_status != sp["status"]:
                subplots[i]["status"] = new_status
                arc["subplots"] = subplots
                story["plot_arc"] = arc
                save_story(username, story)
                st.rerun()
        with bc3:
            if st.button("🗑 Delete", key=f"sp_del_{i}", use_container_width=True):
                subplots.pop(i)
                arc["subplots"] = subplots
                story["plot_arc"] = arc
                save_story(username, story)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# STORY SPINE (Pixar's Framework)
# ══════════════════════════════════════════════════════════════════════════════

_STORY_SPINE = [
    ("ss_once",    "Once upon a time…",        "Establish your protagonist and their world."),
    ("ss_every",   "Every day…",               "Show the protagonist's routine and what they want."),
    ("ss_until",   "Until one day…",           "The inciting incident that breaks the routine."),
    ("ss_because", "Because of that… (×3)",    "Chain of escalating consequences. Repeat 3 times."),
    ("ss_because2","Because of that… (×2)",    "Second consequence — stakes get higher."),
    ("ss_because3","Because of that… (×1)",    "Third consequence — point of no return."),
    ("ss_until2",  "Until finally…",           "The climax — the protagonist faces the ultimate challenge."),
    ("ss_since",   "Ever since then…",         "The new normal. What has permanently changed?"),
]

def _show_story_spine(story, username):
    arc = story.get("plot_arc", {})

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Pixar's storytelling backbone. Used for every Pixar film — forces a cause-and-effect chain "
        "that makes stories feel inevitable and satisfying.</div>",
        unsafe_allow_html=True)

    changed = False

    # Visual spine diagram
    done = sum(1 for key, *_ in _STORY_SPINE if arc.get(f"{key}_text", "").strip())
    pct  = int(done / len(_STORY_SPINE) * 100)
    st.markdown(
        f"<div style='background:rgba(77,107,254,0.08);border-radius:8px;padding:10px 14px;"
        f"margin-bottom:14px;display:flex;align-items:center;gap:12px;'>"
        f"<div style='font-size:1.6rem;'>🎬</div>"
        f"<div><div style='font-size:0.82rem;font-weight:700;color:#A8BCFF;'>"
        f"Story Spine Progress</div>"
        f"<div style='font-size:0.70rem;color:#6B7080;'>{done}/{len(_STORY_SPINE)} beats filled · {pct}% complete</div></div>"
        f"<div style='flex:1;'><div style='background:rgba(77,107,254,0.15);border-radius:4px;height:6px;'>"
        f"<div style='background:{'#34d399' if pct==100 else '#4D6BFE'};width:{pct}%;height:6px;border-radius:4px;'>"
        f"</div></div></div></div>",
        unsafe_allow_html=True)

    for i, (key, label, desc) in enumerate(_STORY_SPINE):
        text_key = f"{key}_text"
        existing = arc.get(text_key, "")
        filled   = bool(existing.strip())

        # Connector line between beats
        if i > 0:
            st.markdown(
                "<div style='display:flex;justify-content:center;margin:2px 0;'>"
                "<div style='width:2px;height:14px;background:rgba(77,107,254,0.25);'></div></div>",
                unsafe_allow_html=True)

        col1, col2 = st.columns([5, 1])
        with col1:
            icon = "✅" if filled else "○"
            color = "#34d399" if filled else "#6B7080"
            st.markdown(
                f"<div style='font-size:0.80rem;font-weight:700;color:{color};"
                f"margin-bottom:3px;'>{icon} {label}</div>"
                f"<div style='font-size:0.68rem;color:#6B7080;margin-bottom:4px;'>{desc}</div>",
                unsafe_allow_html=True)
            text = st.text_area(
                "", value=existing, placeholder=f"Write your {label.lower()} beat here…",
                key=f"ss_{story['id']}_{key}", height=68,
                label_visibility="collapsed")
            if text != existing:
                arc[text_key] = text; changed = True
        with col2:
            if st.button("✨", key=f"ss_ai_{story['id']}_{key}",
                         help="AI suggest", use_container_width=True):
                # Build context from filled beats
                context_parts = []
                for pk, pl, _ in _STORY_SPINE:
                    prev_text = arc.get(f"{pk}_text", "").strip()
                    if prev_text:
                        context_parts.append(f"{pl}: {prev_text}")
                context = "\n".join(context_parts[:i]) or _prose(story)

                with st.spinner(""):
                    result = llm.call(
                        f"Complete this Story Spine beat for a {story.get('genre','Fiction')} story "
                        f"titled '{story.get('title','')}'.\n\n"
                        f"Previous beats:\n{context}\n\n"
                        f"Write the '{label}' beat in 1-2 sentences. "
                        f"Be specific to this story. Start directly with the content, no preamble.", 120)
                if result != llm.AI_UNAVAILABLE:
                    arc[text_key] = result; changed = True
                    st.rerun()

    if changed:
        story["plot_arc"] = arc
        save_story(username, story)

    # Export spine as prose
    st.markdown("---")
    if st.button("📋 Generate Story Spine Summary", key=f"ss_export_{story['id']}",
                 use_container_width=True):
        beats = []
        for key, label, _ in _STORY_SPINE:
            text = arc.get(f"{key}_text", "").strip()
            if text:
                beats.append(f"**{label}** {text}")
        if beats:
            summary = "\n\n".join(beats)
            st.markdown(
                f"<div style='background:var(--bg-card);border:1px solid rgba(77,107,254,0.2);"
                f"border-radius:8px;padding:14px;font-size:0.80rem;line-height:1.7;"
                f"color:var(--text-primary);white-space:pre-line;'>{_html.escape(summary)}</div>",
                unsafe_allow_html=True)
        else:
            st.caption("Fill in at least one beat to generate a summary.")


# ══════════════════════════════════════════════════════════════════════════════
# CONFLICT ESCALATION CURVE
# ══════════════════════════════════════════════════════════════════════════════

def _show_conflict_escalation(story, username):
    """Visual conflict intensity curve across story beats."""
    arc      = story.get("plot_arc", {})
    scenes   = load_scenes(username, story["id"])
    chapters = load_chapters(username, story["id"])

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:14px;'>"
        "Rate the conflict intensity at each story beat. "
        "A good escalation curve rises steadily with strategic dips for recovery beats.</div>",
        unsafe_allow_html=True)

    # Define default beat points (use scenes if available, else story arc points)
    if scenes:
        beat_labels = [s.get("title", f"Scene {i+1}")[:20] for i, s in enumerate(scenes[:12])]
        beat_key    = "scene_conflicts"
    else:
        beat_labels = [label for _, label, _, _ in _THREE_ACT]
        beat_key    = "arc_conflicts"

    conflicts = arc.get(beat_key, {})

    # Sliders for each beat
    st.markdown("**Set conflict intensity (1=calm, 10=maximum tension):**")

    cols_per_row = 3
    beat_items   = list(enumerate(beat_labels))

    for row_start in range(0, len(beat_items), cols_per_row):
        row = beat_items[row_start:row_start+cols_per_row]
        cols = st.columns(len(row))
        changed = False
        for ci, (i, label) in enumerate(row):
            with cols[ci]:
                val = st.slider(
                    label, 1, 10,
                    value=conflicts.get(str(i), 5),
                    key=f"ce_{story['id']}_{i}")
                if val != conflicts.get(str(i), 5):
                    conflicts[str(i)] = val
                    changed = True
        if changed:
            arc[beat_key] = conflicts
            story["plot_arc"] = arc
            save_story(username, story)

    # Build SVG curve
    n = len(beat_labels)
    values = [conflicts.get(str(i), 5) for i in range(n)]

    if n >= 2:
        w, h = 500, 120
        pad_x, pad_y = 30, 16

        # Grid lines
        svg_parts = []
        for level in [2, 5, 8, 10]:
            y = h - pad_y - (level - 1) / 9 * (h - 2*pad_y)
            svg_parts.append(
                f'<line x1="{pad_x}" y1="{y:.1f}" x2="{w-pad_x}" y2="{y:.1f}" '
                f'stroke="rgba(107,112,128,0.2)" stroke-width="1" stroke-dasharray="3,3"/>'
                f'<text x="{pad_x-4}" y="{y+4:.1f}" font-size="8" fill="#6B7080" '
                f'text-anchor="end" font-family="monospace">{level}</text>')

        # Area fill + line
        pts = []
        for i, v in enumerate(values):
            x = pad_x + i * (w - 2*pad_x) / max(n-1, 1)
            y = h - pad_y - (v - 1) / 9 * (h - 2*pad_y)
            pts.append((x, y))

        path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        area_d = path_d + f" L {pts[-1][0]:.1f},{h-pad_y} L {pts[0][0]:.1f},{h-pad_y} Z"

        # Color by intensity
        def _intensity_color(v):
            if v <= 3:  return "#4ADE80"
            if v <= 6:  return "#fbbf24"
            return "#f87171"

        svg_parts.append(
            f'<path d="{area_d}" fill="rgba(248,113,113,0.08)"/>'
            f'<path d="{path_d}" stroke="#f87171" stroke-width="2.5" fill="none" '
            f'stroke-linejoin="round" stroke-linecap="round"/>')

        # Dots + labels
        for i, (x, y) in enumerate(pts):
            v = values[i]
            c = _intensity_color(v)
            svg_parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{c}" stroke="#0D0E14" stroke-width="1.5"/>'
                f'<text x="{x:.1f}" y="{h:.1f}" font-size="7" fill="#6B7080" '
                f'text-anchor="middle" font-family="Inter,sans-serif">'
                f'{beat_labels[i][:8]}</text>')

        svg = (f'<svg width="{w}" height="{h+10}" xmlns="http://www.w3.org/2000/svg" '
               f'style="overflow:visible;max-width:100%;">'
               + "".join(svg_parts) + "</svg>")

        st.markdown(svg, unsafe_allow_html=True)

        # Curve feedback
        max_v    = max(values)
        min_v    = min(values)
        last_3   = values[-3:]
        climax_i = values.index(max_v)

        feedback = []
        if max_v < 7:
            feedback.append(("⚠️", "Peak intensity is low ({}/10). Consider raising the stakes.".format(max_v), "#fbbf24"))
        if climax_i < n * 0.6:
            feedback.append(("⚠️", "Climax appears too early (beat {}). Usually best at 75-90%.".format(climax_i+1), "#fbbf24"))
        if all(v == values[0] for v in values):
            feedback.append(("❌", "All beats at same intensity — no escalation or variation.", "#f87171"))
        if min_v >= 7:
            feedback.append(("💡", "No recovery beats. Add a calm scene to let readers breathe.", "#60a5fa"))
        if not feedback:
            feedback.append(("✅", "Good escalation curve — varied intensity with a strong climax.", "#34d399"))

        for icon, msg, color in feedback:
            st.markdown(
                f"<div style='font-size:0.76rem;color:{color};margin-top:6px;'>"
                f"{icon} {msg}</div>",
                unsafe_allow_html=True)

    # AI analyse button
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    if st.button("🤖 AI Analyse My Conflict Curve", key=f"ce_ai_{story['id']}",
                 use_container_width=True):
        beats_summary = "\n".join(
            f"Beat {i+1} '{beat_labels[i]}': {values[i]}/10"
            for i in range(len(beat_labels)))
        with st.spinner("Analysing conflict curve…"):
            result = llm.call(
                f"Analyse this conflict escalation curve for a {story.get('genre','Fiction')} story "
                f"titled '{story.get('title','Untitled')}':\n\n{beats_summary}\n\n"
                f"Identify: (1) Is the escalation effective? (2) Where is the climax placed? "
                f"(3) Are there good recovery beats? (4) One specific suggestion to improve it. "
                f"Be concise and specific.", 250)
        if result != llm.AI_UNAVAILABLE:
            st.markdown(
                f"<div style='background:rgba(77,107,254,0.07);border-radius:8px;"
                f"padding:12px;font-size:0.80rem;color:var(--text-primary);margin-top:8px;'>"
                f"{_html.escape(result)}</div>",
                unsafe_allow_html=True)
        else:
            st.warning("AI unavailable. Check Ollama is running.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

def show_plot_tools(story, username):
    """Full plot development tools panel."""
    tabs = st.tabs([
        "🎬 Three-Act", "🗺 Hero's Journey", "🐱 Save the Cat",
        "🎯 Story Spine", "📈 Conflict Curve",
        "📋 Kanban", "🌱 Foreshadowing", "🕸 Subplots"
    ])
    with tabs[0]: _show_three_act(story, username)
    with tabs[1]: _show_heros_journey(story, username)
    with tabs[2]: _show_save_the_cat(story, username)
    with tabs[3]: _show_story_spine(story, username)
    with tabs[4]: _show_conflict_escalation(story, username)
    with tabs[5]: _show_kanban(story, username)
    with tabs[6]: _show_foreshadowing(story, username)
    with tabs[7]: _show_subplots(story, username)
