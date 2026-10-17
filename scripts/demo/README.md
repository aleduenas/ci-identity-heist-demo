# Demo commands

Operator commands behind [DEMO.md](../../DEMO.md). Run each as `.venv/Scripts/python.exe -m scripts.demo.<name>` from the repository root.

| Command | What it does |
| --- | --- |
| `login` | Signs the local CLI in as your console IAM user (temporary credentials only) |
| `up` | Idempotent standup: Terraform, GitHub wiring, image, private runner, app bootstrap, data, trusted release |
| `app` | Private access to the app over SSM → EKS API → port-forward; fetches synthetic accounts (`--hold` keeps it open) |
| `watch` | Security's independent watcher: CloudTrail + GitHub run records → live decisions and alerts |
| `attack` | Opens an unreviewed PR that changes the PR-executed probe; `--again` pushes to the same PR |
| `prevent on\|off` | Removes/restores PR trust on the exercise deploy role only |
| `down` | Stops delivery, removes the runner, closes demo PRs, destroys the lab, verifies nothing billable remains |

Supporting modules: `ops` (AWS session, Terraform, tunnel), `gh` (repository identity, variables, runs), `runner` (main-only runner on the private host), `kube` (bootstrap and admin kubectl), `github_api` (token from env or Git Credential Manager; never printed or stored).

Trust is bound to the git remote's immutable owner/repository IDs on every run, so a freshly created repository works without code changes. The runner's registration token passes through one SSM SecureString parameter that the host reads once and the operator deletes; it never appears in command text, logs or Git.
