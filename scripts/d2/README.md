# D2 operator commands

Run these modules from the repository root with the development environment installed. They use the existing boto3 dependency and Python standard library. Read [the D2 runbook](../../docs/d2/README.md) before live operation.

| Command | Purpose |
| --- | --- |
| `python -m scripts.d2.replay` | Print explicitly invented examples; no network or AWS calls |
| `python -m scripts.d2.replay --output docs/d2/generated/mock.json` | Retain those fixture decisions locally |
| `python -m scripts.d2.collect --help` | Inspect live collector arguments |
| `python -m scripts.d2.report docs/d2/generated/live.json` | Summarize observed decisions and live delays |
| `python -m scripts.d2.set_trust show\|block-pr\|allow-pr` | The prevention control: read/edit the exercise role's trust policy directly via the IAM API (no Terraform) |
| `python -m pytest tests/d2` | Check provenance decisions and evidence sanitization |

The hosted workflow executes `demo_probe.py` directly. That probe exchanges its GitHub OIDC token for the exercise role and calls only `GetCallerIdentity`; it never changes EKS or reads application data. Its stdout is an execution aid, not independent detection evidence.

`collect.py` runs separately under an authorized operator identity. It reads CloudTrail through the SDK and GitHub through a separate `D2_GITHUB_TOKEN` environment variable. It retains an allowlist of fields, excluding raw JWTs, temporary credential objects, access-key IDs, and session tokens. The accepted subject is identity context, not the JWT itself. Each record carries `alert.py` output: a high-severity alert (what happened, why it matters, run URL and CloudTrail event ID) for `pr_role_misuse`, an `investigate` notice for `context_not_verified`, and none for expected or denied use. Generated output directories are ignored.
