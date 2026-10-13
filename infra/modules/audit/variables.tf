variable "name" {
  type = string
}
variable "aws_region" {
  type = string
}
variable "table_arns" {
  type = map(string)
}
