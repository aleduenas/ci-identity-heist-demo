# Detection operator commands

Run these modules from the repository root with the development environment installed. They use the existing boto3 dependency and Python standard library. Read [the detection runbook](../../docs/detection/README.md) before live operation.

| Command | Purpose |
| --- | --- |
| `python -m scripts.detection.replay` | Print explicitly invented examples; no network or AWS calls |
| `python -m scripts.detection.replay --output docs/detection/generated/mock.json` | Retain those fixture decisions locally |
| `python -m scripts.detection.collect --help` | Inspect live collector arguments |
| `python -m scripts.detection.report docs/detection/generated/live.json` | Summarize observed decisions and live delays |
| `python -m scripts.detection.set_trust show\|block-pr\|allow-pr` | The prevention control: read/edit the exercise role's trust policy directly via the IAM API (no Terraform) |
| `python -m pytest tests/detection` | Check provenance decisions and evidence sanitization |

The hosted **Application integration checks / transactions** job starts the Docker API and DynamoDB Local, then executes `python -m scripts.detection.demo_probe`. By default it checks readiness, authentication, atomic transfers, idempotency, conflicts, and overdraft rollback through `scripts/checks/local_api.py`; it makes no AWS credential request. The historical workflow filename is retained for detector provenance. When the attack block is uncommented (the Step 2 attack) it exchanges the job's GitHub OIDC token for the exercise role and, on a PR, replaces the app and reads the synthetic customer tables. Its stdout is an execution aid, not independent detection evidence.

The ordinary transaction tests explain why PR code runs in CI. The job's OIDC permission and PR-trusting exercise role remain deliberate lab misconfiguration; transaction checks need neither deployment credentials nor kubectl. The independent detector runs on the operator workstation, not in this job.

`collect.py` runs separately under an authorized operator identity. It reads CloudTrail through the SDK and GitHub through a separate `DETECTION_GITHUB_TOKEN` environment variable. It retains an allowlist of fields, excluding raw JWTs, temporary credential objects, access-key IDs, and session tokens. The accepted subject is identity context, not the JWT itself. Each record carries `alert.py` output: a high-severity alert (what happened, why it matters, run URL and CloudTrail event ID) for `pr_role_misuse`, an `investigate` notice for `context_not_verified`, and none for expected or denied use. Generated output directories are ignored.
