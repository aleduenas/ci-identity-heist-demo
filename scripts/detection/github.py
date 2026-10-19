"""Read GitHub run metadata directly, outside PR execution and job-generated logs."""

import json
import re
import urllib.error
import urllib.request

from .evidence import safe_run


def get_run(repository: str, run_id: int, attempt: int, token: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub owner/repository")
    url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/attempts/{attempt}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mybank-detection-independent-collector",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            document = json.load(response)
            if not isinstance(document, dict):
                raise RuntimeError("Independent GitHub lookup returned an invalid record")
            return safe_run(document)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Independent GitHub lookup returned HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Independent GitHub lookup could not reach the API") from None
    except (TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Independent GitHub lookup failed or returned invalid JSON") from None
