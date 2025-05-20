import { Data, Layout } from 'plotly.js';

export interface CandlestickData {
  dates: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
}

export interface MarketStatus {
  is_open: boolean;
  timezone: string;
  current_time: string;
  market_hours: {
    open: string;
    close: string;
  };
}

// Plotly specific types
export type PlotData = Partial<Data>[];
export type PlotLayout = Partial<Layout> & {
  template?: string | Partial<Layout>;
  paper_bgcolor?: string;
  plot_bgcolor?: string;
  font?: {
    color?: string;
  };
}; 