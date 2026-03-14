import streamlit as st

# ══════════════════════════════════════════════════════════════
#  NarrativeForge — Design System v3
#  DeepSeek-inspired. Dual light/dark theme. Inter throughout.
# ══════════════════════════════════════════════════════════════

_FONTS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
"""

# ── Instant transitions — kills ALL Streamlit fade/blur on tab/page change ─
_NO_FADE_CSS = """
/* ── 1. Kill Streamlit's stale-data blur overlay ── */
/* [data-stale] is the attribute Streamlit sets while rerunning */
[data-stale],
[data-stale] * {
    opacity: 1 !important;
    filter: none !important;
    animation: none !important;
    transition: none !important;
}

/* ── 2. Kill the grey dimming overlay on rerun ── */
.stApp::before,
.stApp::after,
.stStatusWidget,
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
.stApp [data-testid="stToolbar"],
div[class*="StatusWidget"],
div[class*="stSpinner"] > div {
    display: none !important;
    opacity: 0 !important;
}

/* ── 3. Kill ALL animation and transition on everything ── */
.stApp *,
.stApp [data-testid="stAppViewContainer"],
.stApp [data-testid="stAppViewContainer"] *,
.stApp [data-testid="stSidebar"],
.stApp [data-testid="stSidebar"] *,
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div * {
    animation: none !important;
    transition: none !important;
    opacity: 1 !important;
    filter: none !important;
}

/* ── 4. Instant tab panel switching ── */
.stTabs [data-baseweb="tab-panel"],
.stTabs [data-baseweb="tab-panel"] * {
    animation: none !important;
    transition: none !important;
}

/* ── 5. Kill element-level fade-in that Streamlit injects ── */
.element-container,
.stMarkdown,
.stButton,
.stSelectbox,
.stTextInput,
.stTextArea,
.stForm,
.stExpander {
    animation: none !important;
    transition: none !important;
}

/* ── 6. Kill iframe-level transitions (components.html) ── */
iframe {
    animation: none !important;
    transition: none !important;
}
"""

# ── DARK theme variables ───────────────────────────────────────
_DARK_VARS = """
:root {
  --primary:        #4D6BFE;
  --primary-dark:   #3553E8;
  --primary-light:  #7B96FF;
  --primary-glow:   rgba(77,107,254,0.20);
  --primary-border: rgba(77,107,254,0.25);
  --primary-dim:    rgba(77,107,254,0.08);
  --accent:         #A8BCFF;
  --accent-dim:     rgba(168,188,255,0.55);
  --bg-main:        #0D0E14;
  --bg-card:        #161820;
  --bg-surface:     #111318;
  --bg-input:       #1A1C28;
  --text-primary:   #F0F0F5;
  --text-accent:    #C8D4FF;
  --text-muted:     #8B8FA8;
  --text-faint:     #4A4D60;
  --border-subtle:  rgba(255,255,255,0.06);
  --danger:         #FF6B6B;
  --danger-dim:     rgba(255,107,107,0.12);
  --success:        #4ECDC4;
  --warning:        #FFD93D;
  --radius-sm:      8px;
  --radius-md:      12px;
  --radius-lg:      18px;
  --radius-pill:    999px;
}
"""

# ── LIGHT theme variables ──────────────────────────────────────
_LIGHT_VARS = """
:root {
  --primary:        #3553E8;
  --primary-dark:   #2640CC;
  --primary-light:  #4D6BFE;
  --primary-glow:   rgba(53,83,232,0.14);
  --primary-border: rgba(53,83,232,0.22);
  --primary-dim:    rgba(53,83,232,0.07);
  --accent:         #2640CC;
  --accent-dim:     rgba(38,64,204,0.55);
  --bg-main:        #F5F6FA;
  --bg-card:        #FFFFFF;
  --bg-surface:     #EDEEF5;
  --bg-input:       #FFFFFF;
  --text-primary:   #0F1117;
  --text-accent:    #1A2370;
  --text-muted:     #6B7080;
  --text-faint:     #B0B4C8;
  --border-subtle:  rgba(0,0,0,0.07);
  --danger:         #E53935;
  --danger-dim:     rgba(229,57,53,0.08);
  --success:        #00897B;
  --warning:        #F9A825;
  --radius-sm:      8px;
  --radius-md:      12px;
  --radius-lg:      18px;
  --radius-pill:    999px;
}
"""

_RESET = """
html, body, [data-testid="stApp"] {
  background-color: var(--bg-main) !important;
  color: var(--text-primary) !important;
  font-family: 'Inter', system-ui, sans-serif !important;
}
[data-testid="stSidebar"] {
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--primary-border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

button[kind="primary"] {
  background: linear-gradient(135deg, var(--primary-dark), var(--primary)) !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
  border: none !important;
  font-family: 'Inter', sans-serif !important;
  border-radius: var(--radius-sm) !important;
}
button[kind="secondary"] {
  background: var(--bg-card) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--primary-border) !important;
  font-family: 'Inter', sans-serif !important;
  border-radius: var(--radius-sm) !important;
}
button[kind="primary"]:hover {
  background: linear-gradient(135deg, var(--primary), var(--primary-light)) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px var(--primary-glow) !important;
}
button[kind="secondary"]:hover {
  border-color: var(--primary) !important;
  color: var(--primary) !important;
}

