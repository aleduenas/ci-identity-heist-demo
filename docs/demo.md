# Sandbox demonstration walkthrough

This repository models a fictional bank's CI/CD pipeline. The exercise shows a specific boundary failure: allowing unreviewed PR code to obtain a deployment identity. All data is synthetic. The attacker is simulated by the owner making a PR; no real account compromise is required.

## Inspect the demo without deploying anything

Read these files in order:

1. [`demo_probe.py`](../scripts/detection/demo_probe.py): the default `smoke_check()` only prints a status line. The commented `run_attack()` block is the simulated attacker change.
2. [`detection-demo.yml`](../.github/workflows/detection-demo.yml): an owner-operated, same-repository PR editing the probe runs it on a GitHub-hosted runner with OIDC token permission. Fork PRs do not run this job.
3. [`control.json`](../security/control.json): `enforcement_enabled` selects the exercise trust state. It is committed as `true`.
4. [`apply_control.py`](../scripts/detection/apply_control.py): the off policy accepts PR context as well as trusted `main`; the on policy removes PR context. The code validates the target role and known policy shape, updates IAM, and verifies readback.
5. [`security-control.yml`](../.github/workflows/security-control.yml): trusted `main` deploys the policy using a separate, narrowly scoped security role. A second job verifies legitimate access to the same exercise role.

The off-state sequence is:

```text
Owner-authored attack PR simulates unreviewed attacker code
  -> GitHub-hosted CI executes the edited probe
  -> GitHub OIDC token is exchanged for exercise deployment credentials
  -> Deployment role patches the EKS application
  -> Replacement workload inherits the application's Pod Identity
  -> Synthetic DynamoDB records appear in the Actions log
  -> Payload attempts a rollout undo
```

With the control on, AWS STS denies the credential exchange. No exercise deployment credentials are issued for that PR attempt. The control is an IAM context restriction, not a malicious-code classifier.

## Read the recorded runs

Both runs use the **Identity boundary checks** workflow and **verify-boundary** job. Expand **Execute PR-editable probe (grabs the identity; on a PR, demonstrates impact)**.

