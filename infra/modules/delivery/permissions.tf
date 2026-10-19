resource "aws_iam_role_policy" "build" {
  name = "push-app-image"
  role = aws_iam_role.build.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "ecr:GetAuthorizationToken", Resource = "*" },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:DescribeImages"]
        Resource = aws_ecr_repository.app.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "deploy" {
  name = "describe-lab-cluster"
  role = aws_iam_role.deploy.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "eks:DescribeCluster", Resource = var.cluster_arn }]
  })
}

resource "aws_eks_access_entry" "deploy" {
  cluster_name      = var.cluster_name
  principal_arn     = aws_iam_role.deploy.arn
  kubernetes_groups = ["mybank:deployers"]
  type              = "STANDARD"
}
