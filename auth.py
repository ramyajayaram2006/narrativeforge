import time
import json
import streamlit as st
from styles import auth_page_style
from database import (register_user, verify_login, load_stories,
                      change_password, delete_story)

_MAX_ATTEMPTS = 5
_LOCKOUT_SECS = 60


def _check_lockout():
    attempts  = st.session_state.get("_login_attempts", 0)
    locked_at = st.session_state.get("_login_locked_at", None)
    if locked_at is not None:
        elapsed = time.time() - locked_at
        if elapsed < _LOCKOUT_SECS:
            return True, int(_LOCKOUT_SECS - elapsed)
        st.session_state["_login_attempts"]  = 0
        st.session_state["_login_locked_at"] = None
    return False, 0


def _full_logout():
    """FIX #1: Clear entire session state, then reinitialise safe defaults."""
    st.session_state.clear()
    st.session_state.authenticated = False
    st.session_state.current_view  = "auth"


def show_auth():
    auth_page_style()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown("""
            <div class='auth-logo'>
                <span style='color:#4D6BFE;font-size:1.8rem;'>&#9670;</span> NarrativeForge
            </div>
            <div class='auth-sub'>Where Stories Are Forged</div>
            <br>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["  Login  ", "  Sign Up  "])

        with tab1:
            with st.form("login_form"):
                # FIX #7: max_chars on all text inputs
                username  = st.text_input("Username", placeholder="Your username",
                                           max_chars=50, key="login_username")
                password  = st.text_input("Password", type="password",
                                           placeholder="Your password", key="login_password")
                submitted = st.form_submit_button("Login →", use_container_width=True,
                                                   type="primary")
            if submitted:
                is_locked, secs = _check_lockout()
                if is_locked:
                    st.error(f"Too many failed attempts. Wait {secs}s before retrying.")
                elif not username.strip() or not password:
                    st.error("Please enter your username and password.")
                elif not verify_login(username, password):
                    st.session_state["_login_attempts"] = (
                        st.session_state.get("_login_attempts", 0) + 1)
                    if st.session_state["_login_attempts"] >= _MAX_ATTEMPTS:
                        st.session_state["_login_locked_at"] = time.time()
                        st.error(f"Account locked for {_LOCKOUT_SECS}s.")
                    else:
                        rem = _MAX_ATTEMPTS - st.session_state["_login_attempts"]
                        st.error(f"Incorrect credentials. ({rem} attempt(s) remaining)")
                else:
                    st.session_state["_login_attempts"]  = 0
                    st.session_state["_login_locked_at"] = None
                    st.session_state.authenticated  = True
                    st.session_state.username       = username.strip()
                    st.session_state.current_view   = "dashboard"
                    st.session_state.stories        = load_stories(username.strip())
                    st.session_state._login_success = True
                    st.rerun()

        with tab2:
            with st.form("signup_form"):
                new_user    = st.text_input("Username", placeholder="Choose a username",
                                             max_chars=50, key="signup_username")
                new_email   = st.text_input("Email (optional)", placeholder="your@email.com",
                                             max_chars=120, key="signup_email")
                new_pass    = st.text_input("Password", type="password",
                                             placeholder="At least 6 characters",
                                             key="signup_password")
                new_confirm = st.text_input("Confirm Password", type="password",
                                             placeholder="Repeat your password",
                                             key="signup_confirm")
                submitted2  = st.form_submit_button("Create Account →",
                                                     use_container_width=True,
                                                     type="primary")
            if submitted2:
                if not new_user.strip() or not new_pass:
                    st.error("Username and password are required.")
                elif len(new_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                elif new_pass != new_confirm:
                    st.error("Passwords do not match.")
                else:
                    result = register_user(new_user.strip(),
                                           new_email.strip(), new_pass)
                    if result["ok"]:
                        st.session_state.authenticated = True
                        st.session_state.username      = new_user.strip()
                        st.session_state.current_view  = "dashboard"
                        st.session_state.stories       = []
                        st.rerun()
                    else:
                        st.error(result["error"])

        st.markdown(
            "<p style='text-align:center;color:var(--text-faint,#A0A5B8);"
            "font-size:0.72rem;margin-top:16px;font-family:JetBrains Mono,monospace;'>"
            "bcrypt secured · local-first · no cloud</p>",
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  Account Settings panel (shown inside workspace sidebar)
# ══════════════════════════════════════════════════════════════
def show_account_settings(story=None):
    """
    FIX #2 + #3: Password change, account deletion, data export.
    Render inside a Streamlit expander in the sidebar.
    """
    username = st.session_state.get("username", "")

    with st.expander("⚙️ Account Settings", expanded=False):
        st.markdown(
            f"<div style='font-size:0.72rem;color:#6B7080;font-family:JetBrains Mono,monospace;"
            f"margin-bottom:10px;'>Signed in as <strong style='color:#4D6BFE;'>{username}</strong></div>",
            unsafe_allow_html=True)

        # ── FIX #2: Password change ────────────────────────────────────────
        st.markdown(
            "<div style='font-size:0.68rem;color:#6B7080;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;'>"
            "Change Password</div>", unsafe_allow_html=True)
        with st.form("change_pw_form", clear_on_submit=True):
            cur_pw  = st.text_input("Current password", type="password", key="cpw_cur")
            new_pw  = st.text_input("New password",     type="password", key="cpw_new")
            conf_pw = st.text_input("Confirm new",      type="password", key="cpw_conf")
            pw_btn  = st.form_submit_button("Update Password",
                                            use_container_width=True)
        if pw_btn:
            if not verify_login(username, cur_pw):
                st.error("Current password is incorrect.")
            elif len(new_pw) < 6:
                st.error("New password must be at least 6 characters.")
            elif new_pw != conf_pw:
                st.error("Passwords do not match.")
            else:
                change_password(username, new_pw)
                st.success("Password updated successfully.")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # ── FIX #3a: Data export ───────────────────────────────────────────
        st.markdown(
            "<div style='font-size:0.68rem;color:#6B7080;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;'>"
            "Export My Data</div>", unsafe_allow_html=True)
        stories = st.session_state.get("stories", [])
        if stories:
            export_data = json.dumps({
                "username": username,
                "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "stories": stories,
            }, indent=2)
            st.download_button(
                "📦 Download All Data (JSON)",
                data=export_data,
                file_name=f"narrativeforge_export_{username}.json",
                mime="application/json",
                use_container_width=True,
                help="Downloads all your stories and messages as JSON")
        else:
            st.caption("No stories to export.")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # ── FIX #3b: Account deletion ──────────────────────────────────────
        st.markdown(
            "<div style='font-size:0.68rem;color:#E53935;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;'>"
            "Danger Zone</div>", unsafe_allow_html=True)
        if not st.session_state.get("_confirm_delete_account"):
            if st.button("🗑 Delete My Account", use_container_width=True,
                         key="del_account_init"):
                st.session_state["_confirm_delete_account"] = True
                st.rerun()
        else:
            st.markdown(
                "<div style='background:rgba(229,57,53,0.08);border:1px solid rgba(229,57,53,0.25);"
                "border-radius:8px;padding:10px 12px;font-size:0.78rem;color:#FFCDD2;"
                "margin-bottom:8px;'>⚠️ This will permanently delete your account and all "
                "stories. This cannot be undone.</div>",
                unsafe_allow_html=True)
            with st.form("delete_acct_form", clear_on_submit=True):
                del_pw  = st.text_input("Enter password to confirm",
                                         type="password", key="del_acct_pw")
                del_btn = st.form_submit_button("Permanently Delete Account",
                                                 use_container_width=True)
            if del_btn:
                if not verify_login(username, del_pw):
                    st.error("Incorrect password.")
                else:
                    from database import delete_story as _del_story
                    for s in stories:
                        _del_story(username, s["id"])
                    # Remove the user record
                    from database import _db, _q
                    with _db() as (conn, cur):
                        cur.execute(_q("DELETE FROM users WHERE username=?"),
                                    (username,))
                    _full_logout()
                    st.success("Account deleted.")
                    st.rerun()
            if st.button("✖ Cancel", key="cancel_del_acct",
                         use_container_width=True):
                st.session_state.pop("_confirm_delete_account", None)
                st.rerun()
