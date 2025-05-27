import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TwitterFeatureBuilder:
    """Build Twitter engagement features for sentiment strategy."""
    
    def __init__(self):
        self.logger = logging.getLogger("TwitterFeatureBuilder")
        self.output_path = Path("data/features/twitter_engagement")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # NASDAQ symbols to track
        self.symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
            "PYPL", "ADBE", "CRM", "INTC", "AMD", "QCOM", "AVGO", "TXN"
        ]
        
    def build_features(self) -> bool:
        """Build and save Twitter engagement features."""
        try:
            self.logger.info("Starting Twitter feature build")
            
            # Simulate Twitter data (replace with actual API integration)
            twitter_data = self._simulate_twitter_data()
            
            # Calculate engagement metrics
            engagement_features = self._calculate_engagement_features(twitter_data)
            
            if not engagement_features:
                self.logger.error("No engagement features generated")
                return False
            
            # Save features
            feature_df = pd.DataFrame(engagement_features)
            output_file = self.output_path / f"twitter_features_{datetime.now().strftime('%Y%m%d')}.parquet"
            feature_df.to_parquet(output_file)
            
            # Save latest version
            latest_file = self.output_path / "twitter_features_latest.parquet"
            feature_df.to_parquet(latest_file)
            
            self.logger.info(f"Saved {len(engagement_features)} Twitter engagement features")
            return True
            
        except Exception as e:
            self.logger.error(f"Error building Twitter features: {e}")
            return False
    
    def _simulate_twitter_data(self) -> dict:
        """Simulate Twitter engagement data (replace with real API)."""
        np.random.seed(42)  # For reproducible results
        
        twitter_data = {}
        
        for symbol in self.symbols:
            # Simulate monthly engagement data
            base_likes = np.random.randint(100, 5000)
            base_comments = int(base_likes * np.random.uniform(0.05, 0.3))
            
            twitter_data[symbol] = {
                'monthly_likes': base_likes,
                'monthly_comments': base_comments,
                'monthly_impressions': base_likes * np.random.randint(10, 50),
                'sentiment_score': np.random.uniform(0.3, 0.7),
                'mention_count': np.random.randint(50, 500),
                'retweets': int(base_likes * np.random.uniform(0.1, 0.4)),
                'unique_users': int(base_likes * np.random.uniform(0.7, 0.9)),
                'hashtag_mentions': np.random.randint(10, 100)
            }
            
        return twitter_data
    
    def _calculate_engagement_features(self, twitter_data: dict) -> list:
        """Calculate engagement features for all symbols."""
        features = []
        current_month = datetime.now().replace(day=1)
        
        for symbol, data in twitter_data.items():
            try:
                # Basic metrics
                likes = data.get('monthly_likes', 0)
                comments = data.get('monthly_comments', 0)
                impressions = data.get('monthly_impressions', 0)
                
                # Skip if insufficient data
                if likes < 20 or comments < 10:
                    continue
                
                # Calculate engagement ratio
                eng_ratio = comments / likes if likes > 0 else 0
                
                # Calculate other metrics
                engagement_rate = (likes + comments) / impressions if impressions > 0 else 0
                comment_rate = comments / impressions if impressions > 0 else 0
                virality_score = data.get('retweets', 0) / likes if likes > 0 else 0
                
                # Calculate percentile ranks (simplified)
                # In production, this would be calculated across all symbols
                eng_ratio_percentile = min(eng_ratio * 10, 1.0)  # Simplified percentile
                
                features.append({
                    'symbol': symbol,
                    'month': current_month,
                    'likes': likes,
                    'comments': comments,
                    'impressions': impressions,
                    'eng_ratio': eng_ratio,
                    'engagement_rate': engagement_rate,
                    'comment_rate': comment_rate,
                    'virality_score': virality_score,
                    'eng_ratio_percentile': eng_ratio_percentile,
                    'sentiment_score': data.get('sentiment_score', 0.5),
                    'mention_count': data.get('mention_count', 0),
                    'unique_users': data.get('unique_users', 0),
                    'timestamp': datetime.now()
                })
                
            except Exception as e:
                self.logger.error(f"Error calculating features for {symbol}: {e}")
                continue
        
        return features
