"""
Safe Windows graphics-capture and SendInput diagnostic for hosted GitHub Actions.

- Actual DXGI Desktop Duplication backend (dxcam), WGC/WinRT fallback.
- Demonstrates OS-level mouse + keyboard input ONLY against our own Tk test UI.
- Observes the Roblox Studio desktop without clicking any login/2FA controls.
- Outputs only privacy-reduced 48x27 pixelated desktop thumbnails and JSON metrics.
- Never writes raw screenshots, UI text, Roblox credentials, cookies or OTPs.

Usage: python ci/assisted/wgc_sendinput_probe.py --phase safe|studio
"""
from __future__ import annotations

import argparse
import ctypes as ct
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from ctypes import wintypes

OUT_DIR = Path(os.environ.get("RUNNER_TEMP", os.environ.get("TEMP", "."))) / "safe-graphics-probe"
EXPORT = Path(os.environ.get("GITHUB_WORKSPACE", ".")) / "ci" / "assisted" / ".runtime" / "safe-graphics"
EXPORT.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

user32 = ct.WinDLL("user32", use_last_error=True)
kernel32 = ct.WinDLL("kernel32", use_last_error=True)

ULONG_PTR = ct.c_size_t
class MOUSEINPUT(ct.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)
    ]
class KEYBDINPUT(ct.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]
class HARDWAREINPUT(ct.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]
class INPUT_UNION(ct.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
class INPUT(ct.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", wintypes.DWORD), ("data", INPUT_UNION)]
user32.SendInput.argtypes = [wintypes.UINT, ct.POINTER(INPUT), ct.c_int]
user32.SendInput.restype = wintypes.UINT
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ct.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetForegroundWindow.restype = wintypes.HWND

SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


def send_event(event: INPUT) -> None:
    if user32.SendInput(1, ct.byref(event), ct.sizeof(INPUT)) != 1:
        raise RuntimeError("SendInput rejected an event (focus/UIPI/desktop session?)")


def mouse_event(flags: int, x=0, y=0):
    send_event(INPUT(type=0, mi=MOUSEINPUT(x, y, 0, flags, 0, 0)))


def click_abs(x: int, y: int):
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    if width < 2 or height < 2 or not (left <= x < left+width and top <= y < top+height):
        raise RuntimeError("Missing valid interactive virtual desktop geometry")
    xx = round((x - left) * 65535 / (width - 1))
    yy = round((y - top) * 65535 / (height - 1))
    mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, xx, yy)
    time.sleep(0.2)
    mouse_event(MOUSEEVENTF_LEFTDOWN)
    time.sleep(0.1)
    mouse_event(MOUSEEVENTF_LEFTUP)


def type_unicode(s: str):
    for ch in s:
        code = ord(ch)
        if code > 65535:
            raise ValueError("Only BMP Unicode supported in the safe test")
        send_event(INPUT(type=1, ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0)))
        send_event(INPUT(type=1, ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)))


def own_probe_ui() -> None:
    import tkinter as tk
    root = tk.Tk()
    root.title("CI_SAFE_SENDINPUT_PROBE")
    root.geometry("440x250+120+120")
    root.resizable(False, False)
    tk.Label(root, text="WIN32 INPUT TEST - NO ROBLOX CREDENTIALS").place(x=40, y=20)
    text = tk.Entry(root, width=22)
    text.place(x=100, y=70, width=220, height=30)
    text.insert(0, "")
    result_path = OUT_DIR / "sendinput.json"

    def done():
        result_path.write_text(json.dumps({
            "button_clicked": True,
            "keyboard_ok": text.get() == "TEST",
        }), encoding="utf-8")
    tk.Button(root, text="CLICK TEST", command=done, width=24).place(x=105, y=140, width=230, height=38)
    root.after(50_000, root.destroy)
    root.mainloop()


def test_sendinput() -> dict:
    result = {"mouse": False, "keyboard": False, "focused": False, "error_kind": None}
    child = subprocess.Popen([sys.executable, __file__, "--child"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    target = OUT_DIR / "sendinput.json"
    try:
        deadline = time.monotonic() + 14
        hwnd = None
        while time.monotonic() < deadline:
            hwnd = user32.FindWindowW(None, "CI_SAFE_SENDINPUT_PROBE")
            if hwnd:
                break
            time.sleep(0.35)
        if not hwnd:
            raise RuntimeError("Own Tk window did not materialize")
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.7)
        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Own Tk test app did not get keyboard foreground")
        result["focused"] = True
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ct.byref(rect)):
            raise RuntimeError("Cannot get safe Tk window bounds")
        xmid = (rect.left + rect.right) // 2
        # Entry is centered around y ~ 90 in the 250 px client area.
        # Button is centered around y ~ 160 in the 250 px client area.
        click_abs(xmid, rect.top + 105)
        type_unicode("TEST")
        time.sleep(0.5)
        click_abs(xmid, rect.top + 185)
        until = time.monotonic() + 3
        while time.monotonic() < until and not target.exists():
            time.sleep(0.2)
        if target.exists():
            payload = json.loads(target.read_text(encoding="utf-8"))
            result["mouse"] = bool(payload.get("button_clicked"))
            result["keyboard"] = bool(payload.get("keyboard_ok"))
        else:
            result["error_kind"] = "No Tk click callback"
    except Exception as exc:
        result["error_kind"] = type(exc).__name__
    finally:
        child.terminate()
        try:
            child.wait(timeout=4)
        except subprocess.TimeoutExpired:
            child.kill()
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
    return result


