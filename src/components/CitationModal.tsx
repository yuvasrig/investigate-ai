/**
 * CitationModal — slide-over panel showing a raw SEC 10-K section excerpt.
 *
 * Triggered when the user clicks the SEC citation badge on a VerifiedClaim.
 * Fetches the excerpt lazily and caches it for the session.
 */

import { useEffect, useRef, useState } from "react";
import { X, ExternalLink, FileText, Loader2, AlertCircle } from "lucide-react";
import { getSecExcerpt, type SecExcerpt } from "@/services/api";

// Map the sec_section label from the LLM → API section key
const SECTION_KEY_MAP: Record<string, "business" | "risk_factors" | "mda" | "financials"> = {
  "item 1 - business":              "business",
  "item 1a - risk factors":         "risk_factors",
  "item 1a":                        "risk_factors",
  "item 7 - md&a":                  "mda",
  "item 7":                         "mda",
  "item 8 - financial statements":  "financials",
  "item 8":                         "financials",
};

function normalizeSectionKey(
  raw: string
): "business" | "risk_factors" | "mda" | "financials" | null {
  return SECTION_KEY_MAP[raw.toLowerCase()] ?? null;
}

// In-session cache keyed by "TICKER:section"
const _excerptCache: Map<string, SecExcerpt> = new Map();

interface Props {
  ticker: string;
  secSection: string;        // raw value from VerifiedClaim.sec_section
  claimText: string;
  filingUrl?: string | null; // fallback direct link
  onClose: () => void;
}

export default function CitationModal({
  ticker,
  secSection,
  claimText,
  filingUrl,
  onClose,
}: Props) {
  const [excerpt, setExcerpt] = useState<SecExcerpt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const sectionKey = normalizeSectionKey(secSection);

  useEffect(() => {
    if (!sectionKey) {
      setError(`Unknown SEC section: "${secSection}"`);
      setLoading(false);
      return;
    }
    const cacheKey = `${ticker}:${sectionKey}`;
    if (_excerptCache.has(cacheKey)) {
      setExcerpt(_excerptCache.get(cacheKey)!);
      setLoading(false);
      return;
    }
    getSecExcerpt(ticker, sectionKey)
      .then((data) => {
        _excerptCache.set(cacheKey, data);
        setExcerpt(data);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [ticker, sectionKey, secSection]);

  // Close on overlay click
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  };

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm"
      onClick={handleOverlayClick}
    >
      {/* Panel */}
      <div className="relative h-full w-full max-w-xl bg-card shadow-2xl flex flex-col overflow-hidden animate-slide-in-right">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-border bg-card">
          <div className="flex items-center gap-2.5">
            <FileText size={18} className="text-blue-500 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-foreground">
                {excerpt?.section_label ?? secSection}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {ticker.toUpperCase()} 10-K
                {excerpt?.filing_date ? ` · Filed ${excerpt.filing_date}` : ""}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
          >
            <X size={16} />
          </button>
        </div>

        {/* Claim context */}
        <div className="px-6 py-4 bg-blue-500/5 border-b border-border">
          <p className="text-xs text-muted-foreground mb-1 font-medium uppercase tracking-wide">
            Claim cited from this section
          </p>
          <p className="text-sm text-foreground leading-relaxed italic">"{claimText}"</p>
        </div>

        {/* Excerpt body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 size={16} className="animate-spin" />
              Fetching from SEC EDGAR…
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 text-sm text-bear">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Could not load excerpt</p>
                <p className="text-muted-foreground mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {excerpt && !loading && (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">
                Raw filing text (excerpt)
              </p>
              <div className="rounded-lg bg-secondary/50 border border-border p-4 text-xs text-foreground/80 leading-relaxed font-mono whitespace-pre-wrap break-words max-h-[55vh] overflow-y-auto">
                {excerpt.text}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border bg-card flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            Source: SEC EDGAR public filing
          </p>
          <a
            href={excerpt?.filing_url ?? filingUrl ?? "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-medium text-blue-500 hover:text-blue-400 transition-colors"
          >
            <ExternalLink size={13} />
            Open full 10-K
          </a>
        </div>
      </div>
    </div>
  );
}
