import time
import html as _html
import streamlit as st
from styles import dashboard_style, theme_toggle_widget
from utils import force_sidebar_open as _force_sidebar_open
from auth import show_account_settings, _full_logout
from database import (save_story, delete_story, update_story_title,
                      load_characters, load_scenes, search_stories)

try:
    from onboarding import maybe_show_onboarding, show_onboarding
    _HAS_ONBOARDING = True
except ImportError:
    _HAS_ONBOARDING = False

# ── Story templates ────────────────────────────────────────────────────────────
_TEMPLATES = [
    {
        "name": "🕵️ Mystery Thriller",
        "genre": "Mystery", "tone": "Suspenseful",
        "opener": "The body was found at 6:42 AM, still warm. Detective Lena Cross arrived at the scene to find something that would change everything she thought she knew about this quiet town.",
    },
    {
        "name": "🌌 Sci-Fi Adventure",
        "genre": "Science Fiction", "tone": "Epic",
        "opener": "The distress signal had been broadcasting for 300 years before anyone answered. Now, with three hours of oxygen left and a dying crew, Commander Yara had to decide: investigate the alien vessel, or flee.",
    },
    {
        "name": "💔 Romance Drama",
        "genre": "Romance", "tone": "Emotional",
        "opener": "They had been best friends for eleven years before the night everything changed. Now, standing at opposite ends of the airport departures hall, neither of them could move.",
    },
    {
        "name": "🧙 Fantasy Quest",
        "genre": "Fantasy", "tone": "Epic",
        "opener": "The last dragon egg had been missing for a thousand years. Mira had found it in her grandmother's attic, still warm, still pulsing faintly with a light that had no earthly source.",
    },
    {
        "name": "👻 Horror",
        "genre": "Horror", "tone": "Dark",
        "opener": "The children in the village had stopped speaking three days ago. Not a word, not a whisper. They only stared at the old mill at the edge of the forest — and smiled.",
    },
    {
        "name": "📖 Blank Canvas",
        "genre": "Fantasy", "tone": "Light",
        "opener": "",
    },
]


