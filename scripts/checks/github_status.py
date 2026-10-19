"""Report private-repository Actions runs without printing existing Git credentials."""
import argparse
import json
import os
import subprocess
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", action="store_true")
    parser.add_argument("--run-id", type=int)
    args = parser.parse_args()
    result = subprocess.run(
        ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "GCM_INTERACTIVE": "Never", "GIT_TERMINAL_PROMPT": "0"},
    )
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if result.returncode or "password" not in values:
        raise SystemExit("No noninteractive GitHub credential available")
    headers = {
        "Authorization": "Bearer " + values["password"],
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mybank-sandbox-status",
    }

    def read(path):
        request = urllib.request.Request(
            "https://api.github.com/repos/aleduenas/mybank-eks-sandbox" + path, headers=headers,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    if args.metadata:
        repo = read("")
        print(json.dumps({"repository_id": repo["id"], "owner_id": repo["owner"]["id"],
                          "private": repo["private"], "created_at": repo["created_at"]}))
        print(json.dumps(read("/actions/oidc/customization/sub")))
    if args.run_id:
        for job in read(f"/actions/runs/{args.run_id}/jobs")["jobs"]:
            print(json.dumps({"name": job["name"], "status": job["status"],
                              "conclusion": job["conclusion"], "steps": [
                                  {key: step[key] for key in ("name", "status", "conclusion")}
                                  for step in job.get("steps", [])
                              ]}))
        return
    runs = read("/actions/runs?per_page=10")["workflow_runs"]
    for run in runs:
        print(json.dumps({key: run[key] for key in (
            "id", "name", "head_sha", "status", "conclusion", "html_url",
        )}))
    if not runs:
        print("No GitHub Actions runs yet")


if __name__ == "__main__":
    main()
