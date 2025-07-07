"""
Trading Opportunity Model
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TradingOpportunity:
    """Represents a trading opportunity"""

    symbol: str
    current_price: float
    volume_ratio: float
    volatility: float
    technical_score: float
    sentiment_score: float
    news_score: float
    market_cap: float
    timestamp: datetime

    # Calculated fields
    risk_score: Optional[float] = None
    potential_return: Optional[float] = None
    score: Optional[float] = None

    def __post_init__(self):
        """Initialize calculated fields"""
        if self.risk_score is None:
            self.risk_score = 0.5  # Default risk score

        if self.potential_return is None:
            self.potential_return = 0.0  # Default potential return

        if self.score is None:
            self.score = 0.0  # Default score

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "volume_ratio": self.volume_ratio,
            "volatility": self.volatility,
            "technical_score": self.technical_score,
            "sentiment_score": self.sentiment_score,
            "news_score": self.news_score,
            "market_cap": self.market_cap,
            "timestamp": self.timestamp.isoformat(),
            "risk_score": self.risk_score,
            "potential_return": self.potential_return,
            "score": self.score,
        }
