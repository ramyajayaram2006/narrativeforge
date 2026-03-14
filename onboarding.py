"""
onboarding.py — NarrativeForge New User Guide
Shows a step-by-step interactive guide for first-time users.
"""
import re
import streamlit as st

_STEPS = [
    {"icon":"📖","title":"Welcome to NarrativeForge!",
     "desc":"Your AI-powered story co-writer. Write novels, short stories, screenplays — with an AI that thinks like a professional author.",
     "tip":None},
    {"icon":"✍️","title":"Step 1 — Create Your First Story",
     "desc":"On the Dashboard click **＋ New Story**. Pick a template (Fantasy, Horror, Romance…) or start blank. Give it a title, genre, and tone.",
     "tip":"💡 Use a template to get a pre-filled opening scene instantly."},
    {"icon":"💬","title":"Step 2 — Write & Get AI Responses",
     "desc":"Type anything in the chat box — a scene opener, a description, a feeling. Hit Enter. Then pick how the AI continues:\n\n• **Continue** — flows naturally\n• **Paragraph** — one vivid paragraph\n• **Smart** — AI picks the best approach\n• **Dialogue** — spoken exchange between characters\n• **Plot Twist** — unexpected revelation\n• **Monologue** — inner thoughts of your hero",
     "tip":"💡 The more specific you are, the better. Try: *'Aria steps into the burning village and sees...'*"},
    {"icon":"👥","title":"Step 3 — Add Characters",
     "desc":"Open the **Cast** tab in the left sidebar. Add characters with name, role, description, and speaking style.\n\nThe AI automatically uses your characters — they speak, act, and react in character.",
     "tip":"💡 Add a speaking style like *'formal and cold'* or *'sarcastic and quick-witted'* — you'll hear the difference."},
    {"icon":"🧠","title":"Step 4 — Use the Intelligence Panel",
     "desc":"The **Intel** tab is your story health dashboard:\n\n• **Show/Tell scanner** — finds weak telling\n• **Tension meter** — 0-100 scene intensity score\n• **Plot hole detector** — finds logical gaps\n• **Grammar checker** — passive voice, weak adverbs\n• **Analytics** — word count, pacing, vocabulary",
     "tip":"💡 Run the Grammar checker before exporting — it catches things spell-check misses."},
    {"icon":"🎬","title":"Step 5 — Structure Your Plot",
     "desc":"**Intel** tab → Plot Tools. Choose your structure:\n\n• **Three-Act** — setup / confrontation / resolution\n• **Hero's Journey** — 12 stages\n• **Save the Cat** — 15 Hollywood beats\n• **Story Spine** — 8 tight beats\n• **Conflict Curve** — track tension visually",
     "tip":"💡 Use the Kanban board to move scenes between Act 1, 2, and 3 as you write."},
    {"icon":"📥","title":"Step 6 — Export Your Story",
     "desc":"Open the **Export** tab in the sidebar:\n\n• **📱 EPUB** — Kindle, Kobo, Apple Books\n• **🌐 HTML** — beautiful web page\n• **📖 Book PDF** — typeset like a real book\n• **🎬 Screenplay** — industry-standard format\n\nOr click **📖 Book Mode** in the top bar for a live book preview + PDF.",
     "tip":"💡 Book Mode shows your story on a cream page like a real book. Download PDF directly from there."},
    {"icon":"⚙️","title":"Step 7 — Customise Your AI Voice",
     "desc":"Open the **Set** tab (Settings):\n\n• **Writing Style** — paste your own writing, the AI matches your voice\n• **Word Goal** — set a daily target (e.g. 1,000 words)\n• **Story Arc** — define beginning / climax / resolution so AI keeps the big picture",
     "tip":"💡 The more of your own writing you paste into Writing Style, the more the AI sounds like YOU."},
    {"icon":"🏅","title":"Bonus Features",
     "desc":"• **✏️ Edit Messages** — edit or delete any AI response\n• **📸 Snapshots** — save versions before major rewrites\n• **🌍 World Builder** — locations, factions, magic systems\n• **🔀 CYOA** — branching choose-your-own-adventure paths\n• **👥 Beta Reading** — share story with a unique link for feedback\n• **🏅 Achievements** — unlock badges at word milestones",
     "tip":"💡 Use Snapshots before asking the AI to rewrite a scene — you can always restore the original."},
    {"icon":"🚀","title":"You're Ready!",
     "desc":"That's everything you need. The best way to learn is to just start — type one sentence and see where the AI takes it.\n\nGood luck, and happy writing! ✍️",
     "tip":None},
]

