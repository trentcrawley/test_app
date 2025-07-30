from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import pytz
import os
from dotenv import load_dotenv
import httpx
import logging
import random
import requests
from requests.exceptions import RequestException
from requests.auth import HTTPProxyAuth
import asyncio
from technical_calcs import calculate_ttm_squeeze, calculate_volume_spike, analyze_stock_technicals, calculate_ttm_squeeze_with_ema_filter
from concurrent.futures import ThreadPoolExecutor
import time
import statistics
from scheduler import scheduler
from database import create_tables
from database_service import DatabaseService

# Initialize database tables
create_tables()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Log to stdout
        logging.FileHandler('app.log')  # Log to file
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global variable to track running scans
running_scans = set()

# Check if API key is available
eodhd_api_key = os.getenv("EODHD_API_KEY", "").strip()
proxy_username = os.getenv("PROXY_USERNAME")
proxy_password = os.getenv("PROXY_PASSWORD")
proxy_host = os.getenv("PROXY_HOST")

# Log startup configuration
logger.info("="*80)
logger.info("APPLICATION STARTUP")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables loaded: {bool(proxy_username and proxy_password and proxy_host)}")
logger.info(f"Proxy host: {proxy_host}")
logger.info("="*80)

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

# EODHD API base URLs
EODHD_BASE_URL = "https://eodhd.com/api"

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8080",
        "https://*.vercel.app",
        "https://test-ctowuw7l8-trents-projects-d2eec580.vercel.app",
        "https://test-app-alpha-opal.vercel.app",
        "https://test-app-j26v.vercel.app",
        "https://test-app-j26v-git-main-trents-projects-d2eec580.vercel.app",
        "https://test-app-j26v-6gjk93oiu-trents-projects-d2eec580.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
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
    data_source: str = "EODHD"

class StockInfo(BaseModel):
    symbol: str
    name: str
    exchange: str
    currency: str
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    eps: Optional[float]
    dividend_yield: Optional[float]
    beta: Optional[float]
    fifty_two_week_high: Optional[float]
    fifty_two_week_low: Optional[float]

class MarketStatus(BaseModel):
    is_open: bool
    timezone: str
    current_time: str
    market_hours: dict

class NewsItem(BaseModel):
    date: str
    title: str
    link: str
    text: str
    source: str
    tags: List[str]
    symbols: List[str]

class StockSymbol(BaseModel):
    code: str
    name: str
    exchange: str
    currency: str
    type: str

class StockAnalysisResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    has_latest_data: bool
    latest_date: Optional[str]
    data_points: int
    last_close: Optional[float]
    last_volume: Optional[int]

class HistoricalBatchRequest(BaseModel):
    stock_codes: List[str]
    exchange: str = "US"

class StockWithMarketCap(BaseModel):
    symbol: str
    name: str
    exchange: str
    currency: str
    type: str
    market_cap: Optional[float]

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
async def get_stock_candlestick(symbol: str, exchange: str = "US"):
    """Get 2 years of daily OHLC data for a stock"""
    logger.info("="*80)
    logger.info(f"CANDLESTICK DATA REQUEST FOR {symbol}.{exchange}")
    logger.info("="*80)
    
    try:
        # Calculate date range (2 years)
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=730)  # 2 years
        
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Format symbol for EODHD API
        formatted_symbol = f"{symbol.upper()}.{exchange.upper()}"
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

@app.get("/api/stock/{symbol}/info", response_model=StockInfo)
async def get_stock_info(symbol: str, exchange: str = "US"):
    """Get fundamental information for a stock"""
    logger.info("="*80)
    logger.info(f"STOCK INFO REQUEST FOR {symbol}.{exchange}")
    logger.info("="*80)
    
    try:
        formatted_symbol = f"{symbol.upper()}.{exchange.upper()}"
        url = f"{EODHD_BASE_URL}/fundamentals/{formatted_symbol}"
        
        params = {
            'api_token': eodhd_api_key,
            'fmt': 'json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Symbol {symbol} not found in EODHD API"
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant information
            general = data.get('General', {})
            highlights = data.get('Highlights', {})
            technicals = data.get('Technicals', {})
            
            return StockInfo(
                symbol=symbol,
                name=general.get('Name', ''),
                exchange=general.get('Exchange', ''),
                currency=general.get('Currency', ''),
                sector=general.get('Sector', None),
                industry=general.get('Industry', None),
                market_cap=highlights.get('MarketCapitalization', None),
                pe_ratio=highlights.get('PERatio', None),
                eps=highlights.get('EarningsShare', None),
                dividend_yield=highlights.get('DividendYield', None),
                beta=technicals.get('Beta', None),
                fifty_two_week_high=technicals.get('52WeekHigh', None),
                fifty_two_week_low=technicals.get('52WeekLow', None)
            )
            
    except Exception as e:
        logger.error(f"Error fetching stock info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stock info for {symbol}: {str(e)}"
        )

@app.get("/api/stock/{symbol}/news", response_model=List[NewsItem])
async def get_stock_news(symbol: str, exchange: str = "US"):
    """Get news for a stock from the last 5 days"""
    logger.info("="*80)
    logger.info(f"NEWS REQUEST FOR {symbol}.{exchange}")
    logger.info("="*80)
    
    try:
        # Calculate date range (5 days)
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=5)
        
        formatted_symbol = f"{symbol.upper()}.{exchange.upper()}"
        url = f"{EODHD_BASE_URL}/news"
        
        params = {
            'api_token': eodhd_api_key,
            's': formatted_symbol,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'limit': 10,
            'offset': 0,
            'fmt': 'json'
        }
        
        logger.info(f"Making request to EODHD API: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"News not found for {symbol}.{exchange}"
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Transform the news data to our format
            news_items = []
            for item in data:
                news_items.append(NewsItem(
                    date=item.get('date', ''),
                    title=item.get('title', ''),
                    link=item.get('link', ''),
                    text=item.get('text', ''),
                    source=item.get('source', ''),
                    tags=item.get('tags', []),
                    symbols=item.get('symbols', [])
                ))
            
            return news_items
            
    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching news for {symbol}.{exchange}: {str(e)}"
        )

@app.get("/api/stocks/asx", response_model=List[StockSymbol])
async def get_asx_stocks():
    """Get all ASX stocks from EODHD API"""
    logger.info("="*80)
    logger.info("ASX STOCKS REQUEST")
    logger.info("="*80)
    
    try:
        # EODHD exchange-symbol-list endpoint for ASX
        url = f"{EODHD_BASE_URL}/exchange-symbol-list/AU"
        
        params = {
            'api_token': eodhd_api_key,
            'fmt': 'json'
        }
        
        logger.info(f"Making request to EODHD API: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 404:
                logger.error("404 Not Found from EODHD API")
                raise HTTPException(
                    status_code=404,
                    detail="ASX exchange data not found in EODHD API"
                )
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"Got {len(data) if data else 0} ASX stocks")
            
            if not data:
                logger.error("No ASX stocks returned from EODHD API")
                raise HTTPException(
                    status_code=404,
                    detail="No ASX stocks available"
                )
            
            # Convert EODHD data to our format
            stocks = []
            for item in data:
                # Only include common stocks (not ETFs, bonds, etc.)
                if item.get('Type') == 'Common Stock':
                    stocks.append(StockSymbol(
                        code=item.get('Code', ''),
                        name=item.get('Name', ''),
                        exchange=item.get('Exchange', 'ASX'),
                        currency=item.get('Currency', 'AUD'),
                        type=item.get('Type', 'Common Stock')
                    ))
            
            logger.info(f"Returning {len(stocks)} ASX common stocks")
            return stocks
            
    except Exception as e:
        logger.error(f"Error fetching ASX stocks: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching ASX stocks: {str(e)} (Type: {type(e).__name__})"
        )

