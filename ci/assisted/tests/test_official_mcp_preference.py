"""Credential-free tests for official per-account Studio MCP preference.

Runs on GitHub-hosted CI with synthetic usernames and temporary filesystem.
Never needs Roblox authentication, a Studio binary, or a real user ID.
"""
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

SRC = pathlib.Path(__file__).resolve().parents[1] / "enable-official-mcp-preference.py"
spec = importlib.util.spec_from_file_location("pref", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeUrlOpen:
    def __init__(self, payload):
        self.payload = payload
        self.called = False

    def __call__(self, request, *, timeout=0):
        self.called = True
        assert request.full_url == mod.USERS_ENDPOINT
        assert request.get_method() == "POST"
        assert timeout <= 15
        params = json.loads(request.data)
        assert params["usernames"] == ["Sample_User"]
        return io.BytesIO(json.dumps(self.payload).encode())


class PreferenceTests(unittest.TestCase):
    def test_verified_public_username_and_id(self):
        fake = FakeUrlOpen({"data": [{"requestedUsername": "Sample_User",
                                        "name": "sample_user", "id": 123456}]})
        self.assertEqual(mod.official_user_id("Sample_User", urlopen=fake), 123456)
        self.assertTrue(fake.called)

    def test_reject_other_user_id_even_if_api_returns_id(self):
        fake = FakeUrlOpen({"data": [{"requestedUsername": "other_user", "id": 12}]})
        with self.assertRaises(ValueError):
            mod.official_user_id("Sample_User", urlopen=fake)

    def test_reject_email_or_similar_arbitrary_login_without_network(self):
        for username in ("somebody@example.com", "", "xx", "not valid", "x"*80):
            with self.subTest(username=username), self.assertRaises(ValueError):
                mod.official_user_id(username, urlopen=lambda *a, **k: self.fail("network"))

    def test_create_first_party_preference_in_temp_user_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = mod.update_official_preference(111111, tmp)
            self.assertTrue(result["changed"])
            self.assertFalse(result["settings_file_present"])
            config = pathlib.Path(tmp, "Roblox", "AssistantSettings", "111111.json")
            self.assertEqual(json.loads(config.read_text())["mcp-server"]["enabled"], True)
            again = mod.update_official_preference(111111, tmp)
            self.assertFalse(again["changed"])
            self.assertTrue(again["settings_file_present"])

    def test_preserves_all_existing_unrelated_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp, "Roblox", "AssistantSettings", "222222.json")
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({
                "mcp-server": {"enabled": False, "user-permissions": ["none"]},
                "editor": {"theme": "dark"},
                "AssistantHistory": {"lastTab": "Other"},
            }), encoding="utf-8")
            self.assertTrue(mod.update_official_preference(222222, tmp)["changed"])
            content = json.loads(p.read_text())
            self.assertTrue(content["mcp-server"]["enabled"])
            self.assertEqual(content["mcp-server"]["user-permissions"], ["none"])
            self.assertEqual(content["editor"], {"theme": "dark"})
            self.assertEqual(content["AssistantHistory"]["lastTab"], "Other")

    def test_fail_closed_on_invalid_json_without_destroying_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp, "Roblox", "AssistantSettings", "333333.json")
            p.parent.mkdir(parents=True)
            p.write_text("{invalid", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                mod.update_official_preference(333333, tmp)
            self.assertEqual(p.read_text(), "{invalid")

    def test_reject_non_numeric_target_id_and_non_dict_mcp_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                mod.update_official_preference("not-an-id", tmp)
            p = pathlib.Path(tmp, "Roblox", "AssistantSettings", "444444.json")
            p.parent.mkdir(parents=True)
            p.write_text('{"mcp-server":["unrelated"]}')
            with self.assertRaises(ValueError):
                mod.update_official_preference(444444, tmp)
            self.assertEqual(json.loads(p.read_text())["mcp-server"], ["unrelated"])


if __name__ == "__main__":
    unittest.main()
