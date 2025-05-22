from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from core.interfaces import IModule
from core.models import SignalData, SignalType

class MartingaleDCAStrategy(IModule):
    """Martingale/DCA strategy implementation."""
    
    def __init__(self, module_id: Optional[str] = "martingale_dca"):
        super().__init__(module_id=module_id)
        self.equities_file = "data/equities.json"
        self.equities = {}
        self.load_equities()
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the strategy."""
        self.equities_file = config.get("equities_file", "data/equities.json")
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> List[SignalData]:
        """Execute Martingale/DCA strategy logic."""
        symbol = input_data.get("symbol")
        current_price = input_data.get("current_price", 0)
        
        if not symbol or current_price <= 0:
            return []
        
        signals = []
        
        if symbol in self.equities and self.equities[symbol].get("system_on", False):
            equity_data = self.equities[symbol]
            
            # Check if we need to place initial order
            if not equity_data.get("has_position", False):
                # Place initial market order
                signal = SignalData(
                    symbol=symbol,
                    signal_type=SignalType.ENTRY_LONG,
                    price=current_price,
                    timestamp=datetime.now(),
                    confidence=1.0,
                    metadata={"order_type": "initial_entry"}
                )
                signals.append(signal)
                
                # Update equity data
                equity_data["has_position"] = True
                equity_data["entry_price"] = current_price
                self.save_equities()
            
            # Generate DCA levels
            levels = self.generate_dca_levels(
                equity_data.get("entry_price", current_price),
                equity_data.get("drawdown_pct", 5),
                equity_data.get("levels", 5)
            )
            
            # Check if current price hits any DCA level
            for level_price in levels:
                if current_price <= level_price * 1.01:  # 1% tolerance
                    signal = SignalData(
                        symbol=symbol,
                        signal_type=SignalType.ENTRY_LONG,
                        price=level_price,
                        timestamp=datetime.now(),
                        confidence=0.8,
                        metadata={
                            "order_type": "dca_level",
                            "level_price": level_price
                        }
                    )
                    signals.append(signal)
        
        return signals
    
    def generate_dca_levels(self, entry_price: float, drawdown_pct: float, levels: int) -> List[float]:
        """Generate DCA price levels."""
        return [
            round(entry_price * (1 - drawdown_pct/100 * (i+1)), 2)
            for i in range(levels)
        ]
    
    def add_equity(self, symbol: str, levels: int, drawdown_pct: float) -> None:
        """Add new equity to the system."""
        self.equities[symbol] = {
            "levels": levels,
            "drawdown_pct": drawdown_pct,
            "system_on": False,
            "has_position": False,
            "entry_price": 0.0
        }
        self.save_equities()
    
    def toggle_system(self, symbol: str) -> bool:
        """Toggle system on/off for a symbol."""
        if symbol in self.equities:
            current_status = self.equities[symbol].get("system_on", False)
            self.equities[symbol]["system_on"] = not current_status
            self.save_equities()
            return self.equities[symbol]["system_on"]
        return False
    
    def remove_equity(self, symbol: str) -> None:
        """Remove equity from the system."""
        if symbol in self.equities:
            del self.equities[symbol]
            self.save_equities()
    
    def load_equities(self) -> None:
        """Load equities from JSON file."""
        try:
            with open(self.equities_file, 'r') as f:
                self.equities = json.load(f)
        except FileNotFoundError:
            self.equities = {}
        except Exception as e:
            print(f"Error loading equities: {e}")
            self.equities = {}
    
    def save_equities(self) -> None:
        """Save equities to JSON file."""
        try:
            with open(self.equities_file, 'w') as f:
                json.dump(self.equities, f, indent=2)
        except Exception as e:
            print(f"Error saving equities: {e}")
