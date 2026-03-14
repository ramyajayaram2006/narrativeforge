"""
NarrativeForge — World Building Suite
Faction Manager, Magic System Builder, Religion / Pantheon Builder,
Language Name Generator, Geography Notes, Timeline of World Events.
"""
import os
import html as _html
import json
import requests
import streamlit as st
import llm
from database import (save_world_element, load_world_elements,
                      update_world_element, delete_world_element)

llm.AI_UNAVAILABLE = "_llm.AI_UNAVAILABLE__"

_ELEMENT_TYPES = {
    "faction":    {"icon": "⚔️",  "label": "Faction"},
    "magic":      {"icon": "✨",  "label": "Magic System"},
    "religion":   {"icon": "🌙",  "label": "Religion / Pantheon"},
    "location":   {"icon": "🗺️",  "label": "Location"},
    "event":      {"icon": "📅",  "label": "World Event"},
    "language":   {"icon": "🔤",  "label": "Language"},
    "creature":   {"icon": "🐉",  "label": "Creature / Species"},
    "artefact":   {"icon": "💎",  "label": "Artefact / Item"},
}



def _ai_error():
    st.error("⚠️ AI unavailable — is Ollama running?")


# ── Faction Manager ────────────────────────────────────────────────────────
def _show_factions(story, username):
    factions = load_world_elements(username, story["id"], "faction")

    with st.expander("➕ Add Faction", expanded=len(factions) == 0):
        name   = st.text_input("Faction name", key="fac_name", max_chars=60)
        goal   = st.text_input("Goal / agenda", key="fac_goal", max_chars=120)
        leader = st.text_input("Leader", key="fac_leader", max_chars=60)
        values = st.text_input("Core values / beliefs", key="fac_values", max_chars=120)
        power  = st.select_slider("Power level", ["Weak", "Minor", "Moderate", "Major", "Dominant"],
                                  value="Moderate", key="fac_power")
        allies = st.text_input("Allied with", key="fac_allies", max_chars=100)
        enemies = st.text_input("Enemies", key="fac_enemies", max_chars=100)

        gen_col, save_col = st.columns(2)
        with gen_col:
            if st.button("✨ AI Fill", key="fac_ai_fill", use_container_width=True):
                prompt = (
                    f"Create a faction for a {story.get('genre','Fantasy')} story. "
                    f"{'Name: ' + name if name else 'Generate a compelling name.'}\n"
                    f"Return ONLY this JSON (no commentary):\n"
                    f'{{"name":"...","goal":"...","leader":"...","values":"...","power":"Moderate","allies":"...","enemies":"..."}}'
                )
                with st.spinner("Generating…"):
                    result = llm.call(prompt, 200)
                if result != llm.AI_UNAVAILABLE:
                    try:
                        clean = result[result.find("{"):result.rfind("}")+1]
                        data  = json.loads(clean)
                        st.session_state["fac_ai_data"] = data
                        st.info(
                            f"**{data.get('name','')}** — {data.get('goal','')}\n\n"
                            f"Leader: {data.get('leader','')} · "
                            f"Values: {data.get('values','')}\n\n"
                            f"Click Save to add.")
                    except Exception:
                        st.markdown(
                            f"<div style='font-size:0.80rem;white-space:pre-line;"
                            f"color:var(--text-primary);'>{_html.escape(result)}</div>",
                            unsafe_allow_html=True)
                else:
                    _ai_error()

        with save_col:
            if st.button("💾 Save Faction", key="fac_save", use_container_width=True):
                ai_data = st.session_state.pop("fac_ai_data", None)
                n = ai_data.get("name", name) if ai_data else name
                if n.strip():
                    d = ai_data if ai_data else {
                        "goal": goal, "leader": leader, "values": values,
                        "power": power, "allies": allies, "enemies": enemies}
                    save_world_element(username, story["id"], "faction", n, d)
                    st.rerun()

    if not factions:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.78rem;padding:12px;'>No factions yet.</div>",
            unsafe_allow_html=True)
        return

    for fac in factions:
        d   = fac.get("data", {})
        fid = fac["id"]
        st.markdown(
            f"<div style='border:1px solid var(--primary-border);border-radius:8px;"
            f"padding:12px;margin-bottom:8px;background:var(--bg-card);'>"
            f"<div style='font-size:0.88rem;font-weight:700;color:var(--primary);margin-bottom:6px;'>"
            f"⚔️ {_html.escape(fac['name'])}"
            f"<span style='font-size:0.68rem;color:#6B7080;font-weight:400;margin-left:8px;'>"
            f"{d.get('power','')}</span></div>"
            f"<div style='font-size:0.78rem;color:#C5C8D4;line-height:1.6;'>"
            f"<b>Goal:</b> {_html.escape(d.get('goal','—'))}<br>"
            f"<b>Leader:</b> {_html.escape(d.get('leader','—'))}<br>"
            f"<b>Values:</b> {_html.escape(d.get('values','—'))}<br>"
            f"<b>Allies:</b> {_html.escape(d.get('allies','—'))}  "
            f"<b>Enemies:</b> {_html.escape(d.get('enemies','—'))}"
            f"</div></div>",
            unsafe_allow_html=True)
        if st.button(f"🗑 Delete {fac['name']}", key=f"fac_del_{fid}",
                     use_container_width=True):
            delete_world_element(fid, username)
            st.rerun()


