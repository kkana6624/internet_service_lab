"""Execute VM provisioning against a temporary filesystem and mocked commands.

This checks generation and secret reuse, not OCI, Podman, SELinux or reboot behavior.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]


class VMGeneration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vm = pathlib.Path(self.temp.name)
        self.calls = []

    def apply(self, role="service", stage=3, public="false", cidr="203.0.113.8/32", fail_pull=False, firewall_only=False):
        facade = types.ModuleType("pathlib")
        facade.__dict__.update(pathlib.__dict__)
        def vm_path(value):
            value = str(value)
            if value.startswith(("/etc/", "/var/lib/", "/usr/local/")):
                target = self.vm / value.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                return target
            return pathlib.Path(value)
        facade.Path = vm_path
        def command(args, **kwargs):
            self.calls.append(tuple(args))
            if fail_pull and args[:2] == ("podman", "pull"):
                raise subprocess.CalledProcessError(125, args)
            return subprocess.CompletedProcess(args, 0)
        original_write = pathlib.Path.write_text
        def root_write(path, *args, **kwargs):
            # Production runs as root and can replace its owner-read-only files.
            if path.exists():
                path.chmod(path.stat().st_mode | 0o200)
            return original_write(path, *args, **kwargs)
        argv = ["apply-vm.py", role, str(stage), "10.42.1.10", "10.42.1.11", cidr, public]
        if firewall_only: argv.append("--firewall-only")
        with patch.dict(sys.modules, {"pathlib": facade}), patch.object(sys, "argv", argv), patch("subprocess.run", side_effect=command), patch("os.chown"), patch.object(pathlib.Path, "write_text", root_write):
            scope = {"__file__": str(ROOT / "scripts/apply-vm.py"), "__name__": "__main__"}
            try:
                exec(compile((ROOT / "scripts/apply-vm.py").read_text(), scope["__file__"], "exec"), scope)
            except SystemExit as exc:
                if exc.code not in (None, 0):
                    raise

    def unit(self, name):
        return json.loads((self.vm / f"etc/lab/units/{name}.json").read_text())

    def test_secrets_reused_and_never_in_container_arguments(self):
        self.apply()
        password = (self.vm / "var/lib/lab/db-password").read_text()
        self.assertEqual((self.vm / "var/lib/lab/db-password").stat().st_mode & 0o777, 0o400)
        self.apply()
        self.assertEqual((self.vm / "var/lib/lab/db-password").read_text(), password)
        for name in ["db", "wordpress", "nginx", "node"]:
            self.assertNotIn(password, json.dumps(self.unit(name)))
        self.assertNotIn("-p", self.unit("db"))
        self.assertIn("127.0.0.1:8080:80", self.unit("wordpress"))

    def test_private_web_includes_monitor_and_excludes_public_source(self):
        self.apply()
        guard = (self.vm / "etc/lab/guard.nft").read_text()
        self.assertIn("ip saddr 10.42.1.11 tcp dport 80 accept", guard)
        self.assertNotIn("ip saddr 0.0.0.0/0 tcp dport 80 accept", guard)
        self.assertIn("tcp dport {3000,3306,8080,9090,9115} drop", guard)
        self.assertIn("tcp dport 9100 drop", guard)

    def test_stage_one_persists_stage_without_containers(self):
        self.apply(stage=1)
        self.assertEqual((self.vm / "var/lib/lab/stage").read_text().strip(), "1")
        self.assertFalse(any(call[0] == "podman" for call in self.calls))

    def test_monitoring_loopback_and_file_secret(self):
        self.apply(role="monitoring")
        self.assertIn("--web.listen-address=127.0.0.1:9090", self.unit("prometheus"))
        self.assertIn("--web.listen-address=127.0.0.1:9115", self.unit("blackbox"))
        self.assertIn("GF_SERVER_HTTP_ADDR=127.0.0.1", self.unit("grafana"))
        self.assertIn("GF_SECURITY_ADMIN_PASSWORD__FILE=/run/secrets/admin", self.unit("grafana"))
        self.assertNotIn("SERVICE_IP", (self.vm / "etc/lab/prometheus.yml").read_text())

    def test_protection_and_containment(self):
        self.apply(stage=5, public="true")
        nginx = (self.vm / "etc/lab/nginx.conf").read_text()
        self.assertIn("allow 203.0.113.8/32; deny all; limit_req", nginx)
        self.apply(stage=5, public="false")
        self.assertIn("allow 203.0.113.8/32; deny all; limit_req", (self.vm / "etc/lab/nginx.conf").read_text())
        self.assertNotIn("0.0.0.0/0", (self.vm / "etc/lab/guard.nft").read_text())

    def test_reject_world_management_before_mutation(self):
        with self.assertRaises(SystemExit):
            self.apply(cidr="0.0.0.0/0")
        self.assertEqual(self.calls, [])
        self.assertFalse((self.vm / "etc").exists())

    def test_failed_image_pull_does_not_claim_stage_completion(self):
        self.apply(stage=1)
        with self.assertRaises(subprocess.CalledProcessError):
            self.apply(stage=2, fail_pull=True)
        self.assertEqual((self.vm / "var/lib/lab/stage").read_text().strip(), "1")

    def test_containment_restores_network_without_redeploy_or_secret_change(self):
        self.apply(stage=5, public="true")
        password = (self.vm / "var/lib/lab/db-password").read_text()
        self.calls.clear()
        self.apply(stage=5, firewall_only=True)
        reload = self.calls.index(("firewall-cmd", "--reload"))
        guard = self.calls.index(("systemctl", "reload-or-restart", "lab-firewall"))
        network = self.calls.index(("podman", "network", "reload", "--all"))
        self.assertLess(reload, guard)
        self.assertLess(guard, network)
        self.assertIn("ExecReload=/usr/local/libexec/lab-firewall", (self.vm / "etc/systemd/system/lab-firewall.service").read_text())
        self.assertFalse(any(call[:2] == ("podman", "pull") for call in self.calls))
        self.assertEqual(password, (self.vm / "var/lib/lab/db-password").read_text())
        self.assertEqual((self.vm / "var/lib/lab/stage").read_text().strip(), "5")


if __name__ == "__main__":
    unittest.main()
