"""Pure detection decisions over independently collected, allowlisted evidence."""

from .evidence import role_arn as event_role_arn
from .subject import parse_subject


def classify(event: dict, run: dict | None, *, role_arn: str, repository: str,
             subject_prefix: str, workflow: str = ".github/workflows/detection-demo.yml") -> dict:
    """Return a visible decision; unverifiable context never becomes a trusted release."""
    def result(decision, reason, **details):
        return {"decision": decision, "reason": reason, "event_id": event.get("eventID"),
                "event_time_utc": event.get("eventTime"), **details}

    if (event.get("eventSource"), event.get("eventName")) != (
        "sts.amazonaws.com", "AssumeRoleWithWebIdentity",
    ) or event_role_arn(event) != role_arn:
        return result("out_of_scope", "Not the selected STS operation and role")
    if event.get("errorCode"):
        # Denials carry no response; AWS records the rejected subject as the web-identity user.
        rejected = (event.get("userIdentity") or {}).get("userName")
        try:
            context = parse_subject(rejected or "", subject_prefix)
            details = {"run_id": context.run_id, "run_attempt": context.attempt,
                       "github_event": context.event}
        except ValueError:
            details = {}
        return result("assumption_denied", "AWS did not issue the requested credentials",
                      error_code=event.get("errorCode"), rejected_subject=rejected, **details)
    response = event.get("responseElements") or {}
    role_account = role_arn.split(":")[4]
    provider = f"arn:aws:iam::{role_account}:oidc-provider/token.actions.githubusercontent.com"
    if event.get("recipientAccountId") != role_account:
        return result("context_not_verified", "AWS recipient account differs from target role")
    if response.get("provider") != provider or response.get("audience") != "sts.amazonaws.com":
        return result("context_not_verified", "GitHub provider/audience evidence unavailable")
    assumed_arn = (response.get("assumedRoleUser") or {}).get("arn", "")
    expected_arn = f"arn:aws:sts::{role_account}:assumed-role/{role_arn.rsplit('/', 1)[-1]}/"
    if not assumed_arn.startswith(expected_arn):
        return result("context_not_verified", "Successful issued-role identity is missing")
    try:
        context = parse_subject(response.get("subjectFromWebIdentityToken") or "", subject_prefix)
    except ValueError as error:
        return result("context_not_verified", str(error))
    if context.repository != repository:
        return result("context_not_verified", "Configured repository and subject prefix disagree")
    if run is None:
        return result("context_not_verified", "Independent GitHub run record unavailable")
    github_repository = run.get("repository") or {}
    checks = (
        run.get("id") == context.run_id,
        run.get("run_attempt") == context.attempt,
        run.get("event") == context.event,
        github_repository.get("id") == context.repository_id,
        github_repository.get("full_name") == repository,
        (github_repository.get("owner") or {}).get("id") == context.owner_id,
    )
    if not all(checks):
        return result("context_not_verified", "Signed subject and GitHub run metadata disagree")
    details = {"run_id": context.run_id, "run_attempt": context.attempt,
               "github_event": context.event, "workflow": run.get("path"),
               "run_url": run.get("html_url"), "role_arn": role_arn}
    if context.event == "pull_request":
        return result("pr_role_misuse", "PR validation successfully obtained deployment identity",
                      **details)
    if (run.get("path") or "").split("@", 1)[0] != workflow:
        return result("context_not_verified", "Main context is not the expected exercise workflow",
                      **details)
    if run.get("head_branch") != "main":
        return result("context_not_verified", "Trusted comparison is not on main", **details)
    return result("expected_release", "Verified main exercise identity comparison", **details)
