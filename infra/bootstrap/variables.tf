variable "aws_region" {
  type    = string
  default = "ca-central-1"
}

variable "aws_account_id" {
  description = "Explicit sandbox account; reject credentials for any other account."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply the twelve-digit sandbox account ID."
  }
}

variable "operator_principal_arn" {
  description = "Explicit existing IAM user or role allowed to bootstrap private Kubernetes."
  type        = string
  default     = null
  validation {
    condition = var.operator_principal_arn == null || can(regex(
      "^arn:aws:iam::[0-9]{12}:(user|role)/.+$", var.operator_principal_arn
    ))
    error_message = "Use a real IAM user/role ARN, never an STS session ARN."
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
