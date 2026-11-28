"""Credential-free regression for the narrow HTTP -> stdio bridge."""
import json
import os
import sys
import threading
import time
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import bridge

class BridgeTests(unittest.TestCase):
    def test_exact_local_only(self):
        good = {"name":bridge.FIXTURE,"persistedToCloud":False}
        self.assertEqual(bridge.local_fixture_count({"content":[{"type":"text","text":json.dumps({"studios":[good]})}]}),1)
        for bad in [
            {"name":bridge.FIXTURE,"persistedToCloud":True},
            {"name":bridge.FIXTURE},
            {"name":"unrelated","persistedToCloud":False},
            {"name":"not_"+bridge.FIXTURE,"persistedToCloud":False},
            "unstructured "+bridge.FIXTURE,
        ]:
            self.assertEqual(bridge.local_fixture_count(bad),0)
        self.assertEqual(bridge.local_fixture_count([good,good]),2)

    def test_actual_stdio_exchange_with_stub(self):
        # Explicit test fixture, never a substitute for real Studio success.
        result = bridge.verify_upstream([sys.executable,"-u",str(Path(__file__).resolve().with_name("fixture.py"))])
        self.assertTrue(result["verified"])
        self.assertEqual(result["matching_local_fixtures"],1)

    def test_dual_result_counted_once(self):
        result = bridge.verify_upstream([sys.executable,"-u",str(Path(__file__).resolve().with_name("fixture.py")),"--dual"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["matching_local_fixtures"],1)

    def test_conflicting_structured_result_not_verified(self):
        result = bridge.verify_upstream([sys.executable,"-u",str(Path(__file__).resolve().with_name("fixture.py")),"--conflicting"])
        self.assertFalse(result["verified"])
        self.assertEqual(result["matching_local_fixtures"],0)

    def test_secret_environment_not_inherited(self):
        with patch.dict(os.environ,{"ROBLOX_PASSWORD":"synthetic","CF_ACCESS_ALLOWED_EMAIL":"synthetic","OPENAI_TUNNEL_RUNTIME_KEY":"synthetic","CLOUDFLARE_TUNNEL_TOKEN":"synthetic","GMAIL_OAUTH_REFRESH_TOKEN":"synthetic"}):
            env = bridge.safe_env()
            self.assertFalse(set(["ROBLOX_PASSWORD","CF_ACCESS_ALLOWED_EMAIL","OPENAI_TUNNEL_RUNTIME_KEY","CLOUDFLARE_TUNNEL_TOKEN","GMAIL_OAUTH_REFRESH_TOKEN"]) & set(env))

    def test_http_auth_and_method_allowlist(self):
        calls = []
        def verify():
            calls.append(1)
            return {"verified":True,"matching_local_fixtures":1,"source":"synthetic_fixture_test"}
        server = ThreadingHTTPServer(("127.0.0.1",0),bridge.make_handler(lambda h:h.get("Cf-Access-Jwt-Assertion")=="synthetic-test-only",verify,"https://example.invalid"))
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        def request(method, payload=None, token=None, origin=None,path="/mcp"):
            conn=HTTPConnection("127.0.0.1",server.server_port,timeout=5)
            headers={"Content-Type":"application/json"}
            if token: headers["Cf-Access-Jwt-Assertion"]=token
            if origin: headers["Origin"]=origin
            try:
                conn.request(method,path,body=json.dumps(payload) if payload is not None else None,headers=headers)
                r=conn.getresponse()
                raw=r.read()
                return r.status,json.loads(raw) if raw else None
            finally:
                conn.close()
        token="synthetic-test-only"
        def rpc(method,params=None,mid=1):
            return {"jsonrpc":"2.0","id":mid,"method":method,"params":params or {}}
        try:
            self.assertEqual(request("POST",rpc("tools/list"))[0],401)
            self.assertEqual(request("POST",rpc("tools/list"),"invalid")[0],401)
            self.assertEqual(request("POST",rpc("tools/list"),token,"https://attacker.invalid")[0],403)
            self.assertEqual(request("POST",rpc("tools/list"),token,path="/other")[0],404)
            self.assertEqual(request("GET",token=token)[0],405)
            self.assertEqual(request("DELETE",token=token)[0],405)
            status, reply=request("POST",rpc("initialize",{"protocolVersion":"2025-06-18"}),token)
            self.assertEqual(status,200)
            self.assertEqual(reply["result"]["protocolVersion"],"2025-06-18")
            self.assertEqual(request("POST",{"jsonrpc":"2.0","method":"notifications/initialized"},token)[0],202)
            status, reply=request("POST",rpc("tools/list"),token)
            self.assertEqual([t["name"] for t in reply["result"]["tools"]],["verify_ci_studio"])
            self.assertIn("error",request("POST",rpc("tools/call",{"name":"execute_luau","arguments":{}}),token)[1])
            self.assertIn("error",request("POST",rpc("tools/call",{"name":"verify_ci_studio","arguments":{"unexpected":1}}),token)[1])
            self.assertEqual(calls,[])
            status,reply=request("POST",rpc("tools/call",{"name":"verify_ci_studio","arguments":{}}),token)
            self.assertEqual(status,200)
            self.assertFalse(reply["result"]["isError"])
            self.assertEqual(calls,[1])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)

    def test_jwt_signature_issuer_audience_email_expiry(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        from types import SimpleNamespace
        private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        wrong=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        issuer="https://synthetic.cloudflareaccess.com"
        now=int(time.time())
        base={"iss":issuer,"aud":"synthetic-audience","email":"owner@example.invalid","iat":now-1,"exp":now+60}
        with patch.dict(os.environ,{"CF_ACCESS_ISSUER":issuer,"CF_ACCESS_AUD":"synthetic-audience","CF_ACCESS_ALLOWED_EMAIL":"owner@example.invalid"}):
            with patch("jwt.PyJWKClient") as client:
                client.return_value.get_signing_key_from_jwt.return_value=SimpleNamespace(key=private.public_key())
                authorize=bridge.build_auth()
                def check(changes=None,key=private):
                    value={**base,**(changes or {})}
                    token=jwt.encode(value,key,algorithm="RS256",headers={"kid":"synthetic"})
                    return authorize({"Cf-Access-Jwt-Assertion":token})
                self.assertTrue(check())
                self.assertFalse(authorize({}))
                self.assertFalse(check({"aud":"wrong"}))
                self.assertFalse(check({"iss":"https://wrong.invalid"}))
                self.assertFalse(check({"email":"other@example.invalid"}))
                self.assertFalse(check({"exp":now-10}))
                self.assertFalse(check(key=wrong))

if __name__=="__main__":
    unittest.main(verbosity=2)
