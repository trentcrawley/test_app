/*'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { CandlestickData, MarketStatus, PlotData, PlotLayout } from '@/app/types';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);

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

  useEffect(() => {
    console.log('Component mounted, fetching initial data...');
    fetchMarketStatus();
    fetchData();
  }, []); // Only fetch on mount

  const handleSymbolSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
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
    title: { text: `${symbol} Stock Price` },
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
          {marketStatus && (
            <div className={`mb-4 p-2 rounded ${marketStatus.is_open ? 'bg-green-900/50' : 'bg-red-900/50'}`}>
              Market is currently {marketStatus.is_open ? 'OPEN' : 'CLOSED'}
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
*/

'use client';

export const dynamic = "force-dynamic";

export default function Home() {
  return <h1>✅ Dynamic homepage loaded</h1>;
}
