# modules/ai/portfolio_agent.py
import openai
from typing import Any, Dict, Optional, List
import json

from core.interfaces import IModule

class AIPortfolioAgent(IModule):
    """AI-powered portfolio analysis agent using DeepSeek."""
    
    def __init__(self, module_id: Optional[str] = "ai_portfolio_agent"):
        super().__init__(module_id=module_id)
        self.api_key = ""
        self.model = "deepseek-chat"
        self.base_url = "https://api.deepseek.com"
        self.client = None
        self.system_prompt = """
        You are an expert portfolio manager and risk analyst. Your tasks:
        1) Evaluate portfolio risk and exposure
        2) Analyze current positions and open orders
        3) Suggest improvements and optimizations
        4) Provide clear, actionable insights
        5) Identify potential risks and opportunities
        
        Always provide specific, data-driven recommendations.
        """
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the AI agent."""
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "deepseek-chat")
        self.base_url = config.get("base_url", "https://api.deepseek.com")
        
        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        
        super().configure(config)
    
    def execute(self, input_data: Dict[str, Any]) -> str:
        """Analyze portfolio and provide AI insights."""
        if not self.client:
            return "AI agent not configured - missing API key"
            
        user_message = input_data.get("message", "")
        portfolio = input_data.get("portfolio", [])
        orders = input_data.get("orders", [])
        
        # Create analysis prompt
        prompt = f"""
        Portfolio Analysis Request: {user_message}
        
        Current Portfolio:
        {json.dumps(portfolio, indent=2)}
        
        Open Orders:
        {json.dumps(orders, indent=2)}
        
        Please provide your analysis and recommendations.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"Error getting AI analysis: {e}"
    
    def analyze_risk(self, portfolio: List[Dict]) -> str:
        """Analyze portfolio risk."""
        return self.execute({
            "message": "Analyze the risk profile of my current portfolio",
            "portfolio": portfolio,
            "orders": []
        })
    
    def suggest_optimizations(self, portfolio: List[Dict], orders: List[Dict]) -> str:
        """Suggest portfolio optimizations."""
        return self.execute({
            "message": "Suggest optimizations for my trading strategy and portfolio allocation",
            "portfolio": portfolio,
            "orders": orders
        })