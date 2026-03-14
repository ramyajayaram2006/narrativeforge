"""
achievements.py — NarrativeForge Gamification & Achievement System

FIXES:
  - _streak() now reads from database.get_writing_streak() — was always 0
  - _char_count/_scene_count/_notes_count: initialised from DB on first call
  - check_and_award() persists newly earned achievements to DB
  - show_achievements_panel() loads earned set from DB, not session only
"""

import html as _html
import streamlit as st
from datetime import date, timedelta

# ── Achievement definitions ────────────────────────────────────────────────────
ACHIEVEMENTS = [
    # Writing milestones
    {"id": "first_words",   "icon": "✏️",  "name": "First Words",       "desc": "Write your first 10 words",          "check": lambda s, u: _total_words(s, u) >= 10},
    {"id": "short_story",   "icon": "📄",  "name": "Short Story",       "desc": "Write 1,000 words",                   "check": lambda s, u: _total_words(s, u) >= 1000},
    {"id": "novelette",     "icon": "📖",  "name": "Novelette",         "desc": "Reach 10,000 words",                  "check": lambda s, u: _total_words(s, u) >= 10000},
    {"id": "nanowrimo",     "icon": "🏆",  "name": "NaNoWriMo",         "desc": "Hit 50,000 words",                    "check": lambda s, u: _total_words(s, u) >= 50000},
    {"id": "novelist",      "icon": "📚",  "name": "Novelist",          "desc": "Write 80,000 words",                  "check": lambda s, u: _total_words(s, u) >= 80000},
    # Story count
    {"id": "first_story",   "icon": "🌱",  "name": "First Story",       "desc": "Create your first story",             "check": lambda s, u: _story_count(s, u) >= 1},
    {"id": "storyteller",   "icon": "📙",  "name": "Storyteller",       "desc": "Create 5 stories",                    "check": lambda s, u: _story_count(s, u) >= 5},
    {"id": "plot_master",   "icon": "🗺️",  "name": "Plot Master",       "desc": "Have 10 stories",                     "check": lambda s, u: _story_count(s, u) >= 10},
    # Characters
    {"id": "char_creator",  "icon": "🎭",  "name": "Character Creator", "desc": "Create 5 characters across stories",  "check": lambda s, u: _char_count(u) >= 5},
    {"id": "cast_builder",  "icon": "👥",  "name": "Cast Builder",      "desc": "Create 15 characters",                "check": lambda s, u: _char_count(u) >= 15},
    # Scenes
    {"id": "scene_setter",  "icon": "🎬",  "name": "Scene Setter",      "desc": "Create 10 scenes",                    "check": lambda s, u: _scene_count(u) >= 10},
    # Streaks — FIX: now reads from DB via get_writing_streak()
    {"id": "streak_3",      "icon": "🔥",  "name": "On a Roll",         "desc": "Write 3 days in a row",               "check": lambda s, u: _streak(u) >= 3},
    {"id": "streak_7",      "icon": "🔥🔥","name": "Week Writer",        "desc": "Write 7 days in a row",               "check": lambda s, u: _streak(u) >= 7},
    {"id": "streak_30",     "icon": "💎",  "name": "Monthly Habit",     "desc": "Write 30 days in a row",              "check": lambda s, u: _streak(u) >= 30},
    # Time based
    {"id": "night_owl",     "icon": "🦉",  "name": "Night Owl",         "desc": "Write between midnight and 4am",      "check": lambda s, u: _is_night()},
    {"id": "early_bird",    "icon": "🐦",  "name": "Early Bird",        "desc": "Write between 5am and 7am",           "check": lambda s, u: _is_morning()},
    # Intelligence
    {"id": "analyst",       "icon": "🧠",  "name": "Story Analyst",     "desc": "Run 5 AI analysis tools",             "check": lambda s, u: _analysis_count(u) >= 5},
    {"id": "world_builder_ach", "icon": "🌍", "name": "World Builder",  "desc": "Add 10 world notes",                  "check": lambda s, u: _notes_count(u) >= 10},
    # Export
    {"id": "publisher",     "icon": "📤",  "name": "Publisher",         "desc": "Export your story",                   "check": lambda s, u: _export_count(u) >= 1},
    {"id": "pro_publisher", "icon": "🎓",  "name": "Pro Publisher",     "desc": "Export in 3 different formats",       "check": lambda s, u: _export_count(u) >= 3},
]


# ── DB-backed helpers ─────────────────────────────────────────────────────────

def _total_words(stories, username):
    total = 0
    for s in (stories or []):
        for m in s.get("messages", []):
            if m["role"] == "assistant":
                total += len(m["content"].split())
    return total

def _story_count(stories, username):
    return len(stories or [])

def _init_counts_from_db(username):
    """Load DB-backed counts into session state once per session."""
    init_key = f"_ach_db_loaded_{username}"
    if st.session_state.get(init_key):
        return
    try:
        from database import load_all_characters, load_all_scenes, load_notes
        chars_map  = load_all_characters(username)
        scenes_map = load_all_scenes(username)
        total_chars  = sum(len(v) for v in chars_map.values())
        total_scenes = sum(len(v) for v in scenes_map.values())
        st.session_state[f"_ach_chars_{username}"]  = total_chars
        st.session_state[f"_ach_scenes_{username}"] = total_scenes
    except Exception:
        pass
    st.session_state[init_key] = True

def _char_count(username):
    _init_counts_from_db(username)
    return st.session_state.get(f"_ach_chars_{username}", 0)

def _scene_count(username):
    _init_counts_from_db(username)
    return st.session_state.get(f"_ach_scenes_{username}", 0)

def _notes_count(username):
    return st.session_state.get(f"_ach_notes_{username}", 0)

