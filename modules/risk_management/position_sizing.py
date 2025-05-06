# modules/risk_management/position_sizing.py
from typing import Any, Dict, Optional

from core.interfaces import IModule
from core.models import SignalData, RiskParameters

class RiskManager(IModule):
    """Risk management module for position sizing and stop placement."""
    
    def __init__(self, module_id: Optional[str] = "risk_manager"):
        super().__init__(module_id=module_id)
        self.account_size = 10000.0
        self.risk_per_trade = 0.01  # 1%
        self.max_position_size = 0.1  # 10% of account
        self.stop_multiplier = 1.5  # ATR multiplier for stop placement
        self.target_rr_ratio = 2.0  # Risk-reward ratio
        
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
        """Calculate position size and stop levels.
        
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
        
        # Find appropriate stop loss level
        stop_loss_price = 0.0
        
        if signal.signal_type == SignalType.ENTRY_LONG:
            # For long, set stop below the entry
            stop_distance = atr * self.stop_multiplier
            
            # Check if the signal is from a level breakout
            level_price = signal.metadata.get("level_price")
            if level_price and signal.metadata.get("level_type") == "resistance":
                # Place stop below the broken resistance level
                stop_loss_price = min(signal.price - stop_distance, level_price * 0.99)
            else:
                # Place stop based on ATR
                stop_loss_price = signal.price - stop_distance
            
        elif signal.signal_type == SignalType.ENTRY_SHORT:
            # For short, set stop above the entry
            stop_distance = atr * self.stop_multiplier
            
            # Check if the signal is from a level breakout
            level_price = signal.metadata.get("level_price")
            if level_price and signal.metadata.get("level_type") == "support":
                # Place stop above the broken support level
                stop_loss_price = max(signal.price + stop_distance, level_price * 1.01)
            else:
                # Place stop based on ATR
                stop_loss_price = signal.price + stop_distance
        
        # Calculate position size based on risk
        risk_amount = self.account_size * self.risk_per_trade
        price_risk = abs(signal.price - stop_loss_price)
        
        if price_risk <= 0:
            position_size = 0
        else:
            position_size = risk_amount / price_risk
        
        # Limit position size
        max_size = self.account_size * self.max_position_size / signal.price
        position_size = min(position_size, max_size)
        
        # Calculate take profit based on risk-reward ratio
        take_profit_price = 0.0
        if signal.signal_type == SignalType.ENTRY_LONG:
            take_profit_price = signal.price + (price_risk * self.target_rr_ratio)
        elif signal.signal_type == SignalType.ENTRY_SHORT:
            take_profit_price = signal.price - (price_risk * self.target_rr_ratio)
        
        # Return risk parameters
        return RiskParameters(
            position_size=position_size,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            trailing_stop=True,
            trailing_stop_distance=atr
        )