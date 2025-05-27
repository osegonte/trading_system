# jobs/build_cluster_features.py
import pandas as pd
import numpy as np
import pandas_ta as ta
from pathlib import Path
from datetime import datetime, timedelta
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_collection.ohlc_provider import YahooFinanceProvider

class ClusterFeatureBuilder:
    """Build features for cluster momentum strategy."""
    
    def __init__(self):
        self.logger = logging.getLogger("ClusterFeatureBuilder")
        self.output_path = Path("data/features/cluster_momentum")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Stock universe (S&P 500 subset for demo)
        self.stock_universe = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
            "JPM", "JNJ", "V", "PG", "UNH", "HD", "DIS", "MA", "BAC", "ADBE",
            "CRM", "PYPL", "INTC", "CMCSA", "PFE", "T", "VZ", "KO", "PEP",
            "WMT", "ABT", "MRK", "COST", "TMO", "ACN", "AVGO", "TXN", "LLY"
        ]
        
    def build_features(self) -> bool:
        """Build and save cluster features."""
        try:
            self.logger.info("Starting cluster feature build")
            
            # Initialize data provider
            data_provider = YahooFinanceProvider()
            data_provider.configure({
                "symbols": self.stock_universe,
                "timeframe": "1h",
                "lookback_days": 1500  # ~4 years of data
            })
            
            # Fetch price data
            self.logger.info("Fetching price data...")
            price_data = data_provider.execute()
            
            if not price_data:
                self.logger.error("No price data available")
                return False
            
            # Build feature matrix
            self.logger.info("Building feature matrix...")
            feature_df = self._build_feature_dataframe(price_data)
            
            if feature_df.empty:
                self.logger.error("Feature matrix is empty")
                return False
            
            # Add lookback windows for training
            feature_df = self._add_lookback_windows(feature_df)
            
            # Save features
            output_file = self.output_path / f"cluster_features_{datetime.now().strftime('%Y%m%d')}.parquet"
            feature_df.to_parquet(output_file)
            
            # Also save latest version
            latest_file = self.output_path / "cluster_features_latest.parquet"
            feature_df.to_parquet(latest_file)
            
            self.logger.info(f"Saved {len(feature_df)} feature records to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error building cluster features: {e}")
            return False
    
    def _build_feature_dataframe(self, price_data: dict) -> pd.DataFrame:
        """Build comprehensive feature DataFrame."""
        all_features = []
        
        for symbol, data in price_data.items():
            if not data.bars or len(data.bars) < 300:  # Need sufficient history
                continue
            
            try:
                df = data.to_dataframe()
                features = self._calculate_symbol_features(symbol, df)
                
                if features is not None:
                    all_features.append(features)
                    
            except Exception as e:
                self.logger.warning(f"Error calculating features for {symbol}: {e}")
                continue
        
        if not all_features:
            return pd.DataFrame()
        
        # Combine all features
        feature_df = pd.concat(all_features, ignore_index=True)
        
        # Add timestamp
        feature_df['timestamp'] = datetime.now()
        feature_df['build_date'] = datetime.now().date()
        
        return feature_df
    
    def _calculate_symbol_features(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all 18 features for a symbol."""
        try:
            # Resample to daily if hourly data
            if len(df) > 1000:  # Likely hourly data
                df_daily = df.resample('D').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
            else:
                df_daily = df.copy()
            
            if len(df_daily) < 252:  # Need at least 1 year
                return None
            
            # Calculate features for multiple time points
            features_list = []
            
            # Calculate features for last 60 days (rolling window)
            for i in range(max(252, len(df_daily) - 60), len(df_daily)):
                if i < 252:  # Need 252 days of history
                    continue
                
                window_df = df_daily.iloc[:i+1]
                feature_row = self._calculate_features_single_point(symbol, window_df, i)
                
                if feature_row is not None:
                    features_list.append(feature_row)
            
            if not features_list:
                return None
            
            return pd.DataFrame(features_list)
            
        except Exception as e:
            self.logger.error(f"Error calculating features for {symbol}: {e}")
            return None
    
    def _calculate_features_single_point(self, symbol: str, df: pd.DataFrame, index: int) -> dict:
        """Calculate features for a single time point."""
        try:
            # Basic info
            current_date = df.index[index]
            current_price = df['close'].iloc[index]
            
            # 1. RSI (14-period)
            rsi_series = ta.rsi(df['close'], length=14)
            rsi = rsi_series.iloc[index] if not rsi_series.isna().iloc[index] else 50
            
            # 2. ATR (14-period)
            atr_series = ta.atr(df['high'], df['low'], df['close'], length=14)
            atr = atr_series.iloc[index] if not atr_series.isna().iloc[index] else 0
            atr_ratio = (atr / current_price * 100) if current_price > 0 else 0
            
            # 3. Bollinger Band Position
            bb = ta.bbands(df['close'], length=20)
            bb_upper = bb[f'BBU_20_2.0'].iloc[index]
            bb_lower = bb[f'BBL_20_2.0'].iloc[index]
            bb_percent = ((current_price - bb_lower) / (bb_upper - bb_lower)) if (bb_upper - bb_lower) > 0 else 0.5
            
            # 4-7. Momentum indicators (1M, 3M, 6M, 12M)
            mom_1m = ((current_price / df['close'].iloc[max(0, index-21)]) - 1) * 100 if index >= 21 else 0
            mom_3m = ((current_price / df['close'].iloc[max(0, index-63)]) - 1) * 100 if index >= 63 else 0
            mom_6m = ((current_price / df['close'].iloc[max(0, index-126)]) - 1) * 100 if index >= 126 else 0
            mom_12m = ((current_price / df['close'].iloc[max(0, index-252)]) - 1) * 100 if index >= 252 else 0
            
            # 8. Volume ratio
            volume_sma = df['volume'].iloc[max(0, index-19):index+1].mean()
            volume_ratio = df['volume'].iloc[index] / volume_sma if volume_sma > 0 else 1
            
            # 9. MACD signal
            ema_12 = ta.ema(df['close'], length=12).iloc[index]
            ema_26 = ta.ema(df['close'], length=26).iloc[index]
            macd_signal = ((ema_12 - ema_26) / current_price * 100) if not pd.isna(ema_12) and not pd.isna(ema_26) else 0
            
            # 10. 52-week price position
            high_52w = df['high'].iloc[max(0, index-251):index+1].max()
            low_52w = df['low'].iloc[max(0, index-251):index+1].min()
            price_position = ((current_price - low_52w) / (high_52w - low_52w)) if (high_52w - low_52w) > 0 else 0.5
            
            # 11. ROC (10-period)
            roc_10 = ta.roc(df['close'], length=10).iloc[index] if index >= 10 else 0
            roc_10 = roc_10 if not pd.isna(roc_10) else 0
            
            # 12. Stochastic %K
            stoch = ta.stoch(df['high'], df['low'], df['close'])
            stoch_k = stoch['STOCHk_14_3_3'].iloc[index] if not stoch['STOCHk_14_3_3'].isna().iloc[index] else 50
            
            # 13. Regime indicator (SMA ratio)
            sma_50 = ta.sma(df['close'], length=50).iloc[index]
            sma_200 = ta.sma(df['close'], length=200).iloc[index]
            regime_indicator = ((sma_50 / sma_200 - 1) * 100) if not pd.isna(sma_50) and not pd.isna(sma_200) and sma_200 > 0 else 0
            
            # 14. Market beta (simplified)
            returns = df['close'].pct_change().iloc[max(0, index-60):index+1]
            market_beta = 1.0  # Would calculate vs market index in production
            
            # 15. Volatility rank
            returns_vol = returns.rolling(20).std()
            vol_current = returns_vol.iloc[-1] if len(returns_vol) > 0 and not pd.isna(returns_vol.iloc[-1]) else 0
            vol_series = returns_vol.dropna()
            volatility_rank = (vol_series <= vol_current).mean() if len(vol_series) > 0 else 0.5
            
            # 16. Mean reversion score (simplified Hurst)
            if len(returns) > 30:
                returns_clean = returns.dropna()
                if len(returns_clean) > 10:
                    mean_reversion = self._calculate_hurst_exponent(returns_clean)
                else:
                    mean_reversion = 0.5
            else:
                mean_reversion = 0.5
            
            # 17. Breakout strength
            high_20 = df['high'].iloc[max(0, index-19):index+1].max()
            low_20 = df['low'].iloc[max(0, index-19):index+1].min()
            if current_price >= high_20:
                breakout_strength = 1.0
            elif current_price <= low_20:
                breakout_strength = -1.0
            else:
                breakout_strength = (current_price - low_20) / (high_20 - low_20) * 2 - 1 if (high_20 - low_20) > 0 else 0
            
            # 18. Liquidity score
            avg_volume = df['volume'].iloc[max(0, index-19):index+1].mean()
            avg_dollar_volume = (df['close'] * df['volume']).iloc[max(0, index-19):index+1].mean()
            volume_score = min(avg_volume / 1000000, 1.0)
            dollar_score = min(avg_dollar_volume / 10000000, 1.0)
            liquidity_score = (volume_score + dollar_score) / 2
            
            return {
                'symbol': symbol,
                'date': current_date,
                'close_price': current_price,
                'rsi': rsi,
                'atr_ratio': atr_ratio,
                'bb_percent': bb_percent,
                'momentum_1m': mom_1m,
                'momentum_3m': mom_3m,
                'momentum_6m': mom_6m,
                'momentum_12m': mom_12m,
                'volume_ratio': volume_ratio,
                'macd_signal': macd_signal,
                'price_position_52w': price_position,
                'roc_10': roc_10,
                'stoch_k': stoch_k,
                'regime_indicator': regime_indicator,
                'market_beta': market_beta,
                'volatility_rank': volatility_rank,
                'mean_reversion': mean_reversion,
                'breakout_strength': breakout_strength,
                'liquidity_score': liquidity_score
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating single point features: {e}")
            return None
    
    def _calculate_hurst_exponent(self, returns: pd.Series) -> float:
        """Calculate simplified Hurst exponent."""
        try:
            lags = range(2, min(20, len(returns) // 2))
            tau = []
            
            for lag in lags:
                tau.append(np.sqrt(np.std(np.subtract(returns[lag:], returns[:-lag]))))
            
            if len(tau) > 1:
                poly = np.polyfit(np.log(lags), np.log(tau), 1)
                return poly[0] * 2.0
            else:
                return 0.5
                
        except:
            return 0.5
    
    def _add_lookback_windows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add lookback window identifiers for training."""
        df = df.copy()
        
        # Add 4-year training window identifier
        df['lookback_id'] = '4year_window'
        
        # Add cluster ID placeholder (will be filled by clustering algorithm)
        df['cluster_id'] = -1
        
        # Add optimization weight placeholder
        df['opt_weight'] = 0.0
        
        return df