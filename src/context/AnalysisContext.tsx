import { createContext, useContext, useState, type ReactNode } from "react";
import type { AnalysisResponse } from "@/services/api";

interface FormData {
  ticker: string;
  amount: string;
  portfolio: string;
  riskTolerance: string;
  timeHorizon: string;
  userQuery: string;
}

// A single holding as returned by the Plaid exchange endpoint (or demo portfolio)
export interface PortfolioHolding {
  ticker: string;
  value: number;
  name?: string;
  shares?: number;
  cost_basis?: number;
}

export type AnalysisAction = "buy" | "sell" | "hold";

const LS_KEY = "investigateai_last_result";

function loadFromStorage(): AnalysisResponse | null {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? (JSON.parse(raw) as AnalysisResponse) : null;
  } catch {
    return null;
  }
}

interface AnalysisContextType {
  formData: FormData;
  setFormData: (data: FormData) => void;
  analysisResult: AnalysisResponse | null;
  setAnalysisResult: (result: AnalysisResponse | null) => void;
  // Plaid / real holdings (null = not connected, use demo fallback)
  plaidHoldings: PortfolioHolding[] | null;
  setPlaidHoldings: (holdings: PortfolioHolding[] | null) => void;
  // Action being debated: buy more / sell / hold
  analysisAction: AnalysisAction;
  setAnalysisAction: (action: AnalysisAction) => void;
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

export const AnalysisProvider = ({ children }: { children: ReactNode }) => {
  const [formData, setFormData] = useState<FormData>({
    ticker: "",
    amount: "",
    portfolio: "",
    riskTolerance: "",
    timeHorizon: "",
    userQuery: "",
  });

  // Seed from localStorage so /results works even after a page reload
  const [analysisResult, _setAnalysisResult] = useState<AnalysisResponse | null>(
    loadFromStorage
  );
  const [plaidHoldings, setPlaidHoldings] = useState<PortfolioHolding[] | null>(null);
  const [analysisAction, setAnalysisAction] = useState<AnalysisAction>("buy");

  const setAnalysisResult = (result: AnalysisResponse | null) => {
    _setAnalysisResult(result);
    try {
      if (result) localStorage.setItem(LS_KEY, JSON.stringify(result));
      else localStorage.removeItem(LS_KEY);
    } catch {
      // storage quota exceeded — ignore
    }
  };

  return (
    <AnalysisContext.Provider
      value={{
        formData, setFormData,
        analysisResult, setAnalysisResult,
        plaidHoldings, setPlaidHoldings,
        analysisAction, setAnalysisAction,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
};

export const useAnalysis = () => {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within AnalysisProvider");
  return ctx;
};
