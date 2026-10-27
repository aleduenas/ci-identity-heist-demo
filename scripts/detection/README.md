# Detection operator commands

The recorded demonstration's AWS environment is torn down and its live workflows are disabled. To reproduce the exercise, provision your own private copy and enable the workflows as described in the [walkthrough](../../docs/demo.md).

To deploy the control, use the [GitHub-deployed control](../../security/README.md):
edit `security/control.json` on main and watch **Deploy security control**.
`apply_control.py` is the prepared example implementation. The setting enables
the restrictive policy through the existing workflow. The commands below remain
supporting investigation/manual recovery tools.

Run these modules from the repository root with the development environment installed. They use the existing boto3 dependency and Python standard library. Read [the detection runbook](../../docs/detection/README.md) before live operation.

| Command | Purpose |
| --- | --- |
| `python -m scripts.detection.replay` | Print explicitly invented examples; no network or AWS calls |
| `python -m scripts.detection.replay --output docs/detection/generated/mock.json` | Retain those fixture decisions locally |
| `python -m scripts.detection.collect --help` | Inspect live collector arguments |
| `python -m scripts.detection.report docs/detection/generated/live.json` | Summarize observed decisions and live delays |
| `python -m scripts.detection.set_trust show\|block-pr\|allow-pr` | Manual investigation/recovery helper; edits can diverge from the committed setting. Not the GitHub deployment path |
| `python -m pytest tests/detection` | Check provenance decisions and evidence sanitization |

The hosted workflow executes `demo_probe.py` directly. Shipped, it only runs a harmless status check. When the attack block is uncommented it exchanges the job's GitHub OIDC token for the exercise role and, on a PR, replaces the app and reads the synthetic customer tables. Its stdout is an execution aid, not independent detection evidence.

`collect.py` runs separately under an authorized operator identity. It reads CloudTrail through the SDK and GitHub through a separate `DETECTION_GITHUB_TOKEN` environment variable. It retains an allowlist of fields, excluding raw JWTs, temporary credential objects, access-key IDs, and session tokens. The accepted subject is identity context, not the JWT itself. Each record carries `alert.py` output: a high-severity alert (what happened, why it matters, run URL and CloudTrail event ID) for `pr_role_misuse`, an `investigate` notice for `context_not_verified`, and none for expected or denied use. Generated output directories are ignored.
