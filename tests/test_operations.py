"""Regression tests for failures found in repository review; no cloud calls."""
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class OperationalFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = pathlib.Path(self.temp.name)
        self.scripts = self.fixture / "scripts"
        self.scripts.mkdir()
        self.bin = self.fixture / "bin"
        self.bin.mkdir()
        self.log = self.fixture / "actions"
        self.env = dict(os.environ, ACTION_LOG=str(self.log), PATH=str(self.bin) + os.pathsep + os.environ["PATH"])

    def script(self, name, common):
        shutil.copyfile(ROOT / "scripts" / name, self.scripts / name)
        (self.scripts / "common.sh").write_text("set -euo pipefail\n" + common)
        return self.scripts / name

    def command(self, name, body):
        file = self.bin / name
        file.write_text("#!/usr/bin/env bash\n" + body)
        file.chmod(0o755)

    def test_external_measure_records_all_failed_requests(self):
        script = self.script("measure.sh", 'ip() { echo 192.0.2.10; }\n')
        self.command("curl", "printf '000 0.01\\n'; exit 7\n")
        self.command("sleep", "exit 0\n")
        result = subprocess.run(["bash", str(script), "external", "3"], env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("000 0.01"), 3)
        self.assertEqual(result.stdout.count("exit_code=7"), 3)
        self.assertIn("sample=3", result.stdout)

    def test_internal_measure_continues_after_ssh_failure(self):
        script = self.script("measure.sh", 'ip() { echo 10.20.1.10; }\nremote_bounded() { return 255; }\n')
        self.command("sleep", "exit 0\n")
        result = subprocess.run(["bash", str(script), "internal", "3"], env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("exit_code=255"), 3)

    def test_readiness_deadline_interrupts_unresponsive_check(self):
        script = self.script("wait-ready.sh", '''remote_bounded() {
 if [[ "$*" == *"status --long"* ]]; then echo DIAGNOSTICS; return 0; fi
 timeout -k 1 "$1" bash -c 'sleep 30'
}
''')
        start = time.monotonic()
        result = subprocess.run(["bash", str(script), "service", "2"], env=dict(self.env, READY_TIMEOUT="1"), capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertLess(time.monotonic() - start, 4)
        self.assertIn("DIAGNOSTICS", result.stderr)
        self.assertIn("Readiness timeout", result.stderr)

    def test_expired_token_leaves_nginx_stopped_without_terraform(self):
        script = self.script("stop-public.sh", '''remote_bounded() {
 if [[ "$*" == *"cat /var/lib/lab/stage"* ]]; then echo 5; return 0; fi
 printf 'STOP\\n' >> "$ACTION_LOG"
}
session() { printf 'SESSION_FAILED\\n' >> "$ACTION_LOG"; return 1; }
TF="$FIXTURE_TF"
ROOT="$FIXTURE_ROOT"
''')
        self.command("terraform", 'printf "TERRAFORM\\n" >> "$ACTION_LOG"\n')
        result = subprocess.run(["bash", str(script)], env=dict(self.env, FIXTURE_ROOT=str(self.fixture), FIXTURE_TF=str(self.bin / "terraform")), capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.log.read_text().splitlines(), ["STOP", "SESSION_FAILED"])

    def test_login_path_variants_select_protected_location(self):
        config = (ROOT / "service/nginx/nginx.conf").read_text()
        pattern = re.search(r"location ~\* (\S+) \{", config).group(1)
        for path in ["/wp-login.php", "/wp-login.php/", "/wp-login.php/extra", "/xmlrpc.php/extra", "/WP-LOGIN.PHP/"]:
            self.assertIsNotNone(re.search(pattern, path, re.IGNORECASE), path)
        for path in ["/", "/my-wp-login.php", "/wp-login.php.png"]:
            self.assertIsNone(re.search(pattern, path, re.IGNORECASE), path)


if __name__ == "__main__":
    unittest.main()
