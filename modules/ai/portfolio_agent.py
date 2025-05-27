# modules/ai/portfolio_agent.py
import openai
from typing import Any, Dict, Optional, List
import json
import logging

from core.interfaces import IModule

class AIPortfolioAgent(IModule):
    """Enhanced AI-powered portfolio analysis agent with multi-asset expertise."""
    
    def __init__(self, module_id: Optional[str] = "ai_portfolio_agent"):
        super().__init__(module_id=module_id)
        self.api_key = ""
        self.model = "deepseek-chat"
        self.base_url = "https://api.deepseek.com"
        self.client = None
        self.logger = logging.getLogger(f"AIPortfolioAgent.{module_id}")
        self.system_prompt = """
        You are an expert multi-asset portfolio manager and risk analyst specializing in stocks, cryptocurrencies, and forex trading. Your expertise includes:

        1) **Multi-Asset Portfolio Analysis**: Evaluate diversification across stocks, crypto, and forex
        2) **Risk Assessment**: Analyze correlation risks, volatility patterns, and asset-specific risks
        3) **Asset-Specific Strategy**: Provide tailored advice for each asset class
        4) **Cross-Asset Opportunities**: Identify hedging and arbitrage opportunities
        5) **Regulatory Considerations**: Account for different regulations across asset classes
        6) **Market Timing**: Analyze global market cycles and their impact on different assets

        **Asset Class Expertise:**
        - **Stocks**: Traditional equity analysis, sector rotation, fundamental analysis
        - **Crypto**: Volatility management, DeFi opportunities, regulatory risks, correlation with tech stocks
        - **Forex**: Interest rate differentials, economic indicators, carry trades, safe haven analysis

        **Risk Management Focus:**
        - Correlation analysis between asset classes
        - Volatility clustering in crypto markets
        - Leverage considerations in forex
        - Liquidity risks across different markets
        - Time zone and market hour considerations

        Always provide specific, data-driven recommendations with risk-adjusted perspective for multi-asset portfolios.
        Consider the unique characteristics of each asset class when making recommendations.
        """
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the AI agent."""
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "deepseek-chat")
        self.base_url = config.get("base_url", "https://api.deepseek.com")
        
        if self.api_key:
            try:
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                self.logger.info("AI Portfolio Agent configured successfully")
            except Exception as e:
                self.logger.error(f"Failed to configure AI client: {e}")
        
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> str:
        """Analyze multi-asset portfolio and provide AI insights."""
        if not self.client:
            return "AI agent not configured - missing API key"
            
        user_message = input_data.get("message", "")
        portfolio = input_data.get("portfolio", [])
        orders = input_data.get("orders", [])
        trading_systems = input_data.get("trading_systems", {})
        
        # Analyze portfolio composition by asset type
        portfolio_analysis = self._analyze_portfolio_composition(portfolio)
        orders_analysis = self._analyze_orders_by_asset_type(orders)
        systems_analysis = self._analyze_trading_systems(trading_systems)
        
        # Create enhanced analysis prompt
        prompt = f"""
        Multi-Asset Portfolio Analysis Request: {user_message}
        
        PORTFOLIO COMPOSITION:
        {json.dumps(portfolio_analysis, indent=2)}
        
        OPEN ORDERS BY ASSET TYPE:
        {json.dumps(orders_analysis, indent=2)}
        
        ACTIVE TRADING SYSTEMS:
        {json.dumps(systems_analysis, indent=2)}
        
        RAW PORTFOLIO DATA:
        {json.dumps(portfolio[:5], indent=2)}  # Limit for token efficiency
        
        RAW ORDERS DATA:
        {json.dumps(orders[:10], indent=2)}  # Limit for token efficiency
        
        Please provide comprehensive analysis considering:
        1. Asset allocation and diversification across stocks, crypto, and forex
        2. Risk concentration and correlation risks
        3. Liquidity considerations across different markets
        4. Market timing and global economic factors
        5. Specific recommendations for each asset class
        6. Risk management improvements
        7. Opportunity identification across asset classes
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            self.logger.error(f"Error getting AI analysis: {e}")
            return f"Error getting AI analysis: {e}"
    
    def _analyze_portfolio_composition(self, portfolio: List[Dict]) -> Dict[str, Any]:
        """Analyze portfolio composition by asset type."""
        composition = {
            'total_value': 0.0,
            'asset_breakdown': {'stock': 0.0, 'crypto': 0.0, 'forex': 0.0},
            'position_count': {'stock': 0, 'crypto': 0, 'forex': 0},
            'total_pnl': 0.0,
            'pnl_by_asset': {'stock': 0.0, 'crypto': 0.0, 'forex': 0.0},
            'largest_positions': [],
            'risk_metrics': {}
        }
        
        try:
            for position in portfolio:
                asset_type = position.get('asset_type', 'stock')
                market_value = float(position.get('market_value', 0))
                unrealized_pnl = float(position.get('unrealized_pnl', 0))
                
                # Update totals
                composition['total_value'] += market_value
                composition['total_pnl'] += unrealized_pnl
                
                # Update by asset type
                if asset_type in composition['asset_breakdown']:
                    composition['asset_breakdown'][asset_type] += market_value
                    composition['position_count'][asset_type] += 1
                    composition['pnl_by_asset'][asset_type] += unrealized_pnl
                
                # Track largest positions
                composition['largest_positions'].append({
                    'symbol': position.get('symbol', ''),
                    'asset_type': asset_type,
                    'value': market_value,
                    'pnl': unrealized_pnl
                })
            
            # Sort largest positions
            composition['largest_positions'].sort(key=lambda x: x['value'], reverse=True)
            composition['largest_positions'] = composition['largest_positions'][:5]
            
            # Calculate percentages
            total_value = composition['total_value']
            if total_value > 0:
                for asset_type in composition['asset_breakdown']:
                    value = composition['asset_breakdown'][asset_type]
                    percentage = (value / total_value) * 100
                    composition['asset_breakdown'][asset_type] = {
                        'value': value,
                        'percentage': percentage,
                        'pnl': composition['pnl_by_asset'][asset_type],
                        'positions': composition['position_count'][asset_type]
                    }
            
            # Calculate risk metrics
            composition['risk_metrics'] = self._calculate_risk_metrics(portfolio)
            
        except Exception as e:
            self.logger.error(f"Error analyzing portfolio composition: {e}")
        
        return composition
    
    def _analyze_orders_by_asset_type(self, orders: List[Dict]) -> Dict[str, Any]:
        """Analyze open orders by asset type."""
        analysis = {
            'total_orders': len(orders),
            'by_asset_type': {'stock': [], 'crypto': [], 'forex': []},
            'order_value_by_type': {'stock': 0.0, 'crypto': 0.0, 'forex': 0.0},
            'order_summary': {}
        }
        
        try:
            for order in orders:
                asset_type = order.get('asset_type', 'stock')
                
                if asset_type in analysis['by_asset_type']:
                    analysis['by_asset_type'][asset_type].append({
                        'symbol': order.get('symbol', ''),
                        'side': order.get('side', ''),
                        'qty': order.get('qty', 0),
                        'status': order.get('status', '')
                    })
                    
                    # Estimate order value (simplified)
                    qty = float(order.get('qty', 0))
                    # Note: Without price, this is approximate
                    analysis['order_value_by_type'][asset_type] += qty
            
            # Create summary
            for asset_type, orders_list in analysis['by_asset_type'].items():
                analysis['order_summary'][asset_type] = {
                    'count': len(orders_list),
                    'buy_orders': len([o for o in orders_list if o['side'] == 'buy']),
                    'sell_orders': len([o for o in orders_list if o['side'] == 'sell'])
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing orders: {e}")
        
        return analysis
    
    def _analyze_trading_systems(self, trading_systems: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze active trading systems by asset type."""
        analysis = {
            'total_systems': len(trading_systems),
            'by_asset_type': {'stock': [], 'crypto': [], 'forex': []},
            'risk_analysis': {},
            'system_summary': {}
        }
        
        try:
            for symbol, system_data in trading_systems.items():
                asset_type = system_data.get('asset_type', 'stock')
                
                if asset_type in analysis['by_asset_type']:
                    analysis['by_asset_type'][asset_type].append({
                        'symbol': symbol,
                        'levels': system_data.get('levels', 0),
                        'drawdown_pct': system_data.get('drawdown_pct', 0),
                        'has_position': system_data.get('has_position', False),
                        'entry_price': system_data.get('entry_price', 0)
                    })
            
            # Analyze risk concentration
            for asset_type, systems in analysis['by_asset_type'].items():
                total_systems = len(systems)
                systems_with_positions = len([s for s in systems if s['has_position']])
                avg_drawdown = sum(s['drawdown_pct'] for s in systems) / total_systems if total_systems > 0 else 0
                
                analysis['system_summary'][asset_type] = {
                    'total_systems': total_systems,
                    'active_positions': systems_with_positions,
                    'avg_drawdown_tolerance': avg_drawdown,
                    'risk_level': self._assess_risk_level(avg_drawdown, asset_type)
                }
        
        except Exception as e:
            self.logger.error(f"Error analyzing trading systems: {e}")
        
        return analysis
    
    def _calculate_risk_metrics(self, portfolio: List[Dict]) -> Dict[str, float]:
        """Calculate portfolio risk metrics."""
        metrics = {
            'portfolio_volatility': 0.0,
            'max_position_concentration': 0.0,
            'asset_type_concentration': 0.0,
            'correlation_risk': 0.0
        }
        
        try:
            if not portfolio:
                return metrics
            
            # Calculate position concentration
            total_value = sum(float(p.get('market_value', 0)) for p in portfolio)
            if total_value > 0:
                position_weights = [float(p.get('market_value', 0)) / total_value for p in portfolio]
                metrics['max_position_concentration'] = max(position_weights) * 100
                
                # Calculate asset type concentration (Herfindahl Index)
                asset_values = {'stock': 0, 'crypto': 0, 'forex': 0}
                for p in portfolio:
                    asset_type = p.get('asset_type', 'stock')
                    value = float(p.get('market_value', 0))
                    if asset_type in asset_values:
                        asset_values[asset_type] += value
                
                asset_weights = [v / total_value for v in asset_values.values() if v > 0]
                hhi = sum(w**2 for w in asset_weights)
                metrics['asset_type_concentration'] = hhi * 100
                
                # Estimate correlation risk (simplified)
                crypto_weight = asset_values['crypto'] / total_value
                stock_weight = asset_values['stock'] / total_value
                # High correlation risk if both crypto and stocks are significant
                if crypto_weight > 0.2 and stock_weight > 0.2:
                    metrics['correlation_risk'] = min(crypto_weight, stock_weight) * 100
        
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
        
        return metrics
    
    def _assess_risk_level(self, avg_drawdown: float, asset_type: str) -> str:
        """Assess risk level based on drawdown tolerance and asset type."""
        if asset_type == 'crypto':
            if avg_drawdown > 15:
                return 'Very High'
            elif avg_drawdown > 10:
                return 'High'
            elif avg_drawdown > 5:
                return 'Medium'
            else:
                return 'Low'
        elif asset_type == 'forex':
            if avg_drawdown > 8:
                return 'Very High'
            elif avg_drawdown > 5:
                return 'High'
            elif avg_drawdown > 3:
                return 'Medium'
            else:
                return 'Low'
        else:  # stock
            if avg_drawdown > 12:
                return 'Very High'
            elif avg_drawdown > 8:
                return 'High'
            elif avg_drawdown > 5:
                return 'Medium'
            else:
                return 'Low'
    
    def analyze_risk(self, portfolio: List[Dict]) -> str:
        """Analyze portfolio risk with multi-asset focus."""
        return self.execute({
            "message": "Provide a comprehensive risk analysis of my multi-asset portfolio, focusing on correlation risks, volatility clustering, and asset-specific risks",
            "portfolio": portfolio,
            "orders": []
        })
    
    def suggest_optimizations(self, portfolio: List[Dict], orders: List[Dict], trading_systems: Dict) -> str:
        """Suggest portfolio optimizations for multi-asset portfolio."""
        return self.execute({
            "message": "Analyze my current multi-asset portfolio and suggest specific optimizations for asset allocation, risk management, and trading strategy improvements",
            "portfolio": portfolio,
            "orders": orders,
            "trading_systems": trading_systems
        })
    
    def analyze_correlations(self, portfolio: List[Dict]) -> str:
        """Analyze correlations between different asset classes."""
        return self.execute({
            "message": "Analyze the correlation risks in my portfolio across stocks, crypto, and forex. Identify potential hedging opportunities and diversification improvements",
            "portfolio": portfolio,
            "orders": []
        })
    
    def market_outlook_analysis(self, portfolio: List[Dict]) -> str:
        """Provide market outlook across different asset classes."""
        return self.execute({
            "message": "Provide a market outlook analysis considering global economic factors, central bank policies, and their impact on stocks, cryptocurrencies, and forex markets. How should I position my portfolio?",
            "portfolio": portfolio,
            "orders": []
        })
    
    def generate_rebalancing_suggestions(self, portfolio: List[Dict], target_allocation: Dict[str, float] = None) -> str:
        """Generate portfolio rebalancing suggestions."""
        if target_allocation is None:
            target_allocation = {"stock": 60.0, "crypto": 20.0, "forex": 20.0}
        
        message = f"Analyze my current portfolio allocation and suggest rebalancing actions to achieve target allocation: {target_allocation}. Consider transaction costs, tax implications, and market timing."
        
        return self.execute({
            "message": message,
            "portfolio": portfolio,
            "orders": []
        })
    
    def get_asset_specific_advice(self, asset_type: str, portfolio: List[Dict]) -> str:
        """Get advice specific to an asset type."""
        asset_positions = [p for p in portfolio if p.get('asset_type') == asset_type]
        
        advice_prompts = {
            "stock": "Analyze my stock positions and provide advice on sector diversification, dividend yield optimization, and growth vs value balance.",
            "crypto": "Analyze my cryptocurrency positions and provide advice on DeFi opportunities, staking yields, regulatory risks, and volatility management.",
            "forex": "Analyze my forex positions and provide advice on interest rate differentials, carry trade opportunities, and hedging strategies."
        }
        
        message = advice_prompts.get(asset_type, f"Provide advice for my {asset_type} positions")
        
        return self.execute({
            "message": message,
            "portfolio": asset_positions,
            "orders": []
        })