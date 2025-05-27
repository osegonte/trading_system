#!/usr/bin/env python3
"""
DeepSeek-Optimized AI Trading Bot Startup
Handles DeepSeek API configuration properly
"""

import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_directories():
    """Create necessary directories."""
    directories = ["data", "logs", "reports", "config"]
    for dir_name in directories:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
    
    # Initialize data files
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
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    return logging.getLogger("TradingSystem")

def verify_deepseek_config():
    """Verify DeepSeek API configuration."""
    config_file = project_root / "config" / "ai_trading_config.yaml"
    
    if not config_file.exists():
        print("❌ Configuration file not found!")
        print("Make sure config/ai_trading_config.yaml exists")
        return False
    
    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for AI module configuration
        ai_modules = config.get('modules', {}).get('ai', [])
        deepseek_found = False
        
        for module in ai_modules:
            if module.get('class') == 'AIPortfolioAgent':
                module_config = module.get('config', {})
                api_key = module_config.get('api_key', '')
                base_url = module_config.get('base_url', '')
                
                if 'deepseek' in base_url.lower():
                    deepseek_found = True
                    if api_key.startswith('sk-'):
                        print("✅ DeepSeek API configuration found")
                    else:
                        print("⚠️ DeepSeek API key may be missing or invalid")
                break
        
        if not deepseek_found:
            print("⚠️ DeepSeek configuration not found in config file")
            print("AI features may not work properly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False

def install_openai_if_needed():
    """Install OpenAI package if needed for DeepSeek compatibility."""
    try:
        import openai
        print("✅ OpenAI package available for DeepSeek compatibility")
        return True
    except ImportError:
        print("📦 Installing OpenAI package for DeepSeek compatibility...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openai==1.3.0"])
            import openai
            print("✅ OpenAI package installed successfully")
            return True
        except Exception as e:
            print(f"⚠️ Could not install OpenAI package: {e}")
            print("AI features will be disabled")
            return False

def main():
    """Main startup function for DeepSeek-powered trading bot."""
    print("🚀 AI Trading Bot - DeepSeek Edition")
    print("🤖 Powered by DeepSeek API")
    print("💎 Multi-Asset Trading: Stocks • Crypto • Forex (XAUUSD)")
    print("=" * 60)
    
    # Setup
    setup_directories()
    logger = setup_logging()
    
    # Verify configuration
    if not verify_deepseek_config():
        print("\n🔧 Please check your configuration:")
        print("1. Make sure config/ai_trading_config.yaml exists")
        print("2. Verify your DeepSeek API key is set")
        print("3. Check that base_url points to https://api.deepseek.com")
        return 1
    
    # Install OpenAI for compatibility
    openai_available = install_openai_if_needed()
    
    try:
        print("📦 Loading core modules...")
        
        # Import after setup
        import tkinter as tk
        from core.controller import TradingSystemController
        from ui.trading_gui import TradingBotGUI
        
        print("⚙️ Initializing trading system...")
        
        # Initialize controller
        config_path = "config/ai_trading_config.yaml"
        controller = TradingSystemController(config_path)
        
        print("🔧 Setting up modules...")
        controller.setup_from_config()
        
        # Check if AI agent is properly configured
        ai_agent = controller.get_module("ai", "ai_portfolio_agent")
        if ai_agent and openai_available:
            print("🤖 DeepSeek AI Agent ready")
        else:
            print("⚠️ AI Agent not available (continuing without AI features)")
        
        # Check data provider
        data_provider = controller.get_module("data_collection", "yahoo_finance")
        if data_provider:
            supported_forex = data_provider.get_supported_forex_symbols()
            if 'XAUUSD=X' in supported_forex:
                print("🥇 XAUUSD (Gold) trading ready")
            print(f"📈 {len(supported_forex)} forex pairs supported")
        
        # Check executor
        executor = controller.get_module("execution", "alpaca_executor")
        if executor:
            supported_assets = executor.get_supported_assets()
            print(f"🔗 Alpaca executor ready - Assets: {list(supported_assets.keys())}")
        
        controller.start()
        
        print("🖥️ Launching GUI...")
        
        # Create GUI
        root = tk.Tk()
        app = TradingBotGUI(root, controller)
        
        # Handle close
        def on_closing():
            print("🛑 Shutting down trading system...")
            try:
                controller.stop()
            except:
                pass
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        print("✅ Trading Bot launched successfully!")
        print("\n💡 Quick Start Guide:")
        print("   1. Go to Trading tab")
        print("   2. Select 'Forex' asset type")
        print("   3. Add XAUUSD (Gold) - use quick select or type manually")
        print("   4. Set levels (4-5) and drawdown (2-3%)")
        print("   5. Toggle system ON")
        print("   6. Chat with DeepSeek AI in AI Assistant tab")
        print("\n🎯 Supported Assets:")
        print("   📊 Stocks: AAPL, MSFT, GOOGL, TSLA, NVDA")
        print("   🪙 Crypto: BTC-USD, ETH-USD, ADA-USD")
        print("   💱 Forex: EURUSD, GBPUSD, USDJPY, XAUUSD, XAGUSD")
        
        # Start GUI
        root.mainloop()
        
        return 0
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n🔧 Missing dependencies. Install with:")
        print("pip install yfinance pandas numpy matplotlib tkinter")
        print("pip install alpaca-trade-api requests pyyaml")
        return 1
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        logger.error(f"Error: {e}", exc_info=True)
        print("\n📋 Troubleshooting:")
        print("1. Check your DeepSeek API key")
        print("2. Verify internet connection")
        print("3. Check log files in logs/ directory")
        return 1
    
    finally:
        print("🏁 Trading system stopped")

if __name__ == "__main__":
    sys.exit(main())