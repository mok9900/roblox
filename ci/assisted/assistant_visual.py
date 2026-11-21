"""Guarded, in-memory DXGI/OCR discovery of Roblox Studio Assistant.

Use ONLY with the uniquely confirmed local CI Baseplate editor after login.
OCR stays inside the process: no screenshots, account names, OCR results,
cookies or secrets are written, transmitted, or printed. Click only after
two fresh, high-confidence exact Assistant tooltip observations.
"""
from __future__ import annotations

import re
import time


EXACT_ASSISTANT = re.compile(r"^(?:(?:ai\s+)?assistant|어시스턴트)$", re.I)


def tooltip_heading(text):
    """Recognize the documented hover heading, not arbitrary Assistant prose.

    RapidOCR may merge the title with its descriptive tooltip sentence.
    Only the official AI Assistant + "Chat with Studio Assistant" form
    is accepted in that case. Reject settings, sidebars and generic prose.
    """
    line = " ".join(str(text).split()).strip()
    if EXACT_ASSISTANT.fullmatch(line):
        return True
    return bool(re.match(
        r"^AI Assistant\s+Chat with Studio Assistant\b", line, re.I
    ))


def focus_verified_editor(win, user32, *, pause=time.sleep):
    """Make ONLY the uniquely verified local CI Baseplate editor foreground.

    A plain UIA set_focus is insufficient on GitHub-hosted Windows in some
    Studio builds. This uses the restore/temporary-topmost sequence already
    proven in visual-browser-login.py and always undoes the topmost flag.
    The guarded caller must have identified exactly one local test editor.
    """
    import ctypes as ct

    try:
        if "ci_only_baseplate_test" not in (win.window_text() or "").lower():
            return False
        hwnd = int(win.handle)
        if hwnd <= 0 or not user32.IsWindow(hwnd):
            return False
        user32.SetWindowPos.argtypes = [
            ct.c_void_p, ct.c_void_p, ct.c_int, ct.c_int,
            ct.c_int, ct.c_int, ct.c_uint
        ]
        user32.SetWindowPos.restype = ct.c_int
        flags = 0x0001 | 0x0002 | 0x0040  # no resize/move, show
        user32.ShowWindow(hwnd, 3)         # SW_MAXIMIZE: reveal full-right mezzanine
        try:
            for _ in range(3):
                if user32.GetForegroundWindow() == hwnd:
                    return True
                try:
                    win.set_focus()
                except Exception:
                    pass
                user32.SetWindowPos(hwnd, ct.c_void_p(-1), 0, 0, 0, 0, flags)
                user32.SetForegroundWindow(hwnd)
                pause(.5)
                if user32.GetForegroundWindow() == hwnd:
                    return True
                pause(.7)
        finally:
            # Reverting topmost is mandatory even after failures.
            user32.SetWindowPos(hwnd, ct.c_void_p(-2), 0, 0, 0, 0, flags)
        return user32.GetForegroundWindow() == hwnd
    except Exception:
        return False


def unique_tooltip_near_pointer(items, pointer, *, region):
    """Pure selector: items=(text, confidence, x0, y0, x1, y1).

    Require one exact, well-bounded word near the hovered position and
    inside the clipped, verified editor mezzanine. Ambiguity fails closed.
    """
    x, y = pointer
    left, top, right, bottom = region
    if not (left <= x < right and top <= y < bottom):
        return False
    matches = []
    for name, score, x0, y0, x1, y1 in items:
        if not tooltip_heading(name):
            continue
        # Preserve high confidence for exact short labels; allow a slight
        # reduction only for multi-line descriptions that OCR merges.
        merged = not bool(EXACT_ASSISTANT.fullmatch(" ".join(str(name).split())))
        if score < (.88 if merged else .91):
            continue
        if not (left <= x0 < x1 <= right and top <= y0 < y1 <= bottom):
            continue
        # A merged heading+description may be a larger OCR rectangle.
        if x1 - x0 > (420 if merged else 195) or y1 - y0 > (125 if merged else 65):
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # Tooltips near the top-right corner may extend to the left to
        # remain on-screen, rather than centering under the hovered icon.
        if abs(cx - x) <= 260 and abs(cy - y) <= 170:
            matches.append((x0, y0, x1, y1))
    return len(matches) == 1


