# modules/strategies/enhanced_child_bot.py
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from modules.sync.report_uploader import ReportUploader, UpdateFetcher
from core.interfaces import IModule

class EnhancedChildBot(IModule):
    """Enhanced child bot with parent communication capabilities."""
    
    def __init__(self, child_id: str, module_id: Optional[str] = None):
        super().__init__(module_id or f"child_bot_{child_id}")
        self.child_id = child_id
        self.logger = logging.getLogger(f"EnhancedChildBot.{child_id}")
        
        # Communication modules
        self.report_uploader = ReportUploader(child_id)
        self.update_fetcher = UpdateFetcher(child_id)
        
        # Performance tracking
        self.trades_history = []
        self.performance_metrics = {}
        self.last_report_time = datetime.now()
        self.report_interval = timedelta(hours=1)  # Report every hour
        
        # Update checking
        self.last_update_check = datetime.now()
        self.update_check_interval = timedelta(minutes=30)  # Check for updates every 30 min
        
        # Current configuration
        self.current_config = {}
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the enhanced child bot."""
        self.current_config = config.copy()
        self.report_interval = timedelta(
            hours=config.get("report_interval_hours", 1)
        )
        self.update_check_interval = timedelta(
            minutes=config.get("update_check_interval_minutes", 30)
        )
        super().configure(config)
        
    def execute(self, input_data: Dict[str, Any]) -> Any:
        """Execute child bot with parent communication."""
        # Check for updates from parent
        self._check_for_updates()
        
        # Record trade if provided
        if "trade" in input_data:
            self._record_trade(input_data["trade"])
        
        # Update metrics if provided
        if "metrics" in input_data:
            self.performance_metrics.update(input_data["metrics"])
        
        # Send report if interval elapsed
        self._send_report_if_needed()
        
        return {"status": "processed", "child_id": self.child_id}
    
    def _record_trade(self, trade: Dict[str, Any]) -> None:
        """Record a trade for reporting to parent."""
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "child_id": self.child_id,
            **trade
        }
        
        self.trades_history.append(trade_record)
        
        # Upload individual trade update
        self.report_uploader.upload_trade_update(trade_record)
        
        # Keep only recent trades in memory (last 1000)
        if len(self.trades_history) > 1000:
            self.trades_history = self.trades_history[-1000:]
        
        self.logger.debug(f"Recorded trade: {trade.get('symbol', 'Unknown')} - {trade.get('pnl', 0)}")
    
    def _check_for_updates(self) -> None:
        """Check for and apply updates from parent."""
        current_time = datetime.now()
        
        if current_time - self.last_update_check >= self.update_check_interval:
            self.last_update_check = current_time
            
            try:
                updates = self.update_fetcher.fetch_pending_updates()
                
                for update in updates:
                    success = self.update_fetcher.apply_update(update)
                    if success:
                        self.logger.info(f"Applied update: {update.get('description', 'No description')}")
                    else:
                        self.logger.warning(f"Failed to apply update: {update.get('id', 'Unknown')}")
                        
            except Exception as e:
                self.logger.error(f"Error checking for updates: {e}")
    
    def _send_report_if_needed(self) -> None:
        """Send performance report to parent if interval elapsed."""
        current_time = datetime.now()
        
        if current_time - self.last_report_time >= self.report_interval:
            self.last_report_time = current_time
            
            try:
                # Get market conditions
                market_conditions = self._assess_market_conditions()
                
                # Send comprehensive report
                success = self.report_uploader.upload_performance_report(
                    trades=self.trades_history.copy(),
                    metrics=self.performance_metrics.copy(),
                    config=self.current_config.copy(),
                    market_conditions=market_conditions
                )
                
                if success:
                    self.logger.info("Sent performance report to parent")
                    # Clear old trades after successful report
                    self.trades_history = []
                else:
                    self.logger.warning("Failed to send performance report")
                    
            except Exception as e:
                self.logger.error(f"Error sending report: {e}")
    
    def _assess_market_conditions(self) -> Dict[str, Any]:
        """Assess current market conditions for reporting."""
        # This would integrate with your market data providers
        return {
            "timestamp": datetime.now().isoformat(),
            "volatility": "medium",  # Would be calculated from actual data
            "trend": "sideways",     # Would be determined from price analysis
            "volume": "normal",      # Would be compared to historical averages
            "market_session": self._get_market_session()
        }
    
    def _get_market_session(self) -> str:
        """Determine current market session."""
        current_hour = datetime.now().hour
        
        if 9 <= current_hour < 16:
            return "us_open"
        elif 2 <= current_hour < 8:
            return "asian_session"
        elif 8 <= current_hour < 17:
            return "european_session"
        else:
            return "after_hours"
    
    def force_report(self) -> bool:
        """Force immediate report to parent (for testing)."""
        try:
            market_conditions = self._assess_market_conditions()
            
            success = self.report_uploader.upload_performance_report(
                trades=self.trades_history.copy(),
                metrics=self.performance_metrics.copy(),
                config=self.current_config.copy(),
                market_conditions=market_conditions
            )
            
            if success:
                self.trades_history = []
                self.last_report_time = datetime.now()
                self.logger.info("Forced performance report sent successfully")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error in forced report: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current child bot status."""
        return {
            "child_id": self.child_id,
            "trades_pending_report": len(self.trades_history),
            "last_report_time": self.last_report_time.isoformat(),
            "last_update_check": self.last_update_check.isoformat(),
            "performance_metrics": self.performance_metrics.copy(),
            "current_config": self.current_config.copy()
        }