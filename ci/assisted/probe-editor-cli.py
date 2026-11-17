"""
Read-only probe for a Roblox Studio place opened via --task EditFile.

Only boolean and aggregate GUI accessibility signals; no screenshots or
sensitive captions are printed or saved.
"""
import time
from pywinauto import Desktop
import psutil

TEMPLATE_STEM = "CI_Only_Baseplate_Test"
TABS = {"home", "model", "test", "view", "plugins", "script", "홈", "모델", "테스트", "보기", "플러그인"}
EXPLORER = {"explorer", "탐색기"}
ASSISTANT = {"assistant", "어시스턴트"}

def studio_pids():
    return {
        p.info["pid"]
        for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"
    }

def get_studio_windows():
    ids = studio_pids()
    out = []
    for w in Desktop(backend="uia").windows():
        try:
            if w.is_visible() and w.element_info.process_id in ids:
                out.append(w)
        except Exception:
            pass
    return out

def name(c):
    try:
        return (c.element_info.name or "").strip().lower()
    except Exception:
        return ""

deadline = time.monotonic() + 105
last_report = 0
while time.monotonic() < deadline:
    ws = get_studio_windows()
    names = []
    title_match = False
    for w in ws:
        try:
            title_match |= TEMPLATE_STEM.lower() in (w.window_text() or "").lower()
            names.extend(name(c) for c in w.descendants() if c.is_visible())
        except Exception:
            pass
    tabs = sum(1 for n in names if n in TABS)
    has_assistant = any(n in ASSISTANT for n in names)
    has_explorer = any(n in EXPLORER for n in names)
    if title_match or (tabs >= 2 and (has_assistant or has_explorer)):
        print("PLACE_EDITOR_VERIFIED: actual Studio editor window discovered.", flush=True)
        print("PLACE_EDITOR_HINTS: filename_title=%s, tabs=%d, assistant=%s, explorer=%s" %
              (title_match, tabs, has_assistant, has_explorer), flush=True)
        raise SystemExit(0)
    if time.monotonic() - last_report > 20:
        print("PLACE_EDITOR_PENDING: studio_windows=%d, tabs=%d, assistant=%s, explorer=%s, filename_title=%s" %
              (len(ws), tabs, has_assistant, has_explorer, title_match), flush=True)
        last_report = time.monotonic()
    time.sleep(3)

print("PLACE_EDITOR_NOT_VERIFIED: no reliable local editor signal after CLI launch.", flush=True)
raise SystemExit(10)
