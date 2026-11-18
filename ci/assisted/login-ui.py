"""
User-authorized Roblox Studio GUI login: app approval first, email-code fallback.

Uses Roblox's own login form and permitted verification methods. Never bypasses
CAPTCHA / authenticator challenges, captures screenshots, prints tokens, or
stores passwords. Email OTP is only received through ephemeral RSA-encrypted
one-time relay scoped to THIS Actions run.
"""
import os
import re
import sys
import time
import subprocess
import psutil
from pywinauto import Desktop

from otp_relay import wait_for_code

USER = os.environ.get("ROBLOX_USERNAME", "")
PASSWORD = os.environ.get("ROBLOX_PASSWORD", "")
if not USER or not PASSWORD:
    raise SystemExit("MISSING_LOGIN_SECRETS")
del os.environ["ROBLOX_PASSWORD"]
del os.environ["ROBLOX_USERNAME"]

EMAIL_CONTROL = re.compile(
    r"(?:email.*(?:code|verif)|(?:code|verif).*email|"
    r"send.*email|^(?:use |choose |send to )?(?:e-?mail|이메일)$|"
    r"이메일.*(?:코드|인증)|(?:코드|인증).*이메일)",
    re.I,
)
OTHER_CONTROL = re.compile(
    r"(?:try|use|choose|select|verify).*?(?:other|another|different).*?(?:method|way|option)"
    r"|more (?:options|ways)|different method|"
    r"다른 (?:방법|수단)|다른 방법으로|다른 인증 수단",
    re.I,
)
CHALLENGE = re.compile(
    r"2-step|two-step|verification|authenticator|"
    r"인증 코드|2단계|captcha|보안 확인|verify your identity|"
    r"approve sign|승인|로그인 시도|다른 방법|another way",
    re.I,
)
EXPIRED = re.compile(r"(?:expired|만료|try again|다시 시도)", re.I)
CODE = re.compile(r"(?:verification code|email code|enter code|security code|"
                  r"6.digit|one.time code|인증 코드|이메일 코드|코드 입력)", re.I)
VERIFY = re.compile(r"^(?:verify|confirm|continue|submit|next|인증|확인|계속|다음)$", re.I)
LOGIN = re.compile(r"^(?:log in|login|sign in|로그인)$", re.I)
NAV = frozenset(("file", "view", "test", "model", "파일", "보기", "테스트", "모델"))


def windows():
    # Follow both Roblox Studio and the authorized official Edge browser.
    # UI names are never used as sources of credential values or arbitrary
    # secrets. Edge may change its title after a 2FA method menu opens.
    result = []
    process_names = {
        p.info["pid"]: (p.info.get("name") or "").lower()
        for p in psutil.process_iter(attrs=("pid", "name"))
    }
    for win in Desktop(backend="uia").windows():
        try:
            if not win.is_visible():
                continue
            exe = process_names.get(win.element_info.process_id, "")
            if exe in ("robloxstudiobeta.exe", "msedge.exe"):
                result.append(win)
        except Exception:
            pass
    return result


def controls():
    out = []
    for win in windows():
        try:
            out.extend(c for c in win.descendants() if c.is_visible())
        except Exception:
            continue
    return out


def label(control):
    try:
        return (control.element_info.name or "").strip().lower()
    except Exception:
        return ""


def ctype(control):
    try:
        return control.element_info.control_type
    except Exception:
        return None


def in_browser_content(control_rect, window_rect):
    """Exclude browser chrome, address bar and toolbar from Roblox challenge."""
    try:
        cx = (control_rect.left + control_rect.right) / 2
        cy = (control_rect.top + control_rect.bottom) / 2
        return (
            window_rect.left + 25 < cx < window_rect.right - 25
            and window_rect.top + 125 < cy < window_rect.bottom - 25
            and control_rect.right > control_rect.left
            and control_rect.bottom > control_rect.top
        )
    except Exception:
        return False


