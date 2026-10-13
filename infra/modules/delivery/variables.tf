variable "name" {
  type = string
}
variable "github_owner" {
  type = string
}
variable "github_repository" {
  type = string
}
variable "cluster_name" {
  type = string
}
variable "cluster_arn" {
  type = string
}
variable "existing_github_oidc_provider_arn" {
  description = "Reuse account-global GitHub OIDC provider if one already exists."
  type        = string
  default     = null
}
