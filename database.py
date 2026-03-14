"""
database.py — NarrativeForge data layer
Supports both SQLite (local dev) and PostgreSQL (Railway / production).
Set DATABASE_URL env var to a postgres:// URI to use PostgreSQL.

FIXES applied:
  - Added load_all_characters() and load_all_scenes() for dashboard N+1 elimination
  - Added load_story() (single story by key) used by beta_reading.py
  - Added beta_sessions and story_choices to SQLite migration list
  - Fixed SELECT * positional index issues in load_world_elements / load_story_choices
  - init_collab_tables() now called from init_db()
"""

import os, json, hashlib, contextlib, logging

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_USE_PG      = DATABASE_URL.startswith(("postgres://", "postgresql://"))

logger = logging.getLogger("narrativeforge.db")

if _USE_PG:
    import psycopg2, psycopg2.extras
    from psycopg2 import pool as _pg_pool
    _PG_DSN = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    _PH = "%s"
    _pg_connection_pool = _pg_pool.ThreadedConnectionPool(
        minconn=1, maxconn=10, dsn=_PG_DSN,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
else:
    import sqlite3
    _SQLITE_DB = (os.environ.get("NARRATIVEFORGE_DB")
                  or os.environ.get("NARRATIVEFLOW_DB")
                  or "narrativeforge.db")
    _PH = "?"

try:
    import bcrypt
    _BCRYPT = True
except ImportError:
    raise ImportError("bcrypt is required. Run: pip install bcrypt==4.1.2")


@contextlib.contextmanager
def _db():
    if _USE_PG:
        conn = _pg_connection_pool.getconn()
        conn.autocommit = False
        cur  = conn.cursor()
        try:
            yield conn, cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            _pg_connection_pool.putconn(conn)
    else:
        conn = sqlite3.connect(_SQLITE_DB)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.cursor()
        try:
            yield conn, cur
            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally:
            cur.close(); conn.close()


def _q(sql):
    return sql.replace("?", _PH) if _USE_PG else sql

def _r(row, key, idx):
    return row[key] if _USE_PG else row[idx]


def init_db():
    _pk = "SERIAL PRIMARY KEY" if _USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    _ts = "TIMESTAMPTZ"        if _USE_PG else "TIMESTAMP"

    ddl = [
        f"""CREATE TABLE IF NOT EXISTS users (
            id {_pk}, username TEXT UNIQUE NOT NULL,
            email TEXT, password_hash TEXT NOT NULL)""",

        f"""CREATE TABLE IF NOT EXISTS stories (
            story_key TEXT NOT NULL, username TEXT NOT NULL,
            title TEXT, genre TEXT, tone TEXT, messages TEXT,
            plot_arc TEXT DEFAULT '{{}}', writing_style TEXT DEFAULT '',
            word_goal INTEGER DEFAULT 0, style_dna TEXT DEFAULT '',
            updated_at {_ts} DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (story_key, username))""",

        f"""CREATE TABLE IF NOT EXISTS chapters (
            id {_pk}, story_key TEXT NOT NULL, username TEXT NOT NULL,
            chapter_order INTEGER DEFAULT 0,
            title TEXT NOT NULL DEFAULT 'Chapter 1',
            summary TEXT DEFAULT '',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS characters (
            id {_pk}, story_key TEXT NOT NULL, username TEXT NOT NULL,
            name TEXT NOT NULL, role TEXT, description TEXT,
            speaking_style TEXT DEFAULT '',
            arc_notes TEXT DEFAULT '',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS scenes (
            id {_pk}, story_key TEXT NOT NULL, username TEXT NOT NULL,
            chapter_id INTEGER DEFAULT NULL, scene_order INTEGER DEFAULT 0,
            title TEXT, location TEXT, purpose TEXT,
            characters_in_scene TEXT DEFAULT '[]',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS world_notes (
            id {_pk}, story_key TEXT NOT NULL, username TEXT NOT NULL,
            category TEXT DEFAULT 'Lore', title TEXT NOT NULL,
            content TEXT DEFAULT '',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS snapshots (
            id {_pk}, story_key TEXT NOT NULL, username TEXT NOT NULL,
            name TEXT NOT NULL, messages TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS writing_sessions (
            id {_pk}, username TEXT NOT NULL,
            story_key TEXT NOT NULL,
            session_date TEXT NOT NULL,
            words_written INTEGER DEFAULT 0,
            duration_minutes INTEGER DEFAULT 0,
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS achievements (
            id {_pk}, username TEXT NOT NULL,
            achievement_id TEXT NOT NULL,
            unlocked_at {_ts} DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, achievement_id))""",

        f"""CREATE TABLE IF NOT EXISTS world_elements (
            id {_pk}, story_key TEXT NOT NULL, username TEXT NOT NULL,
            element_type TEXT NOT NULL,
            name TEXT NOT NULL,
            data TEXT DEFAULT '{{}}',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS story_choices (
            id {_pk}, story_key TEXT NOT NULL, username TEXT NOT NULL,
            parent_message_idx INTEGER NOT NULL,
            choice_label TEXT NOT NULL,
            branch_messages TEXT DEFAULT '[]',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP)""",

        f"""CREATE TABLE IF NOT EXISTS beta_sessions (
            id {_pk}, username TEXT NOT NULL,
            story_key TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            reader_name TEXT DEFAULT 'Anonymous',
            feedback TEXT DEFAULT '[]',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP,
            expires_at {_ts})""",

        # Collaboration tables
        f"""CREATE TABLE IF NOT EXISTS share_tokens (
            id {_pk},
            token TEXT UNIQUE NOT NULL,
            story_key TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'read',
            created_at {_ts} DEFAULT CURRENT_TIMESTAMP,
            expires_at {_ts} DEFAULT NULL,
            views INTEGER DEFAULT 0)""",

        f"""CREATE TABLE IF NOT EXISTS collaborators (
            id {_pk},
            story_key TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            collaborator_username TEXT NOT NULL,
            token TEXT NOT NULL,
            invited_at {_ts} DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_key, collaborator_username))""",
    ]
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_stories_user   ON stories(username)",
        "CREATE INDEX IF NOT EXISTS idx_chapters_story ON chapters(story_key,username)",
        "CREATE INDEX IF NOT EXISTS idx_scenes_story   ON scenes(story_key,username)",
        "CREATE INDEX IF NOT EXISTS idx_chars_story    ON characters(story_key,username)",
        "CREATE INDEX IF NOT EXISTS idx_notes_story    ON world_notes(story_key,username)",
        "CREATE INDEX IF NOT EXISTS idx_snaps_story    ON snapshots(story_key,username)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_token   ON share_tokens(token)",
        "CREATE INDEX IF NOT EXISTS idx_collab_user    ON collaborators(collaborator_username)",
    ]
    with _db() as (conn, cur):
        for stmt in ddl + indexes:
            cur.execute(stmt)

    # SQLite-only migrations for existing databases
    if not _USE_PG:
        migs = [
            "ALTER TABLE stories ADD COLUMN plot_arc TEXT DEFAULT '{}'",
            "ALTER TABLE stories ADD COLUMN writing_style TEXT DEFAULT ''",
            "ALTER TABLE stories ADD COLUMN word_goal INTEGER DEFAULT 0",
            "ALTER TABLE stories ADD COLUMN style_dna TEXT DEFAULT ''",
            "ALTER TABLE characters ADD COLUMN speaking_style TEXT DEFAULT ''",
            "ALTER TABLE characters ADD COLUMN arc_notes TEXT DEFAULT ''",
            "ALTER TABLE scenes ADD COLUMN chapter_id INTEGER DEFAULT NULL",
            ("CREATE TABLE IF NOT EXISTS writing_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "username TEXT NOT NULL, story_key TEXT NOT NULL, session_date TEXT NOT NULL, "
             "words_written INTEGER DEFAULT 0, duration_minutes INTEGER DEFAULT 0, "
             "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"),
            ("CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "username TEXT NOT NULL, achievement_id TEXT NOT NULL, "
             "unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(username, achievement_id))"),
            ("CREATE TABLE IF NOT EXISTS world_elements (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "story_key TEXT NOT NULL, username TEXT NOT NULL, element_type TEXT NOT NULL, "
             "name TEXT NOT NULL, data TEXT DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"),
            ("CREATE TABLE IF NOT EXISTS story_choices (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "story_key TEXT NOT NULL, username TEXT NOT NULL, parent_message_idx INTEGER NOT NULL, "
             "choice_label TEXT NOT NULL, branch_messages TEXT DEFAULT '[]', "
             "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"),
            # FIX: beta_sessions was missing from migrations
            ("CREATE TABLE IF NOT EXISTS beta_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "username TEXT NOT NULL, story_key TEXT NOT NULL, token TEXT NOT NULL UNIQUE, "
             "reader_name TEXT DEFAULT 'Anonymous', feedback TEXT DEFAULT '[]', "
             "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP)"),
            # FIX: collaboration tables migration
            ("CREATE TABLE IF NOT EXISTS share_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "token TEXT UNIQUE NOT NULL, story_key TEXT NOT NULL, owner_username TEXT NOT NULL, "
             "mode TEXT NOT NULL DEFAULT 'read', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
             "expires_at TIMESTAMP DEFAULT NULL, views INTEGER DEFAULT 0)"),
            ("CREATE TABLE IF NOT EXISTS collaborators (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "story_key TEXT NOT NULL, owner_username TEXT NOT NULL, "
             "collaborator_username TEXT NOT NULL, token TEXT NOT NULL, "
             "invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
             "UNIQUE(story_key, collaborator_username))"),
        ]
        with _db() as (conn, cur):
            for sql in migs:
                try:
                    cur.execute(sql)
                except Exception:
                    pass


