#!/usr/bin/env python3
"""
Stock Market Trading Agent - Main Entry Point
"""

import asyncio
import logging
import signal
import sys
import os
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
    ],
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    try:
        logger.info("🚀 Starting Stock Market Trading Agent...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")

        # Load configuration
        config = Config.from_file("config.yaml")
        logger.info("📋 Configuration loaded successfully")

        # Initialize multi-strategy trading agent
        trading_agent = MultiStrategyAgent(config)
        logger.info("🤖 Multi-strategy trading agent initialized")

        # Initialize web dashboard
        dashboard = WebDashboard(trading_agent)
        logger.info("🌐 Web dashboard initialized")

        # Handle Railway PORT environment variable
        port = int(os.environ.get("PORT", config.system.dashboard_port))
        config.system.dashboard_port = port
        logger.info(f"🎯 Using port: {port}")

        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("🛑 Received shutdown signal")
            asyncio.create_task(shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the trading agent and dashboard
        logger.info("🚀 Starting trading agent and dashboard...")

        # For Railway, start the dashboard first to ensure the web server is running
        await dashboard.start()

    except Exception as e:
        logger.error(f"❌ Critical error in main: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


async def shutdown():
    """Graceful shutdown"""
    logger.info("🛑 Starting graceful shutdown")
    sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
