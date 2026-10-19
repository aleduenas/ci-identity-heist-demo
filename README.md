# Mybank EKS Sandbox

A private, modular AWS lab that models a fictional bank's delivery and employee-access workflow: GitHub → CI/CD → EKS, SAML employee federation, and limited elevated customer-data access. All records and money movements are synthetic.

The [architecture](docs/architecture.md) describes the system and trust boundaries. The lab centers on an IAM trust-boundary control: an isolated deployment role that an unreviewed pull request can assume while enforcement is off, and that only trusted `main` contexts can assume once it is enabled. See the [security control](security/README.md).

## What is included

- AWS networking, EKS, data storage, audit logging, employee identity, delivery roles and a private SSM operations host.
- Private worker nodes, ECR and DynamoDB tables. The lab enables the IAM/RBAC-authenticated public EKS API so GitHub-hosted PR jobs can reach it; the application remains ClusterIP-only.
- A layered FastAPI transfer API with atomic balance updates and durable idempotency.
- A local Keycloak SAML IdP with separate engineer and support identities; temporary AWS credentials.
- GitHub Actions checks, immutable image publishing, OIDC AWS roles and trusted private-runner deployment.
- A [versioned IAM control](security/README.md), enabled through `security/control.json` and deployed to IAM by a scoped GitHub OIDC role.
- Namespace RBAC, Pod Identity, workload restrictions, structured request logs, EKS audit logs and CloudTrail table events.
- Local Docker Compose, synthetic fixtures, tests, bootstrap scripts and teardown procedures.

## Repository boundaries

```text
app/                     API, business rules, persistence, fixtures, request logging
infra/                   Environment setup and component definitions
deploy/kubernetes/       Workload, namespace, RBAC and network manifests
identity/                Keycloak configuration, claim generation, metadata, STS
scripts/access/          Private API tunnel
scripts/data/            Account-checked AWS synthetic seeding
scripts/deploy/          Manifest rendering, bootstrap, publication, rollout
scripts/checks/          API/SAML smoke checks and publication hygiene
scripts/demo/            Exercise lifecycle coordination and independent watcher
scripts/detection/       PR probe, detector, collector and IAM trust control
security/                Versioned enforcement setting and control explanation
tests/                   Application, identity, detection and security-control checks
.github/                 CI/CD and reviewed dependency updates
docs/                    Architecture, runbooks and operational guides
```

Identity passwords and runner registration tokens remain outside version control. Administrative bootstrap and routine releases use different privileges. Component READMEs describe their contracts; configuration examples contain no real credentials.

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

## Environment

The AWS environment and control code are provisioned ahead of time. The setting in `security/control.json` enables the prepared example through its workflow. In production, the restrictive policy would be delivered through reviewed workflow YAML or another security-as-code process; see [production delivery](security/README.md#production-delivery).

The lab uses synthetic data in an owned AWS account. With enforcement off, an unreviewed PR can obtain the isolated deployment role; enabling enforcement restricts that role to trusted `main` contexts, so the same PR request is denied while legitimate behavior is preserved. Setup, maintenance and cost procedures are in the operator runbooks under `docs/`.

## Documentation

| Read | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | System diagram, trust boundaries and shared contracts |
| [Control](security/README.md) | IAM trust control, enforcement behavior and production delivery |
| [Application](docs/application.md) | Routes, transactional invariants and fixtures |
| [Observability](docs/observability.md) | Evidence sources and their limits |

The exercise deliberately allows PR-context assumption of an isolated deployment role while enforcement is off. Its payload reads synthetic records through replacement workload code and attempts to restore the application. Enabling the control blocks new PR credential issuance; baseline release roles remain main-only.
