from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import uuid

class IModule(ABC):
    """Base interface for all trading system modules."""
    
    def __init__(self, module_id: Optional[str] = None):
        self.module_id = module_id or str(uuid.uuid4())
        self.is_configured = False
        self.is_active = False
        self._dependencies = {}
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the module with provided settings.
        
        Args:
            config: Configuration dictionary for this module
        """
        self.is_configured = True
    
    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Execute the module's core functionality.
        
        Args:
            input_data: The input data for this module
            
        Returns:
            The output data from this module
        """
        pass
    
    def register_dependency(self, dependency_id: str, module: 'IModule') -> None:
        """Register another module as a dependency.
        
        Args:
            dependency_id: Identifier for the dependency
            module: The module instance to register
        """
        self._dependencies[dependency_id] = module
    
    def get_dependency(self, dependency_id: str) -> Optional['IModule']:
        """Get a registered dependency module.
        
        Args:
            dependency_id: Identifier for the dependency
            
        Returns:
            The dependency module if found, otherwise None
        """
        return self._dependencies.get(dependency_id)
    
    def activate(self) -> None:
        """Activate this module."""
        if not self.is_configured:
            raise RuntimeError(f"Module {self.module_id} must be configured before activation")
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate this module."""
        self.is_active = False
