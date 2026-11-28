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



class BrowserFocusGuardTest(unittest.TestCase):
    def setUp(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock
        source=SOURCE.with_name("visual-browser-login.py")
        tree=ast.parse(source.read_text(encoding="utf-8"))
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("verified_browser_url","fresh_form")]
        self.win=SimpleNamespace(handle=12)
        self.edits=[object(),object()]
        self.target=object()
        self.url="https://www.roblox.com/login"
        self.scope={
            "browser_form":Mock(return_value=(self.win,self.edits)),
            "verified_browser_url":Mock(return_value=self.url),
            "submit_target":Mock(return_value=(self.target,1,1)),
            "user32":SimpleNamespace(GetForegroundWindow=Mock(return_value=12)),
            "focus_studio":Mock(return_value=True)}
        # Keep URL parser separate from the injected mock used by fresh_form.
        urls={}
        exec(compile(ast.Module(body=[nodes[0]],type_ignores=[]),str(source),"exec"),urls)
        self.parse_url=urls["verified_browser_url"]
        exec(compile(ast.Module(body=[nodes[1]],type_ignores=[]),str(source),"exec"),self.scope)
        self.fresh=self.scope["fresh_form"]

    def test_exact_window_and_url(self):
        self.assertEqual(self.fresh(12,self.url,True),(self.win,self.edits,self.target))
        self.assertIsNone(self.fresh(13,self.url))
        self.assertIsNone(self.fresh(12,"https://www.roblox.com/other"))
        self.scope["focus_studio"].assert_not_called()

    def test_one_guarded_refocus_requires_revalidation(self):
        self.scope["user32"].GetForegroundWindow.side_effect=[99,12,12]
        self.assertEqual(self.fresh(12,self.url,True,True),(self.win,self.edits,self.target))
        self.scope["focus_studio"].assert_called_once_with(self.win)
        self.assertEqual(self.scope["browser_form"].call_count,2)

    def test_changed_url_after_reactivation_is_rejected(self):
        self.scope["user32"].GetForegroundWindow.return_value=99
        self.scope["verified_browser_url"].side_effect=[self.url,"https://www.roblox.com/other"]
        self.assertIsNone(self.fresh(12,self.url,True,True))
        self.scope["focus_studio"].assert_called_once()

    def test_ambiguous_target_and_unverified_origin_do_not_refocus(self):
        self.scope["user32"].GetForegroundWindow.return_value=99
        self.scope["submit_target"].return_value=(None,2,2)
        self.assertIsNone(self.fresh(12,self.url,True,True))
        self.scope["verified_browser_url"].return_value=None
        self.assertIsNone(self.fresh(12,self.url,True,True))
        self.scope["focus_studio"].assert_not_called()

    def test_origin_requires_unique_exact_https_url(self):
        from types import SimpleNamespace
        def control(value):
            return SimpleNamespace(element_info=SimpleNamespace(name="Address and search bar"),is_visible=lambda:True,get_value=lambda:value)
        def win(*urls):
            return SimpleNamespace(descendants=lambda **kw:[control(u) for u in urls])
        self.assertEqual(self.parse_url(win(self.url,self.url)),self.url)
        self.assertIsNone(self.parse_url(win(self.url,"https://www.roblox.com/other")))
        for bad in ("http://www.roblox.com/login","https://www.roblox.com.evil.invalid/login","https://user@www.roblox.com/login","https://www.roblox.com:8443/login"):
            self.assertIsNone(self.parse_url(win(bad)))

if __name__ == "__main__":
    unittest.main()
