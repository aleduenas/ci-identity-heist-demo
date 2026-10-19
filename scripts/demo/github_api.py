"""Use the existing Git credential manager without logging or storing its token."""

import json
import os
import subprocess
import urllib.error
import urllib.request


def get_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"},
    )
    if result.returncode:
        raise RuntimeError("GitHub credential manager has no usable noninteractive credential")
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if not values.get("password"):
        raise RuntimeError("GitHub API authentication is not configured")
    return values["password"]


def request(method, path, payload=None):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Use an API path on api.github.com")
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mybank-sandbox-operator",
    }
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request("https://api.github.com" + path, data=data,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else {"status": response.status}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub {method} {path} returned HTTP {exc.code}") from None
