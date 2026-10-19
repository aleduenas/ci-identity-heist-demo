"""Check decoded GitHub OIDC claim format; this is not signature verification."""
import base64
import json
import os
import re
import urllib.parse
import urllib.request
from collections.abc import Mapping
from pathlib import Path


def expected_subject(event: dict, environment: Mapping[str, str]) -> str:
    repository = event["repository"]
    owner_name, repository_name = environment["GITHUB_REPOSITORY"].split("/", 1)
    subject = (
        f"repo:{owner_name}@{repository['owner']['id']}/"
        f"{repository_name}@{repository['id']}:ref:refs/heads/main"
    )
    if environment.get("MYBANK_OIDC_RUN_CONTEXT", "").lower() != "true":
        return subject
    event_name = environment["GITHUB_EVENT_NAME"]
    if environment.get("GITHUB_REF") != "refs/heads/main" or event_name not in {
        "push", "workflow_dispatch",
    }:
        raise ValueError("Release identity checks accept only main pushes or manual dispatches")
    run_id, attempt = environment["GITHUB_RUN_ID"], environment["GITHUB_RUN_ATTEMPT"]
    if not all(re.fullmatch(r"[1-9][0-9]*", value) for value in (run_id, attempt)):
        raise ValueError("Run ID and attempt must be positive numeric GitHub identifiers")
    return f"{subject}:event_name:{event_name}:run_id:{run_id}:run_attempt:{attempt}"


def checked_claims(claims: dict, event: dict, environment: Mapping[str, str]) -> dict:
    if claims.get("sub") != expected_subject(event, environment):
        raise ValueError("GitHub OIDC subject differs from the expected main-run subject")
    if claims.get("aud") != "sts.amazonaws.com":
        raise ValueError("GitHub OIDC audience differs from sts.amazonaws.com")
    repository = event["repository"]
    if (
        str(claims.get("repository_id")) != str(repository["id"])
        or str(claims.get("repository_owner_id")) != str(repository["owner"]["id"])
    ):
        raise ValueError("GitHub immutable repository identities differ from the event")
    return {key: claims[key] for key in (
        "sub", "aud", "repository_id", "repository_owner_id",
    )}


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
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
    try:
        print(json.dumps(checked_claims(claims, event, os.environ)))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print("PASS: decoded main-run claim format; signature and AWS acceptance not verified")


if __name__ == "__main__":
    main()
