variable "name" {
  description = "Name of the existing synthetic sandbox."
  type        = string
}

variable "aws_account_id" {
  description = "Account boundary for every role, provider and cluster in this exercise."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply the 12-digit sandbox AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "cluster_arn" {
  type = string
  validation {
    condition     = can(regex("^arn:aws:eks:[a-z0-9-]+:${var.aws_account_id}:cluster/.+$", var.cluster_arn))
    error_message = "The cluster must belong to the declared sandbox account."
  }
}

variable "github_oidc_provider_arn" {
  type = string
  validation {
    condition     = var.github_oidc_provider_arn == "arn:aws:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
    error_message = "Use the GitHub OIDC provider in the declared sandbox account."
  }
}

variable "detection_sub_pattern" {
  description = "Exact repository prefix and custom subject template; only signed run identifiers may be wildcarded."
  type        = string
  validation {
    condition = can(regex(
      "^repo:[A-Za-z0-9-]+(@[0-9]+)?/[A-Za-z0-9_.-]+(@[0-9]+)?:\\{context\\}:event_name:\\{event_name\\}:run_id:\\*:run_attempt:\\*$",
      var.detection_sub_pattern
    ))
    error_message = "Use repo:OWNER/REPO:{context}:event_name:{event_name}:run_id:*:run_attempt:* with the verified immutable IDs when applicable."
  }
}

variable "allow_pr_demo" {
  description = "Explicit, temporary permission for the A2 PR-context assumption; false is the main-only B2 state."
  type        = bool
  default     = false
}

variable "mock_operator_principal_arn" {
  description = "Optional exact IAM user or role allowed to assume the mock-agent identity; never an STS session ARN."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition = var.mock_operator_principal_arn == null ? true : can(regex(
      "^arn:aws:iam::${var.aws_account_id}:(user|role)/[A-Za-z0-9+=,.@_/-]+$",
      var.mock_operator_principal_arn
    ))
    error_message = "Use an explicit IAM user or role in the declared sandbox account, or null to omit the mock role."
  }
}
