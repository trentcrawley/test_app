'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface CandlestickData {
  dates: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
  data_source: string;
}

interface StockInfo {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  eps: number | null;
  dividend_yield: number | null;
  beta: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
}

interface NewsItem {
  date: string;
  title: string;
  link: string;
  text: string;
  source: string;
  tags: string[];
  symbols: string[];
}

export default function Home() {
  const [symbol, setSymbol] = useState('AAPL');
  const [exchange, setExchange] = useState('US');
  const [candlestickData, setCandlestickData] = useState<CandlestickData | null>(null);
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (ticker: string, exchangeCode: string) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch candlestick data
      const candlestickResponse = await fetch(
        `http://localhost:8000/api/stock/${ticker}/candlestick?exchange=${exchangeCode}`
      );
      if (!candlestickResponse.ok) {
        throw new Error(`Error fetching candlestick data: ${candlestickResponse.statusText}`);
      }
      const candlestickData = await candlestickResponse.json();
      setCandlestickData(candlestickData);

      // Fetch stock info
      const infoResponse = await fetch(
        `http://localhost:8000/api/stock/${ticker}/info?exchange=${exchangeCode}`
      );
      if (!infoResponse.ok) {
        throw new Error(`Error fetching stock info: ${infoResponse.statusText}`);
      }
      const stockInfo = await infoResponse.json();
      setStockInfo(stockInfo);

      // Fetch news
      const newsResponse = await fetch(
        `http://localhost:8000/api/stock/${ticker}/news?exchange=${exchangeCode}`
      );
      if (!newsResponse.ok) {
        throw new Error(`Error fetching news: ${newsResponse.statusText}`);
      }
      const newsData = await newsResponse.json();
      setNews(newsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(symbol, exchange);
  }, [symbol, exchange]);

  const formatNumber = (num: number | null) => {
    if (num === null) return 'N/A';
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatPercent = (num: number | null) => {
    if (num === null) return 'N/A';
    return `${(num * 100).toFixed(2)}%`;
  };

  return (
    <main className="container mx-auto p-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">Stock Market Data</h1>
        <div className="flex gap-4 items-center">
          <div className="flex gap-2 items-center">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="border p-2 rounded"
              placeholder="Enter stock symbol"
            />
            <select
              value={exchange}
              onChange={(e) => setExchange(e.target.value)}
              className="border p-2 rounded"
            >
              <option value="US">US (NYSE/NASDAQ)</option>
              <option value="AU">ASX (Australian)</option>
              <option value="L">LSE (London)</option>
              <option value="T">TSE (Tokyo)</option>
              <option value="HK">HKEX (Hong Kong)</option>
              <option value="NS">NSE (India)</option>
            </select>
          </div>
          <button
            onClick={() => fetchData(symbol, exchange)}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Search'}
          </button>
        </div>
        {error && (
          <div className="text-red-500 mt-2">
            {error}
          </div>
        )}
      </div>

      {stockInfo && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Company Info</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-bold">{stockInfo.name} ({stockInfo.symbol})</p>
              <p>Exchange: {stockInfo.exchange}</p>
              <p>Sector: {stockInfo.sector || 'N/A'}</p>
              <p>Industry: {stockInfo.industry || 'N/A'}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Market Data</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Market Cap: {formatNumber(stockInfo.market_cap)}</p>
              <p>P/E Ratio: {stockInfo.pe_ratio?.toFixed(2) || 'N/A'}</p>
              <p>EPS: {stockInfo.eps?.toFixed(2) || 'N/A'}</p>
              <p>Dividend Yield: {formatPercent(stockInfo.dividend_yield)}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Technical Data</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Beta: {stockInfo.beta?.toFixed(2) || 'N/A'}</p>
              <p>52W High: {formatNumber(stockInfo.fifty_two_week_high)}</p>
              <p>52W Low: {formatNumber(stockInfo.fifty_two_week_low)}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Latest Price</CardTitle>
            </CardHeader>
            <CardContent>
              {candlestickData && (
                <p className="text-2xl font-bold">
                  {formatNumber(candlestickData.close[candlestickData.close.length - 1])}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {candlestickData && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Price Chart (2 Years)</CardTitle>
          </CardHeader>
          <CardContent>
            <Plot
              data={[
                {
                  type: 'candlestick',
                  x: candlestickData.dates,
                  open: candlestickData.open,
                  high: candlestickData.high,
                  low: candlestickData.low,
                  close: candlestickData.close,
                  name: 'OHLC',
                },
                {
                  type: 'bar',
                  x: candlestickData.dates,
                  y: candlestickData.volume,
                  name: 'Volume',
                  yaxis: 'y2',
                  marker: {
                    color: 'rgba(0, 0, 255, 0.3)',
                  },
                },
              ]}
              layout={{
                title: {
                  text: `${symbol} Stock Price`,
                  font: { size: 24 }
                },
                yaxis: {
                  title: { text: 'Price' },
                  domain: [0.2, 1],
                },
                yaxis2: {
                  title: { text: 'Volume' },
                  domain: [0, 0.2],
                },
                xaxis: {
                  rangeslider: { visible: false },
                },
                height: 600,
                showlegend: true,
                legend: { x: 0, y: 1 },
              }}
              config={{ responsive: true }}
              style={{ width: '100%' }}
            />
          </CardContent>
        </Card>
      )}

      {news.length > 0 && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Recent News</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {news.map((item, index) => (
                <div key={index} className="border-b pb-4 last:border-b-0">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-semibold">
                      <a 
                        href={item.link} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800"
                      >
                        {item.title}
                      </a>
                    </h3>
                    <span className="text-sm text-gray-500">
                      {new Date(item.date).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-gray-600 mb-2">{item.text}</p>
                  <div className="flex gap-2 text-sm text-gray-500">
                    <span>Source: {item.source}</span>
                    {item.tags.length > 0 && (
                      <span>• Tags: {item.tags.join(', ')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
