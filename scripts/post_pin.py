#!/usr/bin/env python3
"""Post the next queued pin to Pinterest via the Make.com scenario.

Picks the first file (sorted) in queue/, PATCHes the Make scenario blueprint
with the pin fields, runs it (start -> run -> stop), then moves the queue file
to posted/ with the execution result. Exits non-zero on failure so the queue
file stays put for the next attempt.

Env: MAKE_TOKEN, GITHUB_REPOSITORY (e.g. "user/fnf-pins")
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

MAKE_BASE = "https://eu1.make.com/api/v2"
SCENARIO_ID = 5596478
CONNECTION_ID = 7182539


def make_api(path, method="GET", body=None):
    req = urllib.request.Request(
        f"{MAKE_BASE}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Token {os.environ['MAKE_TOKEN']}",
            "Content-Type": "application/json",
            # Make.com 前面的 Cloudflare 會用 error 1010 擋 Python-urllib 預設 UA
            "User-Agent": "curl/8.7.1",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        code = e.code
    try:
        return code, json.loads(raw or "{}")
    except json.JSONDecodeError:
        return code, {"raw": raw[:500]}


def main() -> int:
    queued = sorted(f for f in os.listdir("queue") if f.endswith(".json"))
    if not queued:
        print("queue is empty, nothing to post")
        return 0

    qfile = queued[0]
    with open(f"queue/{qfile}", encoding="utf-8") as f:
        pin = json.load(f)

    repo = os.environ["GITHUB_REPOSITORY"]
    image_url = f"https://raw.githubusercontent.com/{repo}/main/" + urllib.parse.quote(pin["image"])
    print(f"posting {qfile}: {pin['title']}")
    print(f"image: {image_url}")

    blueprint = {
        "flow": [{
            "id": 1, "module": "pinterest:createPin", "version": 2,
            "parameters": {"__IMTCONN__": CONNECTION_ID},
            "mapper": {
                "title": pin["title"],
                "description": pin["description"],
                "link": pin["link"],
                "board_id": pin["board_id"],
                "media_source": {"source_type": "image_url", "url": image_url},
            },
            "metadata": {"designer": {"x": 0, "y": 0}},
        }],
        "name": "FuelnFitHub Pinterest Pin Poster",
        "metadata": {
            "instant": False, "version": 1, "zone": "eu1.make.com",
            "scenario": {
                "autoCommit": True, "maxErrors": 3, "roundtrips": 1,
                "sequential": False, "dataloss": False, "dlq": False,
                "freshVariables": False, "autoCommitTriggerLast": True,
            },
            "designer": {"orphans": []}, "notes": [],
            "schedulingState": {"type": "on-demand"},
        },
    }

    status, resp = make_api(f"/scenarios/{SCENARIO_ID}", "PATCH", {
        "blueprint": json.dumps(blueprint),
        "scheduling": json.dumps({"type": "on-demand"}),
    })
    print(f"PATCH blueprint: HTTP {status}")
    if status != 200:
        print(json.dumps(resp)[:500])
        return 1

    make_api(f"/scenarios/{SCENARIO_ID}/start", "POST", {})
    run_status, run_resp = make_api(f"/scenarios/{SCENARIO_ID}/run", "POST", {"responsive": True})
    make_api(f"/scenarios/{SCENARIO_ID}/stop", "POST", {})

    execution_id = run_resp.get("executionId")
    print(f"run: HTTP {run_status}, executionId={execution_id}, status={run_resp.get('status')}")

    # run 回應的 status:1 + executionId 就是成功依據；logs 只做參考輸出
    # （logs 端點最新一筆常是 stop 事件，沒有 status 欄位，不能拿來判定）
    time.sleep(3)
    _, logs = make_api(f"/scenarios/{SCENARIO_ID}/logs?pg%5Blimit%5D=5")
    for log in logs.get("scenarioLogs", []):
        if log.get("imtId", "").endswith(str(execution_id)):
            print(f"log check: status={log.get('status')} operations={log.get('operations')}")

    if run_status != 200 or not execution_id or run_resp.get("status") != 1:
        print("PIN POST FAILED — queue file left in place")
        print(json.dumps(run_resp)[:500])
        return 1

    pin["executionId"] = execution_id
    pin["posted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(f"posted/{qfile}", "w", encoding="utf-8") as f:
        json.dump(pin, f, ensure_ascii=False, indent=2)
    os.remove(f"queue/{qfile}")
    print(f"SUCCESS — moved to posted/{qfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
