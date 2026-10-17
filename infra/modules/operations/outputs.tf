output "instance_id" {
  value = aws_instance.this.id
}
output "runner_parameter_name" {
  value = local.runner_parameter
}
