"""Credential-free tests for Roblox Studio email method selection."""
import ast
import io
import contextlib
import pathlib
import re
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "login-ui.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
selectors = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in ("find_email_method", "select_challenge_host", "safe_choice_diagnostics", "in_browser_content", "find_code_edit", "distinct_visible_edits", "verified_edge_origin", "find_email_send_confirmation", "find_browser_handoff", "find_protocol_consent")]


class Control:
    next_position = 0

    def __init__(self, typ, name="", children=None, bounds=None, visible=True):
        self.typ = typ
        self.name = name.lower()
        self.children = list(children or [])
        Control.next_position += 1
        y = Control.next_position * 30
        self.bounds = bounds or (0, y, 200, y+20)
        self.visible = visible

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return True

    def rectangle(self):
        return Rect(*self.bounds)

    def descendants(self):
        return list(self.children)


scope = {
    "re": re,
    "ctype": lambda c: c.typ,
    "label": lambda c: c.name,
    "VERIFY": re.compile(r"^(?:verify|confirm|continue|submit|next|인증|확인|계속|다음)$", re.I),
    "CODE": re.compile(r"verification code|email code|enter code|security code|6.digit|one.time code|인증 코드|이메일 코드|코드 입력", re.I),
    "_controls": [],
    "challenge_controls": lambda: scope["_controls"],

}
exec(compile(ast.Module(body=selectors, type_ignores=[]), str(SOURCE), "exec"), scope)
find_email_method = scope["find_email_method"]
in_browser_content = scope["in_browser_content"]
find_code_edit = scope["find_code_edit"]
find_browser_handoff = scope["find_browser_handoff"]
find_protocol_consent = scope["find_protocol_consent"]



