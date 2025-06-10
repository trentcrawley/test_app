import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { stockApi } from "@/services/stockApi";
import { VolumeSpikeStock } from "@/types/stock";
import { format } from "date-fns";
import { Volume2, X, BarChart3 } from "lucide-react";

interface VolumeSpikeChartProps {
  stock: VolumeSpikeStock;
  onClose: () => void;
}

interface VolumeChartDataPoint {
  date: string;
  volume: number;
  avg_volume: number;
  volume_ratio: number;
  price: number;
  is_spike: boolean;
}

const generateMockVolumeChartData = (
  stock: VolumeSpikeStock,
): VolumeChartDataPoint[] => {
  const data: VolumeChartDataPoint[] = [];
  const baseVolume = stock.avg_volume_30d;
  const currentPrice = stock.price;
  const days = 30;

  for (let i = days; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);

    // Generate volume data with spikes in recent days
    let volume: number;
    let volume_ratio: number;
    let is_spike = false;

    if (i <= 3) {
      // Recent 3 days have spikes
      volume = baseVolume * (10 + Math.random() * 15); // 10-25x average
      volume_ratio = volume / baseVolume;
      is_spike = true;
    } else {
      // Normal volume for older days
      volume = baseVolume * (0.5 + Math.random() * 1.5); // 0.5-2x average
      volume_ratio = volume / baseVolume;
    }

    // Generate price movement
    const priceVariation = (Math.random() - 0.5) * 20;
    const price = currentPrice + priceVariation;

    data.push({
      date: format(date, "MMM dd"),
      volume: Math.floor(volume),
      avg_volume: Math.floor(baseVolume),
      volume_ratio: Number(volume_ratio.toFixed(1)),
      price: Number(price.toFixed(2)),
      is_spike,
    });
  }

  return data;
};

const useVolumeChartData = (symbol: string) => {
  return useQuery({
    queryKey: ["volume-chart", symbol],
    queryFn: async () => {
      // This will be replaced with real EODHD API call
      await new Promise((resolve) => setTimeout(resolve, 800));
      return generateMockVolumeChartData({} as VolumeSpikeStock);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

const formatVolume = (value: number) => {
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

const CustomVolumeTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 shadow-xl">
        <p className="text-slate-200 font-medium mb-2">{label}</p>
        <div className="space-y-1 text-sm">
          <p className="text-financial-secondary">
            Volume: {formatVolume(data.volume)}
          </p>
          <p className="text-slate-400">
            30D Avg: {formatVolume(data.avg_volume)}
          </p>
          <p
            className={`font-bold ${data.volume_ratio > 5 ? "text-red-400" : "text-blue-400"}`}
          >
            Ratio: {data.volume_ratio}x
          </p>
          <p className="text-financial-primary">
            Price: ${data.price?.toFixed(2)}
          </p>
          {data.is_spike && (
            <Badge className="bg-red-500/20 text-red-400 text-xs">
              Volume Spike!
            </Badge>
          )}
        </div>
      </div>
    );
  }
  return null;
};

export function VolumeSpikeChart({ stock, onClose }: VolumeSpikeChartProps) {
  const {
    data: chartData,
    isLoading,
    error,
  } = useVolumeChartData(stock.symbol);

  if (isLoading) {
    return (
      <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center gap-2">
            <Volume2 className="h-5 w-5 text-financial-secondary" />
            <CardTitle className="text-lg">
              {stock.symbol} - Volume Analysis
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
              <div className="animate-spin h-6 w-6 border-2 border-financial-secondary border-t-transparent rounded-full"></div>
              <span className="text-slate-400">Loading volume data...</span>
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
            <Volume2 className="h-5 w-5 text-financial-secondary" />
            <CardTitle className="text-lg">
              {stock.symbol} - Volume Analysis
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
              <p className="text-market-bear mb-2">
                Failed to load volume data
              </p>
              <p className="text-slate-400 text-sm">
                Please check your connection and try again
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const spikeCount = chartData?.filter((d) => d.is_spike).length || 0;
  const maxRatio = Math.max(...(chartData?.map((d) => d.volume_ratio) || [0]));

  return (
    <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          <Volume2 className="h-5 w-5 text-financial-secondary" />
          <div>
            <CardTitle className="text-lg">
              {stock.symbol} - Volume Spike Analysis
            </CardTitle>
            <div className="flex items-center gap-2 mt-1">
              <Badge className="bg-financial-secondary/20 text-financial-secondary text-xs">
                {stock.company_name}
              </Badge>
              <Badge
                className={`text-xs ${
                  spikeCount >= 3
                    ? "bg-red-500/20 text-red-400"
                    : "bg-green-500/20 text-green-400"
                }`}
              >
                {spikeCount} Spike Days
              </Badge>
              <Badge className="bg-orange-500/20 text-orange-400 text-xs">
                Max: {maxRatio.toFixed(1)}x
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
            <BarChart
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
                tickFormatter={formatVolume}
                width={60}
                orientation="left"
              />
              <Tooltip content={<CustomVolumeTooltip />} />

              {/* Average Volume Line */}
              <Bar
                dataKey="avg_volume"
                fill="#64748B"
                fillOpacity={0.3}
                name="30D Average"
              />

              {/* Actual Volume Bars */}
              <Bar
                dataKey="volume"
                fill="#00D4AA"
                name="Daily Volume"
                radius={[2, 2, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Volume Ratio Chart */}
        <div className="h-32 w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="date"
                stroke="#9CA3AF"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#9CA3AF"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => `${value}x`}
                width={40}
                orientation="left"
              />
              <Tooltip
                formatter={(value: number) => [`${value}x`, "Volume Ratio"]}
                labelStyle={{ color: "#e2e8f0" }}
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #475569",
                  borderRadius: "8px",
                }}
              />

              {/* 10x threshold line */}
              <Line
                type="monotone"
                dataKey={() => 10}
                stroke="#ef4444"
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={false}
                name="10x Threshold"
              />

              {/* Volume ratio line */}
              <Line
                type="monotone"
                dataKey="volume_ratio"
                stroke="#00D4AA"
                strokeWidth={2}
                dot={{ fill: "#00D4AA", strokeWidth: 2, r: 3 }}
                name="Volume Ratio"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Analysis Summary */}
        <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
          <h4 className="text-sm font-medium text-slate-200 mb-2">
            Volume Analysis Summary
          </h4>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-400">Current Volume:</span>
              <span className="ml-2 text-financial-secondary font-mono">
                {formatVolume(stock.volume)}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Volume Ratio:</span>
              <span className="ml-2 text-financial-secondary font-mono">
                {stock.volume_ratio.toFixed(1)}x
              </span>
            </div>
            <div>
              <span className="text-slate-400">Spike Days:</span>
              <span className="ml-2 text-market-warning font-mono">
                {stock.consecutive_days}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Intensity:</span>
              <span className="ml-2 text-market-warning font-mono capitalize">
                {stock.spike_intensity}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
