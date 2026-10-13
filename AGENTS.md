# Repository collaboration guide

This repository is the Mybank EKS sandbox described in `docs/architecture.md`. It is a synthetic transactional AWS security lab. The older Canadian service-demand MLOps brief is not this repository's implementation scope.

Before changing code, read the architecture and `docs/implementation-status.md`. Keep the handoff ledger accurate: distinguish local/static checks from real AWS plan/apply, federation and deployment. Never claim infrastructure exists solely because Terraform validates.

Keep components modular: `infra/modules` owns AWS resources, `app` owns business/persistence/API layers, `deploy` owns Kubernetes policy, `identity` owns local employee federation, and `scripts` holds focused operator commands. Prefer files under 150 lines and split responsibilities when a file grows; documentation and generated provider locks may be longer where that improves readability.

When parallel implementation is requested, allocate disjoint component paths and agree shared Terraform outputs, environment variables and service names before edits. Preserve this ownership contract in any continuation. Do not make overlapping agent edits.

Use synthetic fixtures only. Do not commit `.env`, generated realm/password files, assertions, temporary AWS credentials, Terraform state/plans or operator backend files. Keep EKS and application access private. Do not add public ingress or broaden employee/data permissions as a shortcut to debugging.

Checks: `ruff check app tests identity scripts`, `pytest tests`, delivery unittest discovery, Terraform fmt and backend-free root validation. Container and live acceptance checks are in `docs/testing.md`. Update relevant component READMEs when contracts change. No AWS apply is part of routine validation; deployment is an explicit operator step.
