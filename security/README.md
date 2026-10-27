# GitHub-deployed IAM control

The recorded demonstration's AWS environment is torn down and **Deploy security control** is disabled. The behavior below applies after provisioning a sandbox and enabling its live workflows; see the [demo walkthrough](../docs/demo.md).

The attack obtains deployment credentials from an unreviewed PR. This control
changes the exercise role's AWS IAM trust so only the intended `main` contexts
can obtain credentials. The control code is already written: changing
`security/control.json` enables it through a prepared GitHub workflow. The script
is a small example of deployment; IAM enforces the rule.

The committed flag is currently `true` (enforcement enabled). Setting it back to
`false` restores the deliberately vulnerable lab state in which an unreviewed PR
can obtain the role.

## How the control is deployed

The environment and control code are provisioned ahead of time. The attack PR, if
present, stays open and unmerged.

1. [`scripts/detection/apply_control.py`](../scripts/detection/apply_control.py) is
   the complete implementation. It reads one setting, builds the allowed trust
   policy, rejects unexpected live policies, calls IAM and verifies readback.
   [`security-control.yml`](../.github/workflows/security-control.yml) authenticates
   and runs that script on `main`.
2. [`security/control.json`](control.json) holds `"enforcement_enabled"`. Changing
   `false` to `true` and getting that change onto `main` through the repository's
   authorized merge process deploys the restrictive trust. Editing an unmerged
   branch does not deploy it; if branch protections require a PR, use a separate,
   reviewed control-change PR.
3. **Deploy security control** runs for the `main` change. Its **deploy-control**
   job prints `BEFORE`, `DESIRED enforcement_enabled=true` and `SAVED AND VERIFIED`;
   the `pull_request` subject disappears while the two `main` subjects remain. The
   run summary also records the saved policy.
4. **verify-main-access** obtains the **same exercise role** from `main` and prints
   its identity, confirming legitimate credential issuance still works. It does not
   deploy anything or read customer records.

With enforcement on, a PR that requests the deployment role fails at
`AssumeRoleWithWebIdentity` with an authorization denial, before any app patch or
customer-record read. A harmless PR that makes no AWS call still passes. The
workflow calls IAM directly to apply and verify the policy; a setting-only commit
deploys the control independently of the application release.

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

This is a context rule, not a malicious-code scanner: on-state trust denies every
PR job this deployment role. Harmless PRs pass because they do not ask for it.
The allowed main contexts are push and workflow_dispatch. The signed subject
contains exact immutable repository identity plus context/event; only run and
attempt counters are wildcarded. A release-looking session name cannot change it.

Changing the file on an unmerged PR does not change IAM. Changing an Actions
variable alone is not the deployment trigger. Main push runs the workflow; manual
dispatch reconciles the current committed setting rather than supplying another
on/off value. Serialized runs and current-main checkout avoid restoring stale
settings from queued commits.

The automation role can only `iam:GetRole` and `iam:UpdateAssumeRolePolicy` on
the exact exercise role. It cannot edit its own trust, alter the baseline release
roles, access tables or deploy the app. Its trust remains main-only whether the
exercise control is on or off. IAM trusts the repository's main context, not a
particular workflow filename: trusted main writers are inside this boundary.

## Prerequisites

These identities and repository variables are configuration, not stored AWS
credentials:

| GitHub variable | Meaning |
| --- | --- |
| `SECURITY_CONTROL_ROLE_ARN` | Narrow security identity permitted to update the exercise role's trust |
| `SECURITY_CONTROL_SUBJECT_PREFIX` | Exact immutable GitHub repository identity in the OIDC subject |
| `DETECTION_DEMO_ROLE_ARN` | Exercise deployment identity used by the attack and main-access comparison |
| `AWS_REGION` | Region used by the control workflow |

An unmerged PR has no main OIDC subject and cannot assume the automation role.
Review main-branch protections and who can approve/merge control changes. Do not
claim a protected approval process unless it is actually configured.

## State ownership, reset and evidence

The workflow reads the committed `control.json` setting on main and reconciles
the exercise role's trust. An unmerged PR's copy does not activate the control.

Setting `true` back to `false` through the same authorized main deployment
reopens exercise PR trust; it never changes the automation role's own trust. Do
not reset automatically.

Keep the control commit, successful deployment/main-proof run, denied malicious run
and passing harmless run as evidence. The policy blocks **new** credential issuance;
it does not revoke old sessions. Audit records can still be generated by denied
attempts. This is prevention; the separate CloudTrail detector is optional supporting
visibility and is not required for control activation.

## Production delivery

In production, express the restrictive IAM trust as reviewed security-as-code.
For example, a dedicated GitHub Actions YAML workflow could deploy an approved
policy from protected main using a security role limited to the intended target
role. The job would validate the target account and role, apply the reviewed
policy, verify readback, and retain evidence. Main protections and trusted code
execution need independent verification; main context alone does not prove review.

The policy would accept the intended provider, audience, repository and release
contexts while excluding PR validation. Another reviewed security deployment
system could deliver the same rule. Production would keep the restriction
enforced rather than expose the permissive off state. The prebuilt lab script is
an example of this deployment pattern, not a complete production implementation;
its lab-specific target checks would need adaptation.
