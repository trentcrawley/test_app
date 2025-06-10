import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// Suppress Recharts defaultProps warnings in development
// These warnings come from within the Recharts library and will be fixed when they update
if (import.meta.env.DEV) {
  const originalWarn = console.warn;
  console.warn = (...args) => {
    const message = args[0];
    // Filter out Recharts defaultProps warnings
    if (
      typeof message === "string" &&
      message.includes("Support for defaultProps will be removed") &&
      (message.includes("XAxis") || message.includes("YAxis"))
    ) {
      return; // Suppress this warning
    }
    originalWarn.apply(console, args);
  };
}

createRoot(document.getElementById("root")!).render(<App />);
