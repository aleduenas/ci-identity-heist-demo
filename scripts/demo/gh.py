"""GitHub helpers for the demo: repository identity, variables, workflow runs, OIDC template."""

import re
import subprocess
import time
from datetime import UTC, datetime

from scripts.demo.github_api import request

OIDC_TEMPLATE = {"use_default": False, "use_immutable_subject": True,
                 "include_claim_keys": ["repo", "context", "event_name", "run_id", "run_attempt"]}


def repository() -> dict:
    """Owner/name from the git remote; immutable numeric IDs from GitHub itself."""
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True,
                         text=True, check=True).stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        raise SystemExit(f"origin is not a GitHub repository: {url}")
    owner, name = match.groups()
    info = request("GET", f"/repos/{owner}/{name}")
    if not info.get("private"):
        raise SystemExit("Refusing to run the lab against a public repository")
    owner_id, repo_id = info["owner"]["id"], info["id"]
    return {"owner": owner, "name": name, "full": f"{owner}/{name}",
            "path": f"/repos/{owner}/{name}", "prefix": f"repo:{owner}@{owner_id}/{name}@{repo_id}"}


def set_var(repo: dict, name: str, value: str):
    try:
        request("PATCH", f"{repo['path']}/actions/variables/{name}", {"name": name, "value": value})
    except RuntimeError as error:
        if "404" not in str(error):
            raise
        request("POST", f"{repo['path']}/actions/variables", {"name": name, "value": value})


def delete_var(repo: dict, name: str):
    try:
        request("DELETE", f"{repo['path']}/actions/variables/{name}")
    except RuntimeError as error:
        if "404" not in str(error):
            raise


def set_oidc_template(repo: dict):
    request("PUT", f"{repo['path']}/actions/oidc/customization/sub", OIDC_TEMPLATE)


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def wait_for_run(repo: dict, workflow: str, since: str, event: str | None = None,
                 timeout: int = 1500) -> dict:
    """Wait for the newest run of `workflow` created at/after `since` to complete."""
    query = f"per_page=10&created=%3E%3D{since}" + (f"&event={event}" if event else "")
    deadline, announced = time.monotonic() + timeout, None
    while time.monotonic() < deadline:
        runs = request("GET", f"{repo['path']}/actions/workflows/{workflow}/runs?{query}")
        run = (runs.get("workflow_runs") or [None])[0]
        if run and run["id"] != announced:
            print(f"    run {run['html_url']}", flush=True)
            announced = run["id"]
        if run and run["status"] == "completed":
            jobs = request("GET", f"{repo['path']}/actions/runs/{run['id']}/jobs")["jobs"]
            run["jobs"] = {job["name"]: job["conclusion"] for job in jobs}
            run["job_ids"] = {job["name"]: job["id"] for job in jobs}
            return run
        time.sleep(15)
    raise SystemExit(f"Timed out waiting for {workflow}")


def dispatch(repo: dict, workflow: str, ref: str = "main") -> dict:
    since = utc_now()
    request("POST", f"{repo['path']}/actions/workflows/{workflow}/dispatches", {"ref": ref})
    time.sleep(5)
    return wait_for_run(repo, workflow, since, event="workflow_dispatch")


def job_log(repo: dict, job_id: int) -> str:
    """Job logs redirect to blob storage, which must not receive the GitHub token."""
    import urllib.error
    import urllib.request

    from scripts.demo.github_api import get_token

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    request = urllib.request.Request(
        f"https://api.github.com{repo['path']}/actions/jobs/{job_id}/logs",
        headers={"Authorization": f"Bearer {get_token()}", "User-Agent": "mybank-demo"})
    try:
        urllib.request.build_opener(NoRedirect).open(request, timeout=30)
        return ""
    except urllib.error.HTTPError as error:
        location = error.headers.get("Location")
    if not location:
        return ""
    with urllib.request.urlopen(location, timeout=30) as response:
        return response.read().decode("utf-8", "replace")
