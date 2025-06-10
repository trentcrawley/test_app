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
