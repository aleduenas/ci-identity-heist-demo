# Infrastructure

Terraform is initial provisioning tooling, never a live control dependency.
The optional detection module also provisions a narrow GitHub security role; the
[live control](../security/README.md) deploys through IAM from GitHub after setup.

Terraform is split into an independent state-storage bootstrap, a sandbox composition root, and reusable network, EKS, data, audit, identity, delivery and optional operations-host modules. Each module owns one AWS concern; Kubernetes resources remain in `deploy/`.

Start with [the operator guide](../docs/infrastructure.md), then [bootstrap](bootstrap/README.md) and [sandbox](environments/sandbox/README.md). All examples require an authenticated dedicated AWS lab account. The raw Terraform workflow requires operator plan review. `python -m scripts.demo.up` coordinates an explicit plan/apply and the remaining lab setup; it prompts unless `--yes` is supplied.

Use Terraform >= 1.10 and AWS provider 6.x. Commit generated `.terraform.lock.hcl` files, never state, plan files, credentials, SAML metadata, or secret tfvars. Backend credentials come from the normal AWS credential chain.
