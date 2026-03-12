/**
 * PlaidLink — opens the Plaid Link modal to connect a brokerage account.
 *
 * Uses the Plaid Link JS SDK loaded from their CDN to avoid a build-time
 * dependency. If `react-plaid-link` is installed you can replace this with
 * the usePlaidLink hook instead.
 *
 * Flow:
 *   1. Component mounts → fetches a link_token from /api/plaid/link-token
 *   2. User clicks "Connect Brokerage" → Plaid modal opens
 *   3. User completes auth → public_token sent to /api/plaid/exchange-token
 *   4. Backend returns normalised holdings → onSuccess callback fires
 */

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Loader2, Building2, CheckCircle2, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

// Plaid Link initialised via their CDN script
declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Plaid?: any;
  }
}

export interface PlaidPortfolioHolding {
  ticker: string;
  value: number;
  name?: string;
  shares?: number;
  cost_basis?: number;
}

interface PlaidPortfolio {
  total_value: number;
  holdings: PlaidPortfolioHolding[];
}

interface PlaidLinkProps {
  /** Called when holdings are successfully fetched from the backend */
  onSuccess: (portfolio: PlaidPortfolio) => void;
  /** Optional user ID sent to /api/plaid/link-token */
  userId?: string;
  className?: string;
}

// Load the Plaid Link script once
function loadPlaidScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.Plaid) { resolve(); return; }
    if (document.getElementById("plaid-link-script")) {
      // Already loading — wait
      const check = setInterval(() => {
        if (window.Plaid) { clearInterval(check); resolve(); }
      }, 100);
      return;
    }
    const script = document.createElement("script");
    script.id  = "plaid-link-script";
    script.src = "https://cdn.plaid.com/link/v2/stable/link-initialize.js";
    script.onload  = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Plaid Link script"));
    document.head.appendChild(script);
  });
}

export function PlaidLink({ onSuccess, userId = "anonymous", className }: PlaidLinkProps) {
  const [status, setStatus]   = useState<"idle" | "loading" | "ready" | "success" | "error">("idle");
  const [errorMsg, setError]  = useState<string | null>(null);
  const [holdings, setHoldings] = useState<PlaidPortfolio | null>(null);

  const openPlaidLink = useCallback(async () => {
    setStatus("loading");
    setError(null);

    try {
      // 1. Get link token from backend
      const ltRes = await fetch(`${API_BASE}/api/plaid/link-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!ltRes.ok) {
        const json = (await ltRes.json()) as { detail?: string };
        throw new Error(json.detail || "Failed to get link token");
      }
      const { link_token } = (await ltRes.json()) as { link_token: string };

      // 2. Load Plaid Link script
      await loadPlaidScript();

      // 3. Open modal
      const handler = window.Plaid.create({
        token: link_token,
        onSuccess: async (public_token: string) => {
          setStatus("loading");
          try {
            // 4. Exchange for access_token + fetch holdings
            const exRes = await fetch(`${API_BASE}/api/plaid/exchange-token`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ public_token }),
            });
            if (!exRes.ok) {
              const json = (await exRes.json()) as { detail?: string };
              throw new Error(json.detail || "Exchange failed");
            }
            const portfolio = (await exRes.json()) as PlaidPortfolio;
            setHoldings(portfolio);
            setStatus("success");
            onSuccess(portfolio);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Exchange failed");
            setStatus("error");
          }
        },
        onExit: () => {
          if (status === "loading") setStatus("idle");
        },
        onEvent: () => { /* telemetry */ },
      });

      setStatus("ready");
      handler.open();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open Plaid");
      setStatus("error");
    }
  }, [userId, onSuccess, status]);

  if (status === "success" && holdings) {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium">
          <CheckCircle2 className="h-4 w-4" />
          Connected — {holdings.holdings.length} holdings imported
          (${holdings.total_value.toLocaleString()})
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => { setStatus("idle"); setHoldings(null); }}
          className="text-slate-400 border-slate-600 hover:text-white w-fit"
        >
          Disconnect
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <Button
        onClick={openPlaidLink}
        disabled={status === "loading"}
        className={className ?? "bg-blue-600 hover:bg-blue-700 text-white"}
        type="button"
      >
        {status === "loading" ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Connecting…
          </>
        ) : (
          <>
            <Building2 className="mr-2 h-4 w-4" />
            Connect Brokerage (Plaid)
          </>
        )}
      </Button>

      {status === "error" && errorMsg && (
        <Alert variant="destructive" className="py-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-xs">{errorMsg}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}

export default PlaidLink;
