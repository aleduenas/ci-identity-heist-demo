# Isolated detection exercise identities

This module adds an opt-in exercise deployment role to the existing synthetic lab.
It does not change the normal GitHub build/deploy roles, expose EKS publicly,
create a coding agent, or grant direct access to customer tables.
Local configuration is not evidence of AWS role acceptance or deployment.

## Activation

The composition root sets `enable_detection = false` by default. When enabled,
it derives this module's `allow_pr_demo` from the committed `security/control.json`:
enforcement `true` is main-only; `false` deliberately admits the synthetic PR attack.
The module's own `allow_pr_demo` default remains false for other callers.
Terraform provisions the sandbox once; it is not part of the control workflow.
When enabled, [GitHub Actions](../../../security/README.md) applies the setting
directly through IAM. Do not broaden existing release roles for this exercise.

## GitHub subject contract

The repository must emit the reviewed custom OIDC subject assembled from
`repo`, `context`, `event_name`, `run_id`, and `run_attempt`, in that order.
For this repository the proposed template is:

```text
repo:aleduenas@54992507/ci-identity-heist-demo@1416500552:{context}:event_name:{event_name}:run_id:*:run_attempt:*
```

Supply it as `detection_sub_pattern` only after checking the actual emitted format.
The template makes the repository exact, with wildcards only in signed run
identifiers. The module substitutes these allowed context/event combinations:

| Mode | Context | Event |
| --- | --- | --- |
| Main | `ref:refs/heads/main` | `push` |
| Main | `ref:refs/heads/main` | `workflow_dispatch` |
| Optional A2 | `pull_request` | `pull_request` |

No environment context, `pull_request_target` event, fork repository subject,
or other branch is accepted. The audience must be `sts.amazonaws.com`.
Subject customization affects every OIDC job in the repository: coordinate
normal role/checker migration separately, preserving their main-only boundary.
The module does not customize GitHub settings or migrate other role trusts.

## Permissions and mock identity

The exercise role can describe only the lab cluster. Its EKS access entry maps to
the existing `mybank:deployers` group; namespace RBAC remains in
`deploy/kubernetes/base/rbac/deployers.yaml`. That group can change the app
Deployment, so the role is a real workload trust boundary even though it has
no direct DynamoDB permission. The namespace/RBAC must be bootstrapped first
to demonstrate actual workload access. A2 needs only role issuance and an
identity check; it does not require EKS mutation or PR-runner VPC access.

An optional `mock_operator_principal_arn` creates a mock-agent IAM role
assumable only by that exact IAM user or role in this AWS account. It can
describe the lab cluster and has no EKS access entry, data access, or permission
to assume the exercise role. Null omits it. This identity does not impersonate a
GitHub actor or push PRs: operator-made PR changes must be labeled simulations.

## Outputs and evidence

The sandbox exports `detection_demo_role_arn` for repository variable
`DETECTION_DEMO_ROLE_ARN`, `mock_agent_role_arn`, and `detection_subject_patterns`.
It also exports `security_control_role_arn` and `security_control_subject_prefix`
for `SECURITY_CONTROL_ROLE_ARN` and `SECURITY_CONTROL_SUBJECT_PREFIX`.
Use the same exercise role for N2 main and A2 PR runs. Use independently obtained
GitHub run/attempt evidence; caller-selected role-session names are not proof.
Never print or retain JWTs or temporary credentials as evidence.

`control.tf` provisions a separate main-only automation role with only `iam:GetRole`
and `iam:UpdateAssumeRolePolicy` on the exercise deployment role. It cannot modify
itself or the baseline release roles. Its trust accepts main push/manual events,
never PRs, regardless of the exercise setting. Main repository writers remain a
trusted boundary; protect/review control changes using actual repository settings.
This module provisions no detector, alert destination or application workload.
