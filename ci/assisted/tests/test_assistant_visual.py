"""Credential-free policy tests for visual Studio Assistant discovery."""
import ctypes
import importlib.util
import pathlib
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / "assistant_visual.py"
spec = importlib.util.spec_from_file_location("assistant_visual", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
near = mod.unique_tooltip_near_pointer

REGION = (560, 20, 1190, 240)
POINT = (930, 75)


class AssistantTooltipPolicyTest(unittest.TestCase):
    def test_verified_exact_english_tooltip(self):
        self.assertTrue(near([("Assistant", .99, 890, 95, 982, 120)],
                             POINT, region=REGION))

    def test_exact_ai_assistant_tooltip_matches_official_label(self):
        self.assertTrue(near([("AI Assistant", .99, 890, 95, 994, 120)],
                             POINT, region=REGION))

    def test_ai_assistant_settings_is_not_an_icon_tooltip(self):
        self.assertFalse(near([("AI Assistant Settings", .99, 890, 95, 1050, 120)],
                              POINT, region=REGION))

    def test_official_merged_title_and_description(self):
        long_title = ("AI Assistant Chat with Studio Assistant to get help "
                      "and accelerate creation")
        self.assertTrue(mod.tooltip_heading(long_title))
        self.assertTrue(near([(long_title, .94, 725, 100, 1090, 185)],
                             POINT, region=REGION))

    def test_settings_or_generic_description_never_verified(self):
        for name in ("AI Assistant Settings", "Assistant MCP Servers",
                     "Chat with Studio Assistant", "Assistant content"):
            self.assertFalse(mod.tooltip_heading(name), name)

    def test_fuzzy_lowercase_official_hover_heading(self):
        self.assertTrue(mod.tooltip_heading("AI Assistant"))
        self.assertTrue(mod.tooltip_heading("   AI   Assistant   "))

    def test_unrelated_large_merged_region_rejected(self):
        name = "AI Assistant Chat with Studio Assistant to get help"
        self.assertFalse(near([(name, .99, 560, 40, 1180, 225)],
                              POINT, region=REGION))

    def test_verified_exact_korean_tooltip(self):
        self.assertTrue(near([("어시스턴트", .95, 890, 92, 993, 119)],
                             POINT, region=REGION))

    def test_substrings_and_settings_are_not_actions(self):
        self.assertFalse(near([("Assistant Settings", .99, 890, 90, 1040, 116)],
                              POINT, region=REGION))

    def test_low_confidence_never_clicks(self):
        self.assertFalse(near([("Assistant", .90, 890, 95, 982, 120)],
                              POINT, region=REGION))

    def test_ocr_outside_editor_region_rejected(self):
        self.assertFalse(near([("Assistant", .98, 400, 90, 500, 120)],
                              POINT, region=REGION))

    def test_tooltip_far_from_hover_rejected(self):
        self.assertFalse(near([("Assistant", .99, 570, 90, 660, 112)],
                              POINT, region=REGION))

    def test_multiple_tooltips_are_ambiguous(self):
        items = [("Assistant", .99, 890, 95, 982, 120),
                 ("Assistant", .98, 880, 130, 970, 153)]
        self.assertFalse(near(items, POINT, region=REGION))

    def test_large_overlay_not_a_tooltip(self):
        self.assertFalse(near([("Assistant", .99, 650, 55, 1050, 180)],
                              POINT, region=REGION))

    def test_pointer_outside_editor_region(self):
        self.assertFalse(near([("Assistant", .99, 890, 95, 982, 120)],
                              (1200, 75), region=REGION))

    def test_no_label_no_click(self):
        self.assertFalse(near([], POINT, region=REGION))


class StudioMCPStatusBadgeTests(unittest.TestCase):
    """The official November 2026 status-bar entry is not a guessed click."""
    REGION = (1100, 925, 1914, 1040)

    def label(self, *, name="MCP", score=.98, x0=1780, y0=994,
              x1=1824, y1=1018):
        return (name, score, x0, y0, x1, y1)

    def test_exact_studio_mcp_status_is_actionable(self):
        self.assertEqual(mod.unique_mcp_status_position(
            [self.label()], region=self.REGION), (1802, 1006))

    def test_casefold_whitespace_is_accepted(self):
        self.assertIsNotNone(mod.unique_mcp_status_position(
            [self.label(name="  mCp  ")], region=self.REGION))

    def test_never_click_weak_or_unrelated_text(self):
        for name in ("MCP Servers", "MCP Permissions", "MCP Connected",
                     "Manage MCP", "MCF", "Assistant", "MCP (0)"):
            with self.subTest(name=name):
                self.assertIsNone(mod.unique_mcp_status_position(
                    [self.label(name=name)], region=self.REGION))
        self.assertIsNone(mod.unique_mcp_status_position(
            [self.label(score=.89)], region=self.REGION))

    def test_only_bottom_right_status_region_is_actionable(self):
        for x0, y0, x1, y1 in [
            (1050, 994, 1100, 1018),  # outside right-side section
            (1780, 500, 1824, 521),   # editor content, not status
            (1780, 1030, 1824, 1070), # outside visible editor bounds
            (1600, 980, 1800, 1002),  # abnormally wide OCR rectangle
        ]:
            with self.subTest(rect=(x0, y0, x1, y1)):
                self.assertIsNone(mod.unique_mcp_status_position(
                    [self.label(x0=x0, y0=y0, x1=x1, y1=y1)],
                    region=self.REGION))

    def test_ambiguous_duplicate_mcp_labels_cannot_be_clicked(self):
        items = [self.label(), self.label(x0=1680, x1=1724)]
        self.assertIsNone(mod.unique_mcp_status_position(
            items, region=self.REGION))

    def test_empty_capture_is_not_a_click(self):
        self.assertIsNone(mod.unique_mcp_status_position(
            [], region=self.REGION))


class StudioForegroundGuardTests(unittest.TestCase):
    class PositionSetter:
        def __init__(self):
            self.calls = []

        def __call__(self, hwnd, mode, x, y, w, h, flags):
            self.calls.append((hwnd, mode.value, flags))
            return True

    class FakeUser32:
        def __init__(self, *, allow_foreground=True):
            self.foreground = 42
            self.allow_foreground = allow_foreground
            self.SetWindowPos = StudioForegroundGuardTests.PositionSetter()
            self.show_calls = 0
            self.show_commands = []
            self.set_calls = 0

        def IsWindow(self, hwnd):
            return hwnd == 1234

        def ShowWindow(self, hwnd, command):
            self.show_calls += 1
            self.show_commands.append((hwnd, command))

        def GetForegroundWindow(self):
            return self.foreground

        def SetForegroundWindow(self, hwnd):
            self.set_calls += 1
            if self.allow_foreground:
                self.foreground = hwnd
            return self.allow_foreground

    class FakeEditor:
        handle = 1234

        def __init__(self, title="ci_only_baseplate_test.rbxl - Roblox Studio"):
            self.title = title
            self.focus_attempts = 0

        def window_text(self):
            return self.title

        def set_focus(self):
            self.focus_attempts += 1

    def test_verified_editor_can_be_activated_without_blind_click(self):
        api = self.FakeUser32()
        editor = self.FakeEditor()
        ok = mod.focus_verified_editor(editor, api, pause=lambda _: None)
        self.assertTrue(ok)
        self.assertGreaterEqual(api.set_calls, 1)
        self.assertEqual(api.GetForegroundWindow(), editor.handle)
        self.assertEqual(api.show_commands[0], (editor.handle, 3))
        self.assertEqual(api.SetWindowPos.calls[-1][1], ctypes.c_void_p(-2).value)

    def test_unverified_title_is_never_focused(self):
        api = self.FakeUser32()
        editor = self.FakeEditor(title="unrelated user game")
        self.assertFalse(mod.focus_verified_editor(editor, api, pause=lambda _: None))
        self.assertEqual(api.show_calls, 0)
        self.assertEqual(api.set_calls, 0)

    def test_foreground_refusal_fails_closed_and_cleans_topmost(self):
        api = self.FakeUser32(allow_foreground=False)
        editor = self.FakeEditor()
        self.assertFalse(mod.focus_verified_editor(editor, api, pause=lambda _: None))
        self.assertEqual(api.GetForegroundWindow(), 42)
        self.assertEqual(api.SetWindowPos.calls[-1][1], ctypes.c_void_p(-2).value)

    def test_invalid_window_handle_rejected(self):
        api = self.FakeUser32()
        editor = self.FakeEditor()
        editor.handle = 0
        self.assertFalse(mod.focus_verified_editor(editor, api, pause=lambda _: None))
        self.assertEqual(api.show_calls, 0)


if __name__ == "__main__":
    unittest.main()
