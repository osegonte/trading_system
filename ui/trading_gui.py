# ui/trading_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
from typing import Dict, Any

class TradingBotGUI:
    """Enhanced GUI for the modular trading system."""
    
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.running = True
        
        # Get required modules
        self.alpaca_executor = controller.get_module("execution", "alpaca_executor")
        self.martingale_strategy = controller.get_module("strategies", "martingale_dca")
        self.ai_agent = controller.get_module("ai", "ai_portfolio_agent")
        
        self.setup_gui()
        self.start_auto_update()
    
    def setup_gui(self):
        """Set up the GUI components."""
        self.root.title("AI Trading Bot - Modular System")
        self.root.geometry("1000x700")
        
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
    
    def setup_trading_tab(self, parent):
        """Set up the trading controls tab."""
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="Add New Equity")
        input_frame.pack(fill="x", padx=5, pady=5)
        
        # Symbol input
        ttk.Label(input_frame, text="Symbol:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.symbol_entry = ttk.Entry(input_frame)
        self.symbol_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Levels input
        ttk.Label(input_frame, text="Levels:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.levels_entry = ttk.Entry(input_frame, width=10)
        self.levels_entry.grid(row=0, column=3, padx=5, pady=5)
        self.levels_entry.insert(0, "5")
        
        # Drawdown input
        ttk.Label(input_frame, text="Drawdown %:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.drawdown_entry = ttk.Entry(input_frame, width=10)
        self.drawdown_entry.grid(row=0, column=5, padx=5, pady=5)
        self.drawdown_entry.insert(0, "5")
        
        # Add button
        ttk.Button(input_frame, text="Add Equity", command=self.add_equity).grid(row=0, column=6, padx=5, pady=5)
        
        # Equities list
        list_frame = ttk.LabelFrame(parent, text="Active Trading Systems")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Treeview for equities
        columns = ("Symbol", "Levels", "Drawdown%", "Status", "Entry Price", "Current Price", "P&L")
        self.equities_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.equities_tree.heading(col, text=col)
            self.equities_tree.column(col, width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.equities_tree.yview)
        self.equities_tree.configure(yscrollcommand=scrollbar.set)
        
        self.equities_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(button_frame, text="Toggle System", command=self.toggle_system).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_equity).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_display).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel All Orders", command=self.cancel_all_orders).pack(side="right", padx=5)
    
    def setup_portfolio_tab(self, parent):
        """Set up the portfolio overview tab."""
        # Portfolio summary
        summary_frame = ttk.LabelFrame(parent, text="Portfolio Summary")
        summary_frame.pack(fill="x", padx=5, pady=5)
        
        self.portfolio_text = tk.Text(summary_frame, height=8, width=80)
        self.portfolio_text.pack(padx=5, pady=5)
        
        # Open orders
        orders_frame = ttk.LabelFrame(parent, text="Open Orders")
        orders_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        order_columns = ("Order ID", "Symbol", "Side", "Qty", "Price", "Type", "Status")
        self.orders_tree = ttk.Treeview(orders_frame, columns=order_columns, show="headings", height=8)
        
        for col in order_columns:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=80)
        
        orders_scrollbar = ttk.Scrollbar(orders_frame, orient="vertical", command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=orders_scrollbar.set)
        
        self.orders_tree.pack(side="left", fill="both", expand=True)
        orders_scrollbar.pack(side="right", fill="y")
        
        # Refresh button
        ttk.Button(parent, text="Refresh Portfolio", command=self.refresh_portfolio).pack(pady=5)
    
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
    
    def add_equity(self):
        """Add new equity to the trading system."""
        symbol = self.symbol_entry.get().upper().strip()
        
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
            self.martingale_strategy.add_equity(symbol, levels, drawdown)
            self.refresh_display()
            
            # Clear inputs
            self.symbol_entry.delete(0, tk.END)
            self.levels_entry.delete(0, tk.END)
            self.levels_entry.insert(0, "5")
            self.drawdown_entry.delete(0, tk.END)
            self.drawdown_entry.insert(0, "5")
        else:
            messagebox.showerror("Error", "Martingale strategy module not available")
    
    def toggle_system(self):
        """Toggle the selected equity system on/off."""
        selection = self.equities_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an equity to toggle")
            return
        
        item = self.equities_tree.item(selection[0])
        symbol = item['values'][0]
        
        if self.martingale_strategy:
            new_status = self.martingale_strategy.toggle_system(symbol)
            status_text = "ON" if new_status else "OFF"
            messagebox.showinfo("System Toggle", f"{symbol} system is now {status_text}")
            self.refresh_display()
    
    def remove_equity(self):
        """Remove selected equity from the system."""
        selection = self.equities_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an equity to remove")
            return
        
        item = self.equities_tree.item(selection[0])
        symbol = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Remove {symbol} from the system?"):
            if self.martingale_strategy:
                self.martingale_strategy.remove_equity(symbol)
                self.refresh_display()
    
    def cancel_all_orders(self):
        """Cancel all open orders."""
        if messagebox.askyesno("Confirm", "Cancel all open orders?"):
            if self.alpaca_executor:
                self.alpaca_executor.cancel_all_orders()
                messagebox.showinfo("Orders", "All orders cancelled")
                self.refresh_portfolio()
    
    def refresh_display(self):
        """Refresh the equities display."""
        # Clear existing items
        for item in self.equities_tree.get_children():
            self.equities_tree.delete(item)
        
        if not self.martingale_strategy:
            return
        
        # Add current equities
        for symbol, data in self.martingale_strategy.equities.items():
            current_price = 0
            if self.alpaca_executor:
                current_price = self.alpaca_executor.get_latest_price(symbol)
            
            # Calculate P&L
            pnl = 0
            if data.get("has_position", False) and data.get("entry_price", 0) > 0:
                pnl = (current_price - data["entry_price"]) / data["entry_price"] * 100
            
            status = "ON" if data.get("system_on", False) else "OFF"
            
            self.equities_tree.insert("", "end", values=(
                symbol,
                data.get("levels", 0),
                f"{data.get('drawdown_pct', 0)}%",
                status,
                f"${data.get('entry_price', 0):.2f}",
                f"${current_price:.2f}",
                f"{pnl:.2f}%"
            ))
    
    def refresh_portfolio(self):
        """Refresh portfolio and orders display."""
        if not self.alpaca_executor:
            return
        
        # Get portfolio positions
        positions = self.alpaca_executor.list_positions()
        portfolio_text = "PORTFOLIO POSITIONS:\n" + "="*50 + "\n"
        
        total_value = 0
        for pos in positions:
            market_value = float(pos.market_value)
            total_value += market_value
            unrealized_pnl = float(pos.unrealized_pnl)
            pnl_pct = (unrealized_pnl / market_value * 100) if market_value != 0 else 0
            
            portfolio_text += f"{pos.symbol}: {pos.qty} shares @ ${pos.avg_cost_basis}\n"
            portfolio_text += f"  Market Value: ${market_value:.2f}\n"
            portfolio_text += f"  P&L: ${unrealized_pnl:.2f} ({pnl_pct:.2f}%)\n\n"
        
        portfolio_text += f"TOTAL PORTFOLIO VALUE: ${total_value:.2f}\n"
        
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
            self.orders_tree.insert("", "end", values=(
                order.id[:8] + "...",
                order.symbol,
                order.side,
                order.qty,
                f"${float(order.limit_price or 0):.2f}" if order.limit_price else "Market",
                order.order_type,
                order.status
            ))
    
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
            portfolio = [vars(pos) for pos in self.alpaca_executor.list_positions()]
            orders = [vars(order) for order in self.alpaca_executor.list_open_orders()]
            
            # Get AI response
            response = self.ai_agent.execute({
                "message": message,
                "portfolio": portfolio,
                "orders": orders
            })
            
            self.add_chat_message(f"AI: {response}")
            
        except Exception as e:
            self.add_chat_message(f"AI: Error getting response: {e}")
    
    def quick_ai_analysis(self, analysis_type):
        """Perform quick AI analysis."""
        messages = {
            "risk": "Analyze the risk profile and exposure of my current portfolio",
            "review": "Provide a comprehensive review of my current portfolio performance",
            "optimize": "Suggest optimizations for my trading strategy and portfolio allocation"
        }
        
        message = messages.get(analysis_type, "Analyze my portfolio")
        self.message_entry.delete(0, tk.END)
        self.message_entry.insert(0, message)
        self.send_ai_message()
    
    def add_chat_message(self, message):
        """Add message to chat display."""
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")
    
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
