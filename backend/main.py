from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv
import httpx
import logging
import yfinance as yf
import random
import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if API key is available
eodhd_api_key = os.getenv("EODHD_API_KEY")

if not eodhd_api_key:
    logger.error("EODHD_API_KEY environment variable not found!")
    logger.error("Please make sure EODHD_API_KEY is set in your system environment variables")
else:
    logger.info("EODHD_API_KEY found in environment variables")
    logger.info(f"API Key starts with: {eodhd_api_key[:5]}...")

app = FastAPI(title="Financial Data API")

# EODHD API base URL
EODHD_BASE_URL = "https://eodhd.com/api"

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://*.vercel.app",  # Allow all Vercel deployments
        "https://test-ctowuw7l8-trents-projects-d2eec580.vercel.app",  # Previous Vercel domain
        "https://test-app-alpha-opal.vercel.app"  # New Vercel domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Market hours configuration
MARKET_TIMEZONE = pytz.timezone('America/New_York')
MARKET_OPEN = datetime.strptime('09:30', '%H:%M').time()
MARKET_CLOSE = datetime.strptime('16:00', '%H:%M').time()

def is_market_open() -> bool:
    """Check if the US stock market is currently open"""
    now = datetime.now(MARKET_TIMEZONE)
    current_time = now.time()
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    
    # Check if current time is within market hours
    return MARKET_OPEN <= current_time <= MARKET_CLOSE

class CandlestickData(BaseModel):
    dates: List[str]
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: List[int]
    data_source: str = "EODHD"  # Always EODHD now

class MarketStatus(BaseModel):
    is_open: bool
    timezone: str
    current_time: str
    market_hours: dict

# List of proxies
PROXY_LIST = [
    "156.242.45.155:3129", "156.228.178.225:3129", "156.228.92.123:3129",
    "156.253.174.108:3129", "156.228.178.194:3129", "156.228.89.18:3129",
    "156.233.84.138:3129", "156.228.174.44:3129", "156.228.105.44:3129",
    "154.213.202.143:3129", "156.228.89.193:3129", "156.242.40.29:3129",
    "156.253.178.234:3129", "156.228.179.167:3129", "156.228.183.252:3129",
    "156.233.93.177:3129", "156.228.190.204:3129", "45.201.10.218:3129",
    "156.242.43.226:3129", "156.228.118.89:3129", "156.228.84.228:3129",
    "156.228.92.42:3129", "156.228.96.123:3129", "156.249.138.207:3129",
    "156.248.82.130:3129", "156.228.180.200:3129", "156.228.104.62:3129",
    "156.249.60.201:3129", "156.228.108.154:3129", "156.228.171.165:3129",
    "156.228.100.108:3129", "156.240.99.219:3129", "156.228.78.234:3129",
    "156.253.172.174:3129", "156.242.45.80:3129", "154.213.166.234:3129",
    "156.253.165.7:3129", "154.94.12.215:3129", "156.228.84.78:3129",
    "156.253.174.129:3129", "156.233.89.145:3129", "156.228.174.210:3129",
    "156.228.90.84:3129", "45.202.76.107:3129", "154.213.160.17:3129",
    "154.213.161.199:3129", "156.253.172.18:3129", "156.228.79.183:3129",
    "156.242.33.79:3129", "156.228.100.186:3129", "45.202.79.220:3129",
    "156.228.185.208:3129", "156.228.171.177:3129", "156.248.83.9:3129",
    "45.201.10.186:3129", "156.228.98.173:3129", "156.228.182.118:3129",
    "154.213.202.61:3129", "156.233.89.217:3129", "156.240.99.127:3129",
    "156.228.94.154:3129", "154.214.1.75:3129", "154.94.14.51:3129",
    "156.248.85.63:3129", "156.249.62.97:3129", "156.253.171.99:3129",
    "156.248.83.67:3129", "156.228.103.68:3129", "156.228.108.243:3129",
    "156.249.56.135:3129", "156.228.84.159:3129", "156.253.168.253:3129",
    "156.233.86.155:3129", "156.233.88.66:3129", "156.228.82.245:3129",
    "156.228.86.144:3129", "156.228.76.220:3129", "156.242.38.49:3129",
    "156.233.94.85:3129", "156.242.36.124:3129", "156.233.91.253:3129",
    "156.228.84.116:3129", "156.248.87.183:3129", "156.233.89.13:3129",
    "154.213.165.85:3129", "154.94.12.49:3129", "156.249.138.240:3129",
    "45.202.79.159:3129", "156.233.87.46:3129", "156.253.170.209:3129",
    "156.242.38.253:3129", "156.249.57.205:3129", "156.228.106.64:3129",
    "156.228.99.106:3129", "156.233.84.27:3129", "156.228.176.220:3129",
    "154.213.166.48:3129", "156.228.77.31:3129", "156.233.86.119:3129",
    "156.253.166.62:3129"
]

