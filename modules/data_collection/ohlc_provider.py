# modules/data_collection/ohlc_provider.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import requests
import time

from core.interfaces import IModule
from core.models import PriceBar, PriceData

class YahooFinanceProvider(IModule):
    """Enhanced data collection module that fetches OHLC data from Yahoo Finance for stocks, forex, and crypto."""
    
    def __init__(self, module_id: Optional[str] = "yahoo_finance"):
        super().__init__(module_id=module_id)
        self.symbols = []
        self.timeframe = "1d"
        self.lookback_days = 30
        self.cache = {}  # Symbol -> PriceData mapping
        self.last_fetch = {}  # Symbol -> datetime mapping
        self.asset_types = {}  # Symbol -> asset_type mapping
        
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
        
        # Detect asset types for symbols
        self._detect_asset_types()
        
        super().configure(config)
    
    def _detect_asset_types(self) -> None:
        """Detect asset types for configured symbols."""
        for symbol in self.symbols:
            self.asset_types[symbol] = self._get_asset_type(symbol)
    
    def _get_asset_type(self, symbol: str) -> str:
        """Determine asset type from symbol format."""
        symbol_upper = symbol.upper()
        
        # Crypto patterns
        if symbol_upper.endswith('-USD') or symbol_upper.endswith('USD'):
            return 'crypto'
        if symbol_upper in ['BTC', 'ETH', 'ADA', 'DOT', 'LINK', 'LTC', 'XRP', 'DOGE', 'MATIC', 'SOL']:
            return 'crypto'
        
        # Forex patterns
        if '=' in symbol or len(symbol) == 6 and not any(char.isdigit() for char in symbol):
            return 'forex'
        if symbol_upper.endswith('=X'):
            return 'forex'
        # Precious metals (commodities traded like forex)
        if symbol_upper in ['XAUUSD', 'XAGUSD', 'GC=F', 'SI=F'] or symbol_upper.startswith('XAU') or symbol_upper.startswith('XAG'):
            return 'forex'
        
        # Default to stock
        return 'stock'
    
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
            
            # Format symbol for different asset types
            formatted_symbol = self._format_symbol_for_yahoo(symbol)
            
            # Convert timeframe to yfinance interval format
            interval = self._convert_timeframe(self.timeframe)
            
            # Get data from Yahoo Finance
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            try:
                # Add retry logic for API calls
                df = None
                for attempt in range(3):
                    try:
                        df = yf.download(formatted_symbol, start=start_date, end=end_date, 
                                       interval=interval, progress=False)
                        if not df.empty:
                            break
                    except Exception as e:
                        if attempt == 2:
                            raise e
                        time.sleep(1)  # Wait before retry
                
                if df is None or df.empty:
                    print(f"No data available for {symbol}")
                    continue
                
                # Handle multi-index columns if present
                if df.columns.nlevels > 1:
                    df.columns = df.columns.droplevel(1)
                
                # Convert to PriceData object
                bars = []
                for idx, row in df.iterrows():
                    # Handle missing values
                    if pd.isna(row['Open']) or pd.isna(row['Close']):
                        continue
                        
                    bar = PriceBar(
                        timestamp=idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx,
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=float(row['Volume']) if not pd.isna(row['Volume']) else 0.0
                    )
                    bars.append(bar)
                
                if not bars:
                    print(f"No valid bars for {symbol}")
                    continue
                
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
    
    def _format_symbol_for_yahoo(self, symbol: str) -> str:
        """Format symbol for Yahoo Finance API based on asset type."""
        asset_type = self.asset_types.get(symbol, self._get_asset_type(symbol))
        
        if asset_type == 'crypto':
            # Handle crypto symbols
            if not symbol.endswith('-USD') and not symbol.endswith('USD'):
                # Common crypto symbols
                crypto_map = {
                    'BTC': 'BTC-USD',
                    'ETH': 'ETH-USD',
                    'ADA': 'ADA-USD',
                    'DOT': 'DOT-USD',
                    'LINK': 'LINK-USD',
                    'LTC': 'LTC-USD',
                    'XRP': 'XRP-USD',
                    'DOGE': 'DOGE-USD',
                    'MATIC': 'MATIC-USD',
                    'SOL': 'SOL-USD',
                    'AVAX': 'AVAX-USD',
                    'ATOM': 'ATOM-USD',
                    'UNI': 'UNI-USD',
                    'AAVE': 'AAVE-USD'
                }
                return crypto_map.get(symbol.upper(), f"{symbol.upper()}-USD")
            return symbol
            
        elif asset_type == 'forex':
            # Handle forex symbols
            if '=' not in symbol and not symbol.endswith('=X'):
                # Common forex pairs
                forex_map = {
                    'EURUSD': 'EURUSD=X',
                    'GBPUSD': 'GBPUSD=X',
                    'USDJPY': 'USDJPY=X',
                    'USDCHF': 'USDCHF=X',
                    'AUDUSD': 'AUDUSD=X',
                    'USDCAD': 'USDCAD=X',
                    'NZDUSD': 'NZDUSD=X',
                    'EURGBP': 'EURGBP=X',
                    'EURJPY': 'EURJPY=X',
                    'GBPJPY': 'GBPJPY=X',
                    'XAUUSD': 'GC=F',  # Gold Futures
                    'XAGUSD': 'SI=F',  # Silver Futures
                    'GOLD': 'GC=F',    # Alternative Gold input
                    'SILVER': 'SI=F'   # Alternative Silver input
                }
                return forex_map.get(symbol.upper(), f"{symbol.upper()}=X")
            return symbol
            
        # Return as-is for stocks
        return symbol
    
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
    
    def add_symbol(self, symbol: str) -> None:
        """Add a new symbol to track."""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.asset_types[symbol] = self._get_asset_type(symbol)
    
    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from tracking."""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            self.asset_types.pop(symbol, None)
            self.cache.pop(symbol, None)
            self.last_fetch.pop(symbol, None)
    
    def get_asset_type(self, symbol: str) -> str:
        """Get asset type for a symbol."""
        return self.asset_types.get(symbol, self._get_asset_type(symbol))
    
    def get_supported_crypto_symbols(self) -> List[str]:
        """Get list of supported crypto symbols."""
        return ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD', 
                'LTC-USD', 'XRP-USD', 'DOGE-USD', 'MATIC-USD', 'SOL-USD',
                'AVAX-USD', 'ATOM-USD', 'UNI-USD', 'AAVE-USD']
    
    def get_supported_forex_symbols(self) -> List[str]:
        """Get list of supported forex symbols."""
        return ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'USDCHF=X', 
                'AUDUSD=X', 'USDCAD=X', 'NZDUSD=X', 'EURGBP=X',
                'EURJPY=X', 'GBPJPY=X', 'GC=F', 'SI=F']
    
    def get_supported_commodity_symbols(self) -> List[str]:
        """Get list of supported commodity symbols (precious metals)."""
        return ['GC=F', 'SI=F', 'CL=F', 'NG=F']  # Gold, Silver, Oil, Natural Gas