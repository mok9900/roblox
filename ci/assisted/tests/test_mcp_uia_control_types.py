"""Regression tests: UIA returns title-case control_type while helpers normalize to lowercase.

No Roblox credentials, GUI, pywinauto runtime, or screenshots needed.
This parses only the pure selector functions, not activate-mcp-ui.py's
script-level execution (which requires a signed-in Studio editor).
"""
import ast
import pathlib
import re
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "activate-mcp-ui.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
NEEDED = {"attr", "kind", "safe_name", "click_unique",
          "assistant_topbar", "find_toggle"}
NODES = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in NEEDED]
assert {n.name for n in NODES} == NEEDED
MOD = compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE), "exec")


class FakeControl:
    def __init__(self, name, control_type):
        self.element_info = SimpleNamespace(name=name, control_type=control_type)
        self.click_count = 0

    def click_input(self):
        self.click_count += 1

    def is_visible(self):
        return True


class MCPUIAControlTypeTests(unittest.TestCase):
    def base(self):
        ctx = {"re": re, "time": time,
               "ALLOWED": ("button", "menuitem", "hyperlink",
                           "tabitem", "checkbox", "listitem", "custom"),
               "ASSISTANT": re.compile(r"assistant", re.I),
               "ENABLE": re.compile(r"enable studio as (?:an? )?mcp server", re.I)}
        exec(MOD, ctx)
        return ctx

    def test_kind_normalizes_uia_titlecase(self):
        ctx = self.base()
        self.assertEqual(ctx["kind"](FakeControl("Assistant", "Button")), "button")
        self.assertEqual(ctx["kind"](FakeControl("MCP", "MenuItem")), "menuitem")
        self.assertEqual(ctx["kind"](FakeControl("Toggle", "CheckBox")), "checkbox")

    def test_click_unique_assistant_button(self):
        ctx = self.base()
        target = FakeControl("Assistant", "Button")
        ctx["controls"] = lambda: [target]
        self.assertTrue(ctx["click_unique"](re.compile("assistant"), timeout=0.2))
        self.assertEqual(target.click_count, 1)

    def test_click_unique_overflow_menuitem_explicit_types(self):
        ctx = self.base()
        target = FakeControl("…", "MenuItem")
        ctx["controls"] = lambda: [target]
        self.assertTrue(ctx["click_unique"](re.compile("…"), timeout=0.2,
                                            types=("Button", "MenuItem", "Custom")))
        self.assertEqual(target.click_count, 1)

    def test_unique_named_assistant_topbar(self):
        ctx = self.base()
        target = FakeControl("Assistant", "Button")
        window = SimpleNamespace(descendants=lambda: [target])
        ctx["studio_windows"] = lambda: [window]
        ctx["top_right"] = lambda win, c: True
        ctx["assistant_metadata"] = lambda c: c.element_info.name == "Assistant"
        with redirect_stdout(StringIO()):
            self.assertTrue(ctx["assistant_topbar"]())
        self.assertEqual(target.click_count, 1)

    def test_mcp_checkbox_is_reachable(self):
        ctx = self.base()
        target = FakeControl("Enable Studio as MCP server", "CheckBox")
        ctx["controls"] = lambda: [target]
        self.assertIs(ctx["find_toggle"](), target)

    def test_reject_ambiguous_assistant_buttons(self):
        ctx = self.base()
        target_a = FakeControl("Assistant", "Button")
        target_b = FakeControl("Assistant", "Button")
        probed = []
        def duplicate_controls():
            probed.append(True)
            return [target_a, target_b]
        ctx["controls"] = duplicate_controls
        # Actually run at least one selection pass with two matching buttons.
        self.assertFalse(ctx["click_unique"](re.compile("assistant"), timeout=0.01))
        self.assertGreaterEqual(len(probed), 1)
        self.assertEqual(target_a.click_count + target_b.click_count, 0)

    def test_reject_unrelated_text_as_toggle(self):
        ctx = self.base()
        target = FakeControl("Account Settings", "CheckBox")
        ctx["controls"] = lambda: [target]
        self.assertIsNone(ctx["find_toggle"]())


if __name__ == "__main__":
    unittest.main()
