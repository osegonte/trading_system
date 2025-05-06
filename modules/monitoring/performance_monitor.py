# modules/monitoring/performance_monitor.py
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

from core.interfaces import IModule
from core.models import OrderData, TradeData, PerformanceMetrics

class PerformanceMonitor(IModule):
    """Monitors and calculates trading performance metrics."""
    
    def __init__(self, module_id: Optional[str] = "performance_monitor"):
        super().__init__(module_id=module_id)
        self.trades = []
        self.metrics = PerformanceMetrics()
        self.initial_capital = 10000.0
        self.update_interval = 60  # seconds
        self.last_update = datetime.now()
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the monitor.
        
        Args:
            config: Configuration dictionary with the following options:
                - initial_capital: Initial account capital
                - update_interval: Metrics update interval in seconds
        """
        self.initial_capital = config.get("initial_capital", 10000.0)
        self.update_interval = config.get("update_interval", 60)
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> PerformanceMetrics:
        """Update performance metrics based on new trades.
        
        Args:
            input_data: Dictionary containing:
                - "trades": List of TradeData objects
                - "orders": List of OrderData objects (optional)
            
        Returns:
            PerformanceMetrics object
        """
        trades = input_data.get("trades", [])
        if trades:
            # Add new trades
            self.trades.extend(trades)
        
        # Check if it's time to update metrics
        current_time = datetime.now()
        if (current_time - self.last_update).total_seconds() >= self.update_interval or not trades:
            self._calculate_metrics()
            self.last_update = current_time
        
        return self.metrics
    
    def _calculate_metrics(self) -> None:
        """Calculate performance metrics from trade history."""
        if not self.trades:
            return
        
        # Basic trade statistics
        self.metrics.total_trades = len(self.trades)
        
        # Calculate P&L
        pnl_list = []
        for trade in self.trades:
            if trade.side == OrderSide.BUY:
                pnl = (trade.price - trade.entry_price) * trade.quantity
            else:
                pnl = (trade.entry_price - trade.price) * trade.quantity
            pnl_list.append(pnl)
        
        # Winning and losing trades
        winning_trades = [pnl for pnl in pnl_list if pnl > 0]
        losing_trades = [pnl for pnl in pnl_list if pnl <= 0]
        
        self.metrics.winning_trades = len(winning_trades)
        self.metrics.losing_trades = len(losing_trades)
        
        # Win rate
        self.metrics.win_rate = (self.metrics.winning_trades / self.metrics.total_trades * 100) if self.metrics.total_trades > 0 else 0
        
        # Average win and loss
        self.metrics.average_win = np.mean(winning_trades) if winning_trades else 0
        self.metrics.average_loss = np.mean([abs(loss) for loss in losing_trades]) if losing_trades else 0
        
        # Total P&L
        self.metrics.total_pnl = sum(pnl_list)
        
        # Calculate equity curve
        equity_curve = [self.initial_capital]
        for pnl in pnl_list:
            equity_curve.append(equity_curve[-1] + pnl)
        
        # Max drawdown
        peak = self.initial_capital
        drawdowns = []
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown_pct = (peak - equity) / peak * 100 if peak > 0 else 0
            drawdowns.append(drawdown_pct)
        
        self.metrics.max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Calculate returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] / equity_curve[i-1]) - 1
            returns.append(ret)
        
        # Sharpe Ratio (assuming risk-free rate = 0)
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            self.metrics.sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
            
            # Sortino Ratio (only negative returns for denominator)
            neg_returns = [r for r in returns if r < 0]
            std_neg_return = np.std(neg_returns) if neg_returns else 0
            self.metrics.sortino_ratio = (mean_return / std_neg_return) * np.sqrt(252) if std_neg_return > 0 else 0