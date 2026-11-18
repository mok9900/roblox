"""
Activate Roblox Studio's built-in MCP server using the official Assistant UI.

Roblox 2026 layout: Assistant → ... → Settings → MCP Servers → Enable Studio
as MCP server. Older versions: ... → Manage MCP Servers.
Requires a logged-in Studio instance WITH A PLACE OPEN.
Does not read usernames, email, secrets, page contents or take screenshots.
"""
import re
import time
from pywinauto import Desktop
import psutil

def get_controls():
    # Studio's editor windows may be titled only with the local place name.
    # Identify the process instead of relying on window title substrings.
    pids = {
        p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"
    }
    out = []
    for win in Desktop(backend="uia").windows():
        try:
            if not win.is_visible() or win.element_info.process_id not in pids:
                continue
            out.extend(c for c in win.descendants() if c.is_visible())
        except Exception:
            continue
    return out

def label(c):
    try:
        return (c.element_info.name or "").strip().lower()
    except Exception:
        return ""

def kind(c):
    try:
        return c.element_info.control_type
    except Exception:
        return ""


def safe_identifier(c):
    """Use only UIA metadata to identify Roblox's Assistant button."""
    try:
        return (c.element_info.automation_id or "").strip().lower()
    except Exception:
        return ""


def safe_help(c):
    try:
        return (c.element_info.help_text or "").strip().lower()
    except Exception:
        return ""


def assistant_topbar():
    """Find an unambiguously identified Assistant control in Studio's top-right.

    New Studio UI places Assistant in the right side of the mezzanine, rather
    than the legacy View toolbar. Never click an arbitrary icon or guessed
    coordinate; use a matching label/AutomationId/help text *and* geometry.
    """
    pids = {
        p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"
    }
    hits = []
    for win in Desktop(backend="uia").windows():
        try:
            if not win.is_visible() or win.element_info.process_id not in pids:
                continue
            wr = win.rectangle()
            if wr.width() < 600 or wr.height() < 400:
                continue
            for control in win.descendants():
                if not control.is_visible() or kind(control) not in ("Button", "Hyperlink", "Custom"):
                    continue
                metadata = (label(control), safe_identifier(control), safe_help(control))
                if not any(re.search(r"assistant|어시스턴트", item, re.I) for item in metadata):
                    continue
                cr = control.rectangle()
                mid_x = (cr.left + cr.right) / 2
                mid_y = (cr.top + cr.bottom) / 2
                if (wr.left + wr.width() * 0.58 <= mid_x < wr.right
                        and wr.top <= mid_y <= wr.top + 145
                        and 8 <= cr.width() <= 150 and 8 <= cr.height() <= 95):
                    hits.append(control)
        except Exception:
            continue
    print("MCP_ASSISTANT_TOPBAR_CANDIDATES: %d" % len(hits), flush=True)
    if len(hits) != 1:
        return False
    try:
        hits[0].click_input()
        print("MCP_ASSISTANT_TOPBAR_OPENED: unique verified Assistant accessibility control.",flush=True)
        return True
    except Exception:
        return False

def click_exact(pattern, timeout=12):
    end = time.monotonic() + timeout
    order = ("Button", "MenuItem", "Hyperlink", "TabItem", "CheckBox", "ListItem", "Text", "Custom")
    while time.monotonic() < end:
        cs = get_controls()
        for typ in order:
            matches = [c for c in cs if kind(c) == typ and re.fullmatch(pattern, label(c), re.I)]
            for c in matches[:3]:
                try:
                    c.click_input()
                    return True
                except Exception:
                    pass
        time.sleep(1)
    return False

def find_toggle():
    pattern = re.compile(r"(?:enable studio as mcp server|studio를 mcp 서버로 활성화)", re.I)
    cs = get_controls()
    for typ in ("CheckBox", "Button", "Switch", "Text"):
        for c in cs:
            if kind(c) == typ and pattern.search(label(c)):
                return c
    return None

def safe_uia_summary():
    approved = re.compile(
        r"^(?:assistant|어시스턴트|settings|설정|mcp|mcp servers|mcp 서버|"
        r"manage mcp servers|mcp 서버 관리|enable studio as mcp server|"
        r"studio를 mcp 서버로 활성화|more|more options|other options|"
        r"추가 옵션|더보기|\.{3}|…|⋯)$", re.I)
    names = sorted({f"{kind(c)}:{label(c)}" for c in get_controls() if approved.fullmatch(label(c))})
    print("MCP_SAFE_CONTROLS: " + ", ".join(names[:20]), flush=True)

print("MCP_SETUP: finding Assistant in an open Studio editor.", flush=True)
assistant_opened = click_exact(r"assistant|어시스턴트", 12)
if not assistant_opened:
    assistant_opened = assistant_topbar()
if not assistant_opened:
    # In some Studio layouts Assistant is hidden until its official View
    # ribbon tab or Window menu is opened. Only click individually labeled
    # Studio controls, not guessed screen coordinates or browser chrome.
    for gateway in (r"view|보기", r"window|창"):
        if click_exact(gateway, 8):
            print("MCP_UI_GATEWAY_OPENED: whitelisted Studio ribbon/menu.", flush=True)
            if click_exact(r"assistant|어시스턴트", 15):
                assistant_opened = True
                break
if not assistant_opened:
    safe_uia_summary()
    raise SystemExit("ASSISTANT_UI_NOT_ACCESSIBLE")

# Assistant's overflow menu is typically a more/ellipsis button.
if not click_exact(r"manage mcp servers|mcp 서버 관리", 4):
    if not click_exact(r"(?:\.{3}|…|⋯|more|more options|더보기|추가 옵션)", 10):
        print("MCP_MENU_OVERFLOW_NOT_ACCESSIBLE: checking direct Settings/MCP controls.", flush=True)
    if not click_exact(r"manage mcp servers|mcp 서버 관리", 6):
        if click_exact(r"settings|설정", 10):
            print("ASSISTANT_SETTINGS_OPENED.", flush=True)
        else:
            print("ASSISTANT_SETTINGS_NOT_VISIBLE: trying MCP shortcut.", flush=True)
            click_exact(r"mcp", 5)
        if click_exact(r"mcp servers|mcp 서버", 10):
            print("MCP_SERVER_SETTINGS_OPENED.", flush=True)

toggle = find_toggle()
if toggle is None:
    safe_uia_summary()
    raise SystemExit("STUDIO_MCP_TOGGLE_NOT_ACCESSIBLE")
try:
    enabled = toggle.get_toggle_state() == 1
except Exception:
    enabled = False
if not enabled:
    try:
        toggle.click_input()
    except Exception:
        raise SystemExit("STUDIO_MCP_TOGGLE_CLICK_FAILED")
    time.sleep(3)
print("MCP_TOGGLE_UI_PROCESSED: checking the launcher in session script.", flush=True)
