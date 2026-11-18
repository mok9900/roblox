"""Credential-free tests for Roblox Studio email method selection."""
import ast
import pathlib
import re
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "login-ui.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
selectors = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in ("find_email_method", "in_browser_content", "find_code_edit", "find_browser_handoff")]


class Control:
    def __init__(self, typ, name="", children=None):
        self.typ = typ
        self.name = name.lower()
        self.children = list(children or [])

    def descendants(self):
        return list(self.children)


scope = {
    "re": re,
    "ctype": lambda c: c.typ,
    "label": lambda c: c.name,
    "VERIFY": re.compile(r"^(?:verify|confirm|continue|submit|next|인증|확인|계속|다음)$", re.I),
    "CODE": re.compile(r"verification code|email code|enter code|security code|6.digit|one.time code|인증 코드|이메일 코드|코드 입력", re.I),
}
exec(compile(ast.Module(body=selectors, type_ignores=[]), str(SOURCE), "exec"), scope)
find_email_method = scope["find_email_method"]
in_browser_content = scope["in_browser_content"]
find_code_edit = scope["find_code_edit"]
find_browser_handoff = scope["find_browser_handoff"]


class EmailMethodSelectionTest(unittest.TestCase):
    def test_unique_email_menu_item(self):
        target = Control("MenuItem", "Email")
        self.assertIs(find_email_method([
            Control("MenuItem", "Authenticator app"), target,
            Control("MenuItem", "Backup code")
        ]), target)

    def test_nested_text_email_label(self):
        target = Control("MenuItem", children=[Control("Text", "Send code by email")])
        self.assertIs(find_email_method([
            Control("MenuItem", "Backup code"), target
        ]), target)

    def test_korean_email_option(self):
        target = Control("RadioButton", "이메일로 코드 받기")
        self.assertIs(find_email_method([target]), target)

    def test_native_email_button_inside_list_item(self):
        button = Control("Button", "Email")
        list_item = Control("ListItem", "Email")
        self.assertIs(find_email_method([
            Control("ListItem", "Backup code"), list_item, button
        ]), button)

    def test_ambiguous_email_choices_fail_closed(self):
        self.assertIsNone(find_email_method([
            Control("MenuItem", "Email"), Control("Button", "Email code")
        ]))

    def test_backup_code_only_is_not_email(self):
        self.assertIsNone(find_email_method([
            Control("MenuItem", "Backup code"),
            Control("MenuItem", "Authenticator app")
        ]))

    def test_account_settings_are_excluded(self):
        self.assertIsNone(find_email_method([
            Control("MenuItem", "Change email in account settings")
        ]))

    def test_no_clickable_email_choice_is_rejected(self):
        self.assertIsNone(find_email_method([
            Control("Text", "Email"), Control("Button", "More options")
        ]))

    def test_unlabeled_menu_with_multiple_email_children_rejected(self):
        self.assertIsNone(find_email_method([
            Control("MenuItem", children=[
                Control("Text", "Email"), Control("Text", "Email code")
            ])
        ]))



class EmailCodeFormTest(unittest.TestCase):
    def test_single_unlabeled_code_field(self):
        code = Control("Edit", "")
        self.assertEqual(find_code_edit([code]), [code])

    def test_three_fields_one_unique_unlabeled_code_and_verify(self):
        username = Control("Edit", "Username")
        password = Control("Edit", "Password")
        code = Control("Edit", "")
        cs = [username, password, code, Control("Button", "Verify")]
        self.assertEqual(find_code_edit(cs), [code])

    def test_three_fields_no_verify_is_rejected(self):
        self.assertEqual(find_code_edit([
            Control("Edit", "Username"),
            Control("Edit", "Password"),
            Control("Edit", ""),
            Control("Button", "More options")]), [])

    def test_three_fields_with_ambiguous_unlabeled_edits_rejected(self):
        self.assertEqual(find_code_edit([
            Control("Edit", "Username"),
            Control("Edit", ""),
            Control("Edit", ""),
            Control("Button", "Verify")]), [])

    def test_three_fields_without_verified_credential_labels_rejected(self):
        self.assertEqual(find_code_edit([
            Control("Edit", "First"),
            Control("Edit", "Second"),
            Control("Edit", ""),
            Control("Button", "Verify")]), [])

    def test_explicit_code_label_preferred(self):
        code = Control("Edit", "Verification code")
        self.assertEqual(find_code_edit([Control("Edit", "Email"), code]), [code])


class BrowserHandoffSafetyTest(unittest.TestCase):
    def test_unique_explicit_studio_return_is_allowed(self):
        c = Control("Button", "Open Roblox Studio")
        self.assertIs(find_browser_handoff([c]), c)

    def test_explicit_studio_link_is_allowed(self):
        c = Control("Hyperlink", "Continue to Studio")
        self.assertIs(find_browser_handoff([c]), c)

    def test_generic_browser_prompt_is_rejected(self):
        self.assertIsNone(find_browser_handoff([
            Control("Button", "Open"),
            Control("Button", "Allow"),
            Control("Button", "Continue"),
        ]))

    def test_multiple_handoff_targets_are_rejected(self):
        self.assertIsNone(find_browser_handoff([
            Control("Button", "Open Roblox Studio"),
            Control("Hyperlink", "Return to Roblox Studio"),
        ]))

    def test_unrelated_browser_destination_is_rejected(self):
        self.assertIsNone(find_browser_handoff([
            Control("Button", "Open Account Settings"),
            Control("Hyperlink", "Continue to Roblox"),
        ]))



class Rect:
    def __init__(self,left,top,right,bottom):
        self.left, self.top, self.right, self.bottom = left,top,right,bottom


class BrowserGeometryTest(unittest.TestCase):
    def test_page_choice_included(self):
        self.assertTrue(in_browser_content(Rect(390,300,690,355),
                                           Rect(0,0,1024,768)))

    def test_edge_top_toolbar_excluded(self):
        self.assertFalse(in_browser_content(Rect(900,25,1010,85),
                                            Rect(0,0,1024,768)))

    def test_edge_menu_from_toolbar_excluded(self):
        self.assertFalse(in_browser_content(Rect(870,50,1020,120),
                                            Rect(0,0,1024,768)))

    def test_outside_window_excluded(self):
        self.assertFalse(in_browser_content(Rect(1170,300,1300,350),
                                            Rect(0,0,1024,768)))


if __name__ == "__main__":
    unittest.main()
