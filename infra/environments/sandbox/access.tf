module "identity" {
  source             = "../../modules/identity"
  name               = var.name
  cluster_name       = module.eks.cluster_name
  cluster_arn        = module.eks.cluster_arn
  table_arns         = module.data.table_arns
  saml_metadata_path = var.saml_metadata_path
  depends_on         = [module.eks]
}

module "delivery" {
  source                            = "../../modules/delivery"
  name                              = var.name
  github_owner                      = var.github_owner
  github_repository                 = var.github_repository
  lab_teardown_force                = var.lab_teardown_force
  github_oidc_subject_prefix        = var.github_oidc_subject_prefix
  github_oidc_include_run_context   = var.github_oidc_include_run_context
  cluster_name                      = module.eks.cluster_name
  cluster_arn                       = module.eks.cluster_arn
  existing_github_oidc_provider_arn = var.existing_github_oidc_provider_arn
}
