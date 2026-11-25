"""Run real error/latency fault injection and record first observed firing times.

Requires the observability stack already running. Keeps the fault configuration
running afterward so the user can capture Grafana/Jaeger/Prometheus screenshots.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--phase", choices=("error-only", "combined"), default="combined")
    args = parser.parse_args()
    production = Path(__file__).resolve().parent
    reports = production.parents[2] / "reports"
    reports.mkdir(exist_ok=True)
    slow_rate = "0.03" if args.phase == "error-only" else "0.3"
    duration = "2m" if args.phase == "error-only" else "4m"
    prefix = "chaos_error_only" if args.phase == "error-only" else "chaos"
    env = {**os.environ, "MOCK_ERROR_RATE": "0.2", "MOCK_SLOW_RATE": slow_rate}
    compose = [args.docker, "compose", "-p", "k5-day14-observability"]
    report = {"parameters": {"MOCK_ERROR_RATE": "0.2", "MOCK_SLOW_RATE": slow_rate,
                             "users": 100, "spawn_rate": 10, "duration": duration},
              "first_firing_seconds": {}, "baseline_wait_samples": [], "samples": []}
    output = reports / f"{prefix}_alerts.json"
    # Do not attribute an alert already active during the previous benchmark
    # to the new fault. Wait for a full quiet scrape window and record it.
    for _ in range(30):
        with urllib.request.urlopen("http://localhost:9090/api/v1/alerts", timeout=5) as response:
            active = json.load(response)["data"]["alerts"]
        report["baseline_wait_samples"].append({"at_utc": datetime.now(timezone.utc).isoformat(), "alerts": active})
        if not any(a["labels"]["alertname"] in ("AgentHighErrorRate", "AgentHighLatencyP95") for a in active):
            break
        time.sleep(5)
    else:
        raise SystemExit("Error/latency alerts did not become inactive before fault timing")
    report["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["preexisting_alerts"] = [a["labels"]["alertname"] for a in active if a["state"] == "firing"]
    start = time.monotonic()
    subprocess.run(compose + ["up", "-d", "--no-deps", "--scale", "agent=3", "agent"],
                   cwd=production, env=env, check=True)
    result_dir = production / "benchmark-results"
    result_dir.mkdir(exist_ok=True)
    with (result_dir / f"{prefix}.log").open("w", encoding="utf-8") as log:
        load = subprocess.Popen(compose + ["run", "--rm", "--no-deps", "locust", "-f", "/mnt/locust/locustfile.py",
                               "--host", "http://nginx", "--headless", "-u", "100", "-r", "10", "-t", duration,
                               "--csv", f"/mnt/results/{prefix}"], cwd=production, env=env, stdout=log, stderr=subprocess.STDOUT)
        while load.poll() is None:
            elapsed = round(time.monotonic() - start, 1)
            try:
                with urllib.request.urlopen("http://localhost:9090/api/v1/alerts", timeout=5) as response:
                    alerts = json.load(response)["data"]["alerts"]
                sample = {"elapsed_seconds": elapsed, "alerts": alerts}
                for alert in alerts:
                    if alert["state"] == "firing":
                        name = alert["labels"]["alertname"]
                        if name not in report["preexisting_alerts"]:
                            report["first_firing_seconds"].setdefault(name, elapsed)
            except OSError as exc:
                sample = {"elapsed_seconds": elapsed, "error": str(exc)}
            report["samples"].append(sample)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(5)
        report["locust_exit_code"] = load.returncode
    report["duration_seconds"] = round(time.monotonic() - start, 1)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["first_firing_seconds"], indent=2))
    required = {"AgentHighErrorRate"} if args.phase == "error-only" else {"AgentHighErrorRate", "AgentHighLatencyP95"}
    if not required.issubset(report["first_firing_seconds"]):
        raise SystemExit("Both required fault alerts have not fired; inspect real evidence")


if __name__ == "__main__":
    main()
