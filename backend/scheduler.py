import asyncio
import json
import os
from datetime import datetime, time
import pytz
from pathlib import Path
import logging
from typing import Dict, List, Optional
from database_service import DatabaseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sydney timezone
SYDNEY_TZ = pytz.timezone('Australia/Sydney')

class MarketScannerScheduler:
    def __init__(self):
        self.running = False
        
    async def run_us_market_scanner(self):
        from main import run_market_scanner_manual  # Import here to avoid circular import
        logger.info("🕐 Running US Market Scanner (7am Sydney time)")
        try:
            # Run with default parameters for scheduled scans
            result = await run_market_scanner_manual("US")
            
            logger.info(f"✅ US Market Scanner completed. Found {result.get('results_count', 0)} results")
            
        except Exception as e:
            logger.error(f"❌ Error running US Market Scanner: {e}")
    
    async def run_au_market_scanner(self):
        from main import run_market_scanner_manual  # Import here to avoid circular import
        logger.info("🕐 Running AU Market Scanner (4:30pm Sydney time)")
        try:
            # Run with default parameters for scheduled scans
            result = await run_market_scanner_manual("AU")
            
            logger.info(f"✅ AU Market Scanner completed. Found {result.get('results_count', 0)} results")
            
        except Exception as e:
            logger.error(f"❌ Error running AU Market Scanner: {e}")
    
    async def get_latest_results(self, country: str) -> Optional[Dict]:
        """Get the latest results for a country from database"""
        try:
            results = DatabaseService.get_latest_results(country)
            
            # Add Sydney time for compatibility
            if results["last_updated"]:
                utc_time = datetime.fromisoformat(results["last_updated"].replace('Z', '+00:00'))
                sydney_time = utc_time.astimezone(SYDNEY_TZ)
                results["sydney_time"] = sydney_time.isoformat()
            else:
                results["sydney_time"] = None
            
            return results if results["ttm_squeeze"] or results["volume_spikes"] else None
            
        except Exception as e:
            logger.error(f"Error getting latest results for {country}: {e}")
            return None
    
    async def get_all_latest_results(self) -> Dict[str, Optional[Dict]]:
        """Get latest results for both countries from database"""
        return {
            "US": await self.get_latest_results("US"),
            "AU": await self.get_latest_results("AU")
        }
    
    async def schedule_scanners(self):
        """Main scheduling loop"""
        self.running = True
        logger.info("🚀 Market Scanner Scheduler started")
        
        while self.running:
            try:
                # Get current Sydney time
                sydney_now = datetime.now(SYDNEY_TZ)
                current_time = sydney_now.time()
                
                # Check if it's 7am Sydney time (US market scanner)
                if current_time.hour == 7 and current_time.minute == 0:
                    logger.info("⏰ 7am Sydney time - Running US Market Scanner")
                    await self.run_us_market_scanner()
                    # Wait 2 minutes to avoid running multiple times
                    await asyncio.sleep(120)
                
                # Check if it's 4:30pm Sydney time (AU market scanner)
                elif current_time.hour == 16 and current_time.minute == 30:
                    logger.info("⏰ 4:30pm Sydney time - Running AU Market Scanner")
                    await self.run_au_market_scanner()
                    # Wait 2 minutes to avoid running multiple times
                    await asyncio.sleep(120)
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("🛑 Market Scanner Scheduler stopped")

# Global scheduler instance
scheduler = MarketScannerScheduler()

async def start_scheduler():
    """Start the scheduler"""
    await scheduler.schedule_scanners()

if __name__ == "__main__":
    asyncio.run(start_scheduler()) 