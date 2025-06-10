import { useExcludedStocks } from "@/hooks/useExcludedStocks";
import { ExcludedStockContextMenu } from "@/components/ExcludedStockContextMenu";
import { Badge } from "@/components/ui/badge";
import { EyeOff, Info } from "lucide-react";
import { format } from "date-fns";

export function ExcludedStocksDisplay() {
  const { data: excludedStocks, isLoading } = useExcludedStocks();

  if (isLoading || !excludedStocks || excludedStocks.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <EyeOff className="h-4 w-4 text-slate-400" />
        <h4 className="text-sm font-medium text-slate-300">Excluded Stocks</h4>
        <Badge
          variant="outline"
          className="text-xs bg-slate-700 text-slate-400"
        >
          {excludedStocks.length} excluded
        </Badge>
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        {excludedStocks.map((stock) => (
          <ExcludedStockContextMenu key={stock.symbol} symbol={stock.symbol}>
            <span className="inline-block px-1 py-0.5 bg-slate-700/30 rounded text-xs text-slate-500 hover:bg-slate-700/50 cursor-pointer transition-colors font-mono">
              {stock.symbol}
            </span>
          </ExcludedStockContextMenu>
        ))}
      </div>

      <div className="flex items-start gap-2 text-xs text-slate-500">
        <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
        <p>
          Right-click any excluded stock to re-include it in future TTM Squeeze
          results. Excluded stocks are filtered out to help you focus on new
          opportunities.
        </p>
      </div>
    </div>
  );
}
