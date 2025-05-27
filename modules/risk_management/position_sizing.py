# modules/risk_management/position_sizing.py
from typing import Any, Dict, Optional

from core.interfaces import IModule
from core.models import SignalData, RiskParameters, SignalType

class RiskManager(IModule):
    """Enhanced risk management module for position sizing and stop placement with multi-asset support."""
    
    def __init__(self, module_id: Optional[str] = "risk_manager"):
        super().__init__(module_id=module_id)
        self.account_size = 10000.0
        self.risk_per_trade = 0.01  # 1%
        self.max_position_size = 0.1  # 10% of account
        self.stop_multiplier = 1.5  # ATR multiplier for stop placement
        self.target_rr_ratio = 2.0  # Risk-reward ratio
        
        # Asset-specific risk parameters
        self.asset_configs = {
            'stock': {
                'risk_per_trade': 0.01,  # 1%
                'max_position_size': 0.1,  # 10%
                'stop_multiplier': 1.5,
                'target_rr_ratio': 2.0,
                'min_price': 0.01
            },
            'crypto': {
                'risk_per_trade': 0.005,  # 0.5% (lower due to volatility)
                'max_position_size': 0.05,  # 5%
                'stop_multiplier': 2.0,  # Higher due to volatility
                'target_rr_ratio': 2.5,
                'min_price': 0.000001
            },
            'forex': {
                'risk_per_trade': 0.015,  # 1.5%
                'max_position_size': 0.15,  # 15% (leverage available)
                'stop_multiplier': 1.0,  # Tighter stops
                'target_rr_ratio': 1.5,
                'min_price': 0.00001
            }
        }
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the risk manager.
        
        Args:
            config: Configuration dictionary with the following options:
                - account_size: Current account size
                - risk_per_trade: Maximum risk per trade as a percentage of account
                - max_position_size: Maximum position size as a percentage of account
                - stop_multiplier: ATR multiplier for stop placement
                - target_rr_ratio: Target risk-reward ratio
        """
        self.account_size = config.get("account_size", 10000.0)
        self.risk_per_trade = config.get("risk_per_trade", 0.01)
        self.max_position_size = config.get("max_position_size", 0.1)
        self.stop_multiplier = config.get("stop_multiplier", 1.5)
        self.target_rr_ratio = config.get("target_rr_ratio", 2.0)
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> RiskParameters:
        """Calculate position size and stop levels with multi-asset support.
        
        Args:
            input_data: Dictionary containing:
                - "signal": SignalData object
                - "price_data": PriceData object
                - "level_data": LevelData object
            
        Returns:
            RiskParameters object
        """
        signal = input_data.get("signal")
        price_data = input_data.get("price_data")
        level_data = input_data.get("level_data")
        
        if not signal or not price_data or not price_data.bars:
            return None
        
        # Determine asset type
        asset_type = signal.metadata.get("asset_type", self._detect_asset_type(signal.symbol))
        
        # Get asset-specific configuration
        asset_config = self.asset_configs.get(asset_type, self.asset_configs['stock'])
        
        # Calculate ATR (Average True Range) for volatility-based stops
        bars = price_data.bars
        if len(bars) < 14:
            atr = abs(bars[-1].high - bars[-1].low)  # Fallback if not enough data
        else:
            true_ranges = []
            for i in range(-14, 0):
                high_low = bars[i].high - bars[i].low
                if i > -14:
                    high_close = abs(bars[i].high - bars[i-1].close)
                    low_close = abs(bars[i].low - bars[i-1].close)
                    true_ranges.append(max(high_low, high_close, low_close))
                else:
                    true_ranges.append(high_low)
            atr = sum(true_ranges) / len(true_ranges)
        
        # Adjust ATR based on asset type
        atr_multiplier = asset_config['stop_multiplier']
        
        # Find appropriate stop loss level
        stop_loss_price = 0.0
        
        if signal.signal_type == SignalType.ENTRY_LONG:
            # For long, set stop below the entry
            stop_distance = atr * atr_multiplier
            
            # Check if the signal is from a level breakout
            level_price = signal.metadata.get("level_price")
            if level_price and signal.metadata.get("level_type") == "resistance":
                # Place stop below the broken resistance level
                stop_loss_price = min(signal.price - stop_distance, level_price * 0.99)
            else:
                # Place stop based on ATR
                stop_loss_price = signal.price - stop_distance
            
            # Ensure stop is not too close to current price for crypto/forex
            min_stop_distance = signal.price * 0.02 if asset_type == 'crypto' else signal.price * 0.01
            if signal.price - stop_loss_price < min_stop_distance:
                stop_loss_price = signal.price - min_stop_distance
            
        elif signal.signal_type == SignalType.ENTRY_SHORT:
            # For short, set stop above the entry
            stop_distance = atr * atr_multiplier
            
            # Check if the signal is from a level breakout
            level_price = signal.metadata.get("level_price")
            if level_price and signal.metadata.get("level_type") == "support":
                # Place stop above the broken support level
                stop_loss_price = max(signal.price + stop_distance, level_price * 1.01)
            else:
                # Place stop based on ATR
                stop_loss_price = signal.price + stop_distance
            
            # Ensure stop is not too close to current price
            min_stop_distance = signal.price * 0.02 if asset_type == 'crypto' else signal.price * 0.01
            if stop_loss_price - signal.price < min_stop_distance:
                stop_loss_price = signal.price + min_stop_distance
        
        # Calculate position size based on risk and asset type
        risk_amount = self.account_size * asset_config['risk_per_trade']
        price_risk = abs(signal.price - stop_loss_price)
        
        if price_risk <= 0:
            position_size = 0
        else:
            position_size = risk_amount / price_risk
        
        # Apply asset-specific position size limits
        max_size = self.account_size * asset_config['max_position_size']
        
        # Convert to appropriate units based on asset type
        if asset_type == 'crypto':
            # For crypto, position_size is already in dollar amount
            position_size = min(position_size, max_size)
        elif asset_type == 'forex':
            # For forex, convert to lot size (typically 1000 units = 1 micro lot)
            max_lot_size = max_size / signal.price
            position_size = min(position_size, max_lot_size)
            # Round to nearest micro lot
            position_size = round(position_size / 1000) * 1000
        else:
            # For stocks, convert to share count
            max_shares = max_size / signal.price
            position_size = min(position_size / signal.price, max_shares)
            # Round down to whole shares
            position_size = int(position_size) * signal.price
        
        # Ensure minimum position size
        min_position = asset_config.get('min_position', 10.0)  # Minimum $10 position
        if position_size < min_position:
            position_size = 0  # Skip if position too small
        
        # Calculate take profit based on risk-reward ratio
        take_profit_price = 0.0
        rr_ratio = asset_config['target_rr_ratio']
        
        if signal.signal_type == SignalType.ENTRY_LONG:
            take_profit_price = signal.price + (price_risk * rr_ratio)
        elif signal.signal_type == SignalType.ENTRY_SHORT:
            take_profit_price = signal.price - (price_risk * rr_ratio)
        
        # Apply minimum price constraints
        min_price = asset_config['min_price']
        if stop_loss_price < min_price:
            stop_loss_price = min_price
        if take_profit_price < min_price:
            take_profit_price = min_price
        
        # Return risk parameters
        return RiskParameters(
            position_size=position_size,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            trailing_stop=True,
            trailing_stop_distance=atr,
            max_drawdown=asset_config['risk_per_trade'] * 5  # 5x single trade risk
        )
    
    def _detect_asset_type(self, symbol: str) -> str:
        """Detect asset type from symbol format."""
        symbol_upper = symbol.upper()
        
        # Crypto patterns
        if symbol_upper.endswith('-USD') or symbol_upper.endswith('USD'):
            return 'crypto'
        if symbol_upper in ['BTC', 'ETH', 'ADA', 'DOT', 'LINK', 'LTC', 'XRP', 'DOGE', 'MATIC', 'SOL']:
            return 'crypto'
        
        # Forex patterns
        if '=' in symbol or len(symbol) == 6 and not any(char.isdigit() for char in symbol):
            return 'forex'
        if symbol_upper.endswith('=X'):
            return 'forex'
        
        # Default to stock
        return 'stock'
    
    def update_account_size(self, new_size: float) -> None:
        """Update account size for position sizing calculations."""
        self.account_size = max(new_size, 1000.0)  # Minimum $1000
    
    def get_risk_summary(self, asset_type: str = None) -> Dict[str, Any]:
        """Get risk management summary for asset type."""
        if asset_type and asset_type in self.asset_configs:
            config = self.asset_configs[asset_type]
            return {
                'asset_type': asset_type,
                'risk_per_trade': config['risk_per_trade'] * 100,  # Convert to percentage
                'max_position_size': config['max_position_size'] * 100,
                'stop_multiplier': config['stop_multiplier'],
                'target_rr_ratio': config['target_rr_ratio'],
                'max_risk_amount': self.account_size * config['risk_per_trade']
            }
        else:
            # Return summary for all asset types
            summary = {}
            for asset_type, config in self.asset_configs.items():
                summary[asset_type] = {
                    'risk_per_trade': config['risk_per_trade'] * 100,
                    'max_position_size': config['max_position_size'] * 100,
                    'stop_multiplier': config['stop_multiplier'],
                    'target_rr_ratio': config['target_rr_ratio'],
                    'max_risk_amount': self.account_size * config['risk_per_trade']
                }
            return summary
    
    def validate_trade_size(self, symbol: str, position_size: float, price: float) -> bool:
        """Validate if trade size is within risk limits."""
        asset_type = self._detect_asset_type(symbol)
        config = self.asset_configs[asset_type]
        
        # Calculate position value
        if asset_type == 'forex':
            position_value = position_size * price / 1000  # Convert lots to dollar value
        else:
            position_value = position_size * price if asset_type == 'stock' else position_size
        
        max_position_value = self.account_size * config['max_position_size']
        
        return position_value <= max_position_value
    
    def calculate_max_loss(self, symbol: str, position_size: float, entry_price: float, stop_price: float) -> float:
        """Calculate maximum potential loss for a trade."""
        asset_type = self._detect_asset_type(symbol)
        
        if asset_type == 'forex':
            # For forex, position_size is in lots
            pip_value = position_size / 1000 * 0.0001  # Approximate pip value
            pip_distance = abs(entry_price - stop_price) / 0.0001
            max_loss = pip_distance * pip_value
        else:
            # For stocks and crypto
            price_diff = abs(entry_price - stop_price)
            if asset_type == 'stock':
                shares = position_size / entry_price
                max_loss = shares * price_diff
            else:  # crypto
                max_loss = position_size * (price_diff / entry_price)
        
        return max_loss
    
    def adjust_position_for_correlation(self, symbol: str, position_size: float, existing_positions: list) -> float:
        """Adjust position size based on correlation with existing positions."""
        asset_type = self._detect_asset_type(symbol)
        
        # Simple correlation adjustment - reduce position if too many similar assets
        same_type_count = sum(1 for pos in existing_positions 
                             if self._detect_asset_type(pos.get('symbol', '')) == asset_type)
        
        if same_type_count >= 3:  # If 3+ positions of same type
            correlation_factor = 0.8  # Reduce by 20%
            position_size *= correlation_factor
        
        return position_size