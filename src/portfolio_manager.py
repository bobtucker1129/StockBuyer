"""
Portfolio Manager - Tracks positions, P&L, and portfolio performance
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import sqlite3
import os
import yfinance as yf

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manages portfolio positions, P&L, and performance tracking"""

    def __init__(self, config, strategy_name: str = "default"):
        self.config = config
        self.strategy_name = strategy_name
        self.account_balance = config.account_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.last_reset_date = datetime.now().date()

        # Strategy-specific database
        self.db_file = f"trading_data_{strategy_name}.db"
        self.init_database()

        logger.info(f"💰 Portfolio Manager initialized for {strategy_name}")

    def init_database(self):
        """Initialize SQLite database for portfolio tracking"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Create trades table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    shares INTEGER NOT NULL,
                    price REAL NOT NULL,
                    total REAL NOT NULL,
                    type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    opportunity_score REAL,
                    risk_score REAL
                )
            """
            )

            # Create positions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    shares INTEGER NOT NULL,
                    avg_price REAL NOT NULL,
                    current_price REAL,
                    total_value REAL,
                    pnl REAL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create portfolio_summary table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_balance REAL NOT NULL,
                    total_pnl REAL NOT NULL,
                    daily_pnl REAL NOT NULL,
                    positions_count INTEGER NOT NULL,
                    trades_today INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()
            conn.close()
            logger.info(f"📊 Database initialized: {self.db_file}")

        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")

    async def add_position(
        self, symbol: str, shares: int, price: float, score: float, risk_score: float
    ):
        """Add a new position to the portfolio"""
        try:
            if shares <= 0:
                logger.warning(f"⚠️  Invalid shares for {symbol}: {shares}")
                return

            # Calculate position details
            total_value = shares * price
            self.account_balance -= total_value

            # Store position
            self.positions[symbol] = {
                "shares": shares,
                "avg_price": price,
                "current_price": price,
                "total_value": total_value,
                "pnl": 0.0,
                "score": score,
                "risk_score": risk_score,
            }

            # Store in database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Insert trade record
            cursor.execute(
                """
                INSERT INTO trades (symbol, shares, price, total, type, opportunity_score, risk_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (symbol, shares, price, total_value, "BUY", score, risk_score),
            )

            # Update positions table
            cursor.execute(
                """
                INSERT OR REPLACE INTO positions (symbol, shares, avg_price, current_price, total_value, pnl)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (symbol, shares, price, price, total_value, 0.0),
            )

            conn.commit()
            conn.close()

            self.trades_today += 1
            logger.info(
                f"📈 Added position: {shares} shares of {symbol} at ${price:.2f}"
            )
            logger.info(f"💰 Remaining balance: ${self.account_balance:.2f}")

        except Exception as e:
            logger.error(f"❌ Error adding position for {symbol}: {e}")

    async def update_position(self, symbol: str, current_price: float):
        """Update position with current market price"""
        try:
            if symbol not in self.positions:
                return

            position = self.positions[symbol]
            shares = position["shares"]
            avg_price = position["avg_price"]

            # Calculate new values
            total_value = shares * current_price
            pnl = total_value - (shares * avg_price)

            # Update position
            position["current_price"] = current_price
            position["total_value"] = total_value
            position["pnl"] = pnl

            # Update database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE positions 
                SET current_price = ?, total_value = ?, pnl = ?, last_updated = CURRENT_TIMESTAMP
                WHERE symbol = ?
            """,
                (current_price, total_value, pnl, symbol),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Error updating position for {symbol}: {e}")

    async def review_positions(self):
        """Review and update all positions with current market prices"""
        logger.info("🔍 Reviewing portfolio positions")

        for symbol in list(self.positions.keys()):
            try:
                # Get current market price
                current_price = await self.get_current_price(symbol)
                if current_price > 0:
                    await self.update_position(symbol, current_price)

                    # Check stop loss and take profit
                    await self.check_stop_loss_take_profit(symbol, current_price)

            except Exception as e:
                logger.error(f"❌ Error reviewing position for {symbol}: {e}")

    async def check_stop_loss_take_profit(self, symbol: str, current_price: float):
        """Check if position should be closed due to stop loss or take profit"""
        try:
            position = self.positions[symbol]
            avg_price = position["avg_price"]
            shares = position["shares"]

            # Calculate percentage change
            price_change_pct = ((current_price - avg_price) / avg_price) * 100

            # Check stop loss
            stop_loss_pct = -self.config.stop_loss_percentage
            if price_change_pct <= stop_loss_pct:
                await self.close_position(symbol, current_price, "Stop Loss")
                return

            # Check take profit
            take_profit_pct = self.config.take_profit_percentage
            if price_change_pct >= take_profit_pct:
                await self.close_position(symbol, current_price, "Take Profit")
                return

        except Exception as e:
            logger.error(f"❌ Error checking stop loss/take profit for {symbol}: {e}")

    async def close_position(self, symbol: str, current_price: float, reason: str):
        """Close a position"""
        try:
            position = self.positions[symbol]
            shares = position["shares"]
            avg_price = position["avg_price"]

            # Calculate P&L
            total_value = shares * current_price
            pnl = total_value - (shares * avg_price)

            # Update account balance
            self.account_balance += total_value
            self.total_pnl += pnl
            self.daily_pnl += pnl

            # Remove position
            del self.positions[symbol]

            # Store trade record
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO trades (symbol, shares, price, total, type)
                VALUES (?, ?, ?, ?, ?)
            """,
                (symbol, shares, current_price, total_value, "SELL"),
            )

            # Remove from positions table
            cursor.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))

            conn.commit()
            conn.close()

            logger.info(
                f"📉 Closed position: {shares} shares of {symbol} at ${current_price:.2f} ({reason})"
            )
            logger.info(f"💰 P&L: ${pnl:.2f}, Total P&L: ${self.total_pnl:.2f}")

        except Exception as e:
            logger.error(f"❌ Error closing position for {symbol}: {e}")

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

    async def update_portfolio(self):
        """Update portfolio summary"""
        try:
            # Update all positions with current prices
            for symbol in list(self.positions.keys()):
                current_price = await self.get_current_price(symbol)
                if current_price > 0:
                    await self.update_position(symbol, current_price)

            # Calculate portfolio summary
            total_portfolio_value = self.account_balance
            total_pnl = 0.0

            for position in self.positions.values():
                total_portfolio_value += position["total_value"]
                total_pnl += position["pnl"]

            # Store portfolio summary
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO portfolio_summary (account_balance, total_pnl, daily_pnl, positions_count, trades_today)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    self.account_balance,
                    total_pnl,
                    self.daily_pnl,
                    len(self.positions),
                    self.trades_today,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(
                f"📊 Portfolio updated - Balance: ${self.account_balance:.2f}, Total P&L: ${total_pnl:.2f}"
            )

        except Exception as e:
            logger.error(f"❌ Error updating portfolio: {e}")

    def get_available_capital(self) -> float:
        """Get available capital for new positions"""
        return self.account_balance

    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in a symbol"""
        return symbol in self.positions

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        return {
            "account_balance": self.account_balance,
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "positions_count": len(self.positions),
            "trades_today": self.trades_today,
            "total_positions_value": sum(
                pos["total_value"] for pos in self.positions.values()
            ),
            "strategy_name": self.strategy_name,
        }

    def reset_daily_stats(self):
        """Reset daily statistics"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.last_reset_date = today

    async def shutdown(self):
        """Shutdown the portfolio manager"""
        logger.info("🛑 Portfolio manager shutdown complete")
