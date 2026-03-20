"""Wrapper — imports real handler from handlers.etl.rsf_handlers."""

from handlers.etl.rsf_handlers import transform_one_handler  # noqa: F401 — @state registration
