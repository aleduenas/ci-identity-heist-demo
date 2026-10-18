# Delivery and Kubernetes operations

The PR workflow runs only on GitHub-hosted Ubuntu workers. Main releases run the same checks, publish a commit-tagged image through a GitHub OIDC build role, then optionally deploy its content digest from a trusted VPC-connected runner. Infrastructure apply and initial Kubernetes bootstrap remain operator actions. No GitHub workflow provisions AWS resources.

## Components and prerequisites

| Component | Location | Owner |
| --- | --- | --- |
| Shared tests, image build and schema checks | `.github/workflows/checks.yml` | GitHub-hosted workers |
| Infrastructure formatting/validation, filtered to infrastructure edits | `.github/workflows/infrastructure.yml` | GitHub-hosted workers |
| Versioned IAM control deployment, main only | `.github/workflows/security-control.yml` | Scoped security automation role |
| PR checks | `.github/workflows/ci.yml` | GitHub-hosted workers |
| Main publish and digest deployment | `.github/workflows/release.yml` | Build role, then deployment role |
| Workload and security policies | `deploy/kubernetes/base/` | Bootstrap administrator |
| Typed output renderer | `scripts/deploy/render.py` | Operator |
| First apply and API-key Secret | `scripts/deploy/bootstrap.py` | Bootstrap administrator |
| Subsequent image update | `scripts/deploy/update_image.py` | Trusted release role |

The [security control](../security/README.md) is deployed separately by changing
`security/control.json` on main. Security-only commits skip the application release.
Terraform validation is outside reusable demo checks and runs only for infrastructure
edits or explicit dispatch. The five-step demo never runs Terraform.

Provision the AWS environment using the infrastructure runbook first. An EKS bootstrap administrator must be one of the explicit Terraform access-entry ARNs; the engineer, support, and release roles cannot bootstrap cluster resources. Required tools are Python 3.12, PyYAML (`python -m pip install -e '.[dev]'`), AWS CLI v2, Docker for the first image, and kubectl within one minor version of EKS. The default cluster and CI schema target are Kubernetes 1.35. Match the schema check if changing that version.

The standard operator/bootstrap path and private release runner use the private EKS API on TCP 443 and VPC DNS resolution. The demo additionally enables the public control-plane API for its GitHub-hosted PR runner; the application Service stays private. Follow the main deployment runbook for the local SSM tunnel. For scripts running through that tunnel, set `MYBANK_KUBE_API_SERVER=https://127.0.0.1:8443` and `MYBANK_KUBE_TLS_SERVER_NAME` to the Terraform `cluster_endpoint_hostname` output; both must be set together. TLS still verifies the actual EKS certificate. The VPC runner leaves these variables unset. A successful IAM login does not establish network connectivity. Verify the EKS Pod Identity and VPC CNI managed add-ons are healthy before creating the application.

## First image and bootstrap

From the repository root, export the composition root's outputs into the ignored generated directory:

```bash
terraform -chdir=infra/environments/sandbox output -json > deploy/generated/outputs.json
```

On Windows, use `terraform -chdir=infra/environments/sandbox output -json | Set-Content -Encoding utf8 deploy/generated/outputs.json`. The renderer accepts UTF-8 with or without a BOM. Outputs are configuration, not secret storage; they include operational ARNs and names and should still stay out of commits.

To use the first GitHub-built image, configure the first three repository variables below and merge a trusted commit to `main`. Leave `DEPLOY_ENABLED` absent or `false` until bootstrap completes; publish works without a runner. Alternatively, an authenticated administrator can use Docker and ECR directly:

```bash
REGION=$(terraform -chdir=infra/environments/sandbox output -raw aws_region)
REPOSITORY=$(terraform -chdir=infra/environments/sandbox output -raw ecr_repository_url)
REGISTRY=${REPOSITORY%%/*}
COMMIT=$(git rev-parse HEAD)
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build --tag "$REPOSITORY:$COMMIT" .
docker push "$REPOSITORY:$COMMIT"
DIGEST=$(aws ecr describe-images --region "$REGION" --repository-name "${REPOSITORY#*/}" --image-ids "imageTag=$COMMIT" --query 'imageDetails[0].imageDigest' --output text)
IMAGE="$REPOSITORY@$DIGEST"
docker logout "$REGISTRY"
```

For a GitHub-built image, resolve the digest with the same `describe-images` command and SHA from the successful release. The ECR repository enforces immutable tags; use a new commit for a new image. GitHub publication checks ECR first and reuses an existing SHA tag's digest on retries. Only an explicit `ImageNotFoundException` allows a new image build; authorization or service errors fail the release. A rollout can also be retried independently with the recorded digest and `update_image.py`.

Render and review before applying:

