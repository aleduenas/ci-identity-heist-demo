# Isolated D2 exercise identities

This module adds an opt-in demo deployment role to the existing synthetic lab.
It does not change the normal GitHub build/deploy roles, expose EKS publicly,
create a coding agent, or grant direct access to customer tables.
Local configuration is not evidence of AWS role acceptance or deployment.

## Activation

The composition root sets `enable_d2 = false` by default. When enabled, the
demo role remains main-only unless `allow_pr_demo = true` is explicitly set for
the bounded A2 exercise. Set it back to false for B2 and review/apply the change.
Do not broaden the existing release-role trusts to accommodate this exercise.

## GitHub subject contract

The repository must emit the reviewed custom OIDC subject assembled from
`repo`, `context`, `event_name`, `run_id`, and `run_attempt`, in that order.
For this repository the proposed template is:

```text
repo:aleduenas@54992507/mybank-eks-sandbox@1416500552:{context}:event_name:{event_name}:run_id:*:run_attempt:*
```

Supply it as `d2_sub_pattern` only after checking the actual emitted format.
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

The demo role can describe only the lab cluster. Its EKS access entry maps to
the existing `mybank:deployers` group; namespace RBAC remains in
`deploy/kubernetes/base/rbac/deployers.yaml`. That group can change the app
Deployment, so the role is a real workload trust boundary even though it has
no direct DynamoDB permission. The namespace/RBAC must be bootstrapped first
to demonstrate actual workload access. A2 needs only role issuance and an
identity check; it does not require EKS mutation or PR-runner VPC access.

An optional `mock_operator_principal_arn` creates a mock-agent IAM role
assumable only by that exact IAM user or role in this AWS account. It can
describe the lab cluster and has no EKS access entry, data access, or permission
to assume the demo role. Null omits it. This identity does not impersonate a
GitHub actor or push PRs: operator-made PR changes must be labeled simulations.

## Outputs and evidence

The sandbox exports `d2_demo_role_arn` for repository variable
`D2_DEMO_ROLE_ARN`, `mock_agent_role_arn`, and `d2_subject_patterns`.
Use the same demo role for N2 main and A2 PR runs. Use independently obtained
GitHub run/attempt evidence; caller-selected role-session names are not proof.
Never print or retain JWTs or temporary credentials as evidence.

This module contains no detector, alert destination, GitHub workflow, budget,
or application workload deployment. See the immutable concept's D2 hypothesis in
`docs/plan/Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md`.
