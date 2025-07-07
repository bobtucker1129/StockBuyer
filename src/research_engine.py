"""
Research Engine - Finds trading opportunities through news, sentiment, and technical analysis
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import ta
import pandas as pd
import numpy as np

from .models.trading_opportunity import TradingOpportunity
from .config import ResearchConfig

logger = logging.getLogger(__name__)


class ResearchEngine:
    """Research engine that finds trading opportunities"""

    def __init__(self, config: ResearchConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    async def find_opportunities(self) -> List[TradingOpportunity]:
        """Find trading opportunities through various research methods"""
        logger.info("🔍 Starting research phase")

        opportunities = []

        # 1. Get trending stocks
        trending_stocks = await self.get_trending_stocks()
        logger.info(f"📈 Found {len(trending_stocks)} trending stocks")

        # 2. Research each trending stock
        for symbol in trending_stocks:
            try:
                opportunity = await self.research_stock(symbol)
                if opportunity:
                    opportunities.append(opportunity)
                    logger.info(
                        f"✅ Researched {symbol}: Score={opportunity.score:.3f}"
                    )
            except Exception as e:
                logger.error(f"❌ Error researching {symbol}: {e}")

        # 3. Get news-based opportunities
        news_opportunities = await self.get_news_opportunities()
        opportunities.extend(news_opportunities)

        # 4. Sort by score
        opportunities.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"🎯 Found {len(opportunities)} trading opportunities")
        return opportunities

    async def get_trending_stocks(self) -> List[str]:
        """Get list of trending stocks from various sources"""
        trending = []

        # Popular stocks for research
        popular_stocks = [
            "AAPL",
            "GOOGL",
            "MSFT",
            "TSLA",
            "AMZN",
            "NVDA",
            "META",
            "NFLX",
            "AMD",
            "INTC",
            "CRM",
            "ADBE",
            "PYPL",
            "UBER",
            "LYFT",
            "SNAP",
            "SPY",
            "QQQ",
            "IWM",
            "VTI",  # ETFs for diversification
        ]
        trending.extend(popular_stocks)

        # Get some random stocks for variety
        random_stocks = [
            "PLTR",
            "COIN",
            "RBLX",
            "HOOD",
            "ZM",
            "SQ",
            "SHOP",
            "TWTR",
            "BYND",
            "PTON",
            "ZM",
            "DOCU",
            "CRWD",
            "OKTA",
            "ZM",
            "TEAM",
        ]
        trending.extend(random_stocks)

        return list(set(trending))  # Remove duplicates

    async def research_stock(self, symbol: str) -> TradingOpportunity:
        """Research a specific stock and create trading opportunity"""
        logger.info(f"🔬 Researching {symbol}")

        try:
            # Get stock data
            stock_data = await self.get_stock_data(symbol)
            if stock_data is None or stock_data.empty:
                logger.warning(f"⚠️  No data available for {symbol}")
                return None

            # Calculate technical indicators
            technical_indicators = self.calculate_technical_indicators(stock_data)

            # Get sentiment analysis
            sentiment_score = await self.get_sentiment_score(symbol)

            # Get news analysis
            news_score = await self.get_news_score(symbol)

            # Calculate market cap (simplified)
            market_cap = (
                stock_data["market_cap"].iloc[-1]
                if "market_cap" in stock_data.columns
                else 1000000000
            )

            # Create trading opportunity
            current_price = stock_data["Close"].iloc[-1]
            current_volume = stock_data["Volume"].iloc[-1]
            avg_volume = stock_data["Volume"].mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volatility = stock_data["Close"].pct_change().std()

            opportunity = TradingOpportunity(
                symbol=symbol,
                current_price=current_price,
                volume_ratio=volume_ratio,
                volatility=volatility,
                technical_score=technical_indicators["overall_score"],
                sentiment_score=sentiment_score,
                news_score=news_score,
                market_cap=market_cap,
                timestamp=datetime.now(),
            )

            # Calculate risk and potential return
            opportunity.risk_score = self.calculate_risk_score(opportunity)
            opportunity.potential_return = self.calculate_potential_return(opportunity)
            opportunity.score = opportunity.potential_return / (
                opportunity.risk_score + 0.1
            )

            return opportunity

        except Exception as e:
            logger.error(f"❌ Error researching {symbol}: {e}")
            return None

    async def get_stock_data(self, symbol: str) -> pd.DataFrame:
        """Get historical stock data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="30d")

            if data.empty:
                return None

            # Get market cap from ticker info
            try:
                info = ticker.info
                market_cap = info.get("marketCap", 1000000000)
                data["market_cap"] = market_cap
            except:
                data["market_cap"] = 1000000000

            return data

        except Exception as e:
            logger.error(f"❌ Error getting stock data for {symbol}: {e}")
            return None

    def calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate technical indicators for the stock"""
        try:
            # RSI
            rsi = ta.momentum.RSIIndicator(data["Close"]).rsi()
            rsi_val = rsi.iloc[-1]
            if pd.isna(rsi_val):
                rsi_score = 0
            else:
                rsi_score = (rsi_val - 50) / 50  # Normalize to -1 to 1

            # MACD
            macd = ta.trend.MACD(data["Close"])
            macd_line = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]
            if pd.isna(macd_line) or pd.isna(macd_signal):
                macd_score = 0
            else:
                macd_score = 1 if macd_line > macd_signal else -1

            # Moving averages
            sma_20 = ta.trend.SMAIndicator(data["Close"], window=20).sma_indicator()
            sma_50 = ta.trend.SMAIndicator(data["Close"], window=50).sma_indicator()
            sma_20_val = sma_20.iloc[-1]
            sma_50_val = sma_50.iloc[-1]
            if pd.isna(sma_20_val) or pd.isna(sma_50_val):
                ma_score = 0
            else:
                ma_score = 1 if sma_20_val > sma_50_val else -1

            # Volume - use simple volume comparison instead of VolumeSMAIndicator
            current_volume = data["Volume"].iloc[-1]
            avg_volume = data["Volume"].mean()
            volume_score = 1 if current_volume > avg_volume else -1

            # Bollinger Bands
            bb = ta.volatility.BollingerBands(data["Close"])
            current_price = data["Close"].iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]
            bb_upper = bb.bollinger_hband().iloc[-1]
            if (
                pd.isna(current_price)
                or pd.isna(bb_lower)
                or pd.isna(bb_upper)
                or (bb_upper - bb_lower) == 0
            ):
                bb_score = 0
            else:
                bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
                bb_score = 1 if bb_position > 0.8 else (-1 if bb_position < 0.2 else 0)

            # Overall technical score
            overall_score = (
                rsi_score + macd_score + ma_score + volume_score + bb_score
            ) / 5

            return {
                "rsi": rsi_score,
                "macd": macd_score,
                "ma": ma_score,
                "volume": volume_score,
                "bollinger": bb_score,
                "overall_score": overall_score,
            }

        except Exception as e:
            logger.error(f"❌ Error calculating technical indicators: {e}")
            return {"overall_score": 0}

    async def get_sentiment_score(self, symbol: str) -> float:
        """Get sentiment score for a stock from news and social media"""
        try:
            # For now, return a random sentiment score
            # In a real implementation, this would scrape news and analyze sentiment
            import random

            sentiment_score = random.uniform(-0.5, 0.5)
            return sentiment_score

        except Exception as e:
            logger.error(f"❌ Error getting sentiment for {symbol}: {e}")
            return 0.0

    async def get_news_score(self, symbol: str) -> float:
        """Get news score based on recent news about the stock"""
        try:
            # For now, return a random news score
            # In a real implementation, this would analyze recent news
            import random

            news_score = random.uniform(-0.3, 0.3)
            return news_score

        except Exception as e:
            logger.error(f"❌ Error getting news score for {symbol}: {e}")
            return 0.0

    def calculate_risk_score(self, opportunity: TradingOpportunity) -> float:
        """Calculate risk score based on volatility, volume, and other factors"""
        volatility = opportunity.volatility or 0.2
        volume_ratio = opportunity.volume_ratio or 1.0
        market_cap = opportunity.market_cap or 1000000000

        # Higher volatility = higher risk
        # Lower volume ratio = higher risk
        # Lower market cap = higher risk
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

    async def get_news_opportunities(self) -> List[TradingOpportunity]:
        """Find opportunities based on news analysis"""
        # This would involve scraping financial news sites
        # and analyzing sentiment for mentioned stocks
        # For now, return empty list
        return []