# ── Passwords ─────────────────────────────────────────────────────────────────
def _make_hash(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()

def _check_hash(pw, stored):
    if stored.startswith(("$2b$", "$2a$")):
        return bcrypt.checkpw(pw.encode(), stored.encode())
    return stored == hashlib.sha256(pw.encode()).hexdigest()

def _upgrade_hash(username, pw, stored):
    if not stored.startswith(("$2b$", "$2a$")):
        try:
            with _db() as (conn, cur):
                cur.execute(_q("UPDATE users SET password_hash=? WHERE username=?"),
                            (_make_hash(pw), username.strip()))
        except Exception as e:
            logger.warning("hash upgrade failed: %s", e)


# ── Users ─────────────────────────────────────────────────────────────────────
def register_user(username, email, password):
    try:
        with _db() as (conn, cur):
            cur.execute(_q("INSERT INTO users (username,email,password_hash) VALUES (?,?,?)"),
                        (username.strip(), email.strip(), _make_hash(password)))
        logger.info("User registered: %s", username.strip())
        return {"ok": True}
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg:
            return {"ok": False, "error": "Username already taken"}
        logger.error("register_user error for %s: %s", username, e)
        return {"ok": False, "error": str(e)}

def verify_login(username, password):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT password_hash FROM users WHERE username=?"), (username.strip(),))
        row = cur.fetchone()
    if not row:
        return False
    stored = _r(row, "password_hash", 0)
    if _check_hash(password, stored):
        _upgrade_hash(username, password, stored)
        logger.info("Login success: %s", username.strip())
        return True
    logger.warning("Login failure: %s", username.strip())
    return False

def user_exists(username):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT 1 FROM users WHERE username=?"), (username.strip(),))
        return cur.fetchone() is not None

def change_password(username, new_password):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE users SET password_hash=? WHERE username=?"),
                    (_make_hash(new_password), username.strip()))


