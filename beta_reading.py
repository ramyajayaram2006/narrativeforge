"""
NarrativeForge — Beta Reading Platform
Generate shareable read-only links for beta readers.
Readers can leave inline comments + star ratings per chapter.
Authors see a feedback dashboard with all reader notes.
"""
import html as _html
import streamlit as st
from database import (create_beta_session, load_beta_sessions,
                      get_beta_session_by_token, add_beta_feedback,
                      delete_beta_session)


# ── Helpers ────────────────────────────────────────────────────────────────
def _prose_from_story(story):
    return [m for m in story.get("messages", [])
            if m.get("role") == "assistant"
            and not m["content"].startswith("◆")]

def _wc(story):
    return len(" ".join(m["content"] for m in _prose_from_story(story)).split())


# ── Rating stars ───────────────────────────────────────────────────────────
def _stars(rating, max_stars=5):
    filled = "★" * int(rating)
    empty  = "☆" * (max_stars - int(rating))
    return f"<span style='color:#fbbf24;'>{filled}</span><span style='color:#333;'>{empty}</span>"


# ── Author: Beta Sessions Manager ─────────────────────────────────────────
def show_beta_panel(story, username):
    """Author view: create sessions, view feedback."""

    prose_msgs = _prose_from_story(story)
    wc = _wc(story)

    if wc < 100:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;text-align:center;padding:24px;'>"
            "Write at least 100 words before sharing with beta readers.</div>",
            unsafe_allow_html=True)
        return

    # ── Create new session ─────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>"
        "🔗 Share With Beta Readers</div>",
        unsafe_allow_html=True)

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        reader_name = st.text_input("Reader name (optional)",
            placeholder="e.g. Alice, Writing Group", key="beta_reader_name",
            label_visibility="collapsed")
    with c2:
        expires_days = st.selectbox("Link expires", [7, 14, 30, 60, 90],
            format_func=lambda x: f"{x} days", key="beta_expires",
            label_visibility="collapsed")
    with c3:
        if st.button("🔗 Create Link", key="beta_create", use_container_width=True):
            token = create_beta_session(
                username, story["id"],
                reader_name or "Anonymous", expires_days)
            if token:
                st.session_state["beta_new_token"] = token
                st.rerun()

    # Show newly created link
    if new_token := st.session_state.get("beta_new_token"):
        base_url = st.session_state.get("base_url", "http://localhost:8501")
        share_url = f"{base_url}/?beta_token={new_token}"
        st.markdown(
            f"<div style='background:rgba(52,211,153,0.08);"
            f"border:1px solid rgba(52,211,153,0.35);border-radius:8px;"
            f"padding:12px 14px;margin-bottom:10px;'>"
            f"<div style='font-size:0.72rem;color:#34d399;font-weight:700;margin-bottom:6px;'>"
            f"✅ Link created — share this URL:</div>"
            f"<div style='font-family:monospace;font-size:0.78rem;color:#C5C8D4;"
            f"word-break:break-all;background:rgba(0,0,0,0.3);padding:8px;"
            f"border-radius:6px;'>{_html.escape(share_url)}</div>"
            f"<div style='font-size:0.68rem;color:#6B7080;margin-top:6px;'>"
            f"Reader sees your story + can leave inline comments. "
            f"No account needed.</div></div>",
            unsafe_allow_html=True)
        if st.button("✖ Dismiss", key="beta_dismiss_token"):
            st.session_state.pop("beta_new_token", None)
            st.rerun()

    st.markdown("---")

    # ── Existing sessions + feedback ───────────────────────────────────────
    sessions = load_beta_sessions(username, story["id"])

    if not sessions:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.78rem;text-align:center;padding:16px;'>"
            "No beta readers yet. Create a link above to share your story.</div>",
            unsafe_allow_html=True)
        return

    # Aggregate stats
    total_comments = sum(len(s["feedback"]) for s in sessions)
    all_ratings    = [f["rating"] for s in sessions for f in s["feedback"] if "rating" in f]
    avg_rating     = sum(all_ratings) / len(all_ratings) if all_ratings else 0

    sc1, sc2, sc3 = st.columns(3)
    with sc1: st.metric("👥 Readers", len(sessions))
    with sc2: st.metric("💬 Comments", total_comments)
    with sc3: st.metric("⭐ Avg Rating", f"{avg_rating:.1f}/5" if avg_rating else "—")

    st.markdown("---")

    # Per-session cards
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>"
        "📋 Beta Reader Sessions</div>",
        unsafe_allow_html=True)

    for sess in sessions:
        fb    = sess.get("feedback", [])
        n_fb  = len(fb)
        avg_r = sum(f.get("rating", 0) for f in fb) / n_fb if n_fb else 0
        base_url = st.session_state.get("base_url", "http://localhost:8501")
        link  = f"{base_url}/?beta_token={sess['token']}"

        st.markdown(
            f"<div style='border:1px solid var(--primary-border);border-radius:8px;"
            f"padding:10px 12px;margin-bottom:6px;background:var(--bg-card);'>"
            f"<div style='display:flex;justify-content:space-between;align-items:start;'>"
            f"<div>"
            f"<div style='font-size:0.82rem;font-weight:700;color:#A8BCFF;'>"
            f"👤 {_html.escape(sess['reader_name'])}</div>"
            f"<div style='font-size:0.68rem;color:#6B7080;'>"
            f"Created {sess['created_at']} · Expires {sess['expires_at']}</div>"
            f"</div>"
            f"<div style='text-align:right;'>"
            f"<div style='font-size:0.80rem;'>{_stars(avg_r)}</div>"
            f"<div style='font-size:0.68rem;color:#6B7080;'>{n_fb} comment{'s' if n_fb!=1 else ''}</div>"
            f"</div></div>"
            f"<div style='font-size:0.68rem;color:#4D6BFE;font-family:monospace;"
            f"margin-top:6px;word-break:break-all;'>{_html.escape(link)}</div>"
            f"</div>",
            unsafe_allow_html=True)

        # Show feedback inline
        if fb:
            with st.expander(f"💬 View {n_fb} comment(s) from {sess['reader_name']}"):
                for item in fb:
                    rating = item.get("rating", 0)
                    st.markdown(
                        f"<div style='border-left:3px solid #4D6BFE;padding:6px 10px;"
                        f"margin-bottom:6px;background:var(--primary-dim);border-radius:0 6px 6px 0;'>"
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:center;margin-bottom:3px;'>"
                        f"<span style='font-size:0.68rem;color:#6B7080;'>"
                        f"📍 {_html.escape(item.get('chapter','General'))} · {item.get('at','')}</span>"
                        f"<span style='font-size:0.80rem;'>{_stars(rating)}</span></div>"
                        f"<div style='font-size:0.80rem;color:var(--text-primary);line-height:1.5;'>"
                        f"{_html.escape(item.get('comment',''))}</div></div>",
                        unsafe_allow_html=True)

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button(f"📋 Copy link", key=f"beta_copy_{sess['id']}",
                         use_container_width=True):
                st.code(link)
        with bc2:
            if st.button(f"🗑 Revoke", key=f"beta_revoke_{sess['id']}",
                         use_container_width=True):
                delete_beta_session(sess["id"], username)
                st.rerun()


