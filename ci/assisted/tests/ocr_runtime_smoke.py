"""Credential-free Windows smoke test for the optional local Assistant OCR.

Renders a synthetic, non-account-specific label in memory; verifies that
RapidOCR and the ONNX provider can initialize and recognize it on runners.
No Roblox credentials, windows, screenshots, or network endpoints are used.
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from rapidocr import RapidOCR


def main():
    image = Image.new("RGB", (720, 180), "white")
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 74)
    ImageDraw.Draw(image).text((34, 32), "Assistant", font=font, fill="black")
    result = RapidOCR()(np.asarray(image))
    recognized = bool(result is not None and result.txts and
                      any(t.lower().strip() == "assistant" for t in result.txts))
    print("MCP_OCR_SMOKE: engine_ready=True synthetic_assistant_read=%s" % recognized)
    if not recognized:
        raise SystemExit("MCP_OCR_SMOKE_FAILED")
    # Real Roblox Studio Assistant tooltips use light text on dark chrome.
    # Verify this contrast too, without any live Studio account or pixels.
    dark = Image.new("RGB", (720, 180), (35, 37, 41))
    dark_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 61)
    ImageDraw.Draw(dark).text((34, 38), "AI Assistant",
                              font=dark_font, fill="white")
    test = RapidOCR()(np.asarray(dark))
    dark_ok = bool(test is not None and test.txts and
                   any("assistant" in t.lower() for t in test.txts))
    print("MCP_OCR_SMOKE: synthetic_dark_ai_assistant_read=%s" % dark_ok)
    if not dark_ok:
        raise SystemExit("MCP_OCR_DARK_TOOLTIP_SMOKE_FAILED")
    # The official November 2026 Studio status bar has a compact MCP
    # badge. Test the same 3x scale used by its guarded click helper.
    status = Image.new("RGB", (430, 92), (34, 38, 44))
    mcp_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    ImageDraw.Draw(status).text((320, 35), "MCP", font=mcp_font,
                                fill=(235, 235, 235))
    enlarged = status.resize((1290, 276))
    badge = RapidOCR()(np.asarray(enlarged))
    badge_ok = bool(badge is not None and badge.txts and
                    any(x.strip().casefold() == "mcp" for x in badge.txts))
    print("MCP_OCR_SMOKE: synthetic_compact_mcp_status_read=%s" % badge_ok)
    if not badge_ok:
        raise SystemExit("MCP_OCR_STATUS_BADGE_SMOKE_FAILED")


if __name__ == "__main__":
    main()
