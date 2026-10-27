# Mybank EKS Sandbox

A security sandbox demonstrating how code in an unreviewed pull request can cross a CI identity boundary, obtain AWS deployment credentials, and read application data. An IAM trust control blocks the same attack before credentials are issued.

Mybank is a fictional banking API running on AWS EKS with DynamoDB and GitHub Actions. All customer records, accounts, and transfers are synthetic. The repository includes the application, infrastructure, attack and control implementations, setup instructions, and recorded CI evidence.

**Current state:** the AWS environment is torn down. Live release, attack-demo, and control-deployment workflows are disabled; the recorded runs below remain the demonstration. Local application and infrastructure validation checks remain available.

## Watch the demonstration

Open either run below, select **verify-boundary**, and expand **Execute PR-editable probe (grabs the identity; on a PR, demonstrates impact)**.

| Control | Recorded run | What to look for |
| --- | --- | --- |
| Off | [Attack obtains deployment credentials and reads synthetic records](https://github.com/aleduenas/ci-identity-heist-demo/actions/runs/39293282632/job/118199178766) | An assumed-role identity, followed by `STOLEN CUSTOMER RECORDS` in the CI log. |
| On | [Same attack blocked by IAM](https://github.com/aleduenas/ci-identity-heist-demo/actions/runs/39293816912/job/118201042196) | `AssumeRoleWithWebIdentity` is denied before the payload can replace the application. The failed check is the expected prevention result. |

The logs are execution evidence. The [walkthrough](docs/demo.md) explains the sequence and expected results without requiring access to the logs. GitHub may require sign-in to expand logs, and log availability depends on Actions retention.

## How it works

| File | Role in the demo |
| --- | --- |
| [`scripts/detection/demo_probe.py`](scripts/detection/demo_probe.py) | PR-editable code: a harmless status check and a commented attack payload. |
| [`security/control.json`](security/control.json) | The `enforcement_enabled` boolean: `false` permits exercise PR credentials; `true` restricts issuance to trusted `main` contexts. |
| [`scripts/detection/apply_control.py`](scripts/detection/apply_control.py) | Builds, applies, and verifies the exercise role's IAM trust policy. |
| [Identity boundary workflow](.github/workflows/detection-demo.yml) | Runs the probe in CI for an owner-operated, same-repository PR. |
| [Security control workflow](.github/workflows/security-control.yml) | Deploys the committed setting from `main` and verifies that `main` can still obtain the role. |

1. The owner simulates an attacker by commenting out the normal `smoke_check()` call and uncommenting the payload in `demo_probe.py`, then opening a same-repository PR. The payload stays unmerged.
2. Creating or updating that PR starts CI. With the control off, the payload exchanges the job's GitHub OIDC token for temporary credentials belonging to an isolated exercise deployment role.
3. The payload patches the EKS application. The replacement workload inherits the application's data-reading identity and prints synthetic DynamoDB records into the Actions log, then attempts to restore the application.
4. The owner commits `"enforcement_enabled": true` to `main`. After **Deploy security control** succeeds, a fresh attempt of the attack is denied by AWS STS. Legitimate `main` access remains allowed.

The deployment role cannot read the tables directly: replacing application code is the pivot to data access. The control limits credential issuance by trusted context; it does not scan code or revoke previously issued sessions. The committed setting is **on**; the file alone does not prove the current AWS policy. See the [control explanation](security/README.md).

## Run locally

The application and tests run without AWS or GitHub credentials. Requires Python 3.12+ and Docker with Linux containers.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
export APP_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
docker compose up --build --wait
python scripts/checks/local_api.py
python -m pytest tests
docker compose down
```

On PowerShell, activate with `.venv/Scripts/Activate.ps1` and set the key with `$env:APP_API_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"`. The API is at `http://localhost:8000/docs`; business routes require `X-API-Key`. Local data resets when DynamoDB Local restarts. This local slice exercises the application; the CI-to-AWS attack requires the separate sandbox setup.

## Explore or reproduce

| Guide | Contents |
| --- | --- |
| [Demo walkthrough](docs/demo.md) | Full attack/control comparison, setup prerequisites, evidence, and reset |
| [Architecture](docs/architecture.md) | AWS components, identities, and trust boundaries |
| [Infrastructure](docs/infrastructure.md) and [delivery](docs/delivery.md) | Provisioning, repository variables, and application bootstrap |
| [Testing](docs/testing.md) | Local checks and live acceptance cases |
| [Detection](docs/detection/README.md) | Optional independent CloudTrail/GitHub evidence collection |
| [Teardown](docs/teardown.md) | Removing billable sandbox resources |

This repository is published for inspection. Contributions and live exercise runs are reserved for the owner; reproduce the AWS exercise in your own isolated sandbox using a private copy.
