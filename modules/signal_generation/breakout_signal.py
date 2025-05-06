# modules/signal_generation/breakout_signal.py
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.interfaces import IModule
from core.models import PriceData, LevelData, SignalData, SignalType

class BreakoutSignalGenerator(IModule):
    """Generates breakout signals based on price levels."""
    
    def __init__(self, module_id: Optional[str] = "breakout_signal"):
        super().__init__(module_id=module_id)
        self.min_level_strength = 0.7
        self.confirmation_candles = 1
        self.signal_expiry_minutes = 60
        self.min_volume_ratio = 1.2  # Minimum volume ratio for confirmation
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the signal generator.
        
        Args:
            config: Configuration dictionary with the following options:
                - min_level_strength: Minimum strength for a level to generate a signal
                - confirmation_candles: Number of candles to confirm the breakout
                - signal_expiry_minutes: Signal expiry time in minutes
                - min_volume_ratio: Minimum volume ratio for confirmation
        """
        self.min_level_strength = config.get("min_level_strength", 0.7)
        self.confirmation_candles = config.get("confirmation_candles", 1)
        self.signal_expiry_minutes = config.get("signal_expiry_minutes", 60)
        self.min_volume_ratio = config.get("min_volume_ratio", 1.2)
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> List[SignalData]:
        """Generate breakout signals based on price data and levels.
        
        Args:
            input_data: Dictionary containing "price_data" (PriceData) and "level_data" (LevelData)
            
        Returns:
            List of SignalData objects
        """
        price_data = input_data.get("price_data")
        level_data = input_data.get("level_data")
        
        if not price_data or not level_data or not price_data.bars or not level_data.levels:
            return []
        
        # Filter levels by strength
        strong_levels = [level for level in level_data.levels 
                          if level.strength >= self.min_level_strength]
        
        if not strong_levels:
            return []
        
        signals = []
        df = price_data.to_dataframe()
        
        # Calculate average volume for last 20 bars
        avg_volume = df['volume'].iloc[-20:].mean() if len(df) >= 20 else df['volume'].mean()
        
        # Get the most recent bars for breakout detection
        recent_bars = price_data.bars[-self.confirmation_candles-2:]
        if len(recent_bars) < self.confirmation_candles + 2:
            return []
        
        # Check each level for breakouts
        for level in strong_levels:
            price_level = level.price
            
            # Resistance breakout (long)
            if level.level_type == "resistance":
                # Check if we were below the level and now broke above it
                was_below = all(bar.close < price_level for bar in recent_bars[:-self.confirmation_candles])
                
                # Check if we're now above the level for the confirmation period
                is_above = all(bar.close > price_level for bar in recent_bars[-self.confirmation_candles:])
                
                # Volume confirmation
                volume_increased = recent_bars[-1].volume > avg_volume * self.min_volume_ratio
                
                if was_below and is_above and volume_increased:
                    signal = SignalData(
                        symbol=price_data.symbol,
                        signal_type=SignalType.ENTRY_LONG,
                        price=recent_bars[-1].close,
                        timestamp=datetime.now(),
                        expiration=datetime.now() + timedelta(minutes=self.signal_expiry_minutes),
                        confidence=level.strength,
                        metadata={
                            "level_price": price_level,
                            "level_type": level.level_type,
                            "breakout_bar": recent_bars[-1].timestamp.isoformat()
                        }
                    )
                    signals.append(signal)
            
            # Support breakout (short)
            elif level.level_type == "support":
                # Check if we were above the level and now broke below it
                was_above = all(bar.close > price_level for bar in recent_bars[:-self.confirmation_candles])
                
                # Check if we're now below the level for the confirmation period
                is_below = all(bar.close < price_level for bar in recent_bars[-self.confirmation_candles:])
                
                # Volume confirmation
                volume_increased = recent_bars[-1].volume > avg_volume * self.min_volume_ratio
                
                if was_above and is_below and volume_increased:
                    signal = SignalData(
                        symbol=price_data.symbol,
                        signal_type=SignalType.ENTRY_SHORT,
                        price=recent_bars[-1].close,
                        timestamp=datetime.now(),
                        expiration=datetime.now() + timedelta(minutes=self.signal_expiry_minutes),
                        confidence=level.strength,
                        metadata={
                            "level_price": price_level,
                            "level_type": level.level_type,
                            "breakout_bar": recent_bars[-1].timestamp.isoformat()
                        }
                    )
                    signals.append(signal)
        
        return signals