resource "aws_eks_access_entry" "admins" {
  for_each      = var.bootstrap_admin_role_arns
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = each.value
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "admins" {
  for_each      = var.bootstrap_admin_role_arns
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_eks_access_entry.admins[each.value].principal_arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}

# Read-only console/kubectl visibility for named humans; no Secrets, no writes.
resource "aws_eks_access_entry" "viewers" {
  for_each      = var.console_viewer_arns
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = each.value
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "viewers" {
  for_each      = var.console_viewer_arns
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_eks_access_entry.viewers[each.value].principal_arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"
  access_scope {
    type = "cluster"
  }
}
