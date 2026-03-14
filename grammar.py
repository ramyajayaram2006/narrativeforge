"""
NarrativeForge — Grammar & Style Checker
Real-time style suggestions without external dependencies.
Checks: passive voice, weak adverbs, overused words, dialogue tags,
        show-don't-tell, sentence length variety, filter words.
"""
import re
import html as _html
import streamlit as st

# ── Rule definitions ──────────────────────────────────────────────────────
_PASSIVE_PATTERNS = re.compile(
    r'\b(was|were|is|are|been|be|being)\s+(written|said|told|shown|given|taken|'
    r'made|done|seen|heard|found|used|known|called|set|left|brought|kept|held|'
    r'sent|put|felt|thought|considered|regarded|placed|moved|turned|driven|'
    r'broken|stolen|lost|caught|built|chosen|begun|grown|thrown)\b',
    re.IGNORECASE)

_WEAK_ADVERBS = [
    "very", "really", "quite", "rather", "somewhat", "fairly", "pretty",
    "extremely", "incredibly", "absolutely", "totally", "completely",
    "utterly", "deeply", "highly", "strongly", "greatly", "terribly",
    "awfully", "dreadfully", "horribly", "wonderfully", "basically",
    "literally", "actually", "honestly", "clearly", "obviously", "suddenly",
    "quickly", "slowly", "quietly", "loudly", "softly", "gently",
]

_FILTER_WORDS = [
    "he saw", "she saw", "he heard", "she heard", "he felt", "she felt",
    "he noticed", "she noticed", "he realized", "she realized",
    "he thought", "she thought", "he wondered", "she wondered",
    "i saw", "i heard", "i felt", "i noticed", "i realized",
    "he could see", "she could see", "he could hear", "she could hear",
    "he could feel", "she could feel",
    "he watched", "she watched", "he looked", "she looked",
]

_TELLING_WORDS = {
    "angry", "sad", "happy", "scared", "afraid", "nervous", "excited",
    "tired", "confused", "surprised", "shocked", "worried", "upset",
    "embarrassed", "ashamed", "proud", "jealous", "lonely", "bored",
    "frustrated", "disappointed", "annoyed", "furious", "miserable",
}

_OVERUSED_TAGS = ["said", "replied", "asked", "answered", "told", "whispered", "shouted", "yelled"]

_SENTENCE_STARTERS = re.compile(r'(?<=[.!?])\s+([A-Z][a-z]+)', re.MULTILINE)


def _get_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 10]


def analyse_style(text):
    """
    Run all style checks. Returns dict of issues by category.
    Each issue: {text, suggestion, type, severity}
    """
    if not text or len(text) < 50:
        return {}

    issues = {
        "passive_voice":  [],
        "weak_adverbs":   [],
        "filter_words":   [],
        "telling":        [],
        "long_sentences": [],
        "repeated_words": [],
    }

    sentences = _get_sentences(text)
    words_lower = text.lower().split()

    # 1. Passive voice
    for sent in sentences:
        m = _PASSIVE_PATTERNS.search(sent)
        if m:
            issues["passive_voice"].append({
                "text": sent[:100],
                "suggestion": "Consider rewriting in active voice for more energy.",
                "severity": "medium"
            })

    # 2. Weak adverbs (show top 5 only)
    found_adverbs = []
    for adv in _WEAK_ADVERBS:
        pattern = r'\b' + adv + r'\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found_adverbs.append((adv, len(matches)))
    found_adverbs.sort(key=lambda x: -x[1])
    for adv, count in found_adverbs[:6]:
        suggestion = f'"{adv}" appears {count}x. Try removing it or replacing with a stronger verb.'
        issues["weak_adverbs"].append({
            "text": f'"{adv}" ×{count}',
            "suggestion": suggestion,
            "severity": "low" if count == 1 else "medium"
        })

    # 3. Filter words (POV distance)
    text_lower = text.lower()
    for fw in _FILTER_WORDS:
        if fw in text_lower:
            issues["filter_words"].append({
                "text": f'"{fw.title()}"',
                "suggestion": f'"{fw}" creates POV distance. Show the action directly instead.',
                "severity": "medium"
            })
    # dedupe
    seen = set()
    issues["filter_words"] = [x for x in issues["filter_words"]
                               if x["text"] not in seen and not seen.add(x["text"])]

    # 4. Telling emotions
    for word in _TELLING_WORDS:
        pattern = r'\b(was|felt|felt|seemed|looked|appeared|became)\s+' + word + r'\b'
        if re.search(pattern, text_lower):
            issues["telling"].append({
                "text": f'Telling emotion: "{word}"',
                "suggestion": f'Instead of stating someone "was {word}", show physical reactions.',
                "severity": "medium"
            })

    # 5. Long sentences (>50 words)
    for sent in sentences:
        wc = len(sent.split())
        if wc > 50:
            issues["long_sentences"].append({
                "text": sent[:80] + "…",
                "suggestion": f"Sentence is {wc} words long. Consider splitting for clarity.",
                "severity": "low"
            })

    # 6. Repeated words (top 5 non-stopwords appearing >3x)
    stop = {"the","a","an","and","or","but","in","on","at","to","for","of","with",
            "he","she","it","they","was","were","had","have","has","is","are","be",
            "i","you","we","this","that","his","her","their","its","my","your",
            "not","all","as","from","by","into","out","up","about","so","if",
            "do","did","can","will","would","could","should","may","might","then",
            "than","when","there","what","just","said","one","more","been","no",
            "back","over","like","down","after","before","know","get","our","him"}
    word_counts = {}
    for w in re.findall(r'\b[a-z]{4,}\b', text_lower):
        if w not in stop:
            word_counts[w] = word_counts.get(w, 0) + 1
    repeat = sorted([(w, c) for w, c in word_counts.items() if c >= 4], key=lambda x: -x[1])[:5]
    for word, count in repeat:
        issues["repeated_words"].append({
            "text": f'"{word}" ×{count}',
            "suggestion": f'"{word}" appears {count} times. Vary with synonyms to avoid repetition.',
            "severity": "low" if count < 6 else "medium"
        })

    # Remove empty categories
    return {k: v for k, v in issues.items() if v}