# ── Stories ───────────────────────────────────────────────────────────────────
def save_story(username, story):
    if _USE_PG:
        sql = """INSERT INTO stories
                   (story_key,username,title,genre,tone,messages,plot_arc,
                    writing_style,word_goal,style_dna,updated_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                 ON CONFLICT(story_key,username) DO UPDATE SET
                   title=EXCLUDED.title,genre=EXCLUDED.genre,tone=EXCLUDED.tone,
                   messages=EXCLUDED.messages,plot_arc=EXCLUDED.plot_arc,
                   writing_style=EXCLUDED.writing_style,word_goal=EXCLUDED.word_goal,
                   style_dna=EXCLUDED.style_dna,updated_at=NOW()"""
    else:
        sql = """INSERT INTO stories
                   (story_key,username,title,genre,tone,messages,plot_arc,
                    writing_style,word_goal,style_dna,updated_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                 ON CONFLICT(story_key,username) DO UPDATE SET
                   title=excluded.title,genre=excluded.genre,tone=excluded.tone,
                   messages=excluded.messages,plot_arc=excluded.plot_arc,
                   writing_style=excluded.writing_style,word_goal=excluded.word_goal,
                   style_dna=excluded.style_dna,updated_at=CURRENT_TIMESTAMP"""
    with _db() as (conn, cur):
        cur.execute(sql, (
            story["id"], username,
            story.get("title", "Untitled"), story.get("genre", "Fantasy"),
            story.get("tone", "Light"),
            json.dumps(story.get("messages", [])),
            json.dumps(story.get("plot_arc", {})),
            story.get("writing_style", ""), story.get("word_goal", 0),
            story.get("style_dna", ""),
        ))

