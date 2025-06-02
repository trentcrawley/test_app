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

// Add type for proxy status
interface ProxyStatus {
  status: 'success' | 'error';
  direct_ip: string;
  proxy_ip: string;
  proxy_used: string;
  ips_match: boolean;
  message?: string;
}

interface YFinanceResult {
  status: string;
  message: string;
  proxy_used?: string;
  proxy_ip?: string;
  error_type?: string;
  error_details?: string;
  data_source?: 'yfinance' | 'direct_api';
  data?: {
    symbol: string;
    current_price: number | string;
    company_name: string;
  };
}

interface ProxyResult {
  status: string;
  message: string;
  proxy_used: string;
  proxy_ip?: string;
  yahoo_response?: {
    status: number;
    headers: Record<string, string>;
    body?: string;
    request_headers: Record<string, string>;
    proxy_ip: string;
    crumb_used?: string;
  };
}

interface TestResult {
  yfinance: YFinanceResult;
  proxy: ProxyResult;
}

export default function Home() {
  const [symbol, setSymbol] = useState('AAPL');
  const [data, setData] = useState<CandlestickData | null>(null);
  const [lastPrice, setLastPrice] = useState<LastPrice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testingYFinance, setTestingYFinance] = useState(false);
  const [proxyStatus, setProxyStatus] = useState<ProxyStatus | null>(null);

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
    setError(null);
    try {
      // First test yfinance directly
      const yfResponse = await fetch(`${API_URL}/api/test-yfinance`);
      const yfData = await yfResponse.json();
      console.log("yfinance test result:", yfData);
      
      // Then test proxy with Yahoo Finance
      const proxyResponse = await fetch(`${API_URL}/api/test-proxy-yahoo`);
      const proxyData = await proxyResponse.json();
      console.log("proxy test result:", proxyData);
      
      // If yfinance test failed but we have proxy data, try to extract info from proxy response
      if (yfData.status === "error" && proxyData.yahoo_response?.body) {
        try {
          const proxyBody = JSON.parse(proxyData.yahoo_response.body);
          const chartData = proxyBody.chart?.result?.[0];
          if (chartData?.meta) {
            yfData.status = "success";
            yfData.message = "Successfully got data from Yahoo Finance (via direct API)";
            yfData.data_source = "direct_api";
            yfData.data = {
              symbol: chartData.meta.symbol,
              current_price: chartData.meta.regularMarketPrice,
              company_name: chartData.meta.longName
            };
          }
        } catch (e) {
          console.error("Error parsing proxy response:", e);
        }
      } else if (yfData.status === "success") {
        yfData.data_source = "yfinance";
      }
      
      setTestResult({
        yfinance: yfData,
        proxy: proxyData
      });
      
      // If we got Yahoo Finance response details, show them
      if (proxyData.yahoo_response) {
        const yahooStatus = proxyData.yahoo_response.status;
        const yahooHeaders = Object.entries(proxyData.yahoo_response.headers)
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
        const requestHeaders = Object.entries(proxyData.yahoo_response.request_headers)
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
        const yahooBody = proxyData.yahoo_response.body || 'No body';
        
        setError(
          `Yahoo Finance Response:\n` +
          `Status: ${yahooStatus}\n\n` +
          `Request Headers:\n${requestHeaders}\n\n` +
          `Response Headers:\n${yahooHeaders}\n\n` +
          `Body:\n${yahooBody}`
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test yfinance');
    } finally {
      setTestingYFinance(false);
    }
  };

  const testProxyIP = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("https://test-app-wqrp.onrender.com/api/test-proxy-ip");
      const data = await response.json() as ProxyStatus;
      setProxyStatus(data);
      console.log("Proxy test result:", data);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error("Error testing proxy:", err);
    } finally {
      setLoading(false);
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
              {testingYFinance ? 'Testing...' : 'Test yfinance & Proxy'}
            </button>
          </div>
          {testResult && (
            <div className="mb-4 p-4 bg-gray-800 rounded">
              <h3 className="font-bold mb-2">Test Results:</h3>
              
              <div className="space-y-2">
                <h4 className="font-semibold text-green-400 mb-2">yfinance Test:</h4>
                <div className="bg-gray-100 p-4 rounded-lg">
                  <p className="font-medium">Status: {testResult.yfinance.status}</p>
                  <p className="text-sm text-gray-600">{testResult.yfinance.message}</p>
                  {testResult.yfinance.data_source && (
                    <p className="text-sm font-medium">
                      Data Source: <span className={testResult.yfinance.data_source === 'yfinance' ? 'text-blue-600' : 'text-purple-600'}>
                        {testResult.yfinance.data_source === 'yfinance' ? 'yfinance Library' : 'Direct Yahoo Finance API'}
                      </span>
                    </p>
                  )}
                  {testResult.yfinance.proxy_used && (
                    <p className="text-sm text-gray-600">Proxy Used: {testResult.yfinance.proxy_used}</p>
                  )}
                  {testResult.yfinance.proxy_ip && (
                    <p className="text-sm text-gray-600">Proxy IP: {testResult.yfinance.proxy_ip}</p>
                  )}
                  {testResult.yfinance.error_type && (
                    <p className="text-sm text-red-600">Error Type: {testResult.yfinance.error_type}</p>
                  )}
                  {testResult.yfinance.error_details && (
                    <pre className="text-sm text-red-600 whitespace-pre-wrap mt-2 bg-red-50 p-2 rounded">
                      {testResult.yfinance.error_details}
                    </pre>
                  )}
                  {testResult.yfinance.data && (
                    <pre className="text-sm mt-2 bg-green-50 p-2 rounded">
                      {JSON.stringify(testResult.yfinance.data, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold text-blue-400 mb-2">Proxy Test:</h4>
                <div className="mb-2">
                  <span className="font-semibold">Status:</span> {testResult.proxy.status}
                </div>
                <div className="mb-2">
                  <span className="font-semibold">Proxy Used:</span> {testResult.proxy.proxy_used}
                </div>
                {testResult.proxy.proxy_ip && (
                  <div className="mb-2">
                    <span className="font-semibold">Proxy IP:</span> {testResult.proxy.proxy_ip}
                  </div>
                )}
              </div>
            </div>
          )}
          {error && (
            <div className="mt-4 p-4 bg-red-900/50 rounded">
              <h3 className="font-bold mb-2 text-red-400">Response Details:</h3>
              <pre className="whitespace-pre-wrap font-mono text-sm text-red-200">
                {error}
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

        <div className="mb-8 p-4 border rounded-lg bg-gray-50 w-full max-w-md">
          <h2 className="text-xl font-semibold mb-4">Proxy Connection Test</h2>
          <button
            onClick={testProxyIP}
            disabled={loading}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400"
          >
            {loading ? "Testing..." : "Test Proxy Connection"}
          </button>
          
          {proxyStatus && (
            <div className="mt-4 text-sm">
              <p>Direct IP: {proxyStatus.direct_ip}</p>
              <p>Proxy IP: {proxyStatus.proxy_ip}</p>
              <p className={proxyStatus.ips_match ? "text-red-500" : "text-green-500"}>
                {proxyStatus.ips_match 
                  ? "⚠️ Proxy not working (IPs match)" 
                  : "✅ Proxy working (different IPs)"}
              </p>
            </div>
          )}
          
          {error && (
            <div className="mt-4 text-red-500 text-sm">
              Error: {error}
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
