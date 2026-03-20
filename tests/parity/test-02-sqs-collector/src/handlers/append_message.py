"""Wrapper — imports real handler from handlers.sqs_collector.rsf_handlers."""
from handlers.sqs_collector.rsf_handlers import append_message_handler  # noqa: F401 — @state registration
