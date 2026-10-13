"""Create the explicitly requested private repo using existing Git credentials.

Never prints credentials. Does not open an interactive credential prompt.
"""
import json
import os
import subprocess
import urllib.error
import urllib.request


def main():
    env = {**os.environ, "GCM_INTERACTIVE": "Never", "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True, capture_output=True, env=env, timeout=30,
    )
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    token = values.get("password")
    if result.returncode or not token:
        raise SystemExit("No noninteractive GitHub credential is available. Connect GitHub or authenticate gh.")

    def request(path, body=None):
        req = urllib.request.Request(
            "https://api.github.com" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
                     "User-Agent": "mybank-sandbox-bootstrap"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    try:
        user = request("/user")
        owner = user["login"]
        print("Authenticated GitHub owner:", owner)
        name = "mybank-eks-sandbox"
        try:
            repo = request(f"/repos/{owner}/{name}")
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            repo = request("/user/repos", {
                "name": name, "private": True, "auto_init": False,
                "description": "Synthetic Mybank AWS EKS transactional sandbox with SAML and CI/CD",
            })
        if not repo.get("private"):
            raise SystemExit("Repository exists but is public; stopping without publishing files.")
        print("Verified private repository:", repo["html_url"])
    except urllib.error.HTTPError as error:
        raise SystemExit(f"GitHub API request failed (HTTP {error.code}); no credential was printed.") from None


if __name__ == "__main__":
    main()