.stTextInput input, .stTextArea textarea, .stSelectbox select {
  background: var(--bg-input) !important;
  border: 1px solid var(--primary-border) !important;
  color: var(--text-primary) !important;
  font-family: 'Inter', sans-serif !important;
  border-radius: var(--radius-sm) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--primary-glow) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label {
  color: var(--text-muted) !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
  color: var(--text-muted) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.72rem !important;
  font-weight: 500 !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--primary) !important;
  border-bottom-color: var(--primary) !important;
}

[data-testid="stMarkdownContainer"] { color: var(--text-primary) !important; }
.stAlert { border-radius: var(--radius-md) !important; }
hr { border-color: var(--border-subtle) !important; }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-main); }
::-webkit-scrollbar-thumb { background: var(--primary-border); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary); }

/* Progress bars */
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, var(--primary-dark), var(--primary)) !important;
  border-radius: var(--radius-pill) !important;
}
"""

_AUTH_CSS = """
.auth-wrap {
  max-width: 420px;
  margin: 40px auto;
  padding: 32px 36px;
  background: var(--bg-card);
  border: 1px solid var(--primary-border);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px var(--primary-glow);
}
.auth-logo {
  font-family: 'Inter', sans-serif;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 4px;
  letter-spacing: -0.03em;
}
.auth-logo .brand-blue { color: var(--primary); }
.auth-sub {
  font-family: 'Inter', sans-serif;
  font-size: 0.80rem;
  color: var(--text-muted);
  text-align: center;
  letter-spacing: 0.03em;
  margin-bottom: 24px;
}
.auth-footer {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: var(--text-faint);
  text-align: center;
  margin-top: 24px;
  letter-spacing: 0.06em;
}
"""

_DASH_CSS = """
.dash-header {
  font-family: 'Inter', sans-serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  margin-bottom: 4px;
}
.dash-sub {
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-bottom: 20px;
}
.story-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-md);
  padding: 16px 20px 10px;
  margin-bottom: 6px;
  transition: none;
  box-shadow: 0 1px 4px var(--primary-glow);
}
.story-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px var(--primary-glow);
  border-color: var(--primary-border);
}
.story-card h3 {
  font-family: 'Inter', sans-serif;
  font-size: 1.0rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.01em;
}
.story-badge {
  display: inline-block;
  background: var(--primary-dim);
  border: 1px solid var(--primary-border);
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.60rem;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  margin: 2px 2px 2px 0;
  letter-spacing: 0.03em;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--primary-border);
  border-top: 3px solid var(--primary);
  border-radius: var(--radius-md);
  padding: 16px 14px;
  text-align: center;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px var(--primary-glow);
}
.stat-num {
  font-size: 1.7rem;
  font-weight: 700;
  color: var(--primary);
  font-family: 'Inter', sans-serif;
  line-height: 1.1;
  letter-spacing: -0.03em;
}
.stat-label {
  font-size: 0.60rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-top: 4px;
  font-family: 'JetBrains Mono', monospace;
}
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: var(--bg-card);
  border: 1px dashed var(--primary-border);
  border-radius: var(--radius-lg);
  margin-top: 20px;
}
.template-card {
  background: var(--bg-card);
  border: 1px solid var(--primary-border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  cursor: pointer;
  transition: none;
  margin-bottom: 8px;
}
.template-card:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 12px var(--primary-glow);
}
.template-title { font-size:0.88rem; font-weight:600; color:var(--text-primary); margin-bottom:4px; }
.template-desc  { font-size:0.75rem; color:var(--text-muted); line-height:1.4; }
"""

_WS_CSS = """
.bubble-user {
  background: var(--primary-dim);
  border: 1px solid var(--primary-border);
  border-radius: 14px 14px 4px 14px;
  padding: 12px 16px;
  margin: 8px 0;
  max-width: 85%;
  margin-left: auto;
  animation: none;
}
.bubble-ai {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--primary);
  border-radius: 4px 14px 14px 14px;
  padding: 14px 18px;
  margin: 8px 0;
  max-width: 92%;
  animation: none;
  box-shadow: 0 2px 8px var(--primary-glow);
}
.bubble-user .lbl { font-size:0.60rem; color:var(--primary); font-family:'JetBrains Mono',monospace; font-weight:600; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px; }
.bubble-ai  .lbl  { font-size:0.60rem; color:var(--text-muted); font-family:'JetBrains Mono',monospace; font-weight:600; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px; }
.bubble-user .txt { color:var(--text-primary); font-family:'Inter',sans-serif; line-height:1.7; font-size:0.95rem; }
.bubble-ai  .txt  { color:var(--text-accent); font-family:'Inter',sans-serif; line-height:1.78; font-size:0.96rem; }

