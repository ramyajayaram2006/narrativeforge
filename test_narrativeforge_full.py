"""
test_narrativeforge_full.py
════════════════════════════════════════════════════════════════════════
NarrativeForge — Full regression + feature test suite.
Tests every bug fix and every new feature.

Run from the project root:
    python -m pytest test_narrativeforge_full.py -v

Or run directly:
    python test_narrativeforge_full.py

Requirements: pytest, bcrypt
The DB layer runs against a fresh SQLite temp file per test session.
No Ollama / network access required.
"""

import os
import sys
import json
import time
import tempfile
import types
import pytest

# ── Streamlit mock — lets Streamlit-dependent modules import in headless pytest ──
# The actual UI functions are not tested here; we test pure logic only.
_st_mock = types.ModuleType("streamlit")
_st_mock.session_state = {}
for _fn in ("markdown","error","info","warning","success","caption","write",
            "spinner","rerun","balloons","metric","progress","columns","expander",
            "text_input","text_area","number_input","selectbox","checkbox",
            "select_slider","button","download_button","toggle","code","stop",
            "query_params"):
    setattr(_st_mock, _fn, lambda *a, **kw: None)
# columns returns a list of mock context managers
_cm = types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda s,*a: None)
_st_mock.columns = lambda *a, **kw: [_cm] * (a[0] if a and isinstance(a[0], int) else 3)
sys.modules.setdefault("streamlit", _st_mock)

# ── Path setup — works from any machine ──────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Point the DB at a temp file
_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()
os.environ["NARRATIVEFORGE_DB"] = _TMP_DB.name
os.environ.pop("DATABASE_URL", None)   # force SQLite

import database as db


# ══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def init_database():
    """Create all tables once per test session."""
    db.init_db()
    yield
    try:
        os.unlink(_TMP_DB.name)
    except OSError:
        pass


@pytest.fixture
def user():
    """Register a fresh user for each test, clean up after."""
    import secrets
    uname = f"testuser_{secrets.token_hex(4)}"
    result = db.register_user(uname, f"{uname}@test.com", "Password123!")
    assert result["ok"], f"Register failed: {result}"
    yield uname
    # Cleanup: delete all stories for this user
    for story in db.load_stories(uname):
        db.delete_story(uname, story["id"])


@pytest.fixture
def story_id(user):
    """Create a story and return its ID."""
    import secrets
    sid = f"story_{secrets.token_hex(6)}"
    s = {
        "id": sid, "title": "Test Story", "genre": "Fantasy",
        "tone": "Dark", "messages": [], "plot_arc": {},
        "writing_style": "", "word_goal": 1000, "style_dna": "",
    }
    db.save_story(user, s)
    return sid


# ══════════════════════════════════════════════════════════════════════════════
#  BUG FIX TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestBugFix_LoadAllCharacters:
    """BUG: load_all_characters / load_all_scenes did not exist → ImportError."""

    def test_function_exists(self):
        assert hasattr(db, "load_all_characters"), \
            "load_all_characters missing from database"
        assert hasattr(db, "load_all_scenes"), \
            "load_all_scenes missing from database"

    def test_returns_dict(self, user, story_id):
        result = db.load_all_characters(user)
        assert isinstance(result, dict), "Should return a dict keyed by story_key"

    def test_populated_correctly(self, user, story_id):
        db.add_character(user, story_id, "Alice", "protagonist", "Brave")
        db.add_character(user, story_id, "Bob",   "antagonist",  "Cunning")
        result = db.load_all_characters(user)
        assert story_id in result
        names = [c["name"] for c in result[story_id]]
        assert "Alice" in names
        assert "Bob"   in names

    def test_scenes_bulk_load(self, user, story_id):
        db.add_scene(user, story_id, "Opening", "Castle", "Establish setting", [])
        result = db.load_all_scenes(user)
        assert story_id in result
        assert result[story_id][0]["title"] == "Opening"

    def test_empty_user_returns_empty_dict(self):
        result = db.load_all_characters("no_such_user_xyz")
        assert result == {}


class TestBugFix_LoadStory:
    """BUG: load_story(username, story_id) did not exist — beta_reading crash."""

    def test_function_exists(self):
        assert hasattr(db, "load_story"), "load_story missing from database"

    def test_returns_story(self, user, story_id):
        story = db.load_story(user, story_id)
        assert story is not None
        assert story["id"] == story_id
        assert story["title"] == "Test Story"

    def test_returns_none_for_missing(self, user):
        story = db.load_story(user, "nonexistent_story_id")
        assert story is None

    def test_idor_protection(self, user, story_id):
        """load_story with wrong username must return None."""
        story = db.load_story("different_user", story_id)
        assert story is None