def _row_to_story(r):
    if _USE_PG:
        arc  = r["plot_arc"]  if isinstance(r["plot_arc"],  dict) else json.loads(r["plot_arc"]  or "{}")
        msgs = r["messages"]  if isinstance(r["messages"],  list) else json.loads(r["messages"]  or "[]")
        return {"id": r["story_key"], "title": r["title"], "genre": r["genre"],
                "tone": r["tone"], "messages": msgs, "plot_arc": arc,
                "writing_style": r["writing_style"] or "",
                "word_goal": r["word_goal"] or 0, "style_dna": r["style_dna"] or ""}
    try:
        arc = json.loads(r[5]) if r[5] else {}
    except Exception:
        arc = {}
    return {"id": r[0], "title": r[1], "genre": r[2], "tone": r[3],
            "messages": json.loads(r[4] or "[]"), "plot_arc": arc,
            "writing_style": r[6] or "", "word_goal": r[7] or 0, "style_dna": r[8] or ""}

def load_stories(username):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT story_key,title,genre,tone,messages,plot_arc,"
                       "writing_style,word_goal,style_dna FROM stories "
                       "WHERE username=? ORDER BY updated_at DESC"), (username,))
        return [_row_to_story(r) for r in cur.fetchall()]

def load_story(username, story_id):
    """Load a single story by key. Returns story dict or None."""
    with _db() as (conn, cur):
        cur.execute(_q("SELECT story_key,title,genre,tone,messages,plot_arc,"
                       "writing_style,word_goal,style_dna FROM stories "
                       "WHERE username=? AND story_key=?"), (username, story_id))
        row = cur.fetchone()
    return _row_to_story(row) if row else None

def delete_story(username, story_id):
    tables = ["stories", "characters", "scenes", "world_notes", "snapshots", "chapters",
              "story_choices", "beta_sessions", "world_elements"]
    with _db() as (conn, cur):
        for t in tables:
            cur.execute(_q(f"DELETE FROM {t} WHERE story_key=? AND username=?"),
                        (story_id, username))
    logger.info("Story deleted: %s by %s", story_id, username)

def update_story_title(username, story_id, new_title):
    ts = "NOW()" if _USE_PG else "CURRENT_TIMESTAMP"
    with _db() as (conn, cur):
        cur.execute(_q(f"UPDATE stories SET title=?,updated_at={ts} WHERE story_key=? AND username=?"),
                    (new_title.strip(), story_id, username))


# ── Dashboard bulk loaders (eliminates N+1 queries) ──────────────────────────
def load_all_characters(username):
    """Return {story_key: [char_dict, ...]} for all stories of a user."""
    with _db() as (conn, cur):
        cur.execute(_q("SELECT story_key,id,name,role,description,speaking_style,arc_notes "
                       "FROM characters WHERE username=? ORDER BY created_at"), (username,))
        rows = cur.fetchall()
    result = {}
    for r in rows:
        sk = _r(r, "story_key", 0)
        char = {
            "id":            _r(r, "id",            1),
            "name":          _r(r, "name",          2),
            "role":          _r(r, "role",          3),
            "description":   _r(r, "description",   4),
            "speaking_style":_r(r, "speaking_style",5) or "",
            "arc_notes":     _r(r, "arc_notes",     6) or "",
        }
        result.setdefault(sk, []).append(char)
    return result

def load_all_scenes(username):
    """Return {story_key: [scene_dict, ...]} for all stories of a user."""
    with _db() as (conn, cur):
        cur.execute(_q("SELECT story_key,id,scene_order,title,location,purpose,"
                       "characters_in_scene,chapter_id FROM scenes "
                       "WHERE username=? ORDER BY scene_order"), (username,))
        rows = cur.fetchall()
    result = {}
    for r in rows:
        sk = _r(r, "story_key", 0)
        scene = {
            "id":         _r(r, "id",            1),
            "order":      _r(r, "scene_order",   2),
            "title":      _r(r, "title",         3),
            "location":   _r(r, "location",      4),
            "purpose":    _r(r, "purpose",        5),
            "characters": json.loads(_r(r, "characters_in_scene", 6) or "[]"),
            "chapter_id": _r(r, "chapter_id",    7),
        }
        result.setdefault(sk, []).append(scene)
    return result


# ── Chapters ──────────────────────────────────────────────────────────────────
def add_chapter(username, story_id, title):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT COALESCE(MAX(chapter_order),0) FROM chapters WHERE story_key=? AND username=?"),
                    (story_id, username))
        order = (cur.fetchone()[0] or 0) + 1
        cur.execute(_q("INSERT INTO chapters (story_key,username,chapter_order,title) VALUES (?,?,?,?)"),
                    (story_id, username, order, title.strip()))
        if _USE_PG:
            cur.execute("SELECT lastval()")
        else:
            cur.execute("SELECT last_insert_rowid()")
        return cur.fetchone()[0]

