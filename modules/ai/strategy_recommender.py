# modules/ai/strategy_recommender.py
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta
import logging
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class StrategyRecommender:
    """AI-powered strategy recommendation engine for child bots."""
    
    def __init__(self):
        self.logger = logging.getLogger("StrategyRecommender")
        self.scaler = StandardScaler()
        self.cluster_model = None
        self.performance_patterns = {}
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the strategy recommender."""
        self.min_trades_for_analysis = config.get("min_trades", 50)
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.market_regimes = config.get("market_regimes", ["bullish", "bearish", "sideways"])
        
    def generate_recommendations(self, child_id: str, child_data: pd.DataFrame, 
                               child_metrics: Dict, insights: List[Dict]) -> List[Dict]:
        """Generate personalized strategy recommendations for a child bot."""
        recommendations = []
        
        try:
            # Analyze current performance
            current_performance = self._analyze_child_performance(child_data, child_metrics)
            
            # Identify similar performing children
            similar_children = self._find_similar_children(child_metrics, insights)
            
            # Generate strategy adjustments
            strategy_adjustments = self._generate_strategy_adjustments(
                current_performance, similar_children, insights
            )
            
            # Create recommendations
            for adjustment in strategy_adjustments:
                recommendation = {
                    "child_id": child_id,
                    "strategy_name": adjustment["strategy"],
                    "config": adjustment["config"],
                    "confidence": adjustment["confidence"],
                    "expected_improvement": adjustment["expected_improvement"],
                    "market_regime": adjustment.get("market_regime", "all"),
                    "reasoning": adjustment["reasoning"]
                }
                recommendations.append(recommendation)
                
        except Exception as e:
            self.logger.error(f"Error generating recommendations for {child_id}: {e}")
        
        return recommendations
    
    def _analyze_child_performance(self, data: pd.DataFrame, metrics: Dict) -> Dict:
        """Analyze individual child performance patterns."""
        analysis = {
            "trade_frequency": len(data) / max(1, (data['timestamp'].max() - data['timestamp'].min()).days),
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "avg_hold_time": self._calculate_avg_hold_time(data),
            "best_performing_assets": self._get_best_assets(data),
            "risk_profile": self._assess_risk_profile(data, metrics),
            "market_timing": self._analyze_market_timing(data)
        }
        return analysis
    
    def _find_similar_children(self, child_metrics: Dict, insights: List[Dict]) -> List[Dict]:
        """Find children with similar performance profiles."""
        # This would typically use clustering on performance metrics
        # For now, return simplified similar children based on win rate
        similar = []
        child_win_rate = child_metrics.get("win_rate", 0)
        
        for insight in insights:
            if insight.get("type") == "child_comparison":
                other_win_rate = insight.get("data", {}).get("win_rate", 0)
                if abs(other_win_rate - child_win_rate) < 0.1:  # Within 10%
                    similar.append(insight)
        
        return similar[:3]  # Top 3 similar children
    
    def _generate_strategy_adjustments(self, performance: Dict, 
                                     similar_children: List[Dict], 
                                     insights: List[Dict]) -> List[Dict]:
        """Generate specific strategy adjustments."""
        adjustments = []
        
        # Risk adjustment recommendations
        if performance["risk_profile"] == "high" and performance["win_rate"] < 0.6:
            adjustments.append({
                "strategy": "risk_reduction",
                "config": {
                    "position_size_multiplier": 0.7,
                    "stop_loss_tighter": True,
                    "max_concurrent_trades": max(1, int(performance.get("concurrent_trades", 3) * 0.8))
                },
                "confidence": 0.8,
                "expected_improvement": 0.15,
                "reasoning": "High risk with low win rate - reduce exposure"
            })
        
        # Asset diversification recommendations
        best_assets = performance.get("best_performing_assets", [])
        if len(best_assets) < 2:
            adjustments.append({
                "strategy": "diversification",
                "config": {
                    "add_assets": self._suggest_complementary_assets(best_assets, insights),
                    "asset_allocation": "balanced"
                },
                "confidence": 0.7,
                "expected_improvement": 0.1,
                "reasoning": "Limited asset diversity - expand portfolio"
            })
        
        # Timing optimization
        if performance.get("market_timing", {}).get("score", 0) < 0.5:
            adjustments.append({
                "strategy": "timing_optimization",
                "config": {
                    "entry_confirmation": True,
                    "market_regime_filter": True,
                    "volume_confirmation": True
                },
                "confidence": 0.6,
                "expected_improvement": 0.12,
                "reasoning": "Poor market timing - add confirmation filters"
            })
        
        return adjustments
    
    def _calculate_avg_hold_time(self, data: pd.DataFrame) -> float:
        """Calculate average holding time for trades."""
        if len(data) < 2:
            return 0
        
        # Group by symbol and calculate hold times
        hold_times = []
        for symbol in data['symbol'].unique():
            symbol_data = data[data['symbol'] == symbol].sort_values('timestamp')
            if len(symbol_data) > 1:
                avg_time = (symbol_data['timestamp'].iloc[-1] - symbol_data['timestamp'].iloc[0]).total_seconds() / 3600
                hold_times.append(avg_time)
        
        return np.mean(hold_times) if hold_times else 0
    
    def _get_best_assets(self, data: pd.DataFrame) -> List[str]:
        """Identify best performing assets."""
        asset_performance = data.groupby('symbol')['pnl'].sum().sort_values(ascending=False)
        return asset_performance.head(3).index.tolist()
    
    def _assess_risk_profile(self, data: pd.DataFrame, metrics: Dict) -> str:
        """Assess risk profile based on trading patterns."""
        max_drawdown = metrics.get("max_drawdown", 0)
        sharpe_ratio = metrics.get("sharpe_ratio", 0)
        
        if max_drawdown > 15 or sharpe_ratio < 0.5:
            return "high"
        elif max_drawdown < 5 and sharpe_ratio > 1.5:
            return "low"
        else:
            return "medium"
    
    def _analyze_market_timing(self, data: pd.DataFrame) -> Dict:
        """Analyze market timing effectiveness."""
        if len(data) < 10:
            return {"score": 0.5, "analysis": "insufficient_data"}
        
        # Simple analysis based on win rate over time
        data_sorted = data.sort_values('timestamp')
        recent_trades = data_sorted.tail(20)
        recent_win_rate = (recent_trades['pnl'] > 0).mean()
        
        return {
            "score": recent_win_rate,
            "analysis": "good" if recent_win_rate > 0.6 else "needs_improvement"
        }
    
    def _suggest_complementary_assets(self, current_assets: List[str], 
                                    insights: List[Dict]) -> List[str]:
        """Suggest complementary assets based on insights."""
        suggestions = []
        
        # Look for assets that performed well in similar market conditions
        for insight in insights:
            if insight.get("type") == "asset_performance":
                asset = insight.get("data", {}).get("best_asset")
                if asset and asset not in current_assets:
                    suggestions.append(asset)
        
        # Default suggestions by asset type
        if not suggestions:
            if any("USD" in asset for asset in current_assets):  # Crypto
                suggestions = ["ETH-USD", "ADA-USD", "DOT-USD"]
            elif any("=" in asset for asset in current_assets):  # Forex
                suggestions = ["GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
            else:  # Stocks
                suggestions = ["SPY", "QQQ", "IWM"]
        
        return suggestions[:2]  # Limit to 2 suggestions
    
    def update_with_insights(self, insights: List[Dict]) -> None:
        """Update recommender with new insights from parent learning."""
        try:
            # Update performance patterns
            for insight in insights:
                if insight.get("type") == "pattern_discovery":
                    pattern_key = insight.get("pattern_id", "unknown")
                    self.performance_patterns[pattern_key] = insight.get("data", {})
            
            self.logger.info(f"Updated recommender with {len(insights)} new insights")
            
        except Exception as e:
            self.logger.error(f"Error updating recommender with insights: {e}")