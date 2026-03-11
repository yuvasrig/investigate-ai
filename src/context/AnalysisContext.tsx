import { createContext, useContext, useState, type ReactNode } from "react";
import type { AnalysisResponse } from "@/services/api";

interface FormData {
  ticker: string;
  amount: string;
  portfolio: string;
  riskTolerance: string;
  timeHorizon: string;
}

interface AnalysisContextType {
  formData: FormData;
  setFormData: (data: FormData) => void;
  analysisResult: AnalysisResponse | null;
  setAnalysisResult: (result: AnalysisResponse | null) => void;
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

export const AnalysisProvider = ({ children }: { children: ReactNode }) => {
  const [formData, setFormData] = useState<FormData>({
    ticker: "",
    amount: "",
    portfolio: "",
    riskTolerance: "",
    timeHorizon: "",
  });
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);

  return (
    <AnalysisContext.Provider value={{ formData, setFormData, analysisResult, setAnalysisResult }}>
      {children}
    </AnalysisContext.Provider>
  );
};

export const useAnalysis = () => {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within AnalysisProvider");
  return ctx;
};
