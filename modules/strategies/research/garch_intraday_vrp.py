# modules/strategies/research/garch_intraday_vrp.py
import numpy as np
import pandas as pd
import pandas_ta as ta
from arch import arch_model
from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional, Tuple
import logging

from core.interfaces import IModule
from core.models import SignalData, SignalType

class GARCHIntradayVRPStrategy(IModule):
    """
    Research-grade GARCH Intraday Volatility Risk Premium strategy.
    Trades volatility mean reversion on single liquid symbols.
    """
    
    def __init__(self, module_id: Optional[str] = "garch_intraday_vrp"):
        super().__init__(module_id=module_id)
        self.logger = logging.getLogger("GARCHIntradayVRPStrategy")
        
        # Strategy parameters
        self.rolling_window = 180  # Days for GARCH estimation
        self.volatility_threshold = 1.5  # Sigma threshold for signals
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.bb_period = 20
        self.bb_std = 2
        
        # Intraday timing
        self.start_time = time(9, 30)  # 9:30 AM
        self.end_time = time(15, 45)   # 3:45 PM (15 min before close)
        self.max_trades_per_day = 1
        
        # Risk management
        self.position_size_pct = 0.001  # 0.1% of account per trade
        self.stop_loss_atr_mult = 2.0
        
        # Models and state
        self.garch_models = {}
        self.daily_forecasts = {}
        self.todays_trades = {}
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure GARCH intraday strategy."""
        self.rolling_window = config.get("rolling_window", 180)
        self.volatility_threshold = config.get("volatility_threshold", 1.5)
        self.position_size_pct = config.get("position_size_pct", 0.001)
        super().configure(config)
        
    def execute(self, input_data: Dict[str, Any]) -> List[SignalData]:
        """Execute GARCH intraday VRP strategy."""
        price_data = input_data.get("price_data", {})
        intraday_data = input_data.get("intraday_data", {})
        current_time = input_data.get("current_time", datetime.now())
        
        # Check if we're in trading hours
        if not self._is_trading_time(current_time):
            return []
        
        signals = []
        
        for symbol in price_data.keys():
            try:
                # Update daily GARCH forecast
                self._update_daily_forecast(symbol, price_data[symbol])
                
                # Check for intraday signal
                signal = self._check_intraday_signal(
                    symbol, 
                    price_data[symbol], 
                    intraday_data.get(symbol),
                    current_time
                )
                
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {e}")
                continue
        
        return signals
    
    def _is_trading_time(self, current_time: datetime) -> bool:
        """Check if current time is within trading hours."""
        current_time_only = current_time.time()
        return self.start_time <= current_time_only <= self.end_time
    
    def _update_daily_forecast(self, symbol: str, price_data) -> None:
        """Update daily GARCH volatility forecast."""
        try:
            # Convert to DataFrame and calculate returns
            df = price_data.to_dataframe()
            
            if len(df) < self.rolling_window + 30:
                return
            
            # Calculate daily returns
            returns = df['close'].pct_change().dropna() * 100  # Convert to percentage
            
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
            
            # Fit model
            garch_fit = garch_model.fit(disp='off', show_warning=False)
            
            # Generate 1-day ahead forecast
            forecast = garch_fit.forecast(horizon=1)
            var_forecast = forecast.variance.iloc[-1, 0]
            
            # Calculate volatility risk premium
            rolling_var = recent_returns.var()
            premium = (var_forecast - rolling_var) / rolling_var if rolling_var > 0 else 0
            
            # Calculate z-score of premium
            premium_series = []
            window_size = min(60, len(recent_returns) - 30)
            
            for i in range(30, len(recent_returns)):
                window_returns = recent_returns.iloc[i-window_size:i]
                temp_model = arch_model(window_returns, vol='GARCH', p=1, q=3, mean='Constant')
                temp_fit = temp_model.fit(disp='off', show_warning=False)
                temp_forecast = temp_fit.forecast(horizon=1)
                temp_var_forecast = temp_forecast.variance.iloc[-1, 0]
                temp_premium = (temp_var_forecast - window_returns.var()) / window_returns.var()
                premium_series.append(temp_premium)
            
            premium_mean = np.mean(premium_series)
            premium_std = np.std(premium_series)
            premium_zscore = (premium - premium_mean) / premium_std if premium_std > 0 else 0
            
            # Store forecast
            self.daily_forecasts[symbol] = {
                'var_forecast': var_forecast,
                'premium': premium,
                'premium_zscore': premium_zscore,
                'signal_direction': self._get_signal_direction(premium_zscore),
                'forecast_date': datetime.now().date()
            }
            
            self.logger.debug(f"{symbol}: Var forecast={var_forecast:.6f}, Premium z-score={premium_zscore:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error updating GARCH forecast for {symbol}: {e}")
    
    def _get_signal_direction(self, premium_zscore: float) -> int:
        """Get signal direction based on premium z-score."""
        if premium_zscore > self.volatility_threshold:
            return -1  # Over-forecast volatility -> fade moves
        elif premium_zscore < -self.volatility_threshold:
            return 1   # Under-forecast volatility -> momentum
        else:
            return 0   # No signal
    
    def _check_intraday_signal(self, symbol: str, price_data, intraday_data, 
                             current_time: datetime) -> Optional[SignalData]:
        """Check for intraday signal based on GARCH forecast and technical conditions."""
        
        # Check if we already traded this symbol today
        today = current_time.date()
        if symbol in self.todays_trades and self.todays_trades[symbol].get('date') == today:
            if self.todays_trades[symbol]['count'] >= self.max_trades_per_day:
                return None
        
        # Get daily forecast
        forecast = self.daily_forecasts.get(symbol)
        if not forecast or forecast['forecast_date'] != today:
            return None
        
        signal_direction = forecast['signal_direction']
        if signal_direction == 0:
            return None
        
        # Get intraday price data (5-minute bars)
        if not intraday_data or not intraday_data.bars:
            return None
        
        # Convert intraday data to DataFrame
        intraday_df = intraday_data.to_dataframe()
        if len(intraday_df) < 20:  # Need enough data for indicators
            return None
        
        # Calculate intraday indicators
        current_price = intraday_df['close'].iloc[-1]
        
        # RSI
        rsi = ta.rsi(intraday_df['close'], length=14).iloc[-1]
        
        # Bollinger Bands
        bb = ta.bbands(intraday_df['close'], length=self.bb_period, std=self.bb_std)
        bb_upper = bb[f'BBU_{self.bb_period}_{self.bb_std}'].iloc[-1]
        bb_lower = bb[f'BBL_{self.bb_period}_{self.bb_std}'].iloc[-1]
        
        # Check for signal conditions
        signal = None
        
        if signal_direction == -1:  # Fade moves (high volatility forecast)
            # Long signal: oversold RSI + price below lower BB
            if rsi < self.rsi_oversold and current_price < bb_lower:
                signal = SignalData(
                    symbol=symbol,
                    signal_type=SignalType.ENTRY_LONG,
                    price=current_price,
                    timestamp=current_time,
                    confidence=0.75,
                    metadata={
                        "strategy": "garch_intraday_vrp",
                        "signal_type": "volatility_fade_long",
                        "garch_premium_zscore": forecast['premium_zscore'],
                        "rsi": rsi,
                        "bb_position": "below_lower",
                        "position_size_pct": self.position_size_pct,
                        "intraday_only": True
                    }
                )
        
        # Update trade count if signal generated
        if signal:
            if symbol not in self.todays_trades:
                self.todays_trades[symbol] = {'date': today, 'count': 0}
            self.todays_trades[symbol]['count'] += 1
        
        return signal