@app.get("/api/stocks/us", response_model=List[StockSymbol])
async def get_us_stocks():
    """Get all US common stocks from EODHD API"""
    logger.info("="*80)
    logger.info("US STOCKS REQUEST")
    logger.info("="*80)
    
    try:
        # EODHD exchange-symbol-list endpoint for US
        url = f"{EODHD_BASE_URL}/exchange-symbol-list/US"
        
        params = {
            'api_token': eodhd_api_key,
            'fmt': 'json'
        }
        
        logger.info(f"Making request to EODHD API: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 404:
                logger.error("404 Not Found from EODHD API")
                raise HTTPException(
                    status_code=404,
                    detail="US exchange data not found in EODHD API"
                )
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"Got {len(data) if data else 0} US stocks")
            
            if not data:
                logger.error("No US stocks returned from EODHD API")
                raise HTTPException(
                    status_code=404,
                    detail="No US stocks available"
                )
            
            # Convert EODHD data to our format
            stocks = []
            major_exchanges = {'NASDAQ', 'NYSE', 'AMEX', 'ARCA', 'BATS', 'IEX'}
            
            for item in data:
                # Only include common stocks on major exchanges (not ETFs, bonds, OTC, PINK, etc.)
                if (item.get('Type') == 'Common Stock' and 
                    item.get('Exchange') in major_exchanges):
                    stocks.append(StockSymbol(
                        code=item.get('Code', ''),
                        name=item.get('Name', ''),
                        exchange=item.get('Exchange', 'US'),
                        currency=item.get('Currency', 'USD'),
                        type=item.get('Type', 'Common Stock')
                    ))
            
            logger.info(f"Returning {len(stocks)} US common stocks on major exchanges")
            print(f"✅ US: {len(stocks)}/{len(data)} stocks (major exchanges)")
            return stocks
            
    except Exception as e:
        logger.error(f"Error fetching US stocks: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching US stocks: {str(e)} (Type: {type(e).__name__})"
        )

@app.post("/api/stocks/historical-batch", response_model=List[StockAnalysisResult])
async def get_historical_data_batch(request: HistoricalBatchRequest):
    """Get historical data for multiple stocks and filter for those with latest trading day"""
    logger.info("="*80)
    logger.info(f"HISTORICAL BATCH REQUEST FOR {len(request.stock_codes)} STOCKS ON {request.exchange}")
    logger.info("="*80)
    
    try:
        # Calculate date range (2 years)
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=730)  # 2 years
        
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Process stocks concurrently in large batches
        batch_size = 1000
        all_results = []
        
        for i in range(0, len(request.stock_codes), batch_size):
            batch = request.stock_codes[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} stocks concurrently")
            
            # Fetch data concurrently
            batch_data = await process_stock_batch_concurrent(
                batch,
                request.exchange,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                max_concurrent=200  # High concurrency for speed
            )
            
            # Apply TTM Squeeze analysis concurrently
            squeeze_results = await analyze_ttm_squeeze_concurrent(batch_data, min_squeeze_days=1)
            
            # Add exchange info to results
            for result in squeeze_results:
                result["exchange"] = request.exchange
                result["name"] = ""
                all_results.append(result)
                # Reduced logging - only log final counts
            
            # Minimal delay between batches
            if i + batch_size < len(request.stock_codes):
                logger.info("Waiting 0.05 seconds before next batch...")
                await asyncio.sleep(0.05)
        
        # Find the maximum date across all stocks
        valid_results = [r for r in all_results if r.latest_date is not None]
        if not valid_results:
            logger.warning("No valid data found for any stocks")
            return []
        
        max_date = max(r.latest_date for r in valid_results)
        logger.info(f"Maximum date across all stocks: {max_date}")
        
        # Filter for stocks with the maximum date
        stocks_with_latest_data = [r for r in valid_results if r.latest_date == max_date]
        
        logger.info(f"Total stocks processed: {len(all_results)}")
        logger.info(f"Stocks with latest data ({max_date}): {len(stocks_with_latest_data)}")
        
        return stocks_with_latest_data
        
    except Exception as e:
        logger.error(f"Error in historical batch processing: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing historical data: {str(e)} (Type: {type(e).__name__})"
        )

@app.post("/api/stocks/ttm-squeeze", response_model=List[Dict])
async def analyze_ttm_squeeze(request: HistoricalBatchRequest):
    """Apply TTM Squeeze analysis to a list of stock codes"""
    logger.info("="*80)
    logger.info(f"TTM SQUEEZE ANALYSIS FOR {len(request.stock_codes)} STOCKS ON {request.exchange}")
    logger.info("="*80)
    
    try:
        # Calculate date range (2 years)
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=730)  # 2 years
        
        # Process stocks concurrently in large batches
        batch_size = 1000
        all_results = []
        
        for i in range(0, len(request.stock_codes), batch_size):
            batch = request.stock_codes[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} stocks concurrently")
            
            # Fetch data concurrently
            batch_data = await process_stock_batch_concurrent(
                batch,
                request.exchange,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                max_concurrent=200  # High concurrency for speed
            )
            
            # Apply TTM Squeeze analysis concurrently
            squeeze_results = await analyze_ttm_squeeze_concurrent(batch_data, min_squeeze_days=1)
            
            # Add exchange info to results
            for result in squeeze_results:
                result["exchange"] = request.exchange
                result["name"] = ""
                all_results.append(result)
                # Reduced logging - only log final counts
            
            # Minimal delay between batches
            if i + batch_size < len(request.stock_codes):
                logger.info("Waiting 0.05 seconds before next batch...")
                await asyncio.sleep(0.05)
        
        logger.info(f"TTM Squeeze analysis complete. Found {len(all_results)} stocks meeting criteria")
        return all_results
        
    except Exception as e:
        logger.error(f"Error in TTM Squeeze analysis: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in TTM Squeeze analysis: {str(e)} (Type: {type(e).__name__})"
        )



