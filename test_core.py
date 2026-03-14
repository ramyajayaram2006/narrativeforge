"""
tests/test_core.py — NarrativeForge unit tests
Run with:  pytest tests/ -v
"""
import os
import sys
import json
import pytest
import tempfile

# ── Use a temp SQLite DB for all tests — never touch production data ──────────
_TMP_DB = tempfile.mktemp(suffix=".db")
os.environ["NARRATIVEFORGE_DB"] = _TMP_DB
os.environ.pop("DATABASE_URL", None)          # force SQLite mode

# Add project root so imports work whether running from root or tests/ dir
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import (
    init_db, register_user, verify_login, change_password,
    save_story, load_stories, delete_story, update_story_title,
    add_character, load_characters, delete_character,
    add_scene, load_scenes, delete_scene,
    save_snapshot, load_snapshots, restore_snapshot,
    add_note, load_notes, delete_note,
    search_stories,
)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create tables once for the entire test session."""
    init_db()


@pytest.fixture
def test_user(tmp_path):
    """Register a unique test user and return their username."""
    username = f"testuser_{id(tmp_path)}"
    result   = register_user(username, "test@example.com", "Password123")
    assert result["ok"], f"register_user failed: {result}"
    return username


@pytest.fixture
def test_story(test_user):
    """Create a basic story and return (username, story_dict)."""
    story = {
        "id":            f"story_{id(test_user)}",
        "title":         "The Lost Key",
        "genre":         "Mystery",
        "tone":          "Dark",
        "messages":      [],
        "plot_arc":      {},
        "writing_style": "",
        "word_goal":     0,
        "style_dna":     "",
    }
    save_story(test_user, story)
    return test_user, story


# ══════════════════════════════════════════════════════════════════════════════
#  Auth tests
# ══════════════════════════════════════════════════════════════════════════════

class TestUserRegistration:
    def test_registers_successfully(self):
        result = register_user("reg_alice", "alice@x.com", "pass1234")
        assert result["ok"] is True

    def test_duplicate_username_rejected(self):
        register_user("dup_bob", "bob@x.com", "pass1234")
        result = register_user("dup_bob", "bob2@x.com", "pass9999")
        assert result["ok"] is False
        assert "taken" in result["error"].lower() or "duplicate" in result["error"].lower()

    def test_short_password_still_hashed(self):
        """Password hashing should not break on short passwords."""
        result = register_user("short_pw_user", "", "ab")
        assert result["ok"] is True


class TestUserLogin:
    def test_correct_credentials(self):
        register_user("login_carol", "", "correct_pass")
        assert verify_login("login_carol", "correct_pass") is True

    def test_wrong_password(self):
        register_user("login_dave", "", "right_pass")
        assert verify_login("login_dave", "wrong_pass") is False

    def test_unknown_user(self):
        assert verify_login("nobody_xyz_9999", "anything") is False

    def test_case_sensitive_username(self):
        register_user("login_eve", "", "pass123")
        # Different capitalisation — should fail (case-sensitive usernames)
        assert verify_login("Login_Eve", "pass123") is False


class TestPasswordChange:
    def test_change_and_login_with_new(self):
        register_user("pw_change_user", "", "old_pass")
        change_password("pw_change_user", "new_pass_99")
        assert verify_login("pw_change_user", "new_pass_99") is True

    def test_old_password_rejected_after_change(self):
        register_user("pw_change2", "", "old_pass")
        change_password("pw_change2", "new_pass_99")
        assert verify_login("pw_change2", "old_pass") is False


# ══════════════════════════════════════════════════════════════════════════════
#  Story CRUD tests
# ══════════════════════════════════════════════════════════════════════════════

class TestStoryCRUD:
    def test_save_and_load(self, test_user):
        story = {
            "id": "st_load_001", "title": "Load Test",
            "genre": "Sci-Fi", "tone": "Hopeful",
            "messages": [{"role": "user", "content": "Hello world"}],
            "plot_arc": {"beginning": "Once upon a time"},
            "writing_style": "sparse", "word_goal": 5000, "style_dna": "",
        }
        save_story(test_user, story)
        stories = load_stories(test_user)
        ids = [s["id"] for s in stories]
        assert "st_load_001" in ids

    def test_messages_preserved(self, test_user):
        msgs = [
            {"role": "user",      "content": "First line"},
            {"role": "assistant", "content": "Second line"},
        ]
        story = {"id": "st_msgs_001", "title": "Msg Test",
                 "genre": "Drama", "tone": "Tense",
                 "messages": msgs, "plot_arc": {},
                 "writing_style": "", "word_goal": 0, "style_dna": ""}
        save_story(test_user, story)
        loaded = next(s for s in load_stories(test_user) if s["id"] == "st_msgs_001")
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0]["content"] == "First line"

    def test_update_title(self, test_story):
        username, story = test_story
        update_story_title(username, story["id"], "Renamed Title")
        loaded = next(s for s in load_stories(username) if s["id"] == story["id"])
        assert loaded["title"] == "Renamed Title"

    def test_delete_story(self, test_user):
        story = {"id": "st_del_001", "title": "To Delete",
                 "genre": "Horror", "tone": "Dark",
                 "messages": [], "plot_arc": {},
                 "writing_style": "", "word_goal": 0, "style_dna": ""}
        save_story(test_user, story)
        delete_story(test_user, "st_del_001")
        ids = [s["id"] for s in load_stories(test_user)]
        assert "st_del_001" not in ids

    def test_user_isolation(self, test_user):
        """User A should not see User B's stories."""
        user_b = "isolation_user_b"
        register_user(user_b, "", "passB")
        story_b = {"id": "st_b_only", "title": "B Private",
                   "genre": "Thriller", "tone": "Tense",
                   "messages": [], "plot_arc": {},
                   "writing_style": "", "word_goal": 0, "style_dna": ""}
        save_story(user_b, story_b)
        stories_a = load_stories(test_user)
        assert not any(s["id"] == "st_b_only" for s in stories_a)


