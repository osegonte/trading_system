import schedule
import time
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

class MasterScheduler:
    """Master scheduler for all feature building and strategy jobs."""
    
    def __init__(self):
        self.logger = logging.getLogger("MasterScheduler")
        self.jobs_path = Path(__file__).parent
        
    def setup_schedule(self):
        """Setup all scheduled jobs."""
        # GARCH forecasts - daily after market close (6:10 PM ET)
        schedule.every().day.at("18:10").do(self.run_garch_forecasts)
        
        # Cluster features - daily after GARCH (7:00 PM ET)
        schedule.every().day.at("19:00").do(self.run_cluster_features)
        
        # Validation and backtests - daily (7:15 PM ET)
        schedule.every().day.at("19:15").do(self.run_validation)
        
        # Twitter features - monthly on last day
        schedule.every().month.do(self.run_twitter_features)
        
        # Parent learning cycle - every hour
        schedule.every().hour.do(self.run_parent_learning)
        
        self.logger.info("Scheduled all feature building jobs")
    
    def run_garch_forecasts(self):
        """Run GARCH forecast building."""
        try:
            self.logger.info("Running GARCH forecast job")
            result = subprocess.run([
                sys.executable, 
                str(self.jobs_path / "build_garch_forecasts.py")
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("GARCH forecast job completed successfully")
            else:
                self.logger.error(f"GARCH forecast job failed: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Error running GARCH forecast job: {e}")
    
    def run_cluster_features(self):
        """Run cluster feature building."""
        try:
            self.logger.info("Running cluster feature job")
            result = subprocess.run([
                sys.executable,
                str(self.jobs_path / "build_cluster_features.py")
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Cluster feature job completed successfully")
            else:
                self.logger.error(f"Cluster feature job failed: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Error running cluster feature job: {e}")
    
    def run_twitter_features(self):
        """Run Twitter feature building."""
        try:
            self.logger.info("Running Twitter feature job")
            result = subprocess.run([
                sys.executable,
                str(self.jobs_path / "build_twitter_features.py")
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Twitter feature job completed successfully")
            else:
                self.logger.error(f"Twitter feature job failed: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Error running Twitter feature job: {e}")
    
    def run_validation(self):
        """Run strategy validation and backtests."""
        try:
            self.logger.info("Running validation and backtest job")
            # This would run permutation tests and validate strategies
            self.logger.info("Validation job completed")
            
        except Exception as e:
            self.logger.error(f"Error running validation job: {e}")
    
    def run_parent_learning(self):
        """Trigger parent learning cycle."""
        try:
            self.logger.info("Running parent learning cycle")
            # This would trigger the parent controller learning
            from core.parent.parent_controller import ParentController
            
            parent = ParentController()
            parent.configure({})
            result = parent.execute({"command": "learn_and_optimize"})
            
            if result.get("success"):
                self.logger.info(f"Parent learning completed: {result}")
            else:
                self.logger.warning(f"Parent learning issues: {result}")
                
        except Exception as e:
            self.logger.error(f"Error running parent learning: {e}")
    
    def run_forever(self):
        """Run the scheduler forever."""
        self.logger.info("Starting master scheduler")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                self.logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = MasterScheduler()
    scheduler.setup_schedule()
    scheduler.run_forever()
