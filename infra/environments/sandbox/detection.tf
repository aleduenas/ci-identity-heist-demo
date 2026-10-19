locals {
  # Shared with GitHub Actions: later Terraform applies preserve the committed setting.
  detection_control = jsondecode(file("${path.module}/../../../security/control.json"))
}

module "detection" {
  count          = var.enable_detection ? 1 : 0
  source         = "../../modules/detection"
  name           = var.name
  aws_account_id = var.aws_account_id
  cluster_name   = module.eks.cluster_name
  cluster_arn    = module.eks.cluster_arn
  github_oidc_provider_arn = coalesce(
    var.existing_github_oidc_provider_arn,
    "arn:aws:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
  )
  detection_sub_pattern       = var.detection_sub_pattern
  allow_pr_demo               = !local.detection_control.enforcement_enabled
  mock_operator_principal_arn = var.mock_operator_principal_arn
  depends_on                  = [module.delivery]
}
