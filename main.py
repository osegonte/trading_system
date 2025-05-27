# main.py
import os
import argparse
import logging
from datetime import datetime, timedelta
import time
import yaml
import tkinter as tk
from ui.trading_gui import TradingBotGUI
from utils.logging import setup_logging
from core.controller import TradingSystemController
from core.models import PriceData, SignalType


def main():
    """Main entry point for the enhanced multi-asset trading system."""
    # Set up logging
    logger = setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Enhanced Multi-Asset Trading System")
    parser.add_argument("--config", type=str, default="config/ai_trading_config.yaml",
                       help="Path to system configuration file")
    parser.add_argument("--mode", type=str, 
                       choices=["backtest", "paper", "live", "gui"], 
                       default="gui",
                       help="Trading mode")
    parser.add_argument("--start_date", type=str, default=None,
                       help="Start date for backtest (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default=None,
                       help="End date for backtest (YYYY-MM-DD)")
    parser.add_argument("--asset_types", type=str, nargs='+', 
                       choices=["stock", "crypto", "forex"], 
                       default=["stock", "crypto", "forex"],
                       help="Asset types to include in trading")
    
    args = parser.parse_args()
    
    # Initialize the trading system controller
    logger.info("Initializing enhanced multi-asset trading system...")
    logger.info(f"Enabled asset types: {', '.join(args.asset_types)}")
    controller = TradingSystemController(args.config)
    
    try:
        # Set up the system from configuration
        controller.setup_from_config()
        
        # Configure asset types
        configure_asset_types(controller, args.asset_types, logger)
        
        if args.mode == "backtest":
            run_backtest(controller, args.start_date, args.end_date, args.asset_types, logger)
        elif args.mode == "paper":
            run_paper_trading(controller, args.asset_types, logger)
        elif args.mode == "live":
            run_live_trading(controller, args.asset_types, logger)
        elif args.mode == "gui":
            run_gui_mode(controller, logger)
        
    except Exception as e:
        logger.error(f"Error in trading system: {e}", exc_info=True)
    finally:
        # Stop the system
        controller.stop()
        logger.info("Enhanced multi-asset trading system stopped")

def configure_asset_types(controller, enabled_asset_types, logger):
    """Configure the system for specific asset types."""
    logger.info("Configuring asset types...")
    
    # Get data provider and add default symbols for each asset type
    data_provider = controller.get_module("data_collection", "yahoo_finance")
    if data_provider:
        # Clear existing symbols
        data_provider.symbols = []
        
        # Add symbols based on enabled asset types
        if "stock" in enabled_asset_types:
            stock_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
            for symbol in stock_symbols:
                data_provider.add_symbol(symbol)
            logger.info(f"Added {len(stock_symbols)} stock symbols")
        
        if "crypto" in enabled_asset_types:
            crypto_symbols = ["BTC-USD", "ETH-USD", "ADA-USD", "DOT-USD"]
            for symbol in crypto_symbols:
                data_provider.add_symbol(symbol)
            logger.info(f"Added {len(crypto_symbols)} crypto symbols")
        
        if "forex" in enabled_asset_types:
            forex_symbols = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "XAUUSD=X"]
            for symbol in forex_symbols:
                data_provider.add_symbol(symbol)
            logger.info(f"Added {len(forex_symbols)} forex symbols")
    
    # Configure executor for supported asset types
    executor = controller.get_module("execution", "alpaca_executor")
    if executor:
        supported_assets = executor.get_supported_assets()
        logger.info(f"Executor supports: {supported_assets}")
        
        # Warn about unsupported asset types
        for asset_type in enabled_asset_types:
            if not supported_assets.get(asset_type, False):
                logger.warning(f"Asset type '{asset_type}' is enabled but not supported by executor")

def run_gui_mode(controller, logger):
    """Run the system with enhanced GUI interface."""
    logger.info("Starting enhanced GUI mode with multi-asset support")
    
    # Start the controller
    controller.start()
    
    # Create and run GUI
    root = tk.Tk()
    app = TradingBotGUI(root, controller)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Add window icon and styling
    try:
        root.iconname("Trading Bot")
        root.configure(bg='#f0f0f0')
    except:
        pass  # Ignore if styling fails
    
    root.mainloop()
    
    logger.info("Enhanced GUI mode stopped")

