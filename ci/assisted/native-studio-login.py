"""Safely submit the already-open native Roblox Studio username/password form.

Exit 0: submitted official native form (no secret output).
Exit 10: no verified native form; caller may use visual-browser-login fallback.
Exit 20: unexpected UI/interaction failure; fail closed.
"""
import os
import re
import sys
import time
import psutil
from pywinauto import Desktop

username = os.environ.get("ROBLOX_USERNAME", "")
password = os.environ.get("ROBLOX_PASSWORD", "")
if not username or not password:
    raise SystemExit("ROBLOX_LOGIN_SECRETS_MISSING")


def exact_control(c, pattern):
    try:
        return re.fullmatch(pattern, (c.element_info.name or "").strip(), re.I)
    except Exception:
        return False


def studio_windows():
    pids = {p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
            if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"}
    return [w for w in Desktop(backend="uia").windows()
            if w.is_visible() and w.element_info.process_id in pids]


def verify_native_form():
    wins = studio_windows()
    if len(wins) != 1:
        return None
    win = wins[0]
    try:
        controls = [c for c in win.descendants() if c.is_visible()]
        edits = [c for c in controls if c.element_info.control_type == "Edit"]
        buttons = [c for c in controls if c.element_info.control_type == "Button"]
        users = [c for c in edits if exact_control(
            c, r"(?:username(?:/email/phone)?|user name|email(?: or username)?|"
               r"username, email, or phone|사용자 이름|이메일 또는 사용자 이름)")]
        passwords = [c for c in edits if exact_control(c, r"(?:password|비밀번호)")]
        logins = [c for c in buttons if exact_control(c, r"(?:log in|login|sign in|로그인)")]
        print("NATIVE_STUDIO_FORM_DIAG: edits=%d user_labels=%d pass_labels=%d login_buttons=%d" %
              (len(edits), len(users), len(passwords), len(logins)), flush=True)
        if len(users) != len(passwords) or len(users) != 1 or len(logins) != 1:
            return None
        a,b = users[0].rectangle(),passwords[0].rectangle()
        if a.bottom >= b.top or a.width() < 130 or b.width() < 130:
            return None
        return users[0],passwords[0],logins[0]
    except Exception:
        return None


deadline=time.monotonic()+18
form=None
while time.monotonic()<deadline:
    form=verify_native_form()
    if form:
        break
    time.sleep(2)

if form is None:
    print("NATIVE_STUDIO_FORM_UNAVAILABLE: using guarded visual-browser fallback.", flush=True)
    sys.exit(10)

try:
    field_user,field_password,btn=form
    field_user.set_edit_text(username)
    field_password.set_edit_text(password)
    btn.click_input()
    print("ROBLOX_NATIVE_STUDIO_LOGIN_SUBMITTED: official form clicked, no secrets logged.",flush=True)
except Exception:
    print("NATIVE_STUDIO_FORM_INPUT_FAILED: no retry or blind input.",flush=True)
    sys.exit(20)
username=""
password=""
sys.exit(0)
