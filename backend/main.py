from fastapi import FastAPI, HTTPException, Request
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
proxy_username = os.getenv("PROXY_USERNAME")
proxy_password = os.getenv("PROXY_PASSWORD")
proxy_host = os.getenv("PROXY_HOST")

if not eodhd_api_key:
    logger.error("EODHD_API_KEY environment variable not found!")
    logger.error("Please make sure EODHD_API_KEY is set in your system environment variables")
else:
    logger.info("EODHD_API_KEY found in environment variables")
    logger.info(f"API Key starts with: {eodhd_api_key[:5]}...")

if not all([proxy_username, proxy_password, proxy_host]):
    logger.error("Proxy credentials not found in environment variables!")
    logger.error("Please make sure PROXY_USERNAME, PROXY_PASSWORD, and PROXY_HOST are set")
else:
    logger.info("Proxy credentials found in environment variables")
    PROXY_URL = f"http://{proxy_username}:{proxy_password}@{proxy_host}"
    logger.info(f"Proxy host: {proxy_host}")

app = FastAPI(title="Financial Data API")

# Custom middleware to log CORS requests
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info("="*80)
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Origin: {request.headers.get('origin', 'No origin')}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info("="*80)
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response headers: {dict(response.headers)}")
    logger.info("="*80)
    return response

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

# ProxyScrape configuration
PROXY_USERNAME = "4pice9axorxc0iy"
PROXY_PASSWORD = "znhsvjczqvcgyhh"
PROXY_HOST = "rp.scrapegw.com:6060"
PROXY_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}"

@app.get("/")
async def root(request: Request):
    logger.info("="*80)
    logger.info("ROOT ENDPOINT HIT")
    logger.info(f"Request headers: {dict(request.headers)}")
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
    """Test endpoint to check if yfinance is working with authenticated proxy"""
    logger.info("="*80)
    logger.info("TESTING YFINANCE PROXY CONNECTION")
    logger.info(f"Using ProxyScrape proxy: {PROXY_HOST}")
    
    try:
        # Set proxy as environment variable for yfinance to use
        os.environ['HTTP_PROXY'] = PROXY_URL
        os.environ['HTTPS_PROXY'] = PROXY_URL
        
        logger.info("Testing proxy with direct HTTP request...")
        async with httpx.AsyncClient(proxies=PROXY_URL) as client:
            try:
                test_response = await client.get("https://www.google.com", timeout=10.0)
                logger.info(f"Proxy test request status: {test_response.status_code}")
            except Exception as e:
                logger.error(f"Proxy test request failed: {str(e)}")
        
        # Now try yfinance
        logger.info("Attempting yfinance request...")
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        
        # Clear proxy environment variables
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        
        logger.info("Successfully got yfinance data using ProxyScrape proxy")
        logger.info(f"Current price: ${info.get('currentPrice', 'N/A')}")
        logger.info(f"Company name: {info.get('longName', 'N/A')}")
        
        return {
            "status": "success",
            "message": "Successfully accessed yfinance",
            "proxy_used": PROXY_HOST,
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
        
        logger.error(f"Error accessing yfinance: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return {
            "status": "error",
            "message": f"Could not access yfinance: {str(e)}",
            "proxy_used": PROXY_HOST,
            "error_type": type(e).__name__,
            "error_details": str(e)
        }
    finally:
        logger.info("="*80)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 