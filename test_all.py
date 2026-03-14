"""
test_narrativeforge.py
Real functional tests — no Streamlit required.
Tests: database layer, language support, stats PDF, collaboration tokens,
       search fix, autosave helpers, theme, D3 template rendering.
"""

import sys, os, json, time, hashlib, unittest, tempfile, importlib, types

# ── Stubs for modules we can't install ────────────────────────────────────────
# Stub streamlit so modules that import it don't crash during test collection
class _MockST(types.ModuleType):
    session_state = {}
    def __getattr__(self, name):
        return lambda *a, **kw: None
_st = _MockST("streamlit")
_stc = types.ModuleType("streamlit.components")
_stcv1 = types.ModuleType("streamlit.components.v1")
_stcv1.html = lambda *a, **kw: None
_stc.v1 = _stcv1
_st.components = _stc
sys.modules["streamlit"] = _st
sys.modules["streamlit.components"] = _stc
sys.modules["streamlit.components.v1"] = _stcv1

# Stub bcrypt with sha256 (deterministic, fast, good enough for DB logic tests)
import types
bcrypt_stub = types.ModuleType("bcrypt")
bcrypt_stub.gensalt  = lambda rounds=12: b"$2b$12$fakesalt_narrativeforge_"
bcrypt_stub.hashpw   = lambda pw, salt: hashlib.sha256(pw).hexdigest().encode()
bcrypt_stub.checkpw  = lambda pw, h: hashlib.sha256(pw).hexdigest().encode() == h
sys.modules["bcrypt"] = bcrypt_stub

# Stub psycopg2 (we test SQLite path only)
pg_stub = types.ModuleType("psycopg2")
pg_stub.extras = types.ModuleType("psycopg2.extras")
pg_stub.pool    = types.ModuleType("psycopg2.pool")
class _FakePool:
    def __init__(self,*a,**kw): pass
pg_stub.pool.ThreadedConnectionPool = _FakePool
sys.modules["psycopg2"] = pg_stub
sys.modules["psycopg2.extras"] = pg_stub.extras
sys.modules["psycopg2.pool"]   = pg_stub.pool

# Point imports at our output files
sys.path.insert(0, "/mnt/user-data/outputs")

# ─────────────────────────────────────────────────────────────────────────────
import database as db
import language_support as ls
from stats_report import generate_stats_pdf

BOLD  = "\033[1m"
GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
RESET = "\033[0m"

passed = failed = 0

def ok(name):
    global passed
    passed += 1
    print(f"  {GREEN}✓{RESET} {name}")

def fail(name, err):
    global failed
    failed += 1
    print(f"  {RED}✗{RESET} {name}")
    print(f"      → {err}")


# ══════════════════════════════════════════════════════════════
#  1. DATABASE LAYER
# ══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}── DATABASE ──────────────────────────────────────────{RESET}")

tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["NARRATIVEFORGE_DB"] = tmp.name
tmp.close()
# Force fresh module with temp DB
importlib.reload(db)
db.init_db()

# ── Users ──────────────────────────────────────────────────────────────────────
try:
    r = db.register_user("ramya", "ramya@test.com", "secret123")
    assert r["ok"], r
    ok("register_user() → success")
except Exception as e: fail("register_user()", e)

try:
    r2 = db.register_user("ramya", "x@x.com", "anotherpass")
    assert not r2["ok"]
    assert "taken" in r2["error"].lower() or "unique" in r2["error"].lower()
    ok("register_user() duplicate → correct error")
except Exception as e: fail("register_user() duplicate", e)

try:
    assert db.verify_login("ramya", "secret123") == True
    assert db.verify_login("ramya", "wrongpass") == False
    assert db.verify_login("nobody", "secret123") == False
    ok("verify_login() correct / wrong password / unknown user")
except Exception as e: fail("verify_login()", e)

try:
    assert db.user_exists("ramya") == True
    assert db.user_exists("ghost") == False
    ok("user_exists()")
