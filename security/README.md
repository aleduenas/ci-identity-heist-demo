# GitHub-deployed IAM control

The attack obtains deployment credentials from an unreviewed PR. This control
changes the exercise role's AWS IAM trust so only the intended `main` contexts
can obtain credentials. GitHub Actions deploys the change through OIDC; the
presenter needs no AWS credentials or terminal during the demo.

## Immediately after showing the successful attack

One-time setup below must already be complete. Keep the attack PR open; do not merge it.

1. In GitHub **Code**, open [`scripts/detection/apply_control.py`](../scripts/detection/apply_control.py).
   Show the complete implementation. It reads one setting, builds the allowed
   trust policy, rejects unexpected live policies, calls IAM and verifies readback.
   The IAM role and workflow are also reviewable in
   [`control.tf`](../infra/modules/detection/control.tf) and
   [`security-control.yml`](../.github/workflows/security-control.yml).
2. Open [`security/control.json`](control.json), click **Edit** and change
   `"enforcement_enabled": false` to `"enforcement_enabled": true`.
   Get this change onto `main` through the repository's authorized merge process.
   Editing the attack branch alone does not deploy it. If branch protections require
   a PR, create a separate control-change PR, review it and merge that harmless change.
3. Open **Actions > Deploy security control**, then the new run for that `main`
   change. Open **deploy-control > Show, apply and verify the exercise trust policy**.
   Point to `BEFORE`, `DESIRED enforcement_enabled=true` and `SAVED AND VERIFIED`.
   The `pull_request` subject disappears; the two `main` subjects remain.
   The run summary also displays the saved policy. Wait for both jobs to finish green.
4. Show **verify-main-access**. It obtains the **same exercise role** from `main`
   and prints its identity, proving legitimate credential issuance still works.
   This job does not deploy anything or read customer records.
5. Return to the existing malicious PR. Edit only `CHECK_NOTE` in
   `scripts/detection/demo_probe.py` to trigger a **fresh** run; keep its attack
   payload unchanged. Open **Identity boundary checks > verify-boundary**.
   The probe must fail at `AssumeRoleWithWebIdentity` with an authorization denial,
   before any app patch or customer-record read. An unrelated red check is not proof.
   Allow IAM propagation; if necessary trigger another fresh run after a short wait.
6. Make the original legitimate change on a clean branch: change only `CHECK_NOTE`,
   leaving the payload commented and `smoke_check()` active. Show its new CI run
   passing while enforcement remains enabled. Keep this distinct from the attack PR.

Talk track: "The security rule is versioned in Git. An authorized pipeline deploys
it using a role that can edit only this exercise role's trust. AWS now refuses
deployment credentials to PR jobs. The same attack stops before deployment or data
access, while legitimate checks and main-context access continue to work."

No Terraform runs anywhere in this demo sequence. Terraform is only for initial
sandbox provisioning. The activation workflow calls IAM directly.

## What each part of the code does

| Part | Meaning |
| --- | --- |
| `enforcement_enabled` | `true`: main-only trust; `false`: deliberately vulnerable synthetic lab state |
| `load_setting` | Requires one actual JSON boolean; a string such as `"false"` is rejected |
| `trust_policy` | Names the GitHub provider, STS audience, exact immutable repository and permitted contexts |
| `same_policy` | Compares policies while allowing harmless JSON/subject ordering differences |
| `apply_control` | Checks the target ARN and known policy shape, prints before/desired, updates IAM and verifies saved policy |
| `main` | Reads explicit inputs, creates the IAM SDK client and writes the GitHub run summary |
| Workflow OIDC step | Gets temporary credentials for the security automation role |
| `verify-main-access` | Independently verifies main can still obtain the exercise role |

The automation role can only `iam:GetRole` and `iam:UpdateAssumeRolePolicy` on
the exact exercise role. It cannot edit its own trust, alter the baseline release
roles, access tables or deploy the app. Its trust remains main-only whether the
exercise control is on or off. IAM trusts the repository's main context, not a
particular workflow filename: trusted main writers are inside this boundary.

## One-time initial sandbox setup, before the presentation

An authorized infrastructure operator must provision the new role and inline
policy from `infra/modules/detection/control.tf` using the normal reviewed initial
sandbox plan/apply procedure. Do this before the demo, never as a presentation step.
The optional detection module must be enabled, and this repository's existing
immutable custom OIDC template must already be configured. Do not widen a release role.

Set these GitHub **Settings > Secrets and variables > Actions > Variables** from
the corresponding sandbox outputs; these ARNs/prefixes are configuration, not credentials:

| GitHub variable | Terraform output |
| --- | --- |
| `SECURITY_CONTROL_ROLE_ARN` | `security_control_role_arn` |
| `SECURITY_CONTROL_SUBJECT_PREFIX` | `security_control_subject_prefix` |
| `DETECTION_DEMO_ROLE_ARN` | `detection_demo_role_arn` (already used by the attack) |
| `AWS_REGION` | `aws_region` |

Fresh `scripts.demo.up` setup wires these values after provisioning. For an already
running sandbox, the operator provisions the new role once and sets the variables;
there is no need to rebuild EKS or rerun the full standup.

Before presenting, open **Actions > Deploy security control > Run workflow**, select
`main` and run it against the initial `false` setting. Verify both jobs succeed.
This rehearses deployment and leaves the lab ready for the original successful attack.
Review main-branch protections and who can approve/merge control changes. Do not
claim a protected approval process unless it is actually configured. An unmerged
PR has no main OIDC subject and cannot assume the automation role.

## State ownership, reset and evidence

Both initial Terraform provisioning and the GitHub deployment read `control.json`.
The old root `allow_pr_demo` input is accepted for compatibility but no longer
controls trust. Use an up-to-date trusted `main` checkout for infrastructure work.
`scripts.demo.prevent` now stops with a pointer here instead of running Terraform.
Direct manual IAM edits are an emergency fallback and diverge from the committed setting.

Only reset after the presentation: change `true` back to `false` through the same
authorized main deployment, and verify it. That deliberately reopens exercise PR
trust; it never changes the automation role's own trust. Do not reset automatically.

Keep the control commit, successful deployment/main-proof run, denied malicious run
and passing harmless run as evidence. The policy blocks **new** credential issuance;
it does not revoke old sessions. Audit records can still be generated by denied
attempts. This is prevention; the separate CloudTrail detector is optional supporting
visibility and is not required for control activation.
