"""Global Function Calling Tool Registry with OpenAI/Qwen JSON Schema Exporter."""

import inspect
import asyncio
from typing import Callable, Dict, Any, List, Optional


class ToolRegistry:
    """
    Global Tool Registry managing tool functions, parameter JSON schemas,
    OpenAI/Qwen tool definitions, and tool execution dispatching.
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        func: Optional[Callable] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Registers a tool function into the registry.
        Can be used as a function or decorator `@registry.register`.
        """
        def decorator(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            docstring = description or (fn.__doc__.strip() if fn.__doc__ else f"Tool {tool_name}")
            
            # Infer JSON Schema parameters if not provided
            param_schema = parameters or self._infer_parameters_schema(fn)

            self._tools[tool_name] = {
                "func": fn,
                "name": tool_name,
                "description": docstring,
                "parameters": param_schema
            }
            return fn

        if func is not None:
            return decorator(func)
        return decorator

    def _infer_parameters_schema(self, fn: Callable) -> Dict[str, Any]:
        """Infers JSON Schema parameter definitions from function inspect signature."""
        sig = inspect.signature(fn)
        properties = {}
        required = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = param.annotation
            json_type = "string"
            if param_type in type_map:
                json_type = type_map[param_type]
            elif hasattr(param_type, "__origin__"):
                origin = param_type.__origin__
                if origin in type_map:
                    json_type = type_map[origin]

            properties[param_name] = {
                "type": json_type,
                "description": f"Parameter {param_name}"
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Exports registered tools in standard OpenAI / Qwen function calling format.
        """
        tools_list = []
        for tool_name, info in self._tools.items():
            tools_list.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": info["description"],
                    "parameters": info["parameters"]
                }
            })
        return tools_list

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Executes a registered tool by name with arguments.
        Supports both async and sync tool functions.
        """
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' is not registered in ToolRegistry.")

        fn = self._tools[name]["func"]
        if asyncio.iscoroutinefunction(fn):
            return await fn(**args)
        else:
            return fn(**args)


# Singleton ToolRegistry instance
registry = ToolRegistry()


def register_tool(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
):
    """Global decorator for registering tool functions."""
    return registry.register(func, name=name, description=description, parameters=parameters)
