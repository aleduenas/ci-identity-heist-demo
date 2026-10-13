resource "aws_iam_role" "app" {
  name = "${var.name}-app"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow", Principal = { Service = "pods.eks.amazonaws.com" }
      Action = ["sts:AssumeRole", "sts:TagSession"]
      Condition = {
        StringEquals = {
          "aws:RequestTag/kubernetes-namespace"       = "mybank"
          "aws:RequestTag/kubernetes-service-account" = "mybank-api"
          "aws:RequestTag/eks-cluster-name"           = var.cluster_name
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "app" {
  name = "transactional-app-data"
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "dynamodb:GetItem", Resource = values(var.table_arns) },
      {
        Effect    = "Allow", Action = "dynamodb:UpdateItem", Resource = var.table_arns["accounts"]
        Condition = { "ForAnyValue:StringEquals" = { "dynamodb:EnclosingOperation" = ["TransactWriteItems"] } }
      },
      {
        Effect    = "Allow", Action = "dynamodb:PutItem", Resource = var.table_arns["transfers"]
        Condition = { "ForAnyValue:StringEquals" = { "dynamodb:EnclosingOperation" = ["TransactWriteItems"] } }
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "app" {
  cluster_name    = var.cluster_name
  namespace       = "mybank"
  service_account = "mybank-api"
  role_arn        = aws_iam_role.app.arn
  depends_on      = [aws_iam_role_policy.app]
}
