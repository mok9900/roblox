"""Enable official Roblox Studio MCP via the signed-in local Place editor.

Roblox 2026: Assistant (right mezzanine) > … > Manage MCP Servers
or Assistant > … > Settings > MCP Servers > Enable Studio as MCP server.
Never click an unnamed object unless a unique, official Assistant tooltip
has identified that exact control. Never use screen captures or inspect URLs.
"""
import os
import re
import time
import psutil
from pywinauto import Desktop, mouse

ASSISTANT = re.compile(r"\bassistant\b|어시스턴트", re.I)
MCP_MENU = re.compile(r"^(?:manage mcp servers|mcp 서버 관리|mcp 서버 관리하기)$", re.I)
MCP_SETTINGS = re.compile(r"^(?:mcp servers|mcp 서버)$", re.I)
ENABLE = re.compile(
    r"(?:enable studio as (?:an? )?mcp server|studio를 mcp 서버로 활성화)",
    re.I
)
OVERFLOW = re.compile(r"^(?:\.\.\.|…|⋯|more|more options|더보기|추가 옵션)$", re.I)
SETTINGS = re.compile(r"^(?:settings|설정)$", re.I)
ALLOWED = ("Button", "MenuItem", "Hyperlink", "TabItem", "CheckBox", "ListItem", "Custom")


def studio_pids():
    return {
        p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"
    }


def studio_windows():
    pids = studio_pids()
    out = []
    for window in Desktop(backend="uia").windows():
        try:
            if window.is_visible() and window.element_info.process_id in pids:
                out.append(window)
        except Exception:
            continue
    return out


def controls():
    out = []
    for win in studio_windows():
        try:
            out.extend(c for c in win.descendants() if c.is_visible())
        except Exception:
            continue
    return out


def attr(c, field):
    try:
        return str(getattr(c.element_info, field, "") or "").strip().lower()
    except Exception:
        return ""


def kind(c):
    return attr(c, "control_type")


def safe_name(c):
    return attr(c, "name")


def assistant_metadata(c):
    return any(ASSISTANT.search(attr(c, field))
               for field in ("name", "automation_id", "help_text"))


def click_unique(pattern, timeout=10, *, types=ALLOWED):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        cs = [c for c in controls()
              if kind(c) in types and pattern.fullmatch(safe_name(c))]
        # Never pick the first of several identically named buttons.
        if len(cs) == 1:
            try:
                cs[0].click_input()
                return True
            except Exception:
                pass
        time.sleep(1)
    return False


def top_right(win, c):
    try:
        wr, cr = win.rectangle(), c.rectangle()
        cx, cy = (cr.left + cr.right)/2, (cr.top + cr.bottom)/2
        return (wr.width() >= 580 and wr.height() >= 400
                and wr.left + .55*wr.width() <= cx < wr.right
                and wr.top <= cy < wr.top + 170
                and 8 <= cr.width() <= 170 and 8 <= cr.height() <= 100)
    except Exception:
        return False


def tooltip_assistant():
    names = set()
    for w in Desktop(backend="uia").windows():
        try:
            if (w.is_visible() and w.element_info.control_type == "ToolTip"
                    and w.element_info.process_id in studio_pids()):
                name = (w.element_info.name or "").strip().lower()
                if name in ("assistant", "어시스턴트"):
                    names.add(name)
        except Exception:
            continue
    return bool(names)


