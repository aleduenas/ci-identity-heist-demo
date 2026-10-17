# Sandbox composition root

Seven focused modules connect the VPC, EKS, DynamoDB, audit trail, employee/workload identity, GitHub delivery, and optional SSM operations host. Defaults: ca-central-1, `mybank-sandbox`, EKS 1.35, two t3.medium nodes and one t3.small operations host. No public app/API endpoint exists.

Copy `backend.hcl.example` to ignored `backend.hcl`; copy `terraform.tfvars.example` to ignored `terraform.tfvars`. Replace account/bucket/admin role placeholders. Use IAM role ARNs, not temporary STS session ARNs. Initial federation remains disabled until live Keycloak metadata is exported. Keep the operations host or provide another VPC-connected operator/runner.

```bash
terraform -chdir=infra/environments/sandbox init -backend-config=backend.hcl
terraform -chdir=infra/environments/sandbox plan -out=sandbox.tfplan
terraform -chdir=infra/environments/sandbox apply sandbox.tfplan
terraform -chdir=infra/environments/sandbox output -json
```

Apply is intentionally manual. Output keys match delivery and identity scripts. `identity_configuration` exposes prospective role/provider ARNs before federation is enabled; individual human role outputs are null until the second apply. The disabled-by-default `d2*.tf` files add the isolated [D2 exercise](../../modules/d2/README.md) identities. See [infrastructure operations](../../../docs/infrastructure.md) and [delivery](../../../docs/delivery.md) for cluster bootstrap, runner setup and teardown.
