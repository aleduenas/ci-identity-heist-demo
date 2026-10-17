# Mybank EKS Sandbox

**Running the D2 demo? Start with [DEMO.md](DEMO.md).**

A private, modular AWS lab that models a fictional bank's delivery and employee-access workflow: GitHub → CI/CD → EKS, SAML employee federation, and limited elevated customer-data access. All records and money movements are synthetic.

The architecture was written and committed before three component agents implemented infrastructure, the application and delivery. Current verification and remaining operator steps are recorded in [the handoff ledger](docs/implementation-status.md).

## What is included

- Seven Terraform modules: networking, EKS, data, audit, identity, delivery IAM and a private SSM operations host.
- A private-endpoint EKS cluster, private worker nodes, ECR and DynamoDB tables.
- A layered FastAPI transfer API with atomic balance updates and durable idempotency.
- A local Keycloak SAML IdP with separate engineer and support identities; temporary AWS credentials.
- GitHub Actions checks, immutable image publishing, OIDC AWS roles and trusted private-runner deployment.
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
scripts/checks/          Local API and SAML smoke checks
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

AWS resources have **not** been applied. The code incurs AWS charges when applied; the [cost and teardown guidance](docs/infrastructure.md) identifies persistent resources. GitHub release jobs remain disabled until repository variables and the runner are configured.

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

The environment is prepared for normal operations and authorized exercises. It contains no attack tooling or deliberately introduced vulnerabilities.
