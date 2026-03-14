"""
NarrativeForge — AI Creative Suite
Extended AI tools: name generators, plot twist engine, dialogue improver,
scene rewriter, brainstorming partner, query letter generator, synopsis writer.
"""
import os
import html as _html
import requests
import streamlit as st
import llm

llm.AI_UNAVAILABLE = "_llm.AI_UNAVAILABLE__"



def _ai_error():
    st.error("⚠️ AI unavailable — is Ollama running?")


# ── Name Generators ───────────────────────────────────────────────────────
def _show_name_generator(story, ctx=""):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:8px;'>🧑 Character Name Generator</div>",
        unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        culture = st.selectbox("Culture / Origin",
            ["Fantasy", "Medieval European", "Japanese", "Norse", "Arabic",
             "Celtic", "Sci-Fi", "Latin American", "African", "Slavic"],
            key=f"ait_name_culture_{ctx}")
    with col2:
        n_names = st.selectbox("How many?", [5, 10, 20], key=f"ait_name_count_{ctx}")
    gender = st.selectbox("Gender feel", ["Any", "Masculine", "Feminine", "Neutral"],
                          key=f"ait_name_gender_{ctx}")

    if st.button("✨ Generate Names", key=f"ait_gen_names_{ctx}", use_container_width=True):
        prompt = (f"Generate {n_names} {gender.lower()} character names suitable for a "
                  f"{culture} setting in a {story.get('genre','Fantasy')} story. "
                  f"For each name give: Name | Pronunciation | Brief meaning/feel. "
                  f"Format as a simple list. Names should feel distinct and memorable.")
        with st.spinner("Generating names…"):
            result = llm.call(prompt, 400)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state["ait_names_result"] = result

    if r := st.session_state.get("ait_names_result"):
        st.markdown(
            f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
            f"border-radius:8px;padding:12px;font-size:0.82rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;'>{_html.escape(r)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key=f"ait_clear_names_{ctx}"):
            st.session_state.pop("ait_names_result", None)
            st.rerun()

    st.markdown("<div style='margin:12px 0;border-top:1px solid var(--primary-border);'></div>",
                unsafe_allow_html=True)

    # Place names
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:8px;'>🗺️ Place Name Generator</div>",
        unsafe_allow_html=True)
    place_type = st.selectbox("Place type",
        ["City / Town", "Village", "Forest", "Mountain", "River", "Castle",
         "Magic Academy", "Tavern / Inn", "Island", "Dungeon", "Planet", "Space Station"],
        key=f"ait_place_type_{ctx}")
    if st.button("✨ Generate Places", key=f"ait_gen_places_{ctx}", use_container_width=True):
        prompt = (f"Generate 8 evocative place names for a {place_type} in a "
                  f"{story.get('genre','Fantasy')} story. For each: Name | Brief evocative description (1 sentence). "
                  f"Make each name unique, pronounceable, and fitting for the genre.")
        with st.spinner("Generating place names…"):
            result = llm.call(prompt, 300)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state["ait_places_result"] = result

    if r := st.session_state.get("ait_places_result"):
        st.markdown(
            f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
            f"border-radius:8px;padding:12px;font-size:0.82rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;'>{_html.escape(r)}</div>",
            unsafe_allow_html=True)


