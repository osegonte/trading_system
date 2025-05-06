# modules/execution/order_executor.py
from datetime import datetime
from typing import Any, Dict, Optional, List

from core.interfaces import IModule
from core.models import SignalData, RiskParameters, OrderData, OrderType, OrderSide, TimeInForce

class OrderExecutor(IModule):
    """Executes orders based on signals and risk parameters."""
    
    def __init__(self, module_id: Optional[str] = "order_executor"):
        super().__init__(module_id=module_id)
        self.broker = None
        self.simulate = True
        self.slippage_factor = 0.0005  # 0.05% slippage
        self._orders = []  # Order history
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the order executor.
        
        Args:
            config: Configuration dictionary with the following options:
                - broker: Broker name or connection details
                - simulate: Whether to simulate orders or send to real broker
                - slippage_factor: Slippage factor for simulated orders
        """
        self.broker = config.get("broker")
        self.simulate = config.get("simulate", True)
        self.slippage_factor = config.get("slippage_factor", 0.0005)
        
        # Initialize broker connection if not simulating
        if not self.simulate and self.broker:
            self._connect_broker()
        
        super().configure(config)
    
    def _connect_broker(self) -> None:
        """Connect to the broker API."""
        # Implementation would depend on the specific broker
        pass
    
    def execute(self, input_data: Dict[str, Any]) -> OrderData:
        """Execute an order based on signal and risk parameters.
        
        Args:
            input_data: Dictionary containing:
                - "signal": SignalData object
                - "risk_params": RiskParameters object
            
        Returns:
            OrderData object
        """
        signal = input_data.get("signal")
        risk_params = input_data.get("risk_params")
        
        if not signal or not risk_params or risk_params.position_size <= 0:
            return None
        
        # Determine order side
        side = OrderSide.BUY if signal.signal_type == SignalType.ENTRY_LONG else OrderSide.SELL
        
        # Apply simulated slippage if in simulation mode
        execution_price = signal.price
        if self.simulate:
            if side == OrderSide.BUY:
                execution_price *= (1 + self.slippage_factor)
            else:
                execution_price *= (1 - self.slippage_factor)
        
        # Create order data
        order = OrderData(
            symbol=signal.symbol,
            order_type=OrderType.MARKET,
            side=side,
            quantity=risk_params.position_size,
            price=execution_price,
            time_in_force=TimeInForce.GTC,
            created_at=datetime.now(),
            signal_id=signal.signal_id,
            status="created"
        )
        
        # Send order to broker or simulate execution
        if not self.simulate:
            try:
                order = self._send_to_broker(order)
            except Exception as e:
                print(f"Error sending order to broker: {e}")
                order.status = "rejected"
        else:
            # Simulate immediate fill
            order.status = "filled"
        
        # Store order in history
        self._orders.append(order)
        
        return order
    
    def _send_to_broker(self, order: OrderData) -> OrderData:
        """Send order to the broker API."""
        # Implementation would depend on the specific broker
        # This is a placeholder
        order.status = "submitted"
        return order
    
    def get_orders(self) -> List[OrderData]:
        """Get all orders placed by this module."""
        return self._orders
    
    def get_order(self, order_id: str) -> Optional[OrderData]:
        """Get a specific order by ID."""
        for order in self._orders:
            if order.order_id == order_id:
                return order
        return None