@app.get("/api/test-yfinance")
async def test_yfinance():
    """Test endpoint to check if yfinance works with proxy"""
    logger.info("="*80)
    logger.info("TESTING YFINANCE WITH PROXY")
    logger.info(f"Using ProxyScrape proxy: {PROXY_HOST}")
    
    try:
        # Set proxy as environment variable
        os.environ['HTTP_PROXY'] = PROXY_URL
        os.environ['HTTPS_PROXY'] = PROXY_URL
        logger.info("Set proxy environment variables")
        
        import yfinance as yf
        import requests
        from requests.auth import HTTPProxyAuth
        
        # Create a session with proxy settings
        session = requests.Session()
        session.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        session.verify = False  # Disable SSL verification for proxy
        
        # Configure yfinance to use our session
        import yfinance.utils
        yfinance.utils.requests = session
        
        logger.info("Successfully configured yfinance with proxy")
        
        try:
            # First verify our IP
            async with httpx.AsyncClient(
                proxies=PROXY_URL,
                verify=False,
                timeout=30.0
            ) as client:
                ip_response = await client.get("http://httpbin.org/ip")
                proxy_ip = ip_response.json()["origin"]
                logger.info(f"Proxy IP: {proxy_ip}")
            
            # Try to get AAPL data
            logger.info("Attempting to get AAPL data...")
            ticker = yf.Ticker("AAPL")
            logger.info("Created Ticker object")
            
            try:
                info = ticker.info
                logger.info(f"Got ticker info: {info.keys()}")
                current_price = info.get('regularMarketPrice')
                company_name = info.get('longName')
                logger.info(f"Current price: {current_price}, Company name: {company_name}")
                
                return {
                    "status": "success",
                    "message": "Successfully got data from yfinance",
                    "proxy_used": PROXY_HOST,
                    "proxy_ip": proxy_ip,
                    "data": {
                        "symbol": "AAPL",
                        "current_price": current_price,
                        "company_name": company_name
                    }
                }
            except Exception as e:
                logger.error(f"Error getting ticker info: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
                return {
                    "status": "error",
                    "message": f"Error getting ticker info: {str(e)}",
                    "proxy_used": PROXY_HOST,
                    "proxy_ip": proxy_ip,
                    "error_type": type(e).__name__,
                    "error_details": str(e.__dict__) if hasattr(e, '__dict__') else 'No details available'
                }
                
        except Exception as e:
            logger.error(f"Error creating Ticker object: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
            return {
                "status": "error",
                "message": f"Error creating Ticker object: {str(e)}",
                "proxy_used": PROXY_HOST,
                "error_type": type(e).__name__,
                "error_details": str(e.__dict__) if hasattr(e, '__dict__') else 'No details available'
            }
            
    except Exception as e:
        logger.error(f"Error importing yfinance: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
        return {
            "status": "error",
            "message": f"Error importing yfinance: {str(e)}",
            "proxy_used": PROXY_HOST,
            "error_type": type(e).__name__,
            "error_details": str(e.__dict__) if hasattr(e, '__dict__') else 'No details available'
        }
    finally:
        # Clear proxy
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        logger.info("Cleared proxy environment variables")
        logger.info("="*80)

@app.get("/api/test-proxy-yahoo")
async def test_proxy_yahoo():
    """Test endpoint to check if proxy works with Yahoo Finance"""
    logger.info("="*80)
    logger.info("TESTING PROXY WITH YAHOO FINANCE")
    logger.info(f"Using ProxyScrape proxy: {PROXY_HOST}")
    
    try:
        # Set proxy as environment variable
        os.environ['HTTP_PROXY'] = PROXY_URL
        os.environ['HTTPS_PROXY'] = PROXY_URL
        
        async with httpx.AsyncClient(
            proxies=PROXY_URL,
            verify=False,
            timeout=30.0
        ) as client:
            try:
                # First get our IP
                ip_response = await client.get("http://httpbin.org/ip")
                proxy_ip = ip_response.json()["origin"]
                logger.info(f"Proxy IP: {proxy_ip}")
                
                # Try Yahoo Finance's newer API endpoint
                yahoo_url = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?interval=1d&range=1d"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Origin": "https://finance.yahoo.com",
                    "Referer": "https://finance.yahoo.com/quote/AAPL",
                }
                
                logger.info(f"Making request to Yahoo Finance with headers: {headers}")
                yahoo_response = await client.get(yahoo_url, headers=headers)
                
                # Get all response details
                response_details = {
                    "status": yahoo_response.status_code,
                    "headers": dict(yahoo_response.headers),
                    "body": yahoo_response.text[:1000] if yahoo_response.text else None,
                    "request_headers": dict(yahoo_response.request.headers),
                    "proxy_ip": proxy_ip
                }
                
                logger.info(f"Yahoo Finance response details: {response_details}")
                
                if yahoo_response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"Yahoo Finance returned status {yahoo_response.status_code}",
                        "proxy_used": PROXY_HOST,
                        "proxy_ip": proxy_ip,
                        "yahoo_response": response_details
                    }
                
                return {
                    "status": "success",
                    "message": "Successfully accessed Yahoo Finance through proxy",
                    "proxy_used": PROXY_HOST,
                    "proxy_ip": proxy_ip,
                    "yahoo_response": response_details
                }
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP Error in Yahoo Finance test: {str(e)}")
                response_details = {
                    "status": e.response.status_code if e.response else None,
                    "headers": dict(e.response.headers) if e.response else None,
                    "body": e.response.text[:1000] if e.response and e.response.text else None,
                    "request_headers": dict(e.response.request.headers) if e.response else None,
                    "proxy_ip": proxy_ip if 'proxy_ip' in locals() else None,
                    "error": str(e)
                }
                return {
                    "status": "error",
                    "message": f"Yahoo Finance HTTP error: {str(e)}",
                    "proxy_used": PROXY_HOST,
                    "proxy_ip": proxy_ip if 'proxy_ip' in locals() else None,
                    "yahoo_response": response_details
                }
            except Exception as e:
                logger.error(f"Error in Yahoo Finance test: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Yahoo Finance test failed: {str(e)}",
                    "proxy_used": PROXY_HOST,
                    "proxy_ip": proxy_ip if 'proxy_ip' in locals() else None,
                    "yahoo_response": {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "proxy_ip": proxy_ip if 'proxy_ip' in locals() else None
                    }
                }
                
    except Exception as e:
        logger.error(f"Error in proxy test: {str(e)}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}",
            "proxy_used": PROXY_HOST,
            "yahoo_response": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        }
    finally:
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        logger.info("="*80)

@app.get("/api/test-proxy-simple")
async def test_proxy_simple():
    """Simple test endpoint that just tries to access a website through the proxy"""
    logger.info("="*80)
    logger.info("SIMPLE PROXY TEST")
    
    test_urls = [
        "http://httpbin.org/ip",  # Returns your IP address
        "http://httpbin.org/headers",  # Returns request headers
        "https://www.google.com"  # Basic website
    ]
    
    results = []
    
    try:
        # Set proxy
        os.environ['HTTP_PROXY'] = PROXY_URL
        os.environ['HTTPS_PROXY'] = PROXY_URL
        logger.info("Set proxy environment variables")
        
        async with httpx.AsyncClient(
            proxies=PROXY_URL,
            verify=False,
            timeout=30.0
        ) as client:
            for url in test_urls:
                try:
                    logger.info(f"Testing {url}...")
                    response = await client.get(url)
                    logger.info(f"Status for {url}: {response.status_code}")
                    logger.info(f"Headers: {dict(response.headers)}")
                    
                    # Try to get response content
                    try:
                        content = response.json() if 'json' in response.headers.get('content-type', '') else response.text[:200]
                        logger.info(f"Response content: {content}")
                    except:
                        logger.info("Could not decode response content")
                    
                    results.append({
                        "url": url,
                        "status": response.status_code,
                        "success": True,
                        "headers": dict(response.headers)
                    })
                except Exception as e:
                    logger.error(f"Error with {url}: {str(e)}")
                    results.append({
                        "url": url,
                        "error": str(e),
                        "success": False
                    })
        
        return {
            "status": "success",
            "proxy_used": proxy_host,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in proxy test: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "proxy_used": proxy_host
        }
    finally:
        # Clear proxy
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        logger.info("Cleared proxy environment variables")
        logger.info("="*80)

@app.get("/api/test-proxy-ip")
async def test_proxy_ip():
    """Test endpoint to verify if proxy is actually being used by checking IP"""
    logger.info("="*80)
    logger.info("TESTING PROXY IP")
    
    try:
        # First get IP without proxy
        logger.info("Getting IP without proxy...")
        async with httpx.AsyncClient() as client:
            direct_response = await client.get("http://httpbin.org/ip")
            direct_ip = direct_response.json()["origin"]
            logger.info(f"Direct IP (without proxy): {direct_ip}")
        
        # Now get IP with proxy
        logger.info("Getting IP with proxy...")
        os.environ['HTTP_PROXY'] = PROXY_URL
        os.environ['HTTPS_PROXY'] = PROXY_URL
        
        async with httpx.AsyncClient(
            proxies=PROXY_URL,
            verify=False,
            timeout=30.0
        ) as client:
            # Test with httpbin
            proxy_response = await client.get("http://httpbin.org/ip")
            proxy_ip = proxy_response.json()["origin"]
            logger.info(f"Proxy IP (httpbin): {proxy_ip}")
            
            # Test with Yahoo Finance
            try:
                logger.info("Testing with Yahoo Finance...")
                yahoo_response = await client.get(
                    "https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=price",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                )
                logger.info(f"Yahoo Finance response status: {yahoo_response.status_code}")
                logger.info(f"Yahoo Finance headers: {dict(yahoo_response.headers)}")
            except Exception as e:
                logger.error(f"Yahoo Finance test failed: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"Response status: {e.response.status_code if e.response else 'No response'}")
                    logger.error(f"Response headers: {dict(e.response.headers) if e.response else 'No headers'}")
            
            # Also get headers to see what the proxy is sending
            headers_response = await client.get("http://httpbin.org/headers")
            logger.info(f"Proxy headers: {headers_response.json()['headers']}")
        
        # Clear proxy
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        
        return {
            "status": "success",
            "direct_ip": direct_ip,
            "proxy_ip": proxy_ip,
            "proxy_used": proxy_host,
            "ips_match": direct_ip == proxy_ip,  # If True, proxy isn't working
            "proxy_headers": headers_response.json()['headers'] if 'headers_response' in locals() else None
        }
        
    except Exception as e:
        logger.error(f"Error testing proxy IP: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "proxy_used": proxy_host
        }
    finally:
        # Clear proxy
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        logger.info("="*80)

@app.post("/api/stocks/ema-stacking", response_model=List[Dict])
async def analyze_ema_stacking(request: HistoricalBatchRequest):
    """Check EMA stacking (9EMA > 50EMA > 200EMA) for a list of stock codes"""
    logger.info("="*80)
    logger.info(f"EMA STACKING ANALYSIS FOR {len(request.stock_codes)} STOCKS ON {request.exchange}")
    logger.info("="*80)
    
    try:
        # Calculate date range (2 years)
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=730)  # 2 years
        
        # Process stocks concurrently in large batches
        batch_size = 500
        all_results = []
        
        for i in range(0, len(request.stock_codes), batch_size):
            batch = request.stock_codes[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} stocks concurrently")
            
            # Fetch data concurrently
            batch_data = await process_stock_batch_concurrent(
                batch,
                request.exchange,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                max_concurrent=50
            )
            
            # Analyze EMA stacking concurrently
            def analyze_ema_single_stock(stock_data: Dict) -> Optional[Dict]:
                try:
                    if not stock_data['success'] or not stock_data['data']:
                        return None
                    
                    symbol = stock_data['symbol']
                    data = stock_data['data']
                    
                    # Import the EMA function
                    from technical_calcs import calculate_emas_and_check_stacking
                    ema_result = calculate_emas_and_check_stacking(data)
                    
                    if ema_result:
                        ema_result["symbol"] = symbol
                        ema_result["exchange"] = request.exchange
                        return ema_result
                    
                    return None
                    
                except Exception as e:
                    logger.error(f"Error analyzing EMA for {stock_data.get('symbol', 'unknown')}: {str(e)}")
                    return None
            
            # Use ThreadPoolExecutor for CPU-intensive analysis
            with ThreadPoolExecutor(max_workers=10) as executor:
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(executor, analyze_ema_single_stock, stock_data)
                    for stock_data in batch_data
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Analysis exception: {result}")
                elif result is not None:
                    all_results.append(result)
                    # Removed verbose individual stock logging - only log final counts
            
            # Minimal delay between batches
            if i + batch_size < len(request.stock_codes):
                logger.info("Waiting 0.1 seconds before next batch...")
                await asyncio.sleep(0.1)
        
        stacked_stocks = [r for r in all_results if r['stacked']]
        logger.info(f"EMA stacking analysis complete. Found {len(stacked_stocks)} stocks with properly stacked EMAs out of {len(all_results)} total")
        return all_results
        
    except Exception as e:
        logger.error(f"Error in EMA stacking analysis: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in EMA stacking analysis: {str(e)} (Type: {type(e).__name__})"
        )

# Add these new concurrent processing functions after the existing helper functions

async def fetch_stock_data_concurrent(symbol: str, exchange: str, start_date: str, end_date: str) -> Dict:
    """Fetch data for a single stock concurrently"""
    try:
        formatted_symbol = f"{symbol.upper()}.{exchange.upper()}"
        url = f"{EODHD_BASE_URL}/eod/{formatted_symbol}"
        
        params = {
            'api_token': eodhd_api_key,
            'from': start_date,
            'to': end_date,
            'fmt': 'json',
            'period': 'd',
            'order': 'a'
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 404:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'No data found',
                    'data': None
                }
            
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'Empty data',
                    'data': None
                }
            
            return {
                'symbol': symbol,
                'success': True,
                'error': None,
                'data': data
            }
            
    except Exception as e:
        return {
            'symbol': symbol,
            'success': False,
            'error': str(e),
            'data': None
        }

