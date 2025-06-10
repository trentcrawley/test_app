import {
  StockAnalysis,
  SavedStock,
  StockFilters,
  APIResponse,
} from "@/types/stock";
import { excludedStocksService } from "@/hooks/useExcludedStocks";

// Mock data for development - replace with real API calls
const generateMockTTMSqueezeData = (country: "US" | "AU" = "US") => {
  const usSymbols = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "TSLA",
    "META",
    "NVDA",
    "NFLX",
    "CRM",
    "AMD",
  ];

  const auSymbols = [
    "CBA.AX",
    "BHP.AX",
    "CSL.AX",
    "ANZ.AX",
    "WBC.AX",
    "NAB.AX",
    "WOW.AX",
    "MQG.AX",
    "TLS.AX",
    "RIO.AX",
  ];

  const symbols = country === "AU" ? auSymbols : usSymbols;
  const exchange = country === "AU" ? "ASX" : "NASDAQ";
  return symbols.map((symbol, index) => ({
    symbol,
    company_name: `${symbol.replace(".AX", "")} ${country === "AU" ? "Ltd" : "Company Inc."}`,
    exchange,
    price: 150 + Math.random() * 200,
    change: (Math.random() - 0.5) * 10,
    change_percent: (Math.random() - 0.5) * 5,
    volume: Math.floor(Math.random() * 50000000) + 1000000,
    market_cap: Math.floor(Math.random() * 1000000000000) + 100000000000,
    pe_ratio: Math.random() * 30 + 5,
    last_updated: new Date().toISOString(),
    squeeze_days: Math.floor(Math.random() * 15) + 5,
    bollinger_bands: {
      upper: 160 + Math.random() * 20,
      lower: 140 + Math.random() * 20,
      middle: 150 + Math.random() * 20,
    },
    keltner_channels: {
      upper: 155 + Math.random() * 20,
      lower: 145 + Math.random() * 20,
      middle: 150 + Math.random() * 20,
    },
    momentum: (Math.random() - 0.5) * 2,
    squeeze_intensity: ["low", "medium", "high"][
      Math.floor(Math.random() * 3)
    ] as "low" | "medium" | "high",
  }));
};

const generateMockVolumeSpikeData = (country: "US" | "AU" = "US") => {
  const usSymbols = [
    "ROKU",
    "SQ",
    "SHOP",
    "ZM",
    "PTON",
    "DOCU",
    "ZOOM",
    "PLTR",
    "SNOW",
    "COIN",
  ];

  const auSymbols = [
    "AFI.AX",
    "ALL.AX",
    "ALU.AX",
    "AMP.AX",
    "APT.AX",
    "ASX.AX",
    "AZJ.AX",
    "BEN.AX",
    "CPU.AX",
    "FMG.AX",
  ];

  const symbols = country === "AU" ? auSymbols : usSymbols;
  return symbols.map((symbol, index) => ({
    symbol,
    company_name: `${symbol.replace(".AX", "")} ${country === "AU" ? "Ltd" : "Corporation"}`,
    exchange:
      country === "AU" ? "ASX" : Math.random() > 0.5 ? "NASDAQ" : "NYSE",
    price: 50 + Math.random() * 300,
    change: (Math.random() - 0.5) * 15,
    change_percent: (Math.random() - 0.5) * 8,
    volume: Math.floor(Math.random() * 100000000) + 5000000,
    market_cap: Math.floor(Math.random() * 500000000000) + 50000000000,
    pe_ratio: Math.random() * 40 + 3,
    last_updated: new Date().toISOString(),
    spike_days: 3,
    volume_ratio: Math.random() * 20 + 10,
    avg_volume_30d: Math.floor(Math.random() * 10000000) + 1000000,
    consecutive_days: 3,
    spike_intensity: ["moderate", "high", "extreme"][
      Math.floor(Math.random() * 3)
    ] as "moderate" | "high" | "extreme",
  }));
};

class StockApiService {
  private baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  async getStockAnalysis(filters?: StockFilters): Promise<StockAnalysis> {
    // Simulate API delay
    await new Promise((resolve) =>
      setTimeout(resolve, 1000 + Math.random() * 1000),
    );

    // Get excluded stocks
    const excludedStocks = excludedStocksService.getExcludedStocks();
    const excludedSymbols = new Set(
      excludedStocks.map((stock) => stock.symbol),
    );

    // Generate mock data and filter out excluded stocks
    const country = filters?.country || "US";
    const allTTMSqueezeData = generateMockTTMSqueezeData(country);
    const filteredTTMSqueezeData = allTTMSqueezeData.filter(
      (stock) => !excludedSymbols.has(stock.symbol),
    );

    // Mock implementation - replace with real API call
    return {
      ttm_squeeze: filteredTTMSqueezeData,
      volume_spikes: generateMockVolumeSpikeData(country),
      last_updated: new Date().toISOString(),
    };
  }

  async refreshData(): Promise<StockAnalysis> {
    // Simulate refresh with slight delay
    await new Promise((resolve) => setTimeout(resolve, 800));
    return this.getStockAnalysis();
  }

  async saveStock(
    symbol: string,
    companyName: string,
    notes?: string,
  ): Promise<SavedStock> {
    // Mock implementation - this will be replaced with real API call
    const savedStock: SavedStock = {
      id: `saved_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      symbol,
      company_name: companyName,
      saved_at: new Date().toISOString(),
      notes,
      tags: [],
    };

    // Get existing saved stocks from localStorage
    const existingSaved = this.getSavedStocks();
    const updatedSaved = [...existingSaved, savedStock];
    localStorage.setItem("saved_stocks", JSON.stringify(updatedSaved));

    return savedStock;
  }

  async deleteStock(stockId: string): Promise<void> {
    // Mock implementation - this will be replaced with real API call
    const existingSaved = this.getSavedStocks();
    const updatedSaved = existingSaved.filter((stock) => stock.id !== stockId);
    localStorage.setItem("saved_stocks", JSON.stringify(updatedSaved));
  }

  getSavedStocks(): SavedStock[] {
    try {
      const saved = localStorage.getItem("saved_stocks");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  }

  async searchStocks(query: string): Promise<APIResponse<any>> {
    // Mock search implementation
    await new Promise((resolve) => setTimeout(resolve, 500));

    return {
      data: [],
      total_count: 0,
      page: 1,
      per_page: 20,
      has_more: false,
    };
  }
}

export const stockApi = new StockApiService();
export default stockApi;
