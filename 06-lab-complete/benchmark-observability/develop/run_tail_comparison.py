"""Run the three CP7 tail-latency experiments with isolated agent processes.

From repository root:
  python 06-lab-complete/benchmark-observability/develop/run_tail_comparison.py
Reports are written to the root reports/ directory. Requires develop requirements.
"""
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request


def main():
    develop = Path(__file__).resolve().parent
    root = develop.parents[2]
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    for rate in ("0", "0.03", "0.1"):
        env = {**os.environ, "AGENT_VERSION": "v2", "PORT": "8003",
               "MOCK_SLOW_RATE": rate, "MOCK_ERROR_RATE": "0.01", "PYTHONUTF8": "1"}
        # Discard server logs to avoid pipe backpressure under load.
        agent = subprocess.Popen([sys.executable, "app.py"], cwd=develop,
                                 env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if agent.poll() is not None:
                    raise RuntimeError("Agent exited before readiness")
                try:
                    urllib.request.urlopen("http://localhost:8003/ready", timeout=1).close()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Agent readiness timed out")
            result = subprocess.run([
                sys.executable, str(develop / "load_test.py"), "--url", "http://localhost:8003",
                "--requests", "300", "--concurrency", "20", "--out",
                str(reports / f"load_v2_slow_{rate}.json"),
            ], env=env)
            if result.returncode not in (0, 1):
                raise RuntimeError(f"Load test failed: {result.returncode}")
            if not (reports / f"load_v2_slow_{rate}.json").exists():
                raise RuntimeError("Load test did not write its report")
        finally:
            agent.terminate()
            try:
                agent.wait(timeout=10)
            except subprocess.TimeoutExpired:
                agent.kill()
                agent.wait()


if __name__ == "__main__":
    main()
