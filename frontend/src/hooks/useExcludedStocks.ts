import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "@/hooks/use-toast";

export interface ExcludedStock {
  symbol: string;
  company_name: string;
  excluded_at: string;
  reason?: string;
}

class ExcludedStocksService {
  private storageKey = "excluded_stocks";

  getExcludedStocks(): ExcludedStock[] {
    try {
      const excluded = localStorage.getItem(this.storageKey);
      return excluded ? JSON.parse(excluded) : [];
    } catch {
      return [];
    }
  }

  addExcludedStock(
    symbol: string,
    companyName: string,
    reason?: string,
  ): ExcludedStock {
    const existingExcluded = this.getExcludedStocks();

    // Remove if already exists (to update timestamp)
    const filteredExcluded = existingExcluded.filter(
      (stock) => stock.symbol !== symbol,
    );

    const excludedStock: ExcludedStock = {
      symbol,
      company_name: companyName,
      excluded_at: new Date().toISOString(),
      reason: reason || "User excluded from TTM Squeeze results",
    };

    const updatedExcluded = [...filteredExcluded, excludedStock];
    localStorage.setItem(this.storageKey, JSON.stringify(updatedExcluded));

    return excludedStock;
  }

  removeExcludedStock(symbol: string): void {
    const existingExcluded = this.getExcludedStocks();
    const updatedExcluded = existingExcluded.filter(
      (stock) => stock.symbol !== symbol,
    );
    localStorage.setItem(this.storageKey, JSON.stringify(updatedExcluded));
  }

  isStockExcluded(symbol: string): boolean {
    const excludedStocks = this.getExcludedStocks();
    return excludedStocks.some((stock) => stock.symbol === symbol);
  }
}

const excludedStocksService = new ExcludedStocksService();

export const useExcludedStocks = () => {
  return useQuery({
    queryKey: ["excluded-stocks"],
    queryFn: () => excludedStocksService.getExcludedStocks(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useExcludeStock = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      symbol,
      companyName,
      reason,
    }: {
      symbol: string;
      companyName: string;
      reason?: string;
    }) => excludedStocksService.addExcludedStock(symbol, companyName, reason),
    onSuccess: (excludedStock) => {
      // Update excluded stocks cache
      queryClient.invalidateQueries({ queryKey: ["excluded-stocks"] });
      // Refresh stock analysis to remove excluded stock
      queryClient.invalidateQueries({ queryKey: ["stock-analysis"] });

      toast({
        title: "Stock Excluded",
        description: `${excludedStock.symbol} has been excluded from future TTM Squeeze results.`,
      });
    },
    onError: (error) => {
      toast({
        title: "Exclusion Failed",
        description: "Failed to exclude stock. Please try again.",
        variant: "destructive",
      });
    },
  });
};

export const useReincludeStock = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (symbol: string) => {
      excludedStocksService.removeExcludedStock(symbol);
      return symbol;
    },
    onSuccess: (symbol) => {
      // Update excluded stocks cache
      queryClient.invalidateQueries({ queryKey: ["excluded-stocks"] });
      // Refresh stock analysis to potentially re-include the stock
      queryClient.invalidateQueries({ queryKey: ["stock-analysis"] });

      toast({
        title: "Stock Re-included",
        description: `${symbol} will now appear in TTM Squeeze results again.`,
      });
    },
    onError: (error) => {
      toast({
        title: "Re-inclusion Failed",
        description: "Failed to re-include stock. Please try again.",
        variant: "destructive",
      });
    },
  });
};

export const useIsStockExcluded = (symbol: string) => {
  const { data: excludedStocks } = useExcludedStocks();
  return excludedStocks?.some((stock) => stock.symbol === symbol) || false;
};

export { excludedStocksService };
