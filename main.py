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
        logger.info(f"Files in directory: {os.listdir('.')}")
        logger.info(f"Environment variables: PORT={os.environ.get('PORT', 'Not set')}")

        # Check if config.yaml exists
        config_path = Path("config.yaml")
        if not config_path.exists():
            logger.error(f"❌ config.yaml not found at {config_path.absolute()}")
            raise FileNotFoundError(
                f"config.yaml not found at {config_path.absolute()}"
            )

        # Load configuration
        logger.info("📋 Loading configuration...")
        config = Config.from_file("config.yaml")
        logger.info("📋 Configuration loaded successfully")

        # Initialize multi-strategy trading agent
        logger.info("🤖 Initializing multi-strategy trading agent...")
        trading_agent = MultiStrategyAgent(config)
        logger.info("🤖 Multi-strategy trading agent initialized")

        # Initialize web dashboard
        logger.info("🌐 Initializing web dashboard...")
        dashboard = WebDashboard(trading_agent)
        logger.info("🌐 Web dashboard initialized")

        # Handle Railway/Render PORT environment variable
        port = int(os.environ.get("PORT", config.system.dashboard_port))
        config.system.dashboard_port = port
        logger.info(f"🎯 Using port: {port}")

        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("🛑 Received shutdown signal")
            asyncio.create_task(shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the web dashboard
        logger.info("🚀 Starting web dashboard...")
        await dashboard.start()

    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        sys.exit(1)
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("This might be due to missing dependencies")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Critical error in main: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


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
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
