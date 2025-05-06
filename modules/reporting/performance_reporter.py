# modules/reporting/performance_reporter.py
from datetime import datetime
from typing import Any, Dict, Optional
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64

from core.interfaces import IModule
from core.models import PerformanceMetrics, TradeData

class PerformanceReporter(IModule):
    """Generates performance reports for the trading system."""
    
    def __init__(self, module_id: Optional[str] = "performance_reporter"):
        super().__init__(module_id=module_id)
        self.report_format = "html"
        self.save_path = "reports/"
        self.last_report_time = None
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the reporter.
        
        Args:
            config: Configuration dictionary with the following options:
                - report_format: Format for reports (html, pdf, etc.)
                - save_path: Path to save reports
        """
        self.report_format = config.get("report_format", "html")
        self.save_path = config.get("save_path", "reports/")
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a performance report.
        
        Args:
            input_data: Dictionary containing:
                - "metrics": PerformanceMetrics object
                - "trades": List of TradeData objects
                
        Returns:
            Dictionary with report details:
                - "report_path": Path to the saved report
                - "report_data": Report data in the specified format
                - "report_time": When the report was generated
        """
        metrics = input_data.get("metrics")
        trades = input_data.get("trades", [])
        
        if not metrics:
            return {"error": "No performance metrics provided"}
        
        report_time = datetime.now()
        self.last_report_time = report_time
        
        # Generate report based on format
        report_data = None
        report_path = None
        
        if self.report_format == "html":
            report_data = self._generate_html_report(metrics, trades)
            report_path = f"{self.save_path}report_{report_time.strftime('%Y%m%d_%H%M%S')}.html"
            
            # Save report
            with open(report_path, "w") as f:
                f.write(report_data)
        
        # Return report details
        return {
            "report_path": report_path,
            "report_data": report_data,
            "report_time": report_time
        }
    
    def _generate_html_report(self, metrics: PerformanceMetrics, trades: List[TradeData]) -> str:
        """Generate an HTML performance report."""
        # Create a basic HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trading Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .metrics {{ display: flex; flex-wrap: wrap; }}
                .metric {{ background-color: #f8f9fa; border-radius: 5px; padding: 15px; margin: 10px; flex: 1; min-width: 200px; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Trading Performance Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Performance Metrics</h2>
            <div class="metrics">
                <div class="metric">
                    <h3>Total Trades</h3>
                    <p>{metrics.total_trades}</p>
                </div>
                <div class="metric">
                    <h3>Win Rate</h3>
                    <p>{metrics.win_rate:.2f}%</p>
                </div>
                <div class="metric">
                    <h3>Total P&L</h3>
                    <p class="{'positive' if metrics.total_pnl >= 0 else 'negative'}">${metrics.total_pnl:.2f}</p>
                </div>
                <div class="metric">
                    <h3>Max Drawdown</h3>
                    <p class="negative">{metrics.max_drawdown:.2f}%</p>
                </div>
                <div class="metric">
                    <h3>Sharpe Ratio</h3>
                    <p>{metrics.sharpe_ratio:.2f}</p>
                </div>
                <div class="metric">
                    <h3>Sortino Ratio</h3>
                    <p>{metrics.sortino_ratio:.2f}</p>
                </div>
                <div class="metric">
                    <h3>Avg Win</h3>
                    <p class="positive">${metrics.average_win:.2f}</p>
                </div>
                <div class="metric">
                    <h3>Avg Loss</h3>
                    <p class="negative">${metrics.average_loss:.2f}</p>
                </div>
            </div>
        """
        
        # Add performance chart if we have trades
        if trades:
            equity_curve_img = self._generate_equity_curve_chart(trades)
            monthly_returns_img = self._generate_monthly_returns_chart(trades)
            
            html += f"""
            <h2>Performance Charts</h2>
            <div>
                <h3>Equity Curve</h3>
                <img src="data:image/png;base64,{equity_curve_img}" style="max-width: 100%;" />
            </div>
            <div>
                <h3>Monthly Returns</h3>
                <img src="data:image/png;base64,{monthly_returns_img}" style="max-width: 100%;" />
            </div>
            """
            
            # Add recent trades table
            recent_trades = sorted(trades, key=lambda t: t.timestamp, reverse=True)[:20]
            
            html += """
            <h2>Recent Trades</h2>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>P&L</th>
                </tr>
            """
            
            for trade in recent_trades:
                pnl = 0
                if hasattr(trade, 'pnl'):
                    pnl = trade.pnl
                elif hasattr(trade, 'price') and hasattr(trade, 'entry_price'):
                    if trade.side == OrderSide.BUY:
                        pnl = (trade.price - trade.entry_price) * trade.quantity
                    else:
                        pnl = (trade.entry_price - trade.price) * trade.quantity
                
                pnl_class = "positive" if pnl >= 0 else "negative"
                
                html += f"""
                <tr>
                    <td>{trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td>{trade.symbol}</td>
                    <td>{trade.side.value}</td>
                    <td>{trade.quantity:.2f}</td>
                    <td>${trade.price:.2f}</td>
                    <td class="{pnl_class}">${pnl:.2f}</td>
                </tr>
                """
            
            html += "</table>"
        
        html += """
            </body>
            </html>
        """
        
        return html
    
    def _generate_equity_curve_chart(self, trades: List[TradeData]) -> str:
        """Generate an equity curve chart and return as base64 encoded string."""
        # Create equity curve from trades
        equity_curve = [10000]  # Starting with initial capital
        dates = [trades[0].timestamp]
        
        for trade in sorted(trades, key=lambda t: t.timestamp):
            # Calculate P&L
            pnl = 0
            if hasattr(trade, 'pnl'):
                pnl = trade.pnl
            elif hasattr(trade, 'price') and hasattr(trade, 'entry_price'):
                if trade.side == OrderSide.BUY:
                    pnl = (trade.price - trade.entry_price) * trade.quantity
                else:
                    pnl = (trade.entry_price - trade.price) * trade.quantity
            
            # Update equity curve
            equity_curve.append(equity_curve[-1] + pnl)
            dates.append(trade.timestamp)
        
        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(dates, equity_curve)
        plt.title('Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Equity ($)')
        plt.grid(True)
        
        # Save plot to a buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        
        # Encode to base64
        img_str = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return img_str
    
    def _generate_monthly_returns_chart(self, trades: List[TradeData]) -> str:
        """Generate a monthly returns chart and return as base64 encoded string."""
        # Group trades by month and calculate returns
        monthly_returns = {}
        
        for trade in trades:
            month_key = trade.timestamp.strftime('%Y-%m')
            
            # Calculate P&L
            pnl = 0
            if hasattr(trade, 'pnl'):
                pnl = trade.pnl
            elif hasattr(trade, 'price') and hasattr(trade, 'entry_price'):
                if trade.side == OrderSide.BUY:
                    pnl = (trade.price - trade.entry_price) * trade.quantity
                else:
                    pnl = (trade.entry_price - trade.price) * trade.quantity
            
            if month_key in monthly_returns:
                monthly_returns[month_key] += pnl
            else:
                monthly_returns[month_key] = pnl
        
        # Sort by date
        sorted_months = sorted(monthly_returns.keys())
        returns = [monthly_returns[month] for month in sorted_months]
        
        # Create labels for x-axis
        labels = [m[5:] + '/' + m[:4] for m in sorted_months]
        
        # Create the plot
        plt.figure(figsize=(12, 6))
        bars = plt.bar(labels, returns)
        
        # Color the bars based on returns
        for i, bar in enumerate(bars):
            if returns[i] >= 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
        
        plt.title('Monthly Returns')
        plt.xlabel('Month')
        plt.ylabel('Return ($)')
        plt.grid(True, axis='y')
        plt.xticks(rotation=45)
        
        # Save plot to a buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        
        # Encode to base64
        img_str = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return img_str