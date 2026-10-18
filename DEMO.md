# Mybank security-as-code demo

All records are synthetic in the owned AWS sandbox. The presentation happens in
GitHub: show a harmless PR, show the malicious PR, enable the control, repeat the
malicious action and repeat the harmless action.

The attack executes on a GitHub-hosted PR runner. It obtains the isolated
`mybank-sandbox-detection-demo-deploy` role through OIDC, patches the EKS
application and inherits the application's Pod Identity data access. Normal
build/deploy roles are separate and remain main-only.

The control is an IAM trust policy. Its code is in
[scripts/detection/apply_control.py](scripts/detection/apply_control.py), its switch
is [security/control.json](security/control.json), and
[Deploy security control](.github/workflows/security-control.yml) applies it.
No local terminal or AWS credentials are required during the presentation.
**Terraform is only used for initial sandbox provisioning, never during the demo.**
Infrastructure CI runs separately for infrastructure edits. Probe edits and the
control toggle do not trigger it; security-only commits also skip the app release.

## Before presenting: initial setup and rehearsal

Follow [sandbox setup](docs/deployment.md) and the
[control's one-time setup](security/README.md#one-time-initial-sandbox-setup-before-the-presentation).
An authorized infrastructure operator must have provisioned the separate security
automation role and set its GitHub variables. It can read/update only the exercise
role's trust. It has no data or deployment access and never trusts PRs.

The existing demo uses a CI-reachable EKS control-plane endpoint; worker nodes and
the application Service remain private. This flow adds no network exposure.
The custom OIDC subject contains the immutable repository prefix, context, event,
run ID and attempt. Preserve that existing contract.

Start with `security/control.json` set to `{"enforcement_enabled": false}`.
Run **Actions > Deploy security control > Run workflow > main** and verify
both jobs pass before the presentation. Confirm the exercise role admits PRs,
the application has recovered from earlier attacks and no previous attack is running.
Review who can merge to main; do not claim branch protections that are not configured.
Keep the separate control-change branch clean of attack code.

## Step 1: show the legitimate action

1. GitHub **Code > scripts/detection/demo_probe.py > Edit**.
2. Change only `CHECK_NOTE = "ok"` to another harmless value.
   Leave `smoke_check()` active and the entire attack payload commented out.
3. Create a clean branch and pull request.
4. Show its passing checks. The probe prints a harmless status line and makes
   no AWS request. Retain this run for comparison.

## Step 2: show the malicious action

1. On a separate branch, edit the same probe. Comment out the two existing
   entrypoint lines (`if __name__ == "__main__":` and `smoke_check()`).
2. Uncomment the entire prewritten attack block at the bottom of the file.
   It represents code authored by an attacker using stolen repository access.
3. Open an unreviewed same-repository PR; **do not merge it**.
4. Open **Identity boundary checks > verify-boundary**, then the probe step.
   Show the obtained exercise-role identity, the app replacement and the
   `STOLEN CUSTOMER RECORDS` output containing the fictional accounts/customers.
5. Confirm the legitimate app has recovered before continuing. Retain this run.
   The existing payload attempts rollback; its printed restoration message alone
   does not establish readiness.

Say: "An unreviewed PR obtained deployment credentials, replaced the application
and used the application's identity to read our synthetic customer records."

## Step 3: show and activate the control in GitHub

This is the point immediately after demonstrating that the attack works.

1. Open **Code > scripts/detection/apply_control.py**. Show the complete script.
   Use the [code explanation](security/README.md#what-each-part-of-the-code-does):
   strict boolean setting, exact allowed subject patterns, known-policy check,
   IAM update and readback verification. All substantive logic is in this file.
2. Open **Code > security/control.json > Edit**.
   Change `"enforcement_enabled": false` to `"enforcement_enabled": true`.
3. Put that one-line change onto `main` through the authorized merge process.
   If a PR is required, use a separate harmless control-change PR and merge it.
   Changing the unmerged attack branch does not activate the control.
4. Open **Actions > Deploy security control**, then the run for the main change.
5. Under **deploy-control > Show, apply and verify the exercise trust policy**,
   show `BEFORE`, `DESIRED enforcement_enabled=true` and `SAVED AND VERIFIED`.
   Explain that the PR subject is removed while both main subjects remain.
   The saved policy is also in the run summary.
6. Wait for both jobs to pass. Show **verify-main-access**, which obtains the
   **same exercise role** from main and prints its identity without changing EKS
   or reading tables.

Say: "The rule is security as code. GitHub deploys it with temporary credentials
and permission to edit just this role's trust. AWS will now refuse deployment
credentials to PR jobs."

No Terraform command, monitor, local login or console policy edit is part of
this activation. The workflow calls IAM directly.

## Step 4: repeat the malicious action and show it blocked

1. Return to the existing malicious PR branch. Change only `CHECK_NOTE` to
   trigger a fresh run; leave the attack payload unchanged.
2. Open the new **Identity boundary checks > verify-boundary** run.
3. Show the probe failing at `AssumeRoleWithWebIdentity` with an authorization
   denial. It must stop before obtaining credentials, patching the app or reading
   customer records. Failure in checkout/dependency installation is not acceptance.
4. IAM propagation may take time; if needed wait briefly and trigger another
   fresh run. Compare this run with the successful attack's earlier run.

A denied attempt may still generate audit events. This control blocks new
credential issuance; it does not revoke sessions issued before activation.

## Step 5: repeat the legitimate action and show it passing

1. On a clean branch based on main, edit only `CHECK_NOTE` in the harmless probe.
   Keep `smoke_check()` active and the attack payload commented.
2. Open/update its harmless PR and show the fresh CI run passing while the control
   remains `true`. Do not merge the attack PR.
3. Contrast the denied attack with the passing harmless check. The control
   workflow's main-proof job separately established preserved AWS role issuance.

## Reset, optional detection and troubleshooting

After the demo, an explicitly authorized reset changes the setting back to
`false` through the same main workflow. This reopens the synthetic vulnerability.
Close the attack PR without merging. Never reset automatically during activation.

The existing CloudTrail collector is optional supporting detection. It observes
events; it does not enforce this policy and is not required for this sequence.
Historical detection evidence is in [docs/detection/evidence.md](docs/detection/evidence.md).

| Symptom | Check |
| --- | --- |
| Control run fails in one-time setup | Provision the automation role before the demo and set the variables in [security/README.md](security/README.md) |
| No run after changing the flag | The change must reach main; use manual Run workflow on main to reconcile the current committed setting |
| Unrecognized live trust policy | Compare the live role and exact repository prefix with initial setup; the script deliberately refuses unexpected policy shapes |
| Attack still obtains credentials | Confirm the true-setting deployment finished; allow IAM propagation and use a fresh run |
| Harmless check unexpectedly calls AWS | Use a clean branch with the attack commented, not the malicious PR |
| Need to explain the AWS permission | Use the permission description in [security/README.md](security/README.md): two IAM actions on the exact exercise role |

Record actual runs separately from static checks in
[verification status](docs/implementation-status.md).
Infrastructure teardown is a separate operator task in [docs/teardown.md](docs/teardown.md).
