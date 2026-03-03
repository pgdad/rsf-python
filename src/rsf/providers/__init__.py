"""RSF pluggable infrastructure providers.

Provides the abstract base class, context types, metadata schema,
transport mechanisms, and registry for infrastructure providers
(Terraform, CDK, Custom).
"""

from rsf.providers.base import (
    InfrastructureProvider,
    PrerequisiteCheck,
    ProviderContext,
)
from rsf.providers.metadata import (
    WorkflowMetadata,
    create_metadata,
)
from rsf.providers.registry import (
    ProviderNotFoundError,
    get_provider,
    list_providers,
    register_provider,
)
from rsf.providers.cdk import CDKProvider
from rsf.providers.custom import CustomProvider
from rsf.providers.terraform import TerraformProvider
from rsf.providers.transports import (
    ArgsTransport,
    EnvTransport,
    FileTransport,
    MetadataTransport,
)

# Register built-in providers
register_provider("terraform", TerraformProvider)
register_provider("cdk", CDKProvider)
register_provider("custom", CustomProvider)

__all__ = [
    "ArgsTransport",
    "CDKProvider",
    "CustomProvider",
    "EnvTransport",
    "FileTransport",
    "InfrastructureProvider",
    "MetadataTransport",
    "PrerequisiteCheck",
    "ProviderContext",
    "ProviderNotFoundError",
    "TerraformProvider",
    "WorkflowMetadata",
    "create_metadata",
    "get_provider",
    "list_providers",
    "register_provider",
]