async def process_stock_batch_concurrent(stock_codes: List[str], exchange: str, start_date: str, end_date: str, max_concurrent: int = 400) -> List[Dict]:
    """Process a batch of stocks concurrently with high concurrency for speed"""
    logger.info(f"Processing {len(stock_codes)} stocks concurrently (max {max_concurrent} at once)")
    
    # Check if scan was cancelled
    if exchange not in running_scans:
        logger.info(f"Scan for {exchange} was cancelled")
        return []
    
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(symbol: str) -> Dict:
        async with semaphore:
            try:
                # Minimal delay to respect rate limit (1000/minute = ~16.7/second)
                # Reduced delay for faster processing while staying within limits
                await asyncio.sleep(0.003)  # 3ms delay for maximum speed
                result = await fetch_stock_data_concurrent(symbol, exchange, start_date, end_date)
                if result['success']:
                    # Reduced logging - only log warnings and final counts
                    pass  # Commented out individual stock logging
                else:
                    logger.debug(f"{symbol}: {result['error']}")
                return result
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {str(e)}")
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': str(e),
                    'data': None
                }
    
    # Process all stocks concurrently
    tasks = [fetch_with_semaphore(symbol) for symbol in stock_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions and return valid results
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task exception: {result}")
        else:
            valid_results.append(result)
    
    logger.info(f"Concurrent batch complete: {len(valid_results)} results")
    return valid_results

async def analyze_ttm_squeeze_concurrent(stock_data_list: List[Dict], min_squeeze_days: int = 5) -> List[Dict]:
    """Apply TTM Squeeze analysis to multiple stocks concurrently"""
    logger.info(f"Applying TTM Squeeze analysis to {len(stock_data_list)} stocks concurrently")
    
    def analyze_single_stock(stock_data: Dict) -> Optional[Dict]:
        """Analyze a single stock (runs in thread pool)"""
        try:
            if not stock_data['success'] or not stock_data['data']:
                return None
            
            symbol = stock_data['symbol']
            data = stock_data['data']
            
            # Apply TTM Squeeze analysis with EMA filter
            squeeze_result = calculate_ttm_squeeze_with_ema_filter(symbol, data)
            
            if squeeze_result and squeeze_result['squeeze_days'] >= min_squeeze_days:
                # Reduced logging - only log final counts
                return squeeze_result
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing {stock_data.get('symbol', 'unknown')}: {str(e)}")
            return None
    
    # Use ThreadPoolExecutor for CPU-intensive analysis
    with ThreadPoolExecutor(max_workers=10) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, analyze_single_stock, stock_data)
            for stock_data in stock_data_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Analysis exception: {result}")
        elif result is not None:
            valid_results.append(result)
    
    logger.info(f"TTM Squeeze analysis complete: {len(valid_results)} stocks meet criteria")
    return valid_results