def show_grammar_checker(story, ctx=""):
    """Render the grammar/style checker panel in the Intelligence tab."""
    prose = " ".join(
        m["content"] for m in story.get("messages", [])
        if m.get("role") == "assistant" and not m["content"].startswith("◆")
    )

    if not prose or len(prose.split()) < 30:
        st.markdown(
            "<div style='color:#6B7080;font-size:0.82rem;text-align:center;padding:24px;'>"
            "Write at least 30 words to enable style checking.</div>",
            unsafe_allow_html=True)
        return

    _CATEGORY_META = {
        "passive_voice":  {"label": "⚡ Passive Voice",      "color": "#f87171"},
        "weak_adverbs":   {"label": "💊 Weak Adverbs",        "color": "#fbbf24"},
        "filter_words":   {"label": "🔭 Filter Words",         "color": "#fb923c"},
        "telling":        {"label": "🎭 Telling (not Showing)","color": "#a78bfa"},
        "long_sentences": {"label": "📏 Long Sentences",       "color": "#60a5fa"},
        "repeated_words": {"label": "🔁 Repeated Words",       "color": "#34d399"},
    }

    results_key = f"grammar_results_{story['id']}"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(
            "<div style='font-size:0.78rem;color:#6B7080;margin-bottom:4px;'>"
            f"Analysing {len(prose.split()):,} words…</div>",
            unsafe_allow_html=True)
    with col2:
        if st.button("🔍 Analyse", key=f"grammar_run_{story['id']}_{ctx}", use_container_width=True):
            with st.spinner("Scanning…"):
                st.session_state[results_key] = analyse_style(prose)

    results = st.session_state.get(results_key)
    if results is None:
        return

    if not results:
        st.markdown(
            "<div style='background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.3);"
            "border-radius:8px;padding:14px;text-align:center;'>"
            "<div style='font-size:1.2rem;'>✨</div>"
            "<div style='color:#34d399;font-weight:700;font-size:0.9rem;'>No major style issues found!</div>"
            "<div style='color:#6B7080;font-size:0.75rem;margin-top:4px;'>Your prose looks clean.</div>"
            "</div>",
            unsafe_allow_html=True)
        return

    total_issues = sum(len(v) for v in results.values())
    st.markdown(
        f"<div style='font-size:0.78rem;color:#fbbf24;margin-bottom:10px;'>"
        f"⚠️ Found {total_issues} style suggestion{'s' if total_issues != 1 else ''} across {len(results)} categories</div>",
        unsafe_allow_html=True)

    for cat, issues in results.items():
        meta = _CATEGORY_META.get(cat, {"label": cat, "color": "#4D6BFE"})
        with st.expander(f"{meta['label']} ({len(issues)})", expanded=len(issues) <= 3):
            for issue in issues:
                st.markdown(
                    f"<div style='border-left:3px solid {meta['color']};padding:8px 12px;"
                    f"margin-bottom:8px;background:var(--primary-dim);border-radius:0 6px 6px 0;'>"
                    f"<div style='font-size:0.80rem;color:var(--text-primary);font-weight:600;margin-bottom:3px;'>"
                    f"{_html.escape(issue['text'])}</div>"
                    f"<div style='font-size:0.74rem;color:#6B7080;'>{_html.escape(issue['suggestion'])}</div>"
                    f"</div>",
                    unsafe_allow_html=True)

    if st.button("🗑 Clear", key=f"grammar_clear_{story['id']}_{ctx}"):
        st.session_state.pop(results_key, None)
        st.rerun()
