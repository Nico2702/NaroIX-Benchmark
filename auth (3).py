"""
GitHub OAuth Authentication for Streamlit
------------------------------------------
Flow:
1. User clicks "Login with GitHub"
2. Redirect to GitHub OAuth authorize URL
3. GitHub redirects back with ?code=...
4. Exchange code for access token
5. Fetch GitHub username
6. Check against whitelist in st.secrets
7. Grant or deny access
"""

import streamlit as st
import requests
import urllib.parse


def _cfg():
    return st.secrets.get("github_oauth", {})

def _client_id():     return _cfg().get("client_id", "")
def _client_secret(): return _cfg().get("client_secret", "")
def _redirect_uri():  return _cfg().get("redirect_uri", "")

def _whitelist():
    raw = _cfg().get("allowed_users", [])
    if isinstance(raw, str):
        return [u.strip().lower() for u in raw.split(",") if u.strip()]
    return [u.strip().lower() for u in raw]


GITHUB_AUTH_URL  = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL  = "https://api.github.com/user"


def _auth_url() -> str:
    params = {
        "client_id":    _client_id(),
        "redirect_uri": _redirect_uri(),
        "scope":        "read:user",
        "allow_signup": "false",
    }
    return f"{GITHUB_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _exchange_code(code: str):
    resp = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id":     _client_id(),
            "client_secret": _client_secret(),
            "code":          code,
            "redirect_uri":  _redirect_uri(),
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    if resp.ok:
        return resp.json().get("access_token")
    return None


def _get_github_user(token: str):
    resp = requests.get(
        GITHUB_USER_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=10,
    )
    if resp.ok:
        return resp.json()
    return None


def require_login():
    """
    Call at the top of your Streamlit app.
    Returns the authenticated GitHub username, or stops the app.
    """
    # Already authenticated in session
    if st.session_state.get("github_user"):
        return st.session_state["github_user"]

    # Handle OAuth callback (?code=...)
    params = st.query_params
    if "code" in params:
        code = params["code"]
        with st.spinner("Authentifizierung..."):
            token = _exchange_code(code)
            if token:
                user = _get_github_user(token)
                if user:
                    username = user.get("login", "").lower()
                    if username in _whitelist():
                        st.session_state["github_user"] = username
                        st.session_state["github_name"] = user.get("name") or username
                        st.session_state["github_avatar"] = user.get("avatar_url", "")
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ GitHub-Benutzer **{username}** ist nicht freigeschalten.")
                        st.stop()
        st.error("❌ Authentifizierung fehlgeschlagen.")
        st.stop()

    # Show login page
    st.markdown("""
<div style='display:flex;flex-direction:column;align-items:center;justify-content:center;
            min-height:60vh;gap:24px;'>
  <div style='text-align:center;'>
    <span style='font-size:48px;font-weight:700;color:#A0B4FF;letter-spacing:3px;'>NaroIX</span><br>
    <span style='font-size:20px;color:#8892b0;'>Benchmark Series</span>
  </div>
  <div style='background:#161b27;border:1px solid #2a2f45;border-radius:16px;
              padding:40px 48px;text-align:center;max-width:400px;'>
    <p style='color:#8892b0;font-size:15px;margin-bottom:24px;'>
      Bitte melde dich mit deinem GitHub-Account an.
    </p>
""", unsafe_allow_html=True)

    st.link_button(
        "🔐  Mit GitHub anmelden",
        url=_auth_url(),
        use_container_width=True,
        type="primary",
    )

    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()
