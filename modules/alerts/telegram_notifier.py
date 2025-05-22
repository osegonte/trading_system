import requests
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from core.interfaces import IModule

class TelegramNotifier(IModule):
    """Send notifications via Telegram bot."""
    
    def __init__(self, module_id: Optional[str] = "telegram_notifier"):
        super().__init__(module_id=module_id)
        self.bot_token = ""
        self.chat_id = ""
        self.logger = logging.getLogger(f"TelegramNotifier.{module_id}")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure Telegram notifier."""
        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> bool:
        """Send notification via Telegram."""
        message = input_data.get("message", "")
        if not message or not self.bot_token or not self.chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("Telegram notification sent successfully")
                return True
            else:
                self.logger.error(f"Failed to send Telegram notification: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def send_trade_alert(self, symbol: str, action: str, price: float, quantity: float):
        """Send trade execution alert."""
        message = f"""
🚨 <b>Trade Alert</b> 🚨

<b>Symbol:</b> {symbol}
<b>Action:</b> {action}
<b>Price:</b> ${price:.2f}
<b>Quantity:</b> {quantity}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self.execute({"message": message})
    
    def send_portfolio_update(self, total_value: float, pnl: float, pnl_pct: float):
        """Send portfolio update."""
        emoji = "📈" if pnl >= 0 else "📉"
        message = f"""
{emoji} <b>Portfolio Update</b> {emoji}

<b>Total Value:</b> ${total_value:.2f}
<b>P&L:</b> ${pnl:.2f} ({pnl_pct:.2f}%)
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self.execute({"message": message})
