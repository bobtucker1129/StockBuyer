#!/usr/bin/env python3
"""
Stock Market Trading Agent - Main Entry Point
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config import Config
from src.multi_strategy_agent import MultiStrategyAgent
from src.web_dashboard import WebDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trading_agent.log"),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    try:
        # Load configuration
        config = Config.from_file("config.yaml")
        logger.info("📋 Configuration loaded")

        # Initialize multi-strategy trading agent
        trading_agent = MultiStrategyAgent(config)
        logger.info("🤖 Multi-strategy trading agent initialized")

        # Initialize web dashboard
        dashboard = WebDashboard(trading_agent)
        logger.info("🌐 Web dashboard initialized")
        logger.info(
            f"Dashboard config - host: {config.system.dashboard_host}, port: {config.system.dashboard_port}"
        )

        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("🛑 Received shutdown signal")
            asyncio.create_task(shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the trading agent and dashboard
        logger.info("🚀 Starting trading agent and dashboard...")
        try:
            # For Railway deployment, we need to handle the PORT environment variable
            import os

            port = int(os.environ.get("PORT", config.system.dashboard_port))
            config.system.dashboard_port = port

            await asyncio.gather(
                trading_agent.run(),
                dashboard.start(),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"❌ Error in asyncio.gather: {e}")
            raise

    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
        raise


async def shutdown():
    """Graceful shutdown"""
    logger.info("🛑 Starting graceful shutdown")

    # Stop the trading agent
    if "trading_agent" in locals():
        await trading_agent.shutdown()

    # Stop the dashboard
    if "dashboard" in locals():
        await dashboard.shutdown()

    logger.info("✅ Trading agent shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
