import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Play,
  Settings,
  Square,
  Globe,
  Activity,
} from "lucide-react";
import { useTriggerMarketScan, ScanParameters } from "@/hooks/useStocks";
import { toast } from "@/hooks/use-toast";

interface ScanControlsProps {
  className?: string;
}

export function ScanControls({ className }: ScanControlsProps) {
  const triggerScan = useTriggerMarketScan();
  const [scanParams, setScanParams] = useState<ScanParameters>({
    min_turnover_us: 2000000,
    min_turnover_au: 500000,
    min_squeeze_days: 5,
    min_volume_spike_ratio_us: 10,
    min_volume_spike_ratio_au: 5,
  });
  const [isParamsOpen, setIsParamsOpen] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleScanCountry = async (country: "US" | "AU") => {
    // Create abort controller for this scan
    abortControllerRef.current = new AbortController();
    
    triggerScan.mutate({ 
      country, 
      params: scanParams, 
      signal: abortControllerRef.current.signal 
    });
  };

  const handleScanBoth = async () => {
    // Trigger both scans sequentially
    abortControllerRef.current = new AbortController();
    
    triggerScan.mutate({ 
      country: "US", 
      params: scanParams, 
      signal: abortControllerRef.current.signal 
    });
    
    // Wait a bit before triggering AU scan
    setTimeout(() => {
      if (!abortControllerRef.current?.signal.aborted) {
        const newController = new AbortController();
        abortControllerRef.current = newController;
        triggerScan.mutate({ 
          country: "AU", 
          params: scanParams, 
          signal: newController.signal 
        });
      }
    }, 3000);
  };

  const handleStopScan = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    // Reset the mutation state
    triggerScan.reset();
    
    // Call backend to cancel running scans
    try {
      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      await fetch(`${baseUrl}/api/market-scanner/cancel/US`, { method: 'POST' });
      await fetch(`${baseUrl}/api/market-scanner/cancel/AU`, { method: 'POST' });
    } catch (error) {
      console.error("Error cancelling backend scans:", error);
    }
    
    toast({
      title: "Scan Stopped",
      description: "Market scan has been stopped.",
      variant: "destructive",
    });
  };

  const updateParam = (key: keyof ScanParameters, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      setScanParams(prev => ({ ...prev, [key]: numValue }));
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Parameters Settings */}
      <Popover open={isParamsOpen} onOpenChange={setIsParamsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="border-slate-600 text-slate-300 hover:bg-slate-700"
          >
            <Settings className="h-4 w-4 mr-1" />
            Parameters
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 bg-slate-800 border-slate-700" align="start">
          <div className="space-y-4">
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-slate-200">Scan Parameters</h4>
              <p className="text-xs text-slate-400">Adjust the market scanner criteria</p>
            </div>
            
            <div className="grid gap-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="turnover-us" className="text-xs text-slate-300">
                    US Min Turnover ($)
                  </Label>
                  <Input
                    id="turnover-us"
                    type="number"
                    value={scanParams.min_turnover_us}
                    onChange={(e) => updateParam('min_turnover_us', e.target.value)}
                    className="h-8 text-xs bg-slate-700 border-slate-600"
                  />
                </div>
                <div>
                  <Label htmlFor="turnover-au" className="text-xs text-slate-300">
                    AU Min Turnover ($)
                  </Label>
                  <Input
                    id="turnover-au"
                    type="number"
                    value={scanParams.min_turnover_au}
                    onChange={(e) => updateParam('min_turnover_au', e.target.value)}
                    className="h-8 text-xs bg-slate-700 border-slate-600"
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="squeeze-days" className="text-xs text-slate-300">
                  Min Squeeze Days
                </Label>
                <Input
                  id="squeeze-days"
                  type="number"
                  value={scanParams.min_squeeze_days}
                  onChange={(e) => updateParam('min_squeeze_days', e.target.value)}
                  className="h-8 text-xs bg-slate-700 border-slate-600"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="volume-us" className="text-xs text-slate-300">
                    US Volume Ratio (x)
                  </Label>
                  <Input
                    id="volume-us"
                    type="number"
                    value={scanParams.min_volume_spike_ratio_us}
                    onChange={(e) => updateParam('min_volume_spike_ratio_us', e.target.value)}
                    className="h-8 text-xs bg-slate-700 border-slate-600"
                  />
                </div>
                <div>
                  <Label htmlFor="volume-au" className="text-xs text-slate-300">
                    AU Volume Ratio (x)
                  </Label>
                  <Input
                    id="volume-au"
                    type="number"
                    value={scanParams.min_volume_spike_ratio_au}
                    onChange={(e) => updateParam('min_volume_spike_ratio_au', e.target.value)}
                    className="h-8 text-xs bg-slate-700 border-slate-600"
                  />
                </div>
              </div>
            </div>

            <Button
              onClick={() => setIsParamsOpen(false)}
              className="w-full h-8 text-xs bg-financial-primary hover:bg-financial-primary/80"
            >
              Apply Settings
            </Button>
          </div>
        </PopoverContent>
      </Popover>

      {/* Scan Buttons */}
      {!triggerScan.isPending ? (
        <>
          <Button
            onClick={() => handleScanCountry("US")}
            className="bg-blue-600 hover:bg-blue-700 text-white"
            size="sm"
          >
            <Globe className="h-4 w-4 mr-1" />
            US
          </Button>
          
          <Button
            onClick={() => handleScanCountry("AU")}
            className="bg-orange-600 hover:bg-orange-700 text-white"
            size="sm"
          >
            <Globe className="h-4 w-4 mr-1" />
            AU
          </Button>
          
          <Button
            onClick={handleScanBoth}
            className="bg-green-600 hover:bg-green-700 text-white"
            size="sm"
          >
            <Activity className="h-4 w-4 mr-1" />
            Both
          </Button>
        </>
      ) : (
        <div className="flex items-center gap-2">
          <Button
            onClick={handleStopScan}
            className="bg-red-600 hover:bg-red-700 text-white"
            size="sm"
          >
            <Square className="h-4 w-4 mr-1" />
            Stop Scan
          </Button>
          <Badge variant="outline" className="animate-pulse">
            Scanning...
          </Badge>
        </div>
      )}
    </div>
  );
} 