# ── Reader: Public reading view ────────────────────────────────────────────
def show_beta_reader_view(token):
    """
    Shown to beta readers who access via ?beta_token=...
    Loads story in read-only mode with a comment sidebar.
    """
    from database import load_story

    sess = get_beta_session_by_token(token)
    if not sess:
        st.error("❌ This beta reading link is invalid or has expired.")
        return

    # Load the story
    story = load_story(sess["username"], sess["story_key"])
    if not story:
        st.error("❌ Story not found.")
        return

    prose_msgs = [m for m in story.get("messages", [])
                  if m.get("role") == "assistant"
                  and not m["content"].startswith("◆")]

    if not prose_msgs:
        st.info("The author hasn't written anything yet.")
        return

    # Inject reader CSS
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        .beta-header { background: linear-gradient(135deg,#161820,#1a1c2e);
          border-bottom:1px solid rgba(77,107,254,0.3);padding:12px 24px;
          display:flex;justify-content:space-between;align-items:center; }
        .beta-prose { max-width:680px;margin:0 auto;padding:40px 24px 80px;
          font-family:Georgia,serif;font-size:1.05rem;line-height:1.9;
          color:#C5C8D4; }
        .beta-prose p { text-indent:2em;margin-bottom:0.8em; }
        .beta-prose p:first-child { text-indent:0; }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown(
        f"<div class='beta-header'>"
        f"<div><span style='color:#4D6BFE;font-weight:700;font-size:1rem;'>◆ NarrativeForge</span>"
        f" <span style='color:#6B7080;font-size:0.78rem;margin-left:8px;'>Beta Read</span></div>"
        f"<div style='color:#6B7080;font-size:0.78rem;'>"
        f"Reading: <strong style='color:#A8BCFF;'>"
        f"{_html.escape(story.get('title','Untitled'))}</strong></div></div>",
        unsafe_allow_html=True)

    # Story content
    for i, msg in enumerate(prose_msgs):
        para_html = "".join(
            f"<p>{_html.escape(p)}</p>"
            for p in msg["content"].split("\n\n") if p.strip())
        st.markdown(f"<div class='beta-prose'>{para_html}</div>",
                    unsafe_allow_html=True)

    st.markdown("---")

    # Leave feedback
    st.markdown(
        "<div style='max-width:680px;margin:0 auto;padding:0 24px 60px;'>"
        "<div style='font-size:1rem;font-weight:700;color:#A8BCFF;margin-bottom:12px;'>"
        "💬 Leave Feedback</div></div>",
        unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 1])
    with col_a:
        chapter_ref = st.text_input("Which chapter/section?",
            placeholder="e.g. Chapter 1, Opening scene, General",
            key="beta_chapter_ref")
    with col_b:
        rating = st.select_slider("Rating", [1, 2, 3, 4, 5], value=4,
            key="beta_rating",
            format_func=lambda x: "★" * x)

    comment = st.text_area("Your thoughts",
        height=100, key="beta_comment",
        placeholder="What worked? What didn't? Any questions or suggestions?")

    if comment.strip() and st.button("📤 Submit Feedback", key="beta_submit",
                                      use_container_width=True):
        ok = add_beta_feedback(token, comment.strip(), rating, chapter_ref or "General")
        if ok:
            st.success("✅ Feedback submitted! Thank you for being a beta reader.")
        else:
            st.error("Failed to save feedback. Please try again.")


# ── Route handler (call from app.py) ──────────────────────────────────────
def check_beta_token():
    """
    Call from app.py before auth check.
    If ?beta_token= in URL, show reader view instead of login.
    Returns True if handled.
    """
    params = st.query_params
    token  = params.get("beta_token")
    if token:
        show_beta_reader_view(token)
        return True
    return False