@keyframes slideInLeft  { from { opacity:1; transform:none; } to { opacity:1; transform:none; } }
@keyframes slideInRight { from { opacity:1; transform:none; } to { opacity:1; transform:none; } }

.scene-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px var(--primary-glow);
}
.scene-title { font-size:0.85rem; font-weight:600; color:var(--text-primary); font-family:'Inter',sans-serif; }
.scene-meta  { font-size:0.70rem; color:var(--text-muted); margin-top:3px; font-family:'JetBrains Mono',monospace; }

.char-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px var(--primary-glow);
}
.issue-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  margin-bottom: 6px;
}
.ws-badge {
  display: inline-block;
  background: var(--primary-dim);
  border: 1px solid var(--primary-border);
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.61rem;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  margin: 0 3px;
  letter-spacing: 0.04em;
}
.ws-badge-blue { border-color: var(--primary-border); color: var(--primary); }
.mode-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.67rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  margin: 12px 0 8px;
}
.insight-card {
  background: var(--bg-card);
  border: 1px solid var(--primary-border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: 0 2px 8px var(--primary-glow);
}
.insight-title {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
  font-family: 'JetBrains Mono', monospace;
}
.insight-body {
  font-size: 0.88rem;
  color: var(--text-primary);
  line-height: 1.6;
}
"""

_CONFIRM_CSS = """
.confirm-box {
  background: var(--danger-dim);
  border: 1px solid rgba(229,57,53,0.28);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  margin: 6px 0;
}
.confirm-box .msg {
  font-size: 0.82rem;
  color: var(--danger);
  font-family: 'Inter', sans-serif;
  margin-bottom: 8px;
}
"""

def _vars_for_theme():
    return _LIGHT_VARS if st.session_state.get("light_theme") else _DARK_VARS

def _inject(css: str):
    vars_css = _vars_for_theme()
    st.markdown(f"<style>{_FONTS}{vars_css}{_RESET}{css}</style>", unsafe_allow_html=True)

def auth_page_style():   _inject(_AUTH_CSS)
def dashboard_style():   _inject(_NO_FADE_CSS + _DASH_CSS)

# ── Accessibility — High Contrast + Reduced Motion + Dyslexic Font ──────
_ACCESSIBILITY_CSS = """
/* High contrast mode */
[data-nf-theme="high-contrast"] {
  --primary:       #0066FF;
  --bg-main:       #000000;
  --bg-card:       #111111;
  --text-primary:  #FFFFFF;
  --text-muted:    #CCCCCC;
  --primary-glow:  rgba(0,102,255,0.3);
  --primary-border:rgba(0,102,255,0.5);
}
/* Dyslexic font mode */
[data-nf-font="dyslexic"] * {
  font-family: 'OpenDyslexic', 'Comic Sans MS', 'Trebuchet MS', sans-serif !important;
  letter-spacing: 0.05em !important;
  word-spacing: 0.15em !important;
  line-height: 1.8 !important;
}
/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
}
/* Focus indicators for keyboard navigation */
:focus-visible {
  outline: 2px solid var(--primary) !important;
  outline-offset: 2px !important;
}
/* Screen reader only utility */
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
/* Skip to content link */
.skip-link {
  position: absolute;
  top: -40px; left: 0;
  background: var(--primary);
  color: #fff;
  padding: 8px 16px;
  z-index: 10000;
  border-radius: 0 0 8px 0;
  text-decoration: none;
  font-weight: 700;
}
.skip-link:focus { top: 0; }
"""



_MOBILE_CSS = """
/* ═══════════════════════════════════════════════════════════════
   MOBILE & RESPONSIVE CSS  — NarrativeForge
   Targets: phones ≤640px, tablets 641–1024px
   ═══════════════════════════════════════════════════════════════ */

