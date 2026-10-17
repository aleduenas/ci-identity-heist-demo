"""Render the human-readable D2 alert: what happened, why it matters, where to look."""


def render(result: dict) -> dict | None:
    """Only a verified PR-context success becomes an alert; gaps are reported, not escalated."""
    decision = result.get("decision")
    if decision == "pr_role_misuse":
        return {
            "severity": "high",
            "title": "Deployment credentials issued to PR validation",
            "what_happened": (
                f"AWS issued {result.get('role_arn')} at {result.get('event_time_utc')} to "
                f"GitHub run {result.get('run_id')} attempt {result.get('run_attempt')}, "
                "independently identified as pull_request validation."
            ),
            "why_it_matters": (
                "That job tests unreviewed code and should not hold an identity that can "
                "replace the running backend."
            ),
            "evidence": (
                "AWS-accepted signed subject matched the independently fetched GitHub run, "
                "attempt, event and immutable repository/owner IDs; the session name was ignored."
            ),
            "where_to_look": {"run_url": result.get("run_url"),
                              "cloudtrail_event_id": result.get("event_id")},
            "next_steps": (
                "CI/release owners: inspect the run and PR. Security: check whether any "
                "deployment or EKS activity followed under this role."
            ),
        }
    if decision == "context_not_verified":
        return {
            "severity": "investigate",
            "title": "Deployment-role issuance with unverified workflow context",
            "what_happened": (
                f"AWS issued or processed a request for the exercise role at "
                f"{result.get('event_time_utc')}, but its GitHub context could not be "
                f"verified: {result.get('reason')}."
            ),
            "why_it_matters": "Security cannot tell whether this use was an approved release.",
            "where_to_look": {"cloudtrail_event_id": result.get("event_id")},
            "next_steps": "Treat as a visibility gap; do not assume a trusted release.",
        }
    return None
