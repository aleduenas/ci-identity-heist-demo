"""Summarize retained decisions and observed live delays; never relabel fixtures as live."""

import argparse
import json
from datetime import datetime
from pathlib import Path


def seconds(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    duration = (datetime.fromisoformat(end.replace("Z", "+00:00"))
                - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds()
    return round(duration, 3) if duration >= 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    document = json.loads(args.evidence.read_text(encoding="utf-8-sig"))
    live = document.get("mode") == "live_cloudtrail_lookup_and_independent_github_api"
    rows = []
    for entry in document["records"]:
        result = entry["result"]
        event_time = result.get("event_time_utc")
        rows.append({
            "decision": result["decision"], "event_id": result.get("event_id"),
            "run_url": result.get("run_url"),
            "alert": (entry.get("alert") or {}).get("title"),
            "observed_log_delay_seconds": seconds(
                event_time, entry.get("first_observed_searchable_utc"),
            ) if live else None,
            "observed_ttd_seconds": seconds(
                event_time, entry.get("alert_available_utc"),
            ) if live else None,
        })
    print(json.dumps({"mode": document["mode"], "observations": rows,
                      "note": document.get("measurement_note")}, indent=2))


if __name__ == "__main__":
    main()
