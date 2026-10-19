output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
output "build_role_arn" {
  value = aws_iam_role.build.arn
}
output "deploy_role_arn" {
  value = aws_iam_role.deploy.arn
}
output "github_oidc_subject" {
  description = "First accepted main subject; a pattern in run-context mode. Prefer github_oidc_subjects for all accepted patterns."
  value       = local.subjects[0]
}
output "github_oidc_subjects" {
  description = "Accepted main-only subjects/patterns. Run-context mode allows push and manual dispatch, never PR events."
  value       = local.subjects
}
