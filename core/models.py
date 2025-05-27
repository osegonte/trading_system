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

class AssetType(Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"

class SignalType(Enum):
    ENTRY_LONG = "entry_long"
    ENTRY_SHORT = "entry_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"

@dataclass
class PriceBar:
    """Single price bar/candle data with asset type support."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    asset_type: str = "stock"
    
    def __post_init__(self):
        """Validate price data after initialization."""
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            # Auto-correct invalid OHLC data
            self.high = max(self.open, self.high, self.low, self.close)
            self.low = min(self.open, self.high, self.low, self.close)
    
@dataclass
class PriceData:
    """Collection of price bars with metadata and asset type."""
    symbol: str
    timeframe: str  # e.g., "1m", "5m", "1h", "1d"
    bars: List[PriceBar]
    asset_type: str = "stock"
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert price data to pandas DataFrame."""
        if not self.bars:
            return pd.DataFrame()
            
        data = {
            'timestamp': [bar.timestamp for bar in self.bars],
            'open': [bar.open for bar in self.bars],
            'high': [bar.high for bar in self.bars],
            'low': [bar.low for bar in self.bars],
            'close': [bar.close for bar in self.bars],
            'volume': [bar.volume for bar in self.bars],
            'asset_type': [bar.asset_type for bar in self.bars]
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_latest_price(self) -> float:
        """Get the latest close price."""
        return self.bars[-1].close if self.bars else 0.0
    
    def get_price_change(self) -> Dict[str, float]:
        """Get price change from previous bar."""
        if len(self.bars) < 2:
            return {"change": 0.0, "change_pct": 0.0}
        
        current = self.bars[-1].close
        previous = self.bars[-2].close
        change = current - previous
        change_pct = (change / previous * 100) if previous != 0 else 0.0
        
        return {"change": change, "change_pct": change_pct}

@dataclass
class PriceLevel:
    """Support or resistance price level with asset-specific parameters."""
    price: float
    level_type: str  # "support" or "resistance"
    strength: float  # 0.0 to 1.0
    created_at: datetime
    asset_type: str = "stock"
    last_tested: Optional[datetime] = None
    times_tested: int = 0
    
    def is_strong_level(self) -> bool:
        """Check if this is a strong level based on asset type."""
        strength_thresholds = {
            "stock": 0.7,
            "crypto": 0.6,  # Lower threshold due to volatility
            "forex": 0.8    # Higher threshold due to precision
        }
        threshold = strength_thresholds.get(self.asset_type, 0.7)
        return self.strength >= threshold

@dataclass
class LevelData:
    """Collection of identified price levels with asset type."""
    symbol: str
    timeframe: str
    levels: List[PriceLevel]
    asset_type: str = "stock"
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_levels_by_type(self, level_type: str) -> List[PriceLevel]:
        """Get levels by type (support/resistance)."""
        return [level for level in self.levels if level.level_type == level_type]
    
    def get_strong_levels(self) -> List[PriceLevel]:
        """Get only strong levels."""
        return [level for level in self.levels if level.is_strong_level()]

@dataclass
class SignalData:
    """Trading signal with metadata and asset type support."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    signal_type: SignalType = SignalType.ENTRY_LONG
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    expiration: Optional[datetime] = None
    confidence: float = 1.0  # 0.0 to 1.0
    asset_type: str = "stock"
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if signal has expired."""
        if self.expiration is None:
            return False
        return datetime.now() > self.expiration
    
    def is_valid_for_asset_type(self) -> bool:
        """Validate signal parameters for asset type."""
        if self.asset_type == "crypto":
            return self.confidence >= 0.6  # Higher confidence needed for crypto
        elif self.asset_type == "forex":
            return self.confidence >= 0.8  # Highest confidence for forex
        else:
            return self.confidence >= 0.5  # Standard for stocks

@dataclass
class RiskParameters:
    """Risk management parameters for a trade with asset-specific settings."""
    position_size: float
    stop_loss_price: float
    take_profit_price: Optional[float] = None
    trailing_stop: bool = False
    trailing_stop_distance: Optional[float] = None
    max_drawdown: Optional[float] = None
    asset_type: str = "stock"
    
    def validate(self) -> bool:
        """Validate risk parameters."""
        if self.position_size <= 0:
            return False
        if self.stop_loss_price <= 0:
            return False
        if self.max_drawdown and self.max_drawdown <= 0:
            return False
        return True
    
    def get_risk_reward_ratio(self, entry_price: float) -> float:
        """Calculate risk-reward ratio."""
        if not self.take_profit_price or self.stop_loss_price == entry_price:
            return 0.0
        
        risk = abs(entry_price - self.stop_loss_price)
        reward = abs(self.take_profit_price - entry_price)
        
        return reward / risk if risk > 0 else 0.0

@dataclass
class OrderData:
    """Order information with multi-asset support."""
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
    asset_type: str = "stock"
    commission: float = 0.0
    
    def get_order_value(self) -> float:
        """Calculate total order value."""
        price = self.price or 0.0
        if self.asset_type == "forex":
            # For forex, quantity is in lots
            return self.quantity * price / 1000  # Convert to dollar value
        else:
            return self.quantity * price

@dataclass
class TradeData:
    """Executed trade information with asset type."""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    commission: float = 0.0
    asset_type: str = "stock"
    entry_price: Optional[float] = None  # For P&L calculation
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        if not self.entry_price:
            return 0.0
        
        if self.side == OrderSide.BUY:
            return (current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - current_price) * self.quantity
    
    def get_trade_value(self) -> float:
        """Get total trade value."""
        if self.asset_type == "forex":
            return self.quantity * self.price / 1000
        else:
            return self.quantity * self.price

@dataclass
class PerformanceMetrics:
    """Trading performance metrics with multi-asset breakdown."""
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
    
    # Asset-specific metrics
    stock_pnl: float = 0.0
    crypto_pnl: float = 0.0
    forex_pnl: float = 0.0
    stock_trades: int = 0
    crypto_trades: int = 0
    forex_trades: int = 0
    
    def get_asset_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Get performance breakdown by asset type."""
        return {
            "stock": {
                "pnl": self.stock_pnl,
                "trades": self.stock_trades,
                "avg_pnl": self.stock_pnl / self.stock_trades if self.stock_trades > 0 else 0.0
            },
            "crypto": {
                "pnl": self.crypto_pnl,
                "trades": self.crypto_trades,
                "avg_pnl": self.crypto_pnl / self.crypto_trades if self.crypto_trades > 0 else 0.0
            },
            "forex": {
                "pnl": self.forex_pnl,
                "trades": self.forex_trades,
                "avg_pnl": self.forex_pnl / self.forex_trades if self.forex_trades > 0 else 0.0
            }
        }
    
    def update_asset_metrics(self, trade: TradeData, pnl: float) -> None:
        """Update asset-specific metrics."""
        asset_type = trade.asset_type
        
        if asset_type == "stock":
            self.stock_pnl += pnl
            self.stock_trades += 1
        elif asset_type == "crypto":
            self.crypto_pnl += pnl
            self.crypto_trades += 1
        elif asset_type == "forex":
            self.forex_pnl += pnl
            self.forex_trades += 1

@dataclass
class MarketData:
    """Real-time market data with multi-asset support."""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: datetime
    asset_type: str = "stock"
    
    def get_spread(self) -> float:
        """Get bid-ask spread."""
        return self.ask - self.bid
    
    def get_spread_percentage(self) -> float:
        """Get spread as percentage of mid price."""
        mid_price = (self.bid + self.ask) / 2
        return (self.get_spread() / mid_price * 100) if mid_price > 0 else 0.0

@dataclass
class PortfolioPosition:
    """Portfolio position with asset type tracking."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    asset_type: str = "stock"
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_position_percentage(self, total_portfolio_value: float) -> float:
        """Get position as percentage of total portfolio."""
        return (self.market_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0
    
    def get_pnl_percentage(self) -> float:
        """Get P&L as percentage of cost basis."""
        cost_basis = self.quantity * self.avg_cost
        return (self.unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0