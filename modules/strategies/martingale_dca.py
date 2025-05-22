from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

from core.interfaces import IModule
from core.models import SignalData, SignalType

class MartingaleDCAStrategy(IModule):
    """Enhanced Martingale/DCA strategy implementation with better error handling."""
    
    def __init__(self, module_id: Optional[str] = "martingale_dca"):
        super().__init__(module_id=module_id)
        self.equities_file = "data/equities.json"
        self.equities = {}
        self.ensure_data_directory()
        self.load_equities()
    
    def ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        data_dir = os.path.dirname(self.equities_file)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the strategy."""
        self.equities_file = config.get("equities_file", "data/equities.json")
        self.ensure_data_directory()
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
                equity_data["last_buy_price"] = current_price
                equity_data["position_count"] = 1
                self.save_equities()
            
            # Generate DCA levels
            levels = self.generate_dca_levels(
                equity_data.get("entry_price", current_price),
                equity_data.get("drawdown_pct", 5),
                equity_data.get("levels", 5)
            )
            
            # Check if current price hits any DCA level
            last_buy_price = equity_data.get("last_buy_price", equity_data.get("entry_price", current_price))
            
            for level_price in levels:
                # Only trigger if price drops below level and we haven't bought at this level recently
                if (current_price <= level_price and 
                    current_price < last_buy_price * 0.95):  # 5% drop from last buy
                    
                    signal = SignalData(
                        symbol=symbol,
                        signal_type=SignalType.ENTRY_LONG,
                        price=level_price,
                        timestamp=datetime.now(),
                        confidence=0.8,
                        metadata={
                            "order_type": "dca_level",
                            "level_price": level_price,
                            "position_count": equity_data.get("position_count", 0) + 1
                        }
                    )
                    signals.append(signal)
                    
                    # Update last buy price
                    equity_data["last_buy_price"] = current_price
                    equity_data["position_count"] = equity_data.get("position_count", 0) + 1
                    self.save_equities()
                    break  # Only one signal per execution
        
        return signals
    
    def generate_dca_levels(self, entry_price: float, drawdown_pct: float, levels: int) -> List[float]:
        """Generate DCA price levels with progressive scaling."""
        dca_levels = []
        for i in range(levels):
            # Progressive drawdown: each level is deeper than the last
            level_drawdown = drawdown_pct * (i + 1) * 1.2  # 20% increase per level
            level_price = entry_price * (1 - level_drawdown / 100)
            dca_levels.append(round(level_price, 2))
        return dca_levels
    
    def add_equity(self, symbol: str, levels: int, drawdown_pct: float) -> bool:
        """Add new equity to the system."""
        try:
            self.equities[symbol] = {
                "levels": max(1, min(levels, 10)),  # Limit between 1-10 levels
                "drawdown_pct": max(1.0, min(drawdown_pct, 20.0)),  # Limit between 1-20%
                "system_on": False,
                "has_position": False,
                "entry_price": 0.0,
                "last_buy_price": 0.0,
                "position_count": 0,
                "created_at": datetime.now().isoformat(),
                "total_invested": 0.0
            }
            return self.save_equities()
        except Exception as e:
            print(f"Error adding equity {symbol}: {e}")
            return False
    
    def toggle_system(self, symbol: str) -> bool:
        """Toggle system on/off for a symbol."""
        if symbol in self.equities:
            current_status = self.equities[symbol].get("system_on", False)
            self.equities[symbol]["system_on"] = not current_status
            
            # Log the change
            status = "ON" if not current_status else "OFF"
            print(f"System for {symbol} turned {status}")
            
            self.save_equities()
            return self.equities[symbol]["system_on"]
        return False
    
    def remove_equity(self, symbol: str) -> bool:
        """Remove equity from the system."""
        if symbol in self.equities:
            del self.equities[symbol]
            print(f"Removed {symbol} from trading system")
            return self.save_equities()
        return False
    
    def load_equities(self) -> None:
        """Load equities from JSON file with better error handling."""
        try:
            if os.path.exists(self.equities_file) and os.path.getsize(self.equities_file) > 0:
                with open(self.equities_file, 'r') as f:
                    self.equities = json.load(f)
                print(f"Loaded {len(self.equities)} equities from {self.equities_file}")
            else:
                # Create empty file if it doesn't exist
                self.equities = {}
                self.save_equities()
                print(f"Created new equities file: {self.equities_file}")
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error in {self.equities_file}: {e}")
            # Backup corrupted file and create new one
            backup_file = f"{self.equities_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(self.equities_file):
                os.rename(self.equities_file, backup_file)
                print(f"Corrupted file backed up to: {backup_file}")
            self.equities = {}
            self.save_equities()
            
        except Exception as e:
            print(f"Error loading equities: {e}")
            self.equities = {}
    
    def save_equities(self) -> bool:
        """Save equities to JSON file with error handling."""
        try:
            self.ensure_data_directory()
            
            # Create backup before saving
            if os.path.exists(self.equities_file):
                backup_file = f"{self.equities_file}.bak"
                with open(self.equities_file, 'r') as src, open(backup_file, 'w') as dst:
                    dst.write(src.read())
            
            # Save with pretty formatting
            with open(self.equities_file, 'w') as f:
                json.dump(self.equities, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            print(f"Error saving equities: {e}")
            return False
    
    def get_equity_status(self, symbol: str) -> Dict[str, Any]:
        """Get detailed status for an equity."""
        if symbol not in self.equities:
            return {}
        
        equity_data = self.equities[symbol].copy()
        
        # Add calculated fields
        if equity_data.get("has_position") and equity_data.get("entry_price", 0) > 0:
            # These would be filled by the GUI or another module with current prices
            equity_data["dca_levels"] = self.generate_dca_levels(
                equity_data["entry_price"],
                equity_data["drawdown_pct"],
                equity_data["levels"]
            )
        
        return equity_data
    
    def get_all_active_systems(self) -> Dict[str, Dict]:
        """Get all systems that are currently active."""
        return {
            symbol: data for symbol, data in self.equities.items() 
            if data.get("system_on", False)
        }