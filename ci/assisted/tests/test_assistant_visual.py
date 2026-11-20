"""Credential-free policy tests for visual Studio Assistant discovery."""
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


if __name__ == "__main__":
    unittest.main()
