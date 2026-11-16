"""
Create an unsaved, local Baseplate test place after Roblox Studio login.

Why: Roblox official MCP Assistant controls appear only inside an open place.
This routine doesn't touch any published game or user's existing place.
No screenshots, account names, window titles, or place contents are logged.
"""
import re
import time
from pywinauto import Desktop

KIND_ORDER = ("Button", "ListItem", "Hyperlink", "TabItem", "Group", "Text", "Image", "Custom")

def studio_windows():
    out = []
    for w in Desktop(backend="uia").windows():
        try:
            if w.is_visible() and ("roblox" in (w.window_text() or "").lower()
                                   or "studio" in (w.window_text() or "").lower()):
                out.append(w)
        except Exception:
            pass
    return out

def controls():
    seen = []
    for w in studio_windows():
        try:
            seen.extend([c for c in w.descendants() if c.is_visible()])
        except Exception:
            continue
    return seen

def name(c):
    try:
        return (c.element_info.name or "").strip().lower()
    except Exception:
        return ""

def kind(c):
    try:
        return c.element_info.control_type
    except Exception:
        return ""

def click(pattern):
    items = controls()
    for klass in KIND_ORDER:
        choices = [c for c in items if kind(c) == klass and pattern.fullmatch(name(c))]
        if not choices:
            continue
        for c in choices[:3]:
            try:
                c.click_input()
                return True
            except Exception:
                pass
    return False

ASSISTANT = re.compile(r"assistant|어시스턴트", re.I)
BASEPLATE = re.compile(r"baseplate|베이스플레이트", re.I)
NEW = re.compile(r"new experience|new project|새 경험|새 프로젝트|new", re.I)
PLACE_UI = re.compile(r"^(home|model|avatar|script|plugins|홈|모델|아바타|스크립트|플러그인)$", re.I)

def ready():
    cs = controls()
    names = [name(c) for c in cs]
    # Actual editor UI: Assistant and at least two normal editor tabs.
    tabs = sum(1 for n in names if PLACE_UI.fullmatch(n))
    return tabs >= 2 and any(ASSISTANT.fullmatch(n) for n in names)

print("PLACE_PREP: checking for an already-open Studio place.", flush=True)
if ready():
    print("PLACE_READY: editor + Assistant detected.", flush=True)
    raise SystemExit(0)

opened = False
deadline = time.monotonic() + 150
new_attempted = False
last_notice = 0
while time.monotonic() < deadline:
    if ready():
        print("PLACE_READY: editor + Assistant detected.", flush=True)
        raise SystemExit(0)
    if not opened:
        if click(BASEPLATE):
            print("BASEPLATE_SELECTED: opening unsaved test place.", flush=True)
            opened = True
        elif not new_attempted and click(NEW):
            new_attempted = True
            print("NEW_EXPERIENCE_SELECTED: searching for Baseplate template.", flush=True)
    if opened:
        # Wait for Studio 3D viewport and Assistant to finish initializing.
        now = time.monotonic()
        if now - last_notice > 25:
            print("PLACE_LOADING: waiting for the editor's Assistant controls.", flush=True)
            last_notice = now
    time.sleep(3)

if opened:
    raise SystemExit("BASEPLATE_EDITOR_NOT_READY: template selected but no editor Assistant UI found")
raise SystemExit("BASEPLATE_TEMPLATE_NOT_ACCESSIBLE: unable to open Studio test place via UI automation")
