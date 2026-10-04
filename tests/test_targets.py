import json
import pathlib
import subprocess
import sys
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts/check-targets.py"


class TargetHealth(unittest.TestCase):
    def targets(self):
        jobs = ["prometheus", "node", "node", "blackbox", "blackbox", "blackbox-self"]
        return {"status": "success", "data": {"activeTargets": [{"labels": {"job": job, "instance": str(index)}, "health": "up"} for index, job in enumerate(jobs)]}}

    def check(self, payload):
        return subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(payload), text=True, capture_output=True).returncode

    def test_all_expected_healthy(self):
        self.assertEqual(self.check(self.targets()), 0)

    def test_api_success_is_insufficient_with_empty_targets(self):
        payload = self.targets()
        payload["data"]["activeTargets"] = []
        self.assertNotEqual(self.check(payload), 0)

    def test_api_success_is_insufficient_with_down_target(self):
        payload = self.targets()
        payload["data"]["activeTargets"][2]["health"] = "down"
        self.assertNotEqual(self.check(payload), 0)

    def test_missing_job_is_failure(self):
        payload = self.targets()
        payload["data"]["activeTargets"].pop()
        self.assertNotEqual(self.check(payload), 0)


if __name__ == "__main__":
    unittest.main()