```bash
python scripts/deploy/render.py --outputs deploy/generated/outputs.json --image "$IMAGE"
```

The rendered manifest contains table names from the actual Terraform outputs, not assumed naming conventions. The renderer accepts only the configured private ECR repository, with a full 40-character Git commit tag or SHA-256 digest. Do not apply the raw base with unresolved placeholders. No API key appears in the rendered manifest.

With a VPC-connected bootstrap administrator session, create a new API key in the current process and bootstrap:

```bash
export APP_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
python scripts/deploy/bootstrap.py --outputs deploy/generated/outputs.json --image "$IMAGE"
```

The script makes a temporary kubeconfig, creates the namespace, passes the Secret directly to kubectl on stdin, then applies the other resources and waits for readiness. It never writes the key to a file or includes it in command arguments. Preserve the key using your local secret manager for API exercises, then unset it after use. Avoid shell tracing around the bootstrap command. To rotate it, rerun bootstrap with the new key and current image, then restart the Deployment as an administrator; environment-backed secrets are read when a pod starts.

The namespace enforces the Kubernetes restricted Pod Security profile. Pods run as UID/GID 10001 with no added capabilities, a read-only filesystem, resource limits and bounded writable `/tmp`. The application uses EKS Pod Identity for DynamoDB and has no Kubernetes API token. The agent injects its own projected AWS credential token independently of `automountServiceAccountToken: false`.

`/health` is a process liveness check; `/ready` verifies backing-store readiness. A readiness failure after AWS bootstrap commonly indicates missing tables, Pod Identity propagation, agent failure, or incorrect role permissions. Inspect pod events and application logs using administrator or engineer credentials. Avoid changing liveness to a database health check, which would restart healthy processes during a database outage.

## Trusted runner setup

Use the optional `operations_instance_id` private EC2 host prepared by Terraform, or a dedicated equivalent with VPC access. Its instance role allows SSM management only; it does not receive cluster-administrator or customer-data privileges. The deployment job receives short-lived credentials from GitHub OIDC. Register the runner manually with an ephemeral registration token obtained from this private repository's **Settings → Actions → Runners → New self-hosted runner** screen. Follow the generated, checksum-verified GitHub installation instructions inside an SSM session:

```bash
aws ssm start-session --target OPERATIONS_INSTANCE_ID --region us-east-1
```

Create a dedicated unprivileged Linux user and runner directory. Configure the repository URL `https://github.com/aleduenas/mybank-eks-sandbox` with the custom label `mybank-sandbox` in addition to the default `self-hosted`, `linux`, and `x64` labels. Install AWS CLI v2 and kubectl 1.35 before starting it. Python 3 and Git are also required; the deployment script uses only Python's standard library. Run the runner as that user through the runner's documented service installer. AWS registration tokens and downloaded runner configuration stay on the host, outside this repository and Terraform state.

Confirm from the host that the cluster hostname resolves to private addresses and TCP 443 is reachable. An SSM session relies on the host's outbound connectivity and the operator's SSM permissions, not an inbound SSH security-group rule. Administrator credentials used for bootstrap should never be installed in the runner user's home. Do not grant the host broad AWS permissions to fix an OIDC problem.

This is a trusted release runner: anyone able to change protected `main` workflow or application code can execute code on it and deploy code with the application's data privileges. Use the runner only for this lab repository. Configure branch protection or a ruleset requiring reviewed changes and checks, limit repository write access, and restrict runner groups where your account supports them. PR workflows use hosted workers; no `pull_request_target`, `workflow_run`, or PR artifact executes on the VPC runner. Rebuild or replace the runner between independent attack exercises to remove persistent changes.

## GitHub repository configuration

Set Actions repository variables, not AWS access-key secrets:

| Variable | Terraform output / value |
| --- | --- |
| `AWS_REGION` | `aws_region` |
| `AWS_BUILD_ROLE_ARN` | `build_role_arn` |
| `ECR_REPOSITORY_URL` | `ecr_repository_url` |
| `AWS_DEPLOY_ROLE_ARN` | `deploy_role_arn` |
| `EKS_CLUSTER_NAME` | `cluster_name` |
| `DEPLOY_ENABLED` | `true` only after bootstrap and runner registration |

Unset variables cause publish/deploy jobs to skip while checks still run, so a new repository does not queue an unavailable private runner. OIDC trust binds `aud` to `sts.amazonaws.com` and `sub` to `repo:aleduenas@54992507/mybank-eks-sandbox@1416500552:ref:refs/heads/main`. GitHub's repository API confirmed immutable subjects are enabled. New repositories use owner/repository IDs in the subject; a recreated or transferred repository requires a reviewed trust update. Manual dispatch must select `main` to publish or deploy. The jobs intentionally have no GitHub Environment attached: adding one changes the OIDC subject and requires reviewing the Terraform trust policy.

