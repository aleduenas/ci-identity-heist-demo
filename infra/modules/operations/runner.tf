data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  runner_parameter = "/${var.name}/runner-registration"
}

# The operator writes a short-lived GitHub registration token here, the host reads it once
# during registration, and the operator deletes it. Nothing else is readable.
resource "aws_iam_role_policy" "runner_registration" {
  name = "read-runner-registration-token"
  role = aws_iam_role.this.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "ssm:GetParameter"
      Resource = "arn:${data.aws_partition.current.partition}:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${local.runner_parameter}"
    }]
  })
}
