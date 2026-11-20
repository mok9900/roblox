"""Credential-free visual candidate selection tests; do not take screenshots."""
import importlib.util
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "visual_twofactor.py"
spec = importlib.util.spec_from_file_location("visual_twofactor", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
pick = module.unique_ocr_target


class VisualCandidateTest(unittest.TestCase):
    def setUp(self):
        self.controls = [
            ("MenuItem", 220, 210, 580, 256),
            ("MenuItem", 220, 260, 580, 306),
        ]

    def test_unique_email_menu_is_selected(self):
        self.assertEqual(pick([
            ("Email verification", .97, 280, 220, 400, 244)
        ], self.controls), 0)

    def test_masked_email_menu_is_selected(self):
        self.assertEqual(pick([
            ("s***@gmail.com", .93, 280, 268, 430, 289)
        ], self.controls), 1)

    def test_ocr_lines_outside_real_controls_are_ignored(self):
        self.assertIsNone(pick([
            ("Email verification", .99, 350, 140, 480, 160)
        ], self.controls))

    def test_two_distinct_email_choices_are_ambiguous(self):
        self.assertIsNone(pick([
            ("Email", .95, 280, 220, 340, 243),
            ("Email", .94, 280, 268, 345, 291),
        ], self.controls))

    def test_untrusted_ocr_confidence_is_rejected(self):
        self.assertIsNone(pick([
            ("Email", .75, 280, 220, 330, 243)
        ], self.controls))

    def test_account_settings_email_not_clicked(self):
        self.assertIsNone(pick([
            ("Change Email in account settings", .99, 280, 220, 500, 243)
        ], self.controls))

    def test_nonmenu_large_pane_not_clicked(self):
        self.assertIsNone(pick([
            ("Email", .96, 280, 220, 330, 243)
        ], [("Pane", 190, 180, 710, 450)]))

    def test_duplicate_nested_menu_targets_fail_closed(self):
        controls = self.controls + [
            ("ListItem", 215, 200, 590, 265)
        ]
        self.assertIsNone(pick([
            ("Email", .95, 280, 220, 340, 243)
        ], controls))

    def test_oversized_menu_row_rejected(self):
        self.assertIsNone(pick([
            ("Email", .95, 280, 220, 340, 243)
        ], [("MenuItem", 0, 0, 1500, 700)]))

    def test_error_without_any_candidates(self):
        self.assertIsNone(pick([("Email", .99, 200, 200, 250, 220)], []))


if __name__ == "__main__":
    unittest.main()
