#!/usr/bin/env python3
"""
AI Trading Bot - Simplified Launcher
Clean, optimized startup for the Parent-Child AI Trading Ecosystem
"""

import os
import sys
import json
import logging
import argparse
import threading
import time
import warnings
from pathlib import Path
from datetime import datetime

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Setup the environment."""
    print("🔧 Setting up environment...")
    
    # Create directory structure
    directories = [
        "data/features", "data/parent", "logs/parent", "jobs", "reports"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Environment ready")

def start_parent_controller():
    """Start the parent controller."""
    try:
        from core.parent.parent_controller import ParentController
        parent = ParentController()
        parent.configure({})
        parent.activate()
        print("🧠 Parent Controller: ACTIVE")
        return parent
    except Exception as e:
        print(f"🧠 Parent Controller: SIMPLIFIED ({str(e)[:50]}...)")
        return {"active": True, "deactivate": lambda: None}

def start_trading_system(config_path):
    """Start the main trading system."""
    try:
        from core.controller import TradingSystemController
        
        controller = TradingSystemController(config_path)
        controller.setup_from_config()
        controller.start()
        
        print("⚡ Trading System: ACTIVE")
        return controller
        
    except Exception as e:
        print(f"❌ Trading System Error: {e}")
        return None

def start_gui(controller):
    """Start the GUI interface."""
    try:
        import tkinter as tk
        from ui.trading_gui import TradingBotGUI
        
        root = tk.Tk()
        app = TradingBotGUI(root, controller)
        
        def on_closing():
            print("🛑 Shutting down...")
            try:
                controller.stop()
            except:
                pass
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        return root, app
        
    except Exception as e:
        print(f"❌ GUI Error: {e}")
        return None, None

def main():
    """Main startup function."""
    parser = argparse.ArgumentParser(description="AI Trading Bot")
    parser.add_argument("--mode", choices=["full", "child", "parent"], default="full")
    parser.add_argument("--gui", action="store_true", default=True)
    parser.add_argument("--config", default="config/ai_trading_config.yaml")
    parser.add_argument("--no-gui", action="store_true", help="Run without GUI")
    
    args = parser.parse_args()
    
    if args.no_gui:
        args.gui = False
    
    print("🚀 AI Trading Bot - Parent-Child Ecosystem")
    print("🎯 Multi-Asset • AI-Powered • Distributed Learning")
    print("=" * 60)
    
    # Setup
    setup_environment()
    
    # Setup logging
    log_file = f"logs/trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    try:
        parent = None
        controller = None
        
        # Start components based on mode
        if args.mode in ["parent", "full"]:
            parent = start_parent_controller()
        
        if args.mode in ["child", "full"]:
            controller = start_trading_system(args.config)
            
            if not controller:
                print("❌ Failed to start trading system")
                return 1
        
        # Launch GUI if requested
        if args.gui and controller:
            print("🖥️ Launching GUI...")
            root, app = start_gui(controller)
            
            if root and app:
                print("✅ System launched successfully!")
                print(f"\n📊 Status:")
                print(f"   Mode: {args.mode.upper()}")
                print(f"   Parent Learning: {'ACTIVE' if parent else 'DISABLED'}")
                print(f"   Trading System: {'ACTIVE' if controller else 'DISABLED'}")
                print(f"   GUI: ACTIVE")
                print(f"   Log: {log_file}")
                
                print(f"\n💡 Features:")
                print("   🎯 Multi-Asset Trading (Stocks, Crypto, Commodities)")
                print("   🤖 AI Portfolio Assistant")
                print("   📈 Real-time Monitoring")
                print("   🧠 Distributed Learning Network")
                
                # Start GUI main loop
                root.mainloop()
            else:
                print("❌ Failed to launch GUI")
                return 1
        
        else:
            # Run without GUI
            print("✅ System started successfully!")
            print("Press Ctrl+C to stop...")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping system...")
        
        return 0
        
    except Exception as e:
        print(f"❌ System error: {e}")
        return 1
    
    finally:
        # Cleanup
        if parent and hasattr(parent, 'deactivate'):
            parent.deactivate()
        if controller and hasattr(controller, 'stop'):
            controller.stop()

if __name__ == "__main__":
    sys.exit(main())