# RSF Feature: CloudWatch metric alarms for Lambda observability
# Registry module: terraform-aws-modules/cloudwatch/aws//modules/metric-alarm v5.7.2
#
# Three alarm types, each conditionally created based on whether the alarms variable
# contains an entry of that type. A locals block converts the list to a map keyed by
# alarm type, making the count conditional a simple key lookup.
#
# Alarm types and their CloudWatch metrics:
#   error_rate  → Errors metric, Sum statistic (Lambda invocation errors)
#   duration    → Duration metric, Average statistic (execution time in ms)
#   throttle    → Throttles metric, Sum statistic (Lambda throttling events)
#
# All alarms:
#   - Scoped to the Lambda function name via dimensions
#   - Send notifications to the SNS topic created in sns.tf
#   - treat_missing_data = "notBreaching" to avoid false alarms on sparse traffic
#
# RSF WorkflowMetadata field: alarms (list[dict])
#   Each dict: type, threshold, period, evaluation_periods

locals {
  # Convert alarms list to map keyed by type for O(1) key lookup in count conditionals.
  # Example: [{ type = "error_rate", threshold = 5, ... }]
  #       => { "error_rate" = { type = "error_rate", threshold = 5, ... } }
  alarm_by_type = { for a in var.alarms : a.type => a }
}

# Alarm: Lambda invocation errors exceed threshold within evaluation window
module "alarm_error_rate" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "5.7.2"
  count   = contains(keys(local.alarm_by_type), "error_rate") ? 1 : 0

  alarm_name          = "${var.workflow_name}-error-rate"
  alarm_description   = "Lambda function ${var.workflow_name} error rate exceeded threshold"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = local.alarm_by_type["error_rate"].evaluation_periods
  threshold           = local.alarm_by_type["error_rate"].threshold
  period              = local.alarm_by_type["error_rate"].period

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  statistic   = "Sum"

  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = module.lambda.lambda_function_name
  }

  alarm_actions = [module.sns_alarms.topic_arn]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}

# Alarm: Lambda average execution duration exceeds threshold within evaluation window
module "alarm_duration" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "5.7.2"
  count   = contains(keys(local.alarm_by_type), "duration") ? 1 : 0

  alarm_name          = "${var.workflow_name}-duration"
  alarm_description   = "Lambda function ${var.workflow_name} average duration exceeded threshold (milliseconds)"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = local.alarm_by_type["duration"].evaluation_periods
  threshold           = local.alarm_by_type["duration"].threshold
  period              = local.alarm_by_type["duration"].period

  namespace   = "AWS/Lambda"
  metric_name = "Duration"
  statistic   = "Average"

  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = module.lambda.lambda_function_name
  }

  alarm_actions = [module.sns_alarms.topic_arn]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}

# Alarm: Lambda throttling events exceed threshold within evaluation window
module "alarm_throttle" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "5.7.2"
  count   = contains(keys(local.alarm_by_type), "throttle") ? 1 : 0

  alarm_name          = "${var.workflow_name}-throttle"
  alarm_description   = "Lambda function ${var.workflow_name} throttle count exceeded threshold"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = local.alarm_by_type["throttle"].evaluation_periods
  threshold           = local.alarm_by_type["throttle"].threshold
  period              = local.alarm_by_type["throttle"].period

  namespace   = "AWS/Lambda"
  metric_name = "Throttles"
  statistic   = "Sum"

  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = module.lambda.lambda_function_name
  }

  alarm_actions = [module.sns_alarms.topic_arn]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
