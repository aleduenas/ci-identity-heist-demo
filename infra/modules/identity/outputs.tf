output "app_role_arn" {
  value = aws_iam_role.app.arn
}
output "saml_provider_arn" {
  value = try(aws_iam_saml_provider.keycloak[0].arn, null)
}
output "engineer_role_arn" {
  value = try(aws_iam_role.human["engineer"].arn, null)
}
output "support_role_arn" {
  value = try(aws_iam_role.human["support"].arn, null)
}
output "configuration" {
  description = "Prospective names and ARNs allow generating the IdP before enabling SAML."
  value = {
    account_id         = data.aws_caller_identity.current.account_id
    provider_name      = local.provider_name
    engineer_role_name = local.role_names.engineer
    support_role_name  = local.role_names.support
    saml_provider_arn  = "${local.iam_prefix}:saml-provider/${local.provider_name}"
    engineer_role_arn  = "${local.iam_prefix}:role/${local.role_names.engineer}"
    support_role_arn   = "${local.iam_prefix}:role/${local.role_names.support}"
    enabled            = local.federation_enabled
  }
}
