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
variable "addon_versions" {
  description = "Optional exact versions after reviewing compatible AWS add-ons."
  type        = map(string)
  default     = {}
}
