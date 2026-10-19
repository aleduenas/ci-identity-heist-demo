# Teardown the lab

## Local containers

Stop the application with `docker compose down`. DynamoDB Local is in memory, so its records disappear when the container stops. Stop the local IdP with `docker compose -f identity/keycloak/compose.yml down`.

To deliberately erase the disposable IdP's realm and signing key, use the same identity Compose command with `down --volumes`. That invalidates the existing IAM metadata trust for future assertions: regenerate/import the realm, export metadata and apply the new provider document before using it again. Remove ignored assertion and temporary-credential files after they are no longer needed.

## AWS compute and workload

1. Set `DEPLOY_ENABLED=false` in GitHub. Stop and unregister the private runner, and ensure no release is running.
2. Archive the evidence you need from EKS logs, the CloudTrail audit bucket and the synthetic ledger. Check the account and output identifiers before any deletion.
3. While EKS is reachable, use a bootstrap administrator to delete the `mybank` namespace. It has no persistent Kubernetes volumes or load balancers; its synthetic data lives in DynamoDB.
4. Review `terraform -chdir=infra/environments/sandbox plan -destroy`. ECR and the audit bucket intentionally resist deletion while they contain images or object versions. Use the AWS console or narrowly scoped AWS CLI operations to remove only this lab's ECR images and, if intentionally discarding the archive, every audit-bucket version/delete marker. Do not use a broad account cleanup script.
5. Apply the reviewed environment destroy plan. Check Terraform state and AWS for remaining EKS control plane, managed node group, operations instance, EBS, NAT gateway and elastic IP resources. Partial destroy can leave billable resources; resume the same state after resolving failures.

## State storage

Keep the state until all environment resources are confirmed deleted. Preserve a private backup if desired. The separate bootstrap state bucket has `prevent_destroy`; intentionally remove that guard only when retiring the lab's state lifecycle. Remove its object versions/delete markers and destroy the bootstrap root using its own state. Never delete state first and then rely on memory to find resources.

The state/audit buckets use `force_destroy=false` so destruction cannot silently purge evidence. Compute shutdown alone does not stop EKS, NAT, storage or retained-log charges. See [infrastructure costs](infrastructure.md).
