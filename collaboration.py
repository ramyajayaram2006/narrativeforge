"""
collaboration.py — NarrativeForge Story Collaboration & Share Links
═══════════════════════════════════════════════════════════════════

Two modes:
  1. READ-ONLY SHARE LINK  — generate a URL token. Anyone with the link
     can read the story in a clean view (no editing, no login required).
  2. WRITE INVITE          — invite a collaborator by username. They can
     co-write (add messages) but cannot change settings or delete.

URL scheme (Streamlit query params):
  /?share=TOKEN              → Read-only public view
  /?collab=TOKEN             → Collaborator write view (must be logged in)

HOW TO INTEGRATE:
  1. Call init_collab_tables() inside database.init_db()
  2. In app.py, add query-param routing BEFORE the auth check:
       params = st.query_params
       if "share" in params:
           from collaboration import show_shared_story
           show_shared_story(params["share"])
           st.stop()
  3. In workspace.py sidebar, call render_collaboration_panel(story)
"""

import os
import time
import secrets
import json
import streamlit as st

# Reuse database internals — _USE_PG imported directly, not recomputed
from database import _db, _q, _r, _USE_PG, load_stories, save_story


# ── Local helpers (previously imported from workspace — removed fragile dep) ──
def _word_count(story):
    return sum(len(m["content"].split()) for m in story.get("messages", []))

def _reading_time(story):
    wc = _word_count(story)
    return f"~{max(1, round(wc / 200))} min read"


# ══════════════════════════════════════════════════════════════
#  Database helpers — call init_collab_tables() in init_db()
# ══════════════════════════════════════════════════════════════

def init_collab_tables():
    """Creates share_tokens and collaborators tables. Idempotent."""
    _pk  = "SERIAL PRIMARY KEY" if _USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    _ts  = "TIMESTAMPTZ"        if _USE_PG else "TIMESTAMP"

    ddl = [
        f"""CREATE TABLE IF NOT EXISTS share_tokens (
            id {_pk},
            token TEXT UNIQUE NOT NULL,
            story_key TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'read',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP,
            expires_at {_ts} DEFAULT NULL,
            views INTEGER DEFAULT 0
        )""",
        f"""CREATE TABLE IF NOT EXISTS collaborators (
            id {_pk},
            story_key TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            collaborator_username TEXT NOT NULL,
            token TEXT NOT NULL,
            invited_at {_ts} DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_key, collaborator_username)
        )""",
    ]
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_tokens_token   ON share_tokens(token)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_story   ON share_tokens(story_key,owner_username)",
        "CREATE INDEX IF NOT EXISTS idx_collab_story   ON collaborators(story_key,owner_username)",
        "CREATE INDEX IF NOT EXISTS idx_collab_user    ON collaborators(collaborator_username)",
    ]
    with _db() as (conn, cur):
        for stmt in ddl + indexes:
            cur.execute(stmt)


# ── Token management ──────────────────────────────────────────────────────────

def create_share_token(owner_username: str, story_id: str,
                        mode: str = "read", expires_hours: int = 0) -> str:
    """
    Generate a secure share token.
    mode: "read" (public read-only) | "write" (collaborator invite)
    expires_hours: 0 = never expires
    Returns the token string.
    """
    token = secrets.token_urlsafe(24)  # 32-char URL-safe string

    if expires_hours > 0:
        import datetime
        exp = datetime.datetime.utcnow() + datetime.timedelta(hours=expires_hours)
        exp_str = exp.isoformat()
    else:
        exp_str = None

    if _USE_PG:
        sql = ("INSERT INTO share_tokens (token,story_key,owner_username,mode,expires_at) "
               "VALUES (%s,%s,%s,%s,%s)")
    else:
        sql = ("INSERT INTO share_tokens (token,story_key,owner_username,mode,expires_at) "
               "VALUES (?,?,?,?,?)")

    with _db() as (conn, cur):
        cur.execute(sql, (token, story_id, owner_username, mode, exp_str))
    return token


