"""
NarrativeForge — Interactive Story / CYOA Engine
Create branching story paths: write a scene, add 2-4 choices,
each choice generates a unique continuation via AI.
Shows a visual branch tree of all paths taken.
"""
import os
import html as _html
import json
import requests
import streamlit as st
import llm
from database import (save_story_choice, load_story_choices,
                      delete_story_choice, save_story)

llm.AI_UNAVAILABLE = "_llm.AI_UNAVAILABLE__"



def _ai_error():
    st.error("⚠️ AI unavailable — is Ollama running?")


def _prose_tail(story, n_msgs=6):
    """Last N AI messages as context."""
    msgs = [m for m in story.get("messages", [])[-n_msgs * 2:]
            if m.get("role") == "assistant"
            and not m["content"].startswith("◆")]
    return " ".join(m["content"] for m in msgs[-n_msgs:])[-600:]


# ── Branch Tree Renderer ───────────────────────────────────────────────────
def _render_branch_tree(branches):
    """Render an ASCII-style branch tree in HTML."""
    if not branches:
        return ""

    parts = [
        "<div style='font-family:JetBrains Mono,Courier New,monospace;"
        "font-size:0.75rem;color:#C5C8D4;line-height:2;'>"
        "<div style='color:#4D6BFE;font-weight:700;'>📖 Main Story</div>"
    ]
    for i, b in enumerate(branches):
        is_last = (i == len(branches) - 1)
        connector = "└──" if is_last else "├──"
        label = _html.escape(b["choice_label"][:50])
        n_words = len(" ".join(
            m.get("content", "") for m in b.get("branch_messages", [])
        ).split())
        active_dot = "🟢" if b.get("is_active") else "⚪"
        parts.append(
            f"<div style='padding-left:16px;'>"
            f"<span style='color:#6B7080;'>{connector} </span>"
            f"{active_dot} <span style='color:#A8BCFF;font-weight:600;'>{label}</span>"
            f" <span style='color:#6B7080;'>({n_words} words)</span>"
            f"</div>")

    parts.append("</div>")
    return "".join(parts)


# ── Choice Card ────────────────────────────────────────────────────────────
def _show_choice_card(branch, username, story, idx, ctx=""):
    """Render a single choice/branch card with preview and actions."""
    msgs     = branch.get("branch_messages", [])
    preview  = " ".join(m.get("content", "") for m in msgs if m.get("role") == "assistant")
    preview  = preview[:180] + ("…" if len(preview) > 180 else "")
    n_words  = len(" ".join(m.get("content", "") for m in msgs).split())
    is_active = branch.get("is_active", False)

    border = "rgba(52,211,153,0.4)" if is_active else "rgba(77,107,254,0.2)"
    bg     = "rgba(52,211,153,0.05)" if is_active else "rgba(77,107,254,0.03)"

    st.markdown(
        f"<div style='border:1px solid {border};background:{bg};"
        f"border-radius:10px;padding:12px 14px;margin-bottom:8px;'>"
        f"<div style='font-size:0.80rem;font-weight:700;color:#A8BCFF;margin-bottom:4px;'>"
        f"{'🟢 Active · ' if is_active else ''}🔀 {_html.escape(branch['choice_label'])}</div>"
        f"<div style='font-size:0.74rem;color:#6B7080;margin-bottom:6px;'>"
        f"{n_words:,} words in this branch</div>"
        f"<div style='font-size:0.78rem;color:#C5C8D4;line-height:1.6;font-style:italic;'>"
        f"{_html.escape(preview)}</div></div>",
        unsafe_allow_html=True)

    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if not is_active:
            if st.button("🔀 Switch to", key=f"cyoa_{ctx}_switch_{idx}",
                         use_container_width=True):
                st.session_state[f"cyoa_active_{story['id']}"] = branch["id"]
                # Load this branch's messages into story
                story["messages"] = list(branch["branch_messages"])
                save_story(username, story)
                st.rerun()
        else:
            st.markdown(
                "<div style='text-align:center;font-size:0.72rem;color:#34d399;"
                "padding:6px;'>✓ Currently reading</div>",
                unsafe_allow_html=True)
    with bc2:
        if st.button("👁 Preview", key=f"cyoa_{ctx}_preview_{idx}",
                     use_container_width=True):
            key = f"cyoa_preview_open_{branch['id']}"
            st.session_state[key] = not st.session_state.get(key, False)
            st.rerun()
    with bc3:
        if st.button("🗑 Delete", key=f"cyoa_{ctx}_del_{idx}",
                     use_container_width=True):
            delete_story_choice(branch["id"], username)
            st.rerun()

    # Preview expander
    if st.session_state.get(f"cyoa_preview_open_{branch['id']}"):
        with st.expander("Full branch text", expanded=True):
            for m in branch.get("branch_messages", []):
                if m.get("role") == "assistant":
                    st.markdown(
                        f"<div style='font-size:0.82rem;line-height:1.8;"
                        f"color:var(--text-primary);padding:8px 0;'>"
                        f"{_html.escape(m['content'])}</div>",
                        unsafe_allow_html=True)


