"""
Best-effort Windows UI Automation of official Roblox Studio MCP toggle.
No blind coordinate clicks; fails if the requested official controls are not exposed.
"""
import re
import time
from pywinauto import Desktop

def get_controls():
    all_controls = []
    for window in Desktop(backend="uia").windows():
        if not window.is_visible():
            continue
        try:
            if ("roblox" not in window.window_text().lower() and
                "studio" not in window.window_text().lower()):
                continue
            all_controls.extend(window.descendants())
        except Exception:
            pass
    return [c for c in all_controls if c.is_visible()]

def match(pattern, types=None):
    for ctrl in get_controls():
        if types and ctrl.element_info.control_type not in types:
            continue
        if re.search(pattern, (ctrl.element_info.name or "").strip(), re.I):
            return ctrl
    return None

def click_when_found(pattern, timeout=35):
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = match(pattern, ("Button", "MenuItem", "Hyperlink", "Text", "CheckBox", "TabItem"))
        if found:
            try:
                found.click_input()
                return True
            except Exception:
                pass
        time.sleep(1)
    return False

print("Attempting official Roblox Studio MCP UI toggle.")
if not click_when_found(r"^Assistant$|^어시스턴트$", 30):
    raise SystemExit("ASSISTANT_UI_NOT_ACCESSIBLE")
if not click_when_found(r"Manage MCP Servers|MCP 서버 관리", 25):
    raise SystemExit("MANAGE_MCP_SERVERS_NOT_ACCESSIBLE")
toggle = match(r"Enable Studio as MCP server|Studio를 MCP 서버로 활성화", ("CheckBox", "Button", "Text"))
if not toggle:
    raise SystemExit("MCP_TOGGLE_NOT_ACCESSIBLE")
try:
    is_on = toggle.get_toggle_state() == 1
except Exception:
    is_on = False
if not is_on:
    toggle.click_input()
print("MCP activation UI attempted; launcher presence will be checked separately.")
