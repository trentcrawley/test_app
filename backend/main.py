from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv
import httpx
import logging
import random
import requests
from requests.exceptions import RequestException
from requests.auth import HTTPProxyAuth

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
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

# Check if API key is available
eodhd_api_key = os.getenv("EODHD_API_KEY")
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
        "https://*.vercel.app",
        "https://test-ctowuw7l8-trents-projects-d2eec580.vercel.app",
        "https://test-app-alpha-opal.vercel.app"
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
            for item in data:
                # Only include common stocks (not ETFs, bonds, etc.)
                if item.get('Type') == 'Common Stock':
                    stocks.append(StockSymbol(
                        code=item.get('Code', ''),
                        name=item.get('Name', ''),
                        exchange=item.get('Exchange', 'US'),
                        currency=item.get('Currency', 'USD'),
                        type=item.get('Type', 'Common Stock')
                    ))
            
            logger.info(f"Returning {len(stocks)} US common stocks")
            return stocks
            
    except Exception as e:
        logger.error(f"Error fetching US stocks: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching US stocks: {str(e)} (Type: {type(e).__name__})"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 