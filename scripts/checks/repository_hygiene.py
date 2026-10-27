"""Reject internal paths and recognizable credentials; print paths/rules, never values."""

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERNAL = re.compile(
    r"(^|/)(?:\.aws|\.claude|\.codex|\.agents|\.internal|\.cache|\.tools|\.venv|"
    r"\.terraform|__pycache__)(/|$)|(^|/)(?:AGENTS|control-instructions)\.md$|"
    r"^(?:DEMO|WALKTHROUGH)\.md$|^docs/(?:plan|presentation)/|"
    r"^docs/implementation-status\.md$|"
    r"^docs/(?:d2|detection)/(?:HANDOFF|evidence|control-evidence)\.md$|"
    r"^(?:identity|deploy|docs/detection)/generated/|(^|/)backend\.hcl$|"
    r"\.tfstate|\.tfplan|\.tfvars(?:\.json)?$|(?:^|/)\.env(?:\..+)?$|"
    r"(?:_credentials.*\.csv|\.(?:pem|key|p12|pfx|saml|assertion))$"
)
PATTERNS = {
    "AWS access key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b",
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "JWT": r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
    "Slack token": r"\bxox[baprs]-[A-Za-z0-9-]{20,}",
    "AWS secret assignment": (
        r"(?i)(?:aws_secret_access_key|SecretAccessKey)\s*[=:]\s*[\"']?"
        r"[A-Za-z0-9/+]{40}(?:[\"'\s]|$)"
    ),
}


def check(path: str, data: bytes) -> list[str]:
    allowed = path.endswith(".example") or path.endswith("/generated/.gitignore")
    rules = ["internal/generated path"] if INTERNAL.search(path) and not allowed else []
    content = data.decode("utf-8", "replace")
    return rules + [label for label, pattern in PATTERNS.items() if re.search(pattern, content)]


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def working_files():
    paths = git("ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")
    for raw in sorted(set(paths) - {b""}):
        path = raw.decode("utf-8")
        target = ROOT / path
        if target.is_file():
            yield path, target.read_bytes()


def history():
    objects = git("rev-list", "--objects", "--all").decode().splitlines()
    with subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        for item in objects:
            oid, _, path = item.partition(" ")
            process.stdin.write((oid + "\n").encode())
            process.stdin.flush()
            _, kind, size = process.stdout.readline().decode().split()
            data = process.stdout.read(int(size))
            process.stdout.read(1)
            if kind == "blob":
                yield f"{oid[:12]}:{path}", data
        process.stdin.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true", help="Also scan reachable Git history")
    args = parser.parse_args()
    findings, count = [], 0
    for path, data in working_files():
        count += 1
        findings.extend((path, rule) for rule in check(path, data))
    if args.history:
        for path, data in history():
            count += 1
            findings.extend((path, rule) for rule in check(path.split(":", 1)[1], data))
    for path, rule in findings:
        print(f"{path}: {rule}")
    print(f"Checked {count} files/blobs; {len(findings)} findings (values never printed).")
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
