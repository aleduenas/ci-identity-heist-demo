# SAML employee access runbook

## What SAML does in this lab

Keycloak signs a statement that a lab employee has authenticated and lists the AWS role that employee may assume. IAM verifies the statement against the provider's public signing certificate, then issues temporary credentials. Engineers receive namespace observation access; selected support employees receive direct read access to synthetic customer data. Customer API authentication is the separate lab API key.

Two fictional employees are generated: `lab-engineer` belongs to `engineers`; `lab-support` belongs to `supports`. Group attributes carry exactly one role/provider ARN pair. The SAML user-attribute mapper aggregates group attributes into the case-sensitive AWS Role claim. No user receives both roles by default. Membership and realm administration are privileged operations: the Keycloak administrator can change role claims.

This is direct IAM SAML federation, a smaller substitute for an enterprise SAML IdP plus IAM Identity Center. It does not install an AWS organization, SCIM provisioning or customer SSO. The localhost HTTP development service is appropriate only for the isolated lab. Its volume preserves the signing key; removing it requires exporting new metadata and updating IAM.

## Start federation after foundational AWS apply

1. Follow [infrastructure provisioning](infrastructure.md) with SAML disabled. Save `terraform output -json` to `.cache/outputs.json`. PowerShell operators should use UTF-8 output; the generator also accepts a UTF-8 BOM.
2. Set three different strong, lab-only environment values: `KEYCLOAK_ADMIN_PASSWORD`, `LAB_ENGINEER_PASSWORD`, `LAB_SUPPORT_PASSWORD`. Do not put them in shell command examples or tracked files. Each employee password must contain at least 16 characters.
3. Generate the account-specific import and start Keycloak:

```bash
python -m identity.generate_realm --outputs .cache/outputs.json
docker compose -f identity/keycloak/compose.yml up -d
python -m identity.export_metadata
```

The metadata command may need rerunning after Keycloak finishes starting. Open `http://localhost:8081/admin/` to inspect the Mybank realm using `lab-admin`. Generated imports contain employee passwords; the bootstrap admin password is passed separately through the environment.

4. Set Terraform's `saml_metadata_path` variable to the absolute path of `identity/generated/metadata.xml`, then review/apply a new plan. A non-null metadata path enables federation; null disables it. Metadata is public certificate material; state and generated realm files still remain private.
5. Open `http://localhost:8081/realms/mybank/protocol/saml/clients/aws` in a browser. Sign in as `lab-engineer` or `lab-support`. Keycloak submits a signed assertion to the AWS SAML sign-in endpoint. This should open the AWS console with that employee role, not the provisioning administrator.

Keycloak imports a realm only if it does not already exist. Editing generated JSON and restarting does not update an existing realm. Make changes in the admin console, or deliberately recreate the disposable Keycloak volume and re-export metadata. See [teardown](teardown.md).

## Temporary CLI credentials for kubectl and data checks

Browser console sign-in does not populate AWS CLI credentials. During your own lab sign-in, use browser developer tools with Preserve log enabled to inspect the POST to `https://signin.aws.amazon.com/saml`. Save the decoded form field `SAMLResponse` (the base64 value, not URL-escaped form data and not XML) to `identity/generated/assertion.txt`. Treat it as a temporary login secret. Capture a fresh assertion for each role and exchange it promptly:

```bash
python -m identity.assume_role --outputs .cache/outputs.json \
  --role engineer --assertion identity/generated/assertion.txt
export AWS_SHARED_CREDENTIALS_FILE="$PWD/identity/generated/credentials"
export AWS_PROFILE=mybank-engineer
aws sts get-caller-identity
```

In PowerShell, set `$env:AWS_SHARED_CREDENTIALS_FILE = (Resolve-Path identity/generated/credentials).Path` and `$env:AWS_PROFILE = 'mybank-engineer'`. The exchange helper writes credentials without printing them. Assertions are subject to IAM expiry, signature, audience and role checks. Delete assertion files after exchange; profiles expire after one hour.

From a machine with VPC access, use `aws eks update-kubeconfig --name <cluster-name> --region ca-central-1 --profile mybank-engineer`. Do not add `--role-arn` for the same role: that would request a second AssumeRole action rather than use the SAML session.

## Verify the role boundary

| Role | Expected success | Expected denial |
| --- | --- | --- |
| Engineer | Describe EKS; list Mybank pods; read app logs | Read Kubernetes Secrets; exec into pods; direct DynamoDB customer reads |
| Support | Get/scan synthetic customer, account and transfer tables | Update/delete records; administer EKS |
| Deployer | Patch app Deployment; observe rollout | Read Kubernetes Secrets; direct data reads through IAM |

For Kubernetes, run `kubectl auth can-i get pods -n mybank`, `kubectl auth can-i get secrets -n mybank`, and `kubectl auth can-i create pods/exec -n mybank` using the engineer session. For support, use its own SAML profile to `aws dynamodb get-item` on a seeded customer key and attempt an update only against a disposable synthetic fixture; the write should be denied. Use IAM policy simulation first if avoiding mutation attempts. Record session ARN, UTC timestamp and expected outcome, excluding credentials and customer fields.

A trusted deployer can replace application code, which can then use the application role. This is an intentional operational trust boundary, not an isolated data-access persona. Do not add support staff to engineering/deployment groups to simplify exercises.

## Sources

- [AWS SAML assertion requirements](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_saml_assertions.html)
- [Keycloak SAML protocol mappers](https://www.keycloak.org/admin-api/protocol-mappers)
- [Keycloak container realm import](https://www.keycloak.org/server/containers)
