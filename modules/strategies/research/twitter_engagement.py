import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from core.interfaces import IModule
from core.models import SignalData, SignalType

class TwitterEngagementStrategy(IModule):
    """
    Research-grade Twitter engagement strategy.
    Monthly rebalancing based on comments/likes ratio.
    """
    
    def __init__(self, module_id: Optional[str] = "twitter_engagement"):
        super().__init__(module_id=module_id)
        self.logger = logging.getLogger("TwitterEngagementStrategy")
        
        # Strategy parameters
        self.min_likes = 20
        self.min_comments = 10
        self.top_n_symbols = 5
        self.position_size_pct = 0.01  # 1% of account per position
        self.rebalance_day = 28  # Last day of month
        
        # Tracking
        self.last_rebalance = None
        self.current_positions = {}
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure Twitter engagement strategy."""
        self.min_likes = config.get("min_likes", 20)
        self.min_comments = config.get("min_comments", 10)
        self.top_n_symbols = config.get("top_n_symbols", 5)
        self.position_size_pct = config.get("position_size_pct", 0.01)
        super().configure(config)
        
    def execute(self, input_data: Dict[str, Any]) -> List[SignalData]:
        """Execute Twitter engagement strategy."""
        twitter_data = input_data.get("twitter_data", {})
        price_data = input_data.get("price_data", {})
        current_date = input_data.get("current_date", datetime.now())
        
        # Check if monthly rebalancing is needed
        if not self._should_rebalance(current_date):
            return []
        
        try:
            # Calculate engagement ratios
            engagement_scores = self._calculate_engagement_scores(twitter_data)
            
            if not engagement_scores:
                self.logger.warning("No valid engagement data available")
                return []
            
            # Select top symbols
            top_symbols = self._select_top_symbols(engagement_scores)
            
            # Generate rebalancing signals
            signals = self._generate_engagement_signals(top_symbols, price_data)
            
            # Update tracking
            self.current_positions = {symbol: True for symbol in top_symbols}
            self.last_rebalance = current_date
            
            self.logger.info(f"Generated {len(signals)} Twitter engagement signals")
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in Twitter engagement execution: {e}")
            return []
    
    def _should_rebalance(self, current_date: datetime) -> bool:
        """Check if monthly rebalancing is needed."""
        if self.last_rebalance is None:
            return True
        
        # Rebalance on last calendar day of month
        next_month = current_date.replace(day=28) + timedelta(days=4)
        last_day_of_month = next_month - timedelta(days=next_month.day)
        
        return (current_date.date() >= last_day_of_month.date() and 
                current_date.month != self.last_rebalance.month)
    
    def _calculate_engagement_scores(self, twitter_data: Dict) -> Dict[str, float]:
        """Calculate engagement ratio for each symbol."""
        engagement_scores = {}
        
        for symbol, data in twitter_data.items():
            try:
                # Get monthly aggregated data
                monthly_data = self._aggregate_monthly_data(data)
                
                if not monthly_data:
                    continue
                
                likes = monthly_data.get("likes", 0)
                comments = monthly_data.get("comments", 0)
                
                # Filter by minimum thresholds
                if likes < self.min_likes or comments < self.min_comments:
                    continue
                
                # Calculate engagement ratio
                engagement_ratio = comments / likes if likes > 0 else 0
                
                # Apply filters for noise reduction
                if self._is_valid_engagement(monthly_data):
                    engagement_scores[symbol] = engagement_ratio
                    
            except Exception as e:
                self.logger.warning(f"Error calculating engagement for {symbol}: {e}")
                continue
        
        return engagement_scores
    
    def _aggregate_monthly_data(self, symbol_data: Dict) -> Dict[str, Any]:
        """Aggregate Twitter data for the current month."""
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        # This would integrate with your Twitter data source
        # For now, return simulated monthly aggregates
        return {
            "likes": symbol_data.get("monthly_likes", 0),
            "comments": symbol_data.get("monthly_comments", 0),
            "impressions": symbol_data.get("monthly_impressions", 0),
            "sentiment": symbol_data.get("sentiment_score", 0.5),
            "mention_count": symbol_data.get("mention_count", 0)
        }
    
    def _is_valid_engagement(self, data: Dict) -> bool:
        """Validate engagement data quality."""
        # Check for suspicious patterns that might indicate bot activity
        likes = data.get("likes", 0)
        comments = data.get("comments", 0)
        impressions = data.get("impressions", 0)
        
        # Engagement rate should be reasonable
        if impressions > 0:
            engagement_rate = (likes + comments) / impressions
            if engagement_rate > 0.2:  # Suspiciously high engagement
                return False
        
        # Comments-to-likes ratio should be reasonable
        if likes > 0:
            comment_ratio = comments / likes
            if comment_ratio > 0.5:  # Unusually high comment ratio
                return False
        
        return True
    
    def _select_top_symbols(self, engagement_scores: Dict[str, float]) -> List[str]:
        """Select top N symbols by engagement ratio."""
        # Sort by engagement ratio (descending)
        sorted_symbols = sorted(
            engagement_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Take top N
        top_symbols = [symbol for symbol, score in sorted_symbols[:self.top_n_symbols]]
        
        self.logger.info(f"Selected top symbols: {top_symbols}")
        return top_symbols
    
    def _generate_engagement_signals(self, symbols: List[str], price_data: Dict) -> List[SignalData]:
        """Generate signals for selected symbols."""
        signals = []
        
        for symbol in symbols:
            if symbol in price_data and price_data[symbol].bars:
                current_price = price_data[symbol].bars[-1].close
                
                signal = SignalData(
                    symbol=symbol,
                    signal_type=SignalType.ENTRY_LONG,
                    price=current_price,
                    timestamp=datetime.now(),
                    confidence=0.7,
                    metadata={
                        "strategy": "twitter_engagement",
                        "position_size_pct": self.position_size_pct,
                        "holding_period": "1_month",
                        "entry_type": "equal_weight",
                        "rebalance_signal": True
                    }
                )
                signals.append(signal)
        
        return signals
