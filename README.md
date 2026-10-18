# Mybank EKS Sandbox

**Running the detection demo? Start with [DEMO.md](DEMO.md).**

A private, modular AWS lab that models a fictional bank's delivery and employee-access workflow: GitHub → CI/CD → EKS, SAML employee federation, and limited elevated customer-data access. All records and money movements are synthetic.

[DEMO.md](DEMO.md) defines the presentation flow and repository scope. The supporting architecture and runbooks describe the lab; [verification status](docs/implementation-status.md) separates observed results from untested steps.

## What is included

- Seven platform Terraform modules plus an optional detection module: networking, EKS, data, audit, identity, delivery IAM and a private SSM operations host.
- Private worker nodes, ECR and DynamoDB tables. The demo enables the IAM/RBAC-authenticated public EKS API so GitHub-hosted PR jobs can reach it; the application remains ClusterIP-only.
- A layered FastAPI transfer API with atomic balance updates and durable idempotency.
- A local Keycloak SAML IdP with separate engineer and support identities; temporary AWS credentials.
- GitHub Actions checks, immutable image publishing, OIDC AWS roles and trusted private-runner deployment.
- A [versioned security switch](security/README.md), deployed directly to IAM by a scoped GitHub OIDC role; no Terraform or local AWS session during the demo.
- Namespace RBAC, Pod Identity, workload restrictions, structured request logs, EKS audit logs and CloudTrail table events.
- Local Docker Compose, synthetic fixtures, tests, bootstrap scripts and teardown procedures.

## Repository boundaries

```text
app/                     API, business rules, persistence, fixtures, request logging
infra/bootstrap/         Independent Terraform state-storage lifecycle
infra/environments/      Environment composition and operator configuration
infra/modules/           Seven independently documented AWS components
deploy/kubernetes/       Workload, namespace, RBAC and network manifests
identity/                Keycloak configuration, claim generation, metadata, STS
scripts/access/          Private API tunnel
scripts/data/            Account-checked AWS synthetic seeding
scripts/deploy/          Manifest rendering, bootstrap, publication, rollout
scripts/checks/          API/SAML smoke checks and publication hygiene
scripts/demo/            Demo lifecycle and independent watcher
scripts/detection/       PR probe, detector, collector and IAM trust control
tests/                   Application and identity tests
.github/                 CI/CD and reviewed dependency updates
docs/                    Architecture, runbooks, evidence and handoff
```

Application code does not provision infrastructure. Terraform does not store identity passwords or runner registration tokens. Kubernetes bootstrap and routine releases use different privileges. Component READMEs describe their contracts; configuration examples contain no real credentials.

## Run the local transactional slice

Requires Docker with Linux containers and Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
export APP_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
docker compose up --build --wait
python scripts/checks/local_api.py
```

PowerShell activation is `.venv\Scripts\Activate.ps1`; set the key with `$env:APP_API_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"`. API: `http://localhost:8000`; DynamoDB Local: `http://localhost:8001`. Both bind to loopback. `/health` and `/ready` are public probes; business routes require `X-API-Key`. OpenAPI docs are at `/docs`.

The local database is in memory. Restarting it clears the fixtures; `docker compose up` reseeds them. Stop the local slice with `docker compose down`. The smoke check creates a synthetic transfer and verifies retry/rejection behaviour. It can also exercise the AWS service after an authorized administrator port-forward.

## Provision AWS and employee access

Start with [the deployment sequence](docs/deployment.md). It links the individual state bootstrap, Terraform, private-access, Kubernetes, runner, SAML and seeding procedures. Region defaults to `us-east-1`. Use a dedicated sandbox account, review the plan, and provision with an authenticated operator role.

The demo sandbox has been applied. Its public EKS API, private release runner and healthy application were checked on 2026-10-18; see [verification status](docs/implementation-status.md). It incurs AWS charges while running; [cost and teardown guidance](docs/infrastructure.md) identifies persistent resources. A new installation must configure the repository variables and runner before enabling releases.

## Documentation and verification

| Read | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | System diagram, trust boundaries and shared contracts |
| [Deployment](docs/deployment.md) | Ordered path from empty AWS account to acceptance |
| [Infrastructure](docs/infrastructure.md) | Modules, permissions, costs and validation |
| [Private access](docs/private-access.md) | SSM tunnel with EKS TLS verification |
| [Application](docs/application.md) | Routes, transactional invariants and fixtures |
| [Delivery](docs/delivery.md) | Initial bootstrap, runner, daily releases and rollback |
| [Identity](docs/identity.md) | Local Keycloak, SAML claims and employee checks |
| [Observability](docs/observability.md) | Evidence sources and their limits |
| [Testing](docs/testing.md) | Repeatable checks and what they prove |
| [Teardown](docs/teardown.md) | Stop the lab and handle retained storage |
| [Implementation status](docs/implementation-status.md) | Verified results and continuation checklist |

The detection exercise deliberately allows PR-context assumption of an isolated deployment role during the attack phase. Its commented payload reads synthetic records through a replacement workload, then restores the application. Follow [DEMO.md](DEMO.md) to demonstrate detection and then block PR trust; baseline release roles remain main-only.
