# Demo commands

The live control is deployed in GitHub by changing `security/control.json`; see
[the control walkthrough](../../security/README.md). No Terraform or local operator
command is part of activation. These modules are initial setup/support utilities.

Operator commands behind [DEMO.md](../../DEMO.md). Run each as `.venv/Scripts/python.exe -m scripts.demo.<name>` from the repository root.

| Command | What it does |
| --- | --- |
| `login` | Signs the local CLI in as your console IAM user (temporary credentials only) |
| `up` | Idempotent standup: Terraform, GitHub wiring, image, private runner, app bootstrap, data, trusted release |
| `app` | Private access to the app over SSM → EKS API → port-forward; fetches synthetic accounts (`--hold` keeps it open) |
| `watch` | Security's independent watcher: CloudTrail + GitHub run records → live decisions and alerts |
| `impact` | Post-grab proof (sandbox): uses the deployer identity to replace the app and read synthetic customer records, then restores the app |
| `prevent` | Retired: exits with the GitHub workflow instructions and makes no changes |
| `down` | Stops delivery, removes the runner, closes demo PRs, destroys the lab and checks compute/IP cleanup; retained storage may block destroy until explicitly emptied |

Supporting modules: `ops` (AWS session, Terraform, tunnel), `gh` (repository identity, variables, runs), `runner` (main-only runner on the private host), `kube` (bootstrap and admin kubectl), `github_api` (token from env or Git Credential Manager; never printed or stored).

Copy `infra/environments/sandbox/demo.tfvars.json.example` to ignored `.cache/sandbox.tfvars.json`, replace the account and bootstrap-role placeholders, and configure the ignored `infra/environments/sandbox/backend.hcl` before `up`. The example explicitly enables the public EKS API required by the demo. Unknown local Terraform keys are rejected before planning, including obsolete `enable_d2`.

Trust is bound to the git remote's immutable owner/repository IDs on every run, so a freshly created repository works without code changes. The runner's registration token passes through one SSM SecureString parameter that the host reads once and the operator deletes; it never appears in command text, logs or Git.
