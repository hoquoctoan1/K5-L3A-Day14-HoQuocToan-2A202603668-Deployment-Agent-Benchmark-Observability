"""Run the CP6 self-test against the deployed Part 6 agent.

Usage: AGENT_API_KEY=... python scripts/verify_public_url.py https://your-app.onrender.com
The key is read from the environment only and is masked in every output.
Writes reports/public_url_checks.json and prints a transcript suitable for a screenshot.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def call(method, url, key=None, body=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    base = sys.argv[1].rstrip("/")
    key = os.environ.get("AGENT_API_KEY", "")
    if len(key) < 16:
        raise SystemExit("AGENT_API_KEY missing or too short; set the real key from the platform")
    masked = "********"
    question = {"question": "Hello"}
    steps = [
        ("GET /health", "GET", "/health", None, None, 200),
        ("GET /ready", "GET", "/ready", None, None, 200),
        ("POST /ask (no key)", "POST", "/ask", None, question, 401),
        ("POST /ask (X-API-Key)", "POST", "/ask", key, question, 200),
    ]
    results = []
    for name, method, path, k, body, expected in steps:
        status, text = call(method, base + path, k, body)
        results.append({"check": name, "expected": expected, "status": status,
                        "passed": status == expected, "body": text[:200].replace(key, masked)})
    # Rate limit: send requests until 429 or 20 attempts.
    rate = []
    for i in range(1, 21):
        status, _ = call("POST", base + "/ask", key, {"question": f"rate test {i}"})
        rate.append(status)
        if status == 429:
            break
        time.sleep(0.1)
    report = {"base_url": base, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "api_key": "masked","checks": results,
              "rate_limit_statuses": rate, "rate_limit_429_at": rate.index(429) + 1 if 429 in rate else None}
    out = Path(__file__).resolve().parents[1] / "reports" / "public_url_checks.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Base URL: {base}   (X-API-Key: {masked})")
    for r in results:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['check']:<24} expected {r['expected']} got {r['status']}  {r['body'][:90]}")
    print(f"Rate limit: statuses {rate} -> 429 at request #{report['rate_limit_429_at']}")
    ok = all(r["passed"] for r in results) and report["rate_limit_429_at"] is not None
    print("RESULT:", "ALL PASS" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
