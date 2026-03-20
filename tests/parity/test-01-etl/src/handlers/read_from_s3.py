"""Wrapper — imports real handler from handlers.etl.rsf_handlers."""

from handlers.etl.rsf_handlers import read_from_s3  # noqa: F401 — @state registration
