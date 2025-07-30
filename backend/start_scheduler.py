#!/usr/bin/env python3
"""
Market Scanner Scheduler Startup Script
Runs the automated market scanner at scheduled times.
"""

import asyncio
import logging
from scheduler import start_scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Starting Market Scanner Scheduler...")
    logger.info("📅 Schedule:")
    logger.info("   - US Market: 7:00 AM Sydney time")
    logger.info("   - AU Market: 4:30 PM Sydney time")
    logger.info("💾 Results will be stored in ./results/ directory")
    logger.info("🌐 API endpoints available at:")
    logger.info("   - GET /api/market-scanner/results - All results")
    logger.info("   - GET /api/market-scanner/results/{exchange} - Specific exchange")
    logger.info("   - POST /api/market-scanner/run/{exchange} - Manual trigger")
    logger.info("=" * 60)
    
    try:
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler stopped by user")
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}")
        raise 