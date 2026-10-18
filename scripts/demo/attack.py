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
ATTACK_HEADER = "# === ATTACK PAYLOAD"


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=True).stdout.strip()


def arm(text: str) -> str:
    """Comment out the legitimate entrypoint and uncomment the attack block below the header.

    Mirrors the manual Step 2. Idempotent: a no-op once `run_attack` is already live (`--again`).
    """
    if "\ndef run_attack(" in text:
        return text
    text = text.replace('\nif __name__ == "__main__":\n    smoke_check()\n',
                        '\n# if __name__ == "__main__":\n#     smoke_check()\n')
    head, sep, tail = text.partition(ATTACK_HEADER)
    header_line, _, block = tail.partition("\n")
    uncommented = "\n".join(line[2:] if line.startswith("# ") else
                            line[1:] if line.startswith("#") else line
                            for line in block.split("\n"))
    return head + sep + header_line + "\n" + uncommented


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
            text = arm(probe.read_text(encoding="utf-8"))
            # Bump the harmless value so every push is a real diff that triggers CI.
            text = re.sub(r'^CHECK_NOTE = ".*"$', f'CHECK_NOTE = "stolen-agent-change-{stamp}"',
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