def load_chapters(username, story_id):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT id,chapter_order,title,summary FROM chapters "
                       "WHERE story_key=? AND username=? ORDER BY chapter_order"),
                    (story_id, username))
        rows = cur.fetchall()
    if _USE_PG:
        return [{"id": r["id"], "order": r["chapter_order"],
                 "title": r["title"], "summary": r["summary"] or ""} for r in rows]
    return [{"id": r[0], "order": r[1], "title": r[2], "summary": r[3] or ""} for r in rows]

def update_chapter(chapter_id, username, title, summary=""):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE chapters SET title=?,summary=? WHERE id=? AND username=?"),
                    (title.strip(), summary.strip(), chapter_id, username))

def delete_chapter(chapter_id, username):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE scenes SET chapter_id=NULL WHERE chapter_id=? AND username=?"),
                    (chapter_id, username))
        cur.execute(_q("DELETE FROM chapters WHERE id=? AND username=?"),
                    (chapter_id, username))

def assign_scene_to_chapter(scene_id, chapter_id, username):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE scenes SET chapter_id=? WHERE id=? AND username=?"),
                    (chapter_id, scene_id, username))

def save_chapter_summary(chapter_id, username, summary):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE chapters SET summary=? WHERE id=? AND username=?"),
                    (summary.strip(), chapter_id, username))


# ── Characters ────────────────────────────────────────────────────────────────
def add_character(username, story_id, name, role, description, speaking_style="", arc_notes=""):
    with _db() as (conn, cur):
        cur.execute(_q("INSERT INTO characters (story_key,username,name,role,description,speaking_style,arc_notes) VALUES (?,?,?,?,?,?,?)"),
                    (story_id, username, name.strip(), role.strip(), description.strip(),
                     speaking_style.strip(), arc_notes.strip()))

def load_characters(username, story_id):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT id,name,role,description,speaking_style,arc_notes FROM characters "
                       "WHERE story_key=? AND username=? ORDER BY created_at"), (story_id, username))
        rows = cur.fetchall()
    if _USE_PG:
        return [{"id": r["id"], "name": r["name"], "role": r["role"], "description": r["description"],
                 "speaking_style": r["speaking_style"] or "", "arc_notes": r["arc_notes"] or ""} for r in rows]
    return [{"id": r[0], "name": r[1], "role": r[2], "description": r[3],
             "speaking_style": r[4] or "", "arc_notes": r[5] or ""} for r in rows]

def delete_character(char_id, username):
    with _db() as (conn, cur):
        cur.execute(_q("DELETE FROM characters WHERE id=? AND username=?"), (char_id, username))

def update_character(char_id, username, name, role, description, speaking_style, arc_notes=""):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE characters SET name=?,role=?,description=?,speaking_style=?,arc_notes=? WHERE id=? AND username=?"),
                    (name.strip(), role.strip(), description.strip(),
                     speaking_style.strip(), arc_notes.strip(), char_id, username))


# ── Scenes ────────────────────────────────────────────────────────────────────
def add_scene(username, story_id, title, location, purpose, characters_in, chapter_id=None):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT COALESCE(MAX(scene_order),0) FROM scenes WHERE story_key=? AND username=?"),
                    (story_id, username))
        order = (cur.fetchone()[0] or 0) + 1
        cur.execute(_q("INSERT INTO scenes (story_key,username,scene_order,title,location,purpose,characters_in_scene,chapter_id) VALUES (?,?,?,?,?,?,?,?)"),
                    (story_id, username, order, title.strip(), location.strip(),
                     purpose.strip(), json.dumps(characters_in), chapter_id))

def load_scenes(username, story_id):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT id,scene_order,title,location,purpose,characters_in_scene,chapter_id "
                       "FROM scenes WHERE story_key=? AND username=? ORDER BY scene_order"),
                    (story_id, username))
        rows = cur.fetchall()
    if _USE_PG:
        return [{"id": r["id"], "order": r["scene_order"], "title": r["title"],
                 "location": r["location"], "purpose": r["purpose"],
                 "characters": json.loads(r["characters_in_scene"] or "[]"),
                 "chapter_id": r["chapter_id"]} for r in rows]
    return [{"id": r[0], "order": r[1], "title": r[2], "location": r[3],
             "purpose": r[4], "characters": json.loads(r[5] or "[]"),
             "chapter_id": r[6]} for r in rows]

def delete_scene(scene_id, username):
    with _db() as (conn, cur):
        cur.execute(_q("DELETE FROM scenes WHERE id=? AND username=?"), (scene_id, username))

