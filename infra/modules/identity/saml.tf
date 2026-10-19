data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  federation_enabled = var.saml_metadata_path != null
  role_names         = { engineer = "${var.name}-engineer", support = "${var.name}-support" }
  provider_name      = "${var.name}-keycloak"
  iam_prefix         = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}"
}

resource "aws_iam_saml_provider" "keycloak" {
  count                  = local.federation_enabled ? 1 : 0
  name                   = local.provider_name
  saml_metadata_document = var.saml_metadata_path == null ? "" : file(var.saml_metadata_path)
}

resource "aws_iam_role" "human" {
  for_each             = local.federation_enabled ? local.role_names : {}
  name                 = each.value
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Action = "sts:AssumeRoleWithSAML"
      Principal = { Federated = aws_iam_saml_provider.keycloak[0].arn }
      Condition = { StringEquals = { "SAML:aud" = "https://signin.aws.amazon.com/saml" } }
    }]
  })
}
