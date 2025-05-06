# core/models.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd
import uuid

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class TimeInForce(Enum):
    GTC = "good_till_cancel"
    IOC = "immediate_or_cancel"
    FOK = "fill_or_kill"
    DAY = "day"

@dataclass
class PriceBar:
    """Single price bar/candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    
@dataclass
class PriceData:
    """Collection of price bars with metadata."""
    symbol: str
    timeframe: str  # e.g., "1m", "5m", "1h", "1d"
    bars: List[PriceBar]
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert price data to pandas DataFrame."""
        data = {
            'timestamp': [bar.timestamp for bar in self.bars],
            'open': [bar.open for bar in self.bars],
            'high': [bar.high for bar in self.bars],
            'low': [bar.low for bar in self.bars],
            'close': [bar.close for bar in self.bars],
            'volume': [bar.volume for bar in self.bars]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df

@dataclass
class PriceLevel:
    """Support or resistance price level."""
    price: float
    level_type: str  # "support" or "resistance"
    strength: float  # 0.0 to 1.0
    created_at: datetime
    last_tested: Optional[datetime] = None
    times_tested: int = 0

@dataclass
class LevelData:
    """Collection of identified price levels."""
    symbol: str
    timeframe: str
    levels: List[PriceLevel]
    last_updated: datetime = field(default_factory=datetime.now)

class SignalType(Enum):
    ENTRY_LONG = "entry_long"
    ENTRY_SHORT = "entry_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    
@dataclass
class SignalData:
    """Trading signal with metadata."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    signal_type: SignalType = SignalType.ENTRY_LONG
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    expiration: Optional[datetime] = None
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, any] = field(default_factory=dict)
    
@dataclass
class RiskParameters:
    """Risk management parameters for a trade."""
    position_size: float
    stop_loss_price: float
    take_profit_price: Optional[float] = None
    trailing_stop: bool = False
    trailing_stop_distance: Optional[float] = None
    max_drawdown: Optional[float] = None
    
@dataclass
class OrderData:
    """Order information."""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    order_type: OrderType = OrderType.MARKET
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: Optional[float] = None  # For limit and stop-limit orders
    stop_price: Optional[float] = None  # For stop and stop-limit orders
    time_in_force: TimeInForce = TimeInForce.GTC
    created_at: datetime = field(default_factory=datetime.now)
    signal_id: Optional[str] = None  # Reference to the signal that generated this order
    status: str = "created"  # created, submitted, filled, canceled, rejected
    
@dataclass
class TradeData:
    """Executed trade information."""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    commission: float = 0.0
    
@dataclass
class PerformanceMetrics:
    """Trading performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0