import {
  StockAnalysis,
  SavedStock,
  StockFilters,
  APIResponse,
} from "@/types/stock";
import { excludedStocksService } from "@/hooks/useExcludedStocks";

class StockApiService {
  private baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  async getStockAnalysis(filters?: StockFilters): Promise<StockAnalysis> {
    try {
      const country = filters?.country || "US";
      
      // Fetch scheduled market scanner results
      const response = await fetch(`${this.baseUrl}/api/market-scanner/results/${country}`);
      
      if (!response.ok) {
        // If no scheduled results, return empty data
        console.warn(`No scheduled results for ${country}`);
        return {
          ttm_squeeze: [],
          volume_spikes: [],
          last_updated: new Date().toISOString(),
        };
      }
      
      const scheduledData = await response.json();
      
      // Transform scheduled results to match StockAnalysis interface
      const ttmSqueezeData = scheduledData.ttm_squeeze || [];
      const volumeSpikeData = scheduledData.volume_spikes || [];
      
      // Get excluded stocks
      const excludedStocks = excludedStocksService.getExcludedStocks();
      const excludedSymbols = new Set(
        excludedStocks.map((stock) => stock.symbol),
      );
      
      // Filter out excluded stocks
      const filteredTTMSqueezeData = ttmSqueezeData.filter(
        (stock: any) => !excludedSymbols.has(stock.symbol),
      );
      
      return {
        ttm_squeeze: filteredTTMSqueezeData,
        volume_spikes: volumeSpikeData,
        last_updated: scheduledData.last_updated || new Date().toISOString(),
      };
      
    } catch (error) {
      console.error("Error fetching scheduled data:", error);
      // Return empty data on error
      return {
        ttm_squeeze: [],
        volume_spikes: [],
        last_updated: new Date().toISOString(),
      };
    }
  }

  async refreshData(): Promise<StockAnalysis> {
    // Try to trigger a manual scan and then fetch results
    try {
      const country = "US"; // Default to US for refresh
      await fetch(`${this.baseUrl}/api/market-scanner/run/${country}`, {
        method: 'GET',
      });
      
      // Wait a bit for the scan to complete
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Fetch the updated results
      return this.getStockAnalysis({ 
        country: country as "US" | "AU",
        exchanges: [],
        sectors: []
      });
    } catch (error) {
      console.error("Error refreshing data:", error);
      // Return empty data on error
      return {
        ttm_squeeze: [],
        volume_spikes: [],
        last_updated: new Date().toISOString(),
      };
    }
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