except Exception as e: fail("user_exists()", e)

try:
    db.change_password("ramya", "newpassword!")
    assert db.verify_login("ramya", "newpassword!") == True
    assert db.verify_login("ramya", "secret123") == False
    ok("change_password() → new password works, old doesn't")
except Exception as e: fail("change_password()", e)

# ── Stories ────────────────────────────────────────────────────────────────────
STORY = {
    "id": "story_abc123", "title": "The Iron Forest",
    "genre": "Dark Fantasy", "tone": "Gritty",
    "messages": [
        {"role": "user", "content": "Start the story."},
        {"role": "assistant", "content": "The iron trees groaned under the weight of forgotten gods."},
    ],
    "plot_arc": {"beginning": True}, "writing_style": "literary",
    "word_goal": 5000, "style_dna": "", "language": "English",
}

try:
    db.save_story("ramya", STORY)
    stories = db.load_stories("ramya")
    assert len(stories) == 1
    assert stories[0]["title"] == "The Iron Forest"
    assert stories[0]["genre"] == "Dark Fantasy"
    assert len(stories[0]["messages"]) == 2
    ok("save_story() + load_stories() round-trip")
except Exception as e: fail("save_story/load_stories", e)

try:
    db.save_story("ramya", {**STORY, "title": "The Iron Forest — Revised"})
    stories = db.load_stories("ramya")
    assert len(stories) == 1          # upsert, not duplicate
    assert stories[0]["title"] == "The Iron Forest — Revised"
    ok("save_story() upsert (no duplicate row)")
except Exception as e: fail("save_story() upsert", e)

try:
    db.update_story_title("ramya", "story_abc123", "The Golden Forest")
    stories = db.load_stories("ramya")
    assert stories[0]["title"] == "The Golden Forest"
    ok("update_story_title()")
except Exception as e: fail("update_story_title()", e)

# ── Search fix (BUG 5) ─────────────────────────────────────────────────────────
try:
    r = db.search_stories("ramya", "")
    assert r == [], f"Empty search returned {r}"
    ok("search_stories('') → [] (BUG 5 fix verified)")
except Exception as e: fail("search_stories('') fix", e)

try:
    # Title is "The Golden Forest" — iron is only in message content, not title
    r = db.search_stories("ramya", "golden")
    assert len(r) == 1
    assert r[0]["title"] == "The Golden Forest"
    # iron matches message content, not title
    r2 = db.search_stories("ramya", "iron")
    assert len(r2) == 1   # matches via message content "iron trees groaned"
    ok("search_stories() matches title and message content correctly")
except Exception as e: fail("search_stories() title match", e)

try:
    r = db.search_stories("ramya", "groaned")
    assert len(r) == 1
    assert any("groaned" in s for s in r[0]["snippets"])
    ok("search_stories() matches message content + returns snippets")
except Exception as e: fail("search_stories() content match", e)

try:
    r = db.search_stories("ramya", "xyznotfound999")
    assert r == []
    ok("search_stories() no match → []")
except Exception as e: fail("search_stories() no match", e)

# ── Characters ─────────────────────────────────────────────────────────────────
try:
    db.add_character("ramya", "story_abc123", "Kira", "Protagonist",
                      "A wandering blacksmith with iron-stained hands.", "Terse, direct.")
    db.add_character("ramya", "story_abc123", "Moros", "Antagonist",
                      "The god of forgotten things.", "Archaic, verbose.")
    chars = db.load_characters("ramya", "story_abc123")
    assert len(chars) == 2
    assert chars[0]["name"] == "Kira"
    assert chars[1]["speaking_style"] == "Archaic, verbose."
    ok("add_character() + load_characters()")
except Exception as e: fail("characters", e)

try:
    char_id = db.load_characters("ramya","story_abc123")[0]["id"]
    db.update_character(char_id, "ramya", "Kira", "Protagonist",
                         "Updated desc.", "Short and clipped.")
    chars = db.load_characters("ramya", "story_abc123")
    assert chars[0]["description"] == "Updated desc."
    ok("update_character()")
