# Fix for Alpaca executor account info error
def get_account_info(self) -> dict:
    """Get account information with error handling."""
    try:
        if self.api:
            account = self.api.get_account()
            return {
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'day_trade_count': getattr(account, 'day_trade_count', 0),  # Handle missing attribute
                'trading_blocked': getattr(account, 'trading_blocked', False)
            }
    except Exception as e:
        self.logger.error(f"Error getting account info: {e}")
    
    return {
        'buying_power': 0.0,
        'portfolio_value': 0.0,
        'cash': 0.0,
        'day_trade_count': 0,
        'trading_blocked': False
    }