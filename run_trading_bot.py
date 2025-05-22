#!/usr/bin/env python3
"""
AI Trading Bot - Enhanced Startup Script
Comprehensive environment setup and validation
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """Check and setup the environment."""
    print("🔍 Checking environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check required directories
    required_dirs = ["data", "logs", "reports", "config"]
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {dir_name}")
    
    # Initialize empty data files if they don't exist
    data_files = {
        "data/equities.json": {},
        "data/trades.json": [],
        "data/performance.json": {}
    }
    
    for file_path, default_content in data_files.items():
        full_path = project_root / file_path
        if not full_path.exists() or full_path.stat().st_size == 0:
            with open(full_path, 'w') as f:
                json.dump(default_content, f, indent=2)
            print(f"✅ Initialized: {file_path}")
    
    return True

def check_configuration():
    """Check configuration files."""
    print("⚙️ Checking configuration...")
    
    config_file = project_root / "config" / "ai_trading_config.yaml"
    env_file = project_root / ".env"
    
    if not config_file.exists():
        print(f"❌ Configuration file missing: {config_file}")
        print("Please copy config/ai_trading_config.yaml.example and configure your settings")
        return False
    
    if not env_file.exists():
        print("⚠️  .env file not found - API keys will be loaded from config file")
    
    return True

def check_dependencies():
    """Check required dependencies."""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'tkinter',
        'yaml', 
        'pandas',
        'numpy',
        'yfinance',
        'alpaca_trade_api',
        'openai',
        'matplotlib',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            elif package == 'yaml':
                import yaml
            elif package == 'pandas':
                import pandas
            elif package == 'numpy':
                import numpy
            elif package == 'yfinance':
                import yfinance
            elif package == 'alpaca_trade_api':
                import alpaca_trade_api
            elif package == 'openai':
                import openai
            elif package == 'matplotlib':
                import matplotlib
            elif package == 'requests':
                import requests
                
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies satisfied")
    return True

def setup_logging():
    """Setup logging configuration."""
    log_dir = project_root / "logs"
    log_file = log_dir / f"trading_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('alpaca_trade_api').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    return logging.getLogger("TradingSystem")

def main():
    """Main startup function."""
    print("🚀 AI Trading Bot - Enhanced Modular System")
    print("📊 Mode: GUI with Alpaca Integration and AI Assistant")
    print("⚡ Features: Live Trading, DCA/Martingale, Portfolio AI")
    print("=" * 60)
    
    # Environment checks
    if not check_environment():
        print("❌ Environment check failed")
        return 1
    
    if not check_configuration():
        print("❌ Configuration check failed")
        return 1
    
    if not check_dependencies():
        print("❌ Dependency check failed")
        return 1
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting AI Trading Bot")
    
    try:
        # Import after checks
        import tkinter as tk
        from core.controller import TradingSystemController
        from ui.trading_gui import TradingBotGUI
        
        # Initialize the trading system controller
        config_path = "config/ai_trading_config.yaml"
        controller = TradingSystemController(config_path)
        
        print("🔧 Setting up trading system...")
        controller.setup_from_config()
        controller.start()
        
        print("🖥️ Launching GUI...")
        
        # Create and run GUI
        root = tk.Tk()
        app = TradingBotGUI(root, controller)
        
        # Handle window close properly
        def on_closing():
            print("🛑 Shutting down trading system...")
            controller.stop()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        print("✅ Trading Bot launched successfully!")
        print("📈 Ready for trading - Configure your equities and start!")
        print("💡 Tips:")
        print("   - Start with paper trading to test your strategies")
        print("   - Set conservative drawdown percentages (3-5%)")
        print("   - Monitor your positions regularly")
        print("   - Use the AI assistant for portfolio analysis")
        
        # Start the GUI main loop
        root.mainloop()
        
        return 0
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install missing dependencies: pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"❌ Error starting trading bot: {e}")
        if 'logger' in locals():
            logger.error(f"Error in trading bot: {e}", exc_info=True)
        return 1
        
    finally:
        if 'controller' in locals():
            controller.stop()
        print("🏁 Trading system stopped")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)