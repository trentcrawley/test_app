'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { CandlestickData, MarketStatus, PlotData, PlotLayout, LastPrice } from '@/app/types';

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { 
  ssr: false,
  loading: () => <div>Loading chart component...</div>
});

// Get API URL from environment variable, fallback to localhost for development
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [symbol, setSymbol] = useState('AAPL');
  const [data, setData] = useState<CandlestickData | null>(null);
  const [lastPrice, setLastPrice] = useState<LastPrice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [testResult, setTestResult] = useState<any>(null);
  const [testingYFinance, setTestingYFinance] = useState(false);

  const fetchMarketStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/market-status`);
      if (!response.ok) throw new Error('Failed to fetch market status');
      const status = await response.json();
      setMarketStatus(status);
    } catch (err) {
      console.error('Error fetching market status:', err);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('Fetching data for symbol:', symbol);
      const response = await fetch(`${API_URL}/api/stock/${symbol}/candlestick`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      console.log('Received data:', result);
      setData(result);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchLastPrice = async () => {
    try {
      console.log('Fetching last price for:', symbol);
      const response = await fetch(`${API_URL}/api/stock/${symbol}/last-price`);
      console.log('Last price response status:', response.status);
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        console.error('Last price error:', errorData);
        throw new Error(errorData?.detail || `HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      console.log('Last price result:', result);
      setLastPrice(result);
    } catch (err) {
      console.error('Error fetching last price:', err);
      // Don't set error state here to avoid disrupting the UI
    }
  };

  const testYFinance = async () => {
    setTestingYFinance(true);
    setTestResult(null);
    try {
      const response = await fetch(`${API_URL}/api/test-yfinance`);
      const data = await response.json();
      setTestResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test yfinance');
    } finally {
      setTestingYFinance(false);
    }
  };

  useEffect(() => {
    console.log('Component mounted, fetching initial data...');
    fetchMarketStatus();
    fetchData();
  }, []); // Only fetch on mount

  const handleSymbolSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchData(), fetchLastPrice()]);
    } catch (err) {
      console.error('Error in handleSymbolSubmit:', err);
    } finally {
      setLoading(false);
    }
  };

  const plotData: PlotData = data ? [{
    type: 'candlestick' as const,
    x: data.dates,
    open: data.open,
    high: data.high,
    low: data.low,
    close: data.close,
    name: symbol,
    increasing: { line: { color: '#26a69a' } },
    decreasing: { line: { color: '#ef5350' } }
  }] : [];

  const layout: PlotLayout = {
    title: { 
      text: `${symbol} Stock Price (${data?.data_source || 'Loading...'})`,
      font: { size: 24 }
    },
    yaxis: { title: { text: 'Price' } },
    xaxis: { title: { text: 'Date' } },
    template: 'plotly_dark',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#fff' }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-4">Stock Chart Viewer</h1>
          <div className="flex gap-4 mb-4">
            <button
              onClick={testYFinance}
              disabled={testingYFinance}
              className="px-4 py-2 bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {testingYFinance ? 'Testing yfinance...' : 'Test yfinance Access'}
            </button>
          </div>
          {testResult && (
            <div className="mb-4 p-4 bg-gray-800 rounded">
              <h3 className="font-bold mb-2">yfinance Test Result:</h3>
              <pre className="whitespace-pre-wrap text-sm">
                {JSON.stringify(testResult, null, 2)}
              </pre>
            </div>
          )}
          {marketStatus && (
            <div className={`mb-4 p-2 rounded ${marketStatus.is_open ? 'bg-green-900/50' : 'bg-red-900/50'}`}>
              Market is currently {marketStatus.is_open ? 'OPEN' : 'CLOSED'}
            </div>
          )}
          {lastPrice && (
            <div className="mb-4 p-4 bg-gray-800 rounded">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-400">Last Trade (Polygon)</div>
                  <div className="text-xl font-semibold">
                    ${lastPrice.price.toFixed(2)}
                  </div>
                </div>
                {lastPrice.close_price !== null && (
                  <div>
                    <div className="text-sm text-gray-400">Previous Close (YFinance)</div>
                    <div className="text-xl font-semibold">
                      ${lastPrice.close_price.toFixed(2)}
                    </div>
                  </div>
                )}
              </div>
              <div className="text-sm text-gray-400 mt-2">
                Last updated: {new Date(lastPrice.timestamp).toLocaleString()}
              </div>
            </div>
          )}
          {data && (
            <div className="mb-4 p-2 bg-gray-800 rounded">
              <div className="text-sm text-gray-400">Data Source: <span className="text-white font-semibold">{data.data_source}</span></div>
            </div>
          )}
          <form onSubmit={handleSymbolSubmit} className="flex gap-4 items-center">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="px-4 py-2 rounded bg-gray-800 border border-gray-700 focus:border-blue-500 focus:outline-none"
              placeholder="Enter stock symbol"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Update'}
            </button>
          </form>
          {error && (
            <div className="mt-4 p-4 bg-red-900/50 rounded text-red-200">
              {error}
            </div>
          )}
        </div>

        <div className="bg-gray-800 rounded-lg p-4">
          {loading ? (
            <div className="h-[600px] flex items-center justify-center text-gray-400">
              Loading chart data...
            </div>
          ) : data ? (
            <Plot
              data={plotData}
              layout={layout}
              style={{ width: '100%', height: '600px' }}
              config={{ responsive: true }}
            />
          ) : (
            <div className="h-[600px] flex items-center justify-center text-gray-400">
              Enter a stock symbol to view chart
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
