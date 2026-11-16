"""
Best-effort consent-based Roblox Studio GUI login through Windows UI Automation.
Fails closed if the accessible login controls or verification cannot be identified.
Never logs or stores username, password, cookies, OTP, or screenshots.
No CAPTCHA/2FA bypass.
"""
import os
import re
import sys
import time
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

USER = os.environ.get("ROBLOX_USERNAME", "")
PASSWORD = os.environ.get("ROBLOX_PASSWORD", "")
if not USER or not PASSWORD:
    raise SystemExit("MISSING_LOGIN_SECRETS")
del os.environ["ROBLOX_PASSWORD"]
del os.environ["ROBLOX_USERNAME"]

def windows():
    return [
        w for w in Desktop(backend="uia").windows()
        if w.is_visible() and any(term in (w.window_text() or "").lower()
            for term in ("roblox", "log in", "login", "sign in"))
    ]

def controls(win):
    try:
        return [c for c in win.descendants() if c.is_visible()]
    except Exception:
        return []

def name(ctrl):
    try:
        return (ctrl.element_info.name or "").strip().lower()
    except Exception:
        return ""

def type_into(field, val):
    # Does not print secrets. Operates ONLY on named login form elements.
    field.click_input()
    send_keys("^a")
    send_keys(val, with_spaces=True, pause=0.01, vk_packet=True)

print("Studio GUI login: searching for accessible official login form.")
deadline = time.time() + 95
submitted = False
while time.time() < deadline and not submitted:
    for win in windows():
        desc = controls(win)
        edits = [c for c in desc if c.element_info.control_type in ("Edit", "Document")]
        user_fields = [c for c in edits if re.search(r"username|email|phone|사용자 이름|이메일", name(c))]
        pass_fields = [c for c in edits if re.search(r"password|비밀번호", name(c))]
        submit_buttons = [c for c in desc if c.element_info.control_type in ("Button", "Hyperlink") and
                          re.search(r"^(log in|login|sign in|로그인)$", name(c))]
        if len(user_fields) != 1 or len(pass_fields) != 1 or len(submit_buttons) != 1:
            continue
        type_into(user_fields[0], USER)
        type_into(pass_fields[0], PASSWORD)
        submit_buttons[0].click_input()
        submitted = True
        break
    time.sleep(2)

USER = ""
PASSWORD = ""
if not submitted:
    raise SystemExit("LOGIN_CONTROLS_NOT_ACCESSIBLE: manual consent or different UI required")

print("Login form submitted. Waiting for evidence of Studio login completion.")
deadline = time.time() + 90
while time.time() < deadline:
    for win in windows():
        desc = controls(win)
        labels = [name(c) for c in desc]
        if any(re.search(r"2-step|two-step|verification code|authenticator|인증 코드|2단계|captcha|보안 확인", x) for x in labels):
            raise SystemExit("ADDITIONAL_VERIFICATION_REQUIRED")
        # Conservatively require the Studio navigation UI with no visible login password form.
        nav = any(x in ("file", "view", "test", "model", "파일", "보기", "테스트", "모델") for x in labels)
        login_edit = any(c.element_info.control_type == "Edit" and
                         re.search(r"password|비밀번호", name(c)) for c in desc)
        if nav and not login_edit:
            print("Studio navigation UI detected after login form submission.")
            sys.exit(0)
    time.sleep(3)
raise SystemExit("LOGIN_NOT_VERIFIED")
