import pandas as pd
import numpy as np
from arch import arch_model
from pathlib import Path
from datetime import datetime, timedelta
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_collection.ohlc_provider import YahooFinanceProvider

class GARCHForecastBuilder:
    """Build GARCH volatility forecasts for intraday strategy."""
    
    def __init__(self):
        self.logger = logging.getLogger("GARCHForecastBuilder")
        self.output_path = Path("data/features/garch_forecasts")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # High-liquidity symbols for intraday trading
        self.symbols = ["SPY", "QQQ", "BTC-USD", "AAPL", "TSLA", "NVDA"]
        self.rolling_window = 180
        
    def build_forecasts(self) -> bool:
        """Build and save GARCH forecasts."""
        try:
            self.logger.info("Starting GARCH forecast build")
            
            # Initialize data provider
            data_provider = YahooFinanceProvider()
            data_provider.configure({
                "symbols": self.symbols,
                "timeframe": "1d",
                "lookback_days": 365  # 1 year of daily data
            })
            
            # Fetch price data
            price_data = data_provider.execute()
            
            forecasts = []
            
            for symbol, data in price_data.items():
                try:
                    forecast = self._build_symbol_forecast(symbol, data)
                    if forecast:
                        forecasts.append(forecast)
                except Exception as e:
                    self.logger.error(f"Error forecasting {symbol}: {e}")
                    continue
            
            if not forecasts:
                self.logger.error("No forecasts generated")
                return False
            
            # Save forecasts
            forecast_df = pd.DataFrame(forecasts)
            output_file = self.output_path / f"garch_forecasts_{datetime.now().strftime('%Y%m%d')}.parquet"
            forecast_df.to_parquet(output_file)
            
            # Save latest version
            latest_file = self.output_path / "garch_forecasts_latest.parquet"
            forecast_df.to_parquet(latest_file)
            
            self.logger.info(f"Saved {len(forecasts)} GARCH forecasts")
            return True
            
        except Exception as e:
            self.logger.error(f"Error building GARCH forecasts: {e}")
            return False
    
    def _build_symbol_forecast(self, symbol: str, data) -> dict:
        """Build GARCH forecast for a single symbol."""
        try:
            df = data.to_dataframe()
            
            if len(df) < self.rolling_window + 30:
                return None
            
            # Calculate returns
            returns = df['close'].pct_change().dropna() * 100
            
            # Use rolling window
            recent_returns = returns.tail(self.rolling_window)
            
            # Fit GARCH(1,3) model
            garch_model = arch_model(
                recent_returns,
                vol='GARCH',
                p=1,
                q=3,
                mean='Constant'
            )
            
            garch_fit = garch_model.fit(disp='off', show_warning=False)
            
            # Generate forecast
            forecast = garch_fit.forecast(horizon=1)
            var_pred = forecast.variance.iloc[-1, 0]
            
            # Calculate rolling variance for comparison
            rolling_var = recent_returns.var()
            
            # Calculate premium
            premium = (var_pred - rolling_var) / rolling_var if rolling_var > 0 else 0
            
            # Calculate premium z-score
            premium_zscore = self._calculate_premium_zscore(returns, var_pred)
            
            # Determine signal
            signal_d = 0
            if premium_zscore > 1.5:
                signal_d = 1  # Over-forecast
            elif premium_zscore < -1.5:
                signal_d = -1  # Under-forecast
            
            return {
                'symbol': symbol,
                'date': datetime.now().date(),
                'var_pred': var_pred,
                'rolling_var': rolling_var,
                'premium': premium,
                'premium_zscore': premium_zscore,
                'signal_d': signal_d,
                'model_aic': garch_fit.aic,
                'model_bic': garch_fit.bic,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error building forecast for {symbol}: {e}")
            return None
    
    def _calculate_premium_zscore(self, returns: pd.Series, var_pred: float) -> float:
        """Calculate z-score of volatility risk premium."""
        try:
            # Rolling calculation of premium
            premiums = []
            window_size = min(60, len(returns) - 30)
            
            for i in range(30, len(returns)):
                window_returns = returns.iloc[i-window_size:i]
                
                # Fit GARCH model for this window
                try:
                    temp_model = arch_model(window_returns, vol='GARCH', p=1, q=3, mean='Constant')
                    temp_fit = temp_model.fit(disp='off', show_warning=False)
                    temp_forecast = temp_fit.forecast(horizon=1)
                    temp_var_pred = temp_forecast.variance.iloc[-1, 0]
                    
                    # Calculate premium
                    window_var = window_returns.var()
                    temp_premium = (temp_var_pred - window_var) / window_var if window_var > 0 else 0
                    premiums.append(temp_premium)
                    
                except:
                    continue
            
            if len(premiums) < 10:
                return 0
            
            # Current premium
            current_var = returns.var()
            current_premium = (var_pred - current_var) / current_var if current_var > 0 else 0
            
            # Z-score
            premium_mean = np.mean(premiums)
            premium_std = np.std(premiums)
            
            if premium_std > 0:
                return (current_premium - premium_mean) / premium_std
            else:
                return 0
                
        except Exception as e:
            self.logger.error(f"Error calculating premium z-score: {e}")
            return 0