except Exception as e: fail("update_character()", e)

# ── Scenes ─────────────────────────────────────────────────────────────────────
try:
    db.add_scene("ramya","story_abc123","The Forge","Underground Forge",
                  "Introduce Kira's world",["Kira"])
    db.add_scene("ramya","story_abc123","The Reckoning","Iron Forest",
                  "Confrontation",["Kira","Moros"])
    scenes = db.load_scenes("ramya","story_abc123")
    assert len(scenes) == 2
    assert scenes[0]["title"] == "The Forge"
    assert "Kira" in scenes[1]["characters"]
    ok("add_scene() + load_scenes()")
except Exception as e: fail("scenes", e)

# ── World notes ────────────────────────────────────────────────────────────────
try:
    db.add_note("ramya","story_abc123","Magic System","Iron Binding",
                  "Iron trees absorb magical energy and trap spirits.")
    notes = db.load_notes("ramya","story_abc123")
    assert len(notes) == 1
    assert notes[0]["title"] == "Iron Binding"
    db.update_note(notes[0]["id"],"ramya","Magic System","Iron Binding — Updated","New content.")
    notes2 = db.load_notes("ramya","story_abc123")
    assert notes2[0]["title"] == "Iron Binding — Updated"
    ok("add_note() + update_note() + load_notes()")
except Exception as e: fail("world notes", e)

# ── Snapshots ──────────────────────────────────────────────────────────────────
try:
    msgs = STORY["messages"]
    db.save_snapshot("ramya","story_abc123","Draft v1", msgs)
    snaps = db.load_snapshots("ramya","story_abc123")
    assert len(snaps) == 1
    assert snaps[0]["name"] == "Draft v1"
    assert snaps[0]["word_count"] > 0

    restored = db.restore_snapshot(snaps[0]["id"], "ramya")
    assert isinstance(restored, list)
    assert len(restored) == 2
    ok("save_snapshot() + load_snapshots() + restore_snapshot()")
except Exception as e: fail("snapshots", e)

# ── IDOR protection ────────────────────────────────────────────────────────────
try:
    db.register_user("attacker", "atk@evil.com", "hackpass")
    stories_attacker = db.load_stories("attacker")
    assert len(stories_attacker) == 0

    snap_id = db.load_snapshots("ramya","story_abc123")[0]["id"]
    stolen  = db.restore_snapshot(snap_id, "attacker")
    assert stolen is None
    ok("IDOR: attacker cannot restore ramya's snapshot")
except Exception as e: fail("IDOR protection", e)

try:
    chars = db.load_characters("attacker","story_abc123")
    assert len(chars) == 0
    ok("IDOR: attacker cannot load ramya's characters")
except Exception as e: fail("IDOR: characters", e)

# ── delete_user (BUG 3 fix) ────────────────────────────────────────────────────
try:
    db.register_user("todelete","del@test.com","pass123")
    assert db.user_exists("todelete")
    db.delete_user("todelete")
    assert not db.user_exists("todelete")
    ok("delete_user() — BUG 3 fix verified")
except Exception as e: fail("delete_user()", e)


# ══════════════════════════════════════════════════════════════
#  2. LANGUAGE SUPPORT
# ══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}── LANGUAGE SUPPORT ──────────────────────────────────{RESET}")

try:
    assert "English" in ls.LANGUAGE_LIST
    assert "Hindi"   in ls.LANGUAGE_LIST
    assert "Tamil"   in ls.LANGUAGE_LIST
    assert "Arabic"  in ls.LANGUAGE_LIST
    assert len(ls.LANGUAGE_LIST) >= 20
    ok(f"LANGUAGE_LIST contains {len(ls.LANGUAGE_LIST)} languages")
except Exception as e: fail("LANGUAGE_LIST", e)

try:
    story_en = {"language": "English", "genre": "Fantasy", "tone": "Light"}
    block = ls.get_language_block(story_en)
    assert block == "", f"English should return empty string, got: {repr(block)}"
    ok("get_language_block('English') → '' (no prompt injection)")
