"""Credential-free tests for Assistant install diagnostics.

Synthetic files ONLY. Never open real Roblox account or log files.
"""
import importlib.util
import pathlib
import tempfile
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / "probe-assistant-assets.py"
spec = importlib.util.spec_from_file_location("assistant_asset_probe", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ProbeTest(unittest.TestCase):
    def test_missing_everywhere_is_not_called_installed(self):
        with tempfile.TemporaryDirectory() as root:
            base = pathlib.Path(root)
            studio = base / "Programs" / "RobloxStudioBeta.exe"
            studio.parent.mkdir(parents=True)
            studio.touch()
            actual = mod.inspect_assets(str(studio), str(base / "user"))
            self.assertFalse(actual["ota_present"])
            self.assertFalse(actual["version_present"])
            self.assertFalse(actual["load_failure_logged"])

    def test_version_bundled_assistant_is_accepted_without_ota(self):
        with tempfile.TemporaryDirectory() as root:
            base = pathlib.Path(root)
            studio = base / "Versions" / "test" / "RobloxStudioBeta.exe"
            (studio.parent / "StandaloneBuiltInPlugins").mkdir(parents=True)
            (studio.parent / "StandaloneBuiltInPlugins" / "Assistant.rbxm").write_bytes(b"fixture")
            result = mod.inspect_assets(str(studio), str(base / "user"))
            self.assertFalse(result["ota_present"])
            self.assertTrue(result["version_present"])

    def test_ota_asset_is_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            base = pathlib.Path(root)
            plugin = base / "user" / "Roblox" / "OTAPlugins" / "Deployed" / "BuiltInStandalonePlugins" / "Assistant.rbxm"
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"synthetic fixture")
            result = mod.inspect_assets(str(base / "other" / "RobloxStudioBeta.exe"),str(base / "user"))
            self.assertTrue(result["ota_present"])

    def test_only_exact_assistant_plugin_failures_are_classified(self):
        with tempfile.TemporaryDirectory() as root:
            base = pathlib.Path(root)
            logs = base / "user" / "Roblox" / "logs"
            logs.mkdir(parents=True)
            (logs / "log.log").write_text(
                "Failed to load plugin {type=BuiltInStandalone filepath=Ribbon.rbxm}\n"
                "Assistant.rbxm plugin version updated\n"
                "Failed to load plugin {type=BuiltInStandalone filepath=Assistant.rbxm}\n"
                "Account identity should never be logged here\n",
                encoding="utf-8"
            )
            result = mod.inspect_assets(str(base / "Studio.exe"),str(base / "user"))
            self.assertTrue(result["load_failure_logged"])
            self.assertTrue(result["assistant_log_seen"])
            self.assertEqual(result["logs_examined"], 1)


if __name__ == "__main__":
    unittest.main()
