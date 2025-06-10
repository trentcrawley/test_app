import { ColumnDef } from "@tanstack/react-table";
import { SavedStock } from "@/types/stock";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDeleteStock } from "@/hooks/useStocks";
import { Trash2, Clock } from "lucide-react";
import { format } from "date-fns";

interface SavedStocksTableProps {
  data: SavedStock[];
  isLoading?: boolean;
}

export function SavedStocksTable({ data, isLoading }: SavedStocksTableProps) {
  const deleteStock = useDeleteStock();

  const columns: ColumnDef<SavedStock>[] = [
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
      accessorKey: "notes",
      header: "Notes",
      cell: ({ row }) => {
        const notes = row.getValue("notes") as string;
        return notes ? (
          <div className="max-w-[300px] truncate text-sm text-slate-400">
            {notes}
          </div>
        ) : (
          <span className="text-slate-500 text-sm italic">No notes</span>
        );
      },
    },
    {
      accessorKey: "saved_at",
      header: "Saved At",
      cell: ({ row }) => {
        const savedAt = row.getValue("saved_at") as string;
        return (
          <div className="flex items-center gap-1 text-sm text-slate-400">
            <Clock className="h-3 w-3" />
            {format(new Date(savedAt), "MMM dd, yyyy")}
          </div>
        );
      },
    },
    {
      accessorKey: "tags",
      header: "Tags",
      cell: ({ row }) => {
        const tags = row.getValue("tags") as string[];
        return (
          <div className="flex gap-1 flex-wrap">
            {tags?.map((tag, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {(!tags || tags.length === 0) && (
              <span className="text-slate-500 text-sm italic">No tags</span>
            )}
          </div>
        );
      },
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const stock = row.original;
        return (
          <Button
            size="sm"
            variant="outline"
            className="bg-market-bear/10 border-market-bear text-market-bear hover:bg-market-bear hover:text-white"
            onClick={() => deleteStock.mutate(stock.id)}
            disabled={deleteStock.isPending}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
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
            <span className="text-slate-400">Loading saved stocks...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-200">Saved Stocks</h3>
          <p className="text-sm text-slate-400">
            Your watchlist of saved stocks
          </p>
        </div>
        <Badge className="bg-market-neutral/20 text-market-neutral">
          {data.length} stocks saved
        </Badge>
      </div>
      <DataTable columns={columns} data={data} pageSize={10} />
    </div>
  );
}
