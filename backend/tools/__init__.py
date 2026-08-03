"""Tools Package Initialization exposing global ToolRegistry singleton and decorator."""

from backend.tools.registry import registry, register_tool, ToolRegistry
import backend.tools.impl  # noqa: F401 Trigger registration of core tools

__all__ = [
    "registry",
    "register_tool",
    "ToolRegistry",
]
