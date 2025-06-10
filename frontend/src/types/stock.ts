export interface StockData {
  symbol: string;
  company_name: string;
  exchange: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap: number;
  pe_ratio?: number;
  last_updated: string;
}

export interface TTMSqueezeStock extends StockData {
  squeeze_days: number;
  bollinger_bands: {
    upper: number;
    lower: number;
    middle: number;
  };
  keltner_channels: {
    upper: number;
    lower: number;
    middle: number;
  };
  momentum: number;
  squeeze_intensity: "low" | "medium" | "high";
}

export interface VolumeSpikeStock extends StockData {
  spike_days: number;
  volume_ratio: number;
  avg_volume_30d: number;
  consecutive_days: number;
  spike_intensity: "moderate" | "high" | "extreme";
}

export interface SavedStock {
  id: string;
  symbol: string;
  company_name: string;
  saved_at: string;
  notes?: string;
  tags: string[];
}

export interface StockFilters {
  min_price?: number;
  max_price?: number;
  min_market_cap?: number;
  max_market_cap?: number;
  min_volume?: number;
  exchanges: string[];
  sectors: string[];
  country: "US" | "AU";
}

export interface APIResponse<T> {
  data: T[];
  total_count: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

export interface StockAnalysis {
  ttm_squeeze: TTMSqueezeStock[];
  volume_spikes: VolumeSpikeStock[];
  last_updated: string;
}
