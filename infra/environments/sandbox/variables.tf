variable "aws_account_id" {
  description = "Dedicated lab account ID; provider refuses other accounts."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply a 12-digit AWS lab account ID."
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "mybank-sandbox"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.name))
    error_message = "Name must be 3-25 lowercase letters, digits or dashes, starting with a letter."
  }
}

variable "kubernetes_version" {
  type    = string
  default = "1.35"
}

variable "bootstrap_admin_role_arns" {
  description = "Existing IAM role ARNs explicitly granted bootstrap cluster administration."
  type        = set(string)
  validation {
    condition = length(var.bootstrap_admin_role_arns) > 0 && alltrue([
      for arn in var.bootstrap_admin_role_arns : can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", arn))
    ])
    error_message = "Supply at least one existing IAM role ARN; assumed-role session ARNs are invalid."
  }
}

variable "console_viewer_arns" {
  description = "Human IAM users/roles given read-only EKS console visibility (no Secrets, no writes)."
  type        = set(string)
  default     = []
  validation {
    condition = alltrue([
      for arn in var.console_viewer_arns : can(regex("^arn:aws:iam::[0-9]{12}:(user|role)/.+$", arn))
    ])
    error_message = "Use IAM user or role ARNs, never STS session ARNs or the root user."
  }
}

variable "saml_metadata_path" {
  type    = string
  default = null
}

variable "existing_github_oidc_provider_arn" {
  type    = string
  default = null
}

variable "enable_operations_host" {
  type    = bool
  default = true
}

variable "addon_versions" {
  type    = map(string)
  default = {}
}

variable "github_oidc_subject_prefix" {
  description = "Verified GitHub immutable subject prefix for this repository. Reverify after rename/transfer."
  type        = string
  default     = "repo:aleduenas@54992507/ci-identity-heist-demo@1416500552"
}
variable "github_oidc_include_run_context" {
  description = "Match the coordinated custom GitHub subject containing signed event, run and attempt identifiers."
  type        = bool
  default     = false
}
variable "github_owner" {
  description = "GitHub owner of the delivery repository; scripts/demo derives it from the git remote."
  type        = string
  default     = "aleduenas"
}
variable "github_repository" {
  description = "GitHub repository name; its numeric IDs belong in github_oidc_subject_prefix."
  type        = string
  default     = "ci-identity-heist-demo"
}
variable "lab_teardown_force" {
  description = "Lab only: let destroy remove retained logs/images. Keep false outside disposable labs."
  type        = bool
  default     = false
}
variable "cluster_public_access" {
  description = "Expose the EKS API publicly for the detection exercise so a CI runner can reach it (IAM/RBAC still enforced)."
  type        = bool
  default     = false
}
