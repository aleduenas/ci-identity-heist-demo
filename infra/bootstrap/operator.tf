resource "aws_iam_role" "operator" {
  count = var.operator_principal_arn == null ? 0 : 1
  name  = "mybank-sandbox-bootstrap"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect    = "Allow", Action = "sts:AssumeRole"
      Principal = { AWS = var.operator_principal_arn }
    }]
  })
  lifecycle {
    precondition {
      condition     = split(":", var.operator_principal_arn)[4] == var.aws_account_id
      error_message = "The bootstrap operator must belong to the allowed sandbox account."
    }
  }
}

resource "aws_iam_role_policy" "operator" {
  count = var.operator_principal_arn == null ? 0 : 1
  name  = "describe-lab-cluster"
  role  = aws_iam_role.operator[0].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect   = "Allow", Action = "eks:DescribeCluster"
      Resource = "arn:aws:eks:${var.aws_region}:${var.aws_account_id}:cluster/mybank-sandbox"
    }]
  })
}

output "bootstrap_operator_role_arn" {
  value = try(aws_iam_role.operator[0].arn, null)
}
