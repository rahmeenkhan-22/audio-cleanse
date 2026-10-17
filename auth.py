"""auth.py: per-user Supabase login for Audio Cleanse.

Why this is separate from database.py: get_db() is cached with st.cache_resource,
so ONE client is shared by every visitor. A logged-in session on a shared client
would leak between users. Here each browser session gets its OWN client, stored
in st.session_state.

Note: login lasts for the browser tab session. A page refresh logs the user out.
"""
from __future__ import annotations

import logging
from typing import Optional

import streamlit as st
from supabase import Client, create_client

log = logging.getLogger(__name__)


def _client() -> Client:
    if "sb_client" not in st.session_state:
        st.session_state["sb_client"] = create_client(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        )
    return st.session_state["sb_client"]


def current_user() -> Optional[dict]:
    """{'id': ..., 'email': ...} or None."""
    return st.session_state.get("auth_user")


def sign_out() -> None:
    client = st.session_state.get("sb_client")
    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass
    for key in ("sb_client", "auth_user"):
        st.session_state.pop(key, None)


def user_client() -> Optional[Client]:
    """This session's client, with a fresh access token attached (refreshes if expired)."""
    if not current_user():
        return None
    client = st.session_state.get("sb_client")
    try:
        session = client.auth.get_session()
        if session is None:
            raise RuntimeError("session expired")
        client.postgrest.auth(session.access_token)
        return client
    except Exception:
        log.warning("Auth session invalid, signing out")
        sign_out()
        return None


def _err(e: Exception) -> str:
    return getattr(e, "message", None) or "Something went wrong. Please try again."


def render_auth_gate() -> bool:
    """Call near the top of app.py. Returns True when logged in; otherwise shows
    the login / sign-up forms and returns False (caller should st.stop())."""
    user = current_user()
    if user:
        with st.sidebar:
            st.caption(f"Signed in as {user['email']}")
            if st.button("Log out", key="auth_logout"):
                sign_out()
                st.rerun()
        return True

    st.subheader("Welcome to Audio Cleanse")
    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                try:
                    res = _client().auth.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )
                    st.session_state["auth_user"] = {"id": res.user.id, "email": res.user.email}
                    st.rerun()
                except Exception as e:
                    st.error(_err(e))

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email", key="su_email")
            password = st.text_input("Password (min 6 characters)", type="password", key="su_pw")
            if st.form_submit_button("Create account"):
                try:
                    _client().auth.sign_up({"email": email.strip(), "password": password})
                    st.success("Check your inbox for a confirmation link, then come back and log in.")
                except Exception as e:
                    st.error(_err(e))
    return False


# ---------- mood data helpers (use the logged-in user's own client) ----------
def save_mood(craving_score: int, trigger_context: str, emotional_state: str,
              day_number: int = 1) -> bool:
    client, user = user_client(), current_user()
    if not client or not user:
        return False
    try:
        client.table("mood_logs").insert({
            "user_id": user["id"],
            "day_number": day_number,
            "craving_score": craving_score,
            "trigger_context": trigger_context,
            "emotional_state": emotional_state,
        }).execute()
        return True
    except Exception:
        log.exception("Failed to save mood entry")
        return False


def load_moods() -> list[dict]:
    client, user = user_client(), current_user()
    if not client or not user:
        return []
    try:
        res = (client.table("mood_logs").select("*")
               .eq("user_id", user["id"]).order("created_at").execute())
        return res.data or []
    except Exception:
        log.exception("Failed to load mood entries")
        return []