def challenge_controls():
    """Inspect Roblox Edge page or a single official native Studio window.

    Browser chrome is excluded by geometry. Native Studio may use a built-in
    email-code challenge instead of a separate Edge verification page.
    """
    pmap = {p.info["pid"]: (p.info.get("name") or "").lower()
            for p in psutil.process_iter(attrs=("pid", "name"))}
    edge = []
    studio = []
    for window in Desktop(backend="uia").windows():
        try:
            if not window.is_visible():
                continue
            exe = pmap.get(window.element_info.process_id, "")
            if exe == "msedge.exe" and "roblox" in (window.window_text() or "").lower():
                edge.append(window)
            if exe == "robloxstudiobeta.exe":
                studio.append(window)
        except Exception:
            pass
    if len(edge) == 1:
        try:
            bounds = edge[0].rectangle()
            return [c for c in edge[0].descendants()
                    if c.is_visible() and in_browser_content(c.rectangle(), bounds)]
        except Exception:
            return []
    if len(edge) > 1:
        return []
    if len(studio) == 1:
        try:
            return [c for c in studio[0].descendants() if c.is_visible()]
        except Exception:
            return []
    return []


def success(cs):
    names = [label(c) for c in cs]
    nav = any(n in NAV for n in names)
    auth_fields = any(ctype(c) == "Edit" and
                      re.search(r"password|비밀번호|username|user name|email|이메일|인증 코드|verification code", label(c))
                      for c in cs)
    still_challenged = any(CHALLENGE.search(n) for n in names)
    return nav and not auth_fields and not still_challenged


def find_button(cs, pattern):
    allowed = ("Button", "Hyperlink", "MenuItem", "RadioButton", "TabItem", "ListItem", "Text", "Custom")
    for typ in allowed:
        matches = [c for c in cs if ctype(c) == typ and pattern.search(label(c))]
        if len(matches) == 1:
            return matches[0]
    return None


def click_button(cs, pattern):
    b = find_button(cs, pattern)
    if b is None:
        return False
    try:
        b.click_input()
        return True
    except Exception:
        return False


def await_studio(deadline):
    while time.monotonic() < deadline:
        cs = controls()
        if success(cs):
            print("STUDIO_LOGIN_UI_VERIFIED: signed-in Studio menu detected.", flush=True)
            return True
        time.sleep(2)
    return False


def find_code_edit(cs):
    edits = [c for c in cs if ctype(c) == "Edit"]
    candidates = [c for c in edits if CODE.search(label(c))]
    if len(candidates) == 1:
        return [candidates[0]]
    # A verification-only dialog can have a single unnamed code entry field.
    if len(edits) == 1 and not any(
        re.search(r"username|password|email|비밀번호|이메일|사용자", label(c))
        for c in edits
    ):
        return edits
    if len(candidates) in (6, 8):
        return candidates
    # Roblox's Edge challenge sometimes leaves its prior username/password
    # Edit controls in the accessibility tree alongside one UNNAMED OTP
    # input. Only accept that third field if the two credential controls are
    # explicitly identified, an official Verify button is visible, and no
    # other ambiguous edits exist. Never guess coordinates or input order.
    if len(edits) == 3 and any(
        ctype(c) == "Button" and VERIFY.fullmatch(label(c)) for c in cs
    ):
        users = [c for c in edits if re.fullmatch(
            r"(?:username|user name|username, email, or phone|email|사용자 이름|이메일)", label(c), re.I)]
        passwords = [c for c in edits if re.fullmatch(r"(?:password|비밀번호)", label(c), re.I)]
        if len(users) == len(passwords) == 1 and users[0] is not passwords[0]:
            others = [c for c in edits if c is not users[0] and c is not passwords[0]]
            if len(others) == 1 and not label(others[0]):
                print("EMAIL_CODE_FORM_STRUCTURAL_MATCH: one unlabeled code edit plus two recognized credential edits.",flush=True)
                return others
    return []


