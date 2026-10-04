#!/usr/bin/env python3
"""Read-only local checks. Never creates cloud resources or runs Terraform apply."""
import ast
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
entries = []


def check(label, command, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    entries.append({"check": label, "status": "measured" if result.returncode == 0 else "failed", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "command": command, "cwd": str(cwd), "exit_code": result.returncode, "output": result.stdout + result.stderr, "processing": "none; local validation output; no VM logs"})
    print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}")


def available(env, default):
    candidate = os.environ.get(env, default)
    return shutil.which(candidate)


check("mocked VM configuration safety and repeat application", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
for file in sorted(ROOT.glob("scripts/*.sh")):
    check("shell syntax: " + file.name, ["bash", "-n", str(file)])
for file in sorted(list(ROOT.glob("scripts/*.py")) + list(ROOT.glob("service/*.py")) + list(ROOT.glob("tests/*.py"))):
    try:
        ast.parse(file.read_text(), filename=str(file))
        entries.append({"check": "Python AST: " + str(file.relative_to(ROOT)), "status": "measured", "command": ["ast.parse", str(file.relative_to(ROOT))], "exit_code": 0, "processing": "none"})
    except SyntaxError as error:
        entries.append({"check": "Python AST: " + file.name, "status": "failed", "exit_code": 1, "output": str(error)})
for file in [ROOT / "images.lock.json"] + sorted(ROOT.glob("monitoring/**/*.json")) + sorted(ROOT.glob("stages/config/*.json")) + sorted(ROOT.glob("docs/evidence/step*/manifest.json")):
    try:
        json.loads(file.read_text())
        entries.append({"check": "JSON decode: " + str(file.relative_to(ROOT)), "status": "measured", "command": ["json.loads", str(file.relative_to(ROOT))], "exit_code": 0, "processing": "none"})
    except json.JSONDecodeError as error:
        entries.append({"check": "JSON decode: " + str(file.relative_to(ROOT)), "status": "failed", "exit_code": 1, "output": str(error)})

try:
    import yaml
except ImportError:
    entries.append({"check": "YAML parse", "status": "not-acquired", "reason": "PyYAML unavailable; native Prometheus/blackbox checks are recorded separately"})
else:
    for file in sorted(ROOT.glob("monitoring/**/*.yml")) + sorted(ROOT.glob("terraform/**/*.yaml")):
        try:
            list(yaml.safe_load_all(file.read_text()))
            entries.append({"check": "YAML parse: " + str(file.relative_to(ROOT)), "status": "measured", "command": ["yaml.safe_load_all", str(file.relative_to(ROOT))], "exit_code": 0, "processing": "none"})
        except yaml.YAMLError as error:
            entries.append({"check": "YAML parse: " + str(file.relative_to(ROOT)), "status": "failed", "exit_code": 1, "output": str(error)})

terraform = available("TF", "terraform")
if terraform:
    check("Terraform version", [terraform, "version"])
    check("Terraform formatting", [terraform, "-chdir=" + str(ROOT / "terraform"), "fmt", "-check", "-recursive"])
    check("Terraform validate (requires prior init)", [terraform, "-chdir=" + str(ROOT / "terraform"), "validate"])
    check("Terraform mocked security plans (no cloud API)", [terraform, "-chdir=" + str(ROOT / "terraform"), "test", "-no-color"])
else:
    entries.append({"check": "Terraform fmt/validate", "status": "not-acquired", "reason": "Terraform binary not available; set TF or install then init -backend=false"})

promtool = available("PROMTOOL", "promtool")
if promtool:
    check("promtool version", [promtool, "--version"])
    check("Prometheus alert syntax", [promtool, "check", "rules", str(ROOT / "monitoring/prometheus/alerts.yml")])
    check("Prometheus alert behavior", [promtool, "test", "rules", "prometheus-rules.yml"], ROOT / "tests")
    with tempfile.TemporaryDirectory() as temporary:
        config = pathlib.Path(temporary) / "prometheus.yml"
        source = (ROOT / "monitoring/prometheus/prometheus.yml").read_text().replace("SERVICE_IP", "10.42.1.10").replace("MONITOR_IP", "10.42.1.11").replace("/etc/prometheus/alerts.yml", str(ROOT / "monitoring/prometheus/alerts.yml"))
        config.write_text(source)
        check("Prometheus generated configuration", [promtool, "check", "config", str(config)])
else:
    entries.append({"check": "Prometheus syntax and alert behavior", "status": "not-acquired", "reason": "promtool unavailable; set PROMTOOL to official binary"})

blackbox = available("BLACKBOX", "blackbox_exporter")
if blackbox:
    check("blackbox exporter version", [blackbox, "--version"])
    check("blackbox configuration", [blackbox, "--config.file=" + str(ROOT / "monitoring/blackbox.yml"), "--config.check"])
else:
    entries.append({"check": "blackbox configuration", "status": "not-acquired", "reason": "blackbox_exporter unavailable; set BLACKBOX to official binary"})

commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
tree = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
tracked = list(ROOT.glob("scripts/*")) + list(ROOT.glob("service/**/*")) + list(ROOT.glob("monitoring/**/*")) + list(ROOT.glob("terraform/**/*.tf")) + list(ROOT.glob("terraform/**/*.yaml")) + list(ROOT.glob("terraform/**/*.tftest.hcl")) + list(ROOT.glob("terraform/tests/fixtures/*")) + list(ROOT.glob("tests/*")) + [ROOT / "images.lock.json", ROOT / "terraform/.terraform.lock.hcl"]
utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
for entry in entries:
    entry.setdefault("utc", utc)
    entry.setdefault("processing", "none")
manifest = {"utc": utc, "commit": commit.stdout.strip() if commit.returncode == 0 else "uncommitted", "working_tree_has_changes": bool(tree.stdout.strip()), "kind": "measured-local-validation", "conditions": "Local host only; VM filesystem and process calls mocked; no cloud, container runtime, public reachability, restart or deletion validation", "versions": {"python": sys.version.split()[0]}, "source_sha256": {str(file.relative_to(ROOT)): hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(tracked) if file.is_file()}, "entries": entries, "unverified": ["OCI create/apply/destroy", "Podman image startup", "systemd reboot recovery", "SELinux/firewall live enforcement", "database backup and restore", "public access and separate-source denial", "Grafana rendered dashboards"], "screenshots": "not-acquired"}
destination = ROOT / "docs/evidence/local-review.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print("Evidence: docs/evidence/local-review.json")
sys.exit(1 if any(entry["status"] == "failed" for entry in entries) else 0)
