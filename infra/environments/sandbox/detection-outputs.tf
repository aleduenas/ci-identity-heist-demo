output "detection_demo_role_arn" {
  value = try(module.detection[0].demo_role_arn, null)
}

output "mock_agent_role_arn" {
  value = try(module.detection[0].mock_agent_role_arn, null)
}

output "detection_subject_patterns" {
  value = try(module.detection[0].subject_patterns, [])
}
