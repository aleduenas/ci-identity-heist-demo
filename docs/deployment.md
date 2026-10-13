# Ordered deployment sequence

## 1. Select the account and state storage

Authenticate AWS CLI v2 to your sandbox. Obtain the account ID with `aws sts get-caller-identity`. Select an existing IAM role ARN for bootstrap administration; an `arn:aws:sts::...:assumed-role/...` session ARN is not a role ARN.

Follow [state bootstrap](../infra/bootstrap/README.md), then copy the sandbox's [backend example](../infra/environments/sandbox/backend.hcl.example) and [variable example](../infra/environments/sandbox/terraform.tfvars.example) to `backend.hcl` and `terraform.tfvars` in that same directory. Replace account, bucket and role placeholders. Both local operator files are ignored.

Review [infrastructure permissions and costs](infrastructure.md). Initialize, review a saved plan and apply the sandbox root. Keep `saml_metadata_path` unset on the first apply. Do not reuse the CI build/deploy roles for provisioning.

Save actual outputs from the repository root:

```bash
mkdir -p .cache
terraform -chdir=infra/environments/sandbox output -json > .cache/outputs.json
```

PowerShell: `New-Item -ItemType Directory -Force .cache` then `terraform -chdir=infra/environments/sandbox output -json | Set-Content -Encoding utf8 .cache/outputs.json`.

## 2. Reach EKS and bootstrap the application

Wait for EKS add-ons/nodes and the SSM host to become healthy. Install the Session Manager plugin and a kubectl version compatible with the cluster. Follow [private API access](private-access.md) from the workstation, keeping administrator credentials on the workstation. Alternatively, operate from a trusted VPC-connected machine.

Follow [first image and Kubernetes bootstrap](delivery.md). Publish a commit image into ECR, resolve its digest, render the manifests with `--outputs .cache/outputs.json`, review them, set a fresh `APP_API_KEY`, then run the bootstrap helper. This installs the namespace, workload, Service, Secret and permission boundaries. The app should become ready without fixture records because its tables already exist.

## 3. Seed and exercise synthetic transactions

Using an operator with DynamoDB fixture write permissions:

```bash
python scripts/data/seed_aws.py --outputs .cache/outputs.json
```

This helper checks the active AWS account against the outputs and inserts only absent fixture records. It never creates AWS tables or resets an existing balance. The runtime app role intentionally cannot seed customers/accounts.

As a Kubernetes administrator, port-forward `service/mybank-api` to local port 8000. Preserve the bootstrap API key in your local secret manager and set it in the testing terminal. Run `python scripts/checks/local_api.py` to exercise successful transfer, matching retry, conflicting retry and rejected overdraft. A successful smoke test writes one 500-cent synthetic transfer.

## 4. Enable daily delivery

Register the trusted runner on the optional operations host and configure the repository variables described in [delivery](delivery.md). Enable deployment only after first bootstrap succeeds. Merge a trusted commit; hosted checks run, the build role publishes its SHA image, and the VPC runner assumes its deploy role and rolls out the digest. Manual retries reuse an existing immutable commit image.

Retain the last known-good digest. Roll back through `scripts/deploy/update_image.py` using that digest if a new release fails. A runner that has been used in an exercise should be replaced or rebuilt before reuse.

## 5. Enable SAML employee access

Follow [the identity runbook](identity.md): set local-only passwords, generate the realm using actual outputs, start Keycloak, export its real metadata, then set `saml_metadata_path` and review/apply the federation plan. Run the browser sign-in checks and acquire separate temporary CLI profiles when needed.

Verify real engineer and support sessions against both allowed and denied operations. Administrator impersonation checks alone do not prove federation. Never grant these employees the bootstrap administrator role to work around a configuration problem.

## 6. Record acceptance and teardown

Record results using [the testing matrix](testing.md) and [observability guide](observability.md). Update the [handoff ledger](implementation-status.md) with account/region, image digest, exercise timestamp and outstanding issues, excluding credentials/assertions/customer fields.

Use [the teardown sequence](teardown.md) after the exercise. Retained state/audit storage has a separate lifecycle from compute.
