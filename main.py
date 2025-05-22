# main.py
import os
import argparse
import logging
from datetime import datetime, timedelta
import time
import yaml

from core.controller import TradingSystemController
from core.models import PriceData, SignalType

def setup_logging():
    """Set up logging configuration."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"trading_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
def main():
    """Main entry point for the trading system."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger("main")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Modular Trading System")
    parser.add_argument("--config", type=str, default="config/system_config.yaml",
                       help="Path to system configuration file")
    parser.add_argument("--mode", type=str, choices=["backtest", "paper", "live"], default="backtest",
                       help="Trading mode")
    parser.add_argument("--start_date", type=str, default=None,
                       help="Start date for backtest (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default=None,
                       help="End date for backtest (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Initialize the trading system controller
    logger.info("Initializing trading system...")
    controller = TradingSystemController(args.config)
    
    try:
        # Set up the system from configuration
        controller.setup_from_config()
        
        if args.mode == "backtest":
            run_backtest(controller, args.start_date, args.end_date)
        elif args.mode == "paper":
            run_paper_trading(controller)
        elif args.mode == "live":
            run_live_trading(controller)
        
    except Exception as e:
        logger.error(f"Error in trading system: {e}", exc_info=True)
    finally:
        # Stop the system
        controller.stop()
        logger.info("Trading system stopped")

def run_backtest(controller, start_date_str, end_date_str):
    """Run the system in backtest mode."""
    logger = logging.getLogger("backtest")
    logger.info("Starting backtest mode")
    
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
    
    # Get data provider modules
    data_providers = controller.get_modules_by_type("data_collection")
    level_detectors = controller.get_modules_by_type("level_identification")
    signal_generators = controller.get_modules_by_type("signal_generation")
    risk_managers = controller.get_modules_by_type("risk_management")
    executors = controller.get_modules_by_type("execution")
    monitors = controller.get_modules_by_type("monitoring")
    reporters = controller.get_modules_by_type("reporting")
    
    # Start the system
    controller.start()
    
    # Process each trading day in the backtest period
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Skip weekends
            logger.info(f"Processing trading day: {current_date.strftime('%Y-%m-%d')}")
            
            # Fetch price data
            price_data_by_symbol = {}
            for provider in data_providers:
                price_data = provider.execute()
                price_data_by_symbol.update(price_data)
            
            # Identify levels
            level_data_by_symbol = {}
            for symbol, price_data in price_data_by_symbol.items():
                for detector in level_detectors:
                    level_data = detector.execute(price_data)
                    level_data_by_symbol[symbol] = level_data
            
            # Generate signals
            signals = []
            for generator in signal_generators:
                for symbol in price_data_by_symbol:
                    input_data = {
                        "price_data": price_data_by_symbol[symbol],
                        "level_data": level_data_by_symbol.get(symbol)
                    }
                    new_signals = generator.execute(input_data)
                    if new_signals:
                        signals.extend(new_signals)
            
            # Process signals
            for signal in signals:
                # Calculate risk parameters
                risk_input = {"signal": signal, "price_data": price_data_by_symbol[signal.symbol]}
                for risk_manager in risk_managers:
                    risk_params = risk_manager.execute(risk_input)
                
                # Execute orders
                for executor in executors:
                    exec_input = {"signal": signal, "risk_params": risk_params}
                    order = executor.execute(exec_input)
                    
                    # Simulate trade execution for backtest
                    if order and order.status == "filled":
                        # Create trade data from order
                        trade = {
                            "trade_id": order.order_id,
                            "symbol": order.symbol,
                            "side": order.side,
                            "quantity": order.quantity,
                            "price": order.price,
                            "timestamp": current_date,
                            "entry_price": signal.price
                        }
                        
                        # Update monitors
                        for monitor in monitors:
                            monitor.execute({"trades": [trade]})
            
            # Generate reports at end of backtest
            if current_date == end_date:
                for reporter in reporters:
                    for monitor in monitors:
                        metrics = monitor.metrics
                        trades = monitor.trades
                        reporter.execute({"metrics": metrics, "trades": trades})
        
        # Move to next day
        current_date += timedelta(days=1)
    
    logger.info("Backtest completed")

def run_paper_trading(controller):
    """Run the system in paper trading mode."""
    logger = logging.getLogger("paper_trading")
    logger.info("Starting paper trading mode")
    
    # Start the system
    controller.start()
    
    try:
        # Main trading loop
        while True:
            # Get current time
            now = datetime.now()
            
            # Check if it's trading hours (9:30 AM - 4:00 PM EST on weekdays)
            if now.weekday() < 5 and (9 <= now.hour < 16 or (now.hour == 16 and now.minute == 0)):
                # Get data provider modules
                data_providers = controller.get_modules_by_type("data_collection")
                
                # Fetch price data
                price_data_by_symbol = {}
                for provider in data_providers:
                    price_data = provider.execute()
                    price_data_by_symbol.update(price_data)
                
                # Process the data through the trading pipeline
                process_trading_pipeline(controller, price_data_by_symbol)
            
            # Sleep for 5 minutes before the next iteration
            time.sleep(300)
    
    except KeyboardInterrupt:
        logger.info("Paper trading stopped by user")

def run_live_trading(controller):
    """Run the system in live trading mode."""
    logger = logging.getLogger("live_trading")
    logger.info("Starting live trading mode")
    
    # Start the system
    controller.start()
    
    try:
        # Main trading loop
        while True:
            # Get current time
            now = datetime.now()
            
            # Check if it's trading hours (9:30 AM - 4:00 PM EST on weekdays)
            if now.weekday() < 5 and (9 <= now.hour < 16 or (now.hour == 16 and now.minute == 0)):
                # Get data provider modules
                data_providers = controller.get_modules_by_type("data_collection")
                
                # Fetch price data
                price_data_by_symbol = {}
                for provider in data_providers:
                    price_data = provider.execute()
                    price_data_by_symbol.update(price_data)
                
                # Process the data through the trading pipeline
                process_trading_pipeline(controller, price_data_by_symbol)
            
            # Sleep for 5 minutes before the next iteration
            time.sleep(300)
    
    except KeyboardInterrupt:
        logger.info("Live trading stopped by user")

def process_trading_pipeline(controller, price_data_by_symbol):
    """Process the trading pipeline with the given price data."""
    logger = logging.getLogger("pipeline")
    
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
            level_data = detector.execute(price_data)
            level_data_by_symbol[symbol] = level_data
    
    # Generate signals
    signals = []
    for generator in signal_generators:
        for symbol in price_data_by_symbol:
            input_data = {
                "price_data": price_data_by_symbol[symbol],
                "level_data": level_data_by_symbol.get(symbol)
            }
            new_signals = generator.execute(input_data)
            if new_signals:
                signals.extend(new_signals)
    
    # Process signals
    for signal in signals:
        logger.info(f"Processing signal: {signal.signal_type.value} for {signal.symbol} at {signal.price}")
        
        # Calculate risk parameters
        risk_input = {"signal": signal, "price_data": price_data_by_symbol[signal.symbol]}
        risk_params = None
        for risk_manager in risk_managers:
            risk_params = risk_manager.execute(risk_input)
        
        if risk_params:
            logger.info(f"Risk parameters: pos_size={risk_params.position_size}, "
                        f"stop={risk_params.stop_loss_price}, tp={risk_params.take_profit_price}")
            
            # Execute orders
            for executor in executors:
                exec_input = {"signal": signal, "risk_params": risk_params}
                order = executor.execute(exec_input)
                
                if order:
                    logger.info(f"Order executed: {order.order_id} - {order.side.value} "
                                f"{order.quantity} {order.symbol} @ {order.price}")
                    
                    # Update monitors
                    for monitor in monitors:
                        monitor.execute({"orders": [order]})
def run_gui_mode(controller):
    """Run the system with GUI interface."""
    logger = logging.getLogger("gui_mode")
    logger.info("Starting GUI mode")
    
    # Start the controller
    controller.start()
    
    # Create and run GUI
    root = tk.Tk()
    app = TradingBotGUI(root, controller)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
    
    logger.info("GUI mode stopped")



if __name__ == "__main__":
    main()