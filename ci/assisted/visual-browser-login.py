"""Guarded DXGI+SendInput bootstrap for Roblox browser-based Studio sign-in.
Secrets come only from GitHub Actions environment; NEVER screenshot or log
pages after credentials are entered. Fails closed on unexpected UI structure.
"""
import os, re, time
import dxcam, numpy as np, psutil
from pywinauto import Desktop
from wgc_sendinput_probe import click_abs, type_unicode, user32

username=os.environ.get("ROBLOX_USERNAME","")
password=os.environ.get("ROBLOX_PASSWORD","")
if not username or not password:
    raise SystemExit("ROBLOX_SECRETS_MISSING")

def windows(exe):
    ids={p.info["pid"] for p in psutil.process_iter(attrs=("pid","name"))
         if (p.info.get("name") or "").lower()==exe}
    result=[]
    for w in Desktop(backend="uia").windows():
        try:
            if w.is_visible() and w.element_info.process_id in ids:
                result.append(w)
        except Exception:
            pass
    return result

def focus_studio(window):
    """Restore the real Studio window; never type/click without HWND match."""
    import ctypes as ct
    hwnd = window.handle
    user32.ShowWindow(hwnd, 9)
    # Temporary topmost activation can resolve focus lock after Edge priming
    # on ephemeral Windows runners. Always remove the topmost flag afterward.
    user32.SetWindowPos.argtypes = [
        ct.c_void_p, ct.c_void_p, ct.c_int, ct.c_int,
        ct.c_int, ct.c_int, ct.c_uint
    ]
    user32.SetWindowPos.restype = ct.c_int
    flags = 0x0001 | 0x0002 | 0x0040  # SWP_NOSIZE|NOMOVE|SHOWWINDOW
    try:
        for attempt in range(3):
            if user32.GetForegroundWindow() == hwnd:
                return True
            try:
                window.set_focus()
            except Exception:
                pass
            user32.SetWindowPos(hwnd, ct.c_void_p(-1), 0, 0, 0, 0, flags)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            if user32.GetForegroundWindow() == hwnd:
                return True
            time.sleep(0.7)
    finally:
        user32.SetWindowPos(hwnd, ct.c_void_p(-2), 0, 0, 0, 0, flags)
    return user32.GetForegroundWindow() == hwnd


