variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_account_id" {
  description = "Explicit sandbox account; reject credentials for any other account."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply the twelve-digit sandbox account ID."
  }
}

variable "operator_principal_arns" {
  description = "Explicit existing IAM users or roles allowed to bootstrap private Kubernetes."
  type        = list(string)
  default     = []
  validation {
    condition = alltrue([for arn in var.operator_principal_arns : can(regex(
      "^arn:aws:iam::[0-9]{12}:(user|role)/.+$", arn
    ))])
    error_message = "Use real IAM user/role ARNs, never STS session ARNs."
  }
}

variable "state_bucket_name" {
  description = "Globally unique private bucket name; include your AWS account ID."
  type        = string
}

variable "budget_alert_email" {
  description = "Email for the USD20 monthly cost alert. Alert only; nothing is shut down. Null skips the budget."
  type        = string
  default     = null
}
