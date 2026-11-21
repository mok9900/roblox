"""Opt in the owner's *ephemeral* Studio to its first-party MCP preference.

This is used only on the GitHub-hosted disposable Windows runner, and only
after an official, successful Studio login and isolated local Baseplate edit.
Roblox staff confirmed per-user AssistantSettings JSON has
{"mcp-server":{"enabled":true}}. Do not create Roblox's MCP launcher:
the signed Studio must load this preference and create it itself.

Never print usernames, user IDs, settings JSON, credentials, or paths.
"""
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path


USERS_ENDPOINT = "https://users.roblox.com/v1/usernames/users"


def official_user_id(username, *, urlopen=urllib.request.urlopen):
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        raise ValueError("invalid username syntax (email login is not a public username)")
    payload = json.dumps({"usernames": [username], "excludeBannedUsers": False}).encode()
    req = urllib.request.Request(
        USERS_ENDPOINT, data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=12) as res:
        parsed = json.load(res)
    candidates = parsed.get("data") if isinstance(parsed, dict) else None
    if not isinstance(candidates, list):
        raise ValueError("invalid official API response")
    exact = [
        v for v in candidates
        if isinstance(v, dict) and
        str(v.get("requestedUsername", "")).casefold() == username.casefold()
        and type(v.get("id")) is int and v["id"] > 0
    ]
    if len(exact) != 1:
        raise ValueError("official API did not return a unique requested username")
    return exact[0]["id"]


def update_official_preference(user_id, local_appdata):
    """Only the exact per-account Roblox AssistantSettings file is modified."""
    if type(user_id) is not int or not 0 < user_id < 10**18:
        raise ValueError("unverified Roblox user id")
    if not local_appdata:
        raise ValueError("missing local AppData")
    directory = Path(local_appdata) / "Roblox" / "AssistantSettings"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (str(user_id) + ".json")
    existed = target.is_file()
    config = {}
    if existed:
        if target.stat().st_size > 262144:
            raise ValueError("oversized account settings file")
        config = json.loads(target.read_text(encoding="utf-8-sig"))
        if not isinstance(config, dict):
            raise ValueError("invalid account settings object")
    mcp = config.get("mcp-server", {})
    if not isinstance(mcp, dict):
        raise ValueError("unexpected MCP settings type")
    if mcp.get("enabled") is True:
        return {"settings_file_present": existed, "changed": False, "enabled": True}
    config["mcp-server"] = {**mcp, "enabled": True}

    # Atomic replacement ensures no malformed/partial per-user JSON; keep
    # all other preexisting settings intact. Only this disposable runner.
    handle, tmpname = tempfile.mkstemp(prefix=".assistant-mcp-", suffix=".json",
                                        dir=str(directory))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(config, out, ensure_ascii=False, separators=(",", ":"))
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmpname, target)
    finally:
        if os.path.exists(tmpname):
            os.unlink(tmpname)
    check = json.loads(target.read_text(encoding="utf-8"))
    if check.get("mcp-server", {}).get("enabled") is not True:
        raise ValueError("MCP preference verification failed")
    return {"settings_file_present": existed, "changed": True, "enabled": True}


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("MCP_PREF_SAFE_DIAG: github_hosted_only")
    try:
        user_id = official_user_id(os.environ.get("ROBLOX_USERNAME", ""))
        result = update_official_preference(user_id,
                                            os.environ.get("LOCALAPPDATA", ""))
        print("MCP_PREF_SAFE_DIAG: official_identity_confirmed=true "
              "settings_file_present=%s changed=%s enabled=%s" %
              (str(result["settings_file_present"]).lower(),
               str(result["changed"]).lower(),
               str(result["enabled"]).lower()), flush=True)
    except (ValueError, OSError, TimeoutError, json.JSONDecodeError, KeyError,
            urllib.error.URLError) as exc:
        # Do not output remote API messages or per-user paths.
        print("MCP_PREF_SAFE_DIAG: opt_in_not_applied error_kind=%s" %
              ("invalid_identity_or_settings" if isinstance(exc, (ValueError, KeyError))
               else "unavailable"), flush=True)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