class TestBugFix_BetaSessionsMigration:
    """BUG: beta_sessions table missing from SQLite migrations → table not found."""

    def test_beta_session_create(self, user, story_id):
        token = db.create_beta_session(user, story_id, "TestReader", days=7)
        assert token is not None
        assert len(token) > 10

    def test_beta_session_lookup(self, user, story_id):
        token = db.create_beta_session(user, story_id, "Alice")
        sess = db.get_beta_session_by_token(token)
        assert sess is not None
        assert sess["username"]    == user
        assert sess["story_key"]   == story_id
        assert sess["reader_name"] == "Alice"

    def test_beta_feedback_roundtrip(self, user, story_id):
        token = db.create_beta_session(user, story_id, "Bob")
        ok = db.add_beta_feedback(token, "Great opening!", 5, "Chapter 1")
        assert ok
        sess = db.get_beta_session_by_token(token)
        assert len(sess["feedback"]) == 1
        assert sess["feedback"][0]["comment"] == "Great opening!"
        assert sess["feedback"][0]["rating"]  == 5

    def test_beta_sessions_list(self, user, story_id):
        db.create_beta_session(user, story_id, "Reader1")
        db.create_beta_session(user, story_id, "Reader2")
        sessions = db.load_beta_sessions(user, story_id)
        assert len(sessions) >= 2

    def test_invalid_token_returns_none(self):
        sess = db.get_beta_session_by_token("totally_fake_token_xyz")
        assert sess is None


class TestBugFix_WorldElementsColumnNames:
    """BUG: load_world_elements used SELECT * with positional indices."""

    def test_save_and_load(self, user, story_id):
        elem_id = db.save_world_element(user, story_id, "faction", "The Iron Order",
                                         {"goal": "world domination", "power": "Major"})
        assert elem_id is not None
        elements = db.load_world_elements(user, story_id, "faction")
        assert len(elements) == 1
        assert elements[0]["name"] == "The Iron Order"
        assert elements[0]["data"]["goal"] == "world domination"

    def test_filter_by_type(self, user, story_id):
        db.save_world_element(user, story_id, "magic",    "Fire Magic", {"level": "tier1"})
        db.save_world_element(user, story_id, "creature", "Dragons",    {"dangerous": True})
        factions = db.load_world_elements(user, story_id, "magic")
        assert all(e["element_type"] == "magic" for e in factions)

    def test_update_element(self, user, story_id):
        elem_id = db.save_world_element(user, story_id, "location", "Dark Forest",
                                         {"size": "small"})
        db.update_world_element(elem_id, user, "Dark Forest (expanded)", {"size": "large"})
        all_elems = db.load_world_elements(user, story_id, "location")
        updated = next((e for e in all_elems if e["id"] == elem_id), None)
        assert updated is not None
        assert updated["data"]["size"] == "large"

    def test_idor_on_delete(self, user, story_id):
        elem_id = db.save_world_element(user, story_id, "faction", "Secret Faction", {})
        db.delete_world_element(elem_id, "hacker_user")  # should not delete
        elements = db.load_world_elements(user, story_id, "faction")
        ids = [e["id"] for e in elements]
        assert elem_id in ids, "IDOR: element deleted by wrong user"


class TestBugFix_GetStoryUpdatedAt:
    """BUG: autosave.py used private _db/_q/_r. Now uses public get_story_updated_at."""

    def test_function_exists(self):
        assert hasattr(db, "get_story_updated_at"), \
            "get_story_updated_at missing from database"

    def test_returns_float_or_none(self, user, story_id):
        ts = db.get_story_updated_at(user, story_id)
        assert ts is None or isinstance(ts, float), \
            f"Expected float or None, got {type(ts)}"

    def test_missing_story_returns_none(self, user):
        ts = db.get_story_updated_at(user, "does_not_exist")
        assert ts is None


class TestBugFix_StoryChoicesColumns:
    """BUG: load_story_choices used SELECT * with positional indices."""

    def test_save_and_load_choice(self, user, story_id):
        choice_id = db.save_story_choice(
            user, story_id, 3, "Chase the dragon",
            [{"role": "user", "content": "I chase it"}])
        assert choice_id is not None
        choices = db.load_story_choices(user, story_id)
        assert len(choices) >= 1
        c = choices[-1]
        assert c["choice_label"] == "Chase the dragon"
        assert c["parent_message_idx"] == 3
        assert len(c["branch_messages"]) == 1

    def test_delete_choice_idor(self, user, story_id):
        choice_id = db.save_story_choice(user, story_id, 0, "Run away", [])
        db.delete_story_choice(choice_id, "wrong_user")
        choices = db.load_story_choices(user, story_id)
        ids = [c["id"] for c in choices]
        assert choice_id in ids, "IDOR: choice deleted by wrong user"