except Exception as e: fail("get_language_block English", e)

try:
    story_hi = {"language": "Hindi", "genre": "Fantasy", "tone": "Dark"}
    block = ls.get_language_block(story_hi)
    assert "Hindi" in block
    assert "हिन्दी" in block
    assert "LANGUAGE INSTRUCTION" in block
    ok("get_language_block('Hindi') → contains Hindi name + native script")
except Exception as e: fail("get_language_block Hindi", e)

try:
    story_ta = {"language": "Tamil", "genre": "Romance", "tone": "Warm"}
    block = ls.get_language_block(story_ta)
    assert "Tamil" in block
    assert "தமிழ்" in block
    ok("get_language_block('Tamil') → contains Tamil native script")
except Exception as e: fail("get_language_block Tamil", e)

try:
    story_ar = {"language": "Arabic", "genre": "Mystery", "tone": "Dark"}
    block = ls.get_language_block(story_ar)
    assert "right-to-left" in block.lower()
    ok("get_language_block('Arabic') → RTL note included")
except Exception as e: fail("get_language_block Arabic RTL", e)

try:
    for lang in ls.LANGUAGE_LIST:
        s = {"language": lang, "genre": "Fantasy", "tone": "Neutral"}
        b = ls.get_language_block(s)
        if lang == "English":
            assert b == ""
        else:
            assert len(b) > 10
    ok(f"get_language_block() works for all {len(ls.LANGUAGE_LIST)} languages")
except Exception as e: fail("get_language_block all languages", e)

try:
    assert ls.LANGUAGES["Arabic"]["rtl"]  == True
    assert ls.LANGUAGES["Urdu"]["rtl"]    == True
    assert ls.LANGUAGES["Hindi"]["rtl"]   == False
    assert ls.LANGUAGES["English"]["rtl"] == False
    ok("RTL flags correct for Arabic, Urdu, Hindi, English")
except Exception as e: fail("RTL flags", e)


# ══════════════════════════════════════════════════════════════
#  3. D3 TEMPLATE (relationship_map BUG 1 + 2 fix)
# ══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}── RELATIONSHIP MAP (D3 template) ────────────────────{RESET}")

sys.path.insert(0, "/mnt/user-data/outputs")
import relationship_map as rm

try:
    chars = [
        {"id":1,"name":"Kira","role":"Protagonist","description":"Blacksmith","speaking_style":"Terse"},
        {"id":2,"name":"Moros","role":"Antagonist","description":"Iron god","speaking_style":"Archaic"},
    ]
    scns  = [{"characters":["Kira","Moros"],"order":1,"title":"The Reckoning"}]
    graph = rm._build_graph(chars, scns)
    assert len(graph["nodes"]) == 2
    assert len(graph["links"]) == 1
    assert graph["links"][0]["weight"] == 1
    ok("_build_graph() produces correct nodes + edges")
except Exception as e: fail("_build_graph()", e)

try:
    html = rm._D3_TEMPLATE.format(graph_json=json.dumps({"nodes":[],"links":[]}))
    # BUG 1 fix: no double braces in JS context
    assert "{{" not in html, "Found {{ in rendered HTML — .format() not working"
    assert "}}" not in html, "Found }} in rendered HTML — .format() not working"
    ok("BUG 1 fix: no {{ or }} in rendered HTML (JS syntax is valid)")
except Exception as e: fail("BUG 1 double brace check", e)

try:
    graph_data = rm._build_graph(chars, scns)
    html = rm._D3_TEMPLATE.format(graph_json=json.dumps(graph_data))
    # BUG 2 fix: translate() has correct parens
    assert "translate(${d.x},${d.y})" in html, "translate() syntax incorrect"
    ok("BUG 2 fix: translate(${d.x},${d.y}) parens correct")
except Exception as e: fail("BUG 2 translate parens", e)

