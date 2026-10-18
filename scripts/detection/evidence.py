"""Allowlist evidence: raw STS/GitHub records and credential material never get written."""

from datetime import UTC, datetime


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def role_arn(event: dict) -> str | None:
    """Successes record requestParameters.roleArn; live denials record it only in resources."""
    requested = (event.get("requestParameters") or {}).get("roleArn")
    if requested:
        return requested
    return next((item.get("ARN") for item in event.get("resources") or []
                 if item.get("type") == "AWS::IAM::Role"), None)


def safe_event(event: dict) -> dict:
    """Retain identity context, excluding the entire STS credentials object."""
    response = event.get("responseElements") or {}
    request = event.get("requestParameters") or {}
    identity = event.get("userIdentity") or {}
    return {
        "eventID": event.get("eventID"), "eventTime": event.get("eventTime"),
        "eventSource": event.get("eventSource"), "eventName": event.get("eventName"),
        "awsRegion": event.get("awsRegion"),
        "recipientAccountId": event.get("recipientAccountId"),
        "errorCode": event.get("errorCode"),
        "requestParameters": {"roleArn": request.get("roleArn")},
        "resources": [{"type": item.get("type"), "ARN": item.get("ARN")}
                      for item in event.get("resources") or []],
        "userIdentity": {"identityProvider": identity.get("identityProvider"),
                         "userName": identity.get("userName")},
        "responseElements": {
            "subjectFromWebIdentityToken": response.get("subjectFromWebIdentityToken"),
            "provider": response.get("provider"), "audience": response.get("audience"),
            "assumedRoleUser": {
                "arn": (response.get("assumedRoleUser") or {}).get("arn"),
            },
        },
    }


def safe_run(run: dict) -> dict:
    repository = run.get("repository") or {}
    actor = run.get("actor") or {}
    head_repository = run.get("head_repository") or {}
    return {
        key: run.get(key) for key in (
            "id", "run_attempt", "event", "path", "workflow_id", "head_branch",
            "head_sha", "run_started_at", "created_at", "html_url",
        )
    } | {
        "repository": {
            "id": repository.get("id"), "full_name": repository.get("full_name"),
            "owner": {"id": (repository.get("owner") or {}).get("id")},
        },
        "head_repository": {"id": head_repository.get("id")},
        "actor": {"id": actor.get("id"), "login": actor.get("login")},
    }