_CSS = """<style>
.ob-wrap{max-width:700px;margin:0 auto}
.ob-card{background:linear-gradient(135deg,#161820,#1a1c28);border:1px solid
rgba(77,107,254,0.25);border-radius:16px;padding:32px 36px;margin-bottom:16px}
.ob-icon{font-size:2.8rem;text-align:center;margin-bottom:10px}
.ob-title{font-size:1.35rem;font-weight:700;color:#E2E8F0;text-align:center;margin-bottom:14px}
.ob-desc{font-size:0.94rem;color:#A8BCFF;line-height:1.85}
.ob-tip{background:rgba(77,107,254,0.08);border-left:3px solid #4D6BFE;
border-radius:0 8px 8px 0;padding:10px 14px;font-size:0.84rem;color:#8BA3FF;margin-top:14px}
.ob-dots{display:flex;gap:7px;justify-content:center;margin-bottom:18px}
.ob-dot{width:9px;height:9px;border-radius:50%;background:rgba(77,107,254,0.2)}
.ob-dot-on{background:#4D6BFE;box-shadow:0 0 6px #4D6BFE}
.ob-dot-done{background:#4ADE80}
</style>"""

def show_onboarding():
    st.markdown(_CSS, unsafe_allow_html=True)
    step  = st.session_state.get("_onboard_step", 0)
    total = len(_STEPS)
    s     = _STEPS[step]

    # progress dots
    dots = "".join(
        f"<div class='ob-dot ob-dot-done'></div>" if i < step else
        f"<div class='ob-dot ob-dot-on'></div>"   if i == step else
        f"<div class='ob-dot'></div>"
        for i in range(total)
    )

    desc_html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>',
                re.sub(r'\*(.+?)\*', r'<i>\1</i>',
                s["desc"].replace("\n","<br>")))
    tip_html  = f"<div class='ob-tip'>{s['tip']}</div>" if s["tip"] else ""

    st.markdown(f"""
    <div class='ob-wrap'>
      <div class='ob-dots'>{dots}</div>
      <div class='ob-card'>
        <div class='ob-icon'>{s['icon']}</div>
        <div class='ob-title'>{s['title']}</div>
        <div class='ob-desc'>{desc_html}</div>
        {tip_html}
      </div>
      <div style='text-align:center;font-size:0.75rem;color:#6B7080;margin-top:4px'>
        {step+1} / {total}
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        if st.button("✕ Skip Guide", key="_ob_skip_btn", use_container_width=True):
            _finish()
    with c2:
        if step > 0:
            if st.button("← Back", key="_ob_prev_btn", use_container_width=True):
                st.session_state["_onboard_step"] = step - 1
                st.rerun()
    with c3:
        if step < total - 1:
            if st.button("Next →", key="_ob_next_btn",
                         use_container_width=True, type="primary"):
                st.session_state["_onboard_step"] = step + 1
                st.rerun()
        else:
            if st.button("🚀 Start Writing!", key="_ob_finish_btn",
                         use_container_width=True, type="primary"):
                _finish()

def _finish():
    st.session_state["_onboard_done"] = True
    st.session_state["_onboard_step"] = 0
    st.session_state.pop("show_onboarding", None)
    st.rerun()

def maybe_show_onboarding():
    """Call from dashboard. Returns True if onboarding shown."""
    if st.session_state.get("show_onboarding"):
        show_onboarding()
        return True
    # Auto-show for brand-new users with no stories
    if (not st.session_state.get("_onboard_done") and
            not st.session_state.get("stories") and
            st.session_state.get("username")):
        st.session_state["show_onboarding"] = True
        show_onboarding()
        return True
    return False