# ── Plot Twist Engine ─────────────────────────────────────────────────────
def _show_plot_twist_engine(story, characters, ctx=""):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:8px;'>🌀 Plot Twist Engine</div>",
        unsafe_allow_html=True)
    twist_type = st.selectbox("Twist type",
        ["Shocking Revelation", "Betrayal", "Identity Reversal",
         "Hidden Connection", "Unexpected Alliance", "Tragic Irony",
         "Time / Reality Shift", "The Villain Was Right", "Surprise"],
        key=f"ait_twist_type_{ctx}")
    intensity = st.select_slider("Intensity", ["Subtle", "Medium", "Dramatic", "Mind-blowing"],
                                 value="Dramatic", key=f"ait_twist_intensity_{ctx}")

    recent = " ".join(
        m["content"] for m in story.get("messages", [])[-8:]
        if m.get("role") == "assistant")[:600]
    char_names = ", ".join(c["name"] for c in characters) if characters else "the protagonist"

    if st.button("🌀 Generate 3 Twists", key=f"ait_gen_twists_{ctx}", use_container_width=True):
        prompt = (f"For this {story.get('genre','Fiction')} story with characters ({char_names}), "
                  f"generate 3 {intensity.lower()} '{twist_type}' plot twists. "
                  f"Recent story context: {recent}\n\n"
                  f"For each twist: give a 2-sentence description, then explain the emotional impact. "
                  f"Number them 1, 2, 3. Make them feel earned, not random.")
        with st.spinner("Generating twists…"):
            result = llm.call(prompt, 500)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state["ait_twists_result"] = result

    if r := st.session_state.get("ait_twists_result"):
        st.markdown(
            f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
            f"border-radius:8px;padding:12px;font-size:0.82rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;'>{_html.escape(r)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key=f"ait_clear_twists_{ctx}"):
            st.session_state.pop("ait_twists_result", None)
            st.rerun()


# ── Dialogue Improver ─────────────────────────────────────────────────────
def _show_dialogue_improver(story, characters, ctx=""):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:8px;'>💬 Dialogue Improver</div>",
        unsafe_allow_html=True)
    raw_dialogue = st.text_area("Paste dialogue to improve",
        placeholder='"I want to go to the market," she said.\n"No, you cannot," he replied.',
        height=120, key=f"ait_dialogue_input_{ctx}")
    style = st.selectbox("Improve for",
        ["Subtext & Tension", "Character Voice", "More Natural",
         "More Dramatic", "Period Authentic", "Funnier"],
        key=f"ait_dialogue_style_{ctx}")
    char_context = ", ".join(
        f"{c['name']} ({c.get('role','')})" for c in characters
    ) if characters else "unnamed characters"

    if raw_dialogue and st.button("💬 Improve Dialogue", key=f"ait_improve_dialogue_{ctx}",
                                  use_container_width=True):
        prompt = (f"Improve this dialogue from a {story.get('genre','Fiction')} story. "
                  f"Characters: {char_context}. "
                  f"Goal: make it {style.lower()}. Rewrite the dialogue keeping "
                  f"the same basic exchange but with significantly better craft. "
                  f"Show only the rewritten dialogue, no commentary.\n\n"
                  f"Original:\n{raw_dialogue}")
        with st.spinner("Improving dialogue…"):
            result = llm.call(prompt, 400)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state["ait_dialogue_result"] = result

    if r := st.session_state.get("ait_dialogue_result"):
        st.markdown(
            f"<div style='background:rgba(52,211,153,0.07);border:1px solid rgba(52,211,153,0.25);"
            f"border-radius:8px;padding:12px;font-size:0.84rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;'>{_html.escape(r)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key=f"ait_clear_dialogue_{ctx}"):
            st.session_state.pop("ait_dialogue_result", None)
            st.rerun()


# ── Scene POV Rewriter ────────────────────────────────────────────────────
def _show_scene_rewriter(story, characters, ctx=""):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:8px;'>🔄 Scene POV / Tense Rewriter</div>",
        unsafe_allow_html=True)
    scene_text = st.text_area("Paste a scene to rewrite",
        height=120, key=f"ait_scene_input_{ctx}",
        placeholder="Paste 1-3 paragraphs from your story…")
    col1, col2 = st.columns(2)
    with col1:
        new_pov = st.selectbox("Change POV to",
            ["Keep same", "First Person", "Second Person", "Third Person Limited",
             "Third Person Omniscient"], key=f"ait_scene_pov_{ctx}")
    with col2:
        new_tense = st.selectbox("Change tense to",
            ["Keep same", "Present", "Past", "Future"], key=f"ait_scene_tense_{ctx}")

    if scene_text and st.button("🔄 Rewrite Scene", key=f"ait_rewrite_scene_{ctx}",
                                use_container_width=True):
        changes = []
        if new_pov != "Keep same":  changes.append(f"{new_pov} POV")
        if new_tense != "Keep same": changes.append(f"{new_tense} tense")
        if not changes: changes = ["better prose quality"]
        prompt = (f"Rewrite this scene in {', '.join(changes)}. "
                  f"Genre: {story.get('genre','Fiction')}. "
                  f"Preserve all plot events, character actions, and meaning. "
                  f"Return only the rewritten scene, no commentary.\n\n{scene_text}")
        with st.spinner("Rewriting scene…"):
            result = llm.call(prompt, 600)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state["ait_scene_result"] = result

    if r := st.session_state.get("ait_scene_result"):
        st.markdown(
            f"<div style='background:rgba(251,191,36,0.07);border:1px solid rgba(251,191,36,0.25);"
            f"border-radius:8px;padding:12px;font-size:0.84rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;'>{_html.escape(r)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key=f"ait_clear_scene_{ctx}"):
            st.session_state.pop("ait_scene_result", None)
            st.rerun()


# ── Brainstorming Partner ─────────────────────────────────────────────────
def _show_brainstorm(story, characters, ctx=""):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:8px;'>🧩 Brainstorming Partner</div>",
        unsafe_allow_html=True)
    # Simple multi-turn brainstorm in session state
    bkey = f"brainstorm_{story['id']}"
    if bkey not in st.session_state:
        st.session_state[bkey] = []

    for msg in st.session_state[bkey]:
        role_label = "You" if msg["role"] == "user" else "◆ NarrativeForge"
        color = "#4D6BFE" if msg["role"] == "user" else "#34d399"
        st.markdown(
            f"<div style='margin-bottom:8px;'>"
            f"<div style='font-size:0.68rem;color:{color};font-weight:700;margin-bottom:2px;'>"
            f"{role_label}</div>"
            f"<div style='font-size:0.82rem;color:var(--text-primary);line-height:1.6;"
            f"white-space:pre-wrap;'>{_html.escape(msg['content'])}</div>"
            f"</div>",
            unsafe_allow_html=True)

    user_input = st.text_input("Ask anything about your story…",
                               key=f"brainstorm_input_{story['id']}",
                               placeholder="e.g. How do I make the villain more sympathetic?")
    col1, col2 = st.columns([3, 1])
    with col1:
        send = st.button("💬 Ask", key=f"brainstorm_send_{story['id']}",
                         use_container_width=True)
    with col2:
        if st.button("🗑 Clear", key=f"brainstorm_clear_{story['id']}",
                     use_container_width=True):
            st.session_state[bkey] = []
            st.rerun()

    if send and user_input.strip():
        st.session_state[bkey].append({"role": "user", "content": user_input.strip()})
        char_names = ", ".join(c["name"] for c in characters) if characters else "no characters yet"
        recent_prose = " ".join(
            m["content"] for m in story.get("messages", [])[-6:]
            if m.get("role") == "assistant")[:400]
        history = "\n".join(
            f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
            for m in st.session_state[bkey][-8:])
        system = (f"You are a creative writing partner helping with a {story.get('genre','Fiction')} "
                  f"story titled '{story.get('title','Untitled')}'. "
                  f"Characters: {char_names}. "
                  f"Recent story: {recent_prose}\n\n"
                  f"Give practical, specific, enthusiastic advice. Be concise (3-5 sentences).")
        prompt = f"{system}\n\nConversation:\n{history}\nAssistant:"
        with st.spinner("Thinking…"):
            result = llm.call(prompt, 300)
        if result == llm.AI_UNAVAILABLE:
            st.session_state[bkey].pop()
            _ai_error()
        else:
            st.session_state[bkey].append({"role": "assistant", "content": result})
            st.rerun()


