output "aws_region" {
  value = var.aws_region
}
output "cluster_name" {
  value = module.eks.cluster_name
}
output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}
output "cluster_endpoint_hostname" {
  value = trimprefix(module.eks.cluster_endpoint, "https://")
}
output "vpc_id" {
  value = module.network.vpc_id
}
output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}
output "operations_instance_id" {
  value = try(module.operations[0].instance_id, null)
}
output "runner_parameter_name" {
  value = try(module.operations[0].runner_parameter_name, null)
}
output "customers_table_name" {
  value = module.data.table_names["customers"]
}
output "accounts_table_name" {
  value = module.data.table_names["accounts"]
}
output "transfers_table_name" {
  value = module.data.table_names["transfers"]
}
output "ecr_repository_url" {
  value = module.delivery.ecr_repository_url
}
output "build_role_arn" {
  value = module.delivery.build_role_arn
}
output "deploy_role_arn" {
  value = module.delivery.deploy_role_arn
}
output "app_role_arn" {
  value = module.identity.app_role_arn
}
output "saml_provider_arn" {
  value = module.identity.saml_provider_arn
}
output "engineer_role_arn" {
  value = module.identity.engineer_role_arn
}
output "support_role_arn" {
  value = module.identity.support_role_arn
}
output "identity_configuration" {
  value = module.identity.configuration
}
output "audit_bucket_name" {
  value = module.audit.audit_bucket_name
}
output "cloudtrail_arn" {
  value = module.audit.trail_arn
}
output "github_oidc_subject" {
  value = module.delivery.github_oidc_subject
}
output "github_oidc_subjects" {
  value = module.delivery.github_oidc_subjects
}
