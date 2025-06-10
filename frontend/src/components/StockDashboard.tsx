import { useState } from "react";
import {
  useStockAnalysis,
  useRefreshStockData,
  useSavedStocks,
} from "@/hooks/useStocks";
import { TTMSqueezeTable } from "@/components/TTMSqueezeTable";
import { VolumeSpikeTable } from "@/components/VolumeSpikeTable";
import { CountrySelector } from "@/components/CountrySelector";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  RefreshCw,
  TrendingUp,
  Volume2,
  Bookmark,
  Activity,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { format } from "date-fns";

export function StockDashboard() {
  const [activeTab, setActiveTab] = useState("ttm-squeeze");
  const [selectedCountry, setSelectedCountry] = useState<"US" | "AU">("US");

  const {
    data: stockAnalysis,
    isLoading,
    error,
  } = useStockAnalysis({ country: selectedCountry });
  const { data: savedStocks, isLoading: savedStocksLoading } = useSavedStocks();
  const refreshData = useRefreshStockData();

  const handleRefresh = () => {
    refreshData.mutate();
  };

  const stats = [
    {
      title: "TTM Squeeze Signals",
      value: stockAnalysis?.ttm_squeeze.length || 0,
      icon: TrendingUp,
      description: "Stocks squeezed 5+ days",
      color: "text-financial-primary",
      bgColor: "bg-financial-primary/10",
    },
    {
      title: "Volume Spike Alerts",
      value: stockAnalysis?.volume_spikes.length || 0,
      icon: Volume2,
      description: "High volume activity",
      color: "text-financial-secondary",
      bgColor: "bg-financial-secondary/10",
    },
    {
      title: "Saved Stocks",
      value: savedStocks?.length || 0,
      icon: Bookmark,
      description: "From volume spikes",
      color: "text-market-neutral",
      bgColor: "bg-market-neutral/10",
    },
    {
      title: "Last Updated",
      value: stockAnalysis?.last_updated
        ? format(new Date(stockAnalysis.last_updated), "HH:mm")
        : "--:--",
      icon: Clock,
      description: "Data freshness",
      color: "text-slate-400",
      bgColor: "bg-slate-400/10",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-dark text-slate-200">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Activity className="h-8 w-8 text-financial-primary" />
                <h1 className="text-2xl font-bold bg-gradient-financial bg-clip-text text-transparent">
                  StockScope
                </h1>
              </div>
              <Badge
                variant="outline"
                className="bg-financial-primary/10 text-financial-primary border-financial-primary"
              >
                EODHD API
              </Badge>
            </div>

            <div className="flex items-center gap-3">
              {error && (
                <div className="flex items-center gap-2 text-market-bear">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">Connection error</span>
                </div>
              )}

              <Button
                onClick={handleRefresh}
                disabled={refreshData.isPending || isLoading}
                className="bg-financial-primary hover:bg-financial-primary/80"
              >
                <RefreshCw
                  className={`h-4 w-4 mr-2 ${refreshData.isPending ? "animate-spin" : ""}`}
                />
                Refresh Data
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8 space-y-8">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => (
            <Card
              key={index}
              className="bg-slate-800/50 border-slate-700 backdrop-blur-sm"
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">
                  {stat.title}
                </CardTitle>
                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`h-4 w-4 ${stat.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${stat.color}`}>
                  {stat.value}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Tabs */}
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="space-y-6"
        >
          <TabsList className="grid w-full grid-cols-2 bg-slate-800/50 border border-slate-700">
            <TabsTrigger
              value="ttm-squeeze"
              className="data-[state=active]:bg-financial-primary data-[state=active]:text-white"
            >
              <TrendingUp className="h-4 w-4 mr-2" />
              TTM Squeeze
            </TabsTrigger>
            <TabsTrigger
              value="volume-spikes"
              className="data-[state=active]:bg-financial-secondary data-[state=active]:text-white"
            >
              <Volume2 className="h-4 w-4 mr-2" />
              Volume Spikes
            </TabsTrigger>
          </TabsList>

          <TabsContent value="ttm-squeeze" className="space-y-6">
            <Card className="bg-slate-800/30 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-financial-primary" />
                      TTM Squeeze Analysis
                    </CardTitle>
                    <CardDescription>
                      Stocks where Bollinger Bands are inside Keltner Channels
                      for over 5 days, indicating potential breakout
                      opportunities.
                    </CardDescription>
                  </div>
                  <CountrySelector
                    selectedCountry={selectedCountry}
                    onCountryChange={setSelectedCountry}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <TTMSqueezeTable
                  data={stockAnalysis?.ttm_squeeze || []}
                  isLoading={isLoading}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="volume-spikes" className="space-y-6">
            <Card className="bg-slate-800/30 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Volume2 className="h-5 w-5 text-financial-secondary" />
                      Volume Spike Detection
                    </CardTitle>
                    <CardDescription>
                      Stocks with unusual volume activity - 3 consecutive days
                      of volume exceeding 10x their 30-day average.
                    </CardDescription>
                  </div>
                  <CountrySelector
                    selectedCountry={selectedCountry}
                    onCountryChange={setSelectedCountry}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <VolumeSpikeTable
                  data={stockAnalysis?.volume_spikes || []}
                  isLoading={isLoading}
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