# ── Main Panel ─────────────────────────────────────────────────────────────
def show_interactive_story(story, characters, username, ctx=""):
    """Full CYOA / interactive branching story panel."""

    existing_branches = load_story_choices(username, story["id"])
    active_id = st.session_state.get(f"cyoa_active_{story['id']}")

    # Mark which is active
    for b in existing_branches:
        b["is_active"] = (b["id"] == active_id)

    # ── Branch tree overview ───────────────────────────────────────────────
    if existing_branches:
        st.markdown(
            "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>"
            "🌳 Story Tree</div>",
            unsafe_allow_html=True)
        st.markdown(_render_branch_tree(existing_branches), unsafe_allow_html=True)
        st.markdown("---")

    # ── Create new branch ─────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;margin-bottom:8px;'>"
        "🔀 Create a Branch Point</div>",
        unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:0.74rem;color:#6B7080;margin-bottom:12px;'>"
        "Pick a moment in your story, define 2–4 choices, and each one generates "
        "a unique continuation with AI.</div>",
        unsafe_allow_html=True)

    n_choices = st.select_slider("Number of choices",
        [2, 3, 4], value=3, key=f"cyoa_{ctx}_n_{story['id']}")

    # Collect choice labels
    choice_labels = []
    for i in range(n_choices):
        label = st.text_input(
            f"Choice {i+1}",
            key=f"cyoa_{ctx}_choice_{i}_{story['id']}",
            placeholder=f"e.g. {'The hero enters the cave alone' if i==0 else 'The hero waits for backup' if i==1 else 'The hero turns back'}")
        choice_labels.append(label)

    char_context = ", ".join(c["name"] for c in characters) if characters else "the protagonist"
    prose_tail   = _prose_tail(story)

    generate_all = st.button(
        f"✨ Generate {n_choices} Branches", key=f"cyoa_{ctx}_gen_{story['id']}",
        use_container_width=True,
        disabled=not all(l.strip() for l in choice_labels))

    if generate_all:
        progress_bar = st.progress(0)
        for idx, label in enumerate(choice_labels):
            if not label.strip():
                continue
            progress_bar.progress((idx) / n_choices, text=f"Writing: {label[:40]}…")
            prompt = (
                f"Continue this {story.get('genre','Fiction')} story in a new direction.\n\n"
                f"Story so far (recent):\n{prose_tail}\n\n"
                f"Characters: {char_context}\n"
                f"Genre: {story.get('genre','Fiction')} · Tone: {story.get('tone','')}\n\n"
                f"The reader chose: '{label}'\n\n"
                f"Write 2-3 paragraphs continuing from this choice. "
                f"Make this branch feel meaningfully different from the others. "
                f"End with a hook for further continuation."
            )
            with st.spinner(f"Writing branch: {label[:30]}…"):
                result = llm.call(prompt, 400)

            if result == llm.AI_UNAVAILABLE:
                _ai_error()
                break

            branch_msgs = list(story.get("messages", [])) + [
                {"role": "user",    "content": f"[Branch: {label}]"},
                {"role": "assistant", "content": result},
            ]
            save_story_choice(username, story["id"],
                              len(story.get("messages", [])) - 1,
                              label, branch_msgs)
            progress_bar.progress((idx + 1) / n_choices)

        progress_bar.empty()
        st.success(f"✅ {n_choices} branches generated! Scroll down to explore them.")
        st.rerun()

    # ── Existing branches ──────────────────────────────────────────────────
    if existing_branches:
        st.markdown("---")
        st.markdown(
            "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>"
            f"🔀 All Branches ({len(existing_branches)})</div>",
            unsafe_allow_html=True)

        for idx, branch in enumerate(existing_branches):
            _show_choice_card(branch, username, story, idx, ctx=ctx)

        # Merge branch back to main
        st.markdown("---")
        st.markdown(
            "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:8px;'>"
            "💡 <b>Tip:</b> Switch to any branch to continue writing in that timeline. "
            "Switch back to main story anytime from the Snaps tab.</div>",
            unsafe_allow_html=True)

        if active_id:
            if st.button("↩️ Return to Main Story", key="cyoa_main",
                         use_container_width=True):
                st.session_state.pop(f"cyoa_active_{story['id']}", None)
                st.rerun()
    else:
        st.markdown(
            "<div style='text-align:center;color:#6B7080;font-size:0.82rem;padding:24px;'>"
            "No branches yet. Fill in the choices above and click Generate!</div>",
            unsafe_allow_html=True)
