import alpaca_trade_api as tradeapi
from alpaca_trade_api.stream import Stream
import asyncio
import threading
from typing import Dict, Any, Callable, Optional
import logging

from core.interfaces import IModule

class AlpacaLiveDataStreamer(IModule):
    """Live data streaming from Alpaca."""
    
    def __init__(self, module_id: Optional[str] = "live_data_streamer"):
        super().__init__(module_id=module_id)
        self.api_key = ""
        self.secret_key = ""
        self.base_url = "https://paper-api.alpaca.markets"
        self.stream = None
        self.subscribed_symbols = set()
        self.data_handlers = {}
        self.logger = logging.getLogger(f"LiveDataStreamer.{module_id}")
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the live data streamer."""
        self.api_key = config.get("api_key", "")
        self.secret_key = config.get("secret_key", "")
        self.base_url = config.get("base_url", "https://paper-api.alpaca.markets")
        
        if self.api_key and self.secret_key:
            self.stream = Stream(
                self.api_key,
                self.secret_key,
                base_url=self.base_url,
                data_feed='iex'  # Use IEX feed for paper trading
            )
            
            # Set up default handlers
            self.stream.subscribe_trades(self._handle_trade, "*")
            self.stream.subscribe_quotes(self._handle_quote, "*")
            
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> None:
        """Start the live data stream."""
        if self.stream and not self.is_active:
            try:
                # Start streaming in a separate thread
                def run_stream():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    self.stream.run()
                
                threading.Thread(target=run_stream, daemon=True).start()
                self.is_active = True
                self.logger.info("Live data streaming started")
            except Exception as e:
                self.logger.error(f"Error starting stream: {e}")
    
    def subscribe_symbol(self, symbol: str, handler: Callable = None):
        """Subscribe to live data for a symbol."""
        if symbol not in self.subscribed_symbols:
            self.subscribed_symbols.add(symbol)
            if handler:
                self.data_handlers[symbol] = handler
            self.logger.info(f"Subscribed to {symbol}")
    
    def _handle_trade(self, trade):
        """Handle incoming trade data."""
        symbol = trade.symbol
        if symbol in self.data_handlers:
            self.data_handlers[symbol](trade)
        
        # Log trade info
        self.logger.debug(f"Trade: {symbol} @ ${trade.price} ({trade.size} shares)")
    
    def _handle_quote(self, quote):
        """Handle incoming quote data."""
        symbol = quote.symbol
        if symbol in self.data_handlers:
            self.data_handlers[symbol](quote)
