"""
mobile_styles.py — NarrativeForge Mobile CSS

Add this to styles.py by calling get_mobile_css() and injecting it
inside dashboard_style() and workspace_style():

    st.markdown(get_mobile_css(), unsafe_allow_html=True)

Or paste the CSS string directly into your existing <style> blocks.
"""


def get_mobile_css() -> str:
    return """<style>
/* ════════════════════════════════════════════════════════
   MOBILE RESPONSIVE — NarrativeForge
   Breakpoints: 768px (tablet), 480px (phone)
   ════════════════════════════════════════════════════════ */

/* ── Touch targets — minimum 44px per Apple HIG / WCAG ── */
@media (max-width: 768px) {
    .stButton > button,
    .stDownloadButton > button {
        min-height: 44px !important;
        font-size: 0.88rem !important;
        padding: 10px 14px !important;
        border-radius: 8px !important;
    }
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        min-height: 44px !important;
        font-size: 0.92rem !important;
    }
    /* Checkbox touch target */
    .stCheckbox > label {
        min-height: 36px !important;
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
    }
}

/* ── Sidebar auto-collapse on mobile ── */
@media (max-width: 768px) {
    /* Sidebar starts hidden — user taps hamburger to open */
    section[data-testid="stSidebar"] {
        width: 85vw !important;
        min-width: 260px !important;
        max-width: 320px !important;
        transform: translateX(-100%);
        transition: transform 0.25s ease !important;
        z-index: 999 !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        height: 100vh !important;
        box-shadow: 4px 0 24px rgba(0,0,0,0.5) !important;
    }
    section[data-testid="stSidebar"][aria-expanded="true"] {
        transform: translateX(0) !important;
    }
    /* Main content full-width when sidebar hidden */
    .main .block-container {
        padding-left: 12px !important;
        padding-right: 12px !important;
        max-width: 100vw !important;
    }
}

/* ── Font scaling ── */
@media (max-width: 768px) {
    /* Story cards */
    .story-card h3 {
        font-size: 1.0rem !important;
        line-height: 1.3 !important;
    }
    .story-badge {
        font-size: 0.62rem !important;
        padding: 2px 6px !important;
    }
    /* Dashboard header */
    .dash-header {
        font-size: 1.5rem !important;
    }
    .dash-sub {
        font-size: 0.82rem !important;
    }
    /* Stat cards */
    .stat-num {
        font-size: 1.3rem !important;
    }
    .stat-label {
        font-size: 0.60rem !important;
    }
    /* Workspace tabs */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.72rem !important;
        padding: 6px 8px !important;
    }
}

@media (max-width: 480px) {
    /* Phone: tighter spacing */
    .main .block-container {
        padding-left: 8px !important;
        padding-right: 8px !important;
        padding-top: 8px !important;
    }
    .stButton > button,
    .stDownloadButton > button {
        font-size: 0.80rem !important;
        padding: 8px 10px !important;
    }
    /* Collapse multi-column layouts to single column */
    [data-testid="column"] {
        min-width: 100% !important;
    }
    /* Story card meta badges — wrap nicely */
    .story-card > div {
        flex-wrap: wrap !important;
        gap: 4px !important;
    }
    /* Word count ring — scale down */
    .wc-number {
        font-size: 1.4rem !important;
    }
    /* Tab labels truncate gracefully */
    .stTabs [data-baseweb="tab"] span {
        max-width: 60px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
}

/* ── Textarea height on mobile ── */
@media (max-width: 768px) {
    .stTextArea textarea {
        min-height: 80px !important;
    }
}

/* ── Expander headers — larger tap zone ── */
@media (max-width: 768px) {
    .streamlit-expanderHeader {
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
        font-size: 0.86rem !important;
    }
}

/* ── Horizontal scroll for wide tables on small screens ── */
@media (max-width: 768px) {
    table {
        display: block !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
}

/* ── Download buttons — full width on phone ── */
@media (max-width: 480px) {
    .stDownloadButton {
        width: 100% !important;
    }
    .stDownloadButton > button {
        width: 100% !important;
    }
}
</style>"""


# ── Standalone injection helper ───────────────────────────────────────────────
def inject_mobile_styles():
    """Call this from any page that needs mobile styles."""
    import streamlit as st
    st.markdown(get_mobile_css(), unsafe_allow_html=True)