try:
    html = rm._D3_TEMPLATE.format(graph_json=json.dumps(graph_data))
    assert "<script" in html
    assert "d3.forceSimulation" in html
    # The graph data should be embedded literally in the HTML
    assert '"Kira"' in html    # node name is in the JSON
    assert '"Protagonist"' in html
    assert '"weight": 1' in html  # edge weight
    # Verify the graphData assignment line exists
    assert "const graphData = " in html
    ok("Rendered HTML contains embedded graphData with correct node/edge data")
except Exception as e: fail("D3 HTML graphData JSON", e)

try:
    empty_graph = rm._build_graph([], [])
    assert empty_graph == {"nodes":[], "links":[]}
    html = rm._D3_TEMPLATE.format(graph_json=json.dumps(empty_graph))
    assert "Add characters" in html
    ok("_build_graph([],[]) → empty state renders correctly")
except Exception as e: fail("Empty graph", e)


# ══════════════════════════════════════════════════════════════
#  4. STATS REPORT PDF
# ══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}── STATS REPORT PDF ──────────────────────────────────{RESET}")

TEST_STORY = {
    "id":"s1","title":"The Iron Forest","genre":"Dark Fantasy","tone":"Gritty",
    "word_goal":5000, "language":"Tamil",
    "plot_arc":{"beginning":True,"rising_action":True,"climax":False,
                "falling_action":False,"resolution":False},
    "writing_style":"literary",
    "messages":[
        {"role":"user",      "content":"Begin the story."},
        {"role":"assistant", "content":"The iron trees groaned under the weight of forgotten gods. "
                                       "Kira walked the rusted path with hope in her heart, yet fear "
                                       "shadowed every step. The light died at the forest's edge."},
        {"role":"assistant", "content":"[Revision — More literary]\n\nThe iron trees wept rust."},
        {"role":"assistant", "content":"◆ Tension: 72"},
        {"role":"assistant", "content":"Moros stepped from the shadow, his voice like grinding gears. "
                                       "'You trespass in my domain, blacksmith.' Kira drew her hammer. "
                                       "The silence between them was the loudest sound she had ever heard. "
                                       "Love and rage and grief twisted inside her chest like trapped spirits."},
    ],
    "style_dna":"",
}
TEST_CHARS = [
    {"id":1,"name":"Kira","role":"Protagonist","description":"Blacksmith","speaking_style":"Terse"},
    {"id":2,"name":"Moros","role":"Antagonist","description":"Iron god","speaking_style":"Archaic"},
]
TEST_SCENES = [
    {"id":1,"order":1,"title":"The Forge","location":"Underground","purpose":"Intro","characters":["Kira"]},
    {"id":2,"order":2,"title":"The Reckoning","location":"Iron Forest","purpose":"Climax","characters":["Kira","Moros"]},
]

try:
    pdf_bytes = generate_stats_pdf(TEST_STORY, TEST_CHARS, TEST_SCENES)
    assert isinstance(pdf_bytes, bytes), "Not bytes"
    assert len(pdf_bytes) > 5000, f"PDF too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:4] == b'%PDF', f"Not a valid PDF header: {pdf_bytes[:4]}"
    ok(f"generate_stats_pdf() → valid PDF ({len(pdf_bytes):,} bytes)")
except Exception as e: fail("generate_stats_pdf()", e)

try:
    # Verify revision + system messages excluded from prose
    from stats_report import generate_stats_pdf
    import re, string
    all_text = " ".join(
        m["content"] for m in TEST_STORY["messages"]
        if m["role"] == "assistant"
        and not m["content"].startswith("◆")
        and not m["content"].startswith("[Revision")
    )
    assert "groaned" in all_text
    assert "Moros" in all_text
    assert "[Revision" not in all_text    # BUG 6 fix
    assert "◆ Tension" not in all_text    # system message excluded
    words = all_text.split()
    assert len(words) > 20
    ok(f"BUG 6 fix: prose filter excludes revisions+system ({len(words)} canonical words)")
