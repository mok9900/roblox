import json
import unittest
from unittest.mock import Mock
from studio_session import StudioSession

def entry(name):
    return {"name":name,"inputSchema":{"type":"object"}}

def record(**changes):
    return {"id":"local-fixture-id","name":"CI_Only_Baseplate_Test.rbxlx","persistedToCloud":False,**changes}

class FakeChild:
    def __init__(self,argv):
        self.calls=[]
        self.records=[record()]
        self.closed=False
    def send(self,method,params=None,notification=False):
        self.calls.append((method,params,notification))
        if method=="initialize": return {"protocolVersion":"2025-06-18"}
        if method=="notifications/initialized": return None
        if method=="tools/list":
            return {"tools":[entry(n) for n in ("list_roblox_studios","get_studio_state","multi_edit","execute_luau","open_cloud_invoke","unknown_future_tool")]}
        if params["name"]=="list_roblox_studios":
            return {"structuredContent":{"studios":self.records}}
        return {"content":[{"type":"text","text":"synthetic"}]}
    def close(self): self.closed=True

class SessionTests(unittest.TestCase):
    def test_persistent_process_and_discovery(self):
        factory=Mock(side_effect=FakeChild)
        with StudioSession(["stub"],child_factory=factory) as s:
            child=s.child
            self.assertTrue(s.verify()["verified"])
            self.assertTrue(s.verify()["verified"])
            self.assertEqual(s.invoke("list_roblox_studios",{})["structuredContent"]["studios"][0]["id"],"local-fixture-id")
            self.assertEqual([t["name"] for t in s.visible_catalog()],["get_studio_state","list_roblox_studios"])
            s.invoke("get_studio_state",{"studio_id":"local-fixture-id"})
            factory.assert_called_once()
        self.assertTrue(child.closed)

    def test_cloud_and_stale_targets_rejected(self):
        with StudioSession(["stub"],child_factory=FakeChild) as s:
            with self.assertRaises(ValueError):
                s.invoke("get_studio_state",{"studio_id":"wrong"})
            s.child.records=[record(persistedToCloud=True)]
            with self.assertRaises(RuntimeError):
                s.invoke("get_studio_state",{"studio_id":"local-fixture-id"})

    def test_local_edit_opt_in_never_enables_account_tools(self):
        with StudioSession(["stub"],allow_local_edits=True,child_factory=FakeChild) as s:
            s.invoke("multi_edit",{"studio_id":"local-fixture-id"})
            for name in ("execute_luau","open_cloud_invoke","unknown_future_tool"):
                with self.assertRaises(ValueError): s.invoke(name,{"studio_id":"local-fixture-id"})
        with StudioSession(["stub"],child_factory=FakeChild) as s:
            with self.assertRaises(ValueError): s.invoke("multi_edit",{"studio_id":"local-fixture-id"})

    def test_ambiguous_fixture_and_missing_id_rejected(self):
        with StudioSession(["stub"],child_factory=FakeChild) as s:
            s.child.records=[record(),record(id="second")]
            with self.assertRaises(RuntimeError): s.invoke("list_roblox_studios",{})
            s.child.records=[record(id=None)]
            with self.assertRaises(RuntimeError): s.invoke("list_roblox_studios",{})

    def test_no_fallback_from_structured_cloud_result(self):
        with StudioSession(["stub"],child_factory=FakeChild) as s:
            s.child.records=[record(persistedToCloud=True)]
            self.assertFalse(s.verify()["verified"])

if __name__=="__main__":
    unittest.main(verbosity=2)
