"""Security's view: independently watch CloudTrail + GitHub and raise the detection alert live.

Runs outside the PR's control on the operator workstation. The GitHub credential comes from
GITHUB_TOKEN/GH_TOKEN or the local Git credential manager, is held in memory only, and is
never printed or written to evidence.
"""

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

from scripts.demo import gh
from scripts.demo.github_api import get_token
from scripts.demo.ops import CACHE, activate, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=45, help="How long to keep watching")
    parser.add_argument("--lookback", type=int, default=5, help="Minutes of history to include")
    args = parser.parse_args()
    activate()
    values, repo = outputs(), gh.repository()
    os.environ["DETECTION_GITHUB_TOKEN"] = get_token()
    start = (datetime.now(UTC) - timedelta(minutes=args.lookback)).isoformat()
    evidence = (CACHE.parent / "docs/detection/generated"
                / f"live-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json")
    print(f"Watching role {values['detection_demo_role_arn']} from {start}\n"
          f"Evidence file: {evidence.relative_to(CACHE.parent)}\n"
          "CloudTrail usually makes STS events searchable within ~1-5 minutes.\n", flush=True)
    sys.argv = [
        "collect", "--role-arn", values["detection_demo_role_arn"], "--repository", repo["full"],
        "--subject-prefix", repo["prefix"], "--region", values["aws_region"], "--start", start,
        "--follow-seconds", str(args.minutes * 60), "--poll-seconds", "15",
        "--output", str(evidence),
    ]
    from scripts.detection.collect import main as collect

    try:
        collect()
    except KeyboardInterrupt:
        print("\nStopped watching; evidence kept at", evidence)


if __name__ == "__main__":
    main()