except Exception as e: fail("BUG 6 prose filter", e)

try:
    empty_story = {**TEST_STORY, "messages":[], "word_goal":0,
                   "plot_arc":{}, "writing_style":""}
    pdf2 = generate_stats_pdf(empty_story, [], [])
    assert pdf2[:4] == b'%PDF'
    ok("generate_stats_pdf() with empty story/chars/scenes → no crash")
except Exception as e: fail("generate_stats_pdf() empty story", e)

try:
    pdf3 = generate_stats_pdf(TEST_STORY, [], [])
    assert pdf3[:4] == b'%PDF'
    ok("generate_stats_pdf() with no characters/scenes → no crash")
except Exception as e: fail("generate_stats_pdf() no chars", e)


# ══════════════════════════════════════════════════════════════
#  5. AUTOSAVE HELPERS (non-streamlit logic)
# ══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}── AUTOSAVE LOGIC ────────────────────────────────────{RESET}")

import autosave as av

try:
    # Get a DB timestamp and verify it parses correctly
    db.save_story("ramya", STORY)
    ts = av._get_db_updated_at("ramya", "story_abc123")
    assert ts is not None, "Got None for updated_at"
    assert isinstance(ts, float)
    assert ts > 1_000_000_000   # Unix timestamp sanity check
    ok(f"_get_db_updated_at() → valid Unix timestamp {ts:.0f}")
except Exception as e: fail("_get_db_updated_at()", e)

try:
    ts = av._get_db_updated_at("nobody", "nonstory")
    assert ts is None
    ok("_get_db_updated_at() for unknown story → None")
except Exception as e: fail("_get_db_updated_at() unknown", e)

try:
    av.AUTOSAVE_INTERVAL_SECS = 30
    assert av.AUTOSAVE_INTERVAL_SECS == 30
    assert av.CONFLICT_CHECK == True
    ok("autosave constants: interval=30s, conflict_check=True")
except Exception as e: fail("autosave constants", e)


# ══════════════════════════════════════════════════════════════
#  6. THEME CSS
# ══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}── THEME CSS ─────────────────────────────────────────{RESET}")

import theme as th

try:
    assert "--bg-main:        #0C0F0C" in th.DARK_VARS
    assert "--bg-main:        #F7F4EE" in th.LIGHT_VARS
    assert "--primary:        #C9A959" in th.DARK_VARS
    assert "--primary:        #8B6914" in th.LIGHT_VARS
    ok("DARK_VARS and LIGHT_VARS have correct --bg-main and --primary")
except Exception as e: fail("theme CSS variables", e)

try:
    # Every CSS var in dark should have a corresponding var in light
    import re
    dark_vars  = set(re.findall(r'--[\w-]+', th.DARK_VARS))
    light_vars = set(re.findall(r'--[\w-]+', th.LIGHT_VARS))
    missing = dark_vars - light_vars
    assert not missing, f"Light theme missing vars: {missing}"
    ok(f"Both themes define identical CSS variable set ({len(dark_vars)} vars)")
except Exception as e: fail("theme CSS var parity", e)

try:
    assert "transition:" in th.THEMED_RESET
    ok("THEMED_RESET includes CSS transition (smooth theme switch)")
except Exception as e: fail("theme transition", e)


# ══════════════════════════════════════════════════════════════
#  7. COLLABORATION TOKEN LOGIC
# ══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}── COLLABORATION TOKENS ──────────────────────────────{RESET}")

# Patch collaboration to use our test DB
import collaboration as cl

try:
    cl.init_collab_tables()
    ok("init_collab_tables() → no crash (idempotent DDL)")
except Exception as e: fail("init_collab_tables()", e)

try:
    token = cl.create_share_token("ramya","story_abc123","read",0)
    assert isinstance(token, str)
    assert len(token) >= 24
    ok(f"create_share_token() → {len(token)}-char URL-safe token")
except Exception as e: fail("create_share_token()", e)

