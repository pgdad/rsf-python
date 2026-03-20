output "sfn_arn" {
  value = aws_sfn_state_machine.choice_routing.arn
}

output "rsf_function_name" {
  value = aws_lambda_function.rsf_choice.function_name
}

output "rsf_alias_arn" {
  value = aws_lambda_alias.rsf_live.arn
}

output "rsf_log_group_name" {
  value = aws_cloudwatch_log_group.rsf_logs.name
}
