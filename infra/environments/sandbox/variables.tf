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
  default = "ca-central-1"
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
  default     = "repo:aleduenas@54992507/mybank-eks-sandbox@1416500552"
}
