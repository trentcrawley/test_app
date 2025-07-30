import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { stockApi } from "@/services/stockApi";
import { StockFilters, SavedStock } from "@/types/stock";
import { toast } from "@/hooks/use-toast";

export const useStockAnalysis = (filters?: StockFilters) => {
  return useQuery({
    queryKey: ["stock-analysis", filters],
    queryFn: () => stockApi.getStockAnalysis(filters),
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 15000, // Consider data stale after 15 seconds
  });
};

export const useRefreshStockData = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => stockApi.refreshData(),
    onSuccess: (data) => {
      queryClient.setQueryData(["stock-analysis"], data);
      toast({
        title: "Data Refreshed",
        description: "Stock analysis data has been updated successfully.",
      });
    },
    onError: (error) => {
      toast({
        title: "Refresh Failed",
        description: "Failed to refresh stock data. Please try again.",
        variant: "destructive",
      });
    },
  });
};

export const useSaveStock = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      symbol,
      companyName,
      notes,
    }: {
      symbol: string;
      companyName: string;
      notes?: string;
    }) => stockApi.saveStock(symbol, companyName, notes),
    onSuccess: (savedStock) => {
      // Update the saved stocks cache
      queryClient.invalidateQueries({ queryKey: ["saved-stocks"] });
      toast({
        title: "Stock Saved",
        description: `${savedStock.symbol} has been added to your watchlist.`,
      });
    },
    onError: (error) => {
      toast({
        title: "Save Failed",
        description: "Failed to save stock. Please try again.",
        variant: "destructive",
      });
    },
  });
};

export const useDeleteStock = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (stockId: string) => stockApi.deleteStock(stockId),
    onSuccess: () => {
      // Update the saved stocks cache
      queryClient.invalidateQueries({ queryKey: ["saved-stocks"] });
      toast({
        title: "Stock Removed",
        description: "Stock has been removed from your watchlist.",
      });
    },
    onError: (error) => {
      toast({
        title: "Delete Failed",
        description: "Failed to delete stock. Please try again.",
        variant: "destructive",
      });
    },
  });
};

export const useSavedStocks = () => {
  return useQuery({
    queryKey: ["saved-stocks"],
    queryFn: () => stockApi.getSavedStocks(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export interface ScanParameters {
  min_turnover_us?: number;
  min_turnover_au?: number;
  min_squeeze_days?: number;
  min_volume_spike_ratio_us?: number;
  min_volume_spike_ratio_au?: number;
}

export const useTriggerMarketScan = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ country, params, signal }: { country: "US" | "AU"; params?: ScanParameters; signal?: AbortSignal }) => {
      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const queryParams = new URLSearchParams();
      
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined) {
            queryParams.append(key, value.toString());
          }
        });
      }
      
      const url = `${baseUrl}/api/market-scanner/run/${country}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      const response = await fetch(url, { 
        signal,
        method: 'GET'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to trigger ${country} scan: ${response.statusText}`);
      }
      return response.json();
    },
    onSuccess: (data, { country }) => {
      // Invalidate the stock analysis query to refresh data
      queryClient.invalidateQueries({ queryKey: ["stock-analysis"] });
      toast({
        title: "Scan Completed",
        description: `${country} market scan completed successfully. Found ${data.ttm_squeeze_count || 0} TTM squeeze signals and ${data.volume_spike_count || 0} volume spikes.`,
      });
    },
    onError: (error: Error, { country }) => {
      toast({
        title: "Scan Failed",
        description: `Failed to complete ${country} market scan: ${error.message}`,
        variant: "destructive",
      });
    },
  });
};
