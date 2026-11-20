"""Optional Github-hosted Roblox email 2FA via official Gmail REST/OAuth.

Gmail permission stays in GitHub Actions secrets and is used only after a
verified official Roblox email-code challenge is visible. Never log/persist
Gmail contents, OAuth credentials, or an OTP. This does not bypass Roblox
authentication; it merely reads the user-authorized official email.
"""
from __future__ import annotations

import base64
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parseaddr

REQUIRED = ("GMAIL_OAUTH_CLIENT_ID", "GMAIL_OAUTH_CLIENT_SECRET",
            "GMAIL_OAUTH_REFRESH_TOKEN")
TOKEN_URL = "https://oauth2.googleapis.com/token"
MAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
SENDER = "accounts@roblox.com"

# Limit extraction to official Roblox security-code language; a random six
# digit number elsewhere in a message must not be considered an OTP.
CODE = re.compile(
    r"(?:2단계\s*인증\s*코드(?:는|가|:)?|"
    r"(?:one[- ]time|2[- ]step|two[- ]step|verification|security)\s*code\s*(?:is|:)?|"
    r"인증\s*코드(?:는|가|:)?)\s*[:：]?\s*(\d{6})\b",
    re.I,
)


def configured():
    present = [bool(os.environ.get(n)) for n in REQUIRED]
    if any(present) and not all(present):
        raise RuntimeError("GMAIL_OAUTH_SECRETS_INCOMPLETE")
    return all(present)


def _json_request(url, *, token=None, form=None):
    data = (urllib.parse.urlencode(form).encode("ascii")
            if form is not None else None)
    headers = {"Accept": "application/json",
               "User-Agent": "Roblox-2FA-GitHub-hosted/1.0"}
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers, data=data)
    try:
        with urllib.request.urlopen(request, timeout=18) as res:
            return json.load(res)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GMAIL_OAUTH_OR_API_HTTP_%d" % exc.code) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("GMAIL_OAUTH_OR_API_NETWORK_UNAVAILABLE") from None


def _access_token():
    response = _json_request(
        TOKEN_URL,
        form={
            "grant_type": "refresh_token",
            "client_id": os.environ["GMAIL_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["GMAIL_OAUTH_CLIENT_SECRET"],
            "refresh_token": os.environ["GMAIL_OAUTH_REFRESH_TOKEN"],
        },
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("GMAIL_OAUTH_ACCESS_TOKEN_UNAVAILABLE")
    return token


def _decode_part(part):
    raw = (part.get("body") or {}).get("data")
    if raw:
        try:
            decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            text = decoded.decode("utf-8", errors="replace")
            if part.get("mimeType", "").lower() == "text/html":
                text = html.unescape(re.sub(r"<[^>]*>", " ", text))
            return text
        except (ValueError, TypeError):
            return ""
    return ""


def _message_text(payload):
    items = []
    pending = [payload]
    while pending and len(items) < 24:
        p = pending.pop()
        if not isinstance(p, dict):
            continue
        if p.get("mimeType", "").lower() in ("text/plain", "text/html", ""):
            items.append(_decode_part(p))
        pending.extend(p.get("parts") or [])
    return " ".join(items)


def extract_code(msg, *, earliest_epoch, now_epoch):
    """Return fresh, from-verified Roblox 2FA code or None. No side effects."""
    if not isinstance(msg, dict):
        return None
    headers = {
        str(h.get("name", "")).lower(): str(h.get("value", ""))
        for h in (msg.get("payload") or {}).get("headers", [])
        if isinstance(h, dict)
    }
    if parseaddr(headers.get("from", ""))[1].lower() != SENDER:
        return None
    try:
        arrived = int(msg.get("internalDate", "0")) / 1000
    except (ValueError, TypeError):
        return None
    # A code can arrive moments before the form becomes accessible.
    # Reject old mail from previous hosted runners and impossible future mail.
    if not earliest_epoch - 120 <= arrived <= now_epoch + 15:
        return None
    if now_epoch - arrived > 600:
        return None
    content = _message_text(msg.get("payload") or {})
    if not content:
        content = str(msg.get("snippet") or "")
    match = CODE.search(content)
    return match.group(1) if match else None


def wait_gmail_code(timeout=540, *, sleep=time.sleep):
    """Poll newest matching Gmail messages after official 2FA challenge."""
    if not configured():
        raise RuntimeError("GMAIL_OAUTH_NOT_CONFIGURED")
    token = _access_token()
    started = time.time()
    deadline = time.monotonic() + timeout
    print("GMAIL_2FA_POLL_STARTED: official OAuth readonly mailbox, code redacted.", flush=True)
    while time.monotonic() < deadline:
        try:
            search = urllib.parse.urlencode({
                "q": "from:accounts@roblox.com after:%d" % int(started - 180),
                "maxResults": "8",
            })
            listing = _json_request(MAIL_URL + "?" + search, token=token)
            candidates = []
            for entry in listing.get("messages") or []:
                id_ = entry.get("id")
                # Gmail IDs are opaque lower-case hex-like identifiers.
                if not isinstance(id_, str) or not re.fullmatch(r"[a-fA-F0-9]{8,40}", id_):
                    continue
                msg = _json_request(MAIL_URL + "/" + id_ + "?format=full", token=token)
                code = extract_code(msg, earliest_epoch=started,
                                    now_epoch=time.time())
                if code is not None:
                    candidates.append((int(msg["internalDate"]), code))
            if candidates:
                # Newest eligible official mail is the relevant challenge.
                candidates.sort(reverse=True)
                print("GMAIL_2FA_FRESH_CODE_READY: official Roblox email, values redacted.", flush=True)
                return candidates[0][1]
        except RuntimeError as exc:
            # Authentication failures are persistent configuration problems,
            # not a reason to keep hammering Gmail's API.
            if "HTTP_400" in str(exc) or "HTTP_401" in str(exc) or "HTTP_403" in str(exc):
                raise
            print("GMAIL_2FA_RETRY: transient API/network condition.", flush=True)
        sleep(10)
    raise TimeoutError("GMAIL_2FA_TIMEOUT: no fresh official Roblox email")
