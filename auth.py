"""
Staff authentication, roles and page permissions.

WHO SIGNS IN
    Only Mineral Gleaning Rights staff: field officers, verification officers,
    program coordinators, the Ergo liaison, administrators.

WHO DOES NOT
    The workers on the dumps. They are records in the portal's roster, not
    users of it. They are registered in person by a field officer, and their
    touchpoints are a printed receipt, an SMS and the USSD lookup line. There is deliberately no
    function in this module that can give a roster record a password, and the
    sign-in form asks for a staff email address, which no worker has.

APPROVAL
    Sign-up is open, but a new account lands as "pending" with role None and can
    reach nothing. An administrator assigns a role before the portal opens. An
    open self-signup that could immediately register a dump into a gold
    traceability system would not be defensible, so the wait is shown plainly.

SESSIONS
    A signed-in browser carries an opaque token in the URL query string, matched
    against sessions.json. That is what survives a refresh; Streamlit session
    state alone does not, because a refresh starts a new session.
"""

import hashlib
import re
import secrets
from datetime import datetime

import pandas as pd
import streamlit as st

import store
import theme

# ---------------------------------------------------------------------------
# ROLES
# ---------------------------------------------------------------------------

ROLES = {
    "field_officer": "Field officer",
    "verification_officer": "Verification officer",
    "coordinator": "Program coordinator",
    "ergo_liaison": "Ergo liaison",
    "administrator": "Administrator",
}

ROLE_PURPOSE = {
    "field_officer": "Registers workers in person, logs hauls, runs the collection point scan, "
                     "prints and sends receipts.",
    "verification_officer": "Works the review queue and watches whether the threshold is doing its job.",
    "coordinator": "Registers dumps and permits, keeps the cooperative roster.",
    "ergo_liaison": "Confirms arrival samples, releases payment, reads the ledger.",
    "administrator": "Approves staff accounts, assigns roles, sees everything.",
}

DASHBOARD = "Dashboard"
ACCOUNTS_PAGE = "Staff accounts"
WORKER_PAGE = "Register a worker"
RECEIPT_PAGE = "Print a worker receipt"

# Every page in the portal, in nav order.
ALL_PAGES = [
    DASHBOARD,
    "01 Register a dump",
    "Cooperative members",
    WORKER_PAGE,
    "02 Extract and log a haul",
    "03 Collection point scan",
    "Officer review queue",
    "04 Ergo verification and sale",
    RECEIPT_PAGE,
    "Analytics",
    "Ledger",
    ACCOUNTS_PAGE,
]

# What each role can open. Pages outside this list are not rendered in the nav
# at all, rather than shown and then refused.
ROLE_PAGES = {
    "field_officer": [
        DASHBOARD, WORKER_PAGE, "02 Extract and log a haul",
        "03 Collection point scan", RECEIPT_PAGE,
    ],
    "verification_officer": [DASHBOARD, "Officer review queue", "Analytics"],
    "coordinator": [DASHBOARD, "01 Register a dump", "Cooperative members", "Analytics"],
    "ergo_liaison": [DASHBOARD, "04 Ergo verification and sale", "Ledger"],
    "administrator": list(ALL_PAGES),
}

# Demo credentials, one per role. These plaintext strings exist so the landing
# page can show a judge how to get in. What is written to accounts.json is only
# ever the salt and the hash.
DEMO_ACCOUNTS = [
    ("nomsa.field@mgr.org.za", "Nomsa Dlamini", "field_officer", "field-2026"),
    ("thabo.verify@mgr.org.za", "Thabo Mokoena", "verification_officer", "verify-2026"),
    ("aisha.coord@mgr.org.za", "Aisha Patel", "coordinator", "coord-2026"),
    ("daniel.ergo@mgr.org.za", "Daniel van Wyk", "ergo_liaison", "ergo-2026"),
    ("admin@mgr.org.za", "Grace Sithole", "administrator", "admin-2026"),
]