def assistant_topbar():
    """Use only unique labeled controls or a fresh official tooltip.

    On some Studio builds the mezzanine Assistant icon is unlabeled in UIA.
    In that case, hover over the top-right Studio buttons and require a
    unique Assistant tooltip before clicking. Never blindly click coordinates.
    """
    candidates = []
    for w in studio_windows():
        try:
            for c in w.descendants():
                if not c.is_visible() or kind(c) not in ("Button", "Hyperlink", "Custom"):
                    continue
                if top_right(w, c):
                    candidates.append(c)
        except Exception:
            continue
    labeled = [c for c in candidates if assistant_metadata(c)]
    print("MCP_TOPBAR_SAFE_DIAG: buttons=%d labeled_assistant=%d" %
          (len(candidates), len(labeled)), flush=True)
    if len(labeled) == 1:
        try:
            labeled[0].click_input()
            print("MCP_ASSISTANT_OPEN_REQUESTED: uniquely labeled Studio control.", flush=True)
            return True
        except Exception:
            return False
    if labeled:
        return False
    hovered = 0
    # Candidates must be actual UIA buttons in the *right mezzanine*, not
    # a series of guessed pixels. Tooltips provide the missing identity.
    for c in candidates[:22]:
        try:
            r = c.rectangle()
            mouse.move(coords=((r.left+r.right)//2,(r.top+r.bottom)//2))
            time.sleep(.7)
            hovered += 1
            if tooltip_assistant():
                c.click_input()
                print("MCP_ASSISTANT_OPEN_REQUESTED: identified by exact hover tooltip.", flush=True)
                return True
        except Exception:
            continue
    print("MCP_TOPBAR_TOOLTIP_DIAG: hovered_candidates=%d recognized=False" %
          hovered, flush=True)
    return False


def launcher_ready():
    return os.path.isfile(os.path.expandvars(r"%LOCALAPPDATA%\Roblox\mcp.bat"))


def safe_diagnostics(stage):
    cs = controls()
    keys = [
        (r"assistant|어시스턴트", "assistant"),
        (r"(?:manage )?mcp servers?|mcp 서버(?: 관리)?", "mcp_menu"),
        (r"settings|설정", "settings"),
        (r"more|more options|더보기|\.\.\.|…|⋯", "more"),
        (r"enable studio as (?:an? )?mcp server|studio를 mcp 서버로 활성화", "mcp_toggle"),
    ]
    details = {}
    for pattern, key in keys:
        details[key] = sum(1 for c in cs if
                           re.fullmatch(pattern, safe_name(c), re.I))
    print("MCP_SAFE_DIAG: stage=%s studio_windows=%d controls=%d counts=%s" %
          (stage, len(studio_windows()), len(cs),
           ",".join("%s:%d" % (k, v) for k, v in details.items())), flush=True)


def find_toggle():
    cs = controls()
    labeled = [c for c in cs if ENABLE.search(safe_name(c))]
    toggles = [c for c in labeled if kind(c) in ("CheckBox", "Button", "Switch")]
    if len(toggles) == 1:
        return toggles[0]
    if len(toggles) > 1 or len(labeled) != 1:
        return None
    # Some builds render the caption as Text adjacent to an unlabeled
    # CheckBox. Require a unique nearby control on the same side.
    try:
        rect = labeled[0].rectangle()
        mid_y = (rect.top+rect.bottom)/2
        near = []
        for c in cs:
            if kind(c) not in ("CheckBox", "Switch"):
                continue
            cr = c.rectangle()
            cy = (cr.top+cr.bottom)/2
            if abs(cy-mid_y) < 32 and 0 <= cr.left-rect.right <= 220:
                near.append(c)
        return near[0] if len(near)==1 else None
    except Exception:
        return None


def toggle_state(c):
    try:
        return int(c.get_toggle_state())
    except Exception:
        try:
            return int(c.get_check_state())
        except Exception:
            return None


def enable_toggle():
    c = find_toggle()
    if c is None:
        safe_diagnostics("toggle_missing")
        raise SystemExit("STUDIO_MCP_TOGGLE_NOT_ACCESSIBLE")
    state = toggle_state(c)
    if state == 1:
        print("MCP_UI_TOGGLE_ALREADY_ENABLED", flush=True)
        return
    try:
        c.click_input()
    except Exception:
        raise SystemExit("STUDIO_MCP_TOGGLE_CLICK_FAILED")
    time.sleep(3)
    new = toggle_state(c)
    print("MCP_UI_TOGGLE_ACTIVATED: observable=%s launcher=%s" %
          (new == 1, launcher_ready()), flush=True)
    if new != 1 and not launcher_ready():
        raise SystemExit("STUDIO_MCP_TOGGLE_NOT_VERIFIED")


print("MCP_SETUP: local editor required; locating official Assistant.", flush=True)
safe_diagnostics("initial")
if launcher_ready():
    print("MCP_OFFICIAL_LAUNCHER_ALREADY_PRESENT", flush=True)
    raise SystemExit(0)

opened = False
deadline = time.monotonic() + 65
while time.monotonic() < deadline and not opened:
    opened = click_unique(ASSISTANT, 3, types=("Button","Hyperlink","Custom"))
    if not opened:
        opened = assistant_topbar()
    if not opened:
        time.sleep(2)
if not opened:
    safe_diagnostics("assistant_not_found")
    raise SystemExit("ASSISTANT_UI_NOT_ACCESSIBLE")

time.sleep(2)
safe_diagnostics("assistant_opened")
# Prefer official direct menu, then Assistant overflow -> Manage MCP Servers.
if not click_unique(MCP_MENU, 6):
    if not click_unique(OVERFLOW, 8, types=("Button", "MenuItem", "Custom")):
        safe_diagnostics("overflow_missing")
        raise SystemExit("ASSISTANT_OVERFLOW_NOT_ACCESSIBLE")
    if not click_unique(MCP_MENU, 10):
        if not click_unique(SETTINGS, 8):
            safe_diagnostics("settings_missing")
            raise SystemExit("ASSISTANT_SETTINGS_NOT_ACCESSIBLE")
        if not click_unique(MCP_SETTINGS, 10):
            safe_diagnostics("mcp_settings_missing")
            raise SystemExit("MCP_SERVER_SETTINGS_NOT_ACCESSIBLE")

print("MCP_SERVER_SETTINGS_OPENED", flush=True)
enable_toggle()
if not launcher_ready():
    raise SystemExit("STUDIO_MCP_LAUNCHER_NOT_GENERATED")
print("MCP_OFFICIAL_LAUNCHER_VERIFIED", flush=True)