async def fetch_latest_data_concurrent(symbol: str, exchange: str) -> Dict:
    """Fetch only the latest data point for turnover calculation (much faster)"""
    try:
        formatted_symbol = f"{symbol.upper()}.{exchange.upper()}"
        url = f"{EODHD_BASE_URL}/eod/{formatted_symbol}"
        
        # Get only the last 5 days to ensure we have the latest data
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=5)
        
        params = {
            'api_token': eodhd_api_key,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'fmt': 'json',
            'period': 'd',
            'order': 'a'
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 404:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'No data found',
                    'data': None
                }
            
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'Empty data',
                    'data': None
                }
            
            # Return only the latest data point
            latest = data[-1]
            return {
                'symbol': symbol,
                'success': True,
                'error': None,
                'data': latest
            }
            
    except Exception as e:
        return {
            'symbol': symbol,
            'success': False,
            'error': str(e),
            'data': None
        }

async def filter_by_turnover_fast(stock_codes: List[str], exchange: str, min_turnover: float, max_concurrent: int = 200) -> List[str]:
    """Fast turnover filtering using only latest data points"""
    logger.info(f"Fast turnover filtering for {len(stock_codes)} stocks (min ${min_turnover:,.0f})")
    print(f"🔄 Starting turnover filtering: {len(stock_codes)} stocks to process...")
    
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Track progress
    processed_count = 0
    valid_symbols = []
    
    async def fetch_with_semaphore(symbol: str) -> Optional[str]:
        nonlocal processed_count
        async with semaphore:
            try:
                # Minimal delay for speed
                await asyncio.sleep(0.01)
                result = await fetch_latest_data_concurrent(symbol, exchange)
                
                processed_count += 1
                
                # Progress update every 500 stocks
                if processed_count % 500 == 0:
                    print(f"📊 Turnover progress: {processed_count}/{len(stock_codes)} stocks processed ({processed_count/len(stock_codes)*100:.1f}%)")
                
                if result['success'] and result['data']:
                    latest = result['data']
                    close_price = float(latest['close'])
                    volume = int(latest['volume'])
                    turnover = close_price * volume
                    
                    if turnover >= min_turnover:
                        # Reduced logging - only log final counts
                        return symbol
                    else:
                        return None
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {str(e)}")
                return None
    
    # Process all stocks concurrently
    tasks = [fetch_with_semaphore(symbol) for symbol in stock_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task exception: {result}")
        elif result is not None:
            valid_symbols.append(result)
    
    logger.info(f"Turnover filter complete: {len(valid_symbols)} stocks passed out of {len(stock_codes)}")
    print(f"✅ Turnover filter: {len(valid_symbols)} stocks traded over ${min_turnover:,.0f} out of {len(stock_codes)} stocks")
    return valid_symbols

async def fetch_market_cap_concurrent(symbol: str, exchange: str) -> Dict:
    """Fetch market cap for a single stock"""
    try:
        formatted_symbol = f"{symbol.upper()}.{exchange.upper()}"
        url = f"{EODHD_BASE_URL}/fundamentals/{formatted_symbol}"
        
        params = {
            'api_token': eodhd_api_key,
            'fmt': 'json'
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 404:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'No data found',
                    'market_cap': None
                }
            
            response.raise_for_status()
            data = response.json()
            
            # Extract market cap from fundamentals
            highlights = data.get('Highlights', {})
            market_cap = highlights.get('MarketCapitalization')
            
            return {
                'symbol': symbol,
                'success': True,
                'error': None,
                'market_cap': market_cap
            }
            
    except Exception as e:
        return {
            'symbol': symbol,
            'success': False,
            'error': str(e),
            'market_cap': None
        }

async def filter_stocks_by_market_cap(stock_codes: List[str], exchange: str, min_market_cap: float, max_concurrent: int = 100) -> List[str]:
    """Filter stocks by minimum market cap using concurrent requests"""
    logger.info(f"Filtering {len(stock_codes)} stocks by market cap (min ${min_market_cap:,.0f})")
    print(f"🔄 Starting market cap filtering: {len(stock_codes)} stocks to process...")
    
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Track progress
    processed_count = 0
    valid_symbols = []
    
    async def fetch_with_semaphore(symbol: str) -> Optional[str]:
        nonlocal processed_count, valid_symbols
        async with semaphore:
            try:
                # Minimal delay for rate limiting
                await asyncio.sleep(0.02)
                result = await fetch_market_cap_concurrent(symbol, exchange)
                
                processed_count += 1
                
                # Progress update every 1000 stocks
                if processed_count % 1000 == 0:
                    print(f"📊 Market cap progress: {processed_count}/{len(stock_codes)} stocks processed ({processed_count/len(stock_codes)*100:.1f}%)")
                
                if result['success'] and result['market_cap']:
                    market_cap = result['market_cap']
                    if market_cap >= min_market_cap:
                        return symbol
                    else:
                        return None
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Error fetching market cap for {symbol}: {str(e)}")
                return None
    
    # Process all stocks concurrently
    tasks = [fetch_with_semaphore(symbol) for symbol in stock_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task exception: {result}")
        elif result is not None:
            valid_symbols.append(result)
    
    logger.info(f"Market cap filter complete: {len(valid_symbols)} stocks passed out of {len(stock_codes)}")
    print(f"✅ Market cap filter: {len(valid_symbols)} stocks satisfied the ${min_market_cap:,.0f} constraint out of {len(stock_codes)} total stocks")
    return valid_symbols

@app.get("/api/stocks/with-market-cap/{exchange}", response_model=List[StockWithMarketCap])
async def get_stocks_with_market_cap(
    exchange: str = "US",
    min_market_cap: float = 500000000  # 500M default
):
    """Get all stocks from exchange with market cap data and filter by minimum market cap"""
    logger.info("="*80)
    logger.info(f"STOCKS WITH MARKET CAP REQUEST FOR {exchange}")
    logger.info(f"Min market cap: ${min_market_cap:,.0f}")
    logger.info("="*80)
    
    try:
        # Step 1: Get all common stocks from the exchange
        if exchange.upper() == "US":
            all_stocks_response = await get_us_stocks()
        elif exchange.upper() == "AU":
            all_stocks_response = await get_asx_stocks()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")
        
        if not all_stocks_response:
            logger.warning("No stocks found for exchange")
            return []
        
        logger.info(f"Found {len(all_stocks_response)} common stocks on {exchange}")
        
        # Step 2: Filter by market cap
        stock_codes = [stock.code for stock in all_stocks_response]
        stocks_with_market_cap = await filter_stocks_by_market_cap(
            stock_codes, 
            exchange, 
            min_market_cap, 
            max_concurrent=100
        )
        
        logger.info(f"After market cap filter: {len(stocks_with_market_cap)} stocks (min ${min_market_cap:,.0f})")
        
        if not stocks_with_market_cap:
            logger.warning("No stocks passed market cap filter")
            return []
        
        # Step 3: Create response with market cap data
        result_stocks = []
        for stock in all_stocks_response:
            if stock.code in stocks_with_market_cap:
                # Fetch market cap for this stock
                market_cap_data = await fetch_market_cap_concurrent(stock.code, exchange)
                market_cap = market_cap_data.get('market_cap') if market_cap_data['success'] else None
                
                result_stocks.append(StockWithMarketCap(
                    symbol=stock.code,
                    name=stock.name,
                    exchange=stock.exchange,
                    currency=stock.currency,
                    type=stock.type,
                    market_cap=market_cap
                ))
        
        logger.info(f"Returning {len(result_stocks)} stocks with market cap data")
        return result_stocks
        
    except Exception as e:
        logger.error(f"Error in market cap filtering: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in market cap filtering: {str(e)} (Type: {type(e).__name__})"
        )

async def filter_by_volume_fast(stock_codes: List[str], exchange: str, min_volume_usd: float, max_concurrent: int = 200) -> List[str]:
    """Fast volume filtering using only latest data points"""
    logger.info(f"Fast volume filtering for {len(stock_codes)} stocks (min ${min_volume_usd:,.0f} traded)")
    print(f"🔄 Starting volume filtering: {len(stock_codes)} stocks to process...")
    
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Track progress
    processed_count = 0
    
    async def fetch_with_semaphore(symbol: str) -> Optional[str]:
        nonlocal processed_count
        async with semaphore:
            try:
                # Minimal delay for speed
                await asyncio.sleep(0.01)
                result = await fetch_latest_data_concurrent(symbol, exchange)
                
                processed_count += 1
                
                # Progress update every 500 stocks
                if processed_count % 500 == 0:
                    print(f"📊 Volume progress: {processed_count}/{len(stock_codes)} stocks processed ({processed_count/len(stock_codes)*100:.1f}%)")
                
                if result['success'] and result['data']:
                    latest = result['data']
                    close_price = float(latest['close'])
                    volume = int(latest['volume'])
                    volume_usd = close_price * volume
                    
                    if volume_usd >= min_volume_usd:
                        # Reduced logging - only log final counts
                        return symbol
                    else:
                        return None
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {str(e)}")
                return None
    
    # Process all stocks concurrently
    tasks = [fetch_with_semaphore(symbol) for symbol in stock_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    valid_symbols = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task exception: {result}")
        elif result is not None:
            valid_symbols.append(result)
    
    logger.info(f"Volume filter complete: {len(valid_symbols)} stocks passed out of {len(stock_codes)}")
    print(f"✅ Volume filter: {len(valid_symbols)} stocks traded over ${min_volume_usd:,.0f} out of {len(stock_codes)} stocks")
    return valid_symbols

def calculate_ema(prices: List[float], period: int) -> float:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return prices[-1] if prices else 0
    
    multiplier = 2 / (period + 1)
    ema = prices[0]
    
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema

@app.get("/api/stocks/market-scanner-fast/{exchange}", response_model=List[Dict])
async def market_scanner_fast(
    exchange: str = "US", 
    min_turnover_us: float = 2000000,  # 2M for US stocks
    min_turnover_au: float = 500000,   # 500K for AU stocks (lower due to smaller market)
    min_squeeze_days: int = 5,
    min_volume_spike_ratio_us: float = 10.0,  # 10x for US stocks
    min_volume_spike_ratio_au: float = 5.0    # 5x for AU stocks (lower due to smaller market)
):
    """Fast market scanner that minimizes API calls by using efficient filtering"""
    logger.info("="*80)
    logger.info(f"FAST MARKET SCANNER FOR {exchange}")
    
    # Set turnover threshold based on exchange
    if exchange.upper() == "US":
        min_turnover = min_turnover_us
        min_volume_spike_ratio = min_volume_spike_ratio_us
        logger.info(f"Min turnover (US): ${min_turnover:,.0f}")
        logger.info(f"Min volume spike ratio (US): {min_volume_spike_ratio}x")
    elif exchange.upper() == "AU":
        min_turnover = min_turnover_au
        min_volume_spike_ratio = min_volume_spike_ratio_au
        logger.info(f"Min turnover (AU): ${min_turnover:,.0f}")
        logger.info(f"Min volume spike ratio (AU): {min_volume_spike_ratio}x")
    else:
        min_turnover = min_turnover_us  # Default to US threshold
        min_volume_spike_ratio = min_volume_spike_ratio_us  # Default to US threshold
        logger.info(f"Min turnover (default): ${min_turnover:,.0f}")
        logger.info(f"Min volume spike ratio (default): {min_volume_spike_ratio}x")
    
    logger.info(f"Min squeeze days: {min_squeeze_days}")
    logger.info("="*80)
    
    try:
        # Step 1: Get all stocks from the exchange
        logger.info("Step 1: Getting all stocks from exchange...")
        if exchange.upper() == "US":
            logger.info("Fetching US stocks...")
            all_stocks_response = await get_us_stocks()
        elif exchange.upper() == "AU":
            logger.info("Fetching ASX stocks...")
            all_stocks_response = await get_asx_stocks()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")
        
        if not all_stocks_response:
            logger.warning("No stocks found for exchange")
            return []
        
        logger.info(f"Found {len(all_stocks_response)} common stocks on {exchange}")
        
        stock_codes = [stock.code for stock in all_stocks_response]
        
        # Step 2: Fetch full historical data for ALL stocks in one go (most efficient)
        logger.info("Step 2: Fetching full historical data for all stocks...")
        print(f"🔄 Fetching data for {len(stock_codes)} stocks...")
        
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=730)
        
        # Check if scan was cancelled before starting data fetch
        if exchange not in running_scans:
            logger.info(f"Scan for {exchange} was cancelled before data fetch")
            return {"ttm_squeeze": [], "volume_spikes": []}
        
        # Use maximum concurrency for speed
        all_stock_data = await process_stock_batch_concurrent(
            stock_codes,
            exchange,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            max_concurrent=400  # Higher concurrency for speed
        )
        
        # Check if scan was cancelled after data fetch
        if exchange not in running_scans:
            logger.info(f"Scan for {exchange} was cancelled after data fetch")
            return {"ttm_squeeze": [], "volume_spikes": []}
        
        # Step 3: Process all filters simultaneously in memory (no additional API calls)
        logger.info("Step 3: Processing filters simultaneously...")
        ttm_squeeze_candidates = []
        volume_spike_candidates = []
        
        for data in all_stock_data:
            if data['success'] and data['data'] and len(data['data']) > 20:
                stock_data = data['data']
                latest_data = stock_data[-1]
                close_price = float(latest_data['close'])
                volume = int(latest_data['volume'])
                volume_usd = close_price * volume
                
                # Check turnover filter first - applies to both TTM squeeze and volume spikes
                if volume_usd >= min_turnover:
                    # Add to TTM squeeze candidates
                    ttm_squeeze_candidates.append(data)
                    
                    # Check for volume spikes (only if we have enough data)
                    if len(stock_data) >= 30:
                        recent_volumes = [int(d['volume']) for d in stock_data[-3:]]
                        trailing_volumes = [int(d['volume']) for d in stock_data[-30:]]
                        
                        # Calculate median of trailing 30 days
                        median_volume_30d = statistics.median(trailing_volumes)
                        
                        # Skip stocks with zero volume or zero median volume
                        if median_volume_30d <= 0 or all(vol == 0 for vol in recent_volumes):
                            continue
                        
                        # Calculate 9 EMA
                        closes = [float(d['close']) for d in stock_data]
                        ema_9 = calculate_ema(closes, 9)
                        current_price = closes[-1]
                        
                        # Check volume spike criteria
                        has_volume_spike = all(vol >= median_volume_30d * min_volume_spike_ratio for vol in recent_volumes)
                        above_ema = current_price > ema_9
                        
                        if has_volume_spike and above_ema:
                            volume_spike_candidates.append({
                                'symbol': data['symbol'],
                                'data': stock_data,
                                'latest_volume_usd': volume_usd,
                                'volume_spike_ratio': max(recent_volumes) / median_volume_30d if median_volume_30d > 0 else 0,
                                'current_price': current_price,
                                'ema_9': ema_9
                            })
        
        logger.info(f"After filtering:")
        logger.info(f"  - TTM Squeeze candidates: {len(ttm_squeeze_candidates)} stocks")
        logger.info(f"  - Volume spike candidates: {len(volume_spike_candidates)} stocks")
        print(f"✅ Filters: {len(ttm_squeeze_candidates)} TTM, {len(volume_spike_candidates)} Volume spikes")
        
        if not ttm_squeeze_candidates:
            logger.warning("No stocks passed TTM squeeze filters")
            return {"ttm_squeeze": [], "volume_spikes": []}
        
        # Check if scan was cancelled before TTM analysis
        if exchange not in running_scans:
            logger.info(f"Scan for {exchange} was cancelled before TTM analysis")
            return {"ttm_squeeze": [], "volume_spikes": []}
        
        # Step 4: Apply TTM Squeeze analysis with maximum CPU utilization
        logger.info(f"Step 4: Applying TTM Squeeze analysis (min {min_squeeze_days} days)...")
        squeeze_results = await analyze_ttm_squeeze_concurrent(ttm_squeeze_candidates, min_squeeze_days)
        
        # Add additional info to results
        final_results = []
        for result in squeeze_results:
            # Find the corresponding stock data for turnover
            stock_data = next((s for s in ttm_squeeze_candidates if s['symbol'] == result['symbol']), None)
            if stock_data and stock_data['data']:
                latest_data = stock_data['data'][-1]
                turnover = float(latest_data['close']) * int(latest_data['volume'])
                result["exchange"] = exchange
                result["turnover"] = turnover
                result["name"] = ""
                
                # Filter out stocks with ATR/close ratio < 1%
                atr_ratio = result.get('atr_ratio', None)
                if atr_ratio is not None and atr_ratio < 1.0:
                    logger.info(f"[FILTERED] {result['symbol']}: ATR ratio {atr_ratio:.2f}% < 1% threshold")
                    continue
                
                final_results.append(result)
                
                # Enhanced logging with ATR ratio
                atr_info = f"ATR: {atr_ratio:.2f}%" if atr_ratio is not None else "ATR: N/A"
                logger.info(f"[PASS] {result['symbol']}: Squeeze days={result['squeeze_days']}, intensity={result['squeeze_intensity']}, turnover=${result['turnover']:,.0f}, {atr_info}")
                
                # Print ATR ratio for quick assessment
                if atr_ratio is not None:
                    if atr_ratio < 2.0:
                        print(f"🔴 {result['symbol']}: Low volatility squeeze (ATR: {atr_ratio:.2f}%)")
                    elif atr_ratio < 5.0:
                        print(f"🟡 {result['symbol']}: Medium volatility squeeze (ATR: {atr_ratio:.2f}%)")
                    else:
                        print(f"🟢 {result['symbol']}: High volatility squeeze (ATR: {atr_ratio:.2f}%)")
        
        logger.info(f"TTM Squeeze analysis complete. Found {len(final_results)} stocks meeting criteria")
        print(f"🎯 TTM Squeeze: {len(final_results)} stocks found")
        
        # Log volume spike results for reference
        if volume_spike_candidates:
            print(f"📈 Volume Spikes: {len(volume_spike_candidates)} stocks found")
            
            # Sort by max spike ratio and show detailed results
            sorted_spikes = sorted(volume_spike_candidates, key=lambda x: x['volume_spike_ratio'], reverse=True)
            
            for spike in sorted_spikes:
                symbol = spike['symbol']
                current_price = spike['current_price']
                ema_9 = spike['ema_9']
                
                # Calculate spike ratios for display
                stock_data = spike['data']
                recent_volumes = [int(d['volume']) for d in stock_data[-3:]]
                trailing_volumes = [int(d['volume']) for d in stock_data[-30:]]
                median_volume_30d = statistics.median(trailing_volumes)
                
                # Prevent division by zero
                if median_volume_30d > 0:
                    spike_ratios = [round(vol / median_volume_30d, 1) for vol in recent_volumes]
                    ratios_str = f"{spike_ratios[0]}x, {spike_ratios[1]}x, {spike_ratios[2]}x"
                else:
                    ratios_str = "N/A (zero volume)"
                
                print(f"  {symbol}: ${current_price:.2f} | {ratios_str} | Max: {spike['volume_spike_ratio']:.1f}x | EMA9: ${ema_9:.2f}")
        else:
            print("📈 Volume Spikes: 0 stocks found")
        
        logger.info("="*80)
        
        # Return both TTM squeeze and volume spike results
        return {
            "ttm_squeeze": final_results,
            "volume_spikes": volume_spike_candidates
        }
        
    except Exception as e:
        logger.error(f"Error in fast market scanner: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in fast market scanner: {str(e)} (Type: {type(e).__name__})"
        )

@app.get("/api/market-scanner/results/{country}")
async def get_market_scanner_results(country: str):
    """Get the latest market scanner results for a specific country from database"""
    try:
        if country.upper() not in ["US", "AU"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported country: {country}. Must be US or AU."
            )
        
        results = DatabaseService.get_latest_results(country.upper())
        
        # Add Sydney time for frontend compatibility
        if results["last_updated"]:
            utc_time = datetime.fromisoformat(results["last_updated"].replace('Z', '+00:00'))
            sydney_time = utc_time.astimezone(pytz.timezone('Australia/Sydney'))
            results["sydney_time"] = sydney_time.isoformat()
        else:
            results["sydney_time"] = None
        
        return results
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 400) as-is
        raise
    except Exception as e:
        logger.error(f"Error getting results for {country}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving results: {str(e)}"
        )

@app.get("/api/market-scanner/results")
async def get_all_market_scanner_results():
    """Get the latest market scanner results for both countries from database"""
    try:
        us_results = DatabaseService.get_latest_results("US")
        au_results = DatabaseService.get_latest_results("AU")
        
        return {
            "US": us_results,
            "AU": au_results,
            "timestamp": datetime.now(pytz.UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting all results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving results: {str(e)}"
        )

@app.post("/api/market-scanner/cancel/{country}")
async def cancel_market_scanner(country: str):
    """Cancel a running market scanner for a specific country"""
    try:
        country = country.upper()
        if country in running_scans:
            running_scans.remove(country)
            logger.info(f"Cancelled market scanner for {country}")
            return {"message": f"Market scanner for {country} has been cancelled"}
        else:
            return {"message": f"No running scan found for {country}"}
    except Exception as e:
        logger.error(f"Error cancelling scanner for {country}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling scanner: {str(e)}"
        )

@app.get("/api/market-scanner/run/{country}")
async def run_market_scanner_manual(
    country: str,
    min_turnover_us: float = 2000000,  # 2M for US stocks
    min_turnover_au: float = 500000,   # 500K for AU stocks  
    min_squeeze_days: int = 5,
    min_volume_spike_ratio_us: float = 10.0,  # 10x for US stocks
    min_volume_spike_ratio_au: float = 5.0    # 5x for AU stocks
):
    """Manually trigger a market scanner run and save results to database"""
    try:
        if country.upper() not in ["US", "AU"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported country: {country}. Must be US or AU."
            )
        
        country_upper = country.upper()
        
        # Check if scan is already running for this country
        if country_upper in running_scans:
            raise HTTPException(
                status_code=409,
                detail=f"Market scanner for {country_upper} is already running"
            )
        
        # Add to running scans
        running_scans.add(country_upper)
        logger.info(f"Starting manual market scanner for {country_upper}")
        
        # Run the fast market scanner with parameters
        scanner_results = await market_scanner_fast(
            exchange=country_upper,
            min_turnover_us=min_turnover_us,
            min_turnover_au=min_turnover_au,
            min_squeeze_days=min_squeeze_days,
            min_volume_spike_ratio_us=min_volume_spike_ratio_us,
            min_volume_spike_ratio_au=min_volume_spike_ratio_au
        )
        
        # Convert results to the format expected by DatabaseService
        formatted_results = {
            "ttm_squeeze": [],
            "volume_spikes": []
        }
        
        # Process TTM squeeze results
        for result in scanner_results["ttm_squeeze"]:
            formatted_results["ttm_squeeze"].append({
                "symbol": result["symbol"],
                "company_name": result.get("name", result["symbol"]),
                "exchange": result["exchange"],
                "price": result.get("latest_close", 0),
                "change": 0,
                "change_percent": 0,
                "volume": result.get("latest_volume", 0),
                "market_cap": 0,
                "pe_ratio": 0,
                "squeeze_days": result.get("squeeze_days", 0),
                "bollinger_bands": result.get("bollinger_bands", {}),
                "keltner_channels": result.get("keltner_channels", {}),
                "momentum": result.get("momentum", 0),
                "squeeze_intensity": result.get("squeeze_intensity", "")
            })
        
        # Process volume spike results
        for spike in scanner_results["volume_spikes"]:
            # Calculate volume ratio and other required fields
            stock_data = spike['data']
            recent_volumes = [int(d['volume']) for d in stock_data[-3:]]
            trailing_volumes = [int(d['volume']) for d in stock_data[-30:]]
            median_volume_30d = statistics.median(trailing_volumes)
            max_spike_ratio = max(vol / median_volume_30d for vol in recent_volumes) if median_volume_30d > 0 else 0
            
            # Determine spike intensity based on max ratio
            if max_spike_ratio >= 20:
                intensity = "extreme"
            elif max_spike_ratio >= 10:
                intensity = "high"
            else:
                intensity = "moderate"
            
            formatted_results["volume_spikes"].append({
                "symbol": spike["symbol"],
                "company_name": spike["symbol"],  # We don't have company names in spike data
                "exchange": country.upper(),
                "price": spike["current_price"],
                "change": 0,
                "change_percent": 0,
                "volume": int(stock_data[-1]['volume']),  # Latest volume
                "market_cap": 0,
                "pe_ratio": 0,
                "spike_days": 3,  # Always 3 consecutive days
                "volume_ratio": max_spike_ratio,
                "avg_volume_30d": int(median_volume_30d),
                "consecutive_days": 3,
                "spike_intensity": intensity
            })
        
        # Save results to database
        DatabaseService.save_scan_results(country_upper, formatted_results, "manual")
        
        # Remove from running scans
        running_scans.discard(country_upper)
        
        logger.info(f"Manual market scanner completed for {country_upper}")
        return {
            "message": f"Market scanner completed for {country_upper}", 
            "ttm_squeeze_count": len(formatted_results["ttm_squeeze"]),
            "volume_spike_count": len(formatted_results["volume_spikes"]),
            "total_results": len(formatted_results["ttm_squeeze"]) + len(formatted_results["volume_spikes"])
        }
        
    except Exception as e:
        # Remove from running scans on error
        running_scans.discard(country_upper)
        logger.error(f"Error running manual scanner for {country}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running scanner: {str(e)}"
        )

# Background task to start scheduler
@app.on_event("startup")
async def start_scheduler_background():
    """Start the scheduler as a background task when the app starts"""
    logger.info("🚀 Starting Market Scanner Scheduler in background...")
    asyncio.create_task(scheduler.schedule_scanners())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 