def get_token_info(token: str) -> dict | None:
    """
    Returns token metadata dict or None if invalid/expired.
    Also increments the view counter for read tokens.
    """
    with _db() as (conn, cur):
        cur.execute(_q("SELECT story_key, owner_username, mode, expires_at, views "
                       "FROM share_tokens WHERE token=?"), (token,))
        row = cur.fetchone()
    if not row:
        return None

    if _USE_PG:
        story_key  = row["story_key"]
        owner      = row["owner_username"]
        mode       = row["mode"]
        expires_at = row["expires_at"]
        views      = row["views"]
    else:
        story_key, owner, mode, expires_at, views = row[0], row[1], row[2], row[3], row[4]

    # Check expiry
    if expires_at:
        import datetime
        exp = datetime.datetime.fromisoformat(str(expires_at).replace("Z",""))
        if datetime.datetime.utcnow() > exp:
            return None

    # Increment view count (fire-and-forget, don't block on failure)
    try:
        with _db() as (conn, cur):
            cur.execute(_q("UPDATE share_tokens SET views=views+1 WHERE token=?"), (token,))
    except Exception:
        pass

    return {"story_key": story_key, "owner": owner, "mode": mode, "views": views}


def revoke_token(token: str, owner_username: str):
    """Delete a share token. Owner must match for security."""
    with _db() as (conn, cur):
        cur.execute(_q("DELETE FROM share_tokens WHERE token=? AND owner_username=?"),
                    (token, owner_username))


def list_tokens(owner_username: str, story_id: str) -> list:
    """List all active tokens for a story."""
    with _db() as (conn, cur):
        cur.execute(_q("SELECT token, mode, created_at, expires_at, views "
                       "FROM share_tokens WHERE story_key=? AND owner_username=? "
                       "ORDER BY created_at DESC"),
                    (story_id, owner_username))
        rows = cur.fetchall()
    result = []
    for r in rows:
        if _USE_PG:
            result.append({"token": r["token"], "mode": r["mode"],
                            "created_at": str(r["created_at"]),
                            "expires_at": str(r["expires_at"]) if r["expires_at"] else None,
                            "views": r["views"]})
        else:
            result.append({"token": r[0], "mode": r[1], "created_at": r[2],
                            "expires_at": r[3], "views": r[4] or 0})
    return result


def add_collaborator(owner_username: str, story_id: str,
                      collaborator_username: str) -> dict:
    """
    Invite a collaborator by username. Creates a write token for them.
    Returns {"ok": True, "token": "..."} or {"ok": False, "error": "..."}
    """
    from database import user_exists
    if not user_exists(collaborator_username):
        return {"ok": False, "error": f"User '{collaborator_username}' not found."}
    if collaborator_username == owner_username:
        return {"ok": False, "error": "You can't collaborate with yourself."}

    token = create_share_token(owner_username, story_id, mode="write")
    ph = "%s" if _USE_PG else "?"
    try:
        with _db() as (conn, cur):
            cur.execute(
                f"INSERT INTO collaborators (story_key,owner_username,collaborator_username,token) "
                f"VALUES ({ph},{ph},{ph},{ph})",
                (story_id, owner_username, collaborator_username, token)
            )
        return {"ok": True, "token": token}
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg:
            return {"ok": False, "error": f"'{collaborator_username}' is already a collaborator."}
        return {"ok": False, "error": str(e)}


def get_collaborators(owner_username: str, story_id: str) -> list:
    with _db() as (conn, cur):
        cur.execute(_q("SELECT collaborator_username, token, invited_at "
                       "FROM collaborators WHERE story_key=? AND owner_username=?"),
                    (story_id, owner_username))
        rows = cur.fetchall()
    if _USE_PG:
        return [{"username": r["collaborator_username"], "token": r["token"],
                 "invited_at": str(r["invited_at"])} for r in rows]
    return [{"username": r[0], "token": r[1], "invited_at": r[2]} for r in rows]


