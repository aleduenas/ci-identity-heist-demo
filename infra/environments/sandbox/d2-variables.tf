variable "enable_d2" {
  description = "Create isolated D2 exercise identities."
  type        = bool
  default     = false
}

variable "allow_pr_demo" {
  description = "Temporarily allow A2 PR-context assumption of the isolated demo role; false is main-only."
  type        = bool
  default     = false
}

variable "d2_sub_pattern" {
  description = "Reviewed custom GitHub subject template for repo/context/event/run/attempt; verify before enabling D2."
  type        = string
  default     = "repo:aleduenas@54992507/mybank-eks-sandbox@1416500552:{context}:event_name:{event_name}:run_id:*:run_attempt:*"
}

variable "mock_operator_principal_arn" {
  description = "Optional exact lab operator IAM user/role ARN for the simulated agent identity; null omits it."
  type        = string
  default     = null
  nullable    = true
}
