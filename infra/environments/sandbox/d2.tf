module "d2" {
  count          = var.enable_d2 ? 1 : 0
  source         = "../../modules/d2"
  name           = var.name
  aws_account_id = var.aws_account_id
  cluster_name   = module.eks.cluster_name
  cluster_arn    = module.eks.cluster_arn
  github_oidc_provider_arn = coalesce(
    var.existing_github_oidc_provider_arn,
    "arn:aws:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
  )
  d2_sub_pattern              = var.d2_sub_pattern
  allow_pr_demo               = var.allow_pr_demo
  mock_operator_principal_arn = var.mock_operator_principal_arn
  depends_on                  = [module.delivery]
}
