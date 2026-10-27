"""Synthetic fleet with persistent replay queue; standard library only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROUTE = [(1.285, 103.845), (1.29, 103.853), (1.299, 103.859), (1.305, 103.852), (1.30, 103.841), (1.29, 103.838)]


def sample(device_id, sequence, tick, index, interval):
    # Move at roughly 30 km/h along a synthetic polygon; stop for 30 seconds each lap.
    seconds = tick * interval + index * 37
    moving = seconds % 630 < 600
    progress = min(seconds % 630, 600) / 100
    segment = int(progress) % len(ROUTE)
    fraction = progress % 1
    a, b = ROUTE[segment], ROUTE[(segment + 1) % len(ROUTE)]
    fix = not 35 <= (tick + index * 3) % 90 <= 44
    location = {"fix_valid": fix, "satellites": 12 if fix else 0}
    if fix:
        location.update(latitude=a[0] + (b[0] - a[0]) * fraction,
                        longitude=a[1] + (b[1] - a[1]) * fraction,
                        speed_kmh=math.hypot((b[0] - a[0]) * 111, (b[1] - a[1]) * 111) * 36 if moving else 0,
                        heading_deg=math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360, hdop=0.9)
    return {"schema_version": 1, "device_id": device_id, "sequence_number": sequence,
            "recorded_at": datetime.now(timezone.utc).isoformat(), "location": location,
            "status": {"network_type": "simulator", "external_power": True, "firmware_version": "sim-0.1.0"}}


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state))
    temp.replace(path)


def upload(url, device, samples):
    started = time.monotonic()
    request = Request(url + "/api/v1/telemetry/batch", data=json.dumps({"samples": samples}).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + device["token"]})
    try:
        with urlopen(request, timeout=10) as response:
            ack = json.load(response)
        return set(ack["accepted"] + ack["duplicates"]), time.monotonic() - started, None
    except (URLError, HTTPError, TimeoutError) as exc:
        return set(), time.monotonic() - started, str(exc)


def main(args):
    credentials = json.loads(args.credentials.read_text())
    org = next(o for o in credentials["organizations"] if o["id"] == args.organization)
    devices = org["devices"][:args.devices]
    if len(devices) != args.devices:
        raise SystemExit("Not enough seeded devices; rerun seed with --devices")
    state = json.loads(args.state.read_text()) if args.state.exists() else {"tick": 0, "devices": {}}
    durations, failures, acknowledged = [], 0, 0
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=min(32, args.devices)) as pool:
        for _ in range(args.ticks) if args.ticks else iter(int, 1):
            cycle = time.monotonic()
            futures = []
            for index, device in enumerate(devices):
                entry = state["devices"].setdefault(device["device_id"], {"sequence": time.time_ns() // 1000, "queue": []})
                if len(entry["queue"]) >= 10000:
                    raise RuntimeError("Queue full: stopping acquisition without discarding unacknowledged data")
                entry["sequence"] += 1
                entry["queue"].append(sample(device["device_id"], entry["sequence"], state["tick"], index, args.interval))
            save(args.state, state)  # Persist before any network send.
            for index, device in enumerate(devices):
                entry = state["devices"][device["device_id"]]
                if 12 <= (state["tick"] + index) % 60 < 28:
                    continue  # Simulated network outage; acquisition continues.
                batch = entry["queue"][-199:][::-1]  # Newest first intentionally exercises late arrival.
                if batch:
                    batch = batch + [batch[0]]  # Deliberate duplicate in every batch.
                    futures.append((entry, pool.submit(upload, args.url, device, batch)))
            for entry, future in futures:
                ack, duration, error = future.result()
                durations.append(duration)
                failures += bool(error)
                acknowledged += len(ack)
                entry["queue"] = [p for p in entry["queue"] if p["sequence_number"] not in ack]
                if error:
                    print(f"Upload failed; queue retained: {error}", flush=True)
            state["tick"] += 1
            save(args.state, state)
            pending = sum(len(d["queue"]) for d in state["devices"].values())
            print(f"tick={state['tick']} acknowledged={acknowledged} pending={pending} failures={failures}", flush=True)
            time.sleep(max(0, args.interval - (time.monotonic() - cycle)))
    elapsed = time.monotonic() - started
    durations.sort()
    print(json.dumps({"devices": len(devices), "acknowledged": acknowledged, "failures": failures,
                      "elapsed_seconds": round(elapsed, 2), "samples_per_second": round(acknowledged / elapsed, 2),
                      "request_p95_seconds": durations[min(len(durations) - 1, int(len(durations) * .95))] if durations else None}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--credentials", type=Path, default=Path("infrastructure/demo-credentials.json"))
    parser.add_argument("--organization", default="demo")
    parser.add_argument("--devices", type=int, choices=range(1, 101), default=10)
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--ticks", type=int, default=0, help="0 runs until interrupted")
    parser.add_argument("--state", type=Path, default=Path("simulator/.state/queue.json"))
    options = parser.parse_args()
    if options.interval <= 0 or options.ticks < 0:
        parser.error("interval must be positive and ticks nonnegative")
    try:
        main(options)
    except KeyboardInterrupt:
        print("Stopped; persistent queue retained for next run.")
