# Implementation handoff

Updated: 2026-10-17.

## Active D2 continuation

Use [the D2 handoff checklist](d2/HANDOFF.md) as the current resumable ledger.
The user authorized full AWS/GitHub D2 setup, then requested a handoff before further provisioning.

- Verified temporary CLI/SDK access as sandbox user `codex-builder` in account `404824402451`.
- Created a plain USD20 monthly AWS budget that emails an alert (alert only; nothing is shut down).
- Applied private state storage and narrow bootstrap IAM role (7 creates).
- Full private EKS/D2 environment: reviewed saved plan only, 65 creates/9 data reads; **not applied**.
- New D2 infrastructure, collector, workflow, tests and optional OIDC migration are local/uncommitted.
  GitHub still has default immutable subjects and no repository variables; no new CI/deployment ran.
- Current local checks: Ruff passed; **93 pytest tests passed**; **6 delivery checks passed** with
  filesystem escalation; formatting and all three Terraform roots validated.
- Budget alerts are delayed billing telemetry, not a spending cap. EKS rollout and N2/A2/B2 remain unvalidated.

The sections below retain the original implementation history; current live facts above supersede
older statements that no AWS resources have been applied or all working changes were pushed.

## Completed

- Created and verified private repository `https://github.com/aleduenas/mybank-eks-sandbox`.
- Agreed architecture in `docs/architecture.md` before parallel implementation.

## Implemented

- Infrastructure: seven modules, private EKS, DynamoDB, audit, SAML/workload identity, CI IAM and SSM operations host; separate state bootstrap and environment roots.
- Application: layered transactional API, DynamoDB atomic persistence, idempotency, authentication, synthetic fixtures and privacy-preserving JSON request logs.
- Delivery: restricted Kubernetes manifests, GitHub Actions OIDC build/deploy, immutable-image retries, bootstrap/render/rollout helpers and runner documentation.
- Identity: local Keycloak, generated account-specific group claims, real metadata export and temporary STS profile helper.
- Integration: root README, deployment/access/testing/evidence/teardown runbooks, account-checked AWS seeding and scoped continuation instructions.

## External prerequisites

- AWS account, temporary CLI/SDK access, Session Manager plugin and bootstrap role are now prepared;
  see the current checklist before using them because login can expire.
- Operator registration of the trusted runner on the provisioned private operations host.
- Account-specific Keycloak realm metadata and second Terraform apply for SAML; no paid/existing IdP required.
- GitHub repository variables from Terraform outputs; deployment remains disabled until bootstrap is complete.

## Verification

- `pytest tests`: 32 passed on Python 3.14. One Starlette/HTTPX test-client deprecation warning; tests succeed.
- `ruff check app tests identity scripts`: passed.
- Delivery unittest discovery: 6 passed, covering manifests, permission boundaries and immutable publication retries.
- Terraform 1.13.5 formatting and both root validations: passed. AWS provider 6.68.0 lockfiles verified for Linux and Windows.
- Kubeconform 0.7.0: all 10 Kubernetes resources valid against 1.35.0 schemas.
- Actionlint 1.7.7: all three workflows passed.
- Docker build/runtime: Python 3.12 Linux CPU image runs as nonroot with read-only API filesystem; localhost probes healthy.
- DynamoDB Local 3.1.0 API smoke: readiness, authentication, atomic balance updates, matching retry, conflicting retry and overdraft rollback passed.
- Keycloak 26.6.4 local smoke: both employee profiles emitted separate role claims, AWS audience and signed assertions. Public metadata export succeeded. Assertions were not submitted to AWS.
- [Final GitHub hosted CI](https://github.com/aleduenas/mybank-eks-sandbox/actions/runs/38353103026): application tests/container smoke, Terraform, Kubernetes and live GitHub OIDC claim-format checks all passed on code commit `05d8535`. AWS publish/deploy skipped as intended while repository variables are unset. Earlier implementation CI also passed. The final documentation-only handoff commit skips redundant CI.
- GitHub API verified repository remains private and uses immutable OIDC subjects; AWS trust updated to the exact owner/repository IDs, with a hosted nonsecret claim-format check.

At the original 2026-10-13 handoff, no AWS plan/apply, STS federation, live IAM/CNI enforcement,
CloudTrail delivery or EKS rollout had been performed. The 2026-10-17 bootstrap apply and
local-development CLI login are recorded above; they do not establish application deployment,
employee SAML federation, live workload enforcement or D2 detection. Original local SAML signatures
were checked for presence, not independently verified cryptographically.

## Repository layout verification

- Private visibility and immutable OIDC settings were verified through GitHub's repository API.
- All application, identity, script, test and Terraform code files are 116 lines or fewer. Transfer invariants and recovery tests are separate modules.
- Local documentation links resolve; Git attributes preserve Linux line endings, including EC2 user-data shell scripts.
- Original implementation was committed and pushed. Current D2 additions are uncommitted/unpushed;
  ignored credentials, local state/plans, login cache and generated evidence remain excluded.

## Continuation checklist

1. Follow `docs/deployment.md` with an authenticated sandbox account; configure the state bucket and real bootstrap role.
2. Review/apply AWS resources; save actual Terraform outputs and inspect healthy add-ons/SSM connectivity.
3. Publish the first image and bootstrap Kubernetes; seed synthetic records and run the API smoke through administrator port-forward.
4. Register/configure the trusted runner and repository variables, then prove a main-branch release.
5. Generate the real account realm, export metadata and apply SAML; verify real engineer/support sessions and denied operations.
6. Verify audit delivery and network enforcement; record live acceptance outcomes and retained image digests.
7. Run teardown after the exercise, retaining only deliberately selected evidence/state.
