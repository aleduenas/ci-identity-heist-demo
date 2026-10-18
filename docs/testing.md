# Repeatable verification

## Local checks

Install `python -m pip install -e '.[dev]'` in a virtual environment. Run:

```bash
python scripts/checks/repository_hygiene.py
ruff check app tests identity scripts
pytest tests
python -m unittest discover -s scripts/deploy -p 'test_*.py'
terraform fmt -check -recursive infra
terraform -chdir=infra/bootstrap init -backend=false
terraform -chdir=infra/bootstrap validate
terraform -chdir=infra/environments/sandbox init -backend=false
terraform -chdir=infra/environments/sandbox validate
```

Delivery tests need kubectl for local Kustomize rendering. CI additionally validates all ten Kubernetes resources with checksum-verified kubeconform and builds/runs the Compose transactional slice. Actionlint was used locally to check workflow semantics. The provider lockfiles contain Linux and Windows checksums.

Start [the local application](../README.md) and run `python scripts/checks/local_api.py`. Start [local Keycloak](identity.md) with a generated realm and run `python scripts/checks/local_identity.py`. The latter checks separate employee role claims, AWS audience, and the presence of assertion signatures; it does not submit anything to AWS or independently verify the cryptographic signature. It reads the ignored realm's lab credentials and refuses redirects outside localhost.

## What each check proves

| Check | Evidence | Remaining live check |
| --- | --- | --- |
| Unit/API tests | Conditions, retries, auth, privacy, fixture safety | AWS DynamoDB/IAM behaviour |
| Docker API smoke | Real DynamoDB Local atomic operations; CPU Linux image | EKS readiness/Pod Identity |
| Realm tests/local IdP smoke | Separate groups and signed SAML claim emission | STS acceptance/role permissions |
| Terraform validate | Provider schema and module references | Account permissions, plan, apply |
| Kubernetes schema/contracts | Valid resource shape and declared boundaries | Admission, CNI enforcement, real RBAC |
| Workflow lint | YAML/action/event/expression correctness | Hosted CI and trusted runner release |

## AWS acceptance matrix

- Bootstrap admin: manifests apply, pods become ready, administrator port-forward reaches the API.
- API: valid transfer updates both balances once; matching retry replays; conflicting retry and overdraft fail without partial ledger writes.
- Engineer SAML session: EKS describe, workload read and logs succeed; Secret read, exec and direct table read fail.
- Support SAML session: synthetic table reads succeed; writes and Kubernetes access fail.
- Release OIDC session: main image publish and Deployment rollout succeed; Secrets and unrelated namespace mutation fail.
- Network: no public app endpoint; ordinary pod ingress is denied; app obtains Pod Identity credentials and reaches tables.
- Evidence: request JSON logs, EKS audit events and delivered CloudTrail table events match the exercise.
- Recovery: a known-good image digest rolls out; teardown removes compute while preserving selected evidence.

Record commands/results with credentials and assertions excluded. [Implementation status](implementation-status.md) states what was actually run; this matrix is the remaining live acceptance plan.

## Publication hygiene

`python scripts/checks/repository_hygiene.py` scans tracked working files and new, unignored files.
It rejects local/internal paths and recognizable credential formats without printing values.
`--history` additionally scans every reachable historical blob and reports historical internal
paths; the existing history contains old planning documents. Neither mode rewrites history.
The guard supplements review rather than proving the absence of every possible secret.

The full demo deliberately enables the EKS public API for GitHub-hosted PR jobs, while the app
remains a private ClusterIP Service. Ordinary operator access may still use the SSM tunnel.
