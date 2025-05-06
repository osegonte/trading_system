# modules/data_collection/ohlc_provider.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.interfaces import IModule
from core.models import PriceBar, PriceData

class YahooFinanceProvider(IModule):
    """Data collection module that fetches OHLC data from Yahoo Finance."""
    
    def __init__(self, module_id: Optional[str] = "yahoo_finance"):
        super().__init__(module_id=module_id)
        self.symbols = []
        self.timeframe = "1d"
        self.lookback_days = 30
        self.cache = {}  # Symbol -> PriceData mapping
        self.last_fetch = {}  # Symbol -> datetime mapping
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the Yahoo Finance provider.
        
        Args:
            config: Configuration dictionary with the following options:
                - symbols: List of ticker symbols
                - timeframe: Timeframe for the data (e.g., "1d", "1h")
                - lookback_days: Number of days to fetch
        """
        self.symbols = config.get("symbols", [])
        self.timeframe = config.get("timeframe", "1d")
        self.lookback_days = config.get("lookback_days", 30)
        super().configure(config)
    
    def execute(self, symbols: Optional[list] = None) -> Dict[str, PriceData]:
        """Fetch OHLC data for configured symbols.
        
        Args:
            symbols: Optional list of symbols to fetch (overrides configured symbols)
            
        Returns:
            Dictionary mapping symbols to PriceData objects
        """
        fetch_symbols = symbols or self.symbols
        result = {}
        
        for symbol in fetch_symbols:
            # Check cache
            current_time = datetime.now()
            if (symbol in self.cache and symbol in self.last_fetch and
                    (current_time - self.last_fetch[symbol]).total_seconds() < 300):  # 5-minute cache
                result[symbol] = self.cache[symbol]
                continue
            
            # Convert timeframe to yfinance interval format
            interval = self._convert_timeframe(self.timeframe)
            
            # Get data from Yahoo Finance
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            try:
                df = yf.download(symbol, start=start_date, end=end_date, interval=interval)
                
                # Convert to PriceData object
                bars = []
                for idx, row in df.iterrows():
                    bar = PriceBar(
                        timestamp=idx.to_pydatetime(),
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=float(row['Volume'])
                    )
                    bars.append(bar)
                
                price_data = PriceData(
                    symbol=symbol,
                    timeframe=self.timeframe,
                    bars=bars,
                    last_updated=current_time
                )
                
                # Update cache
                self.cache[symbol] = price_data
                self.last_fetch[symbol] = current_time
                
                result[symbol] = price_data
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                # If we have cached data, use it
                if symbol in self.cache:
                    result[symbol] = self.cache[symbol]
        
        return result
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert our timeframe format to yfinance interval format."""
        mapping = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1wk",
            "1mo": "1mo"
        }
        return mapping.get(timeframe, "1d")