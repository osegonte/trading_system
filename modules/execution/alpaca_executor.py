import alpaca_trade_api as tradeapi
from datetime import datetime
from typing import Any, Dict, Optional, List
import json

from core.interfaces import IModule
from core.models import SignalData, RiskParameters, OrderData, OrderType, OrderSide, TimeInForce

class AlpacaExecutor(IModule):
    """Alpaca-based order executor with live trading capabilities."""
    
    def __init__(self, module_id: Optional[str] = "alpaca_executor"):
        super().__init__(module_id=module_id)
        self.api = None
        self.api_key = ""
        self.secret_key = ""
        self.base_url = "https://paper-api.alpaca.markets"  # Paper trading by default
        self._orders = []
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the Alpaca executor."""
        self.api_key = config.get("api_key", "")
        self.secret_key = config.get("secret_key", "")
        self.base_url = config.get("base_url", "https://paper-api.alpaca.markets")
        
        # Initialize Alpaca API
        if self.api_key and self.secret_key:
            self.api = tradeapi.REST(
                self.api_key, 
                self.secret_key, 
                self.base_url, 
                api_version="v2"
            )
        
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> OrderData:
        """Execute order via Alpaca API."""
        signal = input_data.get("signal")
        risk_params = input_data.get("risk_params")
        
        if not signal or not risk_params or not self.api:
            return None
        
        try:
            # Get current price
            current_price = self.get_latest_price(signal.symbol)
            if current_price <= 0:
                return None
            
            # Determine order parameters
            side = "buy" if signal.signal_type.value == "entry_long" else "sell"
            qty = int(risk_params.position_size)
            
            if qty <= 0:
                return None
            
            # Submit market order
            alpaca_order = self.api.submit_order(
                symbol=signal.symbol,
                qty=qty,
                side=side,
                type="market",
                time_in_force="gtc"
            )
            
            # Create order data
            order = OrderData(
                order_id=alpaca_order.id,
                symbol=signal.symbol,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                quantity=qty,
                price=current_price,
                created_at=datetime.now(),
                signal_id=signal.signal_id,
                status="submitted"
            )
            
            self._orders.append(order)
            return order
            
        except Exception as e:
            print(f"Error executing order: {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> float:
        """Get latest price for a symbol."""
        try:
            return float(self.api.get_latest_trade(symbol).price)
        except:
            return -1
    
    def place_limit_order(self, symbol: str, qty: float, limit_price: float, side: str = "buy") -> dict:
        """Place a limit order."""
        try:
            return self.api.submit_order(
                symbol=symbol,
                qty=int(qty),
                side=side,
                type="limit",
                time_in_force="gtc",
                limit_price=limit_price
            )
        except Exception as e:
            print(f"Error placing limit order: {e}")
            return None
    
    def list_open_orders(self) -> list:
        """Get all open orders."""
        try:
            return self.api.list_orders(status="open")
        except:
            return []
    
    def list_positions(self) -> list:
        """Get all positions."""
        try:
            return self.api.list_positions()
        except:
            return []
    
    def cancel_all_orders(self) -> None:
        """Cancel all open orders."""
        try:
            self.api.cancel_all_orders()
        except Exception as e:
            print(f"Error canceling orders: {e}")