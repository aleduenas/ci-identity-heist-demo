variable "name" {
  type = string
}
variable "kubernetes_version" {
  type = string
}
variable "vpc_cidr" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
}
variable "node_instance_type" {
  type    = string
  default = "t3.medium"
}
variable "bootstrap_admin_role_arns" {
  type = set(string)
}
variable "console_viewer_arns" {
  description = "IAM users/roles given read-only cluster visibility (AmazonEKSViewPolicy)."
  type        = set(string)
  default     = []
}
variable "addon_versions" {
  description = "Optional exact versions after reviewing compatible AWS add-ons."
  type        = map(string)
  default     = {}
}
variable "endpoint_public_access" {
  description = "Expose the EKS API publicly (still IAM/RBAC-authenticated). The D2 exercise sets this so a CI runner can reach the cluster, as in pipelines that deploy over a public endpoint."
  type        = bool
  default     = false
}
variable "public_access_cidrs" {
  description = "CIDRs allowed to the public API endpoint when enabled."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