# ── Magic System Builder ────────────────────────────────────────────────────
def _show_magic(story, username):
    existing = load_world_elements(username, story["id"], "magic")

    with st.expander("✨ Define Magic System", expanded=len(existing) == 0):
        ms_name  = st.text_input("Magic system name", key="ms_name",
                                 placeholder="e.g. The Weaving, Alchemy, Resonance")
        ms_src   = st.text_input("Source / origin of power", key="ms_src",
                                 placeholder="e.g. Stars, bloodlines, emotion, mathematics")
        ms_cost  = st.text_input("Cost / limitation", key="ms_cost",
                                 placeholder="e.g. Life force, memory loss, exhaustion")
        ms_rules = st.text_area("Rules & mechanics", key="ms_rules", height=80,
                                placeholder="e.g. Requires focus words, only works at night, can't affect living beings")
        ms_users = st.text_input("Who can use it?", key="ms_users",
                                 placeholder="e.g. Born gifted, trained mages, anyone with the right tool")
        ms_limit = st.text_input("Forbidden / impossible uses", key="ms_limit",
                                 placeholder="e.g. Cannot reverse death, cannot affect the caster directly")

        g1, g2 = st.columns(2)
        with g1:
            if st.button("✨ AI Generate System", key="ms_ai", use_container_width=True):
                prompt = (
                    f"Design a magic system for a {story.get('genre','Fantasy')} story. "
                    f"{'Named: ' + ms_name if ms_name else ''}\n"
                    f"Return ONLY this JSON:\n"
                    f'{{"name":"...","source":"...","cost":"...","rules":"...","users":"...","forbidden":"..."}}'
                )
                with st.spinner("Designing magic system…"):
                    result = llm.call(prompt, 300)
                if result != llm.AI_UNAVAILABLE:
                    try:
                        clean = result[result.find("{"):result.rfind("}")+1]
                        data  = json.loads(clean)
                        st.session_state["ms_ai_data"] = data
                        st.info(f"**{data.get('name','')}**: {data.get('rules','')} — Click Save.")
                    except:
                        st.markdown(f"<pre style='font-size:0.78rem;'>{_html.escape(result)}</pre>",
                                    unsafe_allow_html=True)
                else:
                    _ai_error()
        with g2:
            if st.button("💾 Save System", key="ms_save", use_container_width=True):
                ai_d = st.session_state.pop("ms_ai_data", None)
                n    = ai_d.get("name", ms_name) if ai_d else ms_name
                if n.strip():
                    d = ai_d if ai_d else {
                        "source": ms_src, "cost": ms_cost, "rules": ms_rules,
                        "users": ms_users, "forbidden": ms_limit}
                    save_world_element(username, story["id"], "magic", n, d)
                    st.rerun()

    for ms in existing:
        d   = ms.get("data", {})
        mid = ms["id"]
        _FIELD_LABELS = [
            ("source","⚡ Source"), ("cost","💰 Cost"), ("rules","📏 Rules"),
            ("users","👤 Users"), ("forbidden","🚫 Forbidden")]
        rows = "".join(
            f"<div><b style='color:#A8BCFF;'>{lbl}:</b> "
            f"{_html.escape(str(d.get(field,'—')))}</div>"
            for field, lbl in _FIELD_LABELS if d.get(field))
        st.markdown(
            f"<div style='border:1px solid var(--primary-border);border-radius:8px;"
            f"padding:12px;margin-bottom:8px;background:var(--bg-card);'>"
            f"<div style='font-size:0.88rem;font-weight:700;color:#fbbf24;margin-bottom:6px;'>"
            f"✨ {_html.escape(ms['name'])}</div>"
            f"<div style='font-size:0.78rem;color:#C5C8D4;line-height:1.8;'>{rows}</div></div>",
            unsafe_allow_html=True)
        if st.button(f"🗑 Delete {ms['name']}", key=f"ms_del_{mid}", use_container_width=True):
            delete_world_element(mid, username)
            st.rerun()