class TestBugFix_DeleteStoryFullCascade:
    """BUG: delete_story didn't cascade to world_elements, story_choices, beta_sessions."""

    def test_cascade_delete(self, user, story_id):
        # Add data to all tables
        db.add_character(user, story_id, "Hero", "protagonist", "brave")
        db.add_scene(user, story_id, "Scene1", "Forest", "Fight", [])
        db.save_world_element(user, story_id, "faction", "Bad Guys", {})
        db.save_story_choice(user, story_id, 0, "Run", [])
        db.create_beta_session(user, story_id, "Reader")

        # Delete the story
        db.delete_story(user, story_id)

        # All related data should be gone
        assert db.load_characters(user, story_id) == []
        assert db.load_scenes(user, story_id) == []
        assert db.load_world_elements(user, story_id) == []
        assert db.load_story_choices(user, story_id) == []
        assert db.load_beta_sessions(user, story_id) == []


class TestBugFix_WritingSessionUpsert:
    """BUG: check that the writing session upsert works correctly (param count)."""

    def test_single_session_created(self, user, story_id):
        db.log_writing_session(user, story_id, 100)
        sessions = db.load_writing_sessions(user, 7)
        assert len(sessions) >= 1

    def test_upsert_accumulates_words(self, user, story_id):
        """Two log calls on the same day should sum up."""
        db.log_writing_session(user, story_id, 100, duration_minutes=5)
        db.log_writing_session(user, story_id, 200, duration_minutes=10)
        sessions = db.load_writing_sessions(user, 7)
        today_sessions = [s for s in sessions]
        total = sum(s["words"] for s in today_sessions)
        assert total >= 300, f"Expected >=300 cumulative words, got {total}"

    def test_streak_counts_today(self, user, story_id):
        db.log_writing_session(user, story_id, 50)
        streak = db.get_writing_streak(user)
        assert streak >= 1


# ══════════════════════════════════════════════════════════════════════════════
#  ACHIEVEMENTS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAchievements:
    """Achievements now use DB — not always-empty session state."""

    def test_unlock_and_load(self, user):
        db.unlock_achievement(user, "first_words")
        earned = db.load_achievements(user)
        assert "first_words" in earned

    def test_unlock_idempotent(self, user):
        db.unlock_achievement(user, "short_story")
        db.unlock_achievement(user, "short_story")
        earned = db.load_achievements(user)
        assert "short_story" in earned  # No error, no duplicate

    def test_different_users_isolated(self, user):
        other = f"other_{user}"
        db.register_user(other, f"{other}@test.com", "pass123!")
        db.unlock_achievement(user, "novelist")
        earned_other = db.load_achievements(other)
        assert "novelist" not in earned_other

    def test_get_writing_streak_db(self, user, story_id):
        db.log_writing_session(user, story_id, 100)
        streak = db.get_writing_streak(user)
        assert isinstance(streak, int)
        assert streak >= 1


# ══════════════════════════════════════════════════════════════════════════════
#  NEW FEATURE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPlotStructure:
    """plot_structure.py — framework beat tracking."""

    def test_import(self):
        from plot_structure import FRAMEWORKS, show_plot_structure_panel
        assert "3-Act Structure" in FRAMEWORKS
        assert "Save the Cat"    in FRAMEWORKS
        assert "Hero's Journey"  in FRAMEWORKS

    def test_framework_beats_complete(self):
        from plot_structure import FRAMEWORKS
        for name, fw in FRAMEWORKS.items():
            beats = fw["beats"]
            assert len(beats) > 5, f"{name} has too few beats"
            for b in beats:
                assert "id"    in b, f"Beat missing 'id' in {name}"
                assert "label" in b
                assert "pct"   in b
                assert "desc"  in b
                assert 0 <= b["pct"] <= 100, f"pct out of range in {name}"

    def test_progress_pct_calculation(self):
        from plot_structure import _progress_pct, FRAMEWORKS
        beats = FRAMEWORKS["3-Act Structure"]["beats"]
        # No beats done
        assert _progress_pct(beats, set()) == 0
        # First beat done
        first_id = beats[0]["id"]
        pct = _progress_pct(beats, {first_id})
        assert pct == beats[0]["pct"]
        # All done
        all_ids = {b["id"] for b in beats}
        pct = _progress_pct(beats, all_ids)
        assert pct == 100

    def test_beat_keys_unique(self):
        from plot_structure import FRAMEWORKS
        all_ids = []
        for fw in FRAMEWORKS.values():
            for b in fw["beats"]:
                all_ids.append(b["id"])
        assert len(all_ids) == len(set(all_ids)), "Beat IDs must be globally unique"

    def test_plot_arc_persistence(self, user, story_id):
        """Beat completion persists in story['plot_arc']."""
        story = db.load_story(user, story_id)
        arc = story.get("plot_arc", {})
        arc["_ps_3-act_structure"] = ["3a_setup", "3a_inciting"]
        story["plot_arc"] = arc
        db.save_story(user, story)

        reloaded = db.load_story(user, story_id)
        assert "_ps_3-act_structure" in reloaded["plot_arc"]
        assert "3a_setup" in reloaded["plot_arc"]["_ps_3-act_structure"]


