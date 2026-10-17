"""Explicitly invented records for repeatable local rule demonstrations, never live evidence."""

ROLE = "arn:aws:iam::111122223333:role/mybank-d2-demo-deploy"
REPOSITORY = "example-owner/example-sandbox"
PREFIX = "repo:example-owner@123/example-sandbox@456"


def sample(event_name: str = "pull_request", run_id: int = 1001) -> tuple[dict, dict]:
    context = "pull_request" if event_name == "pull_request" else "ref:refs/heads/main"
    subject = f"{PREFIX}:{context}:event_name:{event_name}:run_id:{run_id}:run_attempt:1"
    aws = {
        "eventID": f"fixture-{event_name}-{run_id}", "eventTime": "2026-10-17T12:00:00Z",
        "eventSource": "sts.amazonaws.com", "eventName": "AssumeRoleWithWebIdentity",
        "awsRegion": "ca-central-1", "recipientAccountId": "111122223333",
        "requestParameters": {"roleArn": ROLE, "roleSessionName": "release-looking-demo"},
        "responseElements": {
            "subjectFromWebIdentityToken": subject, "audience": "sts.amazonaws.com",
            "provider": ("arn:aws:iam::111122223333:oidc-provider/"
                         "token.actions.githubusercontent.com"),
            "assumedRoleUser": {
                "arn": "arn:aws:sts::111122223333:assumed-role/"
                       "mybank-d2-demo-deploy/release-looking-demo",
            },
        },
    }
    github = {
        "id": run_id, "run_attempt": 1, "event": event_name,
        "path": ".github/workflows/d2-demo.yml", "workflow_id": 42,
        "head_branch": "exercise-pr" if event_name == "pull_request" else "main",
        "head_sha": "a" * 40, "repository": {
            "id": 456, "full_name": REPOSITORY, "owner": {"id": 123},
        },
        "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
    }
    return aws, github
