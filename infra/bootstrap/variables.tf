variable "aws_region" {
  type    = string
  default = "ca-central-1"
}

variable "state_bucket_name" {
  description = "Globally unique private bucket name; include your AWS account ID."
  type        = string
}