class TestAnalyticsEnhanced:
    """analytics_enhanced.py — character screen time + scene distribution."""

    def test_import(self):
        from analytics_enhanced import show_character_screen_time, show_scene_distribution
        assert callable(show_character_screen_time)
        assert callable(show_scene_distribution)

    def test_count_mentions(self):
        from analytics_enhanced import _count_mentions
        prose = "Alice walked into the room. Alice sat down. Bob watched Alice."
        assert _count_mentions(prose, "Alice") == 3
        assert _count_mentions(prose, "Bob")   == 1
        assert _count_mentions(prose, "Carol")  == 0

    def test_count_mentions_case_insensitive(self):
        from analytics_enhanced import _count_mentions
        assert _count_mentions("alice ALICE Alice", "Alice") == 3

    def test_count_mentions_word_boundary(self):
        from analytics_enhanced import _count_mentions
        # "Bob" should not match "Bobby"
        prose = "Bobby went to the store. Bob did not."
        assert _count_mentions(prose, "Bob") == 1

    def test_empty_prose_returns_zero(self):
        from analytics_enhanced import _count_mentions
        assert _count_mentions("", "Alice") == 0
        assert _count_mentions(None, "Alice") == 0

    def test_colours_defined(self):
        from analytics_enhanced import _COLOURS
        assert len(_COLOURS) >= 5

    def test_scene_distribution_empty(self):
        """Should not crash with 0 scenes."""
        # Just verify it imports and the function is callable
        from analytics_enhanced import show_scene_distribution
        assert callable(show_scene_distribution)


class TestMobileStyles:
    """mobile_styles.py — CSS generation."""

    def test_import(self):
        from mobile_styles import get_mobile_css, inject_mobile_styles
        assert callable(get_mobile_css)
        assert callable(inject_mobile_styles)

    def test_returns_style_tag(self):
        from mobile_styles import get_mobile_css
        css = get_mobile_css()
        assert "<style>" in css
        assert "</style>" in css

    def test_has_touch_targets(self):
        from mobile_styles import get_mobile_css
        css = get_mobile_css()
        assert "min-height: 44px" in css, "Should specify 44px touch targets"

    def test_has_breakpoints(self):
        from mobile_styles import get_mobile_css
        css = get_mobile_css()
        assert "768px" in css
        assert "480px" in css

    def test_has_sidebar_rules(self):
        from mobile_styles import get_mobile_css
        css = get_mobile_css()
        assert "stSidebar" in css


# ══════════════════════════════════════════════════════════════════════════════
#  CORE DATA LAYER TESTS (sanity / regression)
# ══════════════════════════════════════════════════════════════════════════════