def update_scene(scene_id, username, title, location, purpose, characters_in):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE scenes SET title=?,location=?,purpose=?,characters_in_scene=? WHERE id=? AND username=?"),
                    (title.strip(), location.strip(), purpose.strip(),
                     json.dumps(characters_in), scene_id, username))


# ── World Notes ───────────────────────────────────────────────────────────────
NOTE_CATEGORIES = ["Lore", "Magic System", "Geography", "History", "Factions", "Other"]

def add_note(username, story_id, category, title, content):
    with _db() as (conn, cur):
        cur.execute(_q("INSERT INTO world_notes (story_key,username,category,title,content) VALUES (?,?,?,?,?)"),
                    (story_id, username, category.strip(), title.strip(), content.strip()))

def load_notes(username, story_id):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT id,category,title,content FROM world_notes "
                       "WHERE story_key=? AND username=? ORDER BY category,created_at"),
                    (story_id, username))
        rows = cur.fetchall()
    if _USE_PG:
        return [{"id": r["id"], "category": r["category"], "title": r["title"],
                 "content": r["content"]} for r in rows]
    return [{"id": r[0], "category": r[1], "title": r[2], "content": r[3]} for r in rows]

def update_note(note_id, username, category, title, content):
    with _db() as (conn, cur):
        cur.execute(_q("UPDATE world_notes SET category=?,title=?,content=? WHERE id=? AND username=?"),
                    (category.strip(), title.strip(), content.strip(), note_id, username))

def delete_note(note_id, username):
    with _db() as (conn, cur):
        cur.execute(_q("DELETE FROM world_notes WHERE id=? AND username=?"), (note_id, username))


# ── Snapshots ─────────────────────────────────────────────────────────────────
def save_snapshot(username, story_id, name, messages):
    wc = sum(len(m["content"].split()) for m in messages)
    with _db() as (conn, cur):
        cur.execute(_q("INSERT INTO snapshots (story_key,username,name,messages,word_count) VALUES (?,?,?,?,?)"),
                    (story_id, username, name.strip(), json.dumps(messages), wc))

def load_snapshots(username, story_id):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT id,name,word_count,created_at FROM snapshots "
                       "WHERE story_key=? AND username=? ORDER BY created_at DESC"),
                    (story_id, username))
        rows = cur.fetchall()
    if _USE_PG:
        return [{"id": r["id"], "name": r["name"], "word_count": r["word_count"],
                 "created_at": str(r["created_at"])} for r in rows]
    return [{"id": r[0], "name": r[1], "word_count": r[2], "created_at": r[3]} for r in rows]

def restore_snapshot(snap_id, username):
    with _db() as (conn, cur):
        cur.execute(_q("SELECT messages FROM snapshots WHERE id=? AND username=?"),
                    (snap_id, username))
        row = cur.fetchone()
    if not row:
        return None
    data = _r(row, "messages", 0)
    return data if isinstance(data, list) else json.loads(data)

def delete_snapshot(snap_id, username):
    with _db() as (conn, cur):
        cur.execute(_q("DELETE FROM snapshots WHERE id=? AND username=?"), (snap_id, username))


# ── Search (title only to avoid JSON blob scan) ───────────────────────────────
def search_stories(username, query):
    """Search by title only. For content search use FTS5 (future)."""
    if not query.strip():
        return []
    q = f"%{query.lower()}%"
    with _db() as (conn, cur):
        cur.execute(_q("SELECT story_key,title FROM stories "
                       "WHERE username=? AND LOWER(title) LIKE ? LIMIT 50"),
                    (username, q))
        rows = cur.fetchall()
    return [{"id": _r(r, "story_key", 0), "title": _r(r, "title", 1), "snippets": []} for r in rows]


# ── Writing Sessions ──────────────────────────────────────────────────────────
def log_writing_session(username, story_key, words_written, duration_minutes=0):
    from datetime import date
    today = date.today().isoformat()
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "SELECT id, words_written FROM writing_sessions "
                "WHERE username=? AND story_key=? AND session_date=?"),
                (username, story_key, today))
            row = cur.fetchone()
            if row:
                existing = _r(row, "words_written", 1)
                row_id   = _r(row, "id", 0)
                cur.execute(_q(
                    "UPDATE writing_sessions "
                    "SET words_written=?, duration_minutes=duration_minutes+? "
                    "WHERE id=?"),
                    (existing + words_written, duration_minutes, row_id))
            else:
                cur.execute(_q(
                    "INSERT INTO writing_sessions "
                    "(username,story_key,session_date,words_written,duration_minutes) "
                    "VALUES (?,?,?,?,?)"),
                    (username, story_key, today, words_written, duration_minutes))
    except Exception as e:
        logger.error("log_writing_session: %s", e)

