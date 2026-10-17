"""Poll CloudTrail independently and classify accepted GitHub subjects against GitHub's API."""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from .alert import render
from .detector import classify
from .evidence import role_arn, safe_event, utc_now
from .github import get_run
from .subject import parse_subject


def lookup(sts_events, start: datetime, end: datetime):
    """Do not use raw records as evidence output; response credentials stay in memory."""
    parameters = {
        "LookupAttributes": [{"AttributeKey": "EventName",
                              "AttributeValue": "AssumeRoleWithWebIdentity"}],
        "StartTime": start, "EndTime": end, "MaxResults": 50,
    }
    while True:
        response = sts_events.lookup_events(**parameters)
        for event in response.get("Events", []):
            yield safe_event(json.loads(event["CloudTrailEvent"]))
        if not response.get("NextToken"):
            break
        parameters["NextToken"] = response["NextToken"]
        time.sleep(0.6)


def record(event: dict, arguments, github_token: str) -> dict:
    observed = utc_now()
    run, lookup_error = None, None
    response = event.get("responseElements") or {}
    try:
        context = parse_subject(response.get("subjectFromWebIdentityToken") or "",
                                arguments.subject_prefix)
        run = get_run(arguments.repository, context.run_id, context.attempt, github_token)
    except (ValueError, RuntimeError) as error:
        lookup_error = str(error)
    decision = classify(event, run, role_arn=arguments.role_arn,
                        repository=arguments.repository, subject_prefix=arguments.subject_prefix)
    now = utc_now()
    return {"aws_event": event, "github_run": run, "github_lookup_error": lookup_error,
            "first_observed_searchable_utc": observed, "decision_available_utc": now,
            "alert_available_utc": now if decision["decision"] == "pr_role_misuse" else None,
            "result": decision, "alert": render(decision)}


def announce(entry: dict):
    """Human-readable line per decision; the full alert when one is raised."""
    result = entry["result"]
    context = f"{result.get('github_event') or '?'} run {result.get('run_id') or '?'}"
    print(f"[{result.get('event_time_utc')}] {context} -> {result['decision']}", flush=True)
    alert = entry.get("alert")
    if alert:
        print(f"    ALERT ({alert['severity']}): {alert['title']}", flush=True)
        print(f"    {alert['what_happened']}", flush=True)
        print(f"    where: {alert['where_to_look']}", flush=True)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--subject-prefix", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--start", required=True, help="UTC ISO timestamp with timezone")
    parser.add_argument("--end", help="Fixed UTC ISO end; omitted means current poll time")
    parser.add_argument("--token-env", default="D2_GITHUB_TOKEN")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--follow-seconds", type=int, default=0)
    parser.add_argument("--poll-seconds", type=int, default=15)
    args = parser.parse_args()
    if not re.fullmatch(r"arn:aws:iam::\d{12}:role/[A-Za-z0-9+=,.@_/-]+", args.role_arn):
        parser.error("Expected a sandbox IAM role ARN")
    if args.follow_seconds < 0 or args.poll_seconds < 1:
        parser.error("Follow duration must be nonnegative and polling interval positive")
    parse_subject(f"{args.subject_prefix}:pull_request:event_name:pull_request:run_id:1:run_attempt:1",
                  args.subject_prefix)
    return args


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include their UTC offset")
    return parsed


def main():
    import boto3

    args = arguments()
    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"Set {args.token_env} to a separate repository Actions:read credential")
    start = timestamp(args.start)
    deadline = time.monotonic() + args.follow_seconds
    client = boto3.client("cloudtrail", region_name=args.region)
    records = {}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    while True:
        end = timestamp(args.end or utc_now())
        for event in lookup(client, start, end):
            if role_arn(event) != args.role_arn:
                continue
            event_id = event.get("eventID")
            if not event_id:
                continue
            previous = records.get(event_id)
            if previous and previous["result"]["decision"] != "context_not_verified":
                continue
            entry = record(event, args, token)
            if previous:
                entry["first_observed_searchable_utc"] = previous["first_observed_searchable_utc"]
            records[event_id] = entry
            if not previous or previous["result"]["decision"] != entry["result"]["decision"]:
                announce(entry)
        document = {
            "mode": "live_cloudtrail_lookup_and_independent_github_api", "recorded_utc": utc_now(),
            "measurement_note": "Observed availability includes collector polling/setup delay.",
            "region": args.region, "records": list(records.values()),
        }
        args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(args.poll_seconds, remaining))


if __name__ == "__main__":
    main()
