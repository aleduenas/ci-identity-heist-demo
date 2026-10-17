variable "name" {
  type = string
}
variable "aws_region" {
  type = string
}
variable "table_arns" {
  type = map(string)
}
variable "lab_teardown_force" {
  description = "Lab only: let destroy remove retained logs/images. Keep false outside disposable labs."
  type        = bool
  default     = false
}
