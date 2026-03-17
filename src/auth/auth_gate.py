"""
Streamlit authentication gate.
Call `require_auth()` at the very top of app.py to protect all pages.
"""

import sys
import os

import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
import jwt as _jwt
from auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    is_token_valid,
)
from auth.user_store import authenticate_user, save_refresh_token, validate_refresh_token, revoke_refresh_token


def _try_silent_refresh() -> bool:
    """
    If access token expired but refresh token is valid → issue new access token.
    Returns True if refresh succeeded.
    """
    refresh = st.session_state.get("refresh_token")
    if not refresh:
        return False
    user_id = validate_refresh_token(refresh)
    if user_id is None:
        return False
    username = st.session_state.get("username", "")
    st.session_state["access_token"] = create_access_token(user_id, username)
    return True


def _show_login_form() -> None:
    """Render the login form and handle submission."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🗳️ Brurna Analytics")
        st.markdown("### Acesso Restrito")
        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="admin")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Preencha usuário e senha.")
                return

            user_id = authenticate_user(username, password)
            if user_id is None:
                st.error("Credenciais inválidas.")
                return

            access_token = create_access_token(user_id, username)
            refresh_token = create_refresh_token(user_id)
            save_refresh_token(user_id, refresh_token)

            st.session_state["access_token"] = access_token
            st.session_state["refresh_token"] = refresh_token
            st.session_state["username"] = username
            st.session_state["user_id"] = user_id
            st.rerun()


def require_auth() -> None:
    """
    Gate all Streamlit pages behind authentication.
    If authenticated → renders a logout button in the sidebar and returns.
    If not → renders login form and stops execution (st.stop()).
    """
    token = st.session_state.get("access_token")

    if token and is_token_valid(token):
        # Authenticated — show sidebar logout
        with st.sidebar:
            st.markdown(f"👤 **{st.session_state.get('username', '')}**")
            if st.button("🚪 Sair", use_container_width=True):
                refresh = st.session_state.get("refresh_token")
                if refresh:
                    revoke_refresh_token(refresh)
                for key in ["access_token", "refresh_token", "username", "user_id"]:
                    st.session_state.pop(key, None)
                st.rerun()
        return

    # Token absent or expired — try silent refresh first
    if _try_silent_refresh():
        return

    # No valid session → show login form and stop rendering the rest of the app
    _show_login_form()
    st.stop()