/* ── Base mobile viewport fix ─────────────────────────────────── */
@media (max-width: 640px) {

  /* Sidebar: full-width overlay on mobile */
  [data-testid="stSidebar"] {
    min-width: 100vw !important;
    max-width: 100vw !important;
  }
  [data-testid="stSidebar"][aria-expanded="false"] {
    margin-left: -100vw !important;
  }

  /* Main content: full width, smaller padding */
  .main .block-container {
    padding: 0.75rem 0.75rem 4rem !important;
    max-width: 100% !important;
  }

  /* Chat input: taller tap target */
  [data-testid="stChatInput"] textarea {
    font-size: 16px !important;   /* prevents iOS zoom on focus */
    min-height: 52px !important;
  }

  /* Buttons: minimum 44px tap target (WCAG 2.5.5) */
  button[kind="secondary"], button[kind="primary"],
  .stButton > button {
    min-height: 44px !important;
    font-size: 0.88rem !important;
    padding: 10px 14px !important;
    touch-action: manipulation !important;
  }

  /* Tabs: scrollable horizontally, no wrap */
  [data-testid="stTabs"] [role="tablist"] {
    overflow-x: auto !important;
    overflow-y: hidden !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    gap: 2px !important;
  }
  [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {
    display: none !important;
  }
  [data-testid="stTabs"] [role="tab"] {
    flex-shrink: 0 !important;
    font-size: 0.72rem !important;
    padding: 6px 10px !important;
    white-space: nowrap !important;
  }

  /* Columns: stack vertically on mobile */
  [data-testid="column"] {
    min-width: 100% !important;
    flex: 0 0 100% !important;
  }

  /* Metric cards: 2-up grid on mobile */
  div[data-testid="metric-container"] {
    min-width: calc(50% - 8px) !important;
  }

  /* Text inputs: full width, iOS-safe font size */
  input[type="text"], input[type="password"],
  textarea, select {
    font-size: 16px !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }

  /* Selectbox: larger tap area */
  [data-testid="stSelectbox"] > div > div {
    min-height: 44px !important;
  }

  /* Code blocks: horizontal scroll */
  pre, code {
    overflow-x: auto !important;
    white-space: pre !important;
    -webkit-overflow-scrolling: touch !important;
  }

  /* Cards: full width, reduced padding */
  .dc-panel, .beta-prose {
    padding: 12px !important;
  }

  /* Hide non-essential UI on smallest screens */
  .hide-mobile {
    display: none !important;
  }

  /* Progress ring: smaller on mobile */
  svg[viewBox="0 0 100 100"] {
    width: 72px !important;
    height: 72px !important;
  }

  /* Relationship map: full width */
  iframe {
    width: 100% !important;
    height: 320px !important;
  }

  /* Floating action: larger tap area */
  .fab-container button {
    width: 52px !important;
    height: 52px !important;
    font-size: 1.1rem !important;
  }
}

/* ── Tablet layout (641px – 1024px) ───────────────────────────── */
@media (min-width: 641px) and (max-width: 1024px) {

  .main .block-container {
    padding: 1rem 1.5rem 4rem !important;
  }

  /* Sidebar: narrower on tablet */
  [data-testid="stSidebar"] {
    min-width: 280px !important;
    max-width: 320px !important;
  }

  /* Tabs: compact */
  [data-testid="stTabs"] [role="tab"] {
    font-size: 0.75rem !important;
    padding: 6px 10px !important;
  }

  /* 2-col becomes 1-col for narrow tablets */
  @media (max-width: 768px) {
    [data-testid="column"] {
      min-width: 100% !important;
    }
  }
}

/* ── Touch-friendly improvements (any touch device) ───────────── */
@media (hover: none) and (pointer: coarse) {

  /* Larger touch targets everywhere */
  button, [role="button"], a, select,
  input[type="checkbox"], input[type="radio"] {
    min-height: 44px !important;
    min-width: 44px !important;
  }

  input[type="checkbox"], input[type="radio"] {
    width: 22px !important;
    height: 22px !important;
  }

  /* Remove hover states that don't work on touch */
  button:hover { opacity: 1 !important; }

  /* Increase line spacing for touch reading */
  p, li, td { line-height: 1.75 !important; }

  /* Scrollable containers: smooth momentum */
  .dc-panel, [data-testid="stTabs"] [role="tabpanel"],
  .main .block-container {
    -webkit-overflow-scrolling: touch !important;
    overscroll-behavior: contain !important;
  }

  /* Pull-to-refresh prevention on body */
  body { overscroll-behavior-y: contain !important; }
}

/* ── iOS-specific fixes ────────────────────────────────────────── */
@supports (-webkit-touch-callout: none) {

  /* Fix iOS rubber-band scroll */
  body {
    position: fixed !important;
    width: 100% !important;
    overflow: hidden !important;
  }
  .main {
    position: absolute !important;
    top: 0; left: 0; right: 0; bottom: 0 !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch !important;
  }

  /* Safe area for iPhone notch / home indicator */
  .main .block-container {
    padding-bottom: calc(1rem + env(safe-area-inset-bottom)) !important;
    padding-left:   calc(0.75rem + env(safe-area-inset-left)) !important;
    padding-right:  calc(0.75rem + env(safe-area-inset-right)) !important;
  }

  /* Fix iOS input zoom (16px minimum) */
  input, textarea, select {
    font-size: max(16px, 1em) !important;
  }
}

/* ── Landscape phone ───────────────────────────────────────────── */
@media (max-width: 896px) and (orientation: landscape) {
  [data-testid="stSidebar"] {
    max-height: 100vh !important;
    overflow-y: auto !important;
  }
  .dc-panel { height: 50vh !important; }
}

/* ── Print styles ──────────────────────────────────────────────── */
@media print {
  [data-testid="stSidebar"],
  [data-testid="stToolbar"],
  button, .stButton { display: none !important; }
  .main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
  }
  body { background: white !important; color: black !important; }
  a::after { content: " (" attr(href) ")"; }
}

