# Infrastructure operator guide

The sandbox is code, not a provisioned AWS environment. It uses a dedicated AWS account, private EKS API/nodes, synthetic DynamoDB records, SAML employee roles, GitHub OIDC delivery roles and an optional SSM operations host. Review [architecture](architecture.md), [bootstrap](../infra/bootstrap/README.md) and [sandbox](../infra/environments/sandbox/README.md) before provisioning.

## Module boundaries

| Module | Owns | Does not own |
| --- | --- | --- |
| network | VPC, two AZ subnets, routes, NAT, DynamoDB endpoint | Inbound app access |
| eks | Cluster, nodes, managed add-ons, bootstrap admins, control-plane logs | App manifests |
| data | Three encrypted/PITR tables | Real data or fixtures |
| audit | Trail data/management selectors and private S3 logs | Queries or account-wide immutable evidence |
| identity | Pod Identity, optional SAML provider/employee roles | Identity passwords/Keycloak runtime |
| delivery | ECR, GitHub OIDC and separate build/deploy roles | Runner registration |
| operations | Optional private SSM host and basic tooling | Operator/runner credentials |

## Provisioning sequence

1. Authenticate the AWS CLI to an isolated account. `aws sts get-caller-identity` confirms the account. Create/select an existing IAM administrator role and supply that role ARN in `bootstrap_admin_role_arns`; the Terraform caller is not implicitly made a cluster administrator.
2. Review/apply the independent bootstrap state bucket. Protect its local state and back it up securely. Copy the backend and tfvars examples and replace placeholders. No credentials belong in those files.
3. Before apply, run `aws eks describe-cluster-versions --region us-east-1` and review EKS support dates. The composition defaults to 1.35; compatible managed add-ons resolve through AWS at plan time and can be explicitly pinned. STANDARD support is configured.
4. Initialize the environment S3 backend with native lockfiles, review a saved plan, and apply it manually. The provider's account allowlist rejects credentials for a different account. Provisioning requires network/EKS/EC2/IAM/DynamoDB/S3/CloudTrail/CloudWatch permissions and `iam:PassRole`; the release roles are deliberately insufficient for provisioning.
5. Check the operations host SSM managed-instance status and cloud-init completion. Install remaining CLI/runner tooling from the delivery instructions. Use the documented VPC access route to bootstrap Kubernetes as the supplied administrator role. No public Kubernetes endpoint is needed.
6. Apply initial namespace/service-account/RBAC/config/Secret/Deployment manifests. The workload association already names `mybank/mybank-api`. Configure GitHub variables and register the trusted private runner. Do not run untrusted PR jobs there.
7. Export `identity_configuration`, generate the Keycloak realm, and export its live signing metadata. Set `saml_metadata_path` to that file and review/apply a second plan. Only then do engineer/support roles exist and role claims become usable.

The repository's GitHub API settings were verified to use immutable subjects with prefix `repo:aleduenas@54992507/mybank-eks-sandbox@1416500552`. By default both release roles trust exactly that prefix plus `:ref:refs/heads/main` and audience `sts.amazonaws.com`; `github_oidc_subject` exports the complete claim. The optional coordinated run-context mode (`github_oidc_include_run_context`, the repository OIDC template and `MYBANK_OIDC_RUN_CONTEXT`) keeps the roles main-only but matches signed event/run/attempt suffixes; `github_oidc_subjects` then lists the accepted patterns. See the [delivery module](../infra/modules/delivery/README.md) and [D2 runbook](d2/README.md). The required delivery-module prefix rejects wildcards and mismatched repository names. Compare it against the release workflow's nonsecret claims check before AWS apply and reverify after repository rename/transfer or OIDC-settings changes. GitHub documents the [immutable subject format](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims); name-only subjects do not match this repository.

## Permissions and verification

Bootstrap administrators have EKS cluster administration. Engineers describe EKS and join `mybank:engineers` for namespace read access. Support reads only the synthetic DynamoDB tables. The application has read access (get/query/scan) to its customer, account and transfer tables and makes only transaction-scoped account updates and transfer inserts — no customer writes or deletion. That table read access is what the D2 exercise shows an attacker inheriting when they replace the app. The node and operations roles cannot read application tables. Release deployers can change workload code and therefore are trusted to exercise application permissions indirectly.

After deployment verify positive and negative access cases with each real session. Support GetItem should succeed and PutItem should fail; engineer DescribeCluster/workload logs should succeed and DynamoDB GetItem should fail; deploy image rollout should succeed while secrets listing and unrelated namespaces fail. Inspect the Pod Identity role in CloudTrail, generate a transaction, and verify table data events arrive in the audit bucket. These are operator acceptance checks: local Terraform validation cannot prove live IAM, SAML, routing or audit delivery.

VPC CNI network policy is enabled in standard mode for reliable system-pod startup. There is a brief policy reconciliation gap for newly starting pods. Strict startup mode requires kube-system policies and explicit live testing. There is no public app ingress; access comes through a VPC-connected `kubectl port-forward` session.

## Cost and availability

This is a billable AWS lab. Continuous costs include EKS control plane, two worker instances, optional operations instance, EBS, NAT gateway and public IPv4 allocation. Usage costs include NAT processing/cross-AZ traffic, CloudWatch logs, CloudTrail data events, DynamoDB operations/PITR, S3 and ECR storage. Single NAT and small nodes are intentional lab compromises. Stopping nodes or the operations host does not stop EKS/NAT charges. Use the [AWS Pricing Calculator](https://calculator.aws/) with us-east-1 settings and set an account budget before apply; this repository makes no fixed-cost promise.

## Teardown and evidence

Stop GitHub deployment and remove the runner registration. Archive relevant audit logs and synthetic-data evidence. Delete app Kubernetes resources while the cluster is still reachable. Review an environment destroy plan; ECR images and the versioned audit bucket intentionally block deletion until explicitly emptied. Confirm exact repository/bucket/account identifiers before deleting images, object versions and delete markers, then run the reviewed destroy operation. EKS, NAT, EC2 and elastic IPs must all be gone to stop their ongoing charges.

Keep environment state until AWS deletion is confirmed. State storage is a separate lifecycle: bootstrap `prevent_destroy` must be deliberately removed, all state bucket versions deleted, and only then should its root be destroyed. Audit logs and state are not automatically purged by this project.

## Validation and references

```bash
terraform fmt -check -recursive infra
terraform -chdir=infra/bootstrap init -backend=false
terraform -chdir=infra/bootstrap validate
terraform -chdir=infra/environments/sandbox init -backend=false
terraform -chdir=infra/environments/sandbox validate
```

These commands install providers and validate schema; they do not apply AWS resources. Run a live plan only with the intended account and configuration.

Sources: [S3 native state locking](https://developer.hashicorp.com/terraform/language/backend/s3), [EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html), [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-association.html), [DynamoDB IAM transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis-iam.html), [CloudTrail bucket policy](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html), and [GitHub OIDC](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).
