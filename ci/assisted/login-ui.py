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



def studio_only_controls():
    """Read only genuine Studio-process controls for signed-in state.

    The external Roblox Edge challenge may stay visible after its 2FA has
    succeeded; its residual username/password/challenge UI must not make the
    already-authenticated Studio appear unauthenticated. Never trust browser
    navigation tabs alone as evidence of Studio success.
    """
    pids = {
        p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "robloxstudiobeta.exe"
    }
    out = []
    for win in Desktop(backend="uia").windows():
        try:
            if win.is_visible() and win.element_info.process_id in pids:
                out.extend(c for c in win.descendants() if c.is_visible())
        except Exception:
            continue
    return out


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


def select_challenge_host(edge, studio, mode):
    """Pure selection: only the host which submitted primary credentials.

    Reject ambiguous multi-window and stale-browser states. The calling
    function separately verifies process, visibility and Roblox title.
    """
    if mode == "native" and len(studio) == 1:
        return "studio", studio[0]
    if len(edge) == 1 and (mode == "browser" or not studio):
        return "edge", edge[0]
    return None, None


def challenge_controls():
    """Inspect only the official UI that initiated this login session.

    The previous implementation prioritized ANY Roblox-titled Edge window,
    even after an official native Studio form had submitted the credentials.
    That stale browser page could hide the real email verification controls.
    The shell now tells us which *verified* primary login was submitted, so
    we prefer its corresponding challenge host rather than an unrelated page.
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

    mode = os.environ.get("ROBLOX_LOGIN_MODE", "native")
    source, window = select_challenge_host(edge, studio, mode)
    if window is None:
        return []
    try:
        if source == "studio":
            return [c for c in window.descendants() if c.is_visible()]
        bounds = window.rectangle()
        return [c for c in window.descendants()
                if c.is_visible() and in_browser_content(c.rectangle(), bounds)]
    except Exception:
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


def find_browser_handoff(cs):
    """Select only a unique, explicitly Studio-named browser handoff action.

    A generic Open/Continue/Allow button is NOT acceptable; this protects
    against unrelated browser prompts and unsafe protocol-handler clicks.
    """
    target = re.compile(
        r"^(?:open|launch|return to|back to|continue to|continue in|"
        r"switch to|go to) (?:the )?(?:roblox )?studio(?: app)?$"
        r"|^(?:roblox )?studio(?:를|로|에서|으로)? (?:열기|실행|돌아가기|계속하기)$",
        re.I
    )
    candidates = [c for c in cs
                  if ctype(c) in ("Button", "Hyperlink", "MenuItem")
                  and target.fullmatch(label(c))]
    return candidates[0] if len(candidates) == 1 else None


def find_protocol_consent(cs, title):
    """Match only Edge's explicit Roblox Studio protocol consent dialog.

    A generic Open or Allow button is unsafe by itself. It can be used only
    inside a uniquely identified Edge modal containing Roblox Studio *and*
    an explicit external-app/protocol launch context. No OAuth URL is read.
    """
    names = [label(c) for c in cs if ctype(c) in
             ("Text", "Window", "Pane", "Custom")]
    # Button text such as a generic "Open" is NOT evidence of an external
    # protocol dialog; it must be corroborated by non-action context.
    context = " ".join(n for n in names if len(n) <= 140)
    title = (title or "").strip().lower()
    is_studio = "roblox studio" in context or "roblox studio" in title
    is_external = bool(re.search(
        r"(?:open|launch|external (?:app|application)|associated (?:app|application)|"
        r"protocol|link|앱에서 열기|외부 앱|애플리케이션 실행|열겠습니까)",
        context + " " + title, re.I
    ))
    if not (is_studio and is_external):
        return None
    buttons = [c for c in cs if ctype(c) == "Button"]
    cancel = [c for c in buttons if re.fullmatch(
        r"(?:cancel|취소|not now|don't open)", label(c), re.I)]
    accept = [c for c in buttons if re.fullmatch(
        r"(?:open|open roblox studio|launch roblox studio|"
        r"roblox studio 열기|열기)", label(c), re.I)]
    if len(accept) != 1 or len(cancel) < 1:
        return None
    return accept[0]


def try_browser_studio_handoff():
    """Click at most one explicitly authenticated Studio handoff target.

    Scope to the Edge process and either an official Roblox page or a known
    external protocol dialog. Never read, print, or replay the OAuth callback
    URI (which can contain an authorization code and state token).
    """
    pids = {
        p.info["pid"] for p in psutil.process_iter(attrs=("pid", "name"))
        if (p.info.get("name") or "").lower() == "msedge.exe"
    }
    candidates = []
    roots_seen = 0
    for win in Desktop(backend="uia").windows():
        try:
            if not win.is_visible() or win.element_info.process_id not in pids:
                continue
            title = win.window_text() or ""
            if "roblox" not in title.lower():
                continue
            roots_seen += 1
            cs = [c for c in win.descendants() if c.is_visible()]
            explicit = find_browser_handoff(cs)
            modal = find_protocol_consent(cs, title)
            if explicit is not None and modal is not None and explicit is not modal:
                continue
            button = modal or explicit
            if button is not None:
                candidates.append((button, bool(modal)))
        except Exception:
            continue
    print("STUDIO_HANDOFF_SAFE_DIAG: roblox_edge_windows=%d verified_targets=%d protocol_prompt=%s" %
          (roots_seen, len(candidates), any(m for _, m in candidates)), flush=True)
    if len(candidates) != 1:
        return False
    try:
        button, protocol = candidates[0]
        button.click_input()
        print("STUDIO_BROWSER_HANDOFF_CLICKED: uniquely verified Studio %s action." %
              ("protocol consent" if protocol else "return"), flush=True)
        return True
    except Exception:
        return False

def await_studio(deadline):
    last_diag = 0
    handoff_next_try = time.monotonic() + 4
    handoff_clicked = False
    while time.monotonic() < deadline:
        cs = studio_only_controls()
        if success(cs):
            print("STUDIO_LOGIN_UI_VERIFIED: signed-in Studio-process menu detected.", flush=True)
            return True
        now=time.monotonic()
        if not handoff_clicked and now >= handoff_next_try and now+8 < deadline:
            # The official browser may render its handoff asynchronously.
            # Recheck a handful of times; never click a generic or ambiguous
            # target, and never repeat a successful handoff click.
            handoff_clicked = try_browser_studio_handoff()
            handoff_next_try = now + 9
        if now-last_diag >= 15:
            nav = {label(c) for c in cs if label(c) in NAV}
            auth = sum(1 for c in cs if ctype(c) == "Edit" and
                       re.search(r"password|비밀번호|username|user name|email|이메일|인증 코드|verification code",label(c)))
            challenge = any(CHALLENGE.search(label(c)) for c in cs)
            print("STUDIO_AUTH_SAFE_POLL: studio_controls=%d nav_count=%d auth_edits=%d challenge_ui=%s handoff_clicked=%s" %
                  (len(cs),len(nav),auth,challenge,handoff_clicked),flush=True)
            last_diag=now
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
    credential_edit_labels = [
        label(c) for c in challenge_controls() if ctype(c) == "Edit"
    ]
    prior_login_fields = (
        any(re.search(r"username|user name|사용자 이름", n) for n in credential_edit_labels)
        and any(re.search(r"password|비밀번호", n) for n in credential_edit_labels)
    )
    official_captcha_hint = any(
        re.search(r"captcha|arkose|challenge verification|보안 문자|보안 확인", label(c), re.I)
        for c in challenge_controls()
    )
    print("SAFE_2FA_CONTEXT: primary_form_still_exposed=%s captcha_hint=%s" %
          (prior_login_fields, official_captcha_hint), flush=True)
    print("SAFE_2FA_UI: " + ", ".join(sorted(safe)[:32]), flush=True)
    print("SAFE_2FA_UI_COUNTS: edits=%d menuitems=%d radios=%d listitems=%d buttons=%d texts=%d" % (
        e,kinds.get("MenuItem",0),kinds.get("RadioButton",0),
        kinds.get("ListItem",0),kinds.get("Button",0),kinds.get("Text",0)
    ),flush=True)
    # Diagnostic metadata, deliberately boolean-only. Do not expose free-form
    # text, AutomationIds, window titles, account names or masked emails.
    for i, item in enumerate(
        [x for x in challenge_controls() if ctype(x) in ("MenuItem", "RadioButton", "ListItem")][:8]
    ):
        raw = label(item)
        meta = getattr(item, "element_info", None)
        aid = str(getattr(meta, "automation_id", "") or "").lower()
        hint = str(getattr(meta, "help_text", "") or "").lower()
        try:
            nested = [label(y) for y in item.descendants() if ctype(y) in ("Text", "Button", "Hyperlink")]
        except Exception:
            nested = []
        categories = {
            "passkey": r"passkey|패스키|security key|보안 키",
            "device": r"another device|other device|다른 기기|quick login|빠른 로그인",
            "authenticator": r"authenticator|인증 앱",
            "backup": r"backup|recovery|백업|복구",
            "sms": r"phone|sms|text message|휴대전화|문자",
            "email": r"e-?mail|이메일|(?:\\*|•|·){2,}.{0,30}@",
            "captcha": r"captcha|arkose|보안 확인",
            "one_time_code": r"one.time code|일회용 코드",
        }
        tags = [key for key, phrase in categories.items()
                if re.search(phrase, raw + " " + aid + " " + hint, re.I)]
        print("SAFE_2FA_CHOICE_SHAPE_%d: kind=%s, named=%s, name_email=%s, id_email=%s, help_email=%s, children=%d, child_email=%s, categories=%s" % (
            i,ctype(item),bool(raw),bool(re.search(r"e-?mail|이메일",raw)),
            bool(re.search(r"e-?mail|이메일",aid)),bool(re.search(r"e-?mail|이메일",hint)),
            len(nested),any(bool(re.search(r"e-?mail|이메일",n)) for n in nested),
            ",".join(tags) or "unclassified"),flush=True)


def find_email_method(cs):
    """Find a single visible email method in Roblox's opened 2FA selector.

    Some Windows accessibility trees expose the method name on a nested
    Text control instead of the clickable MenuItem. Never select a generic
    menu item based on its position or an unverified bounding box.
    """
    eligible = ("MenuItem", "RadioButton", "ListItem", "Button", "Hyperlink")
    # Roblox may show a masked destination without spelling out "email".
    # Only a MASKED address inside a Roblox verified challenge may match.
    email = re.compile(
        r"e-?mail|이메일|[a-z0-9._+-]{0,6}(?:\\*|•|·){2,}[a-z0-9._+-]{0,6}"
        r"@[a-z0-9.-]+\\.[a-z]{2,}",
        re.I,
    )
    excluded = re.compile(
        r"settings|change|remove|disable|account recovery|"
        r"설정|변경|삭제|복구", re.I
    )
    matches = []
    for control in cs:
        if ctype(control) not in eligible:
            continue
        name = label(control)
        # UIA sometimes exposes a verification method through AutomationId
        # or HelpText rather than Name. Accept these only for an existing
        # in-page Roblox method control, with the same exclusion rules.
        info = getattr(control, "element_info", None)
        alt = [
            str(getattr(info, "automation_id", "") or "").strip().lower(),
            str(getattr(info, "help_text", "") or "").strip().lower(),
        ]
        # Some official Roblox menus expose a name only through the UIA
        # ValuePattern. Inspect it exclusively as an in-memory category,
        # never print or serialize the value (it could contain masked email).
        try:
            value = str(control.get_value() or "").strip().lower()
            if len(value) <= 120:
                alt.append(value)
        except Exception:
            pass
        if not email.search(name) and any(
            email.search(x) and not excluded.search(x) and len(x) <= 120
            for x in alt
        ):
            name = next(x for x in alt
                        if email.search(x) and not excluded.search(x) and len(x) <= 120)
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
        if success(studio_only_controls()):
            print("STUDIO_LOGIN_UI_VERIFIED_DURING_EMAIL_DISCOVERY", flush=True)
            return True
        cs = challenge_controls()
        if cs and find_code_edit(cs):
            print("EMAIL_DEFAULT_CODE_FORM_FOUND_DURING_DISCOVERY", flush=True)
            return True
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
if success(studio_only_controls()):
    print("STUDIO_LOGIN_PREEXISTING: edit window already authenticated.", flush=True)
    sys.exit(0)
submitted = os.environ.get("ROBLOX_PRIMARY_SUBMITTED") == "1"
if submitted:
    print("ROBLOX_PRIMARY_LOGIN_ALREADY_SUBMITTED: verified %s login GUI stage completed." % os.environ.get("ROBLOX_LOGIN_MODE","unknown"),flush=True)
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

# The account owner has enabled email 2FA. Prefer verified email challenge
# controls *before* treating the second-device approval prompt as primary.
# Roblox can independently require a second-device login confirmation on a
# new/ephemeral Windows runner even with Email 2SV enabled. Do not bypass it.
print("EMAIL_2FA_PRIORITY: checking official email code and method before device approval.", flush=True)
email_selected = choose_email()
if success(studio_only_controls()):
    print("STUDIO_LOGIN_UI_VERIFIED_AFTER_EMAIL_DISCOVERY", flush=True)
    sys.exit(0)

# Roblox can show a second-device approval screen without an Email option
# on certain new-device challenges. Wait for a user-approved official login
# without repeatedly submitting the password or clicking unknown controls.
if not email_selected:
    print("EMAIL_2FA_NOT_OFFERED_BY_CURRENT_CHALLENGE: checking independent device approval.", flush=True)
    deadline = time.monotonic() + 55
    last_notice = 0
    while time.monotonic() < deadline:
        if success(studio_only_controls()):
            print("APP_APPROVAL_SUCCEEDED.", flush=True)
            sys.exit(0)
        page = challenge_controls()
        if find_code_edit(page):
            print("EMAIL_CODE_FORM_READY_AFTER_DEVICE_CHALLENGE", flush=True)
            email_selected = True
            break
        # A delayed official email option can appear after an initial
        # security challenge. Click only if uniquely and explicitly labeled.
        method = find_email_method(page)
        if method is not None:
            try:
                method.click_input()
                print("EMAIL_METHOD_SELECTED_AFTER_DEVICE_CHALLENGE", flush=True)
                email_selected = True
                break
            except Exception:
                pass
        if time.monotonic()-last_notice >= 14:
            print("DEVICE_APPROVAL_PENDING: email option not exposed; official user approval may be required.", flush=True)
            last_notice = time.monotonic()
        time.sleep(2)
if not email_selected:
    if await_studio(time.monotonic() + 8):
        sys.exit(0)
    raise SystemExit("OFFICIAL_EMAIL_CHALLENGE_NOT_OFFERED: no email code field or unique email method; device approval not confirmed")

# Email method selected or code form already present. Never assume a click
# succeeded in delivering mail; the official code input must actually exist.
code_deadline = time.monotonic() + 35
while time.monotonic() < code_deadline:
    if success(studio_only_controls()):
        print("STUDIO_LOGIN_COMPLETED_WHILE_WAITING_FOR_CODE_FORM", flush=True)
        sys.exit(0)
    if find_code_edit(challenge_controls()):
        break
    time.sleep(2)
else:
    raise SystemExit("EMAIL_CODE_FORM_NOT_PRESENT_AFTER_OFFICIAL_CHALLENGE")

print("EMAIL_CODE_FORM_READY: uniquely accessible official Roblox verification input.", flush=True)
print("OTP_RELAY_READY: awaiting per-run RSA-encrypted Gmail verification code.", flush=True)
code = wait_for_code(timeout=540)
enter_code(code)
code = ""
if not await_studio(time.monotonic() + 90):
    raise SystemExit("EMAIL_CODE_SUBMITTED_BUT_STUDIO_LOGIN_NOT_VERIFIED")
print("EMAIL_2FA_STUDIO_LOGIN_SUCCEEDED.", flush=True)
