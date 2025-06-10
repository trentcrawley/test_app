import { useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { VolumeSpikeStock } from "@/types/stock";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSaveStock } from "@/hooks/useStocks";
import { SavedStocksDisplaySimple } from "@/components/SavedStocksDisplaySimple";
import { VolumeSpikeChart } from "@/components/VolumeSpikeChart";
import {
  ArrowUpRight,
  ArrowDownRight,
  Save,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface VolumeSpikeTableProps {
  data: VolumeSpikeStock[];
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

export function VolumeSpikeTable({ data, isLoading }: VolumeSpikeTableProps) {
  const [selectedStock, setSelectedStock] = useState<VolumeSpikeStock | null>(
    null,
  );
  const saveStock = useSaveStock();

  const columns: ColumnDef<VolumeSpikeStock>[] = [
    {
      accessorKey: "symbol",
      header: "Symbol",
      cell: ({ row }) => (
        <div className="font-mono font-bold text-financial-secondary">
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
      accessorKey: "volume_ratio",
      header: "Volume Ratio",
      cell: ({ row }) => {
        const ratio = row.getValue("volume_ratio") as number;
        return (
          <div className="flex items-center gap-1">
            <TrendingUp className="h-4 w-4 text-financial-secondary" />
            <span className="font-mono font-bold text-financial-secondary">
              {ratio.toFixed(1)}x
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: "consecutive_days",
      header: "Spike Days",
      cell: ({ row }) => (
        <Badge
          variant="outline"
          className="bg-financial-secondary/10 text-financial-secondary border-financial-secondary"
        >
          {row.getValue("consecutive_days")} days
        </Badge>
      ),
    },
    {
      accessorKey: "spike_intensity",
      header: "Intensity",
      cell: ({ row }) => {
        const intensity = row.getValue("spike_intensity") as string;
        const colorMap = {
          moderate: "bg-blue-500/10 text-blue-500 border-blue-500",
          high: "bg-orange-500/10 text-orange-500 border-orange-500",
          extreme: "bg-red-500/10 text-red-500 border-red-500",
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
      header: "Current Volume",
      cell: ({ row }) => (
        <div className="font-mono text-sm">
          {formatNumber(row.getValue("volume"))}
        </div>
      ),
    },
    {
      accessorKey: "avg_volume_30d",
      header: "30D Avg Volume",
      cell: ({ row }) => (
        <div className="font-mono text-sm text-slate-400">
          {formatNumber(row.getValue("avg_volume_30d"))}
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
              className="bg-financial-secondary/10 border-financial-secondary text-financial-secondary hover:bg-financial-secondary hover:text-white"
              onClick={() => setSelectedStock(stock)}
            >
              <BarChart3 className="h-3 w-3 mr-1" />
              Chart
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="bg-financial-primary/10 border-financial-primary text-financial-primary hover:bg-financial-primary hover:text-white"
              onClick={() =>
                saveStock.mutate({
                  symbol: stock.symbol,
                  companyName: stock.company_name,
                  notes: `Volume Spike: ${stock.volume_ratio.toFixed(1)}x for ${stock.consecutive_days} days, Intensity: ${stock.spike_intensity}`,
                })
              }
              disabled={saveStock.isPending}
            >
              <Save className="h-3 w-3 mr-1" />
              Save
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
            <div className="animate-spin h-6 w-6 border-2 border-financial-secondary border-t-transparent rounded-full"></div>
            <span className="text-slate-400">Loading volume spike data...</span>
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
          <VolumeSpikeChart
            stock={selectedStock}
            onClose={() => setSelectedStock(null)}
          />
        </div>
      )}

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-200">
              Volume Spike Alerts
            </h3>
            <p className="text-sm text-slate-400">
              Stocks with 3+ days of volume &gt;10x their 30-day average
            </p>
          </div>
          <Badge className="bg-financial-secondary/20 text-financial-secondary">
            {data.length} stocks found
          </Badge>
        </div>
        <DataTable columns={columns} data={data} pageSize={8} />
      </div>

      {/* Saved Stocks Display */}
      <SavedStocksDisplaySimple />
    </div>
  );
}
