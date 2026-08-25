"""
Disk persistence for staff accounts and sign-in sessions.

Only STAFF accounts live here. The workers on the dumps are records inside the
portal's members roster and never appear in this file, because they never sign in. See auth.py.

Two files sit next to the app:
  accounts.json   one record per staff account, passwords stored as salt + hash
  sessions.json   opaque sign-in tokens, so a browser refresh does not sign you out

Batch, dump and roster data stay in Streamlit session state exactly as before.
Writes go through a temp file and os.replace so an interrupted save cannot leave
a half-written accounts file behind.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACCOUNTS_PATH = HERE / "accounts.json"
SESSIONS_PATH = HERE / "sessions.json"

SESSION_TTL_DAYS = 14


def _read(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default
    return data if isinstance(data, dict) else default


def _write(path, data):
    """Write through a temp file in the same directory, then replace. A crash
    mid-write leaves the previous file intact rather than a truncated one."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_accounts():
    """{email_lowercase: account_record}"""
    return _read(ACCOUNTS_PATH, {})


def save_accounts(accounts):
    _write(ACCOUNTS_PATH, accounts)


def load_sessions():
    """{token: {"email": ..., "created": iso}} with expired tokens dropped."""
    raw = _read(SESSIONS_PATH, {})
    cutoff = datetime.now() - timedelta(days=SESSION_TTL_DAYS)
    live = {}
    for token, rec in raw.items():
        if not isinstance(rec, dict) or "email" not in rec:
            continue
        try:
            if datetime.fromisoformat(rec.get("created", "")) < cutoff:
                continue
        except ValueError:
            continue
        live[token] = rec
    return live


def save_sessions(sessions):
    _write(SESSIONS_PATH, sessions)
