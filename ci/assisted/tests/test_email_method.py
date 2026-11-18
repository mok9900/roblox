"""Credential-free tests for Roblox Studio email method selection."""
import ast
import pathlib
import re
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "login-ui.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
selector = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "find_email_method")


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
}
exec(compile(ast.Module(body=[selector], type_ignores=[]), str(SOURCE), "exec"), scope)
find_email_method = scope["find_email_method"]


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


if __name__ == "__main__":
    unittest.main()