def ocr_items(engine, rgb_image, offset):
    """Convert RapidOCR results into ephemeral absolute desktop rectangles."""
    res = engine(rgb_image)
    if res is None or res.boxes is None or not res.txts:
        return []
    xoff, yoff = offset
    out = []
    for box, text, confidence in zip(res.boxes, res.txts, res.scores):
        if confidence is None or len(str(text)) > 70 or len(box) < 4:
            continue
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        out.append((str(text).strip(), float(confidence),
                    min(xs) + xoff, min(ys) + yoff,
                    max(xs) + xoff, max(ys) + yoff))
    return out


def try_visual_assistant(win):
    """Nonpersistent DXGI scan; click only on verified Assistant hover tooltip."""
    try:
        import dxcam
        import numpy as np
        from rapidocr import RapidOCR
        from pywinauto import mouse
        from wgc_sendinput_probe import click_abs, user32
    except ImportError:
        print("MCP_VISUAL_DIAG: local_ocr_runtime_unavailable", flush=True)
        return False

    if "ci_only_baseplate_test" not in (win.window_text() or "").lower():
        print("MCP_VISUAL_DIAG: unverified_editor", flush=True)
        return False

    try:
        if not focus_verified_editor(win, user32):
            print("MCP_VISUAL_DIAG: editor_not_foreground_after_guarded_activation", flush=True)
            return False
        # Foreground activation may also maximize this verified local editor.
        # Always capture its NEW bounds, never its pre-maximize dimensions.
        rect = win.rectangle()
        if rect.width() < 700 or rect.height() < 500:
            return False

        engine = RapidOCR()
        cam = None
        try:
            cam = dxcam.create(backend="dxgi", output_color="RGB",
                               processor_backend="numpy")
            # Only the right/top Studio chrome is ever passed to the OCR engine.
            # The workspace, editor content, browser, chat and OTP are excluded.
            def read():
                frame = cam.grab(new_frame_only=False)
                if frame is None:
                    return None
                a = np.asarray(frame)
                h, w = a.shape[:2]
                bounds = (max(0, int(rect.left + .55 * rect.width())),
                          max(0, int(rect.top + 4)),
                          min(w, int(rect.right - 12)),
                          min(h, int(rect.top + 235)))
                l, t, r, b = bounds
                if r - l < 200 or b - t < 160:
                    return None
                return ocr_items(engine, a[t:b, l:r, :].copy(), (l, t)), bounds

            # Baseline blocks stale/static Assistant text mistaken for a tooltip.
            mouse.move(coords=(rect.left + rect.width() // 2, rect.top + 250))
            time.sleep(.4)
            baseline = read()
            if baseline is None:
                print("MCP_VISUAL_DIAG: dxgi_frame_unavailable", flush=True)
                return False
            if any(tooltip_heading(a[0]) for a in baseline[0]):
                print("MCP_VISUAL_DIAG: static_assistant_text_ambiguous", flush=True)
                return False

            scanned = 0
            text_hints = 0
            # The Assistant sparkles icon is in Studio's TOP-RIGHT
            # mezzanine, beside sharing and notifications. Hover-only.
            # Include the final 2-4% used by compact-width Studio builds.
            for yoff in (43, 72, 103):
                for ratio in (.70, .78, .84, .89, .93, .96, .985):
                    point = (int(rect.left + rect.width() * ratio),
                             int(rect.top + yoff))
                    if not (baseline[1][0] <= point[0] < baseline[1][2]
                            and baseline[1][1] <= point[1] < baseline[1][3]):
                        continue
                    if user32.GetForegroundWindow() != win.handle:
                        return False
                    mouse.move(coords=point)
                    time.sleep(.85)
                    first = read()
                    scanned += 1
                    if first is None:
                        continue
                    if any(tooltip_heading(item[0]) for item in first[0]):
                        text_hints += 1
                    if not unique_tooltip_near_pointer(
                            first[0], point, region=first[1]):
                        continue
                    time.sleep(.5)
                    second = read()
                    if second is None or not unique_tooltip_near_pointer(
                            second[0], point, region=second[1]):
                        continue
                    if user32.GetForegroundWindow() != win.handle:
                        return False
                    # The pointer remains on the exact control whose tooltip
                    # was observed twice. This is the only mutation.
                    click_abs(*point)
                    print("MCP_ASSISTANT_OPEN_REQUESTED: DXGI exact tooltip double-check + guarded SendInput", flush=True)
                    return True
            print("MCP_VISUAL_DIAG: scanned=%d text_hints=%d tooltip_verified=False" % (scanned, text_hints), flush=True)
        finally:
            if cam is not None:
                cam.release()
    except Exception:
        # Never print exception details, which could contain pixels or OCR data.
        print("MCP_VISUAL_DIAG: safe_scan_unavailable", flush=True)
    return False
