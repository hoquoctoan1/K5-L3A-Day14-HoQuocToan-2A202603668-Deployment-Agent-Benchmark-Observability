"""Run supplied Part 1/4 examples over HTTP without recording credentials."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8014"


def request(path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={
        "Content-Type": "application/json", **(headers or {})})
    try:
        response = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, json.loads(response.read())


def run_example(folder, check):
    env = {**os.environ, "JWT_SECRET": secrets.token_urlsafe(48), "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app",
                             "--host", "127.0.0.1", "--port", "8014"],
                            cwd=ROOT / folder, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise RuntimeError(f"Server exited: {folder}")
            try:
                request("/openapi.json")
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Server startup timeout")
        return check()
    finally:
        proc.terminate()
        proc.wait(timeout=15)


def part1():
    query, answer = request("/ask?question=Hello", {})
    json_status, _ = request("/ask", {"question": "Hello"})
    assert query == 200 and answer.get("answer")
    assert json_status == 422
    return {"query_post_status": query, "json_only_status": json_status,
            "answer_present": bool(answer.get("answer"))}


def part4():
    no_auth, _ = request("/ask", {"question": "Hello"})
    login, data = request("/auth/token", {"username": "student", "password": "demo123"})
    assert login == 200
    headers = {"Authorization": "Bearer " + data["access_token"]}
    statuses = [request("/ask", {"question": "What is Docker?"}, headers)[0]
                for _ in range(11)]
    assert no_auth == 401 and statuses == [200] * 10 + [429]
    return {"missing_auth_status": no_auth, "login_status": login,
            "authenticated_statuses": statuses, "credentials": "omitted"}


result = {"transport": "real HTTP via localhost uvicorn; Windows Python",
          "part1": run_example("01-localhost-vs-production/develop", part1),
          "part4": run_example("04-api-gateway/production", part4)}
out = ROOT / "reports/examples_runtime.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
