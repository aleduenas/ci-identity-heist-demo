locals {
  addons = toset(["vpc-cni", "kube-proxy", "coredns", "eks-pod-identity-agent"])
}

data "aws_eks_addon_version" "compatible" {
  for_each           = local.addons
  addon_name         = each.value
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}

# Install networking before nodes. CoreDNS needs nodes and is installed afterward.
resource "aws_eks_addon" "cni" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "vpc-cni"
  addon_version               = lookup(var.addon_versions, "vpc-cni", data.aws_eks_addon_version.compatible["vpc-cni"].version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  configuration_values        = jsonencode({ enableNetworkPolicy = "true" })
}

resource "aws_eks_addon" "runtime" {
  for_each                    = setsubtract(local.addons, toset(["vpc-cni"]))
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = each.value
  addon_version               = lookup(var.addon_versions, each.value, data.aws_eks_addon_version.compatible[each.value].version)
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  depends_on                  = [aws_eks_node_group.this]
}
