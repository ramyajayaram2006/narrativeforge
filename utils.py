import threading, time
import streamlit as st
from database import init_db, load_stories


def check_ollama(model="llama3.2", host="http://localhost:11434"):
    import requests
    try:
        r = requests.get(f"{host}/api/tags", timeout=1)
        if r.status_code != 200:
            return {"ok": False, "model_ready": False,
                    "error": f"Ollama returned HTTP {r.status_code}"}
        models = [m["name"].split(":")[0] for m in r.json().get("models", [])]
        ready  = model.split(":")[0] in models
        return {"ok": True, "model_ready": ready, "error": None}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "model_ready": False,
                "error": "Ollama not running. Start with: ollama serve"}
    except Exception as e:
        return {"ok": False, "model_ready": False, "error": str(e)}


def _warmup_ollama(model="llama3.2", host="http://localhost:11434"):
    """
    FIX #4: Race condition — _ollama_warmed is set INSIDE the response handler,
    not before the request. Only set True if inference actually succeeds.
    """
    if st.session_state.get("_ollama_warmed"):
        return

    def _ping():
        try:
            import requests
            r = requests.post(f"{host}/api/generate",
                              json={"model": model, "prompt": "hi",
                                    "stream": False, "options": {"num_predict": 1}},
                              timeout=90)
            # FIX: only mark warmed if we got a valid response
            if r.status_code == 200 and r.json().get("response") is not None:
                st.session_state["_ollama_warmed"] = True
        except Exception:
            pass  # Ollama not running — stays False, will retry next rerun

    threading.Thread(target=_ping, daemon=True).start()
    # Do NOT set _ollama_warmed here — wait for the response handler above


def ollama_status_banner(model="llama3.2"):
    """Show inline Ollama status. Returns True if ready to generate."""
    # Skip warmup on story open — only check tags endpoint, don't send inference ping
    now    = time.time()
    cached = st.session_state.get("_ollama_status_cache")
    last   = st.session_state.get("_ollama_status_ts", 0)
    if cached is None or (now - last) > 300:
        cached = check_ollama(model)
        st.session_state["_ollama_status_cache"] = cached
        st.session_state["_ollama_status_ts"]    = now

    if cached["ok"] and cached["model_ready"]:
        st.markdown(
            f"<div style='display:inline-flex;align-items:center;gap:6px;"
            f"background:rgba(77,107,254,0.07);border:1px solid rgba(77,107,254,0.20);"
            f"border-radius:20px;padding:3px 11px;font-size:0.68rem;font-weight:700;"
            f"color:#4D6BFE;letter-spacing:0.08em;font-family:JetBrains Mono,monospace;'>"
            f"<span style='width:6px;height:6px;background:#4D6BFE;border-radius:50%;"
            f"box-shadow:0 0 5px #4D6BFE;'></span> {model} · ready</div>",
            unsafe_allow_html=True)
        return True
    elif cached["ok"] and not cached["model_ready"]:
        st.warning(f"⏳ **{model}** not loaded. Run `ollama pull {model}` in a terminal.")
        return False
    else:
        st.error(f"❌ **Ollama not reachable.** {cached['error']}")
        st.code("ollama serve", language="bash")
        return False


def force_sidebar_open():
    import streamlit.components.v1 as components
    components.html("""<script>
    setTimeout(function(){
        var b=window.parent.document.querySelector('[data-testid="collapsedControl"] button');
        if(b)b.click();
        var s=window.parent.document.querySelector('[data-testid="stSidebar"]');
        if(s){s.style.display='block';s.style.visibility='visible';s.style.transform='none';}
    },250);</script>""", height=0)


def init_session_state():
    init_db()
    defaults = {
        "authenticated": False, "username": "",
        "current_view": "auth", "stories": [],
        "current_story": None, "show_cowrite_options": False,
        "pending_input": "", "_ollama_warmed": False,
        "_login_success": False,
        "_ollama_status_cache": None, "_ollama_status_ts": 0,
        "reading_mode": False, "show_revision_mode": False,
        "revision_results": None, "plot_holes_result": None,
        "voice_check_result": None, "title_results": None,
        "firstline_results": None, "prompt_results": None,
        "_ai_generating": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if (st.session_state.authenticated and st.session_state.username
            and not st.session_state.stories):
        st.session_state.stories = load_stories(st.session_state.username)

    if st.session_state.authenticated:
        try:
            from workspace import OLLAMA_MODEL, OLLAMA_HOST
            _warmup_ollama(OLLAMA_MODEL, OLLAMA_HOST)
        except Exception:
            pass
