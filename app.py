import os
# Load .env file if present — so GROQ_API_KEY works without PowerShell set
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

import streamlit as st
from utils import init_session_state
from logger import setup_logging

# Initialise structured logging (rotating file + console)
setup_logging()

st.set_page_config(
    page_title="NarrativeForge",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()

# ── Beta Reading: check for shared link token before auth ─────────────────
try:
    from beta_reading import check_beta_token
    if check_beta_token():
        st.stop()
except ImportError:
    pass

# ── PWA: inject manifest link + service worker registration ─────────────────
import streamlit.components.v1 as _pwa_sc
_pwa_sc.html("""
<link rel="manifest" href="/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="NarrativeForge">
<meta name="theme-color" content="#4D6BFE">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/sw.js').then(function(reg) {
      console.log('[NF] ServiceWorker registered:', reg.scope);
    }).catch(function(err) {
      console.log('[NF] ServiceWorker registration failed:', err);
    });
  });
}
</script>
""", height=0)



# Route to the correct view
if not st.session_state.get("authenticated", False):
    from auth import show_auth
    show_auth()
elif st.session_state.get("current_view") == "workspace":
    from workspace import show_workspace
    show_workspace()
else:
    # Show onboarding for new users before dashboard
    try:
        from onboarding import maybe_show_onboarding
        if maybe_show_onboarding():
            st.stop()
    except ImportError:
        pass
    from dashboard import show_dashboard
    show_dashboard()