/* ── Sticky tab bar on mobile ──────────────────────────────────── */
@media (max-width: 640px) {
  [data-testid="stTabs"] [role="tablist"] {
    position: sticky !important;
    top: 0 !important;
    z-index: 50 !important;
    background: var(--bg-main) !important;
    padding: 6px 0 !important;
    border-bottom: 1px solid rgba(77,107,254,0.15) !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.35) !important;
  }

  /* Larger tab chips on mobile */
  [data-testid="stTabs"] [role="tab"] {
    min-height: 36px !important;
    padding: 6px 12px !important;
    font-size: 0.78rem !important;
    border-radius: 18px !important;
    background: rgba(77,107,254,0.08) !important;
    margin: 2px !important;
  }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: var(--primary) !important;
    color: #fff !important;
  }

  /* Sliders: larger drag handle */
  [data-testid="stSlider"] [role="slider"] {
    width: 24px !important;
    height: 24px !important;
    margin-top: -10px !important;
  }
  [data-testid="stSlider"] [data-baseweb="slider"] {
    padding: 12px 6px !important;
  }

  /* Checkboxes: bigger tap area */
  [data-testid="stCheckbox"] label {
    min-height: 40px !important;
    display: flex !important;
    align-items: center !important;
    padding: 4px 0 !important;
    gap: 10px !important;
  }
  [data-testid="stCheckbox"] input[type="checkbox"] {
    width: 20px !important;
    height: 20px !important;
    flex-shrink: 0 !important;
  }

  /* Expanders: full-width, easier to tap */
  details[data-testid="stExpander"] summary {
    min-height: 48px !important;
    padding: 12px 14px !important;
    font-size: 0.88rem !important;
    display: flex !important;
    align-items: center !important;
  }

  /* Number inputs: bigger */
  [data-testid="stNumberInput"] input {
    min-height: 44px !important;
    font-size: 16px !important;
    text-align: center !important;
  }
  [data-testid="stNumberInput"] button {
    min-width: 44px !important;
    min-height: 44px !important;
  }

  /* Sidebar story selector: full width */
  [data-testid="stSidebar"] [data-testid="stSelectbox"] {
    width: 100% !important;
  }

  /* Story cards in dashboard: single column */
  .story-card-grid {
    grid-template-columns: 1fr !important;
  }

  /* SVG charts: scale down */
  svg { max-width: 100% !important; height: auto !important; }

  /* Bottom safe zone for phones with home bar */
  .main .block-container {
    padding-bottom: calc(80px + env(safe-area-inset-bottom)) !important;
  }

  /* Reduce heading sizes */
  h1 { font-size: 1.35rem !important; }
  h2 { font-size: 1.1rem !important; }
  h3 { font-size: 0.95rem !important; }

  /* Word count badge in sidebar: compact */
  .wc-badge {
    font-size: 0.65rem !important;
    padding: 2px 6px !important;
  }
}

