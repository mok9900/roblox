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

def verified_browser_url(win):
    """Return the exact unique official URL in memory; never log it."""
    from urllib.parse import urlsplit
    found=set()
    for c in win.descendants(control_type="Edit"):
        try:
            label=(c.element_info.name or "").strip().casefold()
            if not c.is_visible() or not any(t in label for t in ("address and search","address bar","주소 및 검색","주소 표시줄")):
                continue
            value=str(c.get_value()).strip()
            if not value.startswith("https://"):
                continue
            u=urlsplit(value)
            if u.scheme=="https" and u.hostname in {"roblox.com","www.roblox.com","auth.roblox.com"} and not u.username and not u.password and u.port in (None,443):
                found.add(value)
        except Exception:
            continue
    return next(iter(found)) if len(found)==1 else None

def verified_browser_origin(win):
    return verified_browser_url(win) is not None

def fresh_form(hwnd,expected_url,require_enabled=False,allow_refocus=False):
    """Never use stale UIA elements or switch to another window or URL."""
    form=browser_form()
    if not form:
        return None
    win,edits=form
    if win.handle!=hwnd or not expected_url or verified_browser_url(win)!=expected_url:
        return None
    target,_,_=submit_target(win,edits[1],require_enabled=require_enabled)
    if target is None:
        return None
    if user32.GetForegroundWindow()!=hwnd:
        if not allow_refocus or not focus_studio(win):
            return None
        # Activation may have changed the document. Resolve it again.
        return fresh_form(hwnd,expected_url,require_enabled,False)
    if verified_browser_url(win)!=expected_url or user32.GetForegroundWindow()!=hwnd:
        return None
    return win,edits,target


def submit_target(win, password_edit, require_enabled=False):
    """Deduplicate identical UIA wrappers, require a single aligned submit target."""
    p=password_edit.rectangle()
    candidates={}
    labels=0
    for c in win.descendants():
        try:
            if not c.is_visible() or c.element_info.control_type!="Button":
                continue
            label=(c.element_info.name or "").strip().casefold()
            if label not in ("sign in","log in","login","로그인"):
                continue
            labels+=1
            r=c.rectangle()
            overlap=max(0,min(r.right,p.right)-max(r.left,p.left))
            if not (r.top>=p.bottom-2 and r.top-p.bottom<180 and r.height()>=18 and r.width()>=80 and overlap>=min(r.width(),p.width())*.75):
                continue
            if require_enabled and not c.is_enabled():
                continue
            key=(r.left,r.top,r.right,r.bottom)
            candidates[key]=c
        except Exception:
            continue
    return (next(iter(candidates.values())) if len(candidates)==1 else None,labels,len(candidates))

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
    # Exit 10 means no Roblox credentials were typed or submitted. The caller
    # may safely restart Studio once and retry GUI discovery, never blind input.
    print("STUDIO_LOGIN_CTA_TIMEOUT: safe visual target never appeared", flush=True)
    raise SystemExit(10)

deadline=time.monotonic()+70
form=None
while time.monotonic()<deadline:
    form=browser_form()
    if form: break
    time.sleep(2)
if not form: raise SystemExit("ROBLOX_EDGE_TWO_INPUT_FORM_NOT_VERIFIED")
win,edits=form
# No credentials until origin, foreground, and one physical submit target
# have all been independently checked. UIA can duplicate the same rectangle.
deadline=time.monotonic()+25
target=None
while time.monotonic()<deadline:
    form=browser_form()
    if form:
        win,edits=form
        if verified_browser_origin(win):
            target,labels,unique=submit_target(win,edits[1])
            print(f"ROBLOX_BROWSER_SUBMIT_SAFE_DIAG: labeled={labels} physical_targets={unique}",flush=True)
            if target is not None:
                break
    time.sleep(2)
if target is None:
    raise SystemExit("ROBLOX_BROWSER_ORIGIN_OR_SUBMIT_UNVERIFIED: no credentials typed")
if not focus_studio(win) or not verified_browser_origin(win):
    raise SystemExit("ROBLOX_BROWSER_FOCUS_OR_ORIGIN_UNVERIFIED: no credentials typed")
expected_url=verified_browser_url(win)
hwnd=win.handle
current=fresh_form(hwnd,expected_url)
if current is None:
    raise SystemExit("ROBLOX_BROWSER_FORM_CHANGED: no credentials typed")
print("ROBLOX_EDGE_FORM_VERIFIED: official HTTPS origin and unique credential form and submit target.",flush=True)
win,edits,_=current
click_center(edits[0])
if user32.GetForegroundWindow()!=hwnd or verified_browser_url(win)!=expected_url or not edits[0].has_keyboard_focus():
    raise SystemExit("ROBLOX_BROWSER_USERNAME_FOCUS_UNVERIFIED: no credentials typed")
type_unicode(username)
time.sleep(.3)
current=fresh_form(hwnd,expected_url)
if current is None:
    raise SystemExit("ROBLOX_BROWSER_FORM_CHANGED: no password typed")
win,edits,_=current
click_center(edits[1])
if user32.GetForegroundWindow()!=hwnd or verified_browser_url(win)!=expected_url or not edits[1].has_keyboard_focus():
    raise SystemExit("ROBLOX_BROWSER_PASSWORD_FOCUS_UNVERIFIED: no password typed")
type_unicode(password)
time.sleep(.5)
# No more credential input. Allow a transient focus/UIA refresh, but never
# submit after a URL or window change. At most one guarded reactivation.
deadline=time.monotonic()+15
current=None
refocus_used=False
while time.monotonic()<deadline:
    if user32.GetForegroundWindow()!=hwnd and not refocus_used:
        form=browser_form()
        if form and form[0].handle==hwnd and verified_browser_url(form[0])==expected_url:
            refocus_used=True
            current=fresh_form(hwnd,expected_url,True,True)
    else:
        current=fresh_form(hwnd,expected_url,True)
    if current is not None:
        break
    time.sleep(.5)
if current is None:
    raise SystemExit("ROBLOX_BROWSER_FOCUS_OR_ORIGIN_CHANGED: no submit")
win,edits,target=current
if user32.GetForegroundWindow()!=hwnd or verified_browser_url(win)!=expected_url:
    raise SystemExit("ROBLOX_BROWSER_FINAL_GUARD_FAILED: no submit")
click_center(target)
print("ROBLOX_BROWSER_CREDENTIALS_SUBMITTED: official page button clicked, values not logged.",flush=True)
username="";password=""
