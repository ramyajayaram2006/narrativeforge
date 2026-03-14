"""
autosave.py — NarrativeForge Auto-Save with Conflict Detection

FIX: no longer imports private _db, _q, _r from database.
     Uses public get_story_updated_at() instead.

INTEGRATION (workspace.py):
  from autosave import autosave_tick, render_autosave_status, _mark_dirty

  In show_workspace(), early in the function:
      autosave_tick(story, username)

  In top nav bar section:
      render_autosave_status(story, username)

  Call _mark_dirty() after any content change.
"""

import time
import streamlit as st
from database import save_story, get_story_updated_at

AUTOSAVE_INTERVAL_SECS = 30
CONFLICT_CHECK         = True


def _mark_dirty():
    st.session_state["_autosave_dirty"] = True

def _mark_clean(timestamp: float):
    st.session_state["_autosave_dirty"]    = False
    st.session_state["_autosave_last_ts"]  = timestamp
    st.session_state["_autosave_last_at"]  = time.time()
    st.session_state["_autosave_status"]   = "saved"
    st.session_state["_autosave_conflict"] = False


def autosave_tick(story: dict, username: str):
    now     = time.time()
    dirty   = st.session_state.get("_autosave_dirty", False)
    last_at = st.session_state.get("_autosave_last_at", 0)
    elapsed = now - last_at

    if "_autosave_last_ts" not in st.session_state:
        db_ts = get_story_updated_at(username, story["id"])
        st.session_state["_autosave_last_ts"]  = db_ts or now
        st.session_state["_autosave_last_at"]  = now
        st.session_state["_autosave_status"]   = "saved"
        st.session_state["_autosave_dirty"]    = False
        st.session_state["_autosave_conflict"] = False

    if not dirty or elapsed < AUTOSAVE_INTERVAL_SECS:
        return

    if CONFLICT_CHECK:
        db_ts    = get_story_updated_at(username, story["id"])
        local_ts = st.session_state.get("_autosave_last_ts", 0)
        if db_ts and local_ts and db_ts > local_ts + 2:
            st.session_state["_autosave_conflict"]    = True
            st.session_state["_autosave_conflict_ts"] = db_ts
            st.session_state["_autosave_status"]      = "conflict"
            return

    try:
        save_story(username, story)
        db_ts = get_story_updated_at(username, story["id"]) or now
        _mark_clean(db_ts)
    except Exception as e:
        st.session_state["_autosave_status"] = f"error: {str(e)[:40]}"


def render_autosave_status(story: dict = None, username: str = None):
    status   = st.session_state.get("_autosave_status", "saved")
    conflict = st.session_state.get("_autosave_conflict", False)
    dirty    = st.session_state.get("_autosave_dirty", False)

    if conflict and story and username:
        st.markdown(
            "<div style='background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.4);"
            "border-radius:10px;padding:12px 16px;margin:8px 0;'>"
            "<div style='font-size:0.82rem;color:#fcd34d;font-weight:700;margin-bottom:6px;'>"
            "⚠️ Conflict — story was saved from another tab or device.</div>"
            "<div style='font-size:0.75rem;color:#E5D9B3;margin-bottom:10px;'>"
            "Keep your version or load the latest saved version.</div></div>",
            unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca:
            if st.button("💾 Keep My Version", use_container_width=True,
                         type="primary", key="conflict_keep"):
                save_story(username, story)
                db_ts = get_story_updated_at(username, story["id"]) or time.time()
                _mark_clean(db_ts)
                st.rerun()
        with cb:
            if st.button("🔄 Load Latest", use_container_width=True, key="conflict_load"):
                from database import load_stories
                fresh   = load_stories(username)
                updated = next((s for s in fresh if s["id"] == story["id"]), None)
                if updated:
                    for i, s in enumerate(st.session_state.stories):
                        if s["id"] == story["id"]:
                            st.session_state.stories[i] = updated
                            break
                db_ts = get_story_updated_at(username, story["id"]) or time.time()
                _mark_clean(db_ts)
                st.rerun()
        return

    if dirty:
        dot, label, color = "●", "unsaved", "#fbbf24"
    elif status == "saved":
        dot, label, color = "●", "saved", "#4ade80"
    elif status.startswith("error"):
        dot, label, color = "●", "save failed", "#f87171"
    else:
        dot, label, color = "●", status, "#8B8F8B"

    st.markdown(
        f"<span style='font-size:0.68rem;color:{color};font-family:monospace;"
        f"display:inline-flex;align-items:center;gap:4px;'>"
        f"<span style='font-size:0.55rem;'>{dot}</span>{label}</span>",
        unsafe_allow_html=True)
