# modules/sync/report_uploader.py
import json
import os
from datetime import datetime
from typing import Dict, Any, List
import logging
from pathlib import Path

class ReportUploader:
    """Uploads child bot performance data to parent system."""
    
    def __init__(self, child_id: str):
        self.child_id = child_id
        self.logger = logging.getLogger(f"ReportUploader.{child_id}")
        self.upload_path = Path("data/parent/child_reports")
        self.upload_path.mkdir(parents=True, exist_ok=True)
        
    def upload_performance_report(self, trades: List[Dict], 
                                metrics: Dict[str, Any], 
                                config: Dict[str, Any],
                                market_conditions: Dict[str, Any] = None) -> bool:
        """Upload comprehensive performance report to parent."""
        try:
            report = {
                "child_id": self.child_id,
                "timestamp": datetime.now().isoformat(),
                "report_type": "performance",
                "trades": trades,
                "metrics": metrics,
                "config": config,
                "market_conditions": market_conditions or {},
                "system_info": self._get_system_info()
            }
            
            # Generate unique filename
            filename = f"{self.child_id}_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.upload_path / filename
            
            # Save report
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Uploaded performance report: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload performance report: {e}")
            return False
    
    def upload_trade_update(self, trade: Dict[str, Any]) -> bool:
        """Upload individual trade update."""
        try:
            update = {
                "child_id": self.child_id,
                "timestamp": datetime.now().isoformat(),
                "report_type": "trade_update",
                "trade": trade
            }
            
            filename = f"{self.child_id}_trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.upload_path / filename
            
            with open(filepath, 'w') as f:
                json.dump(update, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload trade update: {e}")
            return False
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information."""
        return {
            "python_version": os.sys.version,
            "timestamp": datetime.now().isoformat(),
            "child_version": "1.0.0"
        }

class UpdateFetcher:
    """Fetches strategy updates from parent system."""
    
    def __init__(self, child_id: str):
        self.child_id = child_id
        self.logger = logging.getLogger(f"UpdateFetcher.{child_id}")
        self.updates_path = Path("data/parent/optimizations")
        
    def fetch_pending_updates(self) -> List[Dict[str, Any]]:
        """Fetch pending optimization updates from parent."""
        updates = []
        
        try:
            if not self.updates_path.exists():
                return updates
            
            # Look for updates targeting this child
            for file_path in self.updates_path.glob(f"{self.child_id}_update_*.json"):
                try:
                    with open(file_path, 'r') as f:
                        update = json.load(f)
                    
                    if update.get("status") == "pending":
                        updates.append(update)
                        
                        # Mark as fetched
                        update["status"] = "fetched"
                        update["fetched_at"] = datetime.now().isoformat()
                        
                        with open(file_path, 'w') as f:
                            json.dump(update, f, indent=2, default=str)
                            
                except Exception as e:
                    self.logger.error(f"Error processing update file {file_path}: {e}")
            
            if updates:
                self.logger.info(f"Fetched {len(updates)} pending updates")
            
        except Exception as e:
            self.logger.error(f"Error fetching updates: {e}")
        
        return updates
    
    def apply_update(self, update: Dict[str, Any]) -> bool:
        """Apply strategy update to child bot."""
        try:
            update_type = update.get("update_type", "config")
            
            if update_type == "config":
                return self._apply_config_update(update)
            elif update_type == "strategy":
                return self._apply_strategy_update(update)
            elif update_type == "risk_params":
                return self._apply_risk_update(update)
            else:
                self.logger.warning(f"Unknown update type: {update_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error applying update: {e}")
            return False
    
    def _apply_config_update(self, update: Dict[str, Any]) -> bool:
        """Apply configuration update."""
        # This would integrate with your existing config system
        self.logger.info(f"Applying config update: {update.get('description', 'No description')}")
        return True
    
    def _apply_strategy_update(self, update: Dict[str, Any]) -> bool:
        """Apply strategy parameter update."""
        self.logger.info(f"Applying strategy update: {update.get('description', 'No description')}")
        return True
    
    def _apply_risk_update(self, update: Dict[str, Any]) -> bool:
        """Apply risk management update."""
        self.logger.info(f"Applying risk update: {update.get('description', 'No description')}")
        return True