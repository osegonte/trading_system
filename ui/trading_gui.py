# ui/trading_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
from typing import Dict, Any

class TradingBotGUI:
    """Enhanced GUI for the modular trading system with multi-asset support."""
    
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.running = True
        
        # Get required modules
        self.alpaca_executor = controller.get_module("execution", "alpaca_executor")
        self.martingale_strategy = controller.get_module("strategies", "martingale_dca")
        self.ai_agent = controller.get_module("ai", "ai_portfolio_agent")
        self.data_provider = controller.get_module("data_collection", "yahoo_finance")
        
        # Asset type options
        self.asset_types = {
            "Stock": "stock",
            "Crypto": "crypto", 
            "Forex": "forex"
        }
        
        self.setup_gui()
        self.start_auto_update()
    
    def setup_gui(self):
        """Set up the GUI components."""
        self.root.title("AI Trading Bot - Multi-Asset Modular System")
        self.root.geometry("1200x800")
        
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Trading tab
        trading_frame = ttk.Frame(notebook)
        notebook.add(trading_frame, text="Trading")
        self.setup_trading_tab(trading_frame)
        
        # Portfolio tab
        portfolio_frame = ttk.Frame(notebook)
        notebook.add(portfolio_frame, text="Portfolio")
        self.setup_portfolio_tab(portfolio_frame)
        
        # AI Chat tab
        ai_frame = ttk.Frame(notebook)
        notebook.add(ai_frame, text="AI Assistant")
        self.setup_ai_tab(ai_frame)
        
        # Market Data tab
        market_frame = ttk.Frame(notebook)
        notebook.add(market_frame, text="Market Data")
        self.setup_market_tab(market_frame)
    
    def setup_trading_tab(self, parent):
        """Set up the trading controls tab."""
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="Add New Asset")
        input_frame.pack(fill="x", padx=5, pady=5)
        
        # Asset type selection
        ttk.Label(input_frame, text="Asset Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.asset_type_var = tk.StringVar(value="Stock")
        asset_combo = ttk.Combobox(input_frame, textvariable=self.asset_type_var, 
                                  values=list(self.asset_types.keys()), state="readonly", width=10)
        asset_combo.grid(row=0, column=1, padx=5, pady=5)
        asset_combo.bind('<<ComboboxSelected>>', self.on_asset_type_change)
        
        # Symbol input with suggestions
        ttk.Label(input_frame, text="Symbol:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.symbol_entry = ttk.Entry(input_frame)
        self.symbol_entry.grid(row=0, column=3, padx=5, pady=5)
        self.symbol_entry.bind('<KeyRelease>', self.on_symbol_change)
        
        # Quick select buttons
        self.quick_select_frame = ttk.Frame(input_frame)
        self.quick_select_frame.grid(row=1, column=0, columnspan=6, padx=5, pady=5, sticky="ew")
        self.update_quick_select_buttons()
        
        # Levels input
        ttk.Label(input_frame, text="Levels:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.levels_entry = ttk.Entry(input_frame, width=10)
        self.levels_entry.grid(row=2, column=1, padx=5, pady=5)
        self.levels_entry.insert(0, "5")
        
        # Drawdown input
        ttk.Label(input_frame, text="Drawdown %:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.drawdown_entry = ttk.Entry(input_frame, width=10)
        self.drawdown_entry.grid(row=2, column=3, padx=5, pady=5)
        self.drawdown_entry.insert(0, "5")
        
        # Add button
        ttk.Button(input_frame, text="Add Asset", command=self.add_equity).grid(row=2, column=4, padx=5, pady=5)
        
        # Get suggestions button
        ttk.Button(input_frame, text="Get Price", command=self.get_current_price).grid(row=2, column=5, padx=5, pady=5)
        
        # Current price display
        self.price_label = ttk.Label(input_frame, text="Price: --", foreground="blue")
        self.price_label.grid(row=0, column=4, columnspan=2, padx=5, pady=5)
        
        # Assets list with asset type filtering
        list_frame = ttk.LabelFrame(parent, text="Active Trading Systems")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Filter frame
        filter_frame = ttk.Frame(list_frame)
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter by Asset Type:").pack(side="left", padx=5)
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                   values=["All", "Stock", "Crypto", "Forex"], 
                                   state="readonly", width=10)
        filter_combo.pack(side="left", padx=5)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_display())
        
        # Asset type summary
        self.summary_label = ttk.Label(filter_frame, text="")
        self.summary_label.pack(side="right", padx=5)
        
        # Treeview for assets
        columns = ("Symbol", "Type", "Levels", "Drawdown%", "Status", "Entry Price", "Current Price", "P&L")
        self.equities_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        # Configure column widths
        column_widths = {"Symbol": 80, "Type": 60, "Levels": 60, "Drawdown%": 80, 
                        "Status": 60, "Entry Price": 90, "Current Price": 90, "P&L": 80}
        
        for col in columns:
            self.equities_tree.heading(col, text=col)
            self.equities_tree.column(col, width=column_widths.get(col, 100))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.equities_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.equities_tree.xview)
        self.equities_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.equities_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(button_frame, text="Toggle System", command=self.toggle_system).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_equity).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_display).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel All Orders", command=self.cancel_all_orders).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Export Data", command=self.export_data).pack(side="right", padx=5)
    
    def setup_market_tab(self, parent):
        """Set up the market data tab."""
        # Market overview frame
        overview_frame = ttk.LabelFrame(parent, text="Market Overview")
        overview_frame.pack(fill="x", padx=5, pady=5)
        
        # Asset type tabs
        market_notebook = ttk.Notebook(overview_frame)
        market_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Stock market tab
        stock_frame = ttk.Frame(market_notebook)
        market_notebook.add(stock_frame, text="Stocks")
        self.setup_asset_market_view(stock_frame, "stock")
        
        # Crypto market tab
        crypto_frame = ttk.Frame(market_notebook)
        market_notebook.add(crypto_frame, text="Crypto")
        self.setup_asset_market_view(crypto_frame, "crypto")
        
        # Forex market tab
        forex_frame = ttk.Frame(market_notebook)
        market_notebook.add(forex_frame, text="Forex")
        self.setup_asset_market_view(forex_frame, "forex")
    
    def setup_asset_market_view(self, parent, asset_type):
        """Set up market view for specific asset type."""
        # Price display
        price_frame = ttk.Frame(parent)
        price_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        columns = ("Symbol", "Price", "Change", "Change %", "Volume")
        tree = ttk.Treeview(price_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(price_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store reference
        setattr(self, f"{asset_type}_market_tree", tree)
        
        # Add sample data based on asset type
        if asset_type == "stock":
            sample_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        elif asset_type == "crypto":
            sample_symbols = ["BTC-USD", "ETH-USD", "ADA-USD", "DOT-USD"]
        else:  # forex
            sample_symbols = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
        
        # Refresh button
        ttk.Button(parent, text=f"Refresh {asset_type.title()} Prices", 
                  command=lambda: self.refresh_market_data(asset_type)).pack(pady=5)
    
    def update_quick_select_buttons(self):
        """Update quick select buttons based on asset type."""
        # Clear existing buttons
        for widget in self.quick_select_frame.winfo_children():
            widget.destroy()
        
        asset_type = self.asset_types[self.asset_type_var.get()]
        
        if asset_type == "stock":
            symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMZN"]
        elif asset_type == "crypto":
            symbols = ["BTC-USD", "ETH-USD", "ADA-USD", "DOT-USD", "LINK-USD"]
        else:  # forex
            symbols = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "GC=F", "SI=F"]
        
        ttk.Label(self.quick_select_frame, text="Quick Select:").pack(side="left", padx=5)
        
        for symbol in symbols:
            btn = ttk.Button(self.quick_select_frame, text=symbol, width=8,
                           command=lambda s=symbol: self.quick_select_symbol(s))
            btn.pack(side="left", padx=2)
    
    def on_asset_type_change(self, event=None):
        """Handle asset type change."""
        self.update_quick_select_buttons()
        self.symbol_entry.delete(0, tk.END)
        self.price_label.config(text="Price: --")
        
        # Update default values based on asset type
        asset_type = self.asset_types[self.asset_type_var.get()]
        if asset_type == "crypto":
            self.levels_entry.delete(0, tk.END)
            self.levels_entry.insert(0, "7")
            self.drawdown_entry.delete(0, tk.END)
            self.drawdown_entry.insert(0, "3")
        elif asset_type == "forex":
            self.levels_entry.delete(0, tk.END)
            self.levels_entry.insert(0, "4")
            self.drawdown_entry.delete(0, tk.END)
            self.drawdown_entry.insert(0, "2")
        else:  # stock
            self.levels_entry.delete(0, tk.END)
            self.levels_entry.insert(0, "5")
            self.drawdown_entry.delete(0, tk.END)
            self.drawdown_entry.insert(0, "5")
    
    def quick_select_symbol(self, symbol):
        """Quick select a symbol."""
        self.symbol_entry.delete(0, tk.END)
        self.symbol_entry.insert(0, symbol)
        self.get_current_price()
    
    def on_symbol_change(self, event=None):
        """Handle symbol input change."""
        # Reset price display when symbol changes
        self.price_label.config(text="Price: --")
    
    def get_current_price(self):
        """Get current price for the entered symbol."""
        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            return
        
        def fetch_price():
            try:
                if self.data_provider:
                    # Add symbol temporarily to get price
                    original_symbols = self.data_provider.symbols.copy()
                    self.data_provider.add_symbol(symbol)
                    
                    price_data = self.data_provider.execute([symbol])
                    
                    if symbol in price_data and price_data[symbol].bars:
                        latest_bar = price_data[symbol].bars[-1]
                        price = latest_bar.close
                        asset_type = self.data_provider.get_asset_type(symbol)
                        
                        # Update UI in main thread
                        self.root.after(0, lambda: self.price_label.config(
                            text=f"Price: ${price:.6f} ({asset_type.upper()})",
                            foreground="green"
                        ))
                    else:
                        self.root.after(0, lambda: self.price_label.config(
                            text="Price: Not Found", foreground="red"
                        ))
                    
                    # Restore original symbols
                    self.data_provider.symbols = original_symbols
                else:
                    self.root.after(0, lambda: self.price_label.config(
                        text="Price: Data provider unavailable", foreground="red"
                    ))
            except Exception as e:
                self.root.after(0, lambda: self.price_label.config(
                    text=f"Price: Error - {str(e)[:20]}", foreground="red"
                ))
        
        # Fetch price in background thread
        threading.Thread(target=fetch_price, daemon=True).start()
        self.price_label.config(text="Price: Loading...", foreground="blue")
    
    def setup_portfolio_tab(self, parent):
        """Set up the portfolio overview tab."""
        # Portfolio summary
        summary_frame = ttk.LabelFrame(parent, text="Portfolio Summary")
        summary_frame.pack(fill="x", padx=5, pady=5)
        
        self.portfolio_text = tk.Text(summary_frame, height=8, width=80)
        portfolio_scrollbar = ttk.Scrollbar(summary_frame, orient="vertical", command=self.portfolio_text.yview)
        self.portfolio_text.configure(yscrollcommand=portfolio_scrollbar.set)
        
        self.portfolio_text.pack(side="left", fill="both", expand=True)
        portfolio_scrollbar.pack(side="right", fill="y")
        
        # Open orders with asset type filtering
        orders_frame = ttk.LabelFrame(parent, text="Open Orders")
        orders_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        order_columns = ("Order ID", "Symbol", "Type", "Side", "Qty", "Price", "Status")
        self.orders_tree = ttk.Treeview(orders_frame, columns=order_columns, show="headings", height=8)
        
        for col in order_columns:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=90)
        
        orders_scrollbar = ttk.Scrollbar(orders_frame, orient="vertical", command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=orders_scrollbar.set)
        
        self.orders_tree.pack(side="left", fill="both", expand=True)
        orders_scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        portfolio_buttons = ttk.Frame(parent)
        portfolio_buttons.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(portfolio_buttons, text="Refresh Portfolio", command=self.refresh_portfolio).pack(side="left", padx=5)
        ttk.Button(portfolio_buttons, text="Export Portfolio", command=self.export_portfolio).pack(side="left", padx=5)
        ttk.Button(portfolio_buttons, text="Account Info", command=self.show_account_info).pack(side="right", padx=5)
    
    def setup_ai_tab(self, parent):
        """Set up the AI assistant tab."""
        # Chat display
        chat_frame = ttk.LabelFrame(parent, text="AI Portfolio Assistant")
        chat_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.chat_display = tk.Text(chat_frame, height=20, width=80, state="disabled")
        chat_scrollbar = ttk.Scrollbar(chat_frame, orient="vertical", command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=chat_scrollbar.set)
        
        self.chat_display.pack(side="left", fill="both", expand=True)
        chat_scrollbar.pack(side="right", fill="y")
        
        # Input frame
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        self.message_entry = ttk.Entry(input_frame, width=60)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.message_entry.bind("<Return>", lambda e: self.send_ai_message())
        
        ttk.Button(input_frame, text="Send", command=self.send_ai_message).pack(side="right")
        
        # Quick analysis buttons
        quick_frame = ttk.Frame(parent)
        quick_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(quick_frame, text="Analyze Risk", command=lambda: self.quick_ai_analysis("risk")).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="Portfolio Review", command=lambda: self.quick_ai_analysis("review")).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="Optimize Strategy", command=lambda: self.quick_ai_analysis("optimize")).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="Multi-Asset Analysis", command=lambda: self.quick_ai_analysis("multi_asset")).pack(side="left", padx=2)
    
    def add_equity(self):
        """Add new asset to the trading system."""
        symbol = self.symbol_entry.get().upper().strip()
        asset_type = self.asset_types[self.asset_type_var.get()]
        
        try:
            levels = int(self.levels_entry.get())
            drawdown = float(self.drawdown_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for levels and drawdown")
            return
        
        if not symbol:
            messagebox.showerror("Error", "Please enter a symbol")
            return
        
        if self.martingale_strategy:
            success = self.martingale_strategy.add_equity(symbol, levels, drawdown, asset_type)
            if success:
                self.refresh_display()
                
                # Clear inputs
                self.symbol_entry.delete(0, tk.END)
                self.price_label.config(text="Price: --")
                
                # Add to data provider
                if self.data_provider:
                    self.data_provider.add_symbol(symbol)
                
                messagebox.showinfo("Success", f"Added {asset_type.upper()} {symbol} to trading system")
            else:
                messagebox.showerror("Error", f"Failed to add {symbol}")
        else:
            messagebox.showerror("Error", "Martingale strategy module not available")
    
    def toggle_system(self):
        """Toggle the selected asset system on/off."""
        selection = self.equities_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an asset to toggle")
            return
        
        item = self.equities_tree.item(selection[0])
        symbol = item['values'][0]
        
        if self.martingale_strategy:
            new_status = self.martingale_strategy.toggle_system(symbol)
            status_text = "ON" if new_status else "OFF"
            asset_type = self.martingale_strategy.equities[symbol].get("asset_type", "stock")
            messagebox.showinfo("System Toggle", f"{asset_type.upper()} {symbol} system is now {status_text}")
            self.refresh_display()
    
    def remove_equity(self):
        """Remove selected asset from the system."""
        selection = self.equities_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an asset to remove")
            return
        
        item = self.equities_tree.item(selection[0])
        symbol = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Remove {symbol} from the system?"):
            if self.martingale_strategy:
                success = self.martingale_strategy.remove_equity(symbol)
                if success:
                    # Remove from data provider
                    if self.data_provider:
                        self.data_provider.remove_symbol(symbol)
                    self.refresh_display()
    
    def cancel_all_orders(self):
        """Cancel all open orders."""
        if messagebox.askyesno("Confirm", "Cancel all open orders?"):
            if self.alpaca_executor:
                self.alpaca_executor.cancel_all_orders()
                messagebox.showinfo("Orders", "All orders cancelled")
                self.refresh_portfolio()
    
    def refresh_display(self):
        """Refresh the assets display."""
        # Clear existing items
        for item in self.equities_tree.get_children():
            self.equities_tree.delete(item)
        
        if not self.martingale_strategy:
            return
        
        # Get filter selection
        filter_type = self.filter_var.get()
        
        # Update summary
        summary = self.martingale_strategy.get_asset_type_summary()
        summary_text = f"Stocks: {summary['stock']} | Crypto: {summary['crypto']} | Forex: {summary['forex']}"
        self.summary_label.config(text=summary_text)
        
        # Add current assets
        for symbol, data in self.martingale_strategy.equities.items():
            asset_type = data.get("asset_type", "stock")
            
            # Apply filter
            if filter_type != "All" and asset_type != self.asset_types.get(filter_type, "").lower():
                continue
            
            current_price = 0
            if self.alpaca_executor:
                current_price = self.alpaca_executor.get_latest_price(symbol)
            
            # Calculate P&L
            pnl = 0
            if data.get("has_position", False) and data.get("entry_price", 0) > 0:
                pnl = (current_price - data["entry_price"]) / data["entry_price"] * 100
            
            status = "ON" if data.get("system_on", False) else "OFF"
            
            # Color coding based on asset type
            tags = (asset_type,)
            
            self.equities_tree.insert("", "end", values=(
                symbol,
                asset_type.upper(),
                data.get("levels", 0),
                f"{data.get('drawdown_pct', 0)}%",
                status,
                f"${data.get('entry_price', 0):.6f}",
                f"${current_price:.6f}",
                f"{pnl:.2f}%"
            ), tags=tags)
        
        # Configure tag colors
        self.equities_tree.tag_configure("stock", background="#f0f8ff")
        self.equities_tree.tag_configure("crypto", background="#fff8dc")
        self.equities_tree.tag_configure("forex", background="#f0fff0")
    
    def refresh_portfolio(self):
        """Refresh portfolio and orders display."""
        if not self.alpaca_executor:
            return
        
        # Get portfolio positions
        positions = self.alpaca_executor.list_positions()
        account_info = self.alpaca_executor.get_account_info()
        
        portfolio_text = "PORTFOLIO OVERVIEW:\n" + "="*60 + "\n"
        
        # Account summary
        portfolio_text += f"Account Value: ${account_info.get('portfolio_value', 0):,.2f}\n"
        portfolio_text += f"Buying Power: ${account_info.get('buying_power', 0):,.2f}\n"
        portfolio_text += f"Cash: ${account_info.get('cash', 0):,.2f}\n\n"
        
        # Group positions by asset type
        stock_positions = []
        crypto_positions = []
        forex_positions = []
        
        total_value = 0
        for pos in positions:
            market_value = float(pos.market_value)
            total_value += market_value
            
            # Determine asset type
            if hasattr(self.alpaca_executor, '_get_asset_type'):
                asset_type = self.alpaca_executor._get_asset_type(pos.symbol)
            else:
                asset_type = "stock"  # Default
            
            pos_info = {
                'symbol': pos.symbol,
                'qty': pos.qty,
                'avg_cost': pos.avg_cost_basis,
                'market_value': market_value,
                'unrealized_pnl': float(pos.unrealized_pnl),
                'pnl_pct': (float(pos.unrealized_pnl) / market_value * 100) if market_value != 0 else 0
            }
            
            if asset_type == 'crypto':
                crypto_positions.append(pos_info)
            elif asset_type == 'forex':
                forex_positions.append(pos_info)
            else:
                stock_positions.append(pos_info)
        
        # Display positions by type
        for asset_type, positions_list, header in [
            ("STOCK", stock_positions, "STOCK POSITIONS:"),
            ("CRYPTO", crypto_positions, "CRYPTO POSITIONS:"),
            ("FOREX", forex_positions, "FOREX POSITIONS:")
        ]:
            if positions_list:
                portfolio_text += f"\n{header}\n" + "-"*40 + "\n"
                for pos in positions_list:
                    portfolio_text += f"{pos['symbol']}: {pos['qty']} @ ${pos['avg_cost']}\n"
                    portfolio_text += f"  Market Value: ${pos['market_value']:.2f}\n"
                    portfolio_text += f"  P&L: ${pos['unrealized_pnl']:.2f} ({pos['pnl_pct']:.2f}%)\n\n"
        
        portfolio_text += f"\nTOTAL PORTFOLIO VALUE: ${total_value:.2f}\n"
        
        # Update portfolio text
        self.portfolio_text.config(state="normal")
        self.portfolio_text.delete(1.0, tk.END)
        self.portfolio_text.insert(1.0, portfolio_text)
        self.portfolio_text.config(state="disabled")
        
        # Update orders tree
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        
        orders = self.alpaca_executor.list_open_orders()
        for order in orders:
            # Determine asset type
            if hasattr(self.alpaca_executor, '_get_asset_type'):
                asset_type = self.alpaca_executor._get_asset_type(order.symbol)
            else:
                asset_type = "stock"
            
            self.orders_tree.insert("", "end", values=(
                order.id[:8] + "...",
                order.symbol,
                asset_type.upper(),
                order.side,
                order.qty,
                f"${float(order.limit_price or 0):.6f}" if order.limit_price else "Market",
                order.status
            ))
    
    def refresh_market_data(self, asset_type):
        """Refresh market data for specific asset type."""
        if not self.data_provider:
            return
        
        tree = getattr(self, f"{asset_type}_market_tree", None)
        if not tree:
            return
        
        # Clear existing data
        for item in tree.get_children():
            tree.delete(item)
        
        # Get symbols based on asset type
        if asset_type == "stock":
            symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        elif asset_type == "crypto":
            symbols = self.data_provider.get_supported_crypto_symbols()[:10]
        else:  # forex
            symbols = self.data_provider.get_supported_forex_symbols()[:10]
        
        def fetch_data():
            try:
                price_data = self.data_provider.execute(symbols)
                
                for symbol in symbols:
                    if symbol in price_data and price_data[symbol].bars:
                        bars = price_data[symbol].bars
                        if len(bars) >= 2:
                            current = bars[-1]
                            previous = bars[-2]
                            
                            change = current.close - previous.close
                            change_pct = (change / previous.close) * 100
                            
                            # Update UI in main thread
                            self.root.after(0, lambda s=symbol, c=current, ch=change, chp=change_pct: 
                                           tree.insert("", "end", values=(
                                               s, f"${c.close:.6f}", f"${ch:.6f}", 
                                               f"{chp:.2f}%", f"{c.volume:,.0f}"
                                           )))
            except Exception as e:
                print(f"Error fetching {asset_type} market data: {e}")
        
        # Fetch data in background
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def send_ai_message(self):
        """Send message to AI assistant."""
        message = self.message_entry.get().strip()
        if not message:
            return
        
        self.message_entry.delete(0, tk.END)
        
        # Add user message to chat
        self.add_chat_message(f"You: {message}")
        
        # Get AI response in background thread
        threading.Thread(target=self.get_ai_response, args=(message,), daemon=True).start()
    
    def get_ai_response(self, message):
        """Get AI response in background thread."""
        if not self.ai_agent or not self.alpaca_executor:
            self.add_chat_message("AI: AI agent or executor not available")
            return
        
        try:
            # Get current portfolio and orders
            positions = self.alpaca_executor.list_positions()
            orders = self.alpaca_executor.list_open_orders()
            
            # Include asset type information
            portfolio_data = []
            for pos in positions:
                pos_dict = {
                    'symbol': pos.symbol,
                    'qty': pos.qty,
                    'market_value': float(pos.market_value),
                    'unrealized_pnl': float(pos.unrealized_pnl),
                    'asset_type': getattr(self.alpaca_executor, '_get_asset_type', lambda x: 'stock')(pos.symbol)
                }
                portfolio_data.append(pos_dict)
            
            order_data = []
            for order in orders:
                order_dict = {
                    'symbol': order.symbol,
                    'side': order.side,
                    'qty': order.qty,
                    'status': order.status,
                    'asset_type': getattr(self.alpaca_executor, '_get_asset_type', lambda x: 'stock')(order.symbol)
                }
                order_data.append(order_dict)
            
            # Get trading system data
            trading_systems = {}
            if self.martingale_strategy:
                trading_systems = self.martingale_strategy.get_all_active_systems()
            
            # Enhanced prompt with multi-asset context
            enhanced_message = f"{message}\n\nContext: Multi-asset portfolio with stocks, crypto, and forex. Trading systems: {len(trading_systems)} active."
            
            # Get AI response
            response = self.ai_agent.execute({
                "message": enhanced_message,
                "portfolio": portfolio_data,
                "orders": order_data,
                "trading_systems": trading_systems
            })
            
            self.add_chat_message(f"AI: {response}")
            
        except Exception as e:
            self.add_chat_message(f"AI: Error getting response: {e}")
    
    def quick_ai_analysis(self, analysis_type):
        """Perform quick AI analysis."""
        messages = {
            "risk": "Analyze the risk profile and exposure of my current multi-asset portfolio including stocks, crypto, and forex",
            "review": "Provide a comprehensive review of my current portfolio performance across all asset classes",
            "optimize": "Suggest optimizations for my trading strategy and portfolio allocation considering different asset types",
            "multi_asset": "Analyze the correlation and diversification benefits of my multi-asset portfolio"
        }
        
        message = messages.get(analysis_type, "Analyze my multi-asset portfolio")
        self.message_entry.delete(0, tk.END)
        self.message_entry.insert(0, message)
        self.send_ai_message()
    
    def add_chat_message(self, message):
        """Add message to chat display."""
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")
    
    def export_data(self):
        """Export trading data to file."""
        try:
            from tkinter import filedialog
            import json
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename and self.martingale_strategy:
                export_data = {
                    "equities": self.martingale_strategy.equities,
                    "asset_summary": self.martingale_strategy.get_asset_type_summary(),
                    "export_time": datetime.now().isoformat()
                }
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                messagebox.showinfo("Export Complete", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {e}")
    
    def export_portfolio(self):
        """Export portfolio data."""
        try:
            from tkinter import filedialog
            import json
            
            if not self.alpaca_executor:
                messagebox.showerror("Error", "Executor not available")
                return
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                positions = self.alpaca_executor.list_positions()
                orders = self.alpaca_executor.list_open_orders()
                account_info = self.alpaca_executor.get_account_info()
                
                export_data = {
                    "account_info": account_info,
                    "positions": [vars(pos) for pos in positions],
                    "orders": [vars(order) for order in orders],
                    "export_time": datetime.now().isoformat()
                }
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                messagebox.showinfo("Export Complete", f"Portfolio exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export portfolio: {e}")
    
    def show_account_info(self):
        """Show detailed account information."""
        if not self.alpaca_executor:
            messagebox.showerror("Error", "Executor not available")
            return
        
        account_info = self.alpaca_executor.get_account_info()
        supported_assets = self.alpaca_executor.get_supported_assets()
        
        info_text = "ACCOUNT INFORMATION:\n" + "="*40 + "\n"
        info_text += f"Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}\n"
        info_text += f"Buying Power: ${account_info.get('buying_power', 0):,.2f}\n"
        info_text += f"Cash: ${account_info.get('cash', 0):,.2f}\n"
        info_text += f"Day Trade Count: {account_info.get('day_trade_count', 0)}\n"
        info_text += f"Trading Blocked: {account_info.get('trading_blocked', False)}\n\n"
        
        info_text += "SUPPORTED ASSETS:\n" + "-"*20 + "\n"
        for asset_type, supported in supported_assets.items():
            status = "✓" if supported else "✗"
            info_text += f"{asset_type.upper()}: {status}\n"
        
        messagebox.showinfo("Account Information", info_text)
    
    def start_auto_update(self):
        """Start auto-update thread."""
        def update_loop():
            while self.running:
                try:
                    self.refresh_display()
                    if hasattr(self, 'portfolio_text'):
                        self.refresh_portfolio()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    print(f"Error in auto-update: {e}")
                    time.sleep(30)
        
        threading.Thread(target=update_loop, daemon=True).start()
    
    def on_close(self):
        """Handle window close event."""
        self.running = False
        self.root.destroy()