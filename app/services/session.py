import streamlit as st


def initialize_session():
    defaults = {
        "authenticated": False,
        "token": None,
        "username": None,
        "user_id": None,
        "active_page": "Dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login_user(token, username, user_id):
    st.session_state["authenticated"] = True
    st.session_state["token"] = token
    st.session_state["username"] = username
    st.session_state["user_id"] = user_id


def logout_user():
    st.session_state["authenticated"] = False
    st.session_state["token"] = None
    st.session_state["username"] = None
    st.session_state["user_id"] = None
    st.session_state["active_page"] = "Dashboard"


def is_authenticated():
    return bool(st.session_state.get("authenticated", False))


def get_token():
    return st.session_state.get("token")


def get_username():
    return st.session_state.get("username")


def get_user_id():
    return st.session_state.get("user_id")
