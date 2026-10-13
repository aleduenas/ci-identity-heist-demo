module "network" {
  source     = "../../modules/network"
  name       = var.name
  aws_region = var.aws_region
}

module "eks" {
  source                    = "../../modules/eks"
  name                      = var.name
  kubernetes_version        = var.kubernetes_version
  vpc_cidr                  = module.network.vpc_cidr
  private_subnet_ids        = module.network.private_subnet_ids
  bootstrap_admin_role_arns = var.bootstrap_admin_role_arns
  addon_versions            = var.addon_versions
  depends_on                = [module.network]
}

module "data" {
  source = "../../modules/data"
  name   = var.name
}

module "audit" {
  source     = "../../modules/audit"
  name       = var.name
  aws_region = var.aws_region
  table_arns = module.data.table_arns
}

module "operations" {
  count             = var.enable_operations_host ? 1 : 0
  source            = "../../modules/operations"
  name              = var.name
  vpc_id            = module.network.vpc_id
  private_subnet_id = module.network.private_subnet_ids[0]
  depends_on        = [module.network]
}