# ── Religion / Pantheon Builder ────────────────────────────────────────────
def _show_religion(story, username):
    existing = load_world_elements(username, story["id"], "religion")

    with st.expander("🌙 Add Religion / God", expanded=len(existing) == 0):
        rel_name  = st.text_input("Name (religion or deity)", key="rel_name", max_chars=60)
        rel_type  = st.selectbox("Type", ["Monotheistic", "Polytheistic", "Animist",
                                          "Cult", "Philosophy", "Ancient / Forgotten",
                                          "Secret Order", "Nature Worship"], key="rel_type")
        rel_deity = st.text_input("Deity / central figure (if any)", key="rel_deity", max_chars=80)
        rel_belief = st.text_area("Core beliefs / afterlife / creation myth", key="rel_belief",
                                  height=70)
        rel_practice = st.text_input("Rituals / practices", key="rel_practice", max_chars=120)
        rel_taboo = st.text_input("Taboos / forbidden acts", key="rel_taboo", max_chars=120)

        g1, g2 = st.columns(2)
        with g1:
            if st.button("✨ AI Generate", key="rel_ai", use_container_width=True):
                prompt = (
                    f"Create a religion or deity for a {story.get('genre','Fantasy')} story. "
                    f"Type: {rel_type}. {'Name: ' + rel_name if rel_name else ''}\n"
                    f"Return ONLY this JSON:\n"
                    f'{{"name":"...","type":"...","deity":"...","beliefs":"...","practices":"...","taboos":"..."}}'
                )
                with st.spinner("Generating…"):
                    result = llm.call(prompt, 300)
                if result != llm.AI_UNAVAILABLE:
                    try:
                        clean = result[result.find("{"):result.rfind("}")+1]
                        data  = json.loads(clean)
                        st.session_state["rel_ai_data"] = data
                        st.info(f"**{data.get('name','')}**: {data.get('beliefs','')} — Click Save.")
                    except:
                        st.markdown(f"<pre style='font-size:0.78rem;'>{_html.escape(result)}</pre>",
                                    unsafe_allow_html=True)
                else:
                    _ai_error()
        with g2:
            if st.button("💾 Save", key="rel_save", use_container_width=True):
                ai_d = st.session_state.pop("rel_ai_data", None)
                n    = ai_d.get("name", rel_name) if ai_d else rel_name
                if n.strip():
                    d = ai_d if ai_d else {
                        "type": rel_type, "deity": rel_deity, "beliefs": rel_belief,
                        "practices": rel_practice, "taboos": rel_taboo}
                    save_world_element(username, story["id"], "religion", n, d)
                    st.rerun()

    for rel in existing:
        d   = rel.get("data", {})
        rid = rel["id"]
        st.markdown(
            f"<div style='border:1px solid var(--primary-border);border-radius:8px;"
            f"padding:12px;margin-bottom:8px;background:var(--bg-card);'>"
            f"<div style='font-size:0.88rem;font-weight:700;color:#a78bfa;margin-bottom:6px;'>"
            f"🌙 {_html.escape(rel['name'])} "
            f"<span style='font-size:0.68rem;color:#6B7080;'>{d.get('type','')}</span></div>"
            f"<div style='font-size:0.78rem;color:#C5C8D4;line-height:1.7;'>"
            f"<b>Deity:</b> {_html.escape(d.get('deity','—'))}<br>"
            f"<b>Beliefs:</b> {_html.escape(d.get('beliefs','—'))}<br>"
            f"<b>Taboos:</b> {_html.escape(d.get('taboos','—'))}"
            f"</div></div>",
            unsafe_allow_html=True)
        if st.button(f"🗑 Delete {rel['name']}", key=f"rel_del_{rid}", use_container_width=True):
            delete_world_element(rid, username)
            st.rerun()


