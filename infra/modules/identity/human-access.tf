resource "aws_iam_role_policy" "engineer" {
  count = local.federation_enabled ? 1 : 0
  name  = "describe-lab-cluster"
  role  = aws_iam_role.human["engineer"].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "eks:DescribeCluster", Resource = var.cluster_arn }]
  })
}

resource "aws_eks_access_entry" "engineer" {
  count             = local.federation_enabled ? 1 : 0
  cluster_name      = var.cluster_name
  principal_arn     = aws_iam_role.human["engineer"].arn
  kubernetes_groups = ["mybank:engineers"]
  type              = "STANDARD"
}

resource "aws_iam_role_policy" "support" {
  count = local.federation_enabled ? 1 : 0
  name  = "read-synthetic-customer-data"
  role  = aws_iam_role.human["support"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:DescribeTable", "dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Scan", "dynamodb:Query"]
      Resource = values(var.table_arns)
    }]
  })
}
