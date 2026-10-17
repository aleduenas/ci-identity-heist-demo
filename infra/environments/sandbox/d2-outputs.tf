output "d2_demo_role_arn" {
  value = try(module.d2[0].demo_role_arn, null)
}

output "mock_agent_role_arn" {
  value = try(module.d2[0].mock_agent_role_arn, null)
}

output "d2_subject_patterns" {
  value = try(module.d2[0].subject_patterns, [])
}
