class TradingSystemError(Exception):
    """Base exception for trading system errors."""
    pass

class ModuleError(TradingSystemError):
    """Exception raised for module-related errors."""
    pass

class ConfigurationError(TradingSystemError):
    """Exception raised for configuration errors."""
    pass

class DataError(TradingSystemError):
    """Exception raised for data-related errors."""
    pass

class ExecutionError(TradingSystemError):
    """Exception raised for execution errors."""
    pass

class APIError(TradingSystemError):
    """Exception raised for API-related errors."""
    pass
