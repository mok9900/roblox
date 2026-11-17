"""
Inspect browser or WebView2 after Studio's on-screen login CTA.

This module runs ONLY on a throwaway no-credentials Actions test runner.
No page URL, input values, account identifiers or full desktop are recorded.
A tightly cropped browser image masks the URL/header area.
"""
import ctypes as ct
import json
import os
import re
import time
from ctypes import wintypes
from pathlib import Path

import psutil
from PIL import ImageGrab
from pywinauto import Desktop

OUT = Path(os.environ["GITHUB_WORKSPACE"]) / "ci" / "assisted" / ".runtime" / "safe-graphics"
BROWSERS = {"msedge.exe", "chrome.exe", "firefox.exe", "msedgewebview2.exe", "webview2.exe"}
ALLOWED_TEXT = re.compile(
    r"^(?:Microsoft Edge|Welcome to Microsoft Edge|Roblox|Log In|Log in|Login|Sign in|"
    r"Sign in to Roblox|Sign in to Roblox Studio|Continue|Continue without signing in|"
    r"Continue without an account|Start without your data|Start without data|"
    r"Confirm and start browsing|Skip|Not now|Maybe later|Get started|"
    r"Accept and continue|Accept and get started|Allow|Decline|"
    r"Username|Password|Email|Security check|Verify|"
    r"Set up your new tab page|Sync your data|Choose your theme|"
    r"Finish|Next|Use without signing in|로그인|비밀번호|사용자 이름|이메일|"
    r"시작|건너뛰기|계속|나중에|확인)$", re.I)
user32 = ct.windll.user32
user32.GetWindowRect.argtypes = [wintypes.HWND, ct.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

def scan(tag="after_click"):
    if any(os.environ.get(x) for x in ("ROBLOX_USERNAME","ROBLOX_PASSWORD","CONTROL_PLANE_API_KEY")):
        return {"blocked": "credentials in environment"}
    pmap = {p.info["pid"]: (p.info.get("name") or "").lower() for p in
            psutil.process_iter(attrs=("pid","name"))}
    info = {"tag":tag, "browser_windows":0, "control_types":{},
            "safe_control_labels":[], "window_categories":[],
            "edit_controls":0, "browser_crop_saved":False,
            "window_title_has_roblox":False, "safe_button_labels":[], "edit_input_types":[]}
    labels = set()
    crops = []
    for win in Desktop(backend="uia").windows():
        try:
            if not win.is_visible():
                continue
            exe = pmap.get(win.element_info.process_id, "")
            if exe not in BROWSERS:
                continue
            info["browser_windows"] += 1
            info["window_title_has_roblox"] |= "roblox" in (win.window_text() or "").lower()
            category = "edge" if "edge" in exe else "chrome" if "chrome" in exe else "other_browser"
            info["window_categories"].append(category)
            for c in win.descendants():
                if not c.is_visible():
                    continue
                k = c.element_info.control_type
                if k in ("Button","Edit","Hyperlink","CheckBox","TabItem","Text"):
                    info["control_types"][k] = info["control_types"].get(k,0)+1
                    label=(c.element_info.name or "").strip()
                    if k=="Edit":
                        info["edit_controls"]+=1
                        if re.search(r"username|user name|email|phone|account|사용자|이메일",label,re.I):
                            info["edit_input_types"].append("identifier")
                        elif re.search(r"password|비밀번호",label,re.I):
                            info["edit_input_types"].append("password")
                        else:
                            info["edit_input_types"].append("unlabeled")
                    if k=="Button" and (re.fullmatch(r"[A-Za-z가-힣 ]{2,55}",label)
                        and not re.search(r"account|profile|sync|google|microsoft",label,re.I)):
                        info["safe_button_labels"].append(label)
                    if ALLOWED_TEXT.fullmatch(label):
                        labels.add(f"{k}:{label}")
            # Crop only the client/body below the URL bar.
            rect = wintypes.RECT()
            if user32.GetWindowRect(win.handle, ct.byref(rect)):
                w,h=rect.right-rect.left,rect.bottom-rect.top
                if 550 <= w <= 2500 and 400 <= h <= 1800:
                    crops.append((rect.left,rect.top,rect.right,rect.bottom))
        except Exception:
            continue
    info["safe_control_labels"]=sorted(labels)[:30]
    info["safe_button_labels"]=sorted(set(info["safe_button_labels"]))[:25]
    info["window_categories"]=sorted(info["window_categories"])
    if len(crops)==1:
        try:
            l,t,r,b=crops[0]
            shot=ImageGrab.grab(bbox=(l,max(0,t+120),r,b))
            # On a no-credential test runner only, browser content (not URL bar)
            # can be inspected. Limit output to a single short-lived file.
            out=OUT / f"{tag}_browser_body_only.jpg"
            shot.convert("RGB").save(out,quality=78)
            info["browser_crop_saved"]=True
            info["browser_body_size"]=list(shot.size)
        except Exception as e:
            info["browser_crop_error_kind"]=type(e).__name__
    return info

if __name__=="__main__":
    time.sleep(2)
    print("SAFE_BROWSER_DIAGNOSTICS="+json.dumps(scan(),ensure_ascii=False),flush=True)