/* ── Very small phones (< 380px, e.g. SE) ─────────────────────── */
@media (max-width: 380px) {
  .main .block-container {
    padding: 0.5rem 0.5rem 4rem !important;
  }
  [data-testid="stTabs"] [role="tab"] {
    font-size: 0.68rem !important;
    padding: 5px 8px !important;
  }
  button[kind="secondary"], button[kind="primary"],
  .stButton > button {
    font-size: 0.78rem !important;
    padding: 8px 10px !important;
  }
}

/* ── High-DPI retina display sharpness ─────────────────────────── */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .wc-badge, .story-card { border-width: 0.5px !important; }
}

/* ── Dynamic font size (fluid typography) ──────────────────────── */
:root {
  --fluid-base: clamp(0.82rem, 2.2vw, 0.95rem);
}
@media (max-width: 640px) {
  p, li, span, div { font-size: var(--fluid-base); }
  [data-testid="stMarkdownContainer"] p { font-size: var(--fluid-base) !important; }
}
"""


def workspace_style():   _inject(_NO_FADE_CSS + _WS_CSS + _CONFIRM_CSS + _ACCESSIBILITY_CSS + _MOBILE_CSS)

def theme_toggle_widget():
    """Renders a Light/Dark toggle — must be called inside a sidebar tab."""
    is_light = st.session_state.get("light_theme", False)
    label = "☀️ Light mode" if is_light else "🌙 Dark mode"
    if st.button(f"Theme: {label}", key="_theme_toggle", use_container_width=True):
        st.session_state["light_theme"] = not is_light
        st.rerun()
