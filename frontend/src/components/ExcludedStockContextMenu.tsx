import { useState } from "react";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useReincludeStock } from "@/hooks/useExcludedStocks";
import { RotateCcw } from "lucide-react";

interface ExcludedStockContextMenuProps {
  children: React.ReactNode;
  symbol: string;
}

export function ExcludedStockContextMenu({
  children,
  symbol,
}: ExcludedStockContextMenuProps) {
  const reincludeStock = useReincludeStock();

  const handleReinclude = () => {
    reincludeStock.mutate(symbol);
  };

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="bg-slate-800 border-slate-600">
        <ContextMenuItem
          onClick={handleReinclude}
          disabled={reincludeStock.isPending}
          className="text-slate-200 hover:bg-slate-700 focus:bg-slate-700 cursor-pointer"
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Re-include in results
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