def blue_cta():
    wins=windows("robloxstudiobeta.exe")
    if len(wins)!=1: raise SystemExit("STUDIO_WINDOW_NOT_UNIQUE")
    # Same explicit foreground sequence that passed on both Windows
    # 2022 and 2025 credential-free WGC+SendInput diagnostic runners.
    if not focus_studio(wins[0]):
        raise SystemExit("STUDIO_FOCUS_NOT_READY")
    cam=None
    try:
        cam=dxcam.create(backend="dxgi",output_color="RGB",processor_backend="numpy")
        frame=cam.grab(new_frame_only=False)
        if frame is None: raise SystemExit("STUDIO_GRAPHICS_FRAME_UNAVAILABLE")
        img=np.asarray(frame); h,w=img.shape[:2]
        l,t,r,b=int(w*.10),int(h*.28),int(w*.55),int(h*.70)
        roi=img[t:b,l:r,:].astype(np.int16)
        mask=(roi[:,:,2]>=140)&((roi[:,:,2]-roi[:,:,0])>=58)&((roi[:,:,2]-roi[:,:,1])>=46)
        rows=mask.sum(axis=1)
        ranges=[]; start=None
        for i,ok in enumerate(rows>=85):
            if ok and start is None: start=i
            if start is not None and (not ok or i==len(rows)-1):
                end=i if not ok else i+1
                if end-start>=9: ranges.append((start,end))
                start=None
        choices=[]
        for y0,y1 in ranges:
            strip=mask[y0:y1,:]; cols=strip.sum(axis=0)>=max(3,int((y1-y0)*.4))
            xs=np.flatnonzero(cols)
            if xs.size<100: continue
            x0,x1=int(xs[0]),int(xs[-1])+1
            bw,bh=x1-x0,y1-y0
            if 200<=bw<=360 and 25<=bh<=55 and float(strip[:,x0:x1].mean())>=.38:
                choices.append((l+(x0+x1)//2,t+(y0+y1)//2))
        if len(choices)!=1: raise SystemExit("STUDIO_LOGIN_CTA_NOT_UNIQUE")
        x,y=choices[0]; rect=wins[0].rectangle()
        if not(rect.left<=x<rect.right and rect.top<=y<rect.bottom):
            raise SystemExit("STUDIO_LOGIN_CTA_OUTSIDE_STUDIO")
        click_abs(x,y)
        print("STUDIO_WGC_LOGIN_CTA_CLICKED",flush=True)
    finally:
        if cam is not None:
            try: cam.release()
            except Exception: pass

def browser_form():
    seen=[]
    for win in windows("msedge.exe"):
        try:
            if "roblox" not in (win.window_text() or "").lower(): continue
            wr=win.rectangle()
            users=[]; passwords=[]
            for c in win.descendants():
                if not c.is_visible() or c.element_info.control_type!="Edit": continue
                r=c.rectangle(); x=(r.left+r.right)/2; y=(r.top+r.bottom)/2
                if not (wr.left+wr.width()*.18<x<wr.left+wr.width()*.82
                    and wr.top+110<y<wr.top+wr.height()*.83
                    and r.width()>=160 and r.height()>=18):
                    continue
                label=(c.element_info.name or "").strip().lower()
                if re.search(r"username|user name|email|phone|사용자|이메일",label):
                    users.append(c)
                if re.search(r"password|비밀번호",label):
                    passwords.append(c)
            if len(users)!=1 or len(passwords)!=1: continue
            if passwords[0].rectangle().top<=users[0].rectangle().bottom: continue
            seen.append((win,[users[0],passwords[0]]))
        except Exception:
            continue
    return seen[0] if len(seen)==1 else None

def click_center(c):
    rect=c.rectangle()
    click_abs((rect.left+rect.right)//2,(rect.top+rect.bottom)//2)

# Installer may leave the Studio executable running before the welcome UI
# has finished rendering. Retry only non-mutating WGC screenshots; never
# submit any credentials until a unique expected blue CTA is present.
cta_ready=False
for attempt in range(24):
    try:
        blue_cta()
        cta_ready=True
        break
    except SystemExit as exc:
        if str(exc) not in ("STUDIO_WINDOW_NOT_UNIQUE","STUDIO_GRAPHICS_FRAME_UNAVAILABLE",
                            "STUDIO_LOGIN_CTA_NOT_UNIQUE","STUDIO_FOCUS_NOT_READY"):
            raise
        if attempt%5==0:
            print("STUDIO_LOGIN_CTA_PENDING: " + str(exc),flush=True)
        time.sleep(3)
if not cta_ready:
    raise SystemExit("STUDIO_LOGIN_CTA_TIMEOUT: safe visual target never appeared")

deadline=time.monotonic()+70
form=None
while time.monotonic()<deadline:
    form=browser_form()
    if form: break
    time.sleep(2)
if not form: raise SystemExit("ROBLOX_EDGE_TWO_INPUT_FORM_NOT_VERIFIED")
win,edits=form
print("ROBLOX_EDGE_FORM_VERIFIED: unique Roblox-title window and 2 credential input controls.",flush=True)
try: win.set_focus()
except Exception: pass
time.sleep(.5)
click_center(edits[0]);type_unicode(username)
time.sleep(.3)
click_center(edits[1]);type_unicode(password)
time.sleep(.5)
# Require a unique visible submit button below the password field.
buttons=[]
for c in win.descendants():
    try:
        if not c.is_visible() or c.element_info.control_type!="Button": continue
        label=(c.element_info.name or "").strip().lower()
        rect=c.rectangle()
        if (label in ("sign in","log in","login","로그인")
            and rect.top>=edits[1].rectangle().bottom
            and rect.top-edits[1].rectangle().bottom < 180):
            buttons.append(c)
    except Exception: pass
if len(buttons)!=1:
    raise SystemExit("ROBLOX_BROWSER_SUBMIT_NOT_UNIQUE: credentials not submitted")
click_center(buttons[0])
print("ROBLOX_BROWSER_CREDENTIALS_SUBMITTED: official page button clicked, values not logged.",flush=True)
username="";password=""
