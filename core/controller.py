# core/controller.py
from typing import Any, Dict, List, Optional, Type
import logging
import importlib
import yaml
from pathlib import Path

from .interfaces import IModule
from .exceptions import ModuleError, ConfigurationError

class TradingSystemController:
    """Central controller for the modular trading system."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.modules = {}
        self.config = {}
        self.logger = logging.getLogger("TradingSystem")
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """Load system configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file
        """
        try:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            self.logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def register_module(self, module_type: str, module: IModule) -> None:
        """Register a module with the system.
        
        Args:
            module_type: The type of module (e.g., "data_collection", "signal_generation")
            module: The module instance to register
        """
        module_key = f"{module_type}.{module.module_id}"
        self.modules[module_key] = module
        self.logger.info(f"Registered module: {module_key}")
    
    def unregister_module(self, module_type: str, module_id: str) -> bool:
        """Unregister a module from the system.
        
        Args:
            module_type: The type of module
            module_id: The ID of the module to unregister
            
        Returns:
            True if the module was unregistered, False otherwise
        """
        module_key = f"{module_type}.{module_id}"
        if module_key in self.modules:
            module = self.modules[module_key]
            if module.is_active:
                module.deactivate()
            del self.modules[module_key]
            self.logger.info(f"Unregistered module: {module_key}")
            return True
        return False
    
    def get_module(self, module_type: str, module_id: str) -> Optional[IModule]:
        """Get a registered module.
        
        Args:
            module_type: The type of module
            module_id: The ID of the module
            
        Returns:
            The module instance if found, otherwise None
        """
        module_key = f"{module_type}.{module_id}"
        return self.modules.get(module_key)
    
    def get_modules_by_type(self, module_type: str) -> List[IModule]:
        """Get all registered modules of a specific type.
        
        Args:
            module_type: The type of module
            
        Returns:
            List of module instances
        """
        return [
            module for key, module in self.modules.items()
            if key.startswith(f"{module_type}.")
        ]
    
    def load_module_from_path(self, module_path: str, module_class: str, 
                             module_type: str, module_id: str = None,
                             config: Dict[str, Any] = None) -> IModule:
        """Dynamically load and register a module from a Python path.
        
        Args:
            module_path: Python import path (e.g., "modules.data_collection.ohlc_provider")
            module_class: Class name within the module
            module_type: Type of module to register as
            module_id: Optional custom ID for the module
            config: Optional configuration for the module
            
        Returns:
            The loaded and registered module instance
        """
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, module_class)
            instance = cls(module_id=module_id)
            
            if config:
                instance.configure(config)
                
            self.register_module(module_type, instance)
            return instance
        except Exception as e:
            self.logger.error(f"Failed to load module {module_path}.{module_class}: {e}")
            raise ModuleError(f"Failed to load module: {e}")
    
    def setup_from_config(self) -> None:
        """Set up the system from loaded configuration."""
        if not self.config:
            raise ConfigurationError("No configuration loaded")
        
        # Process modules configuration
        for module_type, modules_config in self.config.get("modules", {}).items():
            for module_config in modules_config:
                self.load_module_from_path(
                    module_path=module_config["path"],
                    module_class=module_config["class"],
                    module_type=module_type,
                    module_id=module_config.get("id"),
                    config=module_config.get("config", {})
                )
        
        # Process dependencies
        for module_type, modules_config in self.config.get("modules", {}).items():
            for module_config in modules_config:
                if "dependencies" in module_config:
                    source_module = self.get_module(module_type, module_config.get("id"))
                    if source_module:
                        for dep_id, dep_info in module_config["dependencies"].items():
                            dep_module = self.get_module(dep_info["type"], dep_info["id"])
                            if dep_module:
                                source_module.register_dependency(dep_id, dep_module)
        
        self.logger.info("System setup complete")
    
    def start(self) -> None:
        """Start the trading system."""
        for module in self.modules.values():
            if not module.is_active and module.is_configured:
                module.activate()
        self.logger.info("Trading system started")
    
    def stop(self) -> None:
        """Stop the trading system."""
        for module in self.modules.values():
            if module.is_active:
                module.deactivate()
        self.logger.info("Trading system stopped")