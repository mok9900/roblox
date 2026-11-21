"""Privacy-safe, read-only check for Roblox Studio's built-in Assistant asset.

The OTA location can be absent when Studio ships a built-in plugin from
its signed version directory. We check BOTH known roots before diagnosing
a missing assistant. Never output paths, logs, contents, or account data.
"""
import os
import re
from pathlib import Path


def inspect_assets(studio_exe: str, local_appdata: str, *, max_logs: int = 6):
    studio_dir = Path(studio_exe).parent
    local = Path(local_appdata) / "Roblox"
    ota = local / "OTAPlugins"
    def contains_assistant(root: Path):
        if not root.is_dir():
            return False
        try:
            # Scanning only the official Roblox root is bounded; no user
            # documents, installed third-party plugins, or arbitrary files.
            return any(x.is_file() for x in root.rglob("Assistant.rbxm"))
        except (OSError, PermissionError):
            return False

    ota_present = contains_assistant(ota)
    version_present = contains_assistant(studio_dir)
    logdir = local / "logs"
    files = []
    if logdir.is_dir():
        try:
            files = sorted(
                (p for p in logdir.glob("*.log") if p.is_file()),
                key=lambda p: p.stat().st_mtime, reverse=True
            )[:max_logs]
        except (OSError, PermissionError):
            files = []
    load_failed = False
    load_mentioned = False
    for file in files:
        try:
            # Restrict to the tail; older startup logs are irrelevant.
            with file.open("rb") as stream:
                stream.seek(0, 2)
                length = stream.tell()
                stream.seek(max(0, length - 262144))
                tail = stream.read(262144).decode("utf-8", "replace")
            for line in tail.splitlines():
                if "Assistant.rbxm" not in line:
                    continue
                load_mentioned = True
                if re.search(r"Failed to load plugin", line, re.I):
                    load_failed = True
        except (OSError, PermissionError):
            continue
    return {
        "ota_present": ota_present,
        "version_present": version_present,
        "load_failure_logged": load_failed,
        "assistant_log_seen": load_mentioned,
        "logs_examined": len(files),
    }


def main():
    info = inspect_assets(os.environ.get("STUDIO_EXE", ""),
                          os.environ.get("LOCALAPPDATA", ""))
    print("MCP_ASSISTANT_ASSET_SAFE_DIAG: " +
          " ".join(f"{k}={str(v).lower() if isinstance(v,bool) else v}"
                   for k, v in info.items()), flush=True)


if __name__ == "__main__":
    main()
