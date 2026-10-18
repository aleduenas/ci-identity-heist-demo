# Implementation handoff

Updated: 2026-10-17.

## Active detection continuation

Use [detection evidence](detection/evidence.md) for results.

- Verified temporary CLI/SDK access as sandbox user `codex-builder` in account `404824402451`.
- Bootstrap state storage, narrow bootstrap role and a plain USD20 budget email alert are live (alert only).
- detection code, OIDC run-context migration and docs are committed and pushed to `main`; hosted CI is green.
- 2026-10-17: the full private sandbox was **applied** (65 resources, EKS 1.35 private endpoint only, healthy
  nodes, add-ons and SSM). The GitHub OIDC template and `MYBANK_OIDC_RUN_CONTEXT` were switched together, and the
  emitted subject was verified live.
- Live detection results: N2 `expected_release`; A2 unreviewed PR `pr_role_misuse` with an observed TTD of 31.1 s; B2
  PR denied while main succeeds; live missing-context gives `context_not_verified`. The mock-agent role was verified inspect-only.
- The lab was then **destroyed**; only the audit evidence bucket remains in sandbox state (`force_destroy=false`).
- Not performed: application image publish/rollout, private runner, synthetic data seeding, SAML federation,
  live CNI enforcement, and any later attack step (deployment change, data read, egress).
- Current local checks: Ruff passed; **70 pytest tests passed**; Terraform fmt passed.

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
employee SAML federation, live workload enforcement or detection. Original local SAML signatures
were checked for presence, not independently verified cryptographically.

## Repository layout verification

- Private visibility and immutable OIDC settings were verified through GitHub's repository API.
- All application, identity, script, test and Terraform code files are 116 lines or fewer. Transfer invariants and recovery tests are separate modules.
- Local documentation links resolve; Git attributes preserve Linux line endings, including EC2 user-data shell scripts.
- Original implementation and detection additions are committed and pushed;
  ignored credentials, local state/plans, login cache and generated evidence remain excluded.

## Continuation checklist

1. Follow `docs/deployment.md` with an authenticated sandbox account; configure the state bucket and real bootstrap role.
2. Review/apply AWS resources; save actual Terraform outputs and inspect healthy add-ons/SSM connectivity.
3. Publish the first image and bootstrap Kubernetes; seed synthetic records and run the API smoke through administrator port-forward.
4. Register/configure the trusted runner and repository variables, then prove a main-branch release.
5. Generate the real account realm, export metadata and apply SAML; verify real engineer/support sessions and denied operations.
6. Verify audit delivery and network enforcement; record live acceptance outcomes and retained image digests.
7. Run teardown after the exercise, retaining only deliberately selected evidence/state.
