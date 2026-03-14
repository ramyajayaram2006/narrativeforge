"""
NarrativeForge — Character Development Suite
Family tree generator, backstory generator, motivation analyser,
character voice simulator, appearance generator.
"""
import os
import html as _html
import re
import requests
import streamlit as st
import llm

llm.AI_UNAVAILABLE = "_llm.AI_UNAVAILABLE__"



def _ai_error():
    st.error("⚠️ AI unavailable — is Ollama running?")


# ── Family Tree ────────────────────────────────────────────────────────────
def _show_family_tree(characters):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;margin-bottom:8px;'>"
        "🌳 Family / Relationship Tree</div>", unsafe_allow_html=True)

    if not characters:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;'>Add characters first.</div>",
            unsafe_allow_html=True)
        return

    # Let user define relationships between characters
    rel_key = "char_suite_rels"
    if rel_key not in st.session_state:
        st.session_state[rel_key] = {}

    rels = st.session_state[rel_key]
    char_names = [c["name"] for c in characters]

    with st.expander("➕ Add relationship", expanded=len(rels) == 0):
        c1, c2, c3 = st.columns(3)
        with c1:
            char_a = st.selectbox("Character A", char_names, key="ft_a")
        with c2:
            rel_type = st.selectbox("Relationship",
                ["Parent of", "Child of", "Sibling of", "Married to", "Enemy of",
                 "Mentor of", "Rival of", "Friend of", "In love with", "Betrayed by",
                 "Ally of", "Master of", "Servant of", "Unknown to"],
                key="ft_rel")
        with c3:
            char_b = st.selectbox("Character B", char_names, key="ft_b")
        if st.button("➕ Add", key="ft_add", use_container_width=True):
            rel_id = f"{char_a}→{char_b}"
            rels[rel_id] = {"a": char_a, "rel": rel_type, "b": char_b}
            st.session_state[rel_key] = rels
            st.rerun()

    if not rels:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.78rem;padding:12px;'>No relationships defined yet.</div>",
            unsafe_allow_html=True)
        return

    # Render tree as HTML graph
    # Collect nodes and edges
    nodes = set()
    edges = []
    for rel_id, r in rels.items():
        nodes.add(r["a"]); nodes.add(r["b"])
        edges.append(r)

    # Assign colours to each character
    colours = ["#4D6BFE", "#f87171", "#fbbf24", "#34d399", "#a78bfa",
               "#fb923c", "#60a5fa", "#f472b6", "#2dd4bf", "#818cf8"]
    node_list = sorted(nodes)
    node_colour = {n: colours[i % len(colours)] for i, n in enumerate(node_list)}

    # Build SVG-style HTML tree
    rows = []
    rows.append(
        "<div style='overflow-x:auto;'>"
        "<table style='border-collapse:separate;border-spacing:0;width:100%;'>")

    # Simple list layout
    for r in edges:
        ca, rel, cb = r["a"], r["rel"], r["b"]
        col_a = node_colour.get(ca, "#4D6BFE")
        col_b = node_colour.get(cb, "#4D6BFE")
        rows.append(
            f"<tr>"
            f"<td style='padding:4px 8px;'>"
            f"<span style='background:{col_a};color:#fff;border-radius:20px;"
            f"padding:3px 10px;font-size:0.78rem;font-weight:600;white-space:nowrap;'>"
            f"{_html.escape(ca)}</span></td>"
            f"<td style='padding:4px 8px;text-align:center;'>"
            f"<span style='font-size:0.70rem;color:#6B7080;white-space:nowrap;'>"
            f"── {_html.escape(rel)} ──▶</span></td>"
            f"<td style='padding:4px 8px;'>"
            f"<span style='background:{col_b};color:#fff;border-radius:20px;"
            f"padding:3px 10px;font-size:0.78rem;font-weight:600;white-space:nowrap;'>"
            f"{_html.escape(cb)}</span></td>"
            f"<td style='padding:4px 4px;'>")

        # Delete button placeholder (rendered after)
        rows.append("</td></tr>")

    rows.append("</table></div>")
    st.markdown("".join(rows), unsafe_allow_html=True)

    # Delete buttons
    to_delete = None
    for rel_id in list(rels.keys()):
        r = rels[rel_id]
        if st.button(f"🗑 {r['a']} {r['rel']} {r['b']}",
                     key=f"ft_del_{rel_id}", use_container_width=True):
            to_delete = rel_id
    if to_delete:
        del rels[to_delete]
        st.session_state[rel_key] = rels
        st.rerun()


