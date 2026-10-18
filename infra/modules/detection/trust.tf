locals {
  trusted_contexts = concat([
    { context = "ref:refs/heads/main", event = "push" },
    { context = "ref:refs/heads/main", event = "workflow_dispatch" },
  ], var.allow_pr_demo ? [{ context = "pull_request", event = "pull_request" }] : [])
  subject_patterns = [for context in local.trusted_contexts : replace(
    replace(var.detection_sub_pattern, "{context}", context.context), "{event_name}", context.event
  )]
}

resource "aws_iam_role" "demo_deploy" {
  name                 = "${var.name}-detection-demo-deploy"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = var.github_oidc_provider_arn }
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike   = { "token.actions.githubusercontent.com:sub" = local.subject_patterns }
      }
    }]
  })
  tags = { Exercise = "detection", Identity = "demo-deployer" }
}
