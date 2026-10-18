"""Run the detector on clearly labeled invented examples without any network or AWS access."""

import argparse
import json
from pathlib import Path

from .alert import render
from .detector import classify
from .evidence import safe_event, safe_run, utc_now
from .sample_data import PREFIX, REPOSITORY, ROLE, sample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pr, pr_run = sample()
    normal, normal_run = sample("workflow_dispatch", 1002)
    cases = [("N2 fixture", normal, normal_run), ("A2 spoofed-session fixture", pr, pr_run),
             ("Missing independent context fixture", pr, None)]
    records = []
    for label, event, run in cases:
        result = classify(event, run, role_arn=ROLE, repository=REPOSITORY, subject_prefix=PREFIX)
        records.append({"label": label, "aws_event": safe_event(event),
                        "github_run": safe_run(run) if run else None, "result": result,
                        "alert": render(result)})
    document = {
        "mode": "invented_mock_replay", "recorded_utc": utc_now(), "records": records,
        "measurement_note": "No live identity, delivery, correlation or latency was measured.",
    }
    output = json.dumps(document, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