# ── Backstory Generator ────────────────────────────────────────────────────
def _show_backstory_generator(story, characters):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;margin-bottom:8px;'>"
        "📜 Backstory Generator</div>", unsafe_allow_html=True)

    if not characters:
        st.caption("Add characters to generate backstories.")
        return

    char_names = [c["name"] for c in characters]
    selected = st.selectbox("Character", char_names, key="bs_char")
    char = next((c for c in characters if c["name"] == selected), characters[0])

    depth = st.select_slider("Depth",
        ["Brief (1 para)", "Standard (3 para)", "Detailed (5 para)", "Deep Dive (8 para)"],
        value="Standard (3 para)", key="bs_depth")
    include = st.multiselect("Include",
        ["Childhood trauma", "First love", "Career / training", "Family secrets",
         "Defining failure", "Moment of triumph", "Hidden shame", "Secret skill"],
        default=["Childhood trauma", "Defining failure"],
        key="bs_include")

    if st.button("📜 Generate Backstory", key="bs_gen", use_container_width=True):
        paras = {"Brief": 1, "Standard": 3, "Detailed": 5, "Deep Dive": 8}[depth.split()[0]]
        include_str = (", ".join(include)) if include else "key life events"
        prompt = (
            f"Write a {paras}-paragraph backstory for a character in a {story.get('genre','Fiction')} story:\n\n"
            f"Name: {char['name']}\n"
            f"Role: {char.get('role','')}\n"
            f"Description: {char.get('description','')}\n"
            f"Speaking style: {char.get('speaking_style','')}\n\n"
            f"Include: {include_str}.\n"
            f"Write in third person, past tense. Make it vivid and specific. "
            f"Each paragraph should reveal something that explains who they are NOW in the story. "
            f"End with a defining moment that set them on their current path."
        )
        with st.spinner("Writing backstory…"):
            result = llm.call(prompt, paras * 120)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state[f"bs_result_{char['name']}"] = result

    result = st.session_state.get(f"bs_result_{char['name']}")
    if result:
        st.markdown(
            f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
            f"border-radius:8px;padding:14px;font-size:0.82rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;'>{_html.escape(result)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key=f"bs_clear_{char['name']}"):
            st.session_state.pop(f"bs_result_{char['name']}", None)
            st.rerun()


# ── Motivation Analyser ────────────────────────────────────────────────────
def _show_motivation_analyser(story, characters):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;margin-bottom:8px;'>"
        "🎯 Motivation Analyser</div>", unsafe_allow_html=True)

    if not characters:
        st.caption("Add characters to analyse motivations.")
        return

    char_names = [c["name"] for c in characters]
    selected   = st.selectbox("Character", char_names, key="mot_char")
    char       = next((c for c in characters if c["name"] == selected), characters[0])

    prose = " ".join(
        m["content"] for m in story.get("messages", [])[-12:]
        if m.get("role") == "assistant")[:800]

    if st.button("🎯 Analyse Motivation", key="mot_run", use_container_width=True):
        prompt = (
            f"Analyse the motivations of '{char['name']}' in this {story.get('genre','Fiction')} story.\n\n"
            f"Character: {char.get('description','')}\n"
            f"Arc notes: {char.get('arc_notes','')}\n"
            f"Recent story events: {prose}\n\n"
            f"Provide analysis in this exact format:\n"
            f"SURFACE GOAL: (what they say they want)\n"
            f"DEEP DESIRE: (what they truly want)\n"
            f"FEAR: (what they're afraid of)\n"
            f"WOUND: (past event driving current behaviour)\n"
            f"BELIEF: (false belief they hold about the world)\n"
            f"GHOST: (unresolved past haunting them)\n"
            f"CONTRADICTION: (where their actions conflict with stated goals)\n"
            f"GROWTH ARC: (how they need to change by the end)\n\n"
            f"Be specific and analytical. Base it on evidence from the story."
        )
        with st.spinner("Analysing…"):
            result = llm.call(prompt, 400)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state[f"mot_result_{char['name']}"] = result

    result = st.session_state.get(f"mot_result_{char['name']}")
    if result:
        _LABELS = {
            "SURFACE GOAL":  "#60a5fa",
            "DEEP DESIRE":   "#a78bfa",
            "FEAR":          "#f87171",
            "WOUND":         "#fb923c",
            "BELIEF":        "#fbbf24",
            "GHOST":         "#94a3b8",
            "CONTRADICTION": "#f472b6",
            "GROWTH ARC":    "#34d399",
        }
        lines = result.split("\n")
        parsed = {}
        for line in lines:
            for label in _LABELS:
                if line.upper().startswith(label + ":"):
                    parsed[label] = line[len(label)+1:].strip()
                    break

        if parsed:
            for label, value in parsed.items():
                color = _LABELS.get(label, "#4D6BFE")
                st.markdown(
                    f"<div style='border-left:3px solid {color};padding:6px 12px;"
                    f"margin-bottom:6px;background:var(--primary-dim);border-radius:0 6px 6px 0;'>"
                    f"<div style='font-size:0.68rem;color:{color};font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;'>"
                    f"{_html.escape(label)}</div>"
                    f"<div style='font-size:0.80rem;color:var(--text-primary);line-height:1.5;'>"
                    f"{_html.escape(value)}</div></div>",
                    unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='background:var(--primary-dim);border-radius:8px;padding:12px;"
                f"font-size:0.82rem;white-space:pre-line;color:var(--text-primary);'>"
                f"{_html.escape(result)}</div>",
                unsafe_allow_html=True)

        if st.button("🗑 Clear", key=f"mot_clear_{char['name']}"):
            st.session_state.pop(f"mot_result_{char['name']}", None)
            st.rerun()


