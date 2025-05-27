import alpaca_trade_api as tradeapi
from datetime import datetime
from typing import Any, Dict, Optional, List
import json
import logging

from core.interfaces import IModule
from core.models import SignalData, RiskParameters, OrderData, OrderType, OrderSide, TimeInForce, SignalType

class AlpacaExecutor(IModule):
    """Enhanced Alpaca-based order executor with multi-asset trading capabilities."""
    
    def __init__(self, module_id: Optional[str] = "alpaca_executor"):
        super().__init__(module_id=module_id)
        self.api = None
        self.crypto_api = None
        self.api_key = ""
        self.secret_key = ""
        self.base_url = "https://paper-api.alpaca.markets"  # Paper trading by default
        self._orders = []
        self.logger = logging.getLogger(f"AlpacaExecutor.{module_id}")
        self.supported_assets = {
            'stocks': True,
            'crypto': False,  # Requires Alpaca Crypto
            'forex': False   # Not supported by Alpaca
        }
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the Alpaca executor."""
        self.api_key = config.get("api_key", "")
        self.secret_key = config.get("secret_key", "")
        self.base_url = config.get("base_url", "https://paper-api.alpaca.markets")
        
        # Initialize Alpaca API
        if self.api_key and self.secret_key:
            try:
                self.api = tradeapi.REST(
                    self.api_key, 
                    self.secret_key, 
                    self.base_url, 
                    api_version="v2"
                )
                
                # Test connection
                account = self.api.get_account()
                self.logger.info(f"Connected to Alpaca - Account: {account.id}")
                
                # Check if crypto is available
                try:
                    # Try to initialize crypto API
                    self.crypto_api = tradeapi.REST(
                        self.api_key,
                        self.secret_key,
                        self.base_url,
                        api_version="v2"
                    )
                    self.supported_assets['crypto'] = True
                    self.logger.info("Crypto trading enabled")
                except Exception as e:
                    self.logger.warning(f"Crypto trading not available: {e}")
                    
            except Exception as e:
                self.logger.error(f"Failed to connect to Alpaca: {e}")
        
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> OrderData:
        """Execute order via Alpaca API."""
        signal = input_data.get("signal")
        risk_params = input_data.get("risk_params")
        
        if not signal or not risk_params or not self.api:
            return None
        
        # Determine asset type
        asset_type = self._get_asset_type(signal.symbol)
        
        if not self._is_asset_supported(asset_type):
            self.logger.error(f"Asset type {asset_type} not supported for {signal.symbol}")
            return None
        
        try:
            # Get current price
            current_price = self.get_latest_price(signal.symbol)
            if current_price <= 0:
                self.logger.error(f"Could not get valid price for {signal.symbol}")
                return None
            
            # Determine order parameters
            side = "buy" if signal.signal_type == SignalType.ENTRY_LONG else "sell"
            
            # Calculate quantity based on asset type
            qty = self._calculate_quantity(signal.symbol, risk_params.position_size, current_price, asset_type)
            
            if qty <= 0:
                self.logger.error(f"Invalid quantity calculated: {qty}")
                return None
            
            # Choose appropriate API based on asset type
            api_to_use = self.crypto_api if asset_type == 'crypto' and self.crypto_api else self.api
            
            # Submit market order
            order_params = {
                "symbol": self._format_symbol_for_alpaca(signal.symbol, asset_type),
                "qty": qty,
                "side": side,
                "type": "market",
                "time_in_force": "gtc"
            }
            
            # Add additional parameters for crypto
            if asset_type == 'crypto':
                order_params["time_in_force"] = "ioc"  # Immediate or cancel for crypto
            
            alpaca_order = api_to_use.submit_order(**order_params)
            
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
            self.logger.info(f"Order submitted: {order.order_id} - {side} {qty} {signal.symbol}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error executing order for {signal.symbol}: {e}")
            return None
    
    def _get_asset_type(self, symbol: str) -> str:
        """Determine asset type from symbol."""
        symbol_upper = symbol.upper()
        
        # Crypto patterns
        if symbol_upper.endswith('-USD') or symbol_upper.endswith('USD'):
            return 'crypto'
        if symbol_upper in ['BTC', 'ETH', 'ADA', 'DOT', 'LINK', 'LTC', 'XRP', 'DOGE', 'MATIC', 'SOL']:
            return 'crypto'
        
        # Forex patterns (not supported by Alpaca)
        if '=' in symbol or len(symbol) == 6 and not any(char.isdigit() for char in symbol):
            return 'forex'
        if symbol_upper.endswith('=X'):
            return 'forex'
        
        # Default to stock
        return 'stock'
    
    def _is_asset_supported(self, asset_type: str) -> bool:
        """Check if asset type is supported."""
        return self.supported_assets.get(asset_type, False)
    
    def _format_symbol_for_alpaca(self, symbol: str, asset_type: str) -> str:
        """Format symbol for Alpaca API."""
        if asset_type == 'crypto':
            # Alpaca uses different crypto symbol format
            if symbol.endswith('-USD'):
                return symbol.replace('-', '/')  # BTC-USD -> BTC/USD
            elif not '/' in symbol:
                return f"{symbol}/USD"
        
        return symbol
    
    def _calculate_quantity(self, symbol: str, position_size: float, current_price: float, asset_type: str) -> float:
        """Calculate appropriate quantity based on asset type."""
        if asset_type == 'crypto':
            # For crypto, position_size is the dollar amount, return the crypto quantity
            return round(position_size / current_price, 8)  # 8 decimal places for crypto
        elif asset_type == 'forex':
            # Forex typically traded in lots
            return int(position_size / 1000) * 1000  # Round to nearest 1000 (micro lot)
        else:
            # For stocks, return whole shares
            return int(position_size / current_price)
    
    def get_latest_price(self, symbol: str) -> float:
        """Get latest price for a symbol."""
        try:
            asset_type = self._get_asset_type(symbol)
            formatted_symbol = self._format_symbol_for_alpaca(symbol, asset_type)
            
            # Choose appropriate API
            api_to_use = self.crypto_api if asset_type == 'crypto' and self.crypto_api else self.api
            
            if asset_type == 'crypto':
                # Get crypto quote
                quote = api_to_use.get_latest_crypto_quote(formatted_symbol)
                return float(quote.bid_price) if quote else -1
            else:
                # Get stock quote
                trade = api_to_use.get_latest_trade(formatted_symbol)
                return float(trade.price) if trade else -1
                
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return -1
    
    def place_limit_order(self, symbol: str, qty: float, limit_price: float, side: str = "buy") -> dict:
        """Place a limit order."""
        try:
            asset_type = self._get_asset_type(symbol)
            
            if not self._is_asset_supported(asset_type):
                self.logger.error(f"Asset type {asset_type} not supported for {symbol}")
                return None
            
            formatted_symbol = self._format_symbol_for_alpaca(symbol, asset_type)
            api_to_use = self.crypto_api if asset_type == 'crypto' and self.crypto_api else self.api
            
            order_params = {
                "symbol": formatted_symbol,
                "qty": self._calculate_quantity(symbol, qty * limit_price, limit_price, asset_type),
                "side": side,
                "type": "limit",
                "time_in_force": "gtc",
                "limit_price": limit_price
            }
            
            if asset_type == 'crypto':
                order_params["time_in_force"] = "gtc"  # Good till cancel for crypto limits
            
            return api_to_use.submit_order(**order_params)
            
        except Exception as e:
            self.logger.error(f"Error placing limit order for {symbol}: {e}")
            return None
    
    def list_open_orders(self) -> list:
        """Get all open orders."""
        try:
            orders = []
            
            # Get stock orders
            if self.api:
                stock_orders = self.api.list_orders(status="open")
                orders.extend(stock_orders)
            
            # Get crypto orders if available
            if self.crypto_api:
                try:
                    crypto_orders = self.crypto_api.list_orders(status="open")
                    orders.extend(crypto_orders)
                except:
                    pass  # Crypto orders might not be available
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Error listing open orders: {e}")
            return []
    
    def list_positions(self) -> list:
        """Get all positions."""
        try:
            positions = []
            
            # Get stock positions
            if self.api:
                stock_positions = self.api.list_positions()
                positions.extend(stock_positions)
            
            # Get crypto positions if available
            if self.crypto_api:
                try:
                    crypto_positions = self.crypto_api.list_positions()
                    positions.extend(crypto_positions)
                except:
                    pass  # Crypto positions might not be available
            
            return positions
            
        except Exception as e:
            self.logger.error(f"Error listing positions: {e}")
            return []
    
    def cancel_all_orders(self) -> None:
        """Cancel all open orders."""
        try:
            # Cancel stock orders
            if self.api:
                self.api.cancel_all_orders()
                self.logger.info("Cancelled all stock orders")
            
            # Cancel crypto orders if available
            if self.crypto_api:
                try:
                    self.crypto_api.cancel_all_orders()
                    self.logger.info("Cancelled all crypto orders")
                except:
                    pass  # Crypto orders might not be available
                    
        except Exception as e:
            self.logger.error(f"Error canceling orders: {e}")
    
    def get_account_info(self) -> dict:
        """Get account information."""
        try:
            if self.api:
                account = self.api.get_account()
                return {
                    'buying_power': float(account.buying_power),
                    'portfolio_value': float(account.portfolio_value),
                    'cash': float(account.cash),
                    'day_trade_count': int(account.day_trade_count),
                    'trading_blocked': account.trading_blocked
                }
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
        
        return {}
    
    def get_supported_assets(self) -> Dict[str, bool]:
        """Get supported asset types."""
        return self.supported_assets.copy()