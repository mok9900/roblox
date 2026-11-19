"""Capture one *encrypted* snapshot of an unexpected official Roblox 2FA GUI.

Security invariants:
- Trigger only after user-authorized official credential submission and
  an unrecognized verification method.
- Never write plaintext screenshots, OCR, filenames of user data or URLs.
- Crop to official Roblox login host, excluding Edge browser chrome.
- Redact all UIA Edit controls before encrypting; RSA-OAEP + AES-256-GCM.
- If capture, masking or encryption fails, upload NOTHING.
The ephemeral RSA private key is held outside GitHub.
"""
from io import BytesIO
from pathlib import Path
import os
import sys

try:
    import dxcam
    import numpy as np
    import psutil
    from pywinauto import Desktop
    from PIL import Image, ImageDraw
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:
    raise SystemExit("TWOFA_ENCRYPTED_DIAG_DEPENDENCIES_UNAVAILABLE")


def process_map():
    return {p.info["pid"]: (p.info.get("name") or "").lower()
            for p in psutil.process_iter(attrs=("pid", "name"))}


def verified_host():
    mode = os.environ.get("ROBLOX_LOGIN_MODE", "native")
    pmap = process_map()
    hosts = []
    for window in Desktop(backend="uia").windows():
        try:
            if not window.is_visible():
                continue
            exe = pmap.get(window.element_info.process_id, "")
            if mode == "native" and exe == "robloxstudiobeta.exe":
                hosts.append(window)
            if mode == "browser" and exe == "msedge.exe" and "roblox" in (window.window_text() or "").lower():
                hosts.append(window)
        except Exception:
            pass
    # Fail closed when two possible login hosts could expose unrelated UI.
    return hosts[0] if len(hosts) == 1 else None


def capture():
    host = verified_host()
    if host is None:
        raise ValueError("Ambiguous Roblox host")
    bounds = host.rectangle()
    cam = None
    try:
        cam = dxcam.create(backend="dxgi", output_color="RGB",
                           processor_backend="numpy")
        frame = cam.grab(new_frame_only=False)
        if frame is None:
            raise ValueError("No DXGI frame")
        pixels = np.asarray(frame)
        h, w = pixels.shape[:2]
        if w < 700 or h < 500:
            raise ValueError("Unexpected framebuffer")
        # Crop to the middle of the first-party login or 2FA window.
        # Browser location bar and unrelated desktop edges are excluded.
        l = max(0, int(bounds.left + bounds.width() * .15))
        r = min(w, int(bounds.right - bounds.width() * .15))
        t = max(0, int(bounds.top + max(132, bounds.height() * .12)))
        b = min(h, int(bounds.bottom - bounds.height() * .08))
        if r - l < 340 or b - t < 230:
            raise ValueError("Invalid verified Roblox crop")
        img = Image.fromarray(pixels).crop((l, t, r, b))
        draw = ImageDraw.Draw(img)
        # Redact every UIA editable field (possibly username, password, OTP).
        try:
            entries = [c for c in host.descendants()
                       if c.is_visible() and c.element_info.control_type == "Edit"]
        except Exception as exc:
            raise ValueError("Cannot enumerate protected edits") from exc
        for entry in entries:
            rect = entry.rectangle()
            x0 = max(0, int(rect.left - l) - 8)
            y0 = max(0, int(rect.top - t) - 8)
            x1 = min(img.width, int(rect.right - l) + 8)
            y1 = min(img.height, int(rect.bottom - t) + 8)
            if x0 < x1 and y0 < y1:
                draw.rectangle((x0, y0, x1, y1), fill=(0, 0, 0))
        output = BytesIO()
        img.save(output, format="JPEG", quality=80, optimize=True)
        raw = output.getvalue()
        if not 1000 < len(raw) < 3_000_000:
            raise ValueError("Screenshot payload outside safe size")
        return raw
    finally:
        if cam is not None:
            try:
                cam.release()
            except Exception:
                pass


def main():
    # Public key may be in repository, private key is NEVER in CI.
    public_path = Path(__file__).resolve().parent / "diag-public.pem"
    if not public_path.is_file():
        raise ValueError("No diagnostic encryption public key")
    rsa_public = serialization.load_pem_public_key(public_path.read_bytes())
    if rsa_public.key_size < 3072:
        raise ValueError("Insufficient key strength")
    image = capture()
    sym_key = os.urandom(32)
    nonce = os.urandom(12)
    wrapped = rsa_public.encrypt(sym_key, padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(), label=None))
    payload = AESGCM(sym_key).encrypt(nonce, image, b"RBXDBG1")
    artifact = b"RBXDBG1" + len(wrapped).to_bytes(2, "big") + wrapped + nonce + payload
    path = Path(__file__).resolve().parent / ".runtime" / "twofactor.enc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(artifact)
    print("TWOFA_ENCRYPTED_DIAG_READY: redact_edit_fields=True; plaintext_not_persisted=True.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("TWOFA_ENCRYPTED_DIAG_UNAVAILABLE: nothing unsafe uploaded.", flush=True)
        sys.exit(1)
