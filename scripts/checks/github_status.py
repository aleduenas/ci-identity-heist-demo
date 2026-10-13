"""Report private-repository Actions runs without printing existing Git credentials."""
import json
import os
import subprocess
import urllib.request


def main():
    result = subprocess.run(
        ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "GCM_INTERACTIVE": "Never", "GIT_TERMINAL_PROMPT": "0"},
    )
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if result.returncode or "password" not in values:
        raise SystemExit("No noninteractive GitHub credential available")
    url = "https://api.github.com/repos/aleduenas/mybank-eks-sandbox/actions/runs?per_page=5"
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + values["password"],
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mybank-sandbox-status",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        runs = json.load(response)["workflow_runs"]
    for run in runs:
        print(json.dumps({key: run[key] for key in (
            "id", "name", "head_sha", "status", "conclusion", "html_url",
        )}))
    if not runs:
        print("No GitHub Actions runs yet")


if __name__ == "__main__":
    main()
