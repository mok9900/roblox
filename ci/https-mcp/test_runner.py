import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parent))
import runner

class RunnerTests(unittest.TestCase):
    def test_idle_does_not_launch_studio(self):
        verify=Mock()
        self.assertIsNone(runner.execute_job({"request_id":None},verify))
        verify.assert_not_called()
    def test_only_fixed_readonly_action(self):
        verify=Mock()
        with self.assertRaises(ValueError):
            runner.execute_job({"request_id":"b02e3057-c552-47fb-8a42-91dd25af87cd","action":"execute_script"},verify)
        verify.assert_not_called()
    def test_proof_forwarding(self):
        proof={"verified":True,"matching_local_fixtures":1,"source":"official_studio_mcp"}
        verify=Mock(return_value=proof)
        rid="b02e3057-c552-47fb-8a42-91dd25af87cd"
        self.assertEqual(runner.execute_job({"request_id":rid,"action":"verify_ci_studio"},verify),{"request_id":rid,"result":proof})
        verify.assert_called_once_with()
    def test_invalid_proof_denied(self):
        verify=Mock(return_value={"verified":"true","matching_local_fixtures":1,"source":"official_studio_mcp"})
        with self.assertRaises(ValueError):
            runner.execute_job({"request_id":"b02e3057-c552-47fb-8a42-91dd25af87cd","action":"verify_ci_studio"},verify)
if __name__=="__main__":
    unittest.main(verbosity=2)
