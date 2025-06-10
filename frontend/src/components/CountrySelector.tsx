import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface CountrySelectorProps {
  selectedCountry: "US" | "AU";
  onCountryChange: (country: "US" | "AU") => void;
  className?: string;
}

// Flag components using SVG for better display
const USFlag = () => (
  <svg
    width="20"
    height="15"
    viewBox="0 0 20 15"
    className="rounded-sm border border-slate-600"
    aria-label="United States flag"
  >
    <defs>
      <pattern id="stars" width="4" height="3" patternUnits="userSpaceOnUse">
        <rect width="4" height="3" fill="#002868" />
        <circle cx="2" cy="1.5" r="0.3" fill="white" />
      </pattern>
    </defs>
    <rect width="20" height="15" fill="#bf0a30" />
    <rect width="20" height="1.15" y="0" fill="white" />
    <rect width="20" height="1.15" y="2.31" fill="white" />
    <rect width="20" height="1.15" y="4.62" fill="white" />
    <rect width="20" height="1.15" y="6.92" fill="white" />
    <rect width="20" height="1.15" y="9.23" fill="white" />
    <rect width="20" height="1.15" y="11.54" fill="white" />
    <rect width="20" height="1.15" y="13.85" fill="white" />
    <rect width="8" height="8.08" fill="url(#stars)" />
  </svg>
);

const AustraliaFlag = () => (
  <svg
    width="20"
    height="15"
    viewBox="0 0 20 15"
    className="rounded-sm border border-slate-600"
    aria-label="Australia flag"
  >
    <rect width="20" height="15" fill="#012169" />
    {/* Union Jack in canton */}
    <g>
      <rect width="10" height="7.5" fill="#012169" />
      <rect width="10" height="0.75" y="3.375" fill="white" />
      <rect width="1" height="7.5" x="4.5" fill="white" />
      <rect width="10" height="0.5" y="3.5" fill="#C8102E" />
      <rect width="0.6" height="7.5" x="4.7" fill="#C8102E" />
      <path d="M0 0 L10 7.5 M0 7.5 L10 0" stroke="white" strokeWidth="1" />
      <path d="M0 0 L10 7.5 M0 7.5 L10 0" stroke="#C8102E" strokeWidth="0.6" />
    </g>
    {/* Southern Cross stars */}
    <circle cx="13" cy="3" r="0.4" fill="white" />
    <circle cx="15" cy="5" r="0.4" fill="white" />
    <circle cx="17" cy="8" r="0.4" fill="white" />
    <circle cx="15" cy="10" r="0.4" fill="white" />
    <circle cx="12" cy="11" r="0.3" fill="white" />
    {/* Commonwealth Star */}
    <circle cx="3" cy="11" r="0.5" fill="white" />
  </svg>
);

export function CountrySelector({
  selectedCountry,
  onCountryChange,
  className,
}: CountrySelectorProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Button
        variant={selectedCountry === "US" ? "default" : "outline"}
        size="sm"
        onClick={() => onCountryChange("US")}
        className={cn(
          "flex items-center gap-2",
          selectedCountry === "US"
            ? "bg-financial-primary hover:bg-financial-primary/80 text-white"
            : "bg-slate-800/50 border-slate-600 text-slate-300 hover:bg-slate-700",
        )}
      >
        <USFlag />
        <span className="font-medium">US</span>
      </Button>

      <Button
        variant={selectedCountry === "AU" ? "default" : "outline"}
        size="sm"
        onClick={() => onCountryChange("AU")}
        className={cn(
          "flex items-center gap-2",
          selectedCountry === "AU"
            ? "bg-financial-primary hover:bg-financial-primary/80 text-white"
            : "bg-slate-800/50 border-slate-600 text-slate-300 hover:bg-slate-700",
        )}
      >
        <AustraliaFlag />
        <span className="font-medium">ASX</span>
      </Button>
    </div>
  );
}