# ── Query Letter & Synopsis ────────────────────────────────────────────────
def _show_publishing_tools(story, characters, ctx=""):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
        "margin-bottom:8px;'>📬 Publishing Tools</div>",
        unsafe_allow_html=True)

    tab_q, tab_s = st.tabs(["📝 Query Letter", "📄 Synopsis"])

    with tab_q:
        if st.button("📝 Generate Query Letter", key=f"ait_query_{ctx}", use_container_width=True):
            char_desc = "; ".join(
                f"{c['name']} ({c.get('description','')[:60]})"
                for c in characters[:3]) if characters else "protagonist"
            prose_sample = " ".join(
                m["content"] for m in story.get("messages", [])[:6]
                if m.get("role") == "assistant")[:400]
            prompt = (f"Write a professional 300-word query letter for a literary agent "
                      f"for this {story.get('genre','Fiction')} story:\n\n"
                      f"Title: {story.get('title','Untitled')}\n"
                      f"Characters: {char_desc}\n"
                      f"Story opening: {prose_sample}\n\n"
                      f"Include: hook, plot summary, stakes, word count estimate, "
                      f"genre/comp titles note, brief bio line. Professional tone.")
            with st.spinner("Writing query letter…"):
                result = llm.call(prompt, 500)
            if result == llm.AI_UNAVAILABLE:
                _ai_error()
            else:
                st.session_state["ait_query_result"] = result
        if r := st.session_state.get("ait_query_result"):
            st.text_area("Query Letter", value=r, height=280, key=f"ait_query_display_{ctx}")
            if st.button("🗑 Clear", key=f"ait_clr_query_{ctx}"):
                st.session_state.pop("ait_query_result", None)
                st.rerun()

    with tab_s:
        if st.button("📄 Generate Synopsis", key=f"ait_synopsis_{ctx}", use_container_width=True):
            all_prose = " ".join(
                m["content"] for m in story.get("messages", [])
                if m.get("role") == "assistant")[:1200]
            char_desc = "; ".join(
                f"{c['name']} ({c.get('role','')})" for c in characters
            ) if characters else "protagonist"
            prompt = (f"Write a one-page synopsis (400 words) for this {story.get('genre','Fiction')} story. "
                      f"Characters: {char_desc}\n\nStory content: {all_prose}\n\n"
                      f"Structure: setup, inciting incident, escalating conflicts, climax, resolution. "
                      f"Third person, past tense. Reveal the ending.")
            with st.spinner("Writing synopsis…"):
                result = llm.call(prompt, 600)
            if result == llm.AI_UNAVAILABLE:
                _ai_error()
            else:
                st.session_state["ait_synopsis_result"] = result
        if r := st.session_state.get("ait_synopsis_result"):
            st.text_area("Synopsis", value=r, height=280, key=f"ait_synopsis_display_{ctx}")
            if st.button("🗑 Clear", key=f"ait_clr_synopsis_{ctx}"):
                st.session_state.pop("ait_synopsis_result", None)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

def show_ai_tools_panel(story, characters, ctx=""):
    """Full AI Tools panel — 6 sub-sections."""
    tool_tabs = st.tabs([
        "🧑 Names", "🌀 Twists", "💬 Dialogue",
        "🔄 Scene", "🧩 Brainstorm", "📬 Publish"
    ])
    with tool_tabs[0]: _show_name_generator(story, ctx=ctx)
    with tool_tabs[1]: _show_plot_twist_engine(story, characters, ctx=ctx)
    with tool_tabs[2]: _show_dialogue_improver(story, characters, ctx=ctx)
    with tool_tabs[3]: _show_scene_rewriter(story, characters, ctx=ctx)
    with tool_tabs[4]: _show_brainstorm(story, characters, ctx=ctx)
    with tool_tabs[5]: _show_publishing_tools(story, characters, ctx=ctx)