def _analysis_count(username):
    return st.session_state.get(f"_ach_analysis_{username}", 0)

def _export_count(username):
    return st.session_state.get(f"_ach_exports_{username}", 0)

def _streak(username):
    """FIX: reads from DB instead of always-empty session state."""
    cache_key = f"_ach_streak_cache_{username}"
    cache_ts  = f"_ach_streak_ts_{username}"
    import time
    now = time.time()
    # Cache for 5 minutes to avoid DB hit on every rerender
    if now - st.session_state.get(cache_ts, 0) < 300:
        return st.session_state.get(cache_key, 0)
    try:
        from database import get_writing_streak
        val = get_writing_streak(username)
    except Exception:
        val = 0
    st.session_state[cache_key] = val
    st.session_state[cache_ts]  = now
    return val

def _is_night():
    import datetime
    h = datetime.datetime.now().hour
    return 0 <= h < 4

def _is_morning():
    import datetime
    h = datetime.datetime.now().hour
    return 5 <= h < 7


# ── Track events (call from workspace / other modules) ───────────────────────

def record_chars(username, count):
    key = f"_ach_chars_{username}"
    st.session_state[key] = st.session_state.get(key, 0) + count

def record_scenes(username, count):
    key = f"_ach_scenes_{username}"
    st.session_state[key] = st.session_state.get(key, 0) + count

def record_notes(username, count):
    key = f"_ach_notes_{username}"
    st.session_state[key] = st.session_state.get(key, 0) + count

def record_analysis(username):
    key = f"_ach_analysis_{username}"
    st.session_state[key] = st.session_state.get(key, 0) + 1

def record_export(username):
    key = f"_ach_exports_{username}"
    st.session_state[key] = st.session_state.get(key, 0) + 1


# ── Check and award ───────────────────────────────────────────────────────────

def check_and_award(stories, username):
    """
    Check all achievements and return newly earned ones.
    FIX: loads earned set from DB, persists new unlocks to DB.
    """
    try:
        from database import load_achievements, unlock_achievement
        earned = load_achievements(username)
    except Exception:
        earned = st.session_state.get(f"_earned_ach_{username}", set())

    newly = []
    for ach in ACHIEVEMENTS:
        if ach["id"] in earned:
            continue
        try:
            if ach["check"](stories, username):
                try:
                    from database import unlock_achievement
                    unlock_achievement(username, ach["id"])
                except Exception:
                    pass
                earned.add(ach["id"])
                newly.append(ach)
        except Exception:
            pass

    # Keep session cache in sync
    st.session_state[f"_earned_ach_{username}"] = earned
    return newly


def show_new_achievement(ach):
    """Display celebration popup for new achievement."""
    st.balloons()
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(77,107,254,0.15),rgba(168,188,255,0.08));"
        f"border:1px solid rgba(77,107,254,0.4);border-radius:14px;padding:20px;text-align:center;"
        f"margin-bottom:12px;'>"
        f"<div style='font-size:2.5rem;'>{ach['icon']}</div>"
        f"<div style='font-size:1.1rem;font-weight:700;color:#A8BCFF;margin:6px 0 4px;'>"
        f"🏅 Achievement Unlocked!</div>"
        f"<div style='font-size:1rem;font-weight:600;color:var(--text-primary);'>{ach['name']}</div>"
        f"<div style='font-size:0.78rem;color:#6B7080;margin-top:4px;'>{ach['desc']}</div>"
        f"</div>",
        unsafe_allow_html=True)


# ── Achievement display panel ─────────────────────────────────────────────────

def show_achievements_panel(stories, username):
    """Full achievements gallery. FIX: loads from DB."""
    try:
        from database import load_achievements
        earned = load_achievements(username)
        # Sync to session
        st.session_state[f"_earned_ach_{username}"] = earned
    except Exception:
        earned = st.session_state.get(f"_earned_ach_{username}", set())

    total_earned = len(earned)
    total_avail  = len(ACHIEVEMENTS)
    pct = total_earned / total_avail if total_avail else 0

    st.markdown(
        f"<div style='margin-bottom:12px;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;"
        f"color:#6B7080;margin-bottom:4px;'>"
        f"<span>Achievements</span><span>{total_earned}/{total_avail} earned</span></div>"
        f"<div style='background:rgba(77,107,254,0.12);border-radius:6px;height:8px;'>"
        f"<div style='background:linear-gradient(90deg,#4D6BFE,#A8BCFF);"
        f"width:{pct*100:.0f}%;height:8px;border-radius:6px;'></div></div></div>",
        unsafe_allow_html=True)

    html_parts = ["<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:8px;'>"]
    for ach in ACHIEVEMENTS:
        is_earned    = ach["id"] in earned
        opacity      = "1.0" if is_earned else "0.35"
        bg           = "rgba(77,107,254,0.12)" if is_earned else "rgba(77,107,254,0.04)"
        border       = "rgba(77,107,254,0.35)" if is_earned else "rgba(77,107,254,0.08)"
        earned_badge = "<div style='font-size:0.55rem;color:#4ADE80;'>✓ EARNED</div>" if is_earned else ""
        html_parts.append(
            f"<div title='{_html.escape(ach['desc'])}' "
            f"style='background:{bg};border:1px solid {border};border-radius:10px;"
            f"padding:10px 6px;text-align:center;opacity:{opacity};'>"
            f"<div style='font-size:1.6rem;'>{ach['icon']}</div>"
            f"<div style='font-size:0.68rem;font-weight:600;color:var(--text-primary);"
            f"margin-top:4px;line-height:1.2;'>{_html.escape(ach['name'])}</div>"
            f"{earned_badge}</div>")
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
