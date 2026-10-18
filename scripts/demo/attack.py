"""Simulate the stolen coding-agent push: an unreviewed PR changes the PR-executed probe.

Default opens a new PR. `--again` pushes another change to the open demo PR (use after
`prevent on` to show the same attack being denied). Your working copy is never touched.
"""

import argparse
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from scripts.demo import gh
from scripts.demo.github_api import request
from scripts.demo.ops import activate, step

PROBE = "scripts/detection/demo_probe.py"
PREFIX = "demo-attack-"


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=True).stdout.strip()


def open_demo_pr(repo: dict) -> dict | None:
    pulls = request("GET", f"{repo['path']}/pulls?state=open&per_page=50")
    return next((p for p in pulls if p["head"]["ref"].startswith(PREFIX)), None)


def push_change(branch: str, base: str, stamp: str):
    git("fetch", "origin", base)
    with tempfile.TemporaryDirectory(prefix="mybank-attack-") as directory:
        worktree = str(Path(directory) / "wt")
        git("worktree", "add", "--detach", worktree, f"origin/{base}")
        try:
            probe = Path(worktree) / PROBE
            text = probe.read_text(encoding="utf-8")
            # Unleash the pre-authored exploit by uncommenting its call (idempotent on --again).
            text = text.replace("\n    # run_attack()\n", "\n    run_attack()\n")
            # Bump the harmless value so every push is a real diff that triggers CI.
            text = re.sub(r'^PROBE_NOTE = ".*"$', f'PROBE_NOTE = "stolen-agent-change-{stamp}"',
                          text, flags=re.M)
            probe.write_text(text, encoding="utf-8", newline="\n")
            git("commit", "-am", f"test: tweak probe {stamp}", cwd=worktree)
            git("push", "origin", f"HEAD:refs/heads/{branch}", cwd=worktree)
        finally:
            git("worktree", "remove", "--force", worktree)


def report(repo: dict, since: str):
    step("Waiting for the PR's automated checks (GitHub-hosted runner)")
    run = gh.wait_for_run(repo, "detection-demo.yml", since, event="pull_request", timeout=600)
    job = run["job_ids"].get("identity-probe")
    print(f"    identity-probe: {run['jobs'].get('identity-probe')}")
    log = gh.job_log(repo, job) if job else ""
    for line in log.splitlines():
        text = line[29:] if len(line) > 29 else line
        if any(key in text for key in ('"obtained_identity"', '"direct_database_read"',
                                       '"reach_private_cluster"', "AccessDenied")):
            print("    " + text.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--again", action="store_true", help="Push to the existing demo PR")
    args = parser.parse_args()
    activate()
    repo = gh.repository()
    stamp = datetime.now(UTC).strftime("%H%M%S")
    since = gh.utc_now()
    existing = open_demo_pr(repo)
    if args.again:
        if not existing:
            raise SystemExit("No open demo PR; run without --again first")
        step(f"Pushing another unreviewed change to PR #{existing['number']}")
        push_change(existing["head"]["ref"], existing["head"]["ref"], stamp)
        print(f"    {existing['html_url']}")
    else:
        branch = f"{PREFIX}{datetime.now(UTC):%Y%m%d}-{stamp}"
        step(f"Attacker (stolen agent token) pushes {branch} and opens a PR")
        push_change(branch, "main", stamp)
        pr = request("POST", f"{repo['path']}/pulls", {
            "title": "Tidy probe output", "head": branch, "base": "main",
            "body": "Simulated stolen coding-agent change for the detection demo. Do not merge.",
        })
        print(f"    {pr['html_url']} (open, unreviewed)")
    report(repo, since)


if __name__ == "__main__":
    main()
