"""
NarrativeForge — Version Timeline
Visual snapshot history with word-count progression chart,
hover previews, and side-by-side diff comparison.
"""
import html as _html
import re
import streamlit as st
from database import load_snapshots, restore_snapshot, delete_snapshot


# ── Diff Engine ────────────────────────────────────────────────────────────
def _word_list(text):
    return re.findall(r'\S+', text)

def _simple_diff(text_a, text_b, context=6):
    """
    Return HTML showing additions (green) and removals (red).
    Works at word level, shows context words around changes.
    """
    words_a = _word_list(text_a)
    words_b = _word_list(text_b)

    # LCS-based diff (simple O(n²) for short texts, chunked for long)
    MAX = 800
    if len(words_a) > MAX:
        words_a = words_a[-MAX:]
    if len(words_b) > MAX:
        words_b = words_b[-MAX:]

    # Build LCS table
    m, n = len(words_a), len(words_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if words_a[i-1].lower() == words_b[j-1].lower():
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    # Traceback
    ops = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and words_a[i-1].lower() == words_b[j-1].lower():
            ops.append(("eq", words_b[j-1]))
            i -= 1; j -= 1
        elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
            ops.append(("add", words_b[j-1]))
            j -= 1
        else:
            ops.append(("del", words_a[i-1]))
            i -= 1
    ops.reverse()

    # Render HTML — only show changed regions with context
    parts = []
    changed_zones = [k for k, (t, _) in enumerate(ops) if t != "eq"]
    if not changed_zones:
        return "<span style='color:#34d399;'>✓ No differences found</span>"

    shown = set()
    for z in changed_zones:
        for k in range(max(0, z - context), min(len(ops), z + context + 1)):
            shown.add(k)

    prev_shown = False
    for k, (typ, word) in enumerate(ops):
        if k not in shown:
            if prev_shown:
                parts.append("<span style='color:#6B7080;'> … </span>")
            prev_shown = False
            continue
        prev_shown = True
        esc = _html.escape(word)
        if typ == "add":
            parts.append(f"<mark style='background:rgba(52,211,153,0.25);color:#34d399;"
                         f"border-radius:3px;padding:0 2px;'>{esc}</mark> ")
        elif typ == "del":
            parts.append(f"<del style='color:#f87171;opacity:0.7;'>{esc}</del> ")
        else:
            parts.append(f"{esc} ")

    return "".join(parts)


def _prose_from_messages(messages):
    return " ".join(
        m["content"] for m in messages
        if m.get("role") == "assistant"
        and not m["content"].startswith("◆"))

def _wc(messages):
    return len(_prose_from_messages(messages).split())


# ── Main Panel ─────────────────────────────────────────────────────────────
def show_version_timeline(story, username):
    """Full version timeline with progression chart and diff compare."""
    snaps = load_snapshots(username, story["id"])

    if not snaps:
        st.markdown(
            "<div style='text-align:center;color:#6B7080;padding:40px;font-size:0.84rem;'>"
            "No snapshots yet.<br>Go to the <strong>Snaps</strong> tab and save one first.</div>",
            unsafe_allow_html=True)
        return

    # Add current state as a virtual snapshot
    current = {
        "id": None,
        "name": "📍 Current (unsaved)",
        "word_count": _wc(story.get("messages", [])),
        "created_at": "now",
        "messages": story.get("messages", []),
    }
    all_versions = snaps + [current]

    # ── Word count progression bar chart ──────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>"
        "📈 Word Count Progression</div>",
        unsafe_allow_html=True)

    max_wc = max((s.get("word_count", 0) for s in all_versions), default=1) or 1
    for snap in all_versions:
        wc   = snap.get("word_count", 0)
        pct  = int(wc / max_wc * 100)
        is_current = snap["id"] is None
        bar_color  = "#4D6BFE" if not is_current else "#34d399"
        name_short = snap["name"][:28]
        ts = snap.get("created_at", "")
        if ts and ts != "now" and len(str(ts)) > 10:
            ts = str(ts)[:16]
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
            f"<div style='width:110px;font-size:0.70rem;color:#C5C8D4;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
            f"{_html.escape(name_short)}</div>"
            f"<div style='flex:1;background:var(--primary-dim);border-radius:3px;height:10px;'>"
            f"<div style='width:{pct}%;background:{bar_color};height:10px;border-radius:3px;'></div></div>"
            f"<div style='width:42px;font-size:0.68rem;color:#6B7080;text-align:right;'>{wc:,}</div>"
            f"</div>",
            unsafe_allow_html=True)

    st.markdown("---")

    # ── Snapshot cards ────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>"
        "🗂 All Versions</div>",
        unsafe_allow_html=True)

    compare_key = f"vt_compare_{story['id']}"
    selected    = st.session_state.get(compare_key, [])

    for snap in reversed(all_versions):
        is_current = snap["id"] is None
        sid        = snap.get("id", "current")
        wc         = snap.get("word_count", 0)
        ts         = str(snap.get("created_at", ""))[:16] if snap.get("created_at") != "now" else "Current session"
        checked    = sid in selected

        border = "rgba(52,211,153,0.4)" if is_current else (
            "rgba(77,107,254,0.4)" if checked else "rgba(77,107,254,0.12)")
        bg     = "rgba(52,211,153,0.05)" if is_current else (
            "rgba(77,107,254,0.07)" if checked else "transparent")

        st.markdown(
            f"<div style='border:1px solid {border};background:{bg};"
            f"border-radius:8px;padding:10px 12px;margin-bottom:6px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div><div style='font-size:0.82rem;font-weight:600;color:var(--text-primary);'>"
            f"{'📍 ' if is_current else '📸 '}{_html.escape(snap['name'])}</div>"
            f"<div style='font-size:0.68rem;color:#6B7080;margin-top:2px;'>"
            f"{ts} · {wc:,} words</div></div>"
            f"<div style='font-size:0.72rem;color:#4D6BFE;font-weight:600;'>"
            f"{'✓ Selected' if checked else ''}</div></div></div>",
            unsafe_allow_html=True)

        if not is_current:
            btn_cols = st.columns([2, 2, 2])
            with btn_cols[0]:
                sel_label = "☑ Deselect" if checked else "☐ Compare"
                if st.button(sel_label, key=f"vt_sel_{sid}", use_container_width=True):
                    cur = list(selected)
                    if sid in cur:
                        cur.remove(sid)
                    elif len(cur) < 2:
                        cur.append(sid)
                    else:
                        cur = [cur[1], sid]  # replace oldest selection
                    st.session_state[compare_key] = cur
                    st.rerun()
            with btn_cols[1]:
                if st.button("↩️ Restore", key=f"vt_restore_{sid}", use_container_width=True):
                    st.session_state[f"vt_confirm_restore_{sid}"] = True
                    st.rerun()
            with btn_cols[2]:
                if st.button("🗑 Delete", key=f"vt_del_{sid}", use_container_width=True):
                    st.session_state[f"vt_confirm_del_{sid}"] = True
                    st.rerun()

            # Confirm restore
            if st.session_state.get(f"vt_confirm_restore_{sid}"):
                st.warning(f"Restore to **{snap['name']}**? This replaces current story.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Yes, restore", key=f"vt_do_restore_{sid}",
                                 use_container_width=True):
                        restore_snapshot(sid, username)
                        st.session_state.pop(f"vt_confirm_restore_{sid}", None)
                        st.session_state.stories = None
                        st.rerun()
                with c2:
                    if st.button("✖ Cancel", key=f"vt_cancel_restore_{sid}",
                                 use_container_width=True):
                        st.session_state.pop(f"vt_confirm_restore_{sid}", None)
                        st.rerun()

            # Confirm delete
            if st.session_state.get(f"vt_confirm_del_{sid}"):
                st.error(f"Delete **{snap['name']}** permanently?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑 Delete", key=f"vt_do_del_{sid}",
                                 use_container_width=True):
                        delete_snapshot(sid, username)
                        st.session_state.pop(f"vt_confirm_del_{sid}", None)
                        st.rerun()
                with c2:
                    if st.button("✖ Cancel", key=f"vt_cancel_del_{sid}",
                                 use_container_width=True):
                        st.session_state.pop(f"vt_confirm_del_{sid}", None)
                        st.rerun()

    # ── Side-by-side diff ─────────────────────────────────────────────────
    if len(selected) == 2:
        st.markdown("---")
        st.markdown(
            "<div style='font-size:0.72rem;color:#6B7080;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>"
            "🔍 Version Comparison</div>",
            unsafe_allow_html=True)

        snap_a = next((s for s in snaps if s["id"] == selected[0]), None)
        snap_b = next((s for s in snaps if s["id"] == selected[1]), None)

        if snap_a and snap_b:
            # Ensure A is older
            if snap_a.get("id", 0) > snap_b.get("id", 0):
                snap_a, snap_b = snap_b, snap_a

            prose_a = _prose_from_messages(snap_a.get("messages", []))
            prose_b = _prose_from_messages(snap_b.get("messages", []))
            wc_a    = snap_a.get("word_count", 0)
            wc_b    = snap_b.get("word_count", 0)
            diff    = wc_b - wc_a
            sign    = "+" if diff >= 0 else ""

            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(
                    f"<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
                    f"margin-bottom:6px;'>📸 {_html.escape(snap_a['name'])}</div>"
                    f"<div style='font-size:0.68rem;color:#6B7080;margin-bottom:8px;'>"
                    f"{wc_a:,} words</div>",
                    unsafe_allow_html=True)
                st.text_area("", value=prose_a[:1200] + ("…" if len(prose_a) > 1200 else ""),
                             height=200, key=f"diff_a_{selected[0]}", disabled=True,
                             label_visibility="collapsed")
            with col_r:
                st.markdown(
                    f"<div style='font-size:0.78rem;font-weight:700;color:#A8BCFF;"
                    f"margin-bottom:6px;'>📸 {_html.escape(snap_b['name'])}</div>"
                    f"<div style='font-size:0.68rem;color:#6B7080;margin-bottom:8px;'>"
                    f"{wc_b:,} words  "
                    f"<span style='color:{'#34d399' if diff >= 0 else '#f87171'};font-weight:700;'>"
                    f"({sign}{diff:,})</span></div>",
                    unsafe_allow_html=True)
                st.text_area("", value=prose_b[:1200] + ("…" if len(prose_b) > 1200 else ""),
                             height=200, key=f"diff_b_{selected[1]}", disabled=True,
                             label_visibility="collapsed")

            # Word-level diff
            st.markdown(
                "<div style='font-size:0.72rem;color:#6B7080;margin:10px 0 6px;'>"
                "🔤 Word-level changes — "
                "<span style='color:#34d399;'>■ added</span>  "
                "<span style='color:#f87171;'>■ removed</span></div>",
                unsafe_allow_html=True)
            with st.spinner("Computing diff…"):
                diff_html = _simple_diff(prose_a, prose_b)
            st.markdown(
                f"<div style='background:var(--primary-dim);border:1px solid var(--primary-border);"
                f"border-radius:8px;padding:14px;font-size:0.80rem;line-height:1.8;"
                f"color:var(--text-primary);max-height:300px;overflow-y:auto;'>"
                f"{diff_html}</div>",
                unsafe_allow_html=True)

            if st.button("✖ Clear selection", key="vt_clear_sel"):
                st.session_state[compare_key] = []
                st.rerun()
    elif len(selected) == 1:
        st.info("Select one more snapshot to compare.")