# ── Language Generator ─────────────────────────────────────────────────────
def _show_language(story, username):
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;margin-bottom:8px;'>"
        "🔤 Fictional Language Generator</div>", unsafe_allow_html=True)

    lang_feel = st.selectbox("Linguistic feel",
        ["Elvish / Flowing", "Harsh / Guttural", "Musical / Tonal", "Ancient / Archaic",
         "Technical / Precise", "Alien / Unpronounceable", "Romantic / Latin-like",
         "Norse / Viking", "Arabic / Middle Eastern"],
        key="lang_feel")
    n_words = st.selectbox("Words to generate", [10, 20, 30, 50], index=1, key="lang_n")
    concepts = st.text_input("Concepts to translate",
        value="fire, water, sky, enemy, friend, king, death, love, magic, war",
        key="lang_concepts", max_chars=200)

    if st.button("🔤 Generate Language Sample", key="lang_gen", use_container_width=True):
        concept_list = [c.strip() for c in concepts.split(",") if c.strip()][:n_words]
        prompt = (
            f"Create a fictional {lang_feel.split('/')[0].strip()} language for a "
            f"{story.get('genre','Fantasy')} story.\n\n"
            f"Generate translations for these {len(concept_list)} words:\n"
            f"{', '.join(concept_list)}\n\n"
            f"Rules:\n"
            f"- Invent consistent phonemes fitting the {lang_feel} style\n"
            f"- Add 3 grammar rules (e.g. 'verbs come before nouns')\n"
            f"- Give the language a name\n\n"
            f"Format: LANGUAGE NAME: [name]\nGRAMMAR: [3 rules]\n"
            f"VOCABULARY:\nword = translation\n..."
        )
        with st.spinner("Constructing language…"):
            result = llm.call(prompt, 500)
        if result == llm.AI_UNAVAILABLE:
            _ai_error()
        else:
            st.session_state["lang_result"] = result

            # Offer to save as world element
            save_world_element(username, story["id"], "language",
                               f"Language ({lang_feel.split('/')[0].strip()})",
                               {"vocabulary": result, "feel": lang_feel})

    if r := st.session_state.get("lang_result"):
        st.markdown(
            f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
            f"border-radius:8px;padding:14px;font-size:0.80rem;color:var(--text-primary);"
            f"line-height:1.8;white-space:pre-line;font-family:JetBrains Mono,monospace;'>"
            f"{_html.escape(r)}</div>",
            unsafe_allow_html=True)
        if st.button("🗑 Clear", key="lang_clear"):
            st.session_state.pop("lang_result", None)
            st.rerun()

    # Show saved languages
    saved_langs = load_world_elements(username, story["id"], "language")
    if saved_langs:
        st.markdown("**Saved Languages:**")
        for lang in saved_langs:
            with st.expander(f"🔤 {lang['name']}"):
                st.text(lang["data"].get("vocabulary", "")[:800])
                if st.button(f"🗑 Delete", key=f"lang_del_{lang['id']}"):
                    delete_world_element(lang["id"], username)
                    st.rerun()


