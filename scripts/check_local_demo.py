"""Read-only live API check against the seeded local demo (standard library)."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--credentials", type=Path, default=Path("infrastructure/demo-credentials.json"))
    args = parser.parse_args()
    org = json.loads(args.credentials.read_text())["organizations"][0]
    headers = {"Authorization": "Bearer " + org["operator_token"], "X-Organization-ID": org["id"]}

    def get(path):
        with urlopen(Request(args.url + "/api/v1" + path, headers=headers), timeout=10) as response:
            return json.load(response)

    assert get("/health")["status"] == "ok"
    snapshot = get("/devices/latest")
    positioned = [d for d in snapshot["devices"] if d["position"]]
    assert positioned, "Run the simulator first"
    now = datetime.now(timezone.utc)
    query = urlencode({"from": (now - timedelta(days=1)).isoformat(), "to": now.isoformat()})
    points = get(f"/assets/{positioned[0]['position']['asset_id']}/positions?{query}")["points"]
    assert points
    assert [p["recorded_at"] for p in points] == sorted(p["recorded_at"] for p in points)
    ids = [(p["device_id"], p["sequence_number"]) for p in points]
    assert len(ids) == len(set(ids))
    print(f"PASS: health, {len(snapshot['devices'])} scoped devices, {len(positioned)} latest fixes, "
          f"{len(points)} ordered unique history samples for first positioned asset")


if __name__ == "__main__":
    main()
