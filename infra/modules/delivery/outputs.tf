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
  value = local.subject
}