# ── Locations ─────────────────────────────────────────────────────────────
def _show_locations(story, username):
    existing = load_world_elements(username, story["id"], "location")

    with st.expander("🗺️ Add Location", expanded=len(existing) == 0):
        loc_name  = st.text_input("Location name", key="loc_name", max_chars=60)
        loc_type  = st.selectbox("Type",
            ["City / Town", "Village", "Forest", "Mountain / Pass", "Cave / Underground",
             "Castle / Fortress", "Ruin", "Island", "Ocean / Sea", "Desert",
             "Magical Realm", "Space Station / Planet"],
            key="loc_type")
        loc_desc  = st.text_area("Description", key="loc_desc", height=70)
        loc_hist  = st.text_input("History / significance", key="loc_hist", max_chars=150)
        loc_danger = st.select_slider("Danger level",
            ["Safe", "Low", "Medium", "High", "Deadly"], key="loc_danger")

        g1, g2 = st.columns(2)
        with g1:
            if st.button("✨ AI Generate", key="loc_ai", use_container_width=True):
                prompt = (
                    f"Create a {loc_type} location for a {story.get('genre','Fantasy')} story. "
                    f"{'Named: ' + loc_name + '. ' if loc_name else ''}"
                    f"Return ONLY this JSON:\n"
                    f'{{"name":"...","type":"...","description":"...","history":"...","danger":"Medium"}}'
                )
                with st.spinner("Generating…"):
                    result = llm.call(prompt, 250)
                if result != llm.AI_UNAVAILABLE:
                    try:
                        clean = result[result.find("{"):result.rfind("}")+1]
                        data  = json.loads(clean)
                        st.session_state["loc_ai_data"] = data
                        st.info(f"**{data.get('name','')}**: {data.get('description','')[:80]}… — Click Save.")
                    except:
                        st.text(result[:200])
                else:
                    _ai_error()
        with g2:
            if st.button("💾 Save Location", key="loc_save", use_container_width=True):
                ai_d = st.session_state.pop("loc_ai_data", None)
                n    = ai_d.get("name", loc_name) if ai_d else loc_name
                if n.strip():
                    d = ai_d if ai_d else {
                        "type": loc_type, "description": loc_desc,
                        "history": loc_hist, "danger": loc_danger}
                    save_world_element(username, story["id"], "location", n, d)
                    st.rerun()

    for loc in existing:
        d   = loc.get("data", {})
        lid = loc["id"]
        danger_color = {"Deadly": "#f87171", "High": "#fb923c",
                        "Medium": "#fbbf24", "Low": "#34d399", "Safe": "#6B7080"}.get(
            d.get("danger","Medium"), "#6B7080")
        st.markdown(
            f"<div style='border:1px solid var(--primary-border);border-radius:8px;"
            f"padding:10px 12px;margin-bottom:6px;background:var(--bg-card);'>"
            f"<div style='display:flex;justify-content:space-between;align-items:start;'>"
            f"<div style='font-size:0.85rem;font-weight:700;color:#60a5fa;'>"
            f"🗺️ {_html.escape(loc['name'])} "
            f"<span style='font-size:0.68rem;color:#6B7080;'>{d.get('type','')}</span></div>"
            f"<span style='font-size:0.68rem;color:{danger_color};font-weight:600;'>"
            f"⚠️ {d.get('danger','')}</span></div>"
            f"<div style='font-size:0.76rem;color:#C5C8D4;margin-top:4px;line-height:1.6;'>"
            f"{_html.escape(d.get('description',''))[:120]}</div></div>",
            unsafe_allow_html=True)
        if st.button(f"🗑 Delete {loc['name']}", key=f"loc_del_{lid}", use_container_width=True):
            delete_world_element(lid, username)
            st.rerun()


# ── Main Panel ─────────────────────────────────────────────────────────────
def show_world_builder(story, username):
    tabs = st.tabs(["⚔️ Factions", "✨ Magic", "🌙 Religion", "🗺️ Locations", "🔤 Language"])
    with tabs[0]: _show_factions(story, username)
    with tabs[1]: _show_magic(story, username)
    with tabs[2]: _show_religion(story, username)
    with tabs[3]: _show_locations(story, username)
    with tabs[4]: _show_language(story, username)
