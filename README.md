# Stock Market Data Application

A full-stack web application for viewing stock market data, built with FastAPI and Next.js. The application provides real-time stock data, historical price charts, fundamental information, and news for stocks from various exchanges worldwide.

## Features

- Real-time stock data from EODHD API
- Interactive candlestick charts with volume
- Fundamental stock information
- Recent news articles
- Support for multiple exchanges (US, ASX, LSE, TSE, HKEX, NSE)
- Responsive design

## Tech Stack

### Backend
- FastAPI (Python)
- EODHD API for market data
- Async HTTP requests with httpx
- CORS middleware for frontend communication

### Frontend
- Next.js 14
- React
- Plotly.js for interactive charts
- Tailwind CSS for styling
- TypeScript for type safety

## Setup

### Prerequisites
- Python 3.8+
- Node.js 18+
- EODHD API key

### Backend Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the backend directory:
   ```
   EODHD_API_KEY=your_api_key_here
   ```

4. Start the backend server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Usage

1. Enter a stock symbol (e.g., "AAPL" for Apple Inc.)
2. Select the exchange (e.g., "US" for NYSE/NASDAQ, "AU" for ASX)
3. Click "Search" to view:
   - Company information
   - Market data
   - Technical indicators
   - Price chart
   - Recent news

## API Endpoints

- `GET /api/stock/{symbol}/candlestick` - Get historical price data
- `GET /api/stock/{symbol}/info` - Get fundamental stock information
- `GET /api/stock/{symbol}/news` - Get recent news articles
- `GET /api/market-status` - Get current market status

## License

MIT License 