"""Credential-free, read-only Roblox Studio Assistant UI accessibility probe.

Launches NO Roblox sign-in, invokes NO MCP UI toggle, never clicks, types or
captures pixels. Moves pointer only over top-right mezzanine after the
isolated local Baseplate window is visible. Logs aggregate UI shapes only.
"""
import time
import psutil
from pywinauto import Desktop, mouse


def studio_pids():
    return {p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
            if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"}


def windows():
    pids = studio_pids()
    out = []
    for w in Desktop(backend="uia").windows():
        try:
            if w.is_visible() and w.element_info.process_id in pids:
                out.append(w)
        except Exception:
            continue
    return out


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


def exposed_assistant():
    counts = {"name":0,"automation_id":0,"help_text":0}
    for w in windows():
        try:
            for c in w.descendants():
                if not c.is_visible():
                    continue
                for key in counts:
                    value = str(getattr(c.element_info, key, "") or "").lower()
                    if "assistant" in value or "어시스턴트" in value:
                        counts[key] += 1
        except Exception:
            continue
    return counts


def has_tooltip(pids):
    for backend in ("win32", "uia"):
        try:
            for w in Desktop(backend=backend).windows():
                try:
                    if not w.is_visible() or w.process_id() not in pids:
                        continue
                    if (w.window_text() or "").strip().lower() in ("assistant","어시스턴트"):
                        if "tooltip" in (w.class_name() or "").lower():
                            return True
                except Exception:
                    continue
        except Exception:
            continue
    return False


def run():
    deadline=time.monotonic()+130
    editor=None
    while time.monotonic()<deadline:
        matches=[w for w in windows()
                 if "ci_only_baseplate_test" in (w.window_text() or "").lower()]
        if len(matches)==1:
            editor=matches[0]
            break
        time.sleep(4)
    print("ASSISTANT_OFFLINE_EDITOR_DIAG: editor_title_found=%s studio_windows=%d" %
          (bool(editor),len(windows())),flush=True)
    counts=exposed_assistant()
    print("ASSISTANT_OFFLINE_UIA_DIAG: name=%d id=%d help=%d" %
          (counts["name"],counts["automation_id"],counts["help_text"]),flush=True)
    if editor is None:
        print("ASSISTANT_OFFLINE_EDITOR_NOT_PRESENT: login may be required to open fixture.",flush=True)
        return
    r=editor.rectangle()
    if r.width()<700 or r.height()<500:
        print("ASSISTANT_OFFLINE_GEOMETRY_UNAVAILABLE",flush=True)
        return
    try:
        editor.set_focus()
    except Exception:
        pass
    mouse.move(coords=(r.left+r.width()//2,r.top+230))
    time.sleep(1.0)
    if has_tooltip(studio_pids()):
        print("ASSISTANT_OFFLINE_EXISTING_TOOLTIP: ambiguous; refusing probe.",flush=True)
        return
    points=0
    found=0
    for yoff in (42,67,92,118,144):
        for fraction in (.60,.64,.68,.72,.76,.80,.84,.88,.92,.96):
            x=int(r.left+r.width()*fraction)
            y=int(r.top+yoff)
            if not (r.left < x < r.right-14 and r.top < y < r.bottom):
                continue
            mouse.move(coords=(x,y))
            time.sleep(.7)
            points += 1
            if has_tooltip(studio_pids()):
                found += 1
                break
        if found: break
    print("ASSISTANT_OFFLINE_HOVER_DIAG: points=%d exact_tooltip_found=%s (NO clicks)" %
          (points,bool(found)),flush=True)


if __name__=="__main__":
    run()