| Run | Expected evidence |
| --- | --- |
| [Control off: attack proceeds](https://github.com/aleduenas/ci-identity-heist-demo/actions/runs/39293282632/job/118199178766) | `obtained_identity` identifies the temporary exercise-role session. `STOLEN CUSTOMER RECORDS` precedes synthetic table output. The payload attempts to undo its application change. |
| [Control on: attack denied](https://github.com/aleduenas/ci-identity-heist-demo/actions/runs/39293816912/job/118201042196) | The probe fails at `AssumeRoleWithWebIdentity`, before any application patch or table read. A red check is the expected blocked-attack result. |

Successful job completion alone does not prove data access: inspect the record output. Similarly, an arbitrary failed job is not proof of prevention: inspect the STS authorization denial. The probe prints the assumed identity and synthetic records, not raw temporary secret keys or the OIDC token.

These runs demonstrate execution, not independent detection. The optional [collector](detection/README.md) correlates CloudTrail events with GitHub run metadata. No production detection accuracy or response-time claim is made. Log links may require GitHub sign-in and can expire under retention settings; the source and this walkthrough remain sufficient to explain the exercise.

## Prepare your own AWS sandbox

The recorded demonstration's AWS environment is torn down, and its **Main release**, **Identity boundary checks**, and **Deploy security control** workflows are disabled in GitHub. Historical runs remain available. Provision a working sandbox and configure its identities before enabling these workflows under **Actions → workflow → Enable workflow** in your own copy. Local PR checks and infrastructure validation do not need a live AWS environment.

The public demonstration is available for inspection. Use your own **private** repository and a dedicated AWS account to reproduce the live attack. The `scripts.demo` lifecycle helpers intentionally reject public repositories; local application tests do not need a GitHub repository or AWS resources.

1. Install the Python development dependencies as shown in the [root README](../README.md#run-locally). For AWS setup, also install Terraform, AWS CLI v2, the Session Manager plugin, Docker, and a kubectl version compatible with the cluster. The existing defaults target EKS 1.35; review support before provisioning.
2. Create a private GitHub repository containing this source and set its URL as `origin`. Authenticate as its owner through Git Credential Manager or a process-scoped `GH_TOKEN`/`GITHUB_TOKEN`; never commit the token. Workflow owner checks require an owner-operated personal repository.
3. Follow the [infrastructure guide](infrastructure.md) and [state bootstrap](../infra/bootstrap/README.md) to configure your own AWS account, state bucket, and bootstrap administrator. The [example configuration](../infra/environments/sandbox/demo.tfvars.json.example) enables the exercise roles, signed run context, and CI-reachable EKS control-plane API. Workers and the application remain private.
4. Follow [delivery setup](delivery.md) to build/publish the image, bootstrap Kubernetes, register the trusted private release runner, and seed the synthetic tables. The [lifecycle helper guide](../scripts/demo/README.md) provides the coordinated alternative for setup; inspect the Terraform plan before applying.
5. Configure GitHub OIDC with your repository's immutable identity and signed event/run context. Use the [detection setup](detection/README.md) and actual Terraform outputs, rather than copying this repository's numeric IDs or role ARNs.
6. Set the repository variables below. Keep `DEPLOY_ENABLED` false until application bootstrap and trusted runner registration are complete. Confirm a harmless owner PR passes before activating the payload.

| Repository variable | Terraform output / meaning |
| --- | --- |
| `AWS_REGION` | `aws_region` |
| `AWS_BUILD_ROLE_ARN` | `build_role_arn` |
| `AWS_DEPLOY_ROLE_ARN` | `deploy_role_arn` |
| `ECR_REPOSITORY_URL` | `ecr_repository_url` |
| `EKS_CLUSTER_NAME` | `cluster_name` |
| `DETECTION_DEMO_ROLE_ARN` | `detection_demo_role_arn` |
| `SECURITY_CONTROL_ROLE_ARN` | `security_control_role_arn` |
| `SECURITY_CONTROL_SUBJECT_PREFIX` | `security_control_subject_prefix` |
| `MYBANK_OIDC_RUN_CONTEXT` | `true`, matching the coordinated OIDC configuration |
| `DEPLOY_ENABLED` | `true` only after release setup is complete |

No AWS access-key secret is required in Actions. Provisioning is billable; review [costs](infrastructure.md#cost-and-availability) and [teardown](teardown.md) before setup. Employee SAML federation is supporting functionality and is not required for this attack/control comparison.

## Compare the two control states

1. In your isolated copy, change `security/control.json` to `{"enforcement_enabled": false}` and commit it to `main`. Wait for **Deploy security control**, including **verify-main-access**, to succeed. An edit on an unmerged PR does not deploy the setting.
2. Create a branch from `main`. In `scripts/detection/demo_probe.py`, comment out the normal `if __name__ == "__main__": smoke_check()` block and uncomment the entire attack block, including its final `run_attack()` entry point.
3. Push that branch to the same repository and open a PR as the owner. Leave it unmerged. In **Identity boundary checks**, inspect the probe for the assumed identity and synthetic customer records. The payload uses the deployment identity to patch the app; it reads data through the replacement workload's identity, not directly from the deployment role.
4. Separately commit `{"enforcement_enabled": true}` to `main`. Wait for the control workflow to print `SAVED AND VERIFIED` and for the legitimate main-role verification to pass.
5. Push a new commit to the existing attack PR, such as a change to `CHECK_NOTE`, to start a **fresh** attempt. The PR should now fail at STS authorization before deployment. Allow for IAM propagation and inspect the actual failure rather than relying on the job color.
6. Submit a separate harmless owner PR with the default probe. It should pass because it requests no AWS credentials. Record this alongside the denied attack and the successful main-role verification.

Changing the setting only affects newly requested credentials after IAM propagation; it does not revoke sessions already issued in the off state. A fork PR is not an equivalent test because this demo job excludes forks even when the IAM control is off.

## Finish the exercise

Keep enforcement on. Close the attack PR without merging it. Inspect the application rollout and readiness; if the payload was interrupted, its undo may not have completed. Restore the known-good workload using the [deployment guide](deployment.md) and confirm readiness before claiming recovery.

Retain only reviewed, sanitized evidence. Disable live deployment when the sandbox is idle, remove the trusted runner registration when finished, and follow [teardown](teardown.md) to remove billable infrastructure. The repository's boolean describes the committed desired state; verify the last successful control deployment and live AWS policy to establish enforcement.