def remove_collaborator(owner_username: str, story_id: str, collaborator_username: str):
    with _db() as (conn, cur):
        # Revoke their write token too
        cur.execute(_q("SELECT token FROM collaborators WHERE story_key=? AND owner_username=? "
                       "AND collaborator_username=?"),
                    (story_id, owner_username, collaborator_username))
        row = cur.fetchone()
        if row:
            token = row["token"] if hasattr(row, "keys") else row[0]
            cur.execute(_q("DELETE FROM share_tokens WHERE token=?"), (token,))
        cur.execute(_q("DELETE FROM collaborators WHERE story_key=? AND owner_username=? "
                       "AND collaborator_username=?"),
                    (story_id, owner_username, collaborator_username))


# ══════════════════════════════════════════════════════════════
#  Streamlit views
# ══════════════════════════════════════════════════════════════

def show_shared_story(token: str):
    """
    Public read-only view for share links. No login required.
    Call from app.py when ?share=TOKEN is in query params.
    """
    from styles import workspace_style
    workspace_style()

    info = get_token_info(token)
    if not info:
        st.error("⚠️ This share link is invalid or has expired.")
        if st.button("← Go to NarrativeForge"):
            st.query_params.clear()
            st.rerun()
        return

    # Load the story
    from database import load_stories
    stories = load_stories(info["owner"])
    story   = next((s for s in stories if s["id"] == info["story_key"]), None)
    if not story:
        st.error("Story not found.")
        return

    import html as _html
    # _word_count and _reading_time are defined locally at top of this module

    # Header
    st.markdown(f"""
        <div style='background:rgba(201,169,89,0.06);border:1px solid rgba(201,169,89,0.15);
        border-radius:12px;padding:16px 20px;margin-bottom:20px;'>
            <div style='font-family:"Playfair Display",serif;font-size:1.6rem;
            font-weight:700;color:#C9A959;'>{_html.escape(story["title"])}</div>
            <div style='font-size:0.78rem;color:#8B8F8B;margin-top:4px;'>
                Shared by <strong style='color:#E5D9B3;'>{_html.escape(info["owner"])}</strong>
                &nbsp;·&nbsp; {_html.escape(story["genre"])}
                &nbsp;·&nbsp; {_word_count(story):,} words
                &nbsp;·&nbsp; {_reading_time(story)}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Prose
    ai_msgs = [m for m in story.get("messages", [])
               if m["role"] == "assistant"
               and not m["content"].startswith("◆")
               and not m["content"].startswith("[Revision")]

    if not ai_msgs:
        st.markdown("<div style='color:#8B8F8B;text-align:center;padding:40px;'>No content yet.</div>",
                    unsafe_allow_html=True)
    else:
        prose = "\n\n".join(m["content"] for m in ai_msgs)
        paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip()]
        html_parts = ["<div style='max-width:680px;margin:0 auto;font-family:\"Playfair Display\","
                      "Georgia,serif;font-size:1.1rem;line-height:1.9;color:#F5F2E9;'>"]
        for para in paragraphs:
            html_parts.append(f"<p style='margin-bottom:1.4em;text-indent:2em;'>{_html.escape(para)}</p>")
        html_parts.append("</div>")
        st.markdown("".join(html_parts), unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(201,169,89,0.15);margin:32px 0;'>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;font-size:0.72rem;color:#555955;font-family:monospace;'>"
        "Read-only view · Shared via NarrativeForge · <a href='/' style='color:#C9A959;'>Create your own story</a></p>",
        unsafe_allow_html=True)


def render_collaboration_panel(story: dict):
    """
    Renders the collaboration panel in the workspace sidebar.
    Add as a new tab (e.g. t11) in show_workspace().
    """
    username = st.session_state.get("username", "")
    story_id = story["id"]

    # ── Public share link ──────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;color:#8B8F8B;font-weight:600;text-transform:uppercase;"
        "letter-spacing:0.1em;margin-bottom:8px;'>🔗 Share This Story</div>",
        unsafe_allow_html=True)

    tokens = list_tokens(username, story_id)
    read_tokens = [t for t in tokens if t["mode"] == "read"]

    if read_tokens:
        for t in read_tokens:
            app_url  = os.environ.get("NARRATIVEFORGE_URL", "http://localhost:8501")
            link     = f"{app_url}/?share={t['token']}"
            views    = t.get("views", 0)
            exp_note = f" · expires {t['expires_at'][:10]}" if t.get("expires_at") else " · no expiry"
            st.markdown(
                f"<div style='background:rgba(74,222,128,0.06);border:1px solid rgba(74,222,128,0.18);"
                f"border-radius:8px;padding:8px 12px;margin-bottom:6px;'>"
                f"<div style='font-size:0.7rem;color:#4ade80;margin-bottom:4px;'>✓ Active link · {views} view(s){exp_note}</div>"
                f"<div style='font-size:0.72rem;color:#E5D9B3;word-break:break-all;'>{link}</div>"
                f"</div>",
                unsafe_allow_html=True)
            st.text_input("Copy link", value=link, key=f"share_link_{t['token']}",
                          label_visibility="collapsed")
            col_r, col_x = st.columns(2)
            with col_r:
                if st.button("🔄 New Link", key=f"new_link_{t['token']}", use_container_width=True):
                    revoke_token(t["token"], username)
                    new_tok = create_share_token(username, story_id, mode="read")
                    st.rerun()
            with col_x:
                if st.button("🗑 Revoke", key=f"rev_link_{t['token']}", use_container_width=True):
                    revoke_token(t["token"], username)
                    st.rerun()
    else:
        exp_options = {"Never": 0, "24 hours": 24, "7 days": 168, "30 days": 720}
        exp_choice  = st.selectbox("Link expiry", list(exp_options.keys()), key="share_expiry")
        if st.button("🔗 Generate Share Link", use_container_width=True, type="primary",
                     key="gen_share_link"):
            token = create_share_token(username, story_id, mode="read",
                                        expires_hours=exp_options[exp_choice])
            st.rerun()

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── Write collaborators ────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;color:#8B8F8B;font-weight:600;text-transform:uppercase;"
        "letter-spacing:0.1em;margin-bottom:8px;'>✍️ Collaborators</div>",
        unsafe_allow_html=True)

    collabs = get_collaborators(username, story_id)
    if collabs:
        for c in collabs:
            st.markdown(
                f"<div style='background:rgba(201,169,89,0.06);border:1px solid rgba(201,169,89,0.15);"
                f"border-radius:8px;padding:8px 12px;margin-bottom:4px;display:flex;"
                f"align-items:center;justify-content:space-between;'>"
                f"<span style='font-size:0.82rem;color:#E5D9B3;'>👤 {c['username']}</span>"
                f"</div>",
                unsafe_allow_html=True)
            if st.button(f"Remove {c['username']}", key=f"rm_collab_{c['username']}",
                         use_container_width=True):
                remove_collaborator(username, story_id, c["username"])
                st.rerun()
    else:
        st.markdown(
            "<div style='color:#8B8F8B;font-size:0.78rem;margin-bottom:8px;'>"
            "No collaborators yet. Invite by username.</div>",
            unsafe_allow_html=True)

    with st.expander("➕ Invite Collaborator"):
        inv_user = st.text_input("Username to invite", key="invite_username",
                                  placeholder="e.g. jane_doe", max_chars=50)
        if st.button("Send Invite", use_container_width=True, key="send_invite",
                     type="primary"):
            if inv_user.strip():
                result = add_collaborator(username, story_id, inv_user.strip())
                if result["ok"]:
                    st.success(f"✓ {inv_user.strip()} has been added as a collaborator.")
                    app_url = os.environ.get("NARRATIVEFORGE_URL", "http://localhost:8501")
                    collab_link = f"{app_url}/?collab={result['token']}"
                    st.info(f"Share this link with them: {collab_link}")
                    st.rerun()
                else:
                    st.error(result["error"])


# ── app.py integration snippet ─────────────────────────────────────────────────
"""
Add to app.py, BEFORE the authentication routing block:

    from collaboration import show_shared_story, init_collab_tables
    init_collab_tables()   # add to init_db() or call here

    # Handle share links (no auth required)
    params = st.query_params
    if "share" in params:
        show_shared_story(params["share"])
        st.stop()
"""