def capture_safe(phase: str):
    from PIL import Image
    import numpy as np
    import dxcam
    result = []
    for backend in ("dxgi", "winrt"):
        report = {"backend": backend, "usable": False, "nonblank": False, "error_kind": None}
        try:
            with dxcam.create(backend=backend, output_color="RGB", processor_backend="numpy") as cam:
                image = None
                for _ in range(10):
                    image = cam.grab(new_frame_only=False)
                    if image is not None:
                        break
                    time.sleep(0.3)
                if image is None:
                    raise RuntimeError("No new frame returned")
                img = np.asarray(image)
                report["usable"] = True
                report["height"] = int(img.shape[0])
                report["width"] = int(img.shape[1])
                report["stddev"] = round(float(img.std()), 1)
                report["nonblank"] = report["stddev"] > 2.0
                # Aggressively irreversible downsampling. Text, OTPs, usernames
                # and fine UI detail are NOT preserved or ever written to disk.
                thumb = Image.fromarray(img.astype("uint8"), mode="RGB").resize(
                    (48, 27), Image.Resampling.BOX
                ).resize((480, 270), Image.Resampling.NEAREST)
                # No full-resolution screenshots are retained.
                out = EXPORT / f"{phase}_{backend}_redacted.png"
                thumb.save(out)
                report["redacted_artifact"] = out.name
        except Exception as exc:
            report["error_kind"] = type(exc).__name__
            # No Roblox account secrets are provided to this diagnostic workflow.
            # Library's short exception type/message identifies API incompatibility.
            hint = str(exc).replace("\\n", " ")
            if len(hint) > 190:
                hint = hint[:190] + "..."
            report["capture_error_hint"] = hint
        result.append(report)

    # Separate, non-DXGI fallback ONLY for differentiating desktop lock
    # from a DXcam/COM library incompatibility. Not counted as WGC/DXGI success.
    gdi = {"backend": "gdi-diagnostic-only", "usable": False, "error_kind": None}
    try:
        from PIL import ImageGrab
        raw = ImageGrab.grab(all_screens=False)
        gdi["usable"] = True
        gdi["width"], gdi["height"] = raw.size
        gdi["stddev"] = round(float(np.asarray(raw).std()), 1)
        thumb = raw.convert("RGB").resize(
            (48, 27), Image.Resampling.BOX
        ).resize((480, 270), Image.Resampling.NEAREST)
        name = f"{phase}_gdi_diagnostic_redacted.png"
        thumb.save(EXPORT / name)
        gdi["redacted_artifact"] = name
    except Exception as exc:
        gdi["error_kind"] = type(exc).__name__
    result.append(gdi)
    return result


def studio_counts():
    import psutil
    from pywinauto import Desktop
    processes = {
        p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"
    }
    windows = []
    counts = {"studio_processes": len(processes), "studio_windows": 0, "studio_edit_controls": 0, "studio_button_controls": 0}
    for w in Desktop(backend="uia").windows():
        try:
            if not w.is_visible() or w.element_info.process_id not in processes:
                continue
            counts["studio_windows"] += 1
            for c in w.descendants():
                if c.is_visible():
                    if c.element_info.control_type == "Edit":
                        counts["studio_edit_controls"] += 1
                    elif c.element_info.control_type == "Button":
                        counts["studio_button_controls"] += 1
        except Exception:
            pass
    return counts


def main(phase):
    report = {
        "phase": phase,
        "session_name": os.environ.get("SESSIONNAME", "(unset)"),
        "desktop_width": user32.GetSystemMetrics(0),
        "desktop_height": user32.GetSystemMetrics(1),
        "interactive_window_foreground_present": bool(user32.GetForegroundWindow()),
    }
    if phase == "safe":
        report["sendinput"] = test_sendinput()
    if phase == "studio":
        exe = os.environ.get("STUDIO_EXE")
        report["studio_before"] = studio_counts()
        if exe and not report["studio_before"]["studio_processes"]:
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(14)
        report["studio_after"] = studio_counts()
    report["capture"] = capture_safe(phase)
    path = EXPORT / f"{phase}_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("SAFE_GRAPHICS_PROBE_RESULT=" + json.dumps(report, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("safe", "studio"))
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if args.child:
        own_probe_ui()
    elif args.phase:
        main(args.phase)
    else:
        parser.error("--phase required")