def enter_code(code):
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        # Use only the isolated official Roblox challenge window, never
        # the union of unrelated Studio/Edge windows.
        cs = challenge_controls()
        edits = find_code_edit(cs)
        if len(edits) == 1:
            edits[0].set_edit_text(code)
            if not click_button(challenge_controls(), VERIFY):
                # Certain official Roblox forms submit automatically on all digits.
                print("EMAIL_CODE_ENTERED: awaiting auto-submit or form validation.", flush=True)
            else:
                print("EMAIL_CODE_ENTERED: official Verify button clicked.", flush=True)
            return
        if len(edits) == len(code):
            for field, digit in zip(edits, code):
                field.set_edit_text(digit)
            click_button(challenge_controls(), VERIFY)
            print("EMAIL_CODE_ENTERED: code digits entered into official verification form.", flush=True)
            return
        time.sleep(2)
    raise SystemExit("EMAIL_CODE_INPUT_NOT_ACCESSIBLE: no unique verification code field")


def safe_choice_diagnostics():
    # Only exact, non-identifying Roblox 2FA control names and aggregate
    # counts. Never print browser URLs, window captions, account data,
    # email addresses, one-time codes or free-form page text.
    phrases = re.compile(
        r"^(?:more options|other options|other methods|other verification methods|"
        r"try another method|try another way|use another method|"
        r"choose another way to verify|choose another verification method|"
        r"email|email code|email me a code|send code to email|"
        r"send code via email|send email|email verification|"
        r"verify with email|verify through email|use email|"
        r"authenticator app|approve on another device|"
        r"backup code|recovery code|two.step verification|"
        r"verify|continue|cancel|back|other|"
        r"다른 방법|다른 인증 수단|다른 방법으로 인증|이메일|"
        r"이메일로 코드 보내기|이메일 인증|인증 앱|백업 코드|"
        r"계속|확인|취소)$", re.I
    )
    safe = set()
    kinds = {}
    e = 0
    for c in challenge_controls():
        typ = ctype(c)
        if typ in ("Button","Hyperlink","MenuItem","RadioButton","TabItem","ListItem","Text","Custom"):
            kinds[typ] = kinds.get(typ, 0) + 1
            n = label(c)
            if phrases.fullmatch(n):
                safe.add(f"{typ}:{n}")
        elif typ == "Edit":
            e += 1
    print("SAFE_2FA_UI: " + ", ".join(sorted(safe)[:32]), flush=True)
    print("SAFE_2FA_UI_COUNTS: edits=%d menuitems=%d radios=%d listitems=%d buttons=%d texts=%d" % (
        e,kinds.get("MenuItem",0),kinds.get("RadioButton",0),
        kinds.get("ListItem",0),kinds.get("Button",0),kinds.get("Text",0)
    ),flush=True)


def find_email_method(cs):
    """Find a single visible email method in Roblox's opened 2FA selector.

    Some Windows accessibility trees expose the method name on a nested
    Text control instead of the clickable MenuItem. Never select a generic
    menu item based on its position or an unverified bounding box.
    """
    eligible = ("MenuItem", "RadioButton", "ListItem", "Button", "Hyperlink")
    email = re.compile(r"e-?mail|이메일", re.I)
    excluded = re.compile(
        r"settings|change|remove|disable|account recovery|"
        r"설정|변경|삭제|복구", re.I
    )
    matches = []
    for control in cs:
        if ctype(control) not in eligible:
            continue
        name = label(control)
        if not name:
            try:
                names = [
                    label(child) for child in control.descendants()
                    if ctype(child) in ("Text", "Button", "Hyperlink")
                ]
                names = [n for n in names if n and len(n) <= 120]
                if len([n for n in names if email.search(n) and not excluded.search(n)]) == 1:
                    name = next(n for n in names if email.search(n) and not excluded.search(n))
            except Exception:
                continue
        if not name or len(name) > 120:
            continue
        if email.search(name) and not excluded.search(name):
            matches.append(control)
    if len(matches) == 1:
        return matches[0]
    # Roblox's native selector represents the SAME Email choice as a
    # clickable Button nested within a ListItem. Treat exactly this pair
    # as one choice; unrelated/ambiguous email options still fail closed.
    if len(matches) == 2:
        types = {ctype(c) for c in matches}
        names = {label(c) for c in matches}
        if types == {"Button", "ListItem"} and names == {"email"}:
            return next(c for c in matches if ctype(c) == "Button")
    return None


