"""
Main Trading Agent - Orchestrates research and trading activities
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .research_engine import ResearchEngine
from .trading_engine import TradingEngine
from .portfolio_manager import PortfolioManager
from .models.trading_opportunity import TradingOpportunity
from .config import Config

logger = logging.getLogger(__name__)


class TradingAgent:
    """Main trading agent that coordinates research and trading"""

    def __init__(self, config: Config):
        self.config = config
        self.research_engine = ResearchEngine(config.research)
        self.trading_engine = TradingEngine(config.trading)
        self.portfolio_manager = PortfolioManager(config.trading)

        self.is_running = False
        self.daily_opportunities: List[TradingOpportunity] = []

        logger.info("🤖 Trading Agent initialized")

    async def run(self):
        """Main trading loop"""
        self.is_running = True
        logger.info(f"🚀 Starting trading agent in {self.config.trading.mode} mode")

        while self.is_running:
            try:
                # Daily trading cycle
                await self.daily_trading_cycle()

                # Wait until next trading day
                await self.wait_for_next_trading_day()

            except Exception as e:
                logger.error(f"❌ Error in trading cycle: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def daily_trading_cycle(self):
        """Execute one complete daily trading cycle"""
        logger.info("📅 Starting daily trading cycle")

        # 1. Research phase
        opportunities = await self.research_engine.find_opportunities()
        self.daily_opportunities = opportunities

        # 2. Analysis and ranking
        ranked_opportunities = await self.analyze_and_rank_opportunities(opportunities)

        # 3. Portfolio review
        await self.portfolio_manager.review_positions()

        # 4. Execute trades
        await self.execute_trades(ranked_opportunities)

        # 5. Update portfolio
        await self.portfolio_manager.update_portfolio()

        logger.info("✅ Daily trading cycle completed")

    async def analyze_and_rank_opportunities(
        self, opportunities: List[TradingOpportunity]
    ) -> List[TradingOpportunity]:
        """Analyze and rank trading opportunities by potential return"""
        logger.info(f"📊 Analyzing {len(opportunities)} opportunities")

        for opportunity in opportunities:
            # Calculate risk-adjusted return
            risk_score = self.calculate_risk_score(opportunity)
            potential_return = self.calculate_potential_return(opportunity)

            opportunity.risk_score = risk_score
            opportunity.potential_return = potential_return
            opportunity.score = potential_return / (
                risk_score + 0.1
            )  # Avoid division by zero

        # Sort by score (highest first)
        ranked = sorted(opportunities, key=lambda x: x.score, reverse=True)

        logger.info(f"🏆 Top opportunities: {[o.symbol for o in ranked[:3]]}")
        return ranked

    def calculate_risk_score(self, opportunity: TradingOpportunity) -> float:
        """Calculate risk score based on volatility, volume, and other factors"""
        # Simplified risk calculation
        volatility = opportunity.volatility or 0.2
        volume_ratio = opportunity.volume_ratio or 1.0
        market_cap = opportunity.market_cap or 1000000000

        risk_score = volatility * (1 / volume_ratio) * (1000000000 / market_cap)
        return min(risk_score, 1.0)  # Cap at 1.0

    def calculate_potential_return(self, opportunity: TradingOpportunity) -> float:
        """Calculate potential return based on technical indicators and sentiment"""
        sentiment_score = opportunity.sentiment_score or 0.0
        technical_score = opportunity.technical_score or 0.0
        news_score = opportunity.news_score or 0.0

        # Weighted average of different factors
        potential_return = (
            sentiment_score * 0.3 + technical_score * 0.4 + news_score * 0.3
        )

        return max(potential_return, 0.0)

    async def execute_trades(self, opportunities: List[TradingOpportunity]):
        """Execute trades based on ranked opportunities"""
        logger.info(f"💼 Executing trades for {len(opportunities)} opportunities")

        trades_executed = 0
        max_trades = self.config.system.max_daily_trades

        for opportunity in opportunities[:max_trades]:  # Limit to max trades per day
            try:
                # Check if we should take this position
                if await self.should_take_position(opportunity):
                    # Execute the trade
                    await self.trading_engine.execute_trade(opportunity)

                    # Add to portfolio
                    shares = int(
                        self.trading_engine.calculate_position_size(opportunity)
                        / opportunity.current_price
                    )
                    await self.portfolio_manager.add_position(
                        opportunity.symbol,
                        shares,
                        opportunity.current_price,
                        opportunity.score,
                        opportunity.risk_score,
                    )

                    trades_executed += 1
                    logger.info(f"✅ Executed trade for {opportunity.symbol}")

                    # Check if we've hit daily trade limit
                    if trades_executed >= max_trades:
                        logger.info(f"🛑 Reached daily trade limit ({max_trades})")
                        break

            except Exception as e:
                logger.error(f"❌ Error executing trade for {opportunity.symbol}: {e}")

        logger.info(f"📊 Executed {trades_executed} trades today")

    async def should_take_position(self, opportunity: TradingOpportunity) -> bool:
        """Determine if we should take a position based on risk management"""
        # Check if we have enough capital
        available_capital = self.portfolio_manager.get_available_capital()
        position_size = self.trading_engine.calculate_position_size(opportunity)

        if position_size > available_capital:
            logger.info(f"💰 Insufficient capital for {opportunity.symbol}")
            return False

        # Check if we already have a position in this stock
        if self.portfolio_manager.has_position(opportunity.symbol):
            logger.info(f"📈 Already have position in {opportunity.symbol}")
            return False

        # Check risk limits
        if opportunity.risk_score > 0.8:
            logger.info(
                f"⚠️  Risk too high for {opportunity.symbol}: {opportunity.risk_score:.3f}"
            )
            return False

        # Check daily loss limit
        portfolio_summary = self.portfolio_manager.get_portfolio_summary()
        if portfolio_summary["daily_pnl"] < -self.config.system.max_daily_loss:
            logger.info(
                f"🛑 Daily loss limit reached: ${portfolio_summary['daily_pnl']:.2f}"
            )
            return False

        # Check minimum score threshold
        if opportunity.score < 0.1:
            logger.info(
                f"📉 Score too low for {opportunity.symbol}: {opportunity.score:.3f}"
            )
            return False

        return True

    async def wait_for_next_trading_day(self):
        """Wait until the next trading day"""
        now = datetime.now()
        next_trading_day = self.get_next_trading_day(now)

        wait_seconds = (next_trading_day - now).total_seconds()

        if wait_seconds > 0:
            logger.info(
                f"⏰ Waiting {wait_seconds/3600:.1f} hours until next trading day"
            )
            await asyncio.sleep(wait_seconds)
        else:
            # If it's already past the next trading day, wait 1 hour
            logger.info("⏰ Waiting 1 hour before next cycle")
            await asyncio.sleep(3600)

    def get_next_trading_day(self, current_time: datetime) -> datetime:
        """Get the next trading day (simplified - assumes weekdays)"""
        next_day = current_time + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            next_day += timedelta(days=1)

        # Set to market open time (9:30 AM ET)
        next_day = next_day.replace(hour=9, minute=30, second=0, microsecond=0)

        return next_day

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        portfolio_summary = self.portfolio_manager.get_portfolio_summary()

        return {
            "is_running": self.is_running,
            "mode": self.config.trading.mode,
            "account_balance": portfolio_summary["account_balance"],
            "total_pnl": portfolio_summary["total_pnl"],
            "daily_pnl": portfolio_summary["daily_pnl"],
            "positions_count": portfolio_summary["positions_count"],
            "trades_today": portfolio_summary["trades_today"],
            "opportunities_count": len(self.daily_opportunities),
        }

    async def shutdown(self):
        """Shutdown the trading agent"""
        self.is_running = False
        await self.trading_engine.shutdown()
        await self.portfolio_manager.shutdown()
        logger.info("🛑 Trading agent shutdown complete")
