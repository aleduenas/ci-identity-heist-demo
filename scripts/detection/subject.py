"""Parse GitHub-generated context from the subject accepted by AWS STS."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Context:
    repository: str
    owner_id: int
    repository_id: int
    event: str
    run_id: int
    attempt: int
    context: str


def parse_subject(subject: str, prefix: str) -> Context:
    """Require the exercise template exactly; session names never enter this function."""
    identity = re.fullmatch(r"repo:([^/@]+)@(\d+)/([^/@]+)@(\d+)", prefix)
    if not identity:
        raise ValueError("Expected an immutable owner/repository subject prefix")
    pattern = re.escape(prefix) + (
        r":(?P<context>pull_request|ref:refs/heads/main)"
        r":event_name:(?P<event>pull_request|push|workflow_dispatch)"
        r":run_id:(?P<run>[1-9]\d*):run_attempt:(?P<attempt>[1-9]\d*)"
    )
    match = re.fullmatch(pattern, subject)
    if not match:
        raise ValueError("Accepted subject does not match the configured exercise template")
    event, context = match["event"], match["context"]
    if (event == "pull_request") != (context == "pull_request"):
        raise ValueError("Subject event and context disagree")
    return Context(
        repository=f"{identity[1]}/{identity[3]}", owner_id=int(identity[2]),
        repository_id=int(identity[4]), event=event, run_id=int(match["run"]),
        attempt=int(match["attempt"]), context=context,
    )
