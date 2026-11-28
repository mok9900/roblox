import json
import unittest
from unittest.mock import Mock
from dev_runner import session_plan, successor_payload, execute

class DevRunnerTests(unittest.TestCase):
    def test_bounded_chain(self):
        now=1000000
        p=session_plan(24,"",0,0,False,now)
        self.assertEqual(p["session_end"],now+86400000)
        self.assertEqual(p["deadline"],now+15000000)
        nxt=successor_payload(p)["inputs"]
        self.assertEqual(nxt["dev_hop"],"1")
        q=session_plan(24,nxt["dev_session_id"],int(nxt["dev_session_end"]),1,False,now+14000000)
        self.assertEqual(q["session_end"],p["session_end"])
        self.assertIsNone(successor_payload({**q,"hop":7}))
        self.assertIsNone(successor_payload({**q,"deadline":q["session_end"]}))

    def test_edit_session_cannot_roll_or_exceed_four_hours(self):
        with self.assertRaises(ValueError):session_plan(24,"",0,0,True,1000)
        p=session_plan(4,"",0,0,True,1000)
        self.assertIsNone(successor_payload(p))
        with self.assertRaises(ValueError):session_plan(4,p["session_id"],p["session_end"],1,True,2000)

    def test_result_fencing_and_no_retry(self):
        s=Mock()
        s.invoke.side_effect=RuntimeError("synthetic unknown outcome")
        job={"request_id":"12345678-1234-4234-9234-123456789012","generation":2,
             "action":{"name":"multi_edit","arguments":{"studio_id":"fixture"}}}
        result=execute(job,s)
        self.assertEqual(result["generation"],2)
        self.assertTrue(result["result"]["isError"])
        s.invoke.assert_called_once()
        with self.assertRaises(ValueError):execute({**job,"generation":"2"},s)

if __name__=="__main__":
    unittest.main(verbosity=2)