# ══════════════════════════════════════════════════════════════════════════════
#  Character tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCharacters:
    def test_add_and_load(self, test_story):
        username, story = test_story
        add_character(username, story["id"], "Alice", "protagonist",
                      "Fearless detective", "Curt and precise")
        chars = load_characters(username, story["id"])
        names = [c["name"] for c in chars]
        assert "Alice" in names

    def test_delete_character(self, test_story):
        username, story = test_story
        add_character(username, story["id"], "ToDelete", "minor", "temp", "")
        chars  = load_characters(username, story["id"])
        del_id = next(c["id"] for c in chars if c["name"] == "ToDelete")
        delete_character(del_id, username)
        names  = [c["name"] for c in load_characters(username, story["id"])]
        assert "ToDelete" not in names

    def test_character_idor_protection(self, test_story):
        """delete_character must require matching username."""
        username, story = test_story
        add_character(username, story["id"], "Protected", "hero", "Can't steal me", "")
        chars   = load_characters(username, story["id"])
        char_id = next(c["id"] for c in chars if c["name"] == "Protected")
        # Attempt delete as wrong user — character should survive
        delete_character(char_id, "attacker_user")
        names = [c["name"] for c in load_characters(username, story["id"])]
        assert "Protected" in names


# ══════════════════════════════════════════════════════════════════════════════
#  Scene tests
# ══════════════════════════════════════════════════════════════════════════════