def show_dashboard():
    # ── Onboarding — auto-shows for new users ──────────────────────────────
    if _HAS_ONBOARDING and maybe_show_onboarding():
        return

    # Help button — reopens onboarding guide
    try:
        from onboarding import show_help_button
        with st.sidebar:
            show_help_button()
    except ImportError:
        pass
    dashboard_style()
    _force_sidebar_open()

    username = st.session_state.username
    stories  = st.session_state.stories

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        is_light = st.session_state.get("light_theme", False)
        logo_color = "#3553E8" if is_light else "#4D6BFE"
        sub_color  = "#6B7080" if is_light else "#8B8FA8"
        st.markdown(
            f"<div style='font-family:Inter,sans-serif;font-size:1.1rem;"
            f"font-weight:700;color:{logo_color};margin-bottom:2px;letter-spacing:-0.02em;'>"
            f"&#9670; NarrativeForge</div>"
            f"<div style='font-size:0.7rem;color:{sub_color};font-family:JetBrains Mono,monospace;'>"
            f"Signed in as <strong>{st.session_state.username}</strong></div>",
            unsafe_allow_html=True)
        st.markdown("---")

        # ── Writing streak ─────────────────────────────────────────────────────
        total_words = sum(
            sum(len(m["content"].split()) for m in s.get("messages", []))
            for s in stories
        )
        goal_words = 10_000
        pct = min(total_words / goal_words, 1.0)
        st.markdown(
            f"<div style='font-size:0.68rem;font-family:JetBrains Mono,monospace;"
            f"color:{sub_color};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;'>"
            f"📝 Writing Goal</div>",
            unsafe_allow_html=True)
        st.progress(pct)
        st.markdown(
            f"<div style='font-size:0.70rem;color:{sub_color};margin-bottom:10px;'>"
            f"{total_words:,} / {goal_words:,} words ({int(pct*100)}%)</div>",
            unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(
            f"<div style='color:{sub_color};font-size:0.75rem;line-height:1.5;margin-bottom:8px;'>"
            "Open a story to access the writing workspace, character manager, "
            "scene organiser, plot arc, and intelligence tools.</div>",
            unsafe_allow_html=True)
        st.markdown("---")

        show_account_settings()
        st.markdown("---")
        theme_toggle_widget()
        st.markdown("---")
        if st.button("Sign Out", use_container_width=True):
            _full_logout()
            st.rerun()

    # ── Page header ────────────────────────────────────────────────────────────
    st.markdown(
        "<div class='dash-header'>Your Stories</div>"
        "<div class='dash-sub'>Pick up where you left off, or start something new.</div>",
        unsafe_allow_html=True)

    # ── Daily writing prompt ───────────────────────────────────────────────────
    show_daily_prompt()

    # ── Stats bar ─────────────────────────────────────────────────────────────
    if stories:
        total_chars  = sum(len(load_characters(username, s["id"])) for s in stories)
        total_scenes = sum(len(load_scenes(username, s["id"]))     for s in stories)
        total_words2 = sum(sum(len(m["content"].split()) for m in s.get("messages", [])) for s in stories)
        read_mins    = max(1, total_words2 // 200)
        c1, c2, c3, c4, c5 = st.columns(5)
        for col, num, label in [
            (c1, len(stories),        "Stories"),
            (c2, f"{total_words2:,}", "Total Words"),
            (c3, total_chars,         "Characters"),
            (c4, total_scenes,        "Scenes"),
            (c5, f"~{read_mins}m",    "Read Time"),
        ]:
            col.markdown(
                f"<div class='stat-card'>"
                f"<div class='stat-num'>{num}</div>"
                f"<div class='stat-label'>{label}</div>"
                f"</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:1px;background:var(--border-subtle);margin-bottom:16px;'></div>",
                    unsafe_allow_html=True)

    # ── Controls row: Search | Sort | Filter | New Story ──────────────────────
    col_s, col_sort, col_genre, col_new = st.columns([3, 1.2, 1.2, 1.2])

    with col_s:
        search_query = st.text_input(
            "search", placeholder="🔍  Search by title or content…",
            key="dash_search", label_visibility="collapsed", max_chars=100)
    with col_sort:
        sort_by = st.selectbox("Sort", ["Newest", "Oldest", "Most Words", "A→Z"],
                               key="dash_sort", label_visibility="collapsed")
    with col_genre:
        all_genres = ["All Genres"] + sorted({s.get("genre","Fantasy") for s in stories})
        genre_filter = st.selectbox("Genre", all_genres,
                                    key="dash_genre", label_visibility="collapsed")
    with col_new:
        if st.button("＋ New Story", use_container_width=True, type="primary"):
            st.session_state["_show_template_picker"] = True
            st.rerun()

    # ── Template picker modal ──────────────────────────────────────────────────
    if st.session_state.get("_show_template_picker"):
        st.markdown("---")
        st.markdown(
            "<div style='font-size:0.92rem;font-weight:600;color:var(--text-primary);"
            "margin-bottom:10px;'>Choose a starting template</div>",
            unsafe_allow_html=True)
        tcols = st.columns(3)
        for i, tmpl in enumerate(_TEMPLATES):
            with tcols[i % 3]:
                opener_preview = ("<br>" + tmpl["opener"][:70] + "…") if tmpl["opener"] else ""
                st.markdown(
                    f"<div class='template-card'>"
                    f"<div class='template-title'>{tmpl['name']}</div>"
                    f"<div class='template-desc'>"
                    f"{tmpl['genre']} · {tmpl['tone']}"
                    f"{opener_preview}"
                    f"</div></div>",
                    unsafe_allow_html=True)
                if st.button("Use this", key=f"tmpl_{i}", use_container_width=True):
                    story_id  = f"story_{int(time.time())}"
                    new_story = {
                        "id": story_id,
                        "title": f"Untitled Story {len(stories)+1}",
                        "genre": tmpl["genre"],
                        "tone":  tmpl["tone"],
                        "messages": (
                            [{"role": "user", "content": tmpl["opener"]}]
                            if tmpl["opener"] else []
                        ),
                        "plot_arc": {}, "writing_style": "",
                        "word_goal": 0, "style_dna": "",
                    }
                    st.session_state.stories.append(new_story)
                    save_story(username, new_story)
                    st.session_state.current_story = story_id
                    st.session_state.current_view  = "workspace"
                    st.session_state.pop("_show_template_picker", None)
                    st.rerun()

        if st.button("✕ Cancel", key="tmpl_cancel"):
            st.session_state.pop("_show_template_picker", None)
            st.rerun()
        st.markdown("---")

    # ── Filter & sort stories ──────────────────────────────────────────────────
    if search_query.strip():
        results         = search_stories(username, search_query.strip())
        result_ids      = {r["id"] for r in results}
        display_stories = [s for s in stories if s["id"] in result_ids]
        if st.button("✕ Clear", key="clear_search",
                     on_click=lambda: st.session_state.update({"dash_search": ""})):
            st.rerun()
    else:
        display_stories = list(stories)

    # Genre filter
    if genre_filter != "All Genres":
        display_stories = [s for s in display_stories if s.get("genre") == genre_filter]

    # Sort
    def _word_count(s):
        return sum(len(m["content"].split()) for m in s.get("messages", []))

    if sort_by == "Newest":
        display_stories = list(reversed(display_stories))
    elif sort_by == "Most Words":
        display_stories = sorted(display_stories, key=_word_count, reverse=True)
    elif sort_by == "A→Z":
        display_stories = sorted(display_stories, key=lambda s: s["title"].lower())
    # "Oldest" = natural order

    st.markdown("<br>", unsafe_allow_html=True)

    if not display_stories:
        st.markdown(
            "<div class='empty-state'>"
            "<div style='font-size:2.5rem;margin-bottom:12px;color:var(--primary);'>&#9670;</div>"
            "<div style='color:var(--text-primary);font-size:1.0rem;font-weight:600;'>"
            "No stories yet.</div>"
            "<div style='color:var(--text-muted);font-size:0.88rem;margin-top:6px;'>"
            "Click <strong style=\"color:var(--primary);\">＋ New Story</strong> to begin.</div>"
            "</div>",
            unsafe_allow_html=True)
        return

    # ── Story cards ────────────────────────────────────────────────────────────
    for story in display_stories:
        msg_count  = len(story.get("messages", []))
        word_count = _word_count(story)
        chars      = load_characters(username, story["id"])
        scenes_    = load_scenes(username, story["id"])
        arc        = story.get("plot_arc", {})
        arc_done   = sum(1 for k in ["beginning","rising_action","climax",
                                      "falling_action","resolution"] if arc.get(k))
        read_min   = max(1, word_count // 200)
        goal       = story.get("word_goal", 0)
        goal_pct   = min(word_count / goal, 1.0) if goal > 0 else None
        goal_bar   = ""
        if goal_pct is not None:
            bar_w = int(goal_pct * 100)
            goal_bar = (
                f"<div style='margin-top:8px;'>"
                f"<div style='font-size:0.60rem;color:var(--text-muted);font-family:JetBrains Mono,monospace;"
                f"margin-bottom:3px;'>WORD GOAL {word_count:,}/{goal:,} ({bar_w}%)</div>"
                f"<div style='background:var(--primary-dim);border-radius:99px;height:4px;'>"
                f"<div style='background:var(--primary);width:{bar_w}%;height:4px;border-radius:99px;'></div>"
                f"</div></div>"
            )

        st.markdown(f"""
            <div class='story-card'>
                <h3>{_html.escape(story['title'])}</h3>
                <div style='margin-top:6px;'>
                    <span class='story-badge'>{_html.escape(story['genre'])}</span>
                    <span class='story-badge'>{_html.escape(story['tone'])}</span>
                    <span class='story-badge'>{word_count:,} words</span>
                    <span class='story-badge'>~{read_min}m read</span>
                    <span class='story-badge'>{msg_count} messages</span>
                    <span class='story-badge'>{len(chars)} chars</span>
                    <span class='story-badge'>{len(scenes_)} scenes</span>
                    <span class='story-badge'>Arc {arc_done}/5</span>
                </div>
                {goal_bar}
            </div>
        """, unsafe_allow_html=True)

        sid = story["id"]
        c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1, 1, 1, 1, 1])

        # ── Rename ──────────────────────────────────────────────────────────
        with c1:
            if st.session_state.get(f"renaming_{sid}"):
                new_name = st.text_input("Rename", value=story["title"],
                                          max_chars=100, key=f"rename_{sid}",
                                          label_visibility="collapsed")
                sr1, sr2 = st.columns(2)
                with sr1:
                    if st.button("Save", key=f"save_ren_{sid}", use_container_width=True):
                        if new_name.strip():
                            story["title"] = new_name.strip()
                            update_story_title(username, sid, new_name.strip())
                        st.session_state[f"renaming_{sid}"] = False
                        st.rerun()
                with sr2:
                    if st.button("Cancel", key=f"cancel_ren_{sid}", use_container_width=True):
                        st.session_state[f"renaming_{sid}"] = False
                        st.rerun()
            else:
                if st.button("✏️ Rename", key=f"ren_{sid}", use_container_width=True):
                    st.session_state[f"renaming_{sid}"] = True
                    st.rerun()

        # ── Open ────────────────────────────────────────────────────────────
        with c2:
            if st.button("Open", key=f"open_{sid}",
                          use_container_width=True, type="primary"):
                st.session_state.current_story = sid
                st.session_state.current_view  = "workspace"
                st.session_state.show_cowrite_options = False
                st.rerun()

        # ── Duplicate ────────────────────────────────────────────────────────
        with c3:
            if st.button("⧉ Copy", key=f"dup_{sid}", use_container_width=True):
                import copy
                dup = copy.deepcopy(story)
                dup["id"]    = f"story_{int(time.time())}"
                dup["title"] = story["title"] + " (Copy)"
                st.session_state.stories.append(dup)
                save_story(username, dup)
                st.rerun()

        # ── Export quick link ─────────────────────────────────────────────
        with c4:
            text = "\n\n".join(m["content"] for m in story.get("messages", []))
            st.download_button(
                "⬇ TXT", data=text,
                file_name=f"{story['title'].replace(' ','_')}.txt",
                mime="text/plain",
                key=f"dl_{sid}", use_container_width=True)

        # ── Story Cover Card ──────────────────────────────────────────────
        with c5:
            cover_data = show_story_cover(story)
            st.download_button(
                "🖼 Cover",
                data=cover_data,
                file_name=f"{story['title'].replace(' ','_')}_cover.html",
                mime="text/html",
                key=f"cover_{sid}", use_container_width=True)

        # ── Delete ──────────────────────────────────────────────────────────
        with c6:
            if not st.session_state.get(f"_confirm_del_{sid}"):
                if st.button("🗑 Del", key=f"del_{sid}", use_container_width=True):
                    st.session_state[f"_confirm_del_{sid}"] = True
                    st.rerun()
            else:
                st.markdown(
                    "<div style='background:var(--danger-dim);"
                    "border:1px solid var(--danger);border-radius:8px;"
                    "padding:6px 10px;font-size:0.72rem;color:var(--danger);margin-bottom:4px;'>"
                    "Delete permanently?</div>", unsafe_allow_html=True)
                da, db = st.columns(2)
                with da:
                    if st.button("Yes", key=f"confirm_del_{sid}", use_container_width=True):
                        st.session_state.stories = [
                            s for s in st.session_state.stories if s["id"] != sid]
                        delete_story(username, sid)
                        st.session_state.pop(f"_confirm_del_{sid}", None)
                        st.rerun()
                with db:
                    if st.button("No", key=f"cancel_del_{sid}", use_container_width=True):
                        st.session_state.pop(f"_confirm_del_{sid}", None)
                        st.rerun()

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Daily Writing Prompt + Story Cover Card — appended to module
# ══════════════════════════════════════════════════════════════════════════════

_DAILY_PROMPTS = [
    "A letter arrives addressed to someone who died ten years ago.",
    "Two strangers share an umbrella during a storm. Neither of them wants it to stop raining.",
    "The last library on Earth is about to close. One book hasn't been returned.",
    "She found her own obituary in the newspaper — dated tomorrow.",
    "The AI assistant started leaving notes that weren't in its programming.",
    "Every morning, the same stranger waves from the house across the street. Today, the house is empty.",
    "The map leads to a place that doesn't exist — but you've been there before.",
    "A musician hears a melody that no one else can hear, but the melody is getting louder.",
    "The time capsule was supposed to be opened in 50 years. It's been opened early.",
    "You find a photograph of yourself from a day you've never lived.",
    "The last lighthouse keeper left one final entry in the logbook: 'It found me.'",
    "A clockmaker discovers one clock that always runs exactly one hour behind.",
    "The botanist finds a plant that only blooms in the presence of lies.",
    "An actor memorises a script and realises the play is about their own life.",
    "The translator discovers the ancient text is a warning — written last week.",
    "Two old friends meet after 20 years. One of them hasn't aged at all.",
    "The painter finishes a portrait of someone they've never met. The next day, that person knocks on the door.",
    "A child builds a door in the middle of the forest. Something opens it from the other side.",
    "The astronaut returns from six months in space to find no one remembers her.",
    "Every night at 3AM, the piano plays a song no one taught it.",
    "She inherited a house full of mirrors. Every mirror shows a different room.",
    "The detective solves every case in the city — except his own disappearance.",
    "The words in the book change every time you read it.",
    "A chef discovers one ingredient that makes anyone tell the truth.",
    "The last bus of the night goes somewhere that isn't on the route map.",
    "They built a city on the ocean floor. Something was already living there.",
    "A historian finds evidence that a famous event never happened.",
    "The lighthouse sends a signal. No one has staffed it for a hundred years.",
    "She wakes up speaking a language she's never learned.",
    "The old radio picks up a broadcast from 50 years ago — and it's talking about today.",
]


def show_daily_prompt():
    """Show today's writing prompt as a card."""
    day_index = int(time.time() // 86400) % len(_DAILY_PROMPTS)
    prompt = _DAILY_PROMPTS[day_index]
    is_light = st.session_state.get("light_theme", False)
    bg    = "#FFFFFF" if is_light else "#161820"
    border = "rgba(53,83,232,0.22)" if is_light else "rgba(77,107,254,0.22)"
    st.markdown(
        f"<div style='background:{bg};border:1px solid {border};"
        f"border-left:3px solid var(--primary);border-radius:12px;"
        f"padding:14px 18px;margin-bottom:16px;'>"
        f"<div style='font-size:0.60rem;font-family:JetBrains Mono,monospace;"
        f"color:var(--primary);text-transform:uppercase;letter-spacing:0.1em;"
        f"margin-bottom:6px;'>✦ Today's Writing Prompt</div>"
        f"<div style='font-size:0.92rem;color:var(--text-primary);line-height:1.6;"
        f"font-style:italic;'>\"{prompt}\"</div>"
        f"</div>",
        unsafe_allow_html=True)


def show_story_cover(story):
    """Generate a downloadable HTML cover card for a story."""
    import urllib.parse
    title   = story.get("title", "Untitled")
    genre   = story.get("genre", "Fiction")
    tone    = story.get("tone", "")
    wc      = sum(len(m["content"].split()) for m in story.get("messages", []))

    html_cover = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
  * {{ margin:0;padding:0;box-sizing:border-box; }}
  body {{
    width:600px;height:900px;
    background: linear-gradient(160deg, #0D0E14 0%, #1A1E3A 60%, #0D0E14 100%);
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    font-family:'Inter',sans-serif;
    position:relative;overflow:hidden;
  }}
  .glow {{
    position:absolute;top:25%;left:50%;transform:translate(-50%,-50%);
    width:400px;height:400px;
    background:radial-gradient(circle,rgba(77,107,254,0.25) 0%,transparent 70%);
    border-radius:50%;
  }}
  .border-top {{
    position:absolute;top:0;left:0;right:0;height:4px;
    background:linear-gradient(90deg,#3553E8,#7B96FF,#3553E8);
  }}
  .border-bottom {{
    position:absolute;bottom:0;left:0;right:0;height:4px;
    background:linear-gradient(90deg,#3553E8,#7B96FF,#3553E8);
  }}
  .content {{
    position:relative;z-index:2;text-align:center;padding:60px 50px;
  }}
  .diamond {{
    font-size:2.5rem;color:#4D6BFE;margin-bottom:32px;letter-spacing:8px;
  }}
  .title {{
    font-size:3.2rem;font-weight:900;color:#F0F0F5;
    line-height:1.1;letter-spacing:-0.03em;margin-bottom:24px;
  }}
  .divider {{
    width:60px;height:2px;background:#4D6BFE;margin:0 auto 24px;
  }}
  .genre {{
    font-size:0.95rem;color:#A8BCFF;letter-spacing:0.25em;
    text-transform:uppercase;margin-bottom:8px;
  }}
  .tone {{
    font-size:0.80rem;color:#8B8FA8;letter-spacing:0.15em;
    text-transform:uppercase;margin-bottom:48px;
  }}
  .stats {{
    display:flex;gap:40px;justify-content:center;margin-bottom:48px;
  }}
  .stat {{ text-align:center; }}
  .stat-n {{ font-size:1.4rem;font-weight:700;color:#4D6BFE; }}
  .stat-l {{ font-size:0.65rem;color:#8B8FA8;letter-spacing:0.12em;text-transform:uppercase;margin-top:2px; }}
  .footer {{
    font-size:0.72rem;color:#4A4D60;letter-spacing:0.15em;text-transform:uppercase;
  }}
</style>
</head>
<body>
  <div class="glow"></div>
  <div class="border-top"></div>
  <div class="border-bottom"></div>
  <div class="content">
    <div class="diamond">◆ ◆ ◆</div>
    <div class="title">{title}</div>
    <div class="divider"></div>
    <div class="genre">{genre}</div>
    <div class="tone">{tone}</div>
    <div class="stats">
      <div class="stat">
        <div class="stat-n">{wc:,}</div>
        <div class="stat-l">Words</div>
      </div>
      <div class="stat">
        <div class="stat-n">~{max(1,wc//200)}m</div>
        <div class="stat-l">Read Time</div>
      </div>
    </div>
    <div class="footer">NarrativeForge · {story.get('id','')[-4:]}</div>
  </div>
</body>
</html>"""
    return html_cover.encode("utf-8")
