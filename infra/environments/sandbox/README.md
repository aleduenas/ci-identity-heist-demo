# Sandbox composition root

Initial provisioning includes the optional detection module's security automation
role. The root reads `security/control.json` for exercise trust, the same setting
used by the GitHub deployment. The old root `allow_pr_demo` input is compatibility
only. See [the security control](../../../security/README.md) for output-to-variable
wiring. Terraform is only for initial sandbox setup, never a live demo command.

Seven platform modules and an optional detection module connect the VPC, EKS, DynamoDB, audit trail, employee/workload identity, GitHub delivery, and optional SSM operations host. Defaults: us-east-1, `mybank-sandbox`, EKS 1.35, two t3.medium nodes and one t3.small operations host. The application has no public ingress. EKS API access defaults to private; the demo opts into a public, IAM/RBAC-authenticated control-plane endpoint so its GitHub-hosted PR runner can reach EKS.

Copy `backend.hcl.example` to ignored `backend.hcl`; copy `terraform.tfvars.example` to ignored `terraform.tfvars`. Replace account/bucket/admin role placeholders. Use IAM role ARNs, not temporary STS session ARNs. Initial federation remains disabled until live Keycloak metadata is exported. Keep the operations host or provide another VPC-connected operator/runner.

```bash
terraform -chdir=infra/environments/sandbox init -backend-config=backend.hcl
terraform -chdir=infra/environments/sandbox plan -out=sandbox.tfplan
terraform -chdir=infra/environments/sandbox apply sandbox.tfplan
terraform -chdir=infra/environments/sandbox output -json
```

Apply is intentionally manual. Output keys match delivery and identity scripts. `identity_configuration` exposes prospective role/provider ARNs before federation is enabled; individual human role outputs are null until the second apply. The disabled-by-default `detection*.tf` files add the isolated [detection exercise](../../modules/detection/README.md) identities. See [infrastructure operations](../../../docs/infrastructure.md) and [delivery](../../../docs/delivery.md) for cluster bootstrap, runner setup and teardown.
