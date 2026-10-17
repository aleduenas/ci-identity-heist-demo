output "demo_role_arn" {
  value = aws_iam_role.demo_deploy.arn
}

output "mock_agent_role_arn" {
  value = try(aws_iam_role.mock_agent[0].arn, null)
}

output "subject_patterns" {
  value = local.subject_patterns
}
