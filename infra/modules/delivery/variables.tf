variable "name" {
  type = string
}
variable "github_owner" {
  type = string
}
variable "github_repository" {
  type = string
}
variable "github_oidc_subject_prefix" {
  description = "Verified repository subject prefix, with immutable IDs when GitHub supplies them."
  type        = string
  validation {
    condition = (
      can(regex("^repo:[A-Za-z0-9-]+(@[0-9]+)?/[A-Za-z0-9_.-]+(@[0-9]+)?$", var.github_oidc_subject_prefix)) &&
      replace(var.github_oidc_subject_prefix, "/@[0-9]+/", "") == "repo:${var.github_owner}/${var.github_repository}"
    )
    error_message = "Use the exact configured owner/repository prefix, optionally with numeric immutable IDs; wildcards and suffixes are forbidden."
  }
}
variable "cluster_name" {
  type = string
}
variable "github_oidc_include_run_context" {
  description = "Use the reviewed custom repo/context/event/run/attempt subject while keeping release roles main-only."
  type        = bool
  default     = false
}
variable "cluster_arn" {
  type = string
}
variable "existing_github_oidc_provider_arn" {
  description = "Reuse account-global GitHub OIDC provider if one already exists."
  type        = string
  default     = null
}
