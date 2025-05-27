from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

from core.interfaces import IModule
from core.models import SignalData, SignalType

class MartingaleDCAStrategy(IModule):
    """Enhanced Martingale/DCA strategy implementation with multi-asset support."""
    
    def __init__(self, module_id: Optional[str] = "martingale_dca"):
        super().__init__(module_id=module_id)
        self.equities_file = "data/equities.json"
        self.equities = {}
        self.asset_configs = {
            'stock': {'min_order_size': 1, 'precision': 2},
            'crypto': {'min_order_size': 0.001, 'precision': 8},
            'forex': {'min_order_size': 1000, 'precision': 5}
        }
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
            asset_type = equity_data.get("asset_type", "stock")
            
            # Check if we need to place initial order
            if not equity_data.get("has_position", False):
                # Place initial market order
                signal = SignalData(
                    symbol=symbol,
                    signal_type=SignalType.ENTRY_LONG,
                    price=current_price,
                    timestamp=datetime.now(),
                    confidence=1.0,
                    metadata={
                        "order_type": "initial_entry",
                        "asset_type": asset_type
                    }
                )
                signals.append(signal)
                
                # Update equity data
                equity_data["has_position"] = True
                equity_data["entry_price"] = current_price
                equity_data["last_buy_price"] = current_price
                equity_data["position_count"] = 1
                self.save_equities()
            
            # Generate DCA levels based on asset type
            levels = self.generate_dca_levels(
                equity_data.get("entry_price", current_price),
                equity_data.get("drawdown_pct", 5),
                equity_data.get("levels", 5),
                asset_type
            )
            
            # Check if current price hits any DCA level
            last_buy_price = equity_data.get("last_buy_price", equity_data.get("entry_price", current_price))
            
            for level_price in levels:
                # Adjust trigger logic based on asset type
                trigger_threshold = self._get_trigger_threshold(asset_type)
                
                # Only trigger if price drops below level and we haven't bought at this level recently
                if (current_price <= level_price and 
                    current_price < last_buy_price * (1 - trigger_threshold)):
                    
                    signal = SignalData(
                        symbol=symbol,
                        signal_type=SignalType.ENTRY_LONG,
                        price=level_price,
                        timestamp=datetime.now(),
                        confidence=0.8,
                        metadata={
                            "order_type": "dca_level",
                            "level_price": level_price,
                            "position_count": equity_data.get("position_count", 0) + 1,
                            "asset_type": asset_type
                        }
                    )
                    signals.append(signal)
                    
                    # Update last buy price
                    equity_data["last_buy_price"] = current_price
                    equity_data["position_count"] = equity_data.get("position_count", 0) + 1
                    self.save_equities()
                    break  # Only one signal per execution
        
        return signals
    
    def _get_trigger_threshold(self, asset_type: str) -> float:
        """Get trigger threshold based on asset type."""
        thresholds = {
            'stock': 0.05,    # 5% drop for stocks
            'crypto': 0.03,   # 3% drop for crypto (more volatile)
            'forex': 0.02     # 2% drop for forex
        }
        return thresholds.get(asset_type, 0.05)
    
    def _get_asset_type(self, symbol: str) -> str:
        """Determine asset type from symbol."""
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
        
        # Default to stock
        return 'stock'
    
    def generate_dca_levels(self, entry_price: float, drawdown_pct: float, levels: int, asset_type: str = 'stock') -> List[float]:
        """Generate DCA price levels with progressive scaling based on asset type."""
        dca_levels = []
        config = self.asset_configs.get(asset_type, self.asset_configs['stock'])
        precision = config['precision']
        
        # Asset-specific multipliers for progressive scaling
        multipliers = {
            'stock': 1.2,    # 20% increase per level
            'crypto': 1.3,   # 30% increase per level (more aggressive for volatile crypto)
            'forex': 1.1     # 10% increase per level (conservative for forex)
        }
        
        multiplier = multipliers.get(asset_type, 1.2)
        
        for i in range(levels):
            # Progressive drawdown: each level is deeper than the last
            level_drawdown = drawdown_pct * (i + 1) * multiplier
            level_price = entry_price * (1 - level_drawdown / 100)
            dca_levels.append(round(level_price, precision))
        return dca_levels
    
    def add_equity(self, symbol: str, levels: int, drawdown_pct: float, asset_type: str = None) -> bool:
        """Add new equity to the system with asset type detection."""
        try:
            # Auto-detect asset type if not provided
            if asset_type is None:
                asset_type = self._get_asset_type(symbol)
            
            # Validate asset type
            if asset_type not in self.asset_configs:
                asset_type = 'stock'  # Default fallback
            
            # Asset-specific validation
            config = self.asset_configs[asset_type]
            
            # Adjust limits based on asset type
            if asset_type == 'crypto':
                max_levels = 15  # Allow more levels for crypto
                max_drawdown = 30.0  # Higher drawdown tolerance for crypto
            elif asset_type == 'forex':
                max_levels = 8   # Fewer levels for forex
                max_drawdown = 15.0  # Moderate drawdown for forex
            else:  # stock
                max_levels = 10
                max_drawdown = 20.0
            
            self.equities[symbol] = {
                "levels": max(1, min(levels, max_levels)),
                "drawdown_pct": max(1.0, min(drawdown_pct, max_drawdown)),
                "asset_type": asset_type,
                "system_on": False,
                "has_position": False,
                "entry_price": 0.0,
                "last_buy_price": 0.0,
                "position_count": 0,
                "created_at": datetime.now().isoformat(),
                "total_invested": 0.0,
                "avg_cost_basis": 0.0
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
            asset_type = self.equities[symbol].get("asset_type", "stock")
            print(f"{asset_type.upper()} system for {symbol} turned {status}")
            
            self.save_equities()
            return self.equities[symbol]["system_on"]
        return False
    
    def remove_equity(self, symbol: str) -> bool:
        """Remove equity from the system."""
        if symbol in self.equities:
            asset_type = self.equities[symbol].get("asset_type", "stock")
            del self.equities[symbol]
            print(f"Removed {asset_type.upper()} {symbol} from trading system")
            return self.save_equities()
        return False
    
    def load_equities(self) -> None:
        """Load equities from JSON file with better error handling."""
        try:
            if os.path.exists(self.equities_file) and os.path.getsize(self.equities_file) > 0:
                with open(self.equities_file, 'r') as f:
                    self.equities = json.load(f)
                
                # Migrate old entries to include asset_type
                for symbol, data in self.equities.items():
                    if "asset_type" not in data:
                        data["asset_type"] = self._get_asset_type(symbol)
                
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
        asset_type = equity_data.get("asset_type", "stock")
        
        # Add calculated fields
        if equity_data.get("has_position") and equity_data.get("entry_price", 0) > 0:
            equity_data["dca_levels"] = self.generate_dca_levels(
                equity_data["entry_price"],
                equity_data["drawdown_pct"],
                equity_data["levels"],
                asset_type
            )
        
        return equity_data
    
    def get_all_active_systems(self) -> Dict[str, Dict]:
        """Get all systems that are currently active."""
        return {
            symbol: data for symbol, data in self.equities.items() 
            if data.get("system_on", False)
        }
    
    def get_equities_by_asset_type(self, asset_type: str) -> Dict[str, Dict]:
        """Get all equities of a specific asset type."""
        return {
            symbol: data for symbol, data in self.equities.items()
            if data.get("asset_type", "stock") == asset_type
        }
    
    def get_asset_type_summary(self) -> Dict[str, int]:
        """Get summary of asset types being tracked."""
        summary = {'stock': 0, 'crypto': 0, 'forex': 0}
        for data in self.equities.values():
            asset_type = data.get("asset_type", "stock")
            summary[asset_type] = summary.get(asset_type, 0) + 1
        return summary
    
    def update_position(self, symbol: str, new_price: float, quantity: float) -> bool:
        """Update position information after a trade."""
        if symbol not in self.equities:
            return False
        
        equity_data = self.equities[symbol]
        
        try:
            # Update average cost basis
            current_invested = equity_data.get("total_invested", 0.0)
            new_invested = new_price * quantity
            total_invested = current_invested + new_invested
            
            current_shares = equity_data.get("total_shares", 0.0)
            total_shares = current_shares + quantity
            
            if total_shares > 0:
                equity_data["avg_cost_basis"] = total_invested / total_shares
                equity_data["total_shares"] = total_shares
                equity_data["total_invested"] = total_invested
            
            return self.save_equities()
            
        except Exception as e:
            print(f"Error updating position for {symbol}: {e}")
            return False