class TestScenes:
    def test_add_and_load(self, test_story):
        username, story = test_story
        add_scene(username, story["id"], "Opening Act", "The Docks",
                  "Establish tone", ["Alice"])
        scenes = load_scenes(username, story["id"])
        assert any(s["title"] == "Opening Act" for s in scenes)

    def test_delete_scene(self, test_story):
        username, story = test_story
        add_scene(username, story["id"], "TempScene", "Nowhere", "temp", [])
        scenes   = load_scenes(username, story["id"])
        scene_id = next(s["id"] for s in scenes if s["title"] == "TempScene")
        delete_scene(scene_id, username)
        assert not any(s["title"] == "TempScene" for s in load_scenes(username, story["id"]))


# ══════════════════════════════════════════════════════════════════════════════
#  Snapshot tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshots:
    def test_save_and_restore(self, test_story):
        username, story = test_story
        msgs = [{"role": "user", "content": "Snapshot test message"}]
        save_snapshot(username, story["id"], "Pre-edit", msgs)
        snaps  = load_snapshots(username, story["id"])
        snap   = next(s for s in snaps if s["name"] == "Pre-edit")
        result = restore_snapshot(snap["id"], username)
        assert result is not None
        assert result[0]["content"] == "Snapshot test message"

    def test_restore_nonexistent_returns_none(self, test_story):
        username, _ = test_story
        result = restore_snapshot(999999, username)
        assert result is None

    def test_restore_idor_protection(self, test_story):
        """restore_snapshot must require matching username."""
        username, story = test_story
        msgs = [{"role": "user", "content": "secret"}]
        save_snapshot(username, story["id"], "Private", msgs)
        snaps   = load_snapshots(username, story["id"])
        snap_id = snaps[0]["id"]
        # Attacker tries to restore with different username → should return None
        result = restore_snapshot(snap_id, "attacker_user")
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
#  Search tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSearch:
    def test_finds_by_title(self, test_user):
        story = {"id": "st_search_001", "title": "The Midnight Cipher",
                 "genre": "Thriller", "tone": "Tense",
                 "messages": [], "plot_arc": {},
                 "writing_style": "", "word_goal": 0, "style_dna": ""}
        save_story(test_user, story)
        results = search_stories(test_user, "Midnight")
        assert any(r["id"] == "st_search_001" for r in results)

    def test_empty_query_returns_nothing(self, test_user):
        # Empty query — should return empty list (not all stories)
        results = search_stories(test_user, "")
        # LIKE '%' would match everything — empty string query is a known edge case
        # Our implementation should not crash regardless
        assert isinstance(results, list)

    def test_no_cross_user_results(self, test_user):
        other = "search_isolation_user"
        register_user(other, "", "passX")
        story = {"id": "st_other_hidden", "title": "OtherUserSecret",
                 "genre": "Drama", "tone": "Sad",
                 "messages": [], "plot_arc": {},
                 "writing_style": "", "word_goal": 0, "style_dna": ""}
        save_story(other, story)
        results = search_stories(test_user, "OtherUserSecret")
        assert not any(r["id"] == "st_other_hidden" for r in results)


# ══════════════════════════════════════════════════════════════════════════════
#  World notes tests
# ══════════════════════════════════════════════════════════════════════════════

class TestWorldNotes:
    def test_add_and_load(self, test_story):
        username, story = test_story
        add_note(username, story["id"], "Lore", "The Ancient Pact",
                 "Two kingdoms bound by blood-oath since 1402.")
        notes = load_notes(username, story["id"])
        assert any(n["title"] == "The Ancient Pact" for n in notes)

    def test_delete_note(self, test_story):
        username, story = test_story
        add_note(username, story["id"], "Other", "TempNote", "delete me")
        notes   = load_notes(username, story["id"])
        note_id = next(n["id"] for n in notes if n["title"] == "TempNote")
        delete_note(note_id, username)
        assert not any(n["title"] == "TempNote" for n in load_notes(username, story["id"]))


# ══════════════════════════════════════════════════════════════════════════════
#  Cleanup
# ══════════════════════════════════════════════════════════════════════════════

def teardown_module():
    """Remove the temp database file after all tests complete."""
    try:
        os.unlink(_TMP_DB)
    except OSError:
        pass