def load_writing_sessions(username, days=90):
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "SELECT session_date, SUM(words_written) as total_words "
                "FROM writing_sessions WHERE username=? "
                "GROUP BY session_date ORDER BY session_date DESC LIMIT ?"),
                (username, days))
            rows = cur.fetchall()
            return [{"date": _r(r, "session_date", 0), "words": _r(r, "total_words", 1)}
                    for r in rows]
    except Exception as e:
        logger.error("load_writing_sessions: %s", e)
        return []

def get_writing_streak(username):
    from datetime import date, timedelta
    sessions = load_writing_sessions(username, 365)
    if not sessions:
        return 0
    dates = {s["date"] for s in sessions}
    streak = 0
    day = date.today()
    while day.isoformat() in dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


# ── Achievements ──────────────────────────────────────────────────────────────
def unlock_achievement(username, achievement_id):
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "INSERT OR IGNORE INTO achievements (username, achievement_id) VALUES (?,?)"),
                (username, achievement_id))
            return cur.rowcount > 0
    except Exception as e:
        logger.error("unlock_achievement: %s", e)
        return False

def load_achievements(username):
    try:
        with _db() as (conn, cur):
            cur.execute(_q("SELECT achievement_id FROM achievements WHERE username=?"), (username,))
            return {_r(r, "achievement_id", 0) for r in cur.fetchall()}
    except Exception as e:
        logger.error("load_achievements: %s", e)
        return set()


# ── World Elements ────────────────────────────────────────────────────────────
import json as _json

def save_world_element(username, story_key, element_type, name, data: dict):
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "INSERT INTO world_elements (username,story_key,element_type,name,data) "
                "VALUES (?,?,?,?,?)"),
                (username, story_key, element_type, name, _json.dumps(data)))
            if _USE_PG:
                cur.execute("SELECT lastval()")
            else:
                cur.execute("SELECT last_insert_rowid()")
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("save_world_element: %s", e)
        return None

def load_world_elements(username, story_key, element_type=None):
    """FIX: use explicit column names instead of SELECT * with positional indices."""
    try:
        with _db() as (conn, cur):
            if element_type:
                cur.execute(_q(
                    "SELECT id,element_type,name,data FROM world_elements "
                    "WHERE username=? AND story_key=? AND element_type=? ORDER BY created_at"),
                    (username, story_key, element_type))
            else:
                cur.execute(_q(
                    "SELECT id,element_type,name,data FROM world_elements "
                    "WHERE username=? AND story_key=? ORDER BY element_type,created_at"),
                    (username, story_key))
            rows = cur.fetchall()
            out = []
            for r in rows:
                d = {"id": _r(r, "id", 0), "element_type": _r(r, "element_type", 1),
                     "name": _r(r, "name", 2)}
                try:
                    d["data"] = _json.loads(_r(r, "data", 3) or "{}")
                except Exception:
                    d["data"] = {}
                out.append(d)
            return out
    except Exception as e:
        logger.error("load_world_elements: %s", e)
        return []

def update_world_element(elem_id, username, name, data: dict):
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "UPDATE world_elements SET name=?,data=? WHERE id=? AND username=?"),
                (name, _json.dumps(data), elem_id, username))
    except Exception as e:
        logger.error("update_world_element: %s", e)

def delete_world_element(elem_id, username):
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "DELETE FROM world_elements WHERE id=? AND username=?"),
                (elem_id, username))
    except Exception as e:
        logger.error("delete_world_element: %s", e)


# ── Story Choices (CYOA) ───────────────────────────────────────────────────────
def save_story_choice(username, story_key, parent_idx, choice_label, branch_messages):
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "INSERT INTO story_choices "
                "(username,story_key,parent_message_idx,choice_label,branch_messages) "
                "VALUES (?,?,?,?,?)"),
                (username, story_key, parent_idx, choice_label, _json.dumps(branch_messages)))
            if _USE_PG:
                cur.execute("SELECT lastval()")
            else:
                cur.execute("SELECT last_insert_rowid()")
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("save_story_choice: %s", e)
        return None

def load_story_choices(username, story_key):
    """FIX: use explicit column names to avoid positional index fragility."""
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "SELECT id,parent_message_idx,choice_label,branch_messages "
                "FROM story_choices WHERE username=? AND story_key=? ORDER BY created_at"),
                (username, story_key))
            rows = cur.fetchall()
            out = []
            for r in rows:
                d = {"id": _r(r, "id", 0),
                     "parent_message_idx": _r(r, "parent_message_idx", 1),
                     "choice_label": _r(r, "choice_label", 2)}
                try:
                    d["branch_messages"] = _json.loads(_r(r, "branch_messages", 3) or "[]")
                except Exception:
                    d["branch_messages"] = []
                out.append(d)
            return out
    except Exception as e:
        logger.error("load_story_choices: %s", e)
        return []