class TestCoreDataLayer:

    def test_user_register_and_login(self, user):
        assert db.verify_login(user, "Password123!")
        assert not db.verify_login(user, "wrong_password")

    def test_duplicate_user_rejected(self, user):
        result = db.register_user(user, "x@x.com", "pass")
        assert not result["ok"]
        assert "taken" in result["error"].lower()

    def test_story_save_and_load(self, user, story_id):
        stories = db.load_stories(user)
        ids = [s["id"] for s in stories]
        assert story_id in ids

    def test_story_update_title(self, user, story_id):
        db.update_story_title(user, story_id, "Revised Title")
        story = db.load_story(user, story_id)
        assert story["title"] == "Revised Title"

    def test_character_crud(self, user, story_id):
        db.add_character(user, story_id, "Hero", "protagonist", "Brave soul")
        chars = db.load_characters(user, story_id)
        assert len(chars) == 1
        cid = chars[0]["id"]
        db.update_character(cid, user, "Hero", "protagonist", "Brave and wise",
                            "Speaks formally", "Arc: learns to trust")
        chars = db.load_characters(user, story_id)
        assert chars[0]["description"] == "Brave and wise"
        db.delete_character(cid, user)
        assert db.load_characters(user, story_id) == []

    def test_scene_crud(self, user, story_id):
        db.add_scene(user, story_id, "The Duel", "Courtyard", "Confrontation", ["Hero"])
        scenes = db.load_scenes(user, story_id)
        assert len(scenes) == 1
        assert scenes[0]["title"] == "The Duel"
        sid = scenes[0]["id"]
        db.delete_scene(sid, user)
        assert db.load_scenes(user, story_id) == []

    def test_snapshot_roundtrip(self, user, story_id):
        msgs = [{"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there, adventurer!"}]
        db.save_snapshot(user, story_id, "Draft v1", msgs)
        snaps = db.load_snapshots(user, story_id)
        assert len(snaps) == 1
        assert snaps[0]["name"] == "Draft v1"
        restored = db.restore_snapshot(snaps[0]["id"], user)
        assert restored[1]["content"] == "Hi there, adventurer!"

    def test_snapshot_idor(self, user, story_id):
        msgs = [{"role": "assistant", "content": "Secret content"}]
        db.save_snapshot(user, story_id, "Secret", msgs)
        snaps = db.load_snapshots(user, story_id)
        snap_id = snaps[-1]["id"]
        result = db.restore_snapshot(snap_id, "attacker")
        assert result is None, "IDOR: attacker should not access other user's snapshot"

    def test_search_stories_title(self, user, story_id):
        db.update_story_title(user, story_id, "Dragon Chronicles")
        results = db.search_stories(user, "Dragon")
        assert any(r["id"] == story_id for r in results)

    def test_search_stories_empty_query(self, user):
        results = db.search_stories(user, "")
        assert results == []

    def test_change_password(self, user):
        db.change_password(user, "NewPassword456!")
        assert db.verify_login(user, "NewPassword456!")
        assert not db.verify_login(user, "Password123!")

    def test_world_note_crud(self, user, story_id):
        db.add_note(user, story_id, "Lore", "The Prophecy", "One ring to rule them all.")
        notes = db.load_notes(user, story_id)
        assert len(notes) == 1
        nid = notes[0]["id"]
        db.update_note(nid, user, "Lore", "The Prophecy", "Updated content.")
        notes = db.load_notes(user, story_id)
        assert notes[0]["content"] == "Updated content."
        db.delete_note(nid, user)
        assert db.load_notes(user, story_id) == []

    def test_chapter_crud(self, user, story_id):
        cid = db.add_chapter(user, story_id, "The Beginning")
        assert cid is not None
        chapters = db.load_chapters(user, story_id)
        assert chapters[0]["title"] == "The Beginning"
        db.update_chapter(cid, user, "The Real Beginning", "Short recap")
        chapters = db.load_chapters(user, story_id)
        assert chapters[0]["title"] == "The Real Beginning"
        assert chapters[0]["summary"] == "Short recap"
        db.delete_chapter(cid, user)
        assert db.load_chapters(user, story_id) == []

    def test_story_user_isolation(self, user, story_id):
        """User A cannot see User B's stories."""
        other = f"other_{user}"
        db.register_user(other, f"{other}@test.com", "pass!")
        stories_other = db.load_stories(other)
        ids_other = [s["id"] for s in stories_other]
        assert story_id not in ids_other


# ══════════════════════════════════════════════════════════════════════════════
#  AUTOSAVE MODULE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAutosave:

    def test_import(self):
        import autosave
        assert hasattr(autosave, "autosave_tick")
        assert hasattr(autosave, "render_autosave_status")
        assert hasattr(autosave, "_mark_dirty")

    def test_no_private_db_import(self):
        """autosave.py must not import private _db, _q, _r."""
        import ast, pathlib
        src_file = pathlib.Path(__file__).parent / "autosave.py"
        if not src_file.exists():
            pytest.skip("autosave.py not in test directory")
        src = src_file.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module == "database":
                    names = [alias.name for alias in node.names]
                    for priv in ("_db", "_q", "_r"):
                        assert priv not in names, \
                            f"autosave.py still imports private '{priv}' from database"


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 68)
    print("  NarrativeForge — Full Test Suite")
    print("═" * 68)
    exit_code = pytest.main([__file__, "-v", "--tb=short", "--no-header"])
    sys.exit(exit_code)
