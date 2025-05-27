# core/parent/parent_controller.py
"""
Parent Controller - Central Intelligence System
Aggregates data from child bots and provides optimizations
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import schedule
import time
import threading

from core.interfaces import IModule
from modules.ai.strategy_recommender import StrategyRecommender

class ParentController(IModule):
    """
    Central Parent Controller that learns from all child bots
    and provides AI-driven strategy optimizations
    """
    
    def __init__(self, module_id: Optional[str] = "parent_controller"):
        super().__init__(module_id=module_id)
        self.logger = logging.getLogger(f"ParentController.{module_id}")
        
        # Core components
        self.strategy_recommender = StrategyRecommender()
        self.child_bots = {}  # child_id -> bot_info
        self.performance_db = None
        self.learning_scheduler = None
        
        # Configuration
        self.data_path = Path("data/parent")
        self.logs_path = Path("logs/parent")
        self.child_reports_path = Path("data/parent/child_reports")
        self.optimizations_path = Path("data/parent/optimizations")
        
        # Learning parameters
        self.min_data_points = 50  # Minimum trades before learning
        self.learning_frequency = "1hour"  # How often to retrain
        self.performance_lookback_days = 30
        
        # Ensure directories exist
        self.setup_directories()
        self.setup_database()
        
    def setup_directories(self):
        """Create necessary directory structure."""
        directories = [
            self.data_path,
            self.logs_path,
            self.child_reports_path,
            self.optimizations_path,
            Path("data/features"),
            Path("data/bronze"),
            Path("data/silver"),
            Path("data/gold")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Parent directory structure created")
    
    def setup_database(self):
        """Initialize SQLite database for performance tracking."""
        db_path = self.data_path / "parent_intelligence.db"
        self.performance_db = sqlite3.connect(str(db_path), check_same_thread=False)
        
        # Create tables
        cursor = self.performance_db.cursor()
        
        # Child bots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS child_bots (
                child_id TEXT PRIMARY KEY,
                name TEXT,
                asset_types TEXT,
                strategy_config TEXT,
                status TEXT,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id TEXT,
                timestamp TIMESTAMP,
                strategy_name TEXT,
                symbol TEXT,
                asset_type TEXT,
                trade_type TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                win_rate REAL,
                profit_factor REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                market_conditions TEXT,
                config_snapshot TEXT,
                FOREIGN KEY (child_id) REFERENCES child_bots (child_id)
            )
        """)
        
        # Strategy recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                strategy_name TEXT,
                recommended_config TEXT,
                confidence_score REAL,
                expected_improvement REAL,
                market_regime TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (child_id) REFERENCES child_bots (child_id)
            )
        """)
        
        # Learning insights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                insight_type TEXT,
                asset_type TEXT,
                strategy_name TEXT,
                key_finding TEXT,
                supporting_data TEXT,
                confidence_level REAL,
                applicable_conditions TEXT
            )
        """)
        
        self.performance_db.commit()
        self.logger.info("Parent database initialized")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the parent controller."""
        self.learning_frequency = config.get("learning_frequency", "1hour")
        self.min_data_points = config.get("min_data_points", 50)
        self.performance_lookback_days = config.get("performance_lookback_days", 30)
        
        # Configure strategy recommender
        self.strategy_recommender.configure(config.get("strategy_recommender", {}))
        
        super().configure(config)
        self.logger.info("Parent controller configured")
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method for parent controller."""
        command = input_data.get("command", "status")
        
        if command == "register_child":
            return self.register_child_bot(input_data)
        elif command == "process_child_report":
            return self.process_child_report(input_data)
        elif command == "get_optimizations":
            return self.get_optimizations_for_child(input_data)
        elif command == "learn_and_optimize":
            return self.learn_and_optimize()
        elif command == "get_global_insights":
            return self.get_global_insights()
        elif command == "status":
            return self.get_system_status()
        else:
            return {"error": f"Unknown command: {command}"}
    
    def register_child_bot(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new child bot with the parent system."""
        child_id = input_data.get("child_id")
        child_name = input_data.get("name", f"Child_{child_id}")
        asset_types = input_data.get("asset_types", [])
        strategy_config = input_data.get("strategy_config", {})
        
        if not child_id:
            return {"error": "child_id is required"}
        
        try:
            cursor = self.performance_db.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO child_bots 
                (child_id, name, asset_types, strategy_config, status, last_seen)
                VALUES (?, ?, ?, ?, 'active', ?)
            """, (
                child_id,
                child_name,
                json.dumps(asset_types),
                json.dumps(strategy_config),
                datetime.now()
            ))
            self.performance_db.commit()
            
            self.child_bots[child_id] = {
                "name": child_name,
                "asset_types": asset_types,
                "strategy_config": strategy_config,
                "status": "active",
                "last_seen": datetime.now()
            }
            
            self.logger.info(f"Registered child bot: {child_id} ({child_name})")
            return {"success": True, "message": f"Child bot {child_id} registered"}
            
        except Exception as e:
            self.logger.error(f"Error registering child bot {child_id}: {e}")
            return {"error": str(e)}
    
    def process_child_report(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance report from a child bot."""
        child_id = input_data.get("child_id")
        report_data = input_data.get("report_data", {})
        
        if not child_id or not report_data:
            return {"error": "child_id and report_data are required"}
        
        try:
            # Save raw report
            report_file = self.child_reports_path / f"{child_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump({
                    "child_id": child_id,
                    "timestamp": datetime.now().isoformat(),
                    "report_data": report_data
                }, f, indent=2)
            
            # Process and store in database
            self.store_performance_data(child_id, report_data)
            
            # Update child bot status
            cursor = self.performance_db.cursor()
            cursor.execute("""
                UPDATE child_bots SET last_seen = ?, status = 'active' 
                WHERE child_id = ?
            """, (datetime.now(), child_id))
            self.performance_db.commit()
            
            self.logger.info(f"Processed report from child bot: {child_id}")
            return {"success": True, "message": "Report processed successfully"}
            
        except Exception as e:
            self.logger.error(f"Error processing report from {child_id}: {e}")
            return {"error": str(e)}
    
    def store_performance_data(self, child_id: str, report_data: Dict[str, Any]) -> None:
        """Store performance data in the database."""
        cursor = self.performance_db.cursor()
        
        # Extract performance metrics
        trades = report_data.get("trades", [])
        metrics = report_data.get("metrics", {})
        config = report_data.get("config", {})
        market_conditions = report_data.get("market_conditions", {})
        
        for trade in trades:
            cursor.execute("""
                INSERT INTO performance_data 
                (child_id, timestamp, strategy_name, symbol, asset_type, trade_type,
                 entry_price, exit_price, quantity, pnl, win_rate, profit_factor,
                 max_drawdown, sharpe_ratio, market_conditions, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                child_id,
                trade.get("timestamp", datetime.now()),
                trade.get("strategy_name", "unknown"),
                trade.get("symbol", ""),
                trade.get("asset_type", "stock"),
                trade.get("trade_type", ""),
                trade.get("entry_price", 0),
                trade.get("exit_price", 0),
                trade.get("quantity", 0),
                trade.get("pnl", 0),
                metrics.get("win_rate", 0),
                metrics.get("profit_factor", 0),
                metrics.get("max_drawdown", 0),
                metrics.get("sharpe_ratio", 0),
                json.dumps(market_conditions),
                json.dumps(config)
            ))
        
        self.performance_db.commit()
    
    def learn_and_optimize(self) -> Dict[str, Any]:
        """Main learning function that analyzes all child data and generates optimizations."""
        try:
            self.logger.info("Starting learning and optimization cycle")
            
            # Get all performance data
            performance_df = self.get_performance_dataframe()
            
            if len(performance_df) < self.min_data_points:
                return {"message": f"Insufficient data for learning. Need {self.min_data_points}, have {len(performance_df)}"}
            
            # Analyze patterns and generate insights
            insights = self.analyze_performance_patterns(performance_df)
            
            # Generate strategy recommendations for each child
            recommendations = self.generate_strategy_recommendations(performance_df, insights)
            
            # Store insights and recommendations
            self.store_learning_insights(insights)
            self.store_strategy_recommendations(recommendations)
            
            # Update strategy recommender with new insights
            self.strategy_recommender.update_with_insights(insights)
            
            results = {
                "success": True,
                "insights_generated": len(insights),
                "recommendations_generated": len(recommendations),
                "data_points_analyzed": len(performance_df),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Learning cycle completed: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in learning cycle: {e}")
            return {"error": str(e)}
    
    def get_performance_dataframe(self) -> pd.DataFrame:
        """Get performance data as pandas DataFrame."""
        query = """
            SELECT * FROM performance_data 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp DESC
        """.format(self.performance_lookback_days)
        
        return pd.read_sql_query(query, self.performance_db)
    
    def analyze_performance_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze performance patterns and generate insights."""
        insights = []
        
        try:
            # Pattern 1: Asset type performance comparison
            asset_performance = df.groupby('asset_type').agg({
                'pnl': ['mean', 'std', 'count'],
                'win_rate': 'mean',
                'profit_factor': 'mean',
                'sharpe_ratio': 'mean'
            }).round(4)
            
            for asset_type in asset_performance.index:
                avg_pnl = asset_performance.loc[asset_type, ('pnl', 'mean')]
                trade_count = asset_performance.loc[asset_type, ('pnl', 'count')]
                
                if trade_count >= 10:  # Minimum trades for significance
                    insights.append({
                        "type": "asset_performance",
                        "asset_type": asset_type,
                        "finding": f"{asset_type} shows average P&L of {avg_pnl:.4f}",
                        "data": asset_performance.loc[asset_type].to_dict(),
                        "confidence": min(0.9, trade_count / 100),
                        "applicable_conditions": "general"
                    })
            
            # Pattern 2: Strategy effectiveness by market conditions
            if 'market_conditions' in df.columns:
                market_analysis = self.analyze_market_condition_patterns(df)
                insights.extend(market_analysis)
            
            # Pattern 3: Time-based patterns
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            hourly_performance = df.groupby('hour')['pnl'].mean()
            
            best_hour = hourly_performance.idxmax()
            worst_hour = hourly_performance.idxmin()
            
            insights.append({
                "type": "temporal_pattern",
                "finding": f"Best trading hour: {best_hour}:00, Worst: {worst_hour}:00",
                "data": hourly_performance.to_dict(),
                "confidence": 0.7,
                "applicable_conditions": "time_sensitive"
            })
            
            # Pattern 4: Symbol-specific patterns
            symbol_performance = df.groupby('symbol').agg({
                'pnl': ['mean', 'count'],
                'win_rate': 'mean'
            }).round(4)
            
            # Find best and worst performing symbols (with minimum trades)
            valid_symbols = symbol_performance[symbol_performance[('pnl', 'count')] >= 5]
            if not valid_symbols.empty:
                best_symbol = valid_symbols[('pnl', 'mean')].idxmax()
                worst_symbol = valid_symbols[('pnl', 'mean')].idxmin()
                
                insights.append({
                    "type": "symbol_performance",
                    "finding": f"Best symbol: {best_symbol}, Worst: {worst_symbol}",
                    "data": valid_symbols.to_dict(),
                    "confidence": 0.8,
                    "applicable_conditions": "symbol_selection"
                })
            
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")
        
        return insights
    
    def analyze_market_condition_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze patterns based on market conditions."""
        insights = []
        
        try:
            # Parse market conditions JSON
            market_conditions = []
            for _, row in df.iterrows():
                try:
                    conditions = json.loads(row['market_conditions'])
                    conditions['pnl'] = row['pnl']
                    conditions['win_rate'] = row['win_rate']
                    market_conditions.append(conditions)
                except:
                    continue
            
            if not market_conditions:
                return insights
            
            market_df = pd.DataFrame(market_conditions)
            
            # Analyze volatility impact
            if 'volatility' in market_df.columns:
                vol_performance = market_df.groupby('volatility')['pnl'].mean()
                
                insights.append({
                    "type": "volatility_impact",
                    "finding": f"Performance by volatility: {vol_performance.to_dict()}",
                    "data": vol_performance.to_dict(),
                    "confidence": 0.75,
                    "applicable_conditions": "volatility_dependent"
                })
            
            # Analyze trend impact
            if 'trend' in market_df.columns:
                trend_performance = market_df.groupby('trend')['pnl'].mean()
                
                insights.append({
                    "type": "trend_impact",
                    "finding": f"Performance by trend: {trend_performance.to_dict()}",
                    "data": trend_performance.to_dict(),
                    "confidence": 0.8,
                    "applicable_conditions": "trend_dependent"
                })
            
        except Exception as e:
            self.logger.error(f"Error analyzing market conditions: {e}")
        
        return insights
    
    def generate_strategy_recommendations(self, df: pd.DataFrame, insights: List[Dict]) -> List[Dict[str, Any]]:
        """Generate personalized strategy recommendations for each child bot."""
        recommendations = []
        
        try:
            # Get unique child bots
            child_ids = df['child_id'].unique()
            
            for child_id in child_ids:
                child_data = df[df['child_id'] == child_id]
                
                if len(child_data) < 10:  # Need minimum data
                    continue
                
                # Analyze child-specific performance
                child_metrics = {
                    'avg_pnl': child_data['pnl'].mean(),
                    'win_rate': child_data['win_rate'].mean(),
                    'profit_factor': child_data['profit_factor'].mean(),
                    'sharpe_ratio': child_data['sharpe_ratio'].mean(),
                    'max_drawdown': child_data['max_drawdown'].mean(),
                    'trade_count': len(child_data)
                }
                
                # Generate recommendations using strategy recommender
                child_recommendations = self.strategy_recommender.generate_recommendations(
                    child_id, child_data, child_metrics, insights
                )
                
                recommendations.extend(child_recommendations)
                
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
        
        return recommendations
    
    def store_learning_insights(self, insights: List[Dict[str, Any]]) -> None:
        """Store learning insights in database."""
        cursor = self.performance_db.cursor()
        
        for insight in insights:
            cursor.execute("""
                INSERT INTO learning_insights 
                (insight_type, asset_type, strategy_name, key_finding, 
                 supporting_data, confidence_level, applicable_conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                insight.get("type", ""),
                insight.get("asset_type", "all"),
                insight.get("strategy_name", "all"),
                insight.get("finding", ""),
                json.dumps(insight.get("data", {})),
                insight.get("confidence", 0.5),
                insight.get("applicable_conditions", "general")
            ))
        
        self.performance_db.commit()
    
    def store_strategy_recommendations(self, recommendations: List[Dict[str, Any]]) -> None:
        """Store strategy recommendations in database."""
        cursor = self.performance_db.cursor()
        
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO strategy_recommendations 
                (child_id, strategy_name, recommended_config, confidence_score,
                 expected_improvement, market_regime, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (
                rec.get("child_id", ""),
                rec.get("strategy_name", ""),
                json.dumps(rec.get("config", {})),
                rec.get("confidence", 0.5),
                rec.get("expected_improvement", 0),
                rec.get("market_regime", "all")
            ))
        
        self.performance_db.commit()
    
    def get_optimizations_for_child(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get pending optimizations for a specific child bot."""
        child_id = input_data.get("child_id")
        
        if not child_id:
            return {"error": "child_id is required"}
        
        try:
            cursor = self.performance_db.cursor()
            cursor.execute("""
                SELECT * FROM strategy_recommendations 
                WHERE child_id = ? AND status = 'pending'
                ORDER BY timestamp DESC
                LIMIT 10
            """, (child_id,))
            
            recommendations = []
            for row in cursor.fetchall():
                recommendations.append({
                    "id": row[0],
                    "strategy_name": row[3],
                    "config": json.loads(row[4]),
                    "confidence": row[5],
                    "expected_improvement": row[6],
                    "market_regime": row[7],
                    "timestamp": row[2]
                })
            
            return {
                "child_id": child_id,
                "recommendations": recommendations,
                "count": len(recommendations)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting optimizations for {child_id}: {e}")
            return {"error": str(e)}
    
    def get_global_insights(self) -> Dict[str, Any]:
        """Get global insights across all child bots."""
        try:
            cursor = self.performance_db.cursor()
            
            # Get recent insights
            cursor.execute("""
                SELECT * FROM learning_insights 
                ORDER BY timestamp DESC 
                LIMIT 20
            """)
            
            insights = []
            for row in cursor.fetchall():
                insights.append({
                    "type": row[2],
                    "asset_type": row[3],
                    "strategy": row[4],
                    "finding": row[5],
                    "confidence": row[7],
                    "timestamp": row[1]
                })
            
            # Get system statistics
            cursor.execute("SELECT COUNT(*) FROM child_bots WHERE status = 'active'")
            active_children = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM performance_data WHERE timestamp >= datetime('now', '-24 hours')")
            recent_trades = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT asset_type, COUNT(*) as count, AVG(pnl) as avg_pnl 
                FROM performance_data 
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY asset_type
            """)
            
            asset_performance = {}
            for row in cursor.fetchall():
                asset_performance[row[0]] = {
                    "trade_count": row[1],
                    "avg_pnl": round(row[2], 4) if row[2] else 0
                }
            
            return {
                "insights": insights,
                "system_stats": {
                    "active_children": active_children,
                    "recent_trades_24h": recent_trades,
                    "asset_performance_7d": asset_performance
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting global insights: {e}")
            return {"error": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        try:
            cursor = self.performance_db.cursor()
            
            # Child bot status
            cursor.execute("SELECT status, COUNT(*) FROM child_bots GROUP BY status")
            child_status = dict(cursor.fetchall())
            
            # Recent activity
            cursor.execute("SELECT COUNT(*) FROM performance_data WHERE timestamp >= datetime('now', '-1 hour')")
            recent_activity = cursor.fetchone()[0]
            
            # Database size
            cursor.execute("SELECT COUNT(*) FROM performance_data")
            total_trades = cursor.fetchone()[0]
            
            return {
                "status": "active",
                "child_bots": child_status,
                "recent_activity_1h": recent_activity,
                "total_trades_stored": total_trades,
                "last_learning_cycle": self.get_last_learning_cycle(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    def get_last_learning_cycle(self) -> str:
        """Get timestamp of last learning cycle."""
        try:
            cursor = self.performance_db.cursor()
            cursor.execute("SELECT MAX(timestamp) FROM learning_insights")
            result = cursor.fetchone()[0]
            return result if result else "Never"
        except:
            return "Unknown"
    
    def start_learning_scheduler(self):
        """Start the automated learning scheduler."""
        def run_scheduler():
            schedule.every().hour.do(lambda: self.execute({"command": "learn_and_optimize"}))
            
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        self.logger.info("Learning scheduler started")
    
    def activate(self):
        """Activate the parent controller."""
        super().activate()
        self.start_learning_scheduler()
        self.logger.info("Parent Controller activated")
    
    def deactivate(self):
        """Deactivate the parent controller."""
        super().deactivate()
        if self.performance_db:
            self.performance_db.close()
        self.logger.info("Parent Controller deactivated")