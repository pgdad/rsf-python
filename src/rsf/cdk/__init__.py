"""RSF CDK app generation module.

Provides the template engine and generator for producing Python CDK apps
from RSF workflow definitions.
"""

from rsf.cdk.engine import render_cdk_template
from rsf.cdk.generator import CDKConfig, CDKResult, generate_cdk

__all__ = [
    "CDKConfig",
    "CDKResult",
    "generate_cdk",
    "render_cdk_template",
]
