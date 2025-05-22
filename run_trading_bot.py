"""
AI Trading Bot - Enhanced Modular System
Launch script for GUI mode with all features
"""

import os
import sys
import logging
import tkinter as tk
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Launch the AI Trading Bot GUI."""
    print("🚀 Starting AI Trading Bot - Enhanced Modular System")
    print("📊 Mode: GUI with Alpaca integration and AI assistant")
    print("⚡ Features: Live trading, DCA/Martingale, Portfolio AI")
    print("=" * 60)
    
    try:
        from core.controller import TradingSystemController
        from ui.trading_gui import TradingBotGUI
        
        # Initialize the trading system controller
        config_path = "config/ai_trading_config.yaml"
        if not os.path.exists(config_path):
            print(f"❌ Configuration file not found: {config_path}")
            print("Please copy config/ai_trading_config.yaml.example and configure your API keys")
            return
        
        controller = TradingSystemController(config_path)
        controller.setup_from_config()
        controller.start()
        
        # Create and run GUI
        root = tk.Tk()
        app = TradingBotGUI(root, controller)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        
        print("✅ GUI launched successfully!")
        print("📈 Ready for trading - Configure your equities and start!")
        
        root.mainloop()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install requirements: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting trading bot: {e}")
        logging.error(f"Error in trading bot: {e}", exc_info=True)
    finally:
        if 'controller' in locals():
            controller.stop()
        print("🛑 Trading system stopped")

if __name__ == "__main__":
    main()