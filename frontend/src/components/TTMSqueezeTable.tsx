import { useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { TTMSqueezeStock } from "@/types/stock";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useExcludeStock } from "@/hooks/useExcludedStocks";
import { StockChart } from "@/components/StockChart";
import { ExcludedStocksDisplay } from "@/components/ExcludedStocksDisplay";
import { ArrowUpRight, ArrowDownRight, TrendingUp, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface TTMSqueezeTableProps {
  data: TTMSqueezeStock[];
  isLoading?: boolean;
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
};

const formatNumber = (value: number) => {
  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(1)}B`;
  }
  if (value >= 1e6) {
    return `${(value / 1e6).toFixed(1)}M`;
  }
  if (value >= 1e3) {
    return `${(value / 1e3).toFixed(1)}K`;
  }
  return value.toLocaleString();
};

export function TTMSqueezeTable({ data, isLoading }: TTMSqueezeTableProps) {
  const [selectedStock, setSelectedStock] = useState<TTMSqueezeStock | null>(
    null,
  );
  const excludeStock = useExcludeStock();

  const columns: ColumnDef<TTMSqueezeStock>[] = [
    {
      accessorKey: "symbol",
      header: "Symbol",
      cell: ({ row }) => (
        <div className="font-mono font-bold text-financial-primary">
          {row.getValue("symbol")}
        </div>
      ),
    },
    {
      accessorKey: "company_name",
      header: "Company",
      cell: ({ row }) => (
        <div className="max-w-[200px] truncate">
          {row.getValue("company_name")}
        </div>
      ),
    },
    {
      accessorKey: "price",
      header: "Price",
      cell: ({ row }) => (
        <div className="font-mono">{formatCurrency(row.getValue("price"))}</div>
      ),
    },
    {
      accessorKey: "change_percent",
      header: "Change %",
      cell: ({ row }) => {
        const change = row.getValue("change_percent") as number;
        return (
          <div
            className={cn(
              "flex items-center gap-1 font-mono",
              change >= 0 ? "text-market-bull" : "text-market-bear",
            )}
          >
            {change >= 0 ? (
              <ArrowUpRight className="h-4 w-4" />
            ) : (
              <ArrowDownRight className="h-4 w-4" />
            )}
            {change >= 0 ? "+" : ""}
            {change.toFixed(2)}%
          </div>
        );
      },
    },
    {
      accessorKey: "squeeze_days",
      header: "Squeeze Days",
      cell: ({ row }) => (
        <Badge
          variant="outline"
          className="bg-financial-primary/10 text-financial-primary border-financial-primary"
        >
          {row.getValue("squeeze_days")} days
        </Badge>
      ),
    },
    {
      accessorKey: "squeeze_intensity",
      header: "Intensity",
      cell: ({ row }) => {
        const intensity = row.getValue("squeeze_intensity") as string;
        const colorMap = {
          low: "bg-yellow-500/10 text-yellow-500 border-yellow-500",
          medium: "bg-orange-500/10 text-orange-500 border-orange-500",
          high: "bg-red-500/10 text-red-500 border-red-500",
        };
        return (
          <Badge
            variant="outline"
            className={colorMap[intensity as keyof typeof colorMap]}
          >
            {intensity.toUpperCase()}
          </Badge>
        );
      },
    },
    {
      accessorKey: "volume",
      header: "Volume",
      cell: ({ row }) => (
        <div className="font-mono text-sm">
          {formatNumber(row.getValue("volume"))}
        </div>
      ),
    },
    {
      accessorKey: "market_cap",
      header: "Market Cap",
      cell: ({ row }) => (
        <div className="font-mono text-sm">
          {formatNumber(row.getValue("market_cap"))}
        </div>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const stock = row.original;
        return (
          <div className="flex gap-1">
            <Button
              size="sm"
              variant="outline"
              className="bg-financial-primary/10 border-financial-primary text-financial-primary hover:bg-financial-primary hover:text-white"
              onClick={() => setSelectedStock(stock)}
            >
              <TrendingUp className="h-3 w-3 mr-1" />
              Chart
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="bg-slate-600/10 border-slate-600 text-slate-400 hover:bg-slate-600 hover:text-white"
              onClick={() =>
                excludeStock.mutate({
                  symbol: stock.symbol,
                  companyName: stock.company_name,
                  reason: `Excluded from TTM Squeeze - ${stock.squeeze_intensity} intensity, ${stock.squeeze_days} days`,
                })
              }
              disabled={excludeStock.isPending}
            >
              <EyeOff className="h-3 w-3 mr-1" />
              Exclude
            </Button>
          </div>
        );
      },
    },
  ];

  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800/50 backdrop-blur-sm p-8">
        <div className="flex items-center justify-center">
          <div className="flex items-center gap-3">
            <div className="animate-spin h-6 w-6 border-2 border-financial-primary border-t-transparent rounded-full"></div>
            <span className="text-slate-400">Loading TTM Squeeze data...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Chart Modal */}
      {selectedStock && (
        <div className="mb-6">
          <StockChart
            stock={selectedStock}
            onClose={() => setSelectedStock(null)}
          />
        </div>
      )}

      {/* Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-200">
              TTM Squeeze Signals
            </h3>
            <p className="text-sm text-slate-400">
              Stocks squeezed for over 5 days - potential breakout candidates
            </p>
          </div>
          <Badge className="bg-financial-primary/20 text-financial-primary">
            {data.length} stocks found
          </Badge>
        </div>
        <DataTable columns={columns} data={data} pageSize={10} />
      </div>

      {/* Excluded Stocks Display */}
      <ExcludedStocksDisplay />
    </div>
  );
}