def choose_email():
    """Use official Roblox email 2FA choice, never Edge's toolbar menu."""
    alternatives_opened = False
    for stage in range(16):
        cs = challenge_controls()
        if not cs:
            if stage % 4 == 0:
                print("ROBLOX_2FA_PAGE_NOT_ACCESSIBLE: browser content not ready.", flush=True)
            time.sleep(2)
            continue

        method = find_email_method(cs)
        if method is not None:
            try:
                method.click_input()
                print("EMAIL_METHOD_SELECTED: uniquely labeled Roblox challenge item.", flush=True)
                time.sleep(3)
                return True
            except Exception:
                pass

        # Only use an explicitly labeled, in-page Roblox verification control.
        # Generic Microsoft Edge 'More options' is outside challenge_controls().
        if not alternatives_opened:
            other = find_button(cs, OTHER_CONTROL)
            if other is not None:
                try:
                    other.click_input()
                    alternatives_opened = True
                    print("ROBLOX_2FA_PAGE_ALTERNATIVES_OPENED.", flush=True)
                    time.sleep(3)
                    safe_choice_diagnostics()
                except Exception:
                    pass
        time.sleep(2)
    safe_choice_diagnostics()
    return False


def submit_primary_login():
    began = time.monotonic()
    deadline = began + 120
    relaunched = False
    last_diag = began
    while time.monotonic() < deadline:
        cs = controls()
        if time.monotonic() - last_diag > 18:
            print("LOGIN_UI_DIAG: visible_windows=%d edit_fields=%d login_buttons=%d" % (
                len(windows()),
                sum(1 for c in cs if ctype(c) == "Edit"),
                sum(1 for c in cs if ctype(c) == "Button" and LOGIN.fullmatch(label(c))),
            ), flush=True)
            last_diag = time.monotonic()
        if not relaunched and time.monotonic() - began > 25:
            exe = os.environ.get("STUDIO_EXE")
            if exe:
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("LOGIN_GUI_RELAUNCH: explicit Studio launch attempted.", flush=True)
            relaunched = True
        # Use one official login window at a time. A second Studio window may
        # have an independent WebView2 form and must not make the field count ambiguous.
        for win in windows():
            try:
                panel = [x for x in win.descendants() if x.is_visible()]
            except Exception:
                continue
            edits = [x for x in panel if ctype(x) == "Edit"]
            user_fields = [x for x in edits if re.search(r"username|email|phone|사용자 이름|이메일", label(x))]
            pw_fields = [x for x in edits if re.search(r"password|비밀번호", label(x))]
            btn = find_button(panel, LOGIN)
            if len(user_fields) == len(pw_fields) == 1 and btn is not None:
                user_fields[0].set_edit_text(USER)
                pw_fields[0].set_edit_text(PASSWORD)
                btn.click_input()
                print("ROBLOX_LOGIN_SUBMITTED: official GUI form submitted.", flush=True)
                return True
        time.sleep(2)
    return False


print("Studio GUI: beginning official Roblox sign-in.", flush=True)
if success(controls()):
    print("STUDIO_LOGIN_PREEXISTING: edit window already authenticated.", flush=True)
    sys.exit(0)
