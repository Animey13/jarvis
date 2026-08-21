"""
JARVIS Plugin Schemas Module.

Provides Pydantic schemas for plugin metadata, capabilities, permissions, and status.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from plugins.permissions import PluginPermission


class PluginMetadata(BaseModel):
    """
    Metadata specification for JARVIS plugins.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Unique identifying name of the plugin")
    version: str = Field(default="1.0.0", description="Plugin version string")
    description: str = Field(default="", description="Human-readable description of plugin functionality")
    author: Optional[str] = Field(default="JARVIS Core Team", description="Plugin author")
    capabilities: List[str] = Field(default_factory=list, description="List of capability tokens or tool names")
    permissions: List[PluginPermission] = Field(
        default_factory=lambda: [PluginPermission.READ_ONLY],
        description="Declared security permissions required by the plugin",
    )
    configuration_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters schema"
    )


class PluginStatus(BaseModel):
    """
    Status model describing current state and diagnostic information of a plugin.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    version: str
    description: str
    enabled: bool = True
    permissions: List[str]
    capabilities: List[str]
    last_error: Optional[str] = None
    execution_count: int = 0
