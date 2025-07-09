"""
Configuration management for the trading agent
"""

import yaml
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TradingConfig:
    mode: str = "virtual"  # "virtual" or "real"
    account_balance: float = 10000.0
    risk_percentage: float = 2.0
    max_position_size: float = 5.0
    stop_loss_percentage: float = 3.0
    take_profit_percentage: float = 6.0
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper_trading: bool = True


@dataclass
class ResearchConfig:
    news_sources: List[str] = None
    sentiment_threshold: float = 0.3
    trend_analysis_window: int = 14
    max_research_time: int = 300
    research_start_time: str = "09:00"
    trading_start_time: str = "09:30"


@dataclass
class SystemConfig:
    database_url: str = "sqlite:///trading_data.db"
    log_level: str = "INFO"
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    max_daily_trades: int = 10
    max_daily_loss: float = 5.0
    emergency_stop_loss: float = 10.0


@dataclass
class VirtualTradingConfig:
    simulate_slippage: bool = True
    simulate_commissions: bool = True
    commission_rate: float = 0.005
    allow_short_selling: bool = True
    margin_trading: bool = False


@dataclass
class RealTradingConfig:
    broker: str = "alpaca"
    require_confirmation: bool = True
    max_trade_size: float = 1000.0
    daily_loss_limit: float = 500.0
    market_open: str = "09:30"
    market_close: str = "16:00"
    pre_market_start: str = "04:00"
    after_hours_end: str = "20:00"


@dataclass
class NotificationConfig:
    email_enabled: bool = False
    email_address: str = ""
    email_password: str = ""
    webhook_url: str = ""
    notify_on_trade: bool = True
    notify_on_loss: bool = True
    notify_on_profit: bool = True
    notify_on_daily_summary: bool = True


@dataclass
class LearningConfig:
    track_performance: bool = True
    performance_window: int = 30
    adapt_strategies: bool = True
    adaptation_threshold: float = 0.1
    enable_backtesting: bool = True
    backtest_days: int = 90


@dataclass
class Config:
    trading: TradingConfig = None
    research: ResearchConfig = None
    system: SystemConfig = None
    virtual_trading: VirtualTradingConfig = None
    real_trading: RealTradingConfig = None
    notifications: NotificationConfig = None
    learning: LearningConfig = None

    def __post_init__(self):
        # Initialize with defaults if not provided
        if self.trading is None:
            self.trading = TradingConfig()
        if self.research is None:
            self.research = ResearchConfig()
        if self.system is None:
            self.system = SystemConfig()
        if self.virtual_trading is None:
            self.virtual_trading = VirtualTradingConfig()
        if self.real_trading is None:
            self.real_trading = RealTradingConfig()
        if self.notifications is None:
            self.notifications = NotificationConfig()
        if self.learning is None:
            self.learning = LearningConfig()

        if self.research.news_sources is None:
            self.research.news_sources = [
                "https://finance.yahoo.com/news",
                "https://www.marketwatch.com/news",
                "https://seekingalpha.com/news",
                "https://www.cnbc.com/markets",
                "https://www.bloomberg.com/markets",
            ]

    @classmethod
    def from_file(cls, config_path: str = "config.yaml") -> "Config":
        """Load configuration from YAML file"""
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)

                # Extract nested configurations with safe defaults
                trading_data = data.get("trading", {})
                research_data = data.get("research", {})
                system_data = data.get("system", {})
                virtual_data = data.get("virtual_trading", {})
                real_data = data.get("real_trading", {})
                notification_data = data.get("notifications", {})
                learning_data = data.get("learning", {})

                # Create config objects with safe defaults
                trading_config = TradingConfig(**trading_data)
                research_config = ResearchConfig(**research_data)
                system_config = SystemConfig(**system_data)
                virtual_config = VirtualTradingConfig(**virtual_data)
                real_config = RealTradingConfig(**real_data)
                notification_config = NotificationConfig(**notification_data)
                learning_config = LearningConfig(**learning_data)

                return cls(
                    trading=trading_config,
                    research=research_config,
                    system=system_config,
                    virtual_trading=virtual_config,
                    real_trading=real_config,
                    notifications=notification_config,
                    learning=learning_config,
                )

        # Return default configuration if file doesn't exist
        return cls()

    def save(self, config_path: str = "config.yaml"):
        """Save configuration to YAML file"""
        data = {
            "trading": {
                "mode": self.trading.mode,
                "account_balance": self.trading.account_balance,
                "risk_percentage": self.trading.risk_percentage,
                "max_position_size": self.trading.max_position_size,
                "stop_loss_percentage": self.trading.stop_loss_percentage,
                "take_profit_percentage": self.trading.take_profit_percentage,
                "alpaca_api_key": self.trading.alpaca_api_key,
                "alpaca_secret_key": self.trading.alpaca_secret_key,
                "alpaca_paper_trading": self.trading.alpaca_paper_trading,
            },
            "research": {
                "news_sources": self.research.news_sources,
                "sentiment_threshold": self.research.sentiment_threshold,
                "trend_analysis_window": self.research.trend_analysis_window,
                "max_research_time": self.research.max_research_time,
                "research_start_time": self.research.research_start_time,
                "trading_start_time": self.research.trading_start_time,
            },
            "system": {
                "database_url": self.system.database_url,
                "log_level": self.system.log_level,
                "dashboard_host": self.system.dashboard_host,
                "dashboard_port": self.system.dashboard_port,
                "max_daily_trades": self.system.max_daily_trades,
                "max_daily_loss": self.system.max_daily_loss,
                "emergency_stop_loss": self.system.emergency_stop_loss,
            },
            "virtual_trading": {
                "simulate_slippage": self.virtual_trading.simulate_slippage,
                "simulate_commissions": self.virtual_trading.simulate_commissions,
                "commission_rate": self.virtual_trading.commission_rate,
                "allow_short_selling": self.virtual_trading.allow_short_selling,
                "margin_trading": self.virtual_trading.margin_trading,
            },
            "real_trading": {
                "broker": self.real_trading.broker,
                "require_confirmation": self.real_trading.require_confirmation,
                "max_trade_size": self.real_trading.max_trade_size,
                "daily_loss_limit": self.real_trading.daily_loss_limit,
                "market_open": self.real_trading.market_open,
                "market_close": self.real_trading.market_close,
                "pre_market_start": self.real_trading.pre_market_start,
                "after_hours_end": self.real_trading.after_hours_end,
            },
            "notifications": {
                "email_enabled": self.notifications.email_enabled,
                "email_address": self.notifications.email_address,
                "email_password": self.notifications.email_password,
                "webhook_url": self.notifications.webhook_url,
                "notify_on_trade": self.notifications.notify_on_trade,
                "notify_on_loss": self.notifications.notify_on_loss,
                "notify_on_profit": self.notifications.notify_on_profit,
                "notify_on_daily_summary": self.notifications.notify_on_daily_summary,
            },
            "learning": {
                "track_performance": self.learning.track_performance,
                "performance_window": self.learning.performance_window,
                "adapt_strategies": self.learning.adapt_strategies,
                "adaptation_threshold": self.learning.adaptation_threshold,
                "enable_backtesting": self.learning.enable_backtesting,
                "backtest_days": self.learning.backtest_days,
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)