submitted = os.environ.get("ROBLOX_PRIMARY_SUBMITTED") == "1"
if submitted:
    print("ROBLOX_PRIMARY_LOGIN_ALREADY_SUBMITTED: browser WGC/SendInput stage completed.",flush=True)
else:
    submitted = submit_primary_login()
USER = ""
PASSWORD = ""
if not submitted:
    raise SystemExit("LOGIN_CONTROLS_NOT_ACCESSIBLE")

# If email verification is configured as the default 2FA method, Roblox may
# present the code form immediately, without a mobile-app approval challenge.
# Use only a Roblox-titled Edge document (not browser chrome or a generic Edit).
page = challenge_controls()
if page and find_code_edit(page):
    print("EMAIL_CODE_FORM_READY: default official Roblox code form detected.", flush=True)
    print("OTP_RELAY_READY: encrypted run-bound email code is required.", flush=True)
    code = wait_for_code(timeout=540)
    enter_code(code)
    code = ""
    if not await_studio(time.monotonic() + 75):
        raise SystemExit("EMAIL_CODE_SUBMITTED_BUT_LOGIN_NOT_VERIFIED")
    print("EMAIL_DEFAULT_METHOD_SUCCEEDED.", flush=True)
    sys.exit(0)

print("APP_APPROVAL_PENDING: open Roblox mobile app NOW and approve this sign-in promptly.", flush=True)
start = time.monotonic()
app_deadline = start + 50
challenge_detected = False
notice_time = 0
while time.monotonic() < app_deadline:
    cs = controls()
    if success(cs):
        print("APP_APPROVAL_SUCCEEDED.", flush=True)
        sys.exit(0)
    labels = [label(c) for c in cs]
    challenge_detected = challenge_detected or any(CHALLENGE.search(n) for n in labels)
    if challenge_detected and time.monotonic() - notice_time > 12:
        print("APP_APPROVAL_STILL_PENDING: approve through the Roblox app before the request expires.", flush=True)
        notice_time = time.monotonic()
    if any(EXPIRED.search(n) for n in labels):
        print("APP_APPROVAL_EXPIRED: attempting official email alternative.", flush=True)
        break
    time.sleep(2)

if not challenge_detected:
    # No recognized 2FA screen: don't click unknown controls.
    if await_studio(time.monotonic() + 10):
        sys.exit(0)
    raise SystemExit("VERIFICATION_SCREEN_NOT_RECOGNIZED")

if await_studio(time.monotonic() + 3):
    sys.exit(0)

print("APP_APPROVAL_NOT_CONFIRMED: checking official Roblox code form before opening alternatives.", flush=True)
if find_code_edit(challenge_controls()):
    print("EMAIL_CODE_FORM_READY: an existing official challenge input is uniquely identified.",flush=True)
else:
    if not choose_email():
        raise SystemExit("EMAIL_METHOD_UNAVAILABLE: email option not accessible in Roblox challenge")

print("EMAIL_METHOD_SELECTED: checking whether Roblox actually displayed an OTP input.", flush=True)
code_form_deadline = time.monotonic() + 30
while time.monotonic() < code_form_deadline:
    if find_code_edit(challenge_controls()):
        break
    time.sleep(2)
else:
    raise SystemExit("EMAIL_OTP_INPUT_NOT_PRESENT: the selected email action may be address verification instead of an OTP challenge")

print("EMAIL_CODE_FORM_READY: a verification-code input is accessible.", flush=True)
print("OTP_RELAY_READY: encrypted one-time code can be delivered through run-bound GitHub relay.", flush=True)
code = wait_for_code(timeout=540)
enter_code(code)
code = ""  # do not retain code longer than needed

if not await_studio(time.monotonic() + 75):
    raise SystemExit("EMAIL_CODE_SUBMITTED_BUT_LOGIN_NOT_VERIFIED")

print("EMAIL_FALLBACK_SUCCEEDED.", flush=True)