The hosted `verify-identity` job obtains an OIDC token for `sts.amazonaws.com`, checks its decoded subject against this repository's event IDs, and prints only nonsecret claims. It never prints the JWT or contacts AWS. This proves claim format, not AWS role acceptance. See [GitHub immutable subjects](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims).

Main releases serialize through the concurrency group and use the image digest emitted by that run's publish job. The deploy role can describe EKS to generate a kubeconfig and patch only `mybank-api` Deployment, with read/watch permissions needed for rollout. It cannot create namespace resources, read Secrets, execute in pods, or mutate Roles. Kubernetes cannot restrict a Deployment patch to only the `image` field; this role is deliberately a trusted release boundary and can indirectly exercise the application IAM role by replacing its code or specification.

Action versions use full commit SHAs (verified against upstream refs during implementation). Dependabot proposes reviewed pin updates. CI builds the Compose containers and exercises real DynamoDB Local transfers, retries, authorization and overdraft rejection before release. The kubeconform download verifies the pinned release checksum; schema validation is offline with respect to EKS but downloads public Kubernetes JSON schemas. It is not a substitute for a server-side validation on the provisioned cluster. Terraform validation initializes roots with `-backend=false`, so CI does not need state-bucket or AWS access.

## Application access and network-policy limits

The Service is ClusterIP; the lab creates no external application load balancer or ingress. A VPC-connected bootstrap administrator can forward it locally:

```bash
kubectl -n mybank port-forward service/mybank-api 8000:8000 --address 127.0.0.1
```

Use the normal administrator kubeconfig created by the deployment runbook or your tunnel. Delivery scripts use temporary kubeconfigs that disappear after completion. The engineer role has read/log permissions, so it cannot establish a port-forward. Port-forward traverses the API/kubelet path and bypasses ordinary pod ingress policies; Kubernetes RBAC controls it.

All ordinary ingress is denied. Egress permits DNS to CoreDNS, TCP 443, and the Pod Identity agent endpoint `169.254.170.23:80`. DynamoDB HTTPS is routed through the gateway endpoint, while application IAM grants only the lab tables. Native NetworkPolicy cannot express a DynamoDB hostname or AWS prefix list: TCP 443 remains broader than a database-only firewall. The VPC CNI add-on enables network-policy enforcement in standard mode, so new pods can briefly start before policy rules converge. These controls model workload isolation, not complete exfiltration prevention. Verify enforcement after bootstrap rather than assuming manifest presence proves it.

## Acceptance and recovery

Under a bootstrap administrator, check readiness and scope:

```bash
kubectl -n mybank get deployment,pods,service,networkpolicy
kubectl auth can-i get pods --namespace mybank --as=lab-engineer --as-group=mybank:engineers
kubectl auth can-i get secrets --namespace mybank --as=lab-engineer --as-group=mybank:engineers
kubectl auth can-i create pods/exec --namespace mybank --as=lab-engineer --as-group=mybank:engineers
kubectl auth can-i patch deployments/mybank-api --namespace mybank --as=lab-release --as-group=mybank:deployers
kubectl auth can-i create secrets --namespace mybank --as=lab-release --as-group=mybank:deployers
```

Expected responses are yes, no, no, yes, no. These are isolated RBAC checks using administrator impersonation; verify real federated and OIDC sessions separately to prove EKS access-entry mapping. Support has no cluster access entry. Confirm a normal pod cannot connect to the application Service; confirm the application can retrieve Pod Identity credentials and reach the DynamoDB tables. Use a temporary diagnostic namespace and administrator access for that probe, then remove it.

Test a successful transactional API call, an idempotent retry, and a rejected overdraft using the application's sample fixtures. Observe EKS audit logs and DynamoDB CloudTrail data events. A live AWS deployment, working SAML login and runtime policy enforcement remain manual acceptance tests; CI does not prove them.

If a release fails readiness, inspect its Deployment and logs, then roll back to a previously retained ECR digest with `update_image.py` using release-role credentials. That path uses the same narrow patch permissions; it does not require cluster administration. Keep known-good image digests before exercising ECR lifecycle cleanup. For teardown, disable `DEPLOY_ENABLED`, remove the runner registration and stop its service, delete the `mybank` namespace as an administrator, then follow the infrastructure teardown instructions. Removing the namespace does not delete DynamoDB or audit/state storage.

References: [GitHub AWS OIDC](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), [self-hosted runner installation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners), [EKS network policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [EKS Pod Identity agent](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-agent-setup.html), and [kubeconform validation limits](https://github.com/yannh/kubeconform#limits-of-kubeconform-validation).
