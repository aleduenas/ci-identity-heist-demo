variable "enable_detection" {
  description = "Create isolated detection exercise identities."
  type        = bool
  default     = false
}

variable "allow_pr_demo" {
  description = "Deprecated compatibility input; security/control.json now owns exercise PR trust."
  type        = bool
  default     = false
}

variable "detection_sub_pattern" {
  description = "Reviewed custom GitHub subject template for repo/context/event/run/attempt; verify before enabling detection."
  type        = string
  default     = "repo:aleduenas@54992507/ci-identity-heist-demo@1416500552:{context}:event_name:{event_name}:run_id:*:run_attempt:*"
}

variable "mock_operator_principal_arn" {
  description = "Optional exact lab operator IAM user/role ARN for the simulated agent identity; null omits it."
  type        = string
  default     = null
  nullable    = true
}
