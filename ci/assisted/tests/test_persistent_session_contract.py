"""Static, credential-free safety contract for persistent Studio workflow."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (ROOT / "ci/assisted/session-persistent.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-openai-tunnel-persistent.yml").read_text(encoding="utf-8")


class PersistentSessionContract(unittest.TestCase):
    def test_no_roblox_password_or_username_needed(self):
        for item in (SCRIPT, WORKFLOW):
            self.assertIsNone(re.search(r"\bROBLOX_(?:USERNAME|PASSWORD)\b", item))

    def test_no_email_otp_relay_needed(self):
        self.assertNotIn("otp_relay.py", SCRIPT.lower())
        self.assertNotIn("otp_relay.py", WORKFLOW.lower())
        self.assertNotIn("login-ui.py", SCRIPT.lower())

    def test_manually_dispatched_only(self):
        self.assertRegex(WORKFLOW, r"(?m)^\s*workflow_dispatch:")
        self.assertNotRegex(WORKFLOW, r"(?m)^\s*push:")
        self.assertNotRegex(WORKFLOW, r"(?m)^\s*schedule:")

    def test_dedicated_interactive_windows_label(self):
        self.assertIn("roblox-studio-interactive", WORKFLOW)
        self.assertIn("GetForegroundWindow()", SCRIPT)
        self.assertIn("PERSISTENT_RUNNER_MUST_BE_INTERACTIVE", SCRIPT)

    def test_official_mcp_and_tunnel_verified_before_run(self):
        for snippet in ("mcp.bat", "open-test-place-cli.ps1",
                        "doctor --profile", "run --profile",
                        "PERSISTENT_OFFICIAL_MCP_LAUNCHER_MISSING"):
            self.assertIn(snippet, SCRIPT)

    def test_tunnel_keys_are_secrets_not_plaintext(self):
        self.assertIn("secrets.OPENAI_TUNNEL_RUNTIME_KEY", WORKFLOW)
        self.assertIn("secrets.OPENAI_TUNNEL_ID", WORKFLOW)
        self.assertNotIn("secrets.ROBLOX", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