@app.get("/")
async def root():
    logger.info("="*80)
    logger.info("ROOT ENDPOINT HIT")
    logger.info("="*80)
    return {"message": "Financial Data API is running"}

@app.get("/api/market-status", response_model=MarketStatus)
async def get_market_status():
    """Get current market status"""
    return {
        "is_open": is_market_open(),
        "timezone": "America/New_York",
        "current_time": datetime.now(MARKET_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "market_hours": {
            "open": MARKET_OPEN.strftime("%H:%M"),
            "close": MARKET_CLOSE.strftime("%H:%M")
        }
    }

@app.get("/api/stock/{symbol}/candlestick", response_model=CandlestickData)
async def get_stock_candlestick(symbol: str, period: str = "1mo", interval: str = "1d"):
    logger.info("="*80)
    logger.info(f"CANDLESTICK DATA REQUEST FOR {symbol}")
    logger.info("="*80)
    
    try:
        # Calculate date range
        end_date = datetime.now(pytz.UTC)
        if period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "6m":
            start_date = end_date - timedelta(days=180)
        elif period == "1m":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)  # Default to 1 month
        
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Format symbol for EODHD API
        formatted_symbol = f"{symbol.upper()}.US"  # Always use .US for US stocks
        url = f"{EODHD_BASE_URL}/eod/{formatted_symbol}"
        
        params = {
            'api_token': eodhd_api_key,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'fmt': 'json',
            'period': 'd',  # daily data
            'order': 'a'    # ascending dates
        }
        
        logger.info(f"Making request to EODHD API: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 404:
                logger.error("404 Not Found from EODHD API")
                raise HTTPException(
                    status_code=404,
                    detail=f"Symbol {symbol} not found in EODHD API"
                )
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"Got {len(data) if data else 0} data points")
            
            if not data:
                logger.error("No data returned from EODHD API")
                raise HTTPException(
                    status_code=404,
                    detail=f"No historical data available for {symbol}"
                )
            
            # Convert EODHD data to our format
            dates = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            
            for item in data:
                dates.append(item['date'])
                opens.append(float(item['open']))
                highs.append(float(item['high']))
                lows.append(float(item['low']))
                closes.append(float(item['close']))
                volumes.append(int(item['volume']))
            
            logger.info(f"First date: {dates[0]}, Last date: {dates[-1]}")
            logger.info(f"First close: ${closes[0]:.2f}, Last close: ${closes[-1]:.2f}")
            
            return CandlestickData(
                dates=dates,
                open=opens,
                high=highs,
                low=lows,
                close=closes,
                volume=volumes
            )

    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching candlestick data for {symbol}: {str(e)}"
        )

@app.get("/api/test-yfinance")
async def test_yfinance():
    """Test endpoint to check if yfinance is working with a random proxy"""
    proxy = random.choice(PROXY_LIST)
    
    logger.info(f"Testing yfinance with proxy: {proxy}")
    
    try:
        # Set proxy as environment variable for yfinance to use
        os.environ['HTTP_PROXY'] = f"http://{proxy}"
        os.environ['HTTPS_PROXY'] = f"http://{proxy}"
        
        # Try to get some basic data for Apple
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        
        # Clear proxy environment variables
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        
        logger.info(f"Successfully got yfinance data using proxy {proxy}")
        logger.info(f"Current price: ${info.get('currentPrice', 'N/A')}")
        logger.info(f"Company name: {info.get('longName', 'N/A')}")
        
        return {
            "status": "success",
            "message": "Successfully accessed yfinance",
            "proxy_used": proxy,
            "data": {
                "symbol": "AAPL",
                "current_price": info.get('currentPrice', 'N/A'),
                "company_name": info.get('longName', 'N/A')
            }
        }
    except Exception as e:
        # Clear proxy environment variables in case of error
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        
        logger.error(f"Error accessing yfinance with proxy {proxy}: {str(e)}")
        return {
            "status": "error",
            "message": f"Could not access yfinance: {str(e)}",
            "proxy_used": proxy
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 