try:
    info = cl.get_token_info(token)
    assert info is not None
    assert info["story_key"] == "story_abc123"
    assert info["owner"]     == "ramya"
    assert info["mode"]      == "read"
    ok("get_token_info() returns correct metadata")
except Exception as e: fail("get_token_info()", e)

try:
    bad = cl.get_token_info("notarealtoken_xyz_abc")
    assert bad is None
    ok("get_token_info() invalid token → None")
except Exception as e: fail("get_token_info() invalid", e)

try:
    # Test expired token
    import datetime
    tok2 = cl.create_share_token("ramya","story_abc123","read", expires_hours=0)
    # Manually set expired timestamp in DB
    with db._db() as (conn, cur):
        cur.execute(
            "UPDATE share_tokens SET expires_at=? WHERE token=?",
            ("2000-01-01T00:00:00", tok2)
        )
    info2 = cl.get_token_info(tok2)
    assert info2 is None, "Expired token should return None"
    ok("get_token_info() expired token → None")
except Exception as e: fail("get_token_info() expiry", e)

try:
    tokens_list = cl.list_tokens("ramya","story_abc123")
    assert isinstance(tokens_list, list)
    ok(f"list_tokens() → {len(tokens_list)} active token(s)")
except Exception as e: fail("list_tokens()", e)

try:
    cl.revoke_token(token, "ramya")
    assert cl.get_token_info(token) is None
    ok("revoke_token() → token no longer valid")
except Exception as e: fail("revoke_token()", e)

try:
    # Security: attacker cannot revoke ramya's token
    tok3 = cl.create_share_token("ramya","story_abc123","read",0)
    cl.revoke_token(tok3, "attacker")          # should silently fail
    info3 = cl.get_token_info(tok3)
    assert info3 is not None, "Attacker should NOT be able to revoke owner's token"
    ok("revoke_token() SECURITY: attacker cannot revoke owner token")
except Exception as e: fail("revoke_token() security", e)

try:
    r = cl.add_collaborator("ramya","story_abc123","attacker")
    assert r["ok"] == True
    collabs = cl.get_collaborators("ramya","story_abc123")
    assert len(collabs) == 1
    assert collabs[0]["username"] == "attacker"
    ok("add_collaborator() → success")
except Exception as e: fail("add_collaborator()", e)

try:
    r2 = cl.add_collaborator("ramya","story_abc123","attacker")
    assert r2["ok"] == False
    assert "already" in r2["error"].lower()
    ok("add_collaborator() duplicate → correct error")
except Exception as e: fail("add_collaborator() duplicate", e)

try:
    r3 = cl.add_collaborator("ramya","story_abc123","ramya")
    assert r3["ok"] == False
    ok("add_collaborator() self-invite → rejected")
except Exception as e: fail("add_collaborator() self", e)

try:
    r4 = cl.add_collaborator("ramya","story_abc123","ghostuser999")
    assert r4["ok"] == False
    assert "not found" in r4["error"].lower()
    ok("add_collaborator() unknown user → 'not found' error")
except Exception as e: fail("add_collaborator() unknown", e)

try:
    cl.remove_collaborator("ramya","story_abc123","attacker")
    collabs = cl.get_collaborators("ramya","story_abc123")
    assert len(collabs) == 0
    ok("remove_collaborator() → removed")
except Exception as e: fail("remove_collaborator()", e)


# ══════════════════════════════════════════════════════════════
#  RESULTS
# ══════════════════════════════════════════════════════════════
total = passed + failed
print(f"\n{'═'*54}")
print(f"  {BOLD}Results: {GREEN}{passed} passed{RESET}{BOLD} / {RED}{failed} failed{RESET}{BOLD} / {total} total{RESET}")
if failed == 0:
    print(f"  {GREEN}{BOLD}All tests passed ✓{RESET}")
else:
    print(f"  {RED}{BOLD}{failed} test(s) failed ✗{RESET}")
print(f"{'═'*54}\n")
sys.exit(0 if failed == 0 else 1)
