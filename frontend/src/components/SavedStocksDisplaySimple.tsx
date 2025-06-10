import { useSavedStocks, useDeleteStock } from "@/hooks/useStocks";
import { Bookmark, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface SavedStockContextMenuProps {
  children: React.ReactNode;
  stockId: string;
}

function SavedStockContextMenu({
  children,
  stockId,
}: SavedStockContextMenuProps) {
  const deleteStock = useDeleteStock();

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    deleteStock.mutate(stockId);
  };

  return (
    <span
      onContextMenu={handleDelete}
      className="cursor-pointer"
      title="Right-click to remove"
    >
      {children}
    </span>
  );
}

export function SavedStocksDisplaySimple() {
  const { data: savedStocks, isLoading } = useSavedStocks();

  if (isLoading || !savedStocks || savedStocks.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <Bookmark className="h-4 w-4 text-slate-400" />
        <h4 className="text-sm font-medium text-slate-300">Saved Stocks</h4>
        <Badge
          variant="outline"
          className="text-xs bg-slate-700 text-slate-400"
        >
          {savedStocks.length} saved
        </Badge>
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        {savedStocks.map((stock) => (
          <SavedStockContextMenu key={stock.id} stockId={stock.id}>
            <span className="inline-block px-1 py-0.5 bg-financial-secondary/20 rounded text-xs text-financial-secondary hover:bg-financial-secondary/30 cursor-pointer transition-colors font-mono">
              {stock.symbol}
            </span>
          </SavedStockContextMenu>
        ))}
      </div>

      <div className="flex items-start gap-2 text-xs text-slate-500">
        <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
        <p>
          Right-click any saved stock to remove it from your watchlist. These
          stocks were saved from volume spike alerts.
        </p>
      </div>
    </div>
  );
}