def delete_story_choice(choice_id, username):
    try:
        with _db() as (conn, cur):
            cur.execute(_q("DELETE FROM story_choices WHERE id=? AND username=?"),
                        (choice_id, username))
    except Exception as e:
        logger.error("delete_story_choice: %s", e)


# ── Beta Reading Sessions ──────────────────────────────────────────────────────
import secrets as _secrets
import json as _json2

def create_beta_session(username, story_key, reader_name="Anonymous", days=30):
    from datetime import datetime, timedelta
    token   = _secrets.token_urlsafe(24)
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "INSERT INTO beta_sessions "
                "(username,story_key,token,reader_name,feedback,expires_at) "
                "VALUES (?,?,?,?,?,?)"),
                (username, story_key, token, reader_name, "[]", expires))
        return token
    except Exception as e:
        logger.error("create_beta_session: %s", e)
        return None

def load_beta_sessions(username, story_key):
    """FIX: use explicit column names."""
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "SELECT id,token,reader_name,feedback,created_at,expires_at "
                "FROM beta_sessions WHERE username=? AND story_key=? "
                "ORDER BY created_at DESC"),
                (username, story_key))
            rows = cur.fetchall()
            out = []
            for r in rows:
                try:
                    fb = _json2.loads(_r(r, "feedback", 3) or "[]")
                except Exception:
                    fb = []
                out.append({
                    "id":          _r(r, "id",          0),
                    "token":       _r(r, "token",       1),
                    "reader_name": _r(r, "reader_name", 2),
                    "feedback":    fb,
                    "created_at":  str(_r(r, "created_at", 4))[:16],
                    "expires_at":  str(_r(r, "expires_at", 5))[:10],
                })
            return out
    except Exception as e:
        logger.error("load_beta_sessions: %s", e)
        return []

def get_beta_session_by_token(token):
    """FIX: use explicit column names."""
    try:
        with _db() as (conn, cur):
            cur.execute(_q(
                "SELECT id,username,story_key,token,reader_name,feedback,expires_at "
                "FROM beta_sessions WHERE token=?"), (token,))
            r = cur.fetchone()
            if not r:
                return None
            try:
                fb = _json2.loads(_r(r, "feedback", 5) or "[]")
            except Exception:
                fb = []
            return {
                "id":          _r(r, "id",          0),
                "username":    _r(r, "username",    1),
                "story_key":   _r(r, "story_key",   2),
                "token":       _r(r, "token",       3),
                "reader_name": _r(r, "reader_name", 4),
                "feedback":    fb,
                "expires_at":  str(_r(r, "expires_at", 6))[:10],
            }
    except Exception as e:
        logger.error("get_beta_session_by_token: %s", e)
        return None

def add_beta_feedback(token, comment, rating, chapter="General"):
    from datetime import datetime
    sess = get_beta_session_by_token(token)
    if not sess:
        return False
    fb = sess.get("feedback", [])
    fb.append({"comment": comment, "rating": rating,
               "chapter": chapter, "at": datetime.now().isoformat()[:16]})
    try:
        with _db() as (conn, cur):
            cur.execute(_q("UPDATE beta_sessions SET feedback=? WHERE token=?"),
                        (_json2.dumps(fb), token))
        return True
    except Exception as e:
        logger.error("add_beta_feedback: %s", e)
        return False

def delete_beta_session(session_id, username):
    try:
        with _db() as (conn, cur):
            cur.execute(_q("DELETE FROM beta_sessions WHERE id=? AND username=?"),
                        (session_id, username))
    except Exception as e:
        logger.error("delete_beta_session: %s", e)

def get_story_updated_at(username, story_id):
    """For autosave conflict detection. Returns Unix timestamp or None."""
    try:
        with _db() as (conn, cur):
            cur.execute(_q("SELECT updated_at FROM stories WHERE story_key=? AND username=?"),
                        (story_id, username))
            row = cur.fetchone()
        if not row:
            return None
        raw = _r(row, "updated_at", 0)
        if raw is None:
            return None
        if hasattr(raw, "timestamp"):
            return raw.timestamp()
        import datetime as _dt
        raw_str = str(raw).replace("Z", "").replace("T", " ")
        try:
            return _dt.datetime.fromisoformat(raw_str).timestamp()
        except Exception:
            return None
    except Exception:
        return None
