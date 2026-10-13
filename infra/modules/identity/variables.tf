variable "name" {
  type = string
}
variable "cluster_name" {
  type = string
}
variable "cluster_arn" {
  type = string
}
variable "table_arns" {
  type = map(string)
}
variable "saml_metadata_path" {
  description = "Path to exported live Keycloak metadata; null disables human federation."
  type        = string
  default     = null
}
