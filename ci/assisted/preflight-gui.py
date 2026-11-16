"""
Non-sensitive Studio GUI accessibility probe.
Never captures screenshots or prints text, usernames, tokens, or window titles.
Only reports aggregate counts of accessible login controls.
"""
import re
import time
from pywinauto import Desktop

def count_controls():
    result = {"windows": 0, "username_fields": 0, "password_fields": 0, "login_buttons": 0}
    for win in Desktop(backend="uia").windows():
        if not win.is_visible():
            continue
        try:
            title = win.window_text().lower()
            if not any(x in title for x in ("roblox", "login", "log in", "sign in")):
                continue
            result["windows"] += 1
            for control in win.descendants():
                if not control.is_visible():
                    continue
                name = (control.element_info.name or "").lower()
                kind = control.element_info.control_type
                if kind == "Edit" and re.search(r"username|email|phone|사용자 이름|이메일", name):
                    result["username_fields"] += 1
                if kind == "Edit" and re.search(r"password|비밀번호", name):
                    result["password_fields"] += 1
                if kind in ("Button", "Hyperlink") and re.search(r"^(log in|login|sign in|로그인)$", name):
                    result["login_buttons"] += 1
        except Exception:
            pass
    return result

time.sleep(15)
r = count_controls()
print("Studio GUI visible windows:", r["windows"])
print("Accessible username fields:", r["username_fields"])
print("Accessible password fields:", r["password_fields"])
print("Accessible login buttons:", r["login_buttons"])
print("This probe makes no authentication claim.")
