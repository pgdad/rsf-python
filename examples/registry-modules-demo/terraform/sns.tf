# RSF Feature: SNS notification topic for CloudWatch alarm actions
# Registry module: terraform-aws-modules/sns/aws v7.1.0
#
# Created unconditionally — CloudWatch alarms always need a notification target.
# The topic ARN is passed to each alarm module block via alarm_actions in alarms.tf.
#
# To receive alarm notifications, subscribe an email address or Lambda function
# to this topic after deployment (out of scope for this tutorial example).
#
# RSF WorkflowMetadata field: alarms[].sns_topic_arn (overridden here by module output)

module "sns_alarms" {
  source  = "terraform-aws-modules/sns/aws"
  version = "7.1.0"

  name = "${var.workflow_name}-alarm-notifications"

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
