"""Run the real deployment shell script with a simulated WordPress response.

WordPress bootstrap can exit zero while returning an installer page or DB error.
These cases must stop before any VM reconfiguration or Terraform invocation.
"""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PublicInstallationGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = pathlib.Path(self.temp.name)
        scripts = self.fixture / "scripts"
        scripts.mkdir()
        config = self.fixture / "stages/config"
        config.mkdir(parents=True)
        (config / "04.json").write_text(json.dumps({"public_web": True}))
        shutil.copyfile(ROOT / "scripts/deploy-stage.sh", scripts / "deploy-stage.sh")
        (scripts / "common.sh").write_text('''#!/usr/bin/env bash
set -euo pipefail
ROOT=${FIXTURE_ROOT:?}
TF="$ROOT/fake-terraform"
session() { printf 'SESSION\\n' >> "$ACTION_LOG"; }
remote() {
 case "$*" in
  *"php -r"*)
   printf 'INSTALLATION_CHECK\\n' >> "$ACTION_LOG"
   printf '%s' "$GATE_OUTPUT"
   return "$GATE_EXIT"
   ;;
  *)
   printf 'NEXT_STAGE_OPERATION\\n' >> "$ACTION_LOG"
   return 42
   ;;
 esac
}
''')
        fake_tf = self.fixture / "fake-terraform"
        fake_tf.write_text('#!/usr/bin/env bash\nprintf "TERRAFORM_CALLED\\n" >> "$ACTION_LOG"\nexit 99\n')
        fake_tf.chmod(0o755)
        self.log = self.fixture / "actions.txt"

    def deploy(self, output, code):
        env = dict(os.environ, FIXTURE_ROOT=str(self.fixture), ACTION_LOG=str(self.log), GATE_OUTPUT=output, GATE_EXIT=str(code))
        result = subprocess.run(["bash", str(self.fixture / "scripts/deploy-stage.sh"), "4"], env=env, capture_output=True, text=True, timeout=10)
        actions = self.log.read_text().splitlines()
        return result, actions

    def assert_refused(self, output, code):
        result, actions = self.deploy(output, code)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(actions, ["SESSION", "INSTALLATION_CHECK"])
        self.assertNotIn("TERRAFORM_CALLED", actions)

    def test_zero_exit_without_output_is_refused(self):
        self.assert_refused("", 0)

    def test_zero_exit_with_database_error_page_is_refused(self):
        self.assert_refused("<html>Error establishing a database connection</html>", 0)

    def test_nonzero_exit_with_success_marker_is_refused(self):
        self.assert_refused("LAB_INSTALLED", 1)

    def test_extra_output_around_success_marker_is_refused(self):
        self.assert_refused("LAB_INSTALLED\n<html>Installer</html>", 0)

    def test_exact_success_marker_reaches_next_stage_check(self):
        result, actions = self.deploy("LAB_INSTALLED", 0)
        # Deliberately stop at the next operation: no VM or Terraform is executed.
        self.assertEqual(result.returncode, 42)
        self.assertEqual(actions, ["SESSION", "INSTALLATION_CHECK", "NEXT_STAGE_OPERATION"])
        self.assertNotIn("TERRAFORM_CALLED", actions)


if __name__ == "__main__":
    unittest.main()
