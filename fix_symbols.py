#!/usr/bin/env python3
"""
Quick fix for symbol formats and API URLs
"""

import os
import yaml

def fix_config_file():
    """Fix the configuration file."""
    config_path = "config/ai_trading_config.yaml"
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Fix Alpaca base URL
        for module_type, modules in config.get('modules', {}).items():
            for module in modules:
                if module.get('class') == 'AlpacaExecutor':
                    if 'config' in module:
                        # Remove /v2 from base_url
                        current_url = module['config'].get('base_url', '')
                        if current_url.endswith('/v2'):
                            module['config']['base_url'] = current_url.replace('/v2', '')
                            print("✅ Fixed Alpaca base URL")
        
        # Fix symbols - replace XAUUSD=X with GC=F
        for module_type, modules in config.get('modules', {}).items():
            for module in modules:
                if module.get('class') == 'YahooFinanceProvider':
                    if 'config' in module and 'symbols' in module['config']:
                        symbols = module['config']['symbols']
                        # Replace problematic symbols
                        if 'XAUUSD=X' in symbols:
                            symbols[symbols.index('XAUUSD=X')] = 'GC=F'
                            print("✅ Fixed Gold symbol: XAUUSD=X → GC=F")
                        if 'XAGUSD=X' in symbols:
                            symbols[symbols.index('XAGUSD=X')] = 'SI=F'
                            print("✅ Fixed Silver symbol: XAGUSD=X → SI=F")
        
        # Write fixed config
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        print("✅ Configuration file updated")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing config: {e}")
        return False

def test_gold_symbol():
    """Test if Gold symbol works."""
    try:
        import yfinance as yf
        
        print("🧪 Testing Gold symbols...")
        
        # Test different Gold symbols
        gold_symbols = ['GC=F', 'GOLD', '^GOLD', 'XAUUSD=X']
        
        for symbol in gold_symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if info and 'regularMarketPrice' in info:
                    price = info['regularMarketPrice']
                    print(f"✅ {symbol}: ${price}")
                    return symbol
                else:
                    # Try fetching recent data
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                        print(f"✅ {symbol}: ${price:.2f} (from history)")
                        return symbol
            except Exception as e:
                print(f"❌ {symbol}: {e}")
        
        print("⚠️ No working Gold symbol found")
        return None
        
    except ImportError:
        print("❌ yfinance not available for testing")
        return None

if __name__ == "__main__":
    print("🔧 Fixing Trading Bot Configuration...")
    print("=" * 40)
    
    # Fix config file
    if fix_config_file():
        print("\n🧪 Testing symbols...")
        working_gold = test_gold_symbol()
        
        if working_gold:
            print(f"\n🥇 Use this symbol for Gold: {working_gold}")
        
        print("\n✅ Configuration fixed!")
        print("\n🚀 Now restart your bot with:")
        print("python deepseek_start.py")
    else:
        print("\n❌ Fix failed - check your config file manually")