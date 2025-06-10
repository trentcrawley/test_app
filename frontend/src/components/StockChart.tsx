import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { stockApi } from "@/services/stockApi";
import { TTMSqueezeStock } from "@/types/stock";
import { format } from "date-fns";
import { TrendingUp, X, Calendar } from "lucide-react";

interface StockChartProps {
  stock: TTMSqueezeStock;
  onClose: () => void;
}

interface ChartDataPoint {
  date: string;
  price: number;
  volume: number;
  bollinger_upper: number;
  bollinger_lower: number;
  keltner_upper: number;
  keltner_lower: number;
  squeeze_active: boolean;
}

const generateMockChartData = (stock: TTMSqueezeStock): ChartDataPoint[] => {
  const data: ChartDataPoint[] = [];
  const basePrice = stock.price;
  const days = 30;

  for (let i = days; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);

    // Generate realistic price movement
    const priceVariation = (Math.random() - 0.5) * 10;
    const price = basePrice + priceVariation;

    // Generate Bollinger Bands (20-period, 2 std dev)
    const bollinger_upper = price + Math.random() * 15;
    const bollinger_lower = price - Math.random() * 15;

    // Generate Keltner Channels (20-period, 2 ATR)
    const keltner_upper = price + Math.random() * 12;
    const keltner_lower = price - Math.random() * 12;

    // Squeeze occurs when Bollinger Bands are inside Keltner Channels
    const squeeze_active =
      bollinger_upper < keltner_upper && bollinger_lower > keltner_lower;

    data.push({
      date: format(date, "MMM dd"),
      price: Number(price.toFixed(2)),
      volume: Math.floor(Math.random() * 50000000) + 10000000,
      bollinger_upper: Number(bollinger_upper.toFixed(2)),
      bollinger_lower: Number(bollinger_lower.toFixed(2)),
      keltner_upper: Number(keltner_upper.toFixed(2)),
      keltner_lower: Number(keltner_lower.toFixed(2)),
      squeeze_active,
    });
  }

  return data;
};

const useStockChartData = (symbol: string) => {
  return useQuery({
    queryKey: ["stock-chart", symbol],
    queryFn: async () => {
      // This will be replaced with real EODHD API call
      await new Promise((resolve) => setTimeout(resolve, 800));
      return generateMockChartData({} as TTMSqueezeStock);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 shadow-xl">
        <p className="text-slate-200 font-medium mb-2">{label}</p>
        <div className="space-y-1 text-sm">
          <p className="text-financial-primary">
            Price: ${data.price?.toFixed(2)}
          </p>
          <p className="text-blue-400">
            BB Upper: ${data.bollinger_upper?.toFixed(2)}
          </p>
          <p className="text-blue-400">
            BB Lower: ${data.bollinger_lower?.toFixed(2)}
          </p>
          <p className="text-orange-400">
            KC Upper: ${data.keltner_upper?.toFixed(2)}
          </p>
          <p className="text-orange-400">
            KC Lower: ${data.keltner_lower?.toFixed(2)}
          </p>
          {data.squeeze_active && (
            <Badge className="bg-red-500/20 text-red-400 text-xs">
              Squeeze Active
            </Badge>
          )}
        </div>
      </div>
    );
  }
  return null;
};

export function StockChart({ stock, onClose }: StockChartProps) {
  const { data: chartData, isLoading, error } = useStockChartData(stock.symbol);

  if (isLoading) {
    return (
      <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-financial-primary" />
            <CardTitle className="text-lg">
              {stock.symbol} - Technical Chart
            </CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="h-96 flex items-center justify-center">
            <div className="flex items-center gap-3">
              <div className="animate-spin h-6 w-6 border-2 border-financial-primary border-t-transparent rounded-full"></div>
              <span className="text-slate-400">Loading chart data...</span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-financial-primary" />
            <CardTitle className="text-lg">
              {stock.symbol} - Technical Chart
            </CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="h-96 flex items-center justify-center">
            <div className="text-center">
              <p className="text-market-bear mb-2">Failed to load chart data</p>
              <p className="text-slate-400 text-sm">
                Please check your connection and try again
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const squeezeCount = chartData?.filter((d) => d.squeeze_active).length || 0;

  return (
    <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          <TrendingUp className="h-5 w-5 text-financial-primary" />
          <div>
            <CardTitle className="text-lg">
              {stock.symbol} - TTM Squeeze Analysis
            </CardTitle>
            <div className="flex items-center gap-2 mt-1">
              <Badge className="bg-financial-primary/20 text-financial-primary text-xs">
                {stock.company_name}
              </Badge>
              <Badge
                className={`text-xs ${
                  squeezeCount > 0
                    ? "bg-red-500/20 text-red-400"
                    : "bg-green-500/20 text-green-400"
                }`}
              >
                {squeezeCount > 0
                  ? `${squeezeCount} Squeeze Days`
                  : "No Squeeze"}
              </Badge>
            </div>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="text-slate-400 hover:text-slate-200"
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="date"
                stroke="#9CA3AF"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#9CA3AF"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `$${value}`}
                width={60}
                orientation="left"
              />
              <Tooltip content={<CustomTooltip />} />

              {/* Bollinger Bands */}
              <Line
                type="monotone"
                dataKey="bollinger_upper"
                stroke="#3B82F6"
                strokeWidth={1}
                dot={false}
                strokeDasharray="5 5"
                name="BB Upper"
              />
              <Line
                type="monotone"
                dataKey="bollinger_lower"
                stroke="#3B82F6"
                strokeWidth={1}
                dot={false}
                strokeDasharray="5 5"
                name="BB Lower"
              />

              {/* Keltner Channels */}
              <Line
                type="monotone"
                dataKey="keltner_upper"
                stroke="#F59E0B"
                strokeWidth={1}
                dot={false}
                strokeDasharray="2 2"
                name="KC Upper"
              />
              <Line
                type="monotone"
                dataKey="keltner_lower"
                stroke="#F59E0B"
                strokeWidth={1}
                dot={false}
                strokeDasharray="2 2"
                name="KC Lower"
              />

              {/* Price Line */}
              <Line
                type="monotone"
                dataKey="price"
                stroke="#0066FF"
                strokeWidth={2}
                dot={false}
                name="Price"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Chart Legend */}
        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-financial-primary"></div>
            <span className="text-slate-400">Price</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-blue-400 border-dashed border-t"></div>
            <span className="text-slate-400">Bollinger Bands</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-orange-400 border-dotted border-t"></div>
            <span className="text-slate-400">Keltner Channels</span>
          </div>
        </div>

        {/* Analysis Summary */}
        <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
          <h4 className="text-sm font-medium text-slate-200 mb-2">
            Analysis Summary
          </h4>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-400">Current Price:</span>
              <span className="ml-2 text-financial-primary font-mono">
                ${stock.price.toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Squeeze Days:</span>
              <span className="ml-2 text-financial-secondary font-mono">
                {stock.squeeze_days}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Intensity:</span>
              <span className="ml-2 text-market-warning font-mono capitalize">
                {stock.squeeze_intensity}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Momentum:</span>
              <span
                className={`ml-2 font-mono ${
                  stock.momentum > 0 ? "text-market-bull" : "text-market-bear"
                }`}
              >
                {stock.momentum > 0 ? "+" : ""}
                {stock.momentum.toFixed(3)}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
