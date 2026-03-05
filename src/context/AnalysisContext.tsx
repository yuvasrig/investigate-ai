import { createContext, useContext, useState, type ReactNode } from "react";

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

  return (
    <AnalysisContext.Provider value={{ formData, setFormData }}>
      {children}
    </AnalysisContext.Provider>
  );
};

export const useAnalysis = () => {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within AnalysisProvider");
  return ctx;
};
