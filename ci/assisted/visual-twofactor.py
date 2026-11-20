"""Volatile DXGI/WGC visual fallback for the *official* Roblox 2FA selector.

Use only after the verified primary Roblox sign-in and UI Automation failed
to find a unique Email method. RapidOCR runs locally on an in-memory crop.
No screenshots, OCR text, emails, URLs, codes or usernames are persisted/logged.
Only a uniquely OCR-labelled, UIA-bounded choice may receive Win32 SendInput.
"""
from __future__ import annotations
import os
import re
import time

EMAIL = re.compile(r"(?<![a-z])e-?mail(?![a-z])|이메일", re.I)
MASKED = re.compile(r"(?:\*|•|·){2,}.{0,32}@[a-z0-9.-]+\.[a-z]{2,}", re.I)
BAD = re.compile(r"settings?|change|remove|disable|recovery|account|설정|변경|삭제|복구", re.I)
TARGET_TYPES = frozenset(("MenuItem", "RadioButton", "ListItem", "Button", "Hyperlink"))


def unique_ocr_target(lines, candidates):
    """Pure geometry + semantics. Return the unique candidate index, else None.

    lines: (text, confidence, left, top, right, bottom) in desktop coords.
    candidates: (control_type, left, top, right, bottom).
    An OCR word is evidence only when its bounding center lies inside an
    actual clickable official challenge control. Never click raw OCR coords.
    """
    matched = set()
    for text, score, left, top, right, bottom in lines:
        if score < .81 or len(text) > 100 or not (
            (EMAIL.search(text) or MASKED.search(text)) and not BAD.search(text)
        ):
            continue
        cx, cy = (left+right)/2, (top+bottom)/2
        enclosing = [
            idx for idx, (typ, x0, y0, x1, y1) in enumerate(candidates)
            if typ in TARGET_TYPES
            and 40 <= x1-x0 <= 1200 and 15 <= y1-y0 <= 160
            and x0+2 <= cx <= x1-2 and y0+2 <= cy <= y1-2
        ]
        if len(enclosing) != 1:
            return None
        matched.add(enclosing[0])
    return next(iter(matched)) if len(matched) == 1 else None


def _snapshot(window, backend):
    import dxcam
    import numpy as np
    cam = None
    try:
        cam = dxcam.create(backend=backend, output_color="RGB",
                           processor_backend="numpy")
        frame = cam.grab(new_frame_only=False)
        if frame is None:
            return None
        image = np.asarray(frame)
        h, w = image.shape[:2]
        rect = window.rectangle()
        mode = os.environ.get("ROBLOX_LOGIN_MODE", "")
        # Browser address bar and browser chrome are outside our crop.
        top_pad = 130 if mode == "browser" else 48
        l = max(0, int(rect.left + 20))
        t = max(0, int(rect.top + top_pad))
        r = min(w, int(rect.right - 20))
        b = min(h, int(rect.bottom - 25))
        if r-l < 260 or b-t < 190:
            return None
        return image[t:b, l:r, :].copy(), (l, t, r, b)
    finally:
        if cam is not None:
            cam.release()


def _lines(image, origin, engine):
    result = engine(image)
    if result is None or result.boxes is None or not result.txts:
        return []
    l, t = origin
    out = []
    for box, raw_text, conf in zip(result.boxes, result.txts, result.scores):
        if conf is None:
            continue
        pts = list(box)
        if len(pts) < 4:
            continue
        xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
        out.append((str(raw_text).lower().strip(), float(conf),
                    min(xs)+l, min(ys)+t, max(xs)+l, max(ys)+t))
    return out


def _target_rects(controls, bounds):
    targets = []
    wrappers = []
    for c in controls:
        try:
            typ = c.element_info.control_type
            if typ not in TARGET_TYPES or not c.is_visible():
                continue
            rect = c.rectangle()
            cx, cy = (rect.left+rect.right)/2, (rect.top+rect.bottom)/2
            if not (bounds[0]+6 < cx < bounds[2]-6
                    and bounds[1]+6 < cy < bounds[3]-6):
                continue
            targets.append((typ, rect.left, rect.top, rect.right, rect.bottom))
            wrappers.append(c)
        except Exception:
            continue
    return targets, wrappers


def try_visual_email(official_window, controls):
    """One guarded action. Returns True only after actual SendInput click."""
    try:
        from rapidocr import RapidOCR
        from wgc_sendinput_probe import click_abs, user32
    except ImportError:
        print("VISUAL_2FA_DIAG: vision_runtime_unavailable", flush=True)
        return False
    if official_window is None or not controls:
        return False
    if not any(getattr(c.element_info, "control_type", "") == "MenuItem"
               for c in controls):
        print("VISUAL_2FA_DIAG: no_official_method_menu", flush=True)
        return False
    # No password or login-form clicks are allowed by this fallback.
    try:
        official_window.set_focus()
        time.sleep(.5)
        if user32.GetForegroundWindow() != official_window.handle:
            print("VISUAL_2FA_DIAG: verified_host_not_foreground", flush=True)
            return False
    except Exception:
        return False
    try:
        engine = RapidOCR()
    except Exception:
        print("VISUAL_2FA_DIAG: vision_model_not_available", flush=True)
        return False

    confirmed = None
    for attempt in range(2):
        snapshot = None
        for backend in ("dxgi", "winrt"):
            try:
                snapshot = _snapshot(official_window, backend)
                if snapshot is not None:
                    print("VISUAL_2FA_DIAG: backend=%s frame_ready=True" % backend, flush=True)
                    break
            except Exception:
                continue
        if snapshot is None:
            print("VISUAL_2FA_DIAG: WGC_DXGI_capture_unavailable", flush=True)
            return False
        image, region = snapshot
        candidates, wrappers = _target_rects(controls, region)
        if not candidates:
            return False
        try:
            words = _lines(image, region[:2], engine)
        except Exception:
            print("VISUAL_2FA_DIAG: OCR_failed", flush=True)
            return False
        # No OCR text, even partial/masked email, is ever logged.
        index = unique_ocr_target(words, candidates)
        print("VISUAL_2FA_DIAG: detected_lines=%d unique_email_target=%s pass=%d" %
              (len(words), index is not None, attempt + 1), flush=True)
        if index is None or (confirmed is not None and confirmed != index):
            return False
        confirmed = index
        time.sleep(.5)

    try:
        target = wrappers[confirmed]
        r = target.rectangle()
        typ, x0, y0, x1, y1 = candidates[confirmed]
        if (abs(r.left-x0) > 8 or abs(r.top-y0) > 8
                or abs(r.right-x1) > 8 or abs(r.bottom-y1) > 8):
            return False
        if user32.GetForegroundWindow() != official_window.handle:
            return False
        click_abs((x0+x1)//2, (y0+y1)//2)
        print("VISUAL_2FA_EMAIL_CLICKED: unique OCR label + UIA bounds + two fresh frames + SendInput", flush=True)
        return True
    except Exception:
        return False
