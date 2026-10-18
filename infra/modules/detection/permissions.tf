resource "aws_iam_role_policy" "demo_deploy" {
  name = "describe-only-lab-cluster"
  role = aws_iam_role.demo_deploy.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "eks:DescribeCluster", Resource = var.cluster_arn }]
  })
}

resource "aws_eks_access_entry" "demo_deploy" {
  cluster_name      = var.cluster_name
  principal_arn     = aws_iam_role.demo_deploy.arn
  kubernetes_groups = ["mybank:deployers"]
  type              = "STANDARD"
}
