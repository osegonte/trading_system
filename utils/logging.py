import logging
import os
from datetime import datetime

def setup_logging(log_level=logging.INFO, log_file=None):
    """Set up logging configuration for the trading system."""
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Default log file with timestamp
    if log_file is None:
        log_file = os.path.join(log_dir, f"trading_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Set specific log levels for external libraries
    logging.getLogger('alpaca_trade_api').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    return logging.getLogger("TradingSystem")