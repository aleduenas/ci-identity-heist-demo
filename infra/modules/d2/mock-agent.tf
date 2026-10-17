resource "aws_iam_role" "mock_agent" {
  count                = var.mock_operator_principal_arn == null ? 0 : 1
  name                 = "${var.name}-d2-mock-agent"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { AWS = var.mock_operator_principal_arn }
    }]
  })
  tags = { Exercise = "d2", Identity = "mock-agent" }
}

resource "aws_iam_role_policy" "mock_agent" {
  count = var.mock_operator_principal_arn == null ? 0 : 1
  name  = "inspect-only-lab-cluster"
  role  = aws_iam_role.mock_agent[0].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "eks:DescribeCluster", Resource = var.cluster_arn }]
  })
}