def run_backtest(controller, start_date_str, end_date_str, asset_types, logger):
    """Run the system in backtest mode with multi-asset support."""
    logger.info("Starting enhanced backtest mode")
    logger.info(f"Asset types: {', '.join(asset_types)}")
    
    # Parse dates
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    else:
        start_date = datetime.now() - timedelta(days=90)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    else:
        end_date = datetime.now()
    
    logger.info(f"Backtest period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Get modules
    data_providers = controller.get_modules_by_type("data_collection")
    level_detectors = controller.get_modules_by_type("level_identification")
    signal_generators = controller.get_modules_by_type("signal_generation")
    risk_managers = controller.get_modules_by_type("risk_management")
    executors = controller.get_modules_by_type("execution")
    monitors = controller.get_modules_by_type("monitoring")
    reporters = controller.get_modules_by_type("reporting")
    
    # Start the system
    controller.start()
    
    # Track performance by asset type
    asset_performance = {asset_type: {'trades': 0, 'pnl': 0.0} for asset_type in asset_types}
    
    # Process each trading day in the backtest period
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Skip weekends
            logger.info(f"Processing trading day: {current_date.strftime('%Y-%m-%d')}")
            
            # Fetch price data for all asset types
            price_data_by_symbol = {}
            for provider in data_providers:
                try:
                    price_data = provider.execute()
                    price_data_by_symbol.update(price_data)
                except Exception as e:
                    logger.error(f"Error fetching price data: {e}")
            
            # Filter by enabled asset types
            filtered_price_data = {}
            for symbol, data in price_data_by_symbol.items():
                if hasattr(provider, 'get_asset_type'):
                    asset_type = provider.get_asset_type(symbol)
                    if asset_type in asset_types:
                        filtered_price_data[symbol] = data
                else:
                    filtered_price_data[symbol] = data  # Default include
            
            # Identify levels for each symbol
            level_data_by_symbol = {}
            for symbol, price_data in filtered_price_data.items():
                for detector in level_detectors:
                    try:
                        level_data = detector.execute(price_data)
                        level_data_by_symbol[symbol] = level_data
                    except Exception as e:
                        logger.error(f"Error detecting levels for {symbol}: {e}")
            
            # Generate signals
            signals = []
            for generator in signal_generators:
                for symbol in filtered_price_data:
                    input_data = {
                        "price_data": filtered_price_data[symbol],
                        "level_data": level_data_by_symbol.get(symbol)
                    }
                    try:
                        new_signals = generator.execute(input_data)
                        if new_signals:
                            signals.extend(new_signals)
                    except Exception as e:
                        logger.error(f"Error generating signals for {symbol}: {e}")
            
            # Process signals by asset type
            processed_trades = 0
            for signal in signals:
                try:
                    # Calculate risk parameters
                    risk_input = {"signal": signal, "price_data": filtered_price_data[signal.symbol]}
                    risk_params = None
                    for risk_manager in risk_managers:
                        risk_params = risk_manager.execute(risk_input)
                        break  # Use first risk manager
                    
                    if not risk_params:
                        continue
                    
                    # Execute orders
                    for executor in executors:
                        exec_input = {"signal": signal, "risk_params": risk_params}
                        order = executor.execute(exec_input)
                        
                        if order and order.status in ["filled", "submitted"]:
                            # Simulate trade execution for backtest
                            asset_type = getattr(executor, '_get_asset_type', lambda x: 'stock')(signal.symbol)
                            
                            # Create trade data
                            trade = {
                                "trade_id": order.order_id,
                                "symbol": order.symbol,
                                "side": order.side,
                                "quantity": order.quantity,
                                "price": order.price,
                                "timestamp": current_date,
                                "entry_price": signal.price,
                                "asset_type": asset_type
                            }
                            
                            # Calculate P&L (simplified)
                            if len(filtered_price_data[signal.symbol].bars) > 1:
                                current_price = filtered_price_data[signal.symbol].bars[-1].close
                                entry_price = signal.price
                                
                                if signal.signal_type == SignalType.ENTRY_LONG:
                                    pnl = (current_price - entry_price) * order.quantity
                                else:
                                    pnl = (entry_price - current_price) * order.quantity
                                
                                # Update asset performance
                                if asset_type in asset_performance:
                                    asset_performance[asset_type]['trades'] += 1
                                    asset_performance[asset_type]['pnl'] += pnl
                                
                                trade['pnl'] = pnl
                            
                            # Update monitors
                            for monitor in monitors:
                                monitor.execute({"trades": [trade]})
                            
                            processed_trades += 1
                            break  # Use first executor
                    
                except Exception as e:
                    logger.error(f"Error processing signal for {signal.symbol}: {e}")
            
            if processed_trades > 0:
                logger.info(f"Processed {processed_trades} trades on {current_date.strftime('%Y-%m-%d')}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    # Generate final reports
    logger.info("Generating backtest reports...")
    for reporter in reporters:
        for monitor in monitors:
            try:
                metrics = monitor.metrics
                trades = getattr(monitor, 'trades', [])
                report_data = reporter.execute({"metrics": metrics, "trades": trades})
                if report_data and 'report_path' in report_data:
                    logger.info(f"Report saved: {report_data['report_path']}")
            except Exception as e:
                logger.error(f"Error generating report: {e}")
    
    # Log asset performance summary
    logger.info("=== BACKTEST RESULTS BY ASSET TYPE ===")
    total_pnl = 0
    total_trades = 0
    for asset_type, performance in asset_performance.items():
        trades = performance['trades']
        pnl = performance['pnl']
        total_pnl += pnl
        total_trades += trades
        avg_pnl = pnl / trades if trades > 0 else 0
        
        logger.info(f"{asset_type.upper()}: {trades} trades, ${pnl:.2f} P&L, ${avg_pnl:.2f} avg per trade")
    
    logger.info(f"TOTAL: {total_trades} trades, ${total_pnl:.2f} P&L")
    logger.info("Enhanced backtest completed")

def run_paper_trading(controller, asset_types, logger):
    """Run the system in paper trading mode with multi-asset support."""
    logger.info("Starting enhanced paper trading mode")
    logger.info(f"Asset types: {', '.join(asset_types)}")
    
    # Start the system
    controller.start()
    
    try:
        # Main trading loop
        while True:
            # Get current time
            now = datetime.now()
            
            # Check if it's trading hours (extended for global markets)
            # Stocks: 9:30 AM - 4:00 PM EST
            # Crypto: 24/7
            # Forex: 24/5 (Sunday 5 PM - Friday 5 PM EST)
            
            is_stock_hours = now.weekday() < 5 and (9 <= now.hour < 16)
            is_crypto_hours = True  # 24/7
            is_forex_hours = not (now.weekday() == 5 and now.hour >= 17) and not (now.weekday() == 6)
            
            active_markets = []
            if "stock" in asset_types and is_stock_hours:
                active_markets.append("stock")
            if "crypto" in asset_types and is_crypto_hours:
                active_markets.append("crypto")
            if "forex" in asset_types and is_forex_hours:
                active_markets.append("forex")
            
            if active_markets:
                logger.info(f"Trading active markets: {', '.join(active_markets)}")
                
                # Get data provider modules
                data_providers = controller.get_modules_by_type("data_collection")
                
                # Fetch price data
                price_data_by_symbol = {}
                for provider in data_providers:
                    try:
                        price_data = provider.execute()
                        # Filter by active markets
                        for symbol, data in price_data.items():
                            if hasattr(provider, 'get_asset_type'):
                                asset_type = provider.get_asset_type(symbol)
                                if asset_type in active_markets:
                                    price_data_by_symbol[symbol] = data
                            else:
                                price_data_by_symbol[symbol] = data
                    except Exception as e:
                        logger.error(f"Error fetching data: {e}")
                
                # Process the data through the trading pipeline
                if price_data_by_symbol:
                    process_trading_pipeline(controller, price_data_by_symbol, logger)
            else:
                logger.info("No active markets at this time")
            
            # Sleep for 5 minutes before the next iteration
            time.sleep(300)
    
    except KeyboardInterrupt:
        logger.info("Enhanced paper trading stopped by user")

def run_live_trading(controller, asset_types, logger):
    """Run the system in live trading mode with multi-asset support."""
    logger.warning("LIVE TRADING MODE - REAL MONEY AT RISK")
    logger.info(f"Asset types: {', '.join(asset_types)}")
    
    # Additional confirmation for live trading
    print("\n" + "="*50)
    print("⚠️  LIVE TRADING MODE - REAL MONEY AT RISK ⚠️")
    print("="*50)
    print(f"Asset types enabled: {', '.join(asset_types)}")
    print("This will place real orders with real money!")
    response = input("Type 'CONFIRM' to continue with live trading: ")
    
    if response != "CONFIRM":
        logger.info("Live trading cancelled by user")
        return
    
    # Start the system
    controller.start()
    
    try:
        # Main trading loop (similar to paper trading)
        while True:
            now = datetime.now()
            
            # Market hours check (same as paper trading)
            is_stock_hours = now.weekday() < 5 and (9 <= now.hour < 16)
            is_crypto_hours = True
            is_forex_hours = not (now.weekday() == 5 and now.hour >= 17) and not (now.weekday() == 6)
            
            active_markets = []
            if "stock" in asset_types and is_stock_hours:
                active_markets.append("stock")
            if "crypto" in asset_types and is_crypto_hours:
                active_markets.append("crypto")
            if "forex" in asset_types and is_forex_hours:
                active_markets.append("forex")
            
            if active_markets:
                logger.info(f"Live trading active markets: {', '.join(active_markets)}")
                
                data_providers = controller.get_modules_by_type("data_collection")
                
                price_data_by_symbol = {}
                for provider in data_providers:
                    try:
                        price_data = provider.execute()
                        for symbol, data in price_data.items():
                            if hasattr(provider, 'get_asset_type'):
                                asset_type = provider.get_asset_type(symbol)
                                if asset_type in active_markets:
                                    price_data_by_symbol[symbol] = data
                            else:
                                price_data_by_symbol[symbol] = data
                    except Exception as e:
                        logger.error(f"Error fetching data: {e}")
                
                if price_data_by_symbol:
                    process_trading_pipeline(controller, price_data_by_symbol, logger)
            
            time.sleep(300)  # 5 minute intervals
    
    except KeyboardInterrupt:
        logger.info("Live trading stopped by user")

def process_trading_pipeline(controller, price_data_by_symbol, logger):
    """Process the enhanced trading pipeline with multi-asset support."""
    
    # Get modules by type
    level_detectors = controller.get_modules_by_type("level_identification")
    signal_generators = controller.get_modules_by_type("signal_generation")
    risk_managers = controller.get_modules_by_type("risk_management")
    executors = controller.get_modules_by_type("execution")
    monitors = controller.get_modules_by_type("monitoring")
    
    # Identify levels
    level_data_by_symbol = {}
    for symbol, price_data in price_data_by_symbol.items():
        for detector in level_detectors:
            try:
                level_data = detector.execute(price_data)
                level_data_by_symbol[symbol] = level_data
            except Exception as e:
                logger.error(f"Error detecting levels for {symbol}: {e}")
    
    # Generate signals
    signals = []
    for generator in signal_generators:
        for symbol in price_data_by_symbol:
            input_data = {
                "price_data": price_data_by_symbol[symbol],
                "level_data": level_data_by_symbol.get(symbol)
            }
            try:
                new_signals = generator.execute(input_data)
                if new_signals:
                    signals.extend(new_signals)
            except Exception as e:
                logger.error(f"Error generating signals for {symbol}: {e}")
    
    # Process signals
    for signal in signals:
        try:
            # Determine asset type
            asset_type = signal.metadata.get('asset_type', 'stock')
            
            logger.info(f"Processing {asset_type.upper()} signal: {signal.signal_type.value} for {signal.symbol} at {signal.price}")
            
            # Calculate risk parameters
            risk_input = {"signal": signal, "price_data": price_data_by_symbol[signal.symbol]}
            risk_params = None
            for risk_manager in risk_managers:
                risk_params = risk_manager.execute(risk_input)
                break  # Use first risk manager
            
            if risk_params and risk_params.validate():
                logger.info(f"Risk parameters for {signal.symbol}: pos_size={risk_params.position_size}, "
                           f"stop={risk_params.stop_loss_price}, tp={risk_params.take_profit_price}")
                
                # Execute orders
                for executor in executors:
                    # Check if executor supports this asset type
                    if hasattr(executor, 'get_supported_assets'):
                        supported = executor.get_supported_assets()
                        if not supported.get(asset_type, False):
                            logger.warning(f"Executor does not support {asset_type} - skipping {signal.symbol}")
                            continue
                    
                    exec_input = {"signal": signal, "risk_params": risk_params}
                    order = executor.execute(exec_input)
                    
                    if order:
                        logger.info(f"Order executed: {order.order_id} - {order.side.value} "
                                   f"{order.quantity} {order.symbol} @ {order.price} ({asset_type.upper()})")
                        
                        # Update monitors
                        for monitor in monitors:
                            monitor.execute({"orders": [order]})
                        break  # Use first successful executor
                    else:
                        logger.warning(f"Failed to execute order for {signal.symbol}")
            else:
                logger.warning(f"Invalid risk parameters for {signal.symbol}")
                
        except Exception as e:
            logger.error(f"Error processing signal for {signal.symbol}: {e}")

if __name__ == "__main__":
    main()