PROTOTYPE_NOTE = (
    "Prototype sign-in. Passwords are salted and hashed, but this is not production "
    "authentication: there is no rate limiting, no email verification, and the session "
    "token travels in the URL."
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ---------------------------------------------------------------------------
# PASSWORDS
# ---------------------------------------------------------------------------


def hash_password(password, salt=None):
    """Per-user salt plus SHA-256. Adequate for a prototype and stated as such
    in the UI. Production would want a slow KDF such as scrypt or Argon2."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, digest


def verify_password(password, salt, expected):
    _, digest = hash_password(password, salt)
    return secrets.compare_digest(digest, expected)


# ---------------------------------------------------------------------------
# ACCOUNTS
# ---------------------------------------------------------------------------


def seed_demo_accounts():
    """Create the five demo accounts once, already approved, so a judge is
    inside the portal in seconds. Existing accounts are never overwritten."""
    accounts = store.load_accounts()
    changed = False
    for email, name, role, password in DEMO_ACCOUNTS:
        if email in accounts:
            continue
        salt, digest = hash_password(password)
        accounts[email] = {
            "email": email,
            "name": name,
            "salt": salt,
            "hash": digest,
            "role": role,
            "status": "active",
            "created": datetime.now().isoformat(timespec="seconds"),
            "approved_by": "seed",
            "approved_at": datetime.now().isoformat(timespec="seconds"),
            "demo": True,
        }
        changed = True
    if changed:
        store.save_accounts(accounts)


def create_account(email, name, password):
    """Open sign-up. Always lands as pending with no role."""
    email = (email or "").strip().lower()
    name = (name or "").strip()
    if not name:
        return False, "Enter your full name."
    if not EMAIL_RE.match(email):
        return False, "Enter a valid work email address."
    if len(password or "") < 8:
        return False, "Choose a password of at least 8 characters."
    accounts = store.load_accounts()
    if email in accounts:
        return False, "An account already exists for that email address."
    salt, digest = hash_password(password)
    accounts[email] = {
        "email": email,
        "name": name,
        "salt": salt,
        "hash": digest,
        "role": None,
        "status": "pending",
        "created": datetime.now().isoformat(timespec="seconds"),
        "approved_by": None,
        "approved_at": None,
    }
    store.save_accounts(accounts)
    return True, "Request received. An administrator has to approve this account and assign a role."


def set_role(email, role, approved_by):
    accounts = store.load_accounts()
    rec = accounts.get(email)
    if not rec:
        return False, "No such account."
    if role not in ROLES:
        return False, "Unknown role."
    rec["role"] = role
    rec["status"] = "active"
    rec["approved_by"] = approved_by
    rec["approved_at"] = datetime.now().isoformat(timespec="seconds")
    store.save_accounts(accounts)
    return True, f"{rec['name']} approved as {ROLES[role]}."


def suspend_account(email, by):
    accounts = store.load_accounts()
    rec = accounts.get(email)
    if not rec:
        return False, "No such account."
    rec["status"] = "suspended"
    rec["approved_by"] = by
    store.save_accounts(accounts)
    _drop_sessions_for(email)
    return True, f"{rec['name']} suspended. Any open session has been ended."


def reinstate_account(email, by):
    accounts = store.load_accounts()
    rec = accounts.get(email)
    if not rec:
        return False, "No such account."
    rec["status"] = "active" if rec.get("role") else "pending"
    rec["approved_by"] = by
    store.save_accounts(accounts)
    return True, f"{rec['name']} reinstated."


def pending_accounts():
    return [a for a in store.load_accounts().values() if a.get("status") == "pending"]


# ---------------------------------------------------------------------------
# SESSIONS
# ---------------------------------------------------------------------------

TOKEN_KEY = "s"


def _drop_sessions_for(email):
    sessions = store.load_sessions()
    store.save_sessions({t: r for t, r in sessions.items() if r.get("email") != email})


def sign_in(email, password):
    email = (email or "").strip().lower()
    accounts = store.load_accounts()
    rec = accounts.get(email)
    if not rec or not verify_password(password or "", rec["salt"], rec["hash"]):
        return False, "That email address and password do not match an account."
    if rec.get("status") == "suspended":
        return False, "This account is suspended. Contact an administrator."

    token = secrets.token_urlsafe(24)
    sessions = store.load_sessions()
    sessions[token] = {"email": email, "created": datetime.now().isoformat(timespec="seconds")}
    store.save_sessions(sessions)

    st.session_state.auth_email = email
    st.query_params[TOKEN_KEY] = token
    return True, ""


def sign_out():
    token = st.query_params.get(TOKEN_KEY)
    if token:
        sessions = store.load_sessions()
        sessions.pop(token, None)
        store.save_sessions(sessions)
    st.session_state.pop("auth_email", None)
    st.session_state.view = "landing"
    st.query_params.clear()


def restore_session():
    """Called once per run before routing. Turns a token in the URL back into a
    signed-in user, which is what makes a browser refresh survive."""
    if st.session_state.get("auth_email"):
        return
    token = st.query_params.get(TOKEN_KEY)
    if not token:
        return
    rec = store.load_sessions().get(token)
    if rec:
        st.session_state.auth_email = rec["email"]


def current_user():
    """The signed-in account record, or None. Read fresh from disk each run so
    an administrator's role change takes effect on the user's next click."""
    email = st.session_state.get("auth_email")
    if not email:
        return None
    rec = store.load_accounts().get(email)
    if not rec or rec.get("status") == "suspended":
        return None
    return rec


def is_active(user):
    return bool(user and user.get("status") == "active" and user.get("role") in ROLES)


def pages_for(role):
    return [p for p in ALL_PAGES if p in ROLE_PAGES.get(role, [])]


def can_open(user, page):
    return is_active(user) and page in ROLE_PAGES.get(user["role"], [])


# ---------------------------------------------------------------------------
# PUBLIC SCREENS
# ---------------------------------------------------------------------------


def _back_to_landing():
    if st.button("Back to the overview", key="back_landing"):
        st.session_state.view = "landing"
        st.rerun()


def render_sign_in():
    theme.page_header("Staff access", "Sign in", "review")
    st.caption("For Mineral Gleaning Rights staff. The workers on the dumps do not sign in and "
               "have no password. "
               "They are registered in person by a field officer and hold a printed receipt.")

    left, right = st.columns([1, 1])
    with left:
        with st.form("sign_in_form"):
            email = st.text_input("Work email address", placeholder="name@mgr.org.za")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary"):
                ok, message = sign_in(email, password)
                if ok:
                    st.session_state.view = "portal"
                    st.rerun()
                else:
                    st.error(message)
        _back_to_landing()
        st.caption(PROTOTYPE_NOTE)
    with right:
        theme.demo_credentials_panel(DEMO_ACCOUNTS, ROLES)


def render_sign_up():
    theme.page_header("Staff access", "Request staff access", "members")
    st.caption("Anyone can ask. Nobody gets in until an administrator approves the account and "
               "assigns a role. Until then the account can reach nothing.")

    with st.form("sign_up_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name")
        email = c2.text_input("Work email address", placeholder="name@mgr.org.za")
        c3, c4 = st.columns(2)
        password = c3.text_input("Choose a password", type="password",
                                 help="At least 8 characters.")
        confirm = c4.text_input("Confirm password", type="password")
        if st.form_submit_button("Request access", type="primary"):
            if password != confirm:
                st.error("The two passwords do not match.")
            else:
                ok, message = create_account(email, name, password)
                (st.success if ok else st.error)(message)
                if ok:
                    st.info("An administrator will assign your role. Sign in after that to reach the portal.")
    _back_to_landing()
    st.caption(PROTOTYPE_NOTE)


def render_pending(user):
    """Signed in, approved for nothing. Acceptance criterion 2 lands here."""
    theme.page_header("Awaiting approval", "Your account is pending", "review")
    st.warning(f"{user['name']}, your account exists but no role has been assigned yet. "
               "An administrator has to approve it before any part of the portal opens.")
    st.caption("This step is deliberate. An account that could register a dump into a gold "
               "traceability system the moment it was created would not be defensible.")
    st.markdown("#### What happens next")
    st.markdown(
        "1. An administrator opens **Staff accounts** and sees your request.\n"
        "2. They assign the role that matches your job.\n"
        "3. You sign in again and only the pages for that role appear."
    )
    if st.button("Sign out"):
        sign_out()
        st.rerun()


def render_account_sidebar(user):
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f'<div class="acct">{theme.avatar_svg(user["name"], user["email"], 34)}'
        f'<div><div class="acct-name">{user["name"]}</div>'
        f'<div class="acct-role">{ROLES.get(user["role"], "No role")}</div></div></div>',
        unsafe_allow_html=True,
    )
    if user["role"] == "administrator":
        waiting = len(pending_accounts())
        if waiting:
            st.sidebar.warning(f"{waiting} account request(s) waiting for approval")
    if st.sidebar.button("Sign out"):
        sign_out()
        st.rerun()


def render_accounts_page(user):
    """The approval queue and role assignment. Lives here rather than in
    app.py because everything it touches is an account, not a haul."""
    theme.page_header("Administration", "Staff accounts", "review")
    st.caption("Sign-up is open, but a new account arrives with no role and can reach nothing. "
               "Approving it here is what opens the portal, and only for the pages that role needs.")

    st.info("This page governs STAFF accounts only. The workers on the dumps are records in the "
            "cooperative roster and "
            "have no account to approve.")

    accounts = store.load_accounts()
    waiting = [a for a in accounts.values() if a.get("status") == "pending"]

    st.markdown("### Waiting for approval")
    if not waiting:
        st.success("No requests waiting.")
    else:
        for acc in waiting:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(
                        f'<div class="acct">{theme.avatar_svg(acc["name"], acc["email"], 38)}'
                        f'<div><div class="acct-name">{acc["name"]}</div>'
                        f'<div class="acct-role">Requested {acc["created"][:10]}</div></div></div>',
                        unsafe_allow_html=True)
                    st.caption(acc["email"])
                with c2:
                    chosen = st.selectbox(
                        "Assign a role", list(ROLES.keys()),
                        format_func=lambda r: ROLES[r], key=f"role_{acc['email']}")
                    st.caption(ROLE_PURPOSE[chosen])
                    if st.button("Approve and assign", key=f"approve_{acc['email']}",
                                 type="primary"):
                        ok, msg = set_role(acc["email"], chosen, user["email"])
                        (st.success if ok else st.error)(msg)
                        st.rerun()

    st.markdown("### All staff accounts")
    rows = []
    for acc in sorted(accounts.values(), key=lambda a: (a.get("status", ""), a.get("name", ""))):
        rows.append({
            "Name": acc.get("name", ""),
            "Email": acc.get("email", ""),
            "Role": ROLES.get(acc.get("role"), "Not assigned"),
            "Status": acc.get("status", ""),
            "Approved by": acc.get("approved_by") or "",
            "Created": (acc.get("created") or "")[:10],
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.markdown("### Change an existing account")
    others = {f"{a['name']} ({a['email']})": a["email"]
              for a in accounts.values() if a["email"] != user["email"]}
    if not others:
        st.caption("No other accounts to change.")
    else:
        pick = st.selectbox("Account", list(others.keys()))
        target = others[pick]
        c1, c2, c3 = st.columns(3)
        new_role = c1.selectbox("Role", list(ROLES.keys()),
                                format_func=lambda r: ROLES[r], key="reassign_role")
        if c1.button("Change role"):
            ok, msg = set_role(target, new_role, user["email"])
            (st.success if ok else st.error)(msg)
            st.rerun()
        if c2.button("Suspend account"):
            ok, msg = suspend_account(target, user["email"])
            (st.success if ok else st.error)(msg)
            st.rerun()
        if c3.button("Reinstate account"):
            ok, msg = reinstate_account(target, user["email"])
            (st.success if ok else st.error)(msg)
            st.rerun()
        st.caption("Suspending an account ends any session it has open. You cannot change your "
                   "own account here.")

    st.caption(PROTOTYPE_NOTE)
