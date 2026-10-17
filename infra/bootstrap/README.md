# State bootstrap

This root uses local state to create a versioned, SSE-S3 encrypted bucket with TLS enforcement and public-access blocking. S3 native lockfiles are enabled by the environment backend, so no lock table is needed.

```bash
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap plan -var='aws_account_id=ACCOUNT_ID' -var='state_bucket_name=mybank-tfstate-ACCOUNT_ID-ca-central-1' -out=bootstrap.tfplan
terraform -chdir=infra/bootstrap apply bootstrap.tfplan
```

Keep the bootstrap state securely outside Git (or migrate it to its own key in this bucket using a separately added S3 backend and `init -migrate-state`). The environment state must use a different key. The bucket has `prevent_destroy`; teardown requires a deliberate code change and removal of every object version and delete marker. Do not delete state before destroying the environment.

The operator needs bucket provisioning permissions, and later `s3:ListBucket`, GetObject/PutObject on the state key, and GetObject/PutObject/DeleteObject on its `.tflock` key. Use one AWS account/role per lab. Lockfiles prevent concurrent writers; versioning permits recovery but does not replace protected role access.

`aws_account_id` is required and enforced by the provider. Optional
`operator_principal_arn` creates `mybank-sandbox-bootstrap`, trusted only by the
specified same-account IAM user/role, with IAM permission to describe this lab
cluster. The environment root must explicitly grant that role EKS/Kubernetes
bootstrap access. It does not receive AWS AdministratorAccess. See the
[active handoff](../../docs/d2/HANDOFF.md) before continuing a live setup.

Optional `budget_alert_email` creates a plain USD20 monthly AWS budget that emails
that address when actual spend exceeds the limit. It is an alert only: AWS Budgets
data is delayed and nothing is shut down automatically.
