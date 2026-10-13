# Implementation handoff

Updated: 2026-10-13.

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

- An AWS sandbox account and authenticated operator; no AWS resources have been applied.
- AWS CLI v2 and Session Manager plugin, plus an existing bootstrap administrator IAM role.
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
- [GitHub hosted CI](https://github.com/aleduenas/mybank-eks-sandbox/actions/runs/38352721327): application tests/container smoke, Terraform and Kubernetes checks all passed on implementation commit `0c2e67f`. AWS publish/deploy skipped as intended while repository variables are unset. Final OIDC compatibility follow-up is being verified separately.
- GitHub API verified repository remains private and uses immutable OIDC subjects; AWS trust updated to the exact owner/repository IDs, with a hosted nonsecret claim-format check.

No AWS plan/apply, STS federation, live IAM/CNI enforcement, CloudTrail delivery or EKS rollout has been performed. Local signatures were checked for presence, not independently verified cryptographically. Temporary test containers and generated identity artifacts are removed after verification.

## Continuation checklist

1. Follow `docs/deployment.md` with an authenticated sandbox account; configure the state bucket and real bootstrap role.
2. Review/apply AWS resources; save actual Terraform outputs and inspect healthy add-ons/SSM connectivity.
3. Publish the first image and bootstrap Kubernetes; seed synthetic records and run the API smoke through administrator port-forward.
4. Register/configure the trusted runner and repository variables, then prove a main-branch release.
5. Generate the real account realm, export metadata and apply SAML; verify real engineer/support sessions and denied operations.
6. Verify audit delivery and network enforcement; record live acceptance outcomes and retained image digests.
7. Run teardown after the exercise, retaining only deliberately selected evidence/state.
