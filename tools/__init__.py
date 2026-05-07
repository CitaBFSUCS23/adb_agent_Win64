from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional, Any
import os
import sys
import importlib
import inspect


class BaseTool(ABC):
    """Base class for all tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get tool name (uppercase, used for selection)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get tool description"""
        pass

    @classmethod
    @abstractmethod
    def requires_context(cls) -> bool:
        """
        Does this tool require special context/parameters to initialize?
        
        Returns:
            True if tool needs context (like ADBTool needs adb_client), False otherwise
        """
        pass

    @classmethod
    def get_init_params(cls) -> Dict[str, Any]:
        """
        Get parameter descriptions for initialization
        
        Returns:
            Dictionary of parameter name to description
        """
        return {}

    @abstractmethod
    def execute(self, command: str, context: dict = None) -> Tuple[str, bool]:
        """
        Execute a command
        
        Args:
            command: Command to execute
            context: Additional context information
            
        Returns:
            Tuple of (output, success)
        """
        pass

    def get_prompt_section(self) -> str:
        """Get the prompt section for this tool"""
        return f"""### Tool: {self.name}
- Purpose: {self.description}
- Syntax: TOOL: {self.name.upper()}, COMMAND: <command>
"""


def discover_tools(tools_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover all tool classes in the tools directory
    
    Args:
        tools_dir: Directory to search for tool modules (default: current tools/ directory)
        
    Returns:
        Dictionary mapping tool name to tool class
    """
    if tools_dir is None:
        # Get the directory where this __init__.py is located
        tools_dir = os.path.dirname(os.path.abspath(__file__))
    
    tool_classes = {}
    
    # Add current directory to path for imports
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    
    # Get parent directory for relative imports
    parent_dir = os.path.dirname(tools_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Search for all Python files in tools directory
    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # Remove .py extension
            
            try:
                # Import the module
                module = importlib.import_module(f'tools.{module_name}')
                
                # Find all classes that inherit from BaseTool
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseTool) and 
                        obj != BaseTool and 
                        not inspect.isabstract(obj)):
                        # Get tool name from the class
                        # Create a dummy instance to get name (if possible)
                        try:
                            if not obj.requires_context():
                                dummy_instance = obj()
                                tool_name = dummy_instance.name
                                tool_classes[tool_name] = obj
                            else:
                                # For context-required tools, try to get name from class doc or convention
                                # Convention: class name matches tool name (e.g., ADBTool -> ADB)
                                if name.endswith('Tool'):
                                    tool_name = name[:-4].upper()
                                    tool_classes[tool_name] = obj
                        except Exception:
                            # If we can't get name from instance, use class name convention
                            if name.endswith('Tool'):
                                tool_name = name[:-4].upper()
                                tool_classes[tool_name] = obj
                            
            except Exception as e:
                print(f"Warning: Could not load tool module {filename}: {e}")
                continue
    
    return tool_classes


def load_tools(
    tool_classes: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, BaseTool]:
    """
    Load and instantiate tools
    
    Args:
        tool_classes: Dictionary of tool name to tool class (from discover_tools)
        context: Context dictionary with initialization parameters
        
    Returns:
        Dictionary mapping tool names to tool instances
    """
    if tool_classes is None:
        tool_classes = discover_tools()
    
    if context is None:
        context = {}
    
    tools = {}
    
    for tool_name, tool_class in tool_classes.items():
        try:
            if tool_class.requires_context():
                # Tool requires special context, check if we have the needed params
                params = tool_class.get_init_params()
                init_kwargs = {}
                
                # Try to get required params from context
                for param_name in params:
                    if param_name in context:
                        init_kwargs[param_name] = context[param_name]
                
                # Only instantiate if we have all required params
                if len(init_kwargs) >= len(params):
                    tools[tool_name] = tool_class(**init_kwargs)
            else:
                # Tool doesn't require special context, instantiate directly
                tools[tool_name] = tool_class()
        except Exception as e:
            print(f"Warning: Could not instantiate tool {tool_name}: {e}")
            continue
    
    return tools