# ── Voice Simulator ───────────────────────────────────────────────────────
def _show_voice_simulator(story, characters):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;margin-bottom:8px;'>"
        "🎭 Voice Simulator</div>", unsafe_allow_html=True)

    if not characters:
        st.caption("Add characters first.")
        return

    char_names = [c["name"] for c in characters]
    selected   = st.selectbox("Character", char_names, key="vs_char")
    char       = next((c for c in characters if c["name"] == selected), characters[0])

    situation  = st.text_input("Situation / what they need to say",
        placeholder="e.g. They discover their mentor has been lying to them",
        key="vs_situation")
    emotion    = st.selectbox("Emotional state",
        ["Angry", "Afraid", "Hopeful", "Desperate", "Calm", "Grief-stricken",
         "Determined", "Confused", "Joyful", "Betrayed", "Exhausted", "Triumphant"],
        key="vs_emotion")

    if situation and st.button("🎭 Generate Dialogue", key="vs_gen",
                               use_container_width=True):
        prose_sample = " ".join(
            m["content"] for m in story.get("messages", [])
            if m.get("role") == "assistant")[:400]
        prompt = (
            f"Write 3-5 lines of dialogue spoken by '{char['name']}' in this exact situation:\n"
            f"'{situation}'\n\n"
            f"Character details:\n"
            f"- Role: {char.get('role','')}\n"
            f"- Description: {char.get('description','')}\n"
            f"- Speaking style: {char.get('speaking_style','')}\n"
            f"- Arc notes: {char.get('arc_notes','')}\n"
            f"- Current emotion: {emotion}\n\n"
            f"Story genre: {story.get('genre','Fiction')}\n"
            f"Story context: {prose_sample[:200]}\n\n"
            f"Write ONLY the dialogue lines, no action tags or narration. "
            f"Make each line feel distinctly like this character's voice."
        )
        with st.spinner("Generating voice…"):
            result = llm.call(prompt, 250)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state[f"vs_result_{char['name']}"] = result

    result = st.session_state.get(f"vs_result_{char['name']}")
    if result:
        st.markdown(
            f"<div style='background:rgba(168,188,255,0.07);border:1px solid rgba(168,188,255,0.2);"
            f"border-radius:8px;padding:14px;font-size:0.88rem;font-style:italic;"
            f"color:var(--text-primary);line-height:1.9;white-space:pre-line;'>"
            f"{_html.escape(result)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key=f"vs_clear_{char['name']}"):
            st.session_state.pop(f"vs_result_{char['name']}", None)
            st.rerun()


# ── Appearance Generator ──────────────────────────────────────────────────
def _show_appearance_generator(story, characters):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;margin-bottom:8px;'>"
        "👁 Appearance Generator</div>", unsafe_allow_html=True)

    if not characters:
        st.caption("Add characters first.")
        return

    char_names = [c["name"] for c in characters]
    selected   = st.selectbox("Character", char_names, key="ap_char")
    char       = next((c for c in characters if c["name"] == selected), characters[0])

    c1, c2 = st.columns(2)
    with c1:
        age_range = st.selectbox("Age range",
            ["Child (8-12)", "Teen (13-17)", "Young Adult (18-25)",
             "Adult (26-40)", "Middle-aged (41-60)", "Elder (60+)"],
            key="ap_age")
    with c2:
        build = st.selectbox("Build",
            ["Slender", "Athletic", "Average", "Stocky", "Tall and lean",
             "Short and compact", "Willowy", "Imposing"],
            key="ap_build")

    distinctive = st.text_input("Any distinctive features?",
        placeholder="e.g. scar on left cheek, silver hair, one eye",
        key="ap_distinctive")

    if st.button("👁 Generate Appearance", key="ap_gen", use_container_width=True):
        prompt = (
            f"Write a vivid physical description for '{char['name']}', a {age_range.split('(')[0].strip()}, "
            f"{build.lower()} character in a {story.get('genre','Fiction')} story.\n"
            f"Role: {char.get('role','')}\n"
            f"Description: {char.get('description','')}\n"
            f"{'Distinctive features: ' + distinctive if distinctive else ''}\n\n"
            f"Write 2 paragraphs:\n"
            f"1. Physical appearance (face, hair, eyes, height, build, notable features)\n"
            f"2. How they carry themselves (posture, manner, what people notice first)\n\n"
            f"Be specific and use sensory details. Avoid generic descriptions. "
            f"Make the appearance reflect their personality and role in the story."
        )
        with st.spinner("Generating appearance…"):
            result = llm.call(prompt, 300)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state[f"ap_result_{char['name']}"] = result

    result = st.session_state.get(f"ap_result_{char['name']}")
    if result:
        st.markdown(
            f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
            f"border-radius:8px;padding:14px;font-size:0.82rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;'>{_html.escape(result)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key=f"ap_clear_{char['name']}"):
            st.session_state.pop(f"ap_result_{char['name']}", None)
            st.rerun()


# ── Main Panel ─────────────────────────────────────────────────────────────
def show_character_suite(story, characters):
    tabs = st.tabs(["🌳 Tree", "📜 Backstory", "🎯 Motivation", "🎭 Voice", "👁 Appearance"])
    with tabs[0]: _show_family_tree(characters)
    with tabs[1]: _show_backstory_generator(story, characters)
    with tabs[2]: _show_motivation_analyser(story, characters)
    with tabs[3]: _show_voice_simulator(story, characters)
    with tabs[4]: _show_appearance_generator(story, characters)
