#!/usr/bin/env python3
"""Validate Prometheus active scrape targets; reading JSON alone is insufficient."""
import json
import sys
from collections import Counter

try:
    payload = json.load(sys.stdin)
    if payload.get("status") != "success":
        raise ValueError("Prometheus API did not report success")
    targets = payload["data"]["activeTargets"]
    counts = Counter(target.get("labels", {}).get("job") for target in targets)
    expected = {"prometheus": 1, "node": 2, "blackbox": 2, "blackbox-self": 1}
    if counts != expected:
        raise ValueError(f"unexpected job counts: {dict(counts)}; expected {expected}")
    unhealthy = [f'{target.get("labels", {}).get("job")}/{target.get("labels", {}).get("instance")}: {target.get("health", "missing")}' for target in targets if target.get("health") != "up"]
    if unhealthy:
        raise ValueError("unhealthy scrape targets: " + "; ".join(unhealthy))
except (ValueError, KeyError, TypeError) as error:
    print(str(error), file=sys.stderr)
    sys.exit(1)
print("All 6 expected Prometheus scrape targets are up")
