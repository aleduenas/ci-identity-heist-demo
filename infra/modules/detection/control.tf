resource "aws_iam_role" "security_control" {
  name                 = "${var.name}-github-security-control"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = var.github_oidc_provider_arn }
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [for event in ["push", "workflow_dispatch"] : replace(
            replace(var.detection_sub_pattern, "{context}", "ref:refs/heads/main"), "{event_name}", event
          )]
        }
      }
    }]
  })
  tags = { Exercise = "detection", Identity = "security-control" }
}

resource "aws_iam_role_policy" "security_control" {
  name = "manage-exercise-trust-only"
  role = aws_iam_role.security_control.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["iam:GetRole", "iam:UpdateAssumeRolePolicy"]
      Resource = aws_iam_role.demo_deploy.arn
    }]
  })
}
