"""Verify GitHub's current immutable main-branch subject without exposing its JWT."""
import base64
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    repository = event["repository"]
    owner_name, repository_name = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    expected = (
        f"repo:{owner_name}@{repository['owner']['id']}/"
        f"{repository_name}@{repository['id']}:ref:refs/heads/main"
    )
    parsed = urllib.parse.urlparse(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    query = urllib.parse.parse_qsl(parsed.query) + [("audience", "sts.amazonaws.com")]
    url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
    })
    with urllib.request.urlopen(request, timeout=15) as response:
        token = json.load(response)["value"]
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    if claims["sub"] != expected or claims["aud"] != "sts.amazonaws.com":
        raise SystemExit("GitHub OIDC claims differ from the expected main-branch subject")
    print(json.dumps({key: claims[key] for key in (
        "sub", "aud", "repository_id", "repository_owner_id",
    )}))
    print("PASS: immutable main-branch OIDC subject; no AWS API was called")


if __name__ == "__main__":
    main()
