from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import pandas as pd
import pytz
import time

app = FastAPI(title="Financial Data API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://*.vercel.app"  # Allow all Vercel deployments
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

class StockData(BaseModel):
    symbol: str
    current_price: float
    change_percent: float
    volume: int
    timestamp: datetime

class CandlestickData(BaseModel):
    dates: List[str]
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: List[int]

# def get_stock_data(symbol: str, max_retries: int = 3) -> yf.Ticker:
#     """Get stock data with retries and better error handling"""
#     for attempt in range(max_retries):
#         try:
#             # Create a new Ticker instance each time
#             stock = yf.Ticker(symbol)
            
#             # Try to get basic info first
#             info = stock.info
#             if not info:
#                 raise ValueError(f"No info available for {symbol}")
            
#             # Verify we have a valid symbol
#             if 'regularMarketPrice' not in info and 'currentPrice' not in info:
#                 raise ValueError(f"Invalid or delisted symbol: {symbol}")
            
#             return stock
#         except Exception as e:
#             if attempt == max_retries - 1:  # Last attempt
#                 if "symbol may be delisted" in str(e):
#                     raise HTTPException(
#                         status_code=404,
#                         detail=f"Symbol {symbol} may be delisted or incorrect. Please verify the symbol."
#                     )
#                 raise HTTPException(
#                     status_code=500,
#                     detail=f"Error fetching data for {symbol} after {max_retries} attempts: {str(e)}"
#                 )
#             time.sleep(1)  # Wait before retrying
def get_stock_data(symbol: str, max_retries: int = 3) -> yf.Ticker:
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Attempt {attempt + 1} to fetch {symbol}")
            stock = yf.Ticker(symbol)

            # ✅ NEW: Print the raw info dict
            info = stock.info
            print(f"[DEBUG] stock.info = {info}")

            if not info:
                raise ValueError(f"No info available for {symbol}")

            if 'regularMarketPrice' not in info and 'currentPrice' not in info:
                raise ValueError(f"Invalid or delisted symbol: {symbol}")

            return stock
        except Exception as e:
            print(f"[ERROR] get_stock_data failed: {e}")
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error fetching data for {symbol}: {str(e)}"
                )
            time.sleep(1)
def fetch_historical_data(stock: yf.Ticker, period: str, interval: str = "1d") -> pd.DataFrame:
    """Fetch historical data with retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            hist = stock.history(period=period, interval=interval)
            if not hist.empty:
                return hist
            time.sleep(1)  # Wait before retrying
        except Exception as e:
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch historical data after {max_retries} attempts: {str(e)}"
                )
            time.sleep(1)
    return pd.DataFrame()  # Return empty DataFrame if all retries failed

@app.get("/")
async def root():
    return {"message": "Financial Data API is running"}

@app.get("/api/market-status")
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

@app.get("/api/stock/{symbol}", response_model=StockData)
async def get_stock_data_endpoint(symbol: str):
    try:
        stock = get_stock_data(symbol)
        info = stock.info
        
        # Try to get current price from info first
        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
        if not current_price:
            # Fallback to historical data
            hist = fetch_historical_data(stock, "5d")
            if hist.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No price data available for {symbol}"
                )
            current_price = hist['Close'].iloc[-1]
        
        # Get previous close for change calculation
        prev_close = info.get('regularMarketPreviousClose')
        if not prev_close:
            hist = fetch_historical_data(stock, "5d")
            if len(hist) > 1:
                prev_close = hist['Close'].iloc[-2]
            else:
                prev_close = current_price
        
        change_percent = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0
        
        return StockData(
            symbol=symbol.upper(),
            current_price=round(float(current_price), 2),
            change_percent=round(change_percent, 2),
            volume=int(info.get('regularMarketVolume', 0)),
            timestamp=datetime.now(MARKET_TIMEZONE)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing data for {symbol}: {str(e)}"
        )

@app.get("/api/stock/{symbol}/candlestick", response_model=CandlestickData)
async def get_stock_candlestick(symbol: str, period: str = "1mo", interval: str = "1d"):
    try:
        print(f"[DEBUG] Fetching candlestick data for {symbol}")
        stock = get_stock_data(symbol)

        hist = fetch_historical_data(stock, period, interval)
        print(f"[DEBUG] Retrieved {len(hist)} rows for {symbol}")

        if hist.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data available for {symbol} with period={period} and interval={interval}"
            )

        return CandlestickData(
            dates=hist.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            open=hist['Open'].round(2).tolist(),
            high=hist['High'].round(2).tolist(),
            low=hist['Low'].round(2).tolist(),
            close=hist['Close'].round(2).tolist(),
            volume=hist['Volume'].tolist()
        )

    except Exception as e:
        print(f"[ERROR] Failed to get candlestick data for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}"
        )


# @app.get("/api/stock/{symbol}/candlestick", response_model=CandlestickData)
# async def get_stock_candlestick(
#     symbol: str,
#     period: str = "1mo",
#     interval: str = "1d"
# ):
#     try:
#         stock = get_stock_data(symbol)
        
#         # Adjust period based on interval
#         if interval == "1d":
#             if period == "1d":
#                 period = "5d"  # Get more data for daily view
#         elif interval in ["1h", "30m", "15m"]:
#             if period == "1d":
#                 period = "5d"  # Get more data for intraday view
        
#         hist = fetch_historical_data(stock, period, interval)
#         if hist.empty:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"No historical data available for {symbol} with period={period} and interval={interval}"
#             )
        
#         return CandlestickData(
#             dates=hist.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
#             open=hist['Open'].round(2).tolist(),
#             high=hist['High'].round(2).tolist(),
#             low=hist['Low'].round(2).tolist(),
#             close=hist['Close'].round(2).tolist(),
#             volume=hist['Volume'].tolist()
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error fetching candlestick data for {symbol}: {str(e)}"
#         )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 