"""
Ephemeral RSA-OAEP-SHA256 relay for a user-authorized Roblox email sign-in code.

Private key never leaves the GitHub Actions runner. Public key is uploaded as an
Actions artifact while the job runs. Only a recipient-encrypted, run-bound code
is committed to the public repository. Never log the code or encrypted payload.
"""
import base64
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

REPO = "mok9900/roblox"
BRANCH = "feature/studio-openai-tunnel-assisted"


def key_path():
    return Path(os.environ["RUNNER_TEMP"]) / "roblox-otp-relay-private.pem"


def generate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    key_path().write_bytes(private)
    os.chmod(key_path(), 0o600)
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_file = Path(os.environ["GITHUB_WORKSPACE"]) / "ci" / "assisted" / ".runtime" / "otp-public.pem"
    public_file.parent.mkdir(parents=True, exist_ok=True)
    public_file.write_bytes(public)
    print("OTP_RELAY_PUBLIC_KEY_READY: run-bound, one-time RSA key.", flush=True)


def fetch_ciphertext(run_id):
    path = f"ci/assisted/otp-relay/otp-{run_id}.txt"
    url = (
        f"https://api.github.com/repos/{REPO}/contents/"
        f"{path}?ref={urllib.parse.quote(BRANCH, safe='')}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "roblox-studio-assisted-otp-relay",
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "Cache-Control": "no-cache",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=12) as resp:
            import json
            data = json.load(resp)
            encoded = base64.b64decode(data["content"])
            if len(encoded) > 4096:
                raise ValueError("Encrypted relay payload too long")
            return encoded.decode("ascii").strip()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def wait_for_code(timeout=540):
    run_id = os.environ["GITHUB_RUN_ID"]
    private_bytes = key_path().read_bytes()
    key = serialization.load_pem_private_key(private_bytes, password=None)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            blob = fetch_ciphertext(run_id)
            if blob:
                ciphertext = base64.b64decode(blob, validate=True)
                plain = key.decrypt(
                    ciphertext,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None,
                    ),
                ).decode("ascii")
                prefix = f"{run_id}:"
                if not plain.startswith(prefix):
                    raise ValueError("OTP relay run ID mismatch")
                code = plain[len(prefix):]
                if not re.fullmatch(r"\d{4,10}", code):
                    raise ValueError("Invalid OTP shape")
                print("OTP_RELAY_RECEIVED: encrypted one-time email code, run ID verified.", flush=True)
                return code
        except (ValueError, UnicodeError) as exc:
            # Never log values. A malformed payload is not trusted.
            raise RuntimeError("OTP_RELAY_INVALID_CIPHERTEXT") from exc
        except Exception as exc:
            # Transient GitHub API errors: do not log response bodies.
            print("OTP_RELAY_POLL_RETRY: transient API issue.", flush=True)
        time.sleep(10)
    raise TimeoutError("OTP_RELAY_TIMEOUT: no encrypted email code received")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "generate":
        generate()
    else:
        raise SystemExit("Usage: otp_relay.py generate")
