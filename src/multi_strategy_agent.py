"""
Multi-Strategy Trading Agent - Runs multiple trading strategies simultaneously
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import yaml
import sqlite3
import os

from .research_engine import ResearchEngine
from .trading_engine import TradingEngine
from .portfolio_manager import PortfolioManager
from .models.trading_opportunity import TradingOpportunity
from .config import Config

logger = logging.getLogger(__name__)


class MultiStrategyAgent:
    """Multi-strategy trading agent that runs multiple strategies simultaneously"""

    def __init__(self, config: Config):
        self.config = config
        self.strategies = {}
        self.is_running = False

        # Load strategy configurations
        self.load_strategy_configs()

        # Initialize strategies
        self.initialize_strategies()

        logger.info("🤖 Multi-Strategy Trading Agent initialized")

    def load_strategy_configs(self):
        """Load strategy configurations from config file"""
        try:
            with open("config.yaml", "r") as f:
                config_data = yaml.safe_load(f)

            self.strategy_configs = config_data.get("strategies", {})
            logger.info(f"📊 Loaded {len(self.strategy_configs)} strategies")

        except Exception as e:
            logger.error(f"❌ Error loading strategy configs: {e}")
            self.strategy_configs = {}

    def initialize_strategies(self):
        """Initialize each trading strategy"""
        for strategy_name, strategy_config in self.strategy_configs.items():
            try:
                # Create strategy-specific config
                strategy_config_obj = self.create_strategy_config(
                    strategy_name, strategy_config
                )

                # Initialize components for this strategy
                research_engine = ResearchEngine(strategy_config_obj.research)
                trading_engine = TradingEngine(strategy_config_obj.trading)
                portfolio_manager = PortfolioManager(
                    strategy_config_obj.trading, strategy_name
                )

                # Store strategy components
                self.strategies[strategy_name] = {
                    "config": strategy_config_obj,
                    "research_engine": research_engine,
                    "trading_engine": trading_engine,
                    "portfolio_manager": portfolio_manager,
                    "daily_opportunities": [],
                    "is_active": True,
                }

                logger.info(f"✅ Initialized {strategy_name} strategy")

            except Exception as e:
                logger.error(f"❌ Error initializing {strategy_name} strategy: {e}")

    def create_strategy_config(
        self, strategy_name: str, strategy_config: dict
    ) -> Config:
        """Create a Config object for a specific strategy"""
        # Create a copy of the base config
        strategy_config_obj = Config()

        # Override with strategy-specific settings
        strategy_config_obj.trading.account_balance = strategy_config.get(
            "account_balance", 10000.0
        )
        strategy_config_obj.trading.risk_percentage = strategy_config.get(
            "risk_percentage", 2.0
        )
        strategy_config_obj.trading.max_position_size = strategy_config.get(
            "max_position_size", 5.0
        )
        strategy_config_obj.system.max_daily_trades = strategy_config.get(
            "max_daily_trades", 10
        )
        strategy_config_obj.system.max_daily_loss = strategy_config.get(
            "max_daily_loss", 5.0
        )
        strategy_config_obj.trading.stop_loss_percentage = strategy_config.get(
            "stop_loss_percentage", 3.0
        )
        strategy_config_obj.trading.take_profit_percentage = strategy_config.get(
            "take_profit_percentage", 6.0
        )

        # Store strategy-specific thresholds
        strategy_config_obj.trading.min_score_threshold = strategy_config.get(
            "min_score_threshold", 0.1
        )
        strategy_config_obj.trading.max_risk_score = strategy_config.get(
            "max_risk_score", 0.8
        )

        return strategy_config_obj

    async def run(self):
        """Main trading loop for all strategies"""
        self.is_running = True
        logger.info(f"🚀 Starting multi-strategy trading agent")

        while self.is_running:
            try:
                # Daily trading cycle for all strategies
                await self.daily_trading_cycle()

                # Wait until next trading day
                await self.wait_for_next_trading_day()

            except Exception as e:
                logger.error(f"❌ Error in multi-strategy trading cycle: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def daily_trading_cycle(self):
        """Execute daily trading cycle for all strategies"""
        logger.info("📅 Starting daily trading cycle for all strategies")

        # Research phase (shared across all strategies)
        opportunities = await self.research_opportunities()

        # Execute trades for each strategy
        for strategy_name, strategy_data in self.strategies.items():
            if strategy_data["is_active"]:
                try:
                    await self.execute_strategy_trades(strategy_name, opportunities)
                except Exception as e:
                    logger.error(f"❌ Error executing {strategy_name} strategy: {e}")

        logger.info("✅ Daily trading cycle completed for all strategies")

    async def research_opportunities(self) -> List[TradingOpportunity]:
        """Research opportunities (shared across all strategies)"""
        # Use the first strategy's research engine for shared research
        first_strategy = list(self.strategies.values())[0]
        research_engine = first_strategy["research_engine"]

        opportunities = await research_engine.find_opportunities()
        logger.info(
            f"🔍 Researched {len(opportunities)} opportunities for all strategies"
        )

        return opportunities

    async def execute_strategy_trades(
        self, strategy_name: str, opportunities: List[TradingOpportunity]
    ):
        """Execute trades for a specific strategy"""
        strategy_data = self.strategies[strategy_name]
        config = strategy_data["config"]
        trading_engine = strategy_data["trading_engine"]
        portfolio_manager = strategy_data["portfolio_manager"]

        logger.info(f"💼 Executing trades for {strategy_name} strategy")

        # Analyze and rank opportunities for this strategy
        ranked_opportunities = await self.analyze_and_rank_opportunities(
            opportunities, config
        )

        # Portfolio review
        await portfolio_manager.review_positions()

        # Execute trades
        trades_executed = 0
        max_trades = config.system.max_daily_trades

        for opportunity in ranked_opportunities[:max_trades]:
            try:
                # Check if we should take this position for this strategy
                if await self.should_take_position(opportunity, strategy_name):
                    # Execute the trade
                    await trading_engine.execute_trade(opportunity)

                    # Add to portfolio
                    shares = int(
                        trading_engine.calculate_position_size(opportunity)
                        / opportunity.current_price
                    )
                    await portfolio_manager.add_position(
                        opportunity.symbol,
                        shares,
                        opportunity.current_price,
                        opportunity.score,
                        opportunity.risk_score,
                    )

                    trades_executed += 1
                    logger.info(
                        f"✅ Executed {strategy_name} trade for {opportunity.symbol}"
                    )

                    # Check if we've hit daily trade limit
                    if trades_executed >= max_trades:
                        logger.info(
                            f"🛑 Reached daily trade limit for {strategy_name} ({max_trades})"
                        )
                        break

            except Exception as e:
                logger.error(
                    f"❌ Error executing {strategy_name} trade for {opportunity.symbol}: {e}"
                )

        logger.info(
            f"📊 Executed {trades_executed} trades for {strategy_name} strategy"
        )

        # Update portfolio
        await portfolio_manager.update_portfolio()

    async def analyze_and_rank_opportunities(
        self, opportunities: List[TradingOpportunity], config: Config
    ) -> List[TradingOpportunity]:
        """Analyze and rank trading opportunities for a specific strategy"""
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

    async def should_take_position(
        self, opportunity: TradingOpportunity, strategy_name: str
    ) -> bool:
        """Determine if we should take a position based on strategy-specific risk management"""
        strategy_data = self.strategies[strategy_name]
        config = strategy_data["config"]
        portfolio_manager = strategy_data["portfolio_manager"]

        # Check if we have enough capital
        available_capital = portfolio_manager.get_available_capital()
        position_size = strategy_data["trading_engine"].calculate_position_size(
            opportunity
        )

        if position_size > available_capital:
            logger.info(
                f"💰 Insufficient capital for {strategy_name} - {opportunity.symbol}"
            )
            return False

        # Check if we already have a position in this stock
        if portfolio_manager.has_position(opportunity.symbol):
            logger.info(
                f"📈 Already have position in {strategy_name} - {opportunity.symbol}"
            )
            return False

        # Check risk limits (strategy-specific)
        max_risk_score = config.trading.max_risk_score
        if opportunity.risk_score > max_risk_score:
            logger.info(
                f"⚠️  Risk too high for {strategy_name} - {opportunity.symbol}: {opportunity.risk_score:.3f}"
            )
            return False

        # Check daily loss limit (strategy-specific)
        portfolio_summary = portfolio_manager.get_portfolio_summary()
        max_daily_loss = config.system.max_daily_loss
        if portfolio_summary["daily_pnl"] < -max_daily_loss:
            logger.info(
                f"🛑 Daily loss limit reached for {strategy_name}: ${portfolio_summary['daily_pnl']:.2f}"
            )
            return False

        # Check minimum score threshold (strategy-specific)
        min_score_threshold = config.trading.min_score_threshold
        if opportunity.score < min_score_threshold:
            logger.info(
                f"📉 Score too low for {strategy_name} - {opportunity.symbol}: {opportunity.score:.3f}"
            )
            return False

        return True

    async def wait_for_next_trading_day(self):
        """Wait until the next trading day"""
        now = datetime.now()
        next_trading_day = self.get_next_trading_day(now)
        wait_time = (next_trading_day - now).total_seconds()

        logger.info(f"⏰ Waiting {wait_time/3600:.1f} hours until next trading day")
        await asyncio.sleep(wait_time)

    def get_next_trading_day(self, current_time: datetime) -> datetime:
        """Get the next trading day"""
        # Simple implementation - wait 24 hours
        next_day = current_time + timedelta(days=1)
        return next_day

    def get_status(self) -> Dict[str, Any]:
        """Get status of all strategies"""
        status = {"is_running": self.is_running, "strategies": {}}

        for strategy_name, strategy_data in self.strategies.items():
            portfolio_manager = strategy_data["portfolio_manager"]
            portfolio_summary = portfolio_manager.get_portfolio_summary()

            status["strategies"][strategy_name] = {
                "is_active": strategy_data["is_active"],
                "account_balance": portfolio_summary["account_balance"],
                "total_pnl": portfolio_summary["total_pnl"],
                "daily_pnl": portfolio_summary["daily_pnl"],
                "positions_count": portfolio_summary["positions_count"],
                "trades_today": portfolio_summary["trades_today"],
                "opportunities_count": len(strategy_data["daily_opportunities"]),
            }

        return status

    async def shutdown(self):
        """Shutdown the multi-strategy agent"""
        self.is_running = False

        for strategy_name, strategy_data in self.strategies.items():
            try:
                await strategy_data["trading_engine"].shutdown()
                await strategy_data["portfolio_manager"].shutdown()
                logger.info(f"🛑 {strategy_name} strategy shutdown complete")
            except Exception as e:
                logger.error(f"❌ Error shutting down {strategy_name} strategy: {e}")

        logger.info("🛑 Multi-strategy trading agent shutdown complete")