class Safe2FADiagnosticsTest(unittest.TestCase):
    def test_method_categories_are_safe_and_formatting_succeeds(self):
        scope["_controls"] = [
            Control("Button", "Cancel"),
            Control("MenuItem", "Use authenticator app"),
            Control("MenuItem", "Backup code"),
            Control("Edit", "Username"),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            scope["safe_choice_diagnostics"]()
        text = output.getvalue()
        self.assertIn("SAFE_2FA_CHOICE_SHAPE_0", text)
        self.assertIn("categories=authenticator", text)
        self.assertIn("categories=backup", text)
        self.assertNotIn("use authenticator app", text)
        self.assertNotIn("masked@", text)
        scope["_controls"] = []



class ChallengeHostSelectionTest(unittest.TestCase):
    def test_native_login_does_not_inspect_stale_roblox_edge(self):
        native = object()
        stale_edge = object()
        self.assertEqual(scope["select_challenge_host"](
            [stale_edge], [native], "native"), ("studio", native))

    def test_browser_login_uses_browser_not_studio(self):
        native = object()
        official_edge = object()
        self.assertEqual(scope["select_challenge_host"](
            [official_edge], [native], "browser"), ("edge", official_edge))

    def test_ambiguous_browser_windows_never_selected(self):
        self.assertEqual(scope["select_challenge_host"](
            [object(), object()], [object()], "browser"), (None, None))

    def test_native_login_with_multiple_studio_windows_never_selected(self):
        self.assertEqual(scope["select_challenge_host"](
            [], [object(), object()], "native"), (None, None))


class MaskedEmailChoiceTest(unittest.TestCase):
    def test_unique_masked_email_destination(self):
        target = Control("MenuItem", "Send code to s***@gmail.com")
        self.assertIs(find_email_method([target]), target)

    def test_unmasked_email_address_without_explicit_email_label_is_rejected(self):
        target = Control("MenuItem", "Send code to example@gmail.com")
        self.assertIsNone(find_email_method([target]))

    def test_multiple_masked_destinations_rejected(self):
        self.assertIsNone(find_email_method([
            Control("MenuItem", "To s***@gmail.com"),
            Control("MenuItem", "To z***@outlook.com"),
        ]))



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

    def test_generic_named_menuitem_with_email_text_descendant(self):
        target = Control("MenuItem", "Choose a method",
                         children=[Control("Text", "Send code to Email")])
        self.assertIs(find_email_method([target]), target)

    def test_generic_named_menuitem_with_ambiguous_email_descendants(self):
        target = Control("MenuItem", "Choose a method",
                         children=[Control("Text", "Email"),
                                   Control("Text", "Email code")])
        self.assertIsNone(find_email_method([target]))

    def test_account_settings_parent_with_nested_email_is_rejected(self):
        target = Control("MenuItem", "Change account settings",
                         children=[Control("Text", "Email")])
        self.assertIsNone(find_email_method([target]))

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

    def test_unique_email_automation_id_is_accepted(self):
        target = Control("MenuItem", "Verification method")
        target.element_info = type("Meta", (), {
            "automation_id": "email-method", "help_text": ""
        })()
        self.assertIs(find_email_method([
            target, Control("MenuItem", "Backup code")
        ]), target)

    def test_email_account_settings_automation_id_is_rejected(self):
        target = Control("MenuItem", "Verification method")
        target.element_info = type("Meta", (), {
            "automation_id": "change-email-settings", "help_text": ""
        })()
        self.assertIsNone(find_email_method([target]))

    def test_unique_email_value_pattern_is_accepted(self):
        target = Control("MenuItem", "Verification method")
        target.get_value = lambda: "Send verification code to Email"
        self.assertIs(find_email_method([
            target, Control("MenuItem", "Backup code")
        ]), target)

    def test_account_email_settings_value_is_rejected(self):
        target = Control("MenuItem", "Verification method")
        target.get_value = lambda: "Change Email in account settings"
        self.assertIsNone(find_email_method([target]))

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


class ChallengeFieldSafetyTest(unittest.TestCase):
    def test_duplicate_physical_field_is_collapsed(self):
        rect = (40,200,240,240)
        a = Control("Edit", "", bounds=rect)
        b = Control("Edit", "Verification code", bounds=rect)
        self.assertEqual(find_code_edit([a,b]), [b])

    def test_invisible_duplicate_is_not_selected(self):
        a = Control("Edit", "Verification code", visible=False)
        b = Control("Edit", "Verification code")
        self.assertEqual(find_code_edit([a,b]), [b])

    def test_independent_captcha_is_rejected(self):
        self.assertEqual(find_code_edit([Control("Edit","Verification code"), Control("Text","CAPTCHA")]), [])

    def test_distinct_multiple_code_fields_remain_ambiguous(self):
        self.assertEqual(find_code_edit([Control("Edit","Verification code"), Control("Edit","Verification code")]), [])

    def test_official_https_origin_and_spoofed_origin(self):
        def window(url):
            c = Control("Edit","Address and search bar")
            c.get_value = lambda: url
            return type("Window", (), {"descendants": lambda self, **kw: [c]})()
        verify = scope["verified_edge_origin"]
        self.assertTrue(verify(window("https://www.roblox.com/login")))
        self.assertFalse(verify(window("https://www.roblox.com.example.invalid/login")))
        self.assertFalse(verify(window("http://www.roblox.com/login")))
        self.assertFalse(verify(window("https://www.roblox.com@evil.invalid/login")))


class EmailDeliveryConfirmationTests(unittest.TestCase):
    def test_explicit_delivery(self):
        c = Control("Button", "Send verification code via email")
        self.assertIs(scope["find_email_send_confirmation"]([c]), c)

    def test_generic_next_never_clicked(self):
        self.assertIsNone(scope["find_email_send_confirmation"]([Control("Button", "Next")]))

    def test_multiple_confirmations_rejected(self):
        self.assertIsNone(scope["find_email_send_confirmation"]([Control("Button", "Email me a code"), Control("Button", "Send code via email")]))

    def test_existing_input_and_independent_challenges_rejected(self):
        c = Control("Button", "Send code via email")
        for extra in (Control("Edit", "Verification code"), Control("Text", "CAPTCHA"), Control("Text", "Authenticator"), Control("Text", "Security key")):
            self.assertIsNone(scope["find_email_send_confirmation"]([c,extra]))


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




class BrowserProtocolConsentTest(unittest.TestCase):
    def test_specific_protocol_open_with_cancel_in_studio_context(self):
        target = Control("Button", "Open")
        cs = [
            Control("Text", "Open Roblox Studio?"),
            Control("Text", "A link wants to launch an external application"),
            target,
            Control("Button", "Cancel"),
        ]
        self.assertIs(find_protocol_consent(cs, "Open Roblox Studio?"), target)

    def test_generic_open_without_studio_context_is_rejected(self):
        self.assertIsNone(find_protocol_consent([
            Control("Text", "Open an external application?"),
            Control("Button", "Open"),
            Control("Button", "Cancel"),
        ], "Open external link?"))

    def test_studio_name_without_external_context_is_rejected(self):
        self.assertIsNone(find_protocol_consent([
            Control("Text", "Roblox Studio"),
            Control("Button", "Open"),
            Control("Button", "Cancel"),
        ], "Roblox Studio"))

    def test_missing_cancel_guard_is_rejected(self):
        self.assertIsNone(find_protocol_consent([
            Control("Text", "Open Roblox Studio external app?"),
            Control("Button", "Open"),
        ], "Open Roblox Studio?"))

    def test_ambiguous_two_open_buttons_rejected(self):
        self.assertIsNone(find_protocol_consent([
            Control("Text", "Open Roblox Studio external application"),
            Control("Button", "Open"),
            Control("Button", "Open Roblox Studio"),
            Control("Button", "Cancel"),
        ], "Roblox Studio protocol"))


class Rect:
    def __init__(self,left,top,right,bottom):
        self.left, self.top, self.right, self.bottom = left,top,right,bottom

    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top


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
