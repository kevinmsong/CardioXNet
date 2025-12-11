"""
Submit an analysis to the local CardioXNet API and poll until completion.
Saves the final results JSON to outputs/<analysis_id>_report_api.json

Usage:
  .\venv\Scripts\python.exe tools\submit_and_monitor_analysis.py

This script uses only the Python stdlib so it works without extra packages.
"""

import urllib.request
import urllib.error
import json
import time
import sys
import os

API_BASE = "http://127.0.0.1:8000/api/v1"
SEEDS = ["TTN", "MYH7", "MYBPC3", "TNNT2", "LMNA"]
TIMEOUT_SECONDS = 900  # 15 minutes
POLL_INTERVAL = 5


def wait_for_server(timeout=30):
    url = API_BASE + "/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return True
        except Exception:
            time.sleep(0.5)
    return False


def post_json(path, payload, timeout=10):
    url = API_BASE + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def get_json(path, timeout=10):
    url = API_BASE + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def main():
    print("Waiting for API server at http://127.0.0.1:8000/")
    if not wait_for_server(30):
        print("ERROR: API server did not respond within 30s. Make sure the backend is running.")
        sys.exit(2)

    payload = {
        "seed_genes": SEEDS,
        "config_overrides": {},
        "disease_context": "cardiac"
    }

    print(f"Submitting analysis with seeds: {SEEDS}")
    try:
        resp = post_json("/analysis/run", payload)
    except urllib.error.HTTPError as e:
        print("HTTP error when submitting analysis:", e.read().decode())
        sys.exit(2)
    except Exception as e:
        print("Failed to submit analysis:", e)
        sys.exit(2)

    analysis_id = resp.get("analysis_id")
    if not analysis_id:
        print("No analysis_id returned by API:", resp)
        sys.exit(2)

    print(f"Analysis submitted. ID: {analysis_id}")

    start_time = time.time()
    deadline = start_time + TIMEOUT_SECONDS
    status = None

    while time.time() < deadline:
        try:
            s = get_json(f"/analysis/{analysis_id}/status")
        except Exception as e:
            print("Error fetching status, retrying:", e)
            time.sleep(POLL_INTERVAL)
            continue

        status = s.get("status")
        current_stage = s.get("current_stage")
        progress = s.get("progress_percentage") or s.get("progress")
        print(f"Status: {status}, stage: {current_stage}, progress: {progress}")

        if status == "completed":
            break
        if status == "failed":
            print("Analysis failed. Exiting.")
            sys.exit(1)

        time.sleep(POLL_INTERVAL)

    if status != "completed":
        print("Timeout waiting for analysis to complete")
        sys.exit(3)

    print("Fetching final results...")
    try:
        results = get_json(f"/analysis/{analysis_id}/results")
    except Exception as e:
        print("Failed to fetch results:", e)
        sys.exit(2)

    out_dir = "outputs"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{analysis_id}_report_api.json")
    with open(out_path, "w", encoding="utf8") as fh:
        json.dump(results, fh, indent=2)

    print(f"Saved results to {out_path}")
    # Also print short summary
    ranked = results.get("hypotheses") or results.get("ranked_hypotheses") or {}
    if isinstance(ranked, dict):
        total = ranked.get("total_count") or len(ranked.get("hypotheses", []))
    elif isinstance(ranked, list):
        total = len(ranked)
    else:
        total = 0
    print(f"Hypotheses returned: {total}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
