"""Credential-free synthetic Gmail 2FA parser tests. Never contact Gmail."""
import base64
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

SRC = pathlib.Path(__file__).resolve().parents[1] / "gmail_otp.py"
spec = importlib.util.spec_from_file_location("gmail_otp", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def message(text, *, sender="Roblox <accounts@roblox.com>",
            internal_ms=1020000, html=False):
    body = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")
    return {"internalDate": str(internal_ms),
            "payload": {
                "headers": [{"name": "From", "value": sender}],
                "parts": [{"mimeType": "text/html" if html else "text/plain",
                           "body": {"data": body}}],
            }}


class GmailCodeTests(unittest.TestCase):
    def code(self, msg, *, started=1000, now=1040):
        return mod.extract_code(msg, earliest_epoch=started, now_epoch=now)

    def test_korean_code_followed_immediately_by_hangul(self):
        self.assertEqual(self.code(message(
            "mok_990O 님의 Roblox 2단계 인증 코드는 123456입니다.")), "123456")

    def test_korean_colon(self):
        self.assertEqual(self.code(message("2단계 인증 코드: 123456")), "123456")

    def test_english_verification_code(self):
        self.assertEqual(self.code(message(
            "Your Roblox verification code is 123456.")), "123456")

    def test_english_security_code(self):
        self.assertEqual(self.code(message("Security code: 123456")), "123456")

    def test_html_body_decoded_in_memory(self):
        self.assertEqual(self.code(message("<b>2단계 인증 코드: 123456</b>", html=True)),
                         "123456")

    def test_sender_spoof_rejected(self):
        self.assertIsNone(self.code(message("2단계 인증 코드: 123456",
                                            sender="Roblox <attacker@example.com>")))

    def test_random_six_digit_in_message_rejected(self):
        self.assertIsNone(self.code(message("Order 123456 has shipped.")))

    def test_old_email_rejected(self):
        self.assertIsNone(self.code(message("2단계 인증 코드: 123456",
                                            internal_ms=700000)))

    def test_future_email_rejected(self):
        self.assertIsNone(self.code(message("2단계 인증 코드: 123456",
                                            internal_ms=1100000)))

    def test_non_numeric_otp_rejected(self):
        self.assertIsNone(self.code(message("2단계 인증 코드: ABCDEF")))

    def test_partial_oauth_secrets_fail_closed(self):
        with patch.dict(mod.os.environ, {"GMAIL_OAUTH_CLIENT_ID": "example"},
                        clear=True):
            with self.assertRaisesRegex(RuntimeError, "INCOMPLETE"):
                mod.configured()

    def test_full_oauth_secrets_selectable_without_network(self):
        with patch.dict(mod.os.environ, {
            "GMAIL_OAUTH_CLIENT_ID": "dummy",
            "GMAIL_OAUTH_CLIENT_SECRET": "dummy",
            "GMAIL_OAUTH_REFRESH_TOKEN": "dummy"}, clear=True):
            self.assertTrue(mod.configured())


if __name__ == "__main__":
    unittest.main()
