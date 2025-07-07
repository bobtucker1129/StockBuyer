"""
Trading Engine - Executes trades and manages orders
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import yfinance as yf
import random

from .models.trading_opportunity import TradingOpportunity
from .config import TradingConfig

logger = logging.getLogger(__name__)


class TradingEngine:
    """Trading engine that executes trades"""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.is_virtual = config.mode == "virtual"

        if not self.is_virtual:
            # Initialize real trading API connections
            self.setup_real_trading()

        logger.info(f"🏦 Trading Engine initialized in {config.mode} mode")

    def setup_real_trading(self):
        """Setup real trading API connections"""
        # This would initialize connections to Alpaca, TD Ameritrade, etc.
        # For now, we'll keep it virtual
        logger.warning("⚠️  Real trading not implemented yet - using virtual mode")
        self.is_virtual = True

    async def execute_trade(self, opportunity: TradingOpportunity):
        """Execute a trade based on the opportunity"""
        logger.info(f"💼 Executing trade for {opportunity.symbol}")

        if self.is_virtual:
            await self.execute_virtual_trade(opportunity)
        else:
            await self.execute_real_trade(opportunity)

    async def execute_virtual_trade(self, opportunity: TradingOpportunity):
        """Execute a virtual trade (paper trading)"""
        try:
            # Get current market price
            current_price = await self.get_current_price(opportunity.symbol)

            if current_price <= 0:
                logger.warning(
                    f"⚠️  Invalid price for {opportunity.symbol}: ${current_price}"
                )
                return

            # Calculate position size based on risk management
            position_size = self.calculate_position_size(opportunity)
            shares = int(position_size / current_price)

            if shares > 0:
                # Simulate market conditions
                execution_price = self.simulate_market_conditions(current_price)

                # Record the virtual trade
                trade = {
                    "symbol": opportunity.symbol,
                    "shares": shares,
                    "price": execution_price,
                    "total": shares * execution_price,
                    "timestamp": datetime.now(),
                    "type": "BUY",
                    "opportunity_score": opportunity.score,
                    "risk_score": opportunity.risk_score,
                }

                # Apply commission simulation
                if (
                    self.config.alpaca_paper_trading
                ):  # Using this as virtual config flag
                    commission = trade["total"] * 0.005  # 0.5% commission
                    trade["commission"] = commission
                    trade["total_with_commission"] = trade["total"] + commission

                logger.info(
                    f"✅ Virtual trade executed: {shares} shares of {opportunity.symbol} at ${execution_price:.2f}"
                )
                logger.info(
                    f"💰 Total: ${trade['total']:.2f}, Score: {opportunity.score:.3f}"
                )

                # Store trade in virtual portfolio
                await self.store_virtual_trade(trade)

            else:
                logger.warning(f"⚠️  Position size too small for {opportunity.symbol}")

        except Exception as e:
            logger.error(
                f"❌ Error executing virtual trade for {opportunity.symbol}: {e}"
            )

    async def execute_real_trade(self, opportunity: TradingOpportunity):
        """Execute a real trade through broker API"""
        # This would implement real trading through Alpaca, TD Ameritrade, etc.
        logger.warning("⚠️  Real trading not implemented yet")

    async def get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get("regularMarketPrice", 0)

            if current_price == 0:
                # Fallback to historical data
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = hist["Close"].iloc[-1]

            return current_price

        except Exception as e:
            logger.error(f"❌ Error getting current price for {symbol}: {e}")
            return 0

    def calculate_position_size(self, opportunity: TradingOpportunity) -> float:
        """Calculate position size based on risk management"""
        # Use account balance from config
        account_balance = self.config.account_balance

        # Calculate risk amount
        risk_amount = account_balance * (self.config.risk_percentage / 100)

        # Adjust position size based on risk score
        # Lower risk score = larger position
        risk_adjustment = 1 - opportunity.risk_score
        position_size = risk_amount * (1 + risk_adjustment)

        # Cap at maximum position size
        max_position = account_balance * (self.config.max_position_size / 100)
        position_size = min(position_size, max_position)

        # Ensure minimum position size
        min_position = 100  # $100 minimum
        position_size = max(position_size, min_position)

        return position_size

    def simulate_market_conditions(self, base_price: float) -> float:
        """Simulate real market conditions like slippage"""
        # Simulate small price variations
        variation = random.uniform(-0.02, 0.02)  # ±2% variation
        execution_price = base_price * (1 + variation)

        return execution_price

    async def store_virtual_trade(self, trade: Dict[str, Any]):
        """Store virtual trade in database"""
        # This would store the trade in a database
        # For now, just log it
        logger.info(
            f"📊 Stored virtual trade: {trade['symbol']} - {trade['shares']} shares @ ${trade['price']:.2f}"
        )

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of current portfolio"""
        # This would calculate portfolio value, P&L, etc.
        return {
            "total_value": 0,
            "total_pnl": 0,
            "positions": [],
            "cash_balance": self.config.account_balance,
        }

    async def shutdown(self):
        """Shutdown the trading engine"""
        logger.info("🛑 Trading engine shutdown complete")
