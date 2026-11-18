"""Conservative read-only verifier for a local Roblox Studio EditFile editor.

Accepted evidence (never just a running Studio process or a CLI invocation):
  * the expected local fixture name in an actual visible Studio window title; or
  * at least three distinct editor-exclusive ribbon labels in ONE Studio window,
    stable across two polls; or
  * at least two distinct editor-exclusive ribbons together with Explorer,
    Properties, Output or Assistant in the SAME Studio window.

Only prints aggregate counts / whitelisted Studio UI terms. Never records
captions, usernames, email addresses, screenshots, passwords or OTP values.
"""
import time
import psutil
from pywinauto import Desktop

TEMPLATE_STEM = "CI_Only_Baseplate_Test"
EDITOR_TABS = {"model", "test", "view", "plugins", "script",
               "모델", "테스트", "보기", "플러그인", "스크립트"}
BASIC_TABS = {"home", "홈"}
EDITOR_PANELS = {"assistant", "어시스턴트", "explorer", "탐색기",
                 "properties", "속성", "output", "출력", "toolbox", "도구 상자"}
AUTH_HINTS = {"password", "비밀번호", "username", "사용자 이름", "verification code", "인증 코드"}


def studio_pids():
    return {
        p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"
    }


def studio_windows():
    pids = studio_pids()
    found = []
    for window in Desktop(backend="uia").windows():
        try:
            if window.is_visible() and window.element_info.process_id in pids:
                found.append(window)
        except Exception:
            pass
    return found


def safe_label(control):
    try:
        return (control.element_info.name or "").strip().lower()
    except Exception:
        return ""


def inspect_window(win):
    try:
        names = []
        challenge_fields = False
        for control in win.descendants():
            if not control.is_visible():
                continue
            name = safe_label(control)
            if name:
                names.append(name)
            if control.element_info.control_type == "Edit" and name in AUTH_HINTS:
                challenge_fields = True
        all_names = set(names)
        tabs = all_names & EDITOR_TABS
        panels = all_names & EDITOR_PANELS
        title_hit = TEMPLATE_STEM.lower() in (win.window_text() or "").lower()
        # An editor's dedicated ribbon tabs are structurally different from
        # a welcome page: do not mistake duplicate generic "Home" labels.
        ribbon_strong = len(tabs) >= 3
        ribbon_plus_panel = len(tabs) >= 2 and bool(panels)
        verified = (title_hit or ribbon_strong or ribbon_plus_panel) and not challenge_fields
        return {"verified": verified, "title_hit": title_hit,
                "tabs": tabs, "panels": panels, "auth": challenge_fields}
    except Exception:
        return {"verified": False, "title_hit": False, "tabs": set(),
                "panels": set(), "auth": False}


deadline = time.monotonic() + 120
last_report = 0
stable_key = None
stable_polls = 0
while time.monotonic() < deadline:
    windows = studio_windows()
    details = [inspect_window(w) for w in windows]
    candidates = [d for d in details if d["verified"]]
    if candidates:
        chosen = max(candidates, key=lambda d:(d["title_hit"],len(d["tabs"]),len(d["panels"])))
        fingerprint = (chosen["title_hit"],tuple(sorted(chosen["tabs"])),
                       tuple(sorted(chosen["panels"])))
        if fingerprint == stable_key:
            stable_polls += 1
        else:
            stable_key,stable_polls = fingerprint,1
        if stable_polls >= 2:
            print("PLACE_EDITOR_VERIFIED: editor-only ribbon or local fixture title stable across polls.",flush=True)
            print("PLACE_EDITOR_SAFE_HINTS: file_title=%s, ribbon_tabs=%s, panel_count=%d" %
                  (chosen["title_hit"], ",".join(sorted(chosen["tabs"])),
                   len(chosen["panels"])),flush=True)
            raise SystemExit(0)
    else:
        stable_key,stable_polls = None,0
    if time.monotonic()-last_report > 15:
        max_tabs=max((len(d["tabs"]) for d in details),default=0)
        max_panels=max((len(d["panels"]) for d in details),default=0)
        known_tabs=sorted(set().union(*(d["tabs"] for d in details)))
        print("PLACE_EDITOR_PENDING: studio_windows=%d, max_editor_tabs_per_window=%d, panels=%d, candidate=%s, auth_fields=%s" %
              (len(windows),max_tabs,max_panels,bool(candidates),any(d["auth"] for d in details)),flush=True)
        print("PLACE_EDITOR_SAFE_RIBBON: "+",".join(known_tabs[:12]),flush=True)
        last_report=time.monotonic()
    time.sleep(3)

print("PLACE_EDITOR_NOT_VERIFIED: no stable per-window editor evidence after CLI launch.",flush=True)
raise SystemExit(10)
