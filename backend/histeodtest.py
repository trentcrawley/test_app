import os
import pandas as pd
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv
import logging
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
EODHD_API_KEY = os.getenv("EODHD_API_KEY")

if not EODHD_API_KEY:
    raise ValueError("EODHD_API_KEY not found in environment variables")

# ASX stocks to test
ASX_STOCKS = [
    "CBA.AU",  # Commonwealth Bank
    "BHP.AU",  # BHP Group
    "CSL.AU",  # CSL Limited
    "NAB.AU",  # National Australia Bank
    "WBC.AU",  # Westpac Banking
    "ANZ.AU",  # ANZ Banking
    "WES.AU",  # Wesfarmers
    "WOW.AU",  # Woolworths
    "WPL.AU",  # Woodside Energy
    "RIO.AU"   # Rio Tinto
]

async def fetch_stock_data(symbol: str, client: httpx.AsyncClient) -> pd.DataFrame:
    """Fetch 5 years of daily data for an ASX stock"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)  # 5 years
    
    url = f"https://eodhd.com/api/eod/{symbol}"
    
    params = {
        'api_token': EODHD_API_KEY,
        'from': start_date.strftime('%Y-%m-%d'),
        'to': end_date.strftime('%Y-%m-%d'),
        'fmt': 'json',
        'period': 'd'  # daily data
    }
    
    logger.info(f"Fetching data for {symbol}")
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Add symbol column
        df['symbol'] = symbol
        
        logger.info(f"Successfully fetched {len(df)} days of data for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {str(e)}")
        return pd.DataFrame()

async def main():
    # Create output directory if it doesn't exist
    output_dir = Path("asx_data")
    output_dir.mkdir(exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        # Fetch data for all stocks concurrently
        tasks = [fetch_stock_data(symbol, client) for symbol in ASX_STOCKS]
        dfs = await asyncio.gather(*tasks)
        
        # Filter out empty DataFrames
        dfs = [df for df in dfs if not df.empty]
        
        if not dfs:
            logger.error("No data was fetched for any stocks")
            return
        
        # Combine all data into one DataFrame
        combined_df = pd.concat(dfs, axis=0)
        
        # Save individual stock data
        for symbol in ASX_STOCKS:
            stock_df = combined_df[combined_df['symbol'] == symbol]
            if not stock_df.empty:
                output_file = output_dir / f"{symbol.replace('.AU', '')}_daily.csv"
                stock_df.to_csv(output_file)
                logger.info(f"Saved {symbol} data to {output_file}")
        
        # Save combined data
        combined_file = output_dir / "all_asx_stocks.csv"
        combined_df.to_csv(combined_file)
        logger.info(f"Saved combined data to {combined_file}")
        
        # Print some basic statistics
        logger.info("\nData Summary:")
        for symbol in ASX_STOCKS:
            stock_df = combined_df[combined_df['symbol'] == symbol]
            if not stock_df.empty:
                logger.info(f"\n{symbol}:")
                logger.info(f"Date range: {stock_df.index.min()} to {stock_df.index.max()}")
                logger.info(f"Number of trading days: {len(stock_df)}")
                logger.info(f"Latest close: ${stock_df['close'].iloc[-1]:.2f}")
                logger.info(f"52-week high: ${stock_df['high'].max():.2f}")
                logger.info(f"52-week low: ${stock_df['low'].min():.2f}")

if __name__ == "__main__":
    asyncio.run(main())
