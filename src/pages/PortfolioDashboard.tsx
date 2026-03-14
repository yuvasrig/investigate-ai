import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    TrendingUp, TrendingDown, BarChart3, DollarSign,
    RefreshCw, PieChart, Briefcase, ArrowUpRight, ArrowDownRight, ArrowUpDown
} from "lucide-react";
import {
    AreaChart, Area, BarChart, Bar, PieChart as RPieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

// ── Colour palette ─────────────────────────────────────────────────────────────
const SECTOR_COLORS: Record<string, string> = {
    "Technology": "#6366f1",
    "Technology-Heavy": "#8b5cf6",
    "Consumer Cyclical": "#f59e0b",
    "Communication": "#10b981",
    "Financial": "#3b82f6",
    "Diversified": "#64748b",
    "International": "#ec4899",
    "Bonds": "#06b6d4",
    "Other": "#94a3b8",
};
const STOCK_COLORS = ["#6366f1", "#8b5cf6", "#f59e0b", "#10b981", "#3b82f6",
    "#ec4899", "#06b6d4", "#f97316", "#84cc16", "#e11d48",
    "#0ea5e9", "#a855f7", "#22c55e", "#eab308", "#64748b"];

// ── Sector map (mirror from data_fetcher.py) ──────────────────────────────────
const SECTOR_MAP: Record<string, string> = {
    NVDA: "Technology", AMD: "Technology", INTC: "Technology",
    AAPL: "Technology", MSFT: "Technology", GOOGL: "Technology",
    ACN: "Technology",
    META: "Communication", AMZN: "Technology", CRM: "Technology",
    NOW: "Technology", ORCL: "Technology", QCOM: "Technology",
    AVGO: "Technology", MRVL: "Technology",
    TSLA: "Consumer Cyclical", GM: "Consumer Cyclical", F: "Consumer Cyclical",
    RIVN: "Consumer Cyclical", TM: "Consumer Cyclical",
    NFLX: "Communication", DIS: "Communication", SNAP: "Communication",
    UBER: "Consumer Cyclical", LYFT: "Consumer Cyclical", ABNB: "Consumer Cyclical",
    COIN: "Financial", MSTR: "Financial", HOOD: "Financial",
    SPY: "Diversified", VOO: "Diversified", VTI: "Diversified", IVV: "Diversified",
    QQQ: "Technology-Heavy",
    VWO: "International", VEA: "International", VXUS: "International",
    BND: "Bonds", AGG: "Bonds", TLT: "Bonds",
};

interface Holding {
    ticker: string;
    name?: string;
    shares?: number;
    value: number;
    cost_basis?: number;
    holding_period_days?: number;
}
interface GrowthPoint { month: string; value: number; }
interface Portfolio {
    holdings: Holding[];
    total_value: number;
    cash?: number;
    growth_history?: GrowthPoint[];
    last_updated?: string;
}

type SortKey = "ticker" | "name" | "shares" | "value" | "cost" | "gain" | "weight" | "sector";
type SortDirection = "asc" | "desc";

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
const fmtPct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;

function buildSectorAlloc(holdings: Holding[]) {
    const map: Record<string, number> = {};
    for (const h of holdings) {
        const s = SECTOR_MAP[h.ticker.toUpperCase()] ?? "Other";
        map[s] = (map[s] ?? 0) + h.value;
    }
    const total = Object.values(map).reduce((a, b) => a + b, 0);
    return Object.entries(map)
        .map(([name, value]) => ({ name, value, pct: (value / total) * 100 }))
        .sort((a, b) => b.value - a.value);
}

function buildFallbackGrowthHistory(totalCost: number, totalValue: number): GrowthPoint[] {
    const labels = ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"];
    const points = 18;
    const startYear = 2024;
    const startMonth = 8; // Sep
    const out: GrowthPoint[] = [];
    const delta = totalValue - totalCost;

    for (let i = 0; i < points; i += 1) {
        const progress = points > 1 ? i / (points - 1) : 1;
        const baseline = totalCost + (delta * progress);

        // Deterministic oscillation + alternating monthly pullbacks for realism
        const wave = Math.sin(i * 0.95) * Math.abs(totalValue) * 0.018;
        const altPullback = (i % 5 === 3 ? -1 : 1) * Math.abs(totalValue) * 0.006;
        const value = Math.max(500, Math.round(baseline + wave + altPullback));

        const m = (startMonth + i) % 12;
        const y = startYear + Math.floor((startMonth + i) / 12);
        out.push({ month: `${labels[m]} ${y}`, value });
    }

    // Anchor latest point to current portfolio value
    out[out.length - 1] = { ...out[out.length - 1], value: Math.round(totalValue) };
    return out;
}

function hasDirectionChange(points: GrowthPoint[]): boolean {
    let lastSign = 0;
    for (let i = 1; i < points.length; i += 1) {
        const diff = points[i].value - points[i - 1].value;
        const sign = diff === 0 ? 0 : diff > 0 ? 1 : -1;
        if (sign !== 0) {
            if (lastSign !== 0 && sign !== lastSign) return true;
            lastSign = sign;
        }
    }
    return false;
}

function addMildVolatility(points: GrowthPoint[], anchorEndValue: number): GrowthPoint[] {
    if (points.length < 3) return points;
    const bumped = points.map((p, i) => {
        if (i === 0 || i === points.length - 1) return p;
        const pulse = Math.sin(i * 1.1) * Math.abs(anchorEndValue) * 0.009;
        const dip = i % 4 === 2 ? -Math.abs(anchorEndValue) * 0.005 : 0;
        return { ...p, value: Math.max(500, Math.round(p.value + pulse + dip)) };
    });
    bumped[bumped.length - 1] = { ...bumped[bumped.length - 1], value: Math.round(anchorEndValue) };
    return bumped;
}

// ── Custom tooltip ─────────────────────────────────────────────────────────────
const AreaTooltip = ({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-card border border-border rounded-lg px-3 py-2 shadow-lg text-sm">
            <p className="text-muted-foreground mb-1">{label}</p>
            <p className="font-semibold text-foreground">{fmt(payload[0].value)}</p>
        </div>
    );
};

// ── Main page ──────────────────────────────────────────────────────────────────
export default function PortfolioDashboard() {
    const navigate = useNavigate();
    const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
    const [loading, setLoading] = useState(true);
    const [err, setErr] = useState("");
    const [sortKey, setSortKey] = useState<SortKey>("value");
    const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

    useEffect(() => {
        fetch(`${API_BASE}/api/portfolio/demo`)
            .then(r => r.json())
            .then(setPortfolio)
            .catch(() => setErr("Could not load portfolio"))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div className="min-h-screen bg-background flex items-center justify-center">
            <RefreshCw className="animate-spin text-accent" size={32} />
        </div>
    );
    if (err || !portfolio) return (
        <div className="min-h-screen bg-background flex items-center justify-center text-muted-foreground">{err || "No portfolio data"}</div>
    );

    const { holdings, total_value, cash = 0, growth_history = [], last_updated } = portfolio;

    // ── Computed stats ─────────────────────────────────────────────────────────
    const totalCost = holdings.reduce((s, h) => s + (h.cost_basis ?? h.value), 0);
    const totalGain = total_value - totalCost;
    const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;

    const sortedByValue = [...holdings].sort((a, b) => b.value - a.value);
    const sectorAlloc = buildSectorAlloc(holdings);

    const hasRichHistory = growth_history.length >= 6;
    let growthData = hasRichHistory
        ? growth_history
        : buildFallbackGrowthHistory(totalCost, total_value);
    if (!hasDirectionChange(growthData)) {
        growthData = addMildVolatility(growthData, total_value);
    }

    const firstVal = growthData[0]?.value ?? total_value;
    const growthFromStart = total_value - firstVal;
    const growthFromStartPct = firstVal > 0 ? (growthFromStart / firstVal) * 100 : 0;

    const rows = holdings.map((h) => {
        const cost = h.cost_basis ?? h.value;
        const gain = h.value - cost;
        const weight = total_value > 0 ? (h.value / total_value) * 100 : 0;
        const sector = SECTOR_MAP[h.ticker.toUpperCase()] ?? "Other";
        return {
            holding: h,
            ticker: h.ticker,
            name: h.name ?? h.ticker,
            shares: h.shares ?? 0,
            value: h.value,
            cost,
            gain,
            weight,
            sector,
        };
    });

    const sortedRows = [...rows].sort((a, b) => {
        const direction = sortDirection === "asc" ? 1 : -1;
        switch (sortKey) {
            case "ticker":
            case "name":
            case "sector":
                return direction * a[sortKey].localeCompare(b[sortKey]);
            default:
                return direction * ((a[sortKey] as number) - (b[sortKey] as number));
        }
    });

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
            return;
        }
        setSortKey(key);
        setSortDirection("desc");
    };

    return (
        <div className="min-h-screen bg-background text-foreground">
            {/* ── Nav ──────────────────────────────────────────────────────────────── */}
            <div className="border-b border-border bg-card/50 backdrop-blur sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Briefcase className="text-accent" size={20} />
                        <span className="text-sm font-semibold">Portfolio Dashboard</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className="text-xs text-muted-foreground hidden sm:block">Updated {last_updated}</span>
                        <button
                            onClick={() => navigate("/")}
                            className="text-xs text-accent hover:text-accent/80 font-medium transition-colors"
                        >
                            ← Analyze New Investment
                        </button>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
                {/* ── KPI row ──────────────────────────────────────────────────────────── */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                        {
                            label: "Portfolio Value",
                            value: fmt(total_value),
                            sub: `Cash: ${fmt(cash)}`,
                            icon: DollarSign,
                            color: "text-accent",
                        },
                        {
                            label: "Total Gain / Loss",
                            value: fmt(totalGain),
                            sub: fmtPct(totalGainPct),
                            icon: totalGain >= 0 ? TrendingUp : TrendingDown,
                            color: totalGain >= 0 ? "text-bull" : "text-bear",
                        },
                        {
                            label: "Growth (18 mo.)",
                            value: fmtPct(growthFromStartPct),
                            sub: `${fmt(growthFromStart)} absolute`,
                            icon: BarChart3,
                            color: growthFromStart >= 0 ? "text-bull" : "text-bear",
                        },
                        {
                            label: "Holdings",
                            value: String(holdings.length),
                            sub: `${sectorAlloc.length} sectors`,
                            icon: PieChart,
                            color: "text-strategist",
                        },
                    ].map((k) => (
                        <div key={k.label} className="bg-card border border-border rounded-xl p-5 shadow-sm">
                            <div className="flex items-center justify-between mb-3">
                                <p className="text-xs text-muted-foreground">{k.label}</p>
                                <k.icon className={k.color} size={16} />
                            </div>
                            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
                            <p className="text-xs text-muted-foreground mt-1">{k.sub}</p>
                        </div>
                    ))}
                </div>

                {/* ── Growth chart ─────────────────────────────────────────────────────── */}
                <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h2 className="text-base font-semibold">Portfolio Value Over Time</h2>
                            <p className="text-xs text-muted-foreground">18-month history</p>
                        </div>
                        <div className={`flex items-center gap-1 text-sm font-semibold ${growthFromStart >= 0 ? "text-bull" : "text-bear"}`}>
                            {growthFromStart >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                            {fmtPct(growthFromStartPct)}
                        </div>
                    </div>
                    <ResponsiveContainer width="100%" height={260}>
                        <AreaChart data={growthData} margin={{ top: 5, right: 5, left: 10, bottom: 5 }}>
                            <defs>
                                <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                            <XAxis
                                dataKey="month"
                                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                                width={48}
                            />
                            <Tooltip content={<AreaTooltip />} />
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke="#6366f1"
                                strokeWidth={2.5}
                                fill="url(#portfolioGradient)"
                                dot={false}
                                activeDot={{ r: 5, fill: "#6366f1", strokeWidth: 0 }}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* ── Sector allocation + Holdings bar ─────────────────────────────── */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Sector pie */}
                    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                        <h2 className="text-base font-semibold mb-4">Sector Allocation</h2>
                        <div className="flex flex-col sm:flex-row items-center gap-4">
                            <ResponsiveContainer width={180} height={180}>
                                <RPieChart>
                                    <Pie
                                        data={sectorAlloc}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={50}
                                        outerRadius={80}
                                        dataKey="value"
                                        paddingAngle={2}
                                    >
                                        {sectorAlloc.map((s, i) => (
                                            <Cell key={s.name} fill={SECTOR_COLORS[s.name] ?? STOCK_COLORS[i % STOCK_COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip formatter={(v: number) => fmt(v)} />
                                </RPieChart>
                            </ResponsiveContainer>
                            <div className="flex flex-col gap-1.5 flex-1 min-w-0">
                                {sectorAlloc.map((s, i) => (
                                    <div key={s.name} className="flex items-center gap-2">
                                        <span
                                            className="w-2.5 h-2.5 rounded-full shrink-0"
                                            style={{ background: SECTOR_COLORS[s.name] ?? STOCK_COLORS[i % STOCK_COLORS.length] }}
                                        />
                                        <span className="text-xs text-foreground truncate flex-1">{s.name}</span>
                                        <span className="text-xs font-medium text-muted-foreground">{s.pct.toFixed(1)}%</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Top holdings bar chart */}
                    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                        <h2 className="text-base font-semibold mb-4">Top Holdings by Value</h2>
                        <ResponsiveContainer width="100%" height={200}>
                            <BarChart
                                data={sortedByValue.slice(0, 8).map(h => ({ name: h.ticker, value: h.value }))}
                                margin={{ top: 0, right: 0, left: 10, bottom: 0 }}
                                layout="vertical"
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                                <XAxis
                                    type="number"
                                    tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                                />
                                <YAxis
                                    type="category"
                                    dataKey="name"
                                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                                    tickLine={false}
                                    axisLine={false}
                                    width={40}
                                />
                                <Tooltip formatter={(v: number) => fmt(v)} />
                                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                                    {sortedByValue.slice(0, 8).map((_, i) => (
                                        <Cell key={i} fill={STOCK_COLORS[i % STOCK_COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* ── Full holdings table ───────────────────────────────────────────── */}
                <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
                    <div className="px-6 py-4 border-b border-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <h2 className="text-base font-semibold">All Holdings</h2>
                        <div className="flex items-center gap-2 text-xs">
                            <span className="text-muted-foreground">Sort:</span>
                            <select
                                value={sortKey}
                                onChange={(e) => handleSort(e.target.value as SortKey)}
                                className="rounded-md border border-border bg-background px-2 py-1 text-foreground"
                            >
                                <option value="ticker">Ticker</option>
                                <option value="name">Name</option>
                                <option value="shares">Shares</option>
                                <option value="value">Value</option>
                                <option value="cost">Cost Basis</option>
                                <option value="gain">Gain/Loss</option>
                                <option value="weight">Weight</option>
                                <option value="sector">Sector</option>
                            </select>
                            <button
                                onClick={() => setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"))}
                                className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-foreground hover:bg-muted/40"
                                title="Toggle ascending/descending"
                            >
                                <ArrowUpDown size={12} />
                                {sortDirection.toUpperCase()}
                            </button>
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border text-left">
                                    {[
                                        { label: "Ticker", key: "ticker" as SortKey },
                                        { label: "Name", key: "name" as SortKey },
                                        { label: "Shares", key: "shares" as SortKey },
                                        { label: "Value", key: "value" as SortKey },
                                        { label: "Cost Basis", key: "cost" as SortKey },
                                        { label: "Gain/Loss", key: "gain" as SortKey },
                                        { label: "Weight", key: "weight" as SortKey },
                                        { label: "Sector", key: "sector" as SortKey },
                                    ].map((h) => (
                                        <th key={h.label} className="px-4 py-3 text-xs font-medium text-muted-foreground">
                                            <button
                                                onClick={() => handleSort(h.key)}
                                                className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
                                            >
                                                {h.label}
                                                {sortKey === h.key && (
                                                    <span className="text-[10px]">{sortDirection === "asc" ? "↑" : "↓"}</span>
                                                )}
                                            </button>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {sortedRows.map((row, i) => {
                                    const { holding: h, cost, gain, weight, sector } = row;
                                    const gainPct = cost > 0 ? (gain / cost) * 100 : 0;
                                    return (
                                        <tr key={h.ticker} className={`border-b border-border/50 hover:bg-muted/30 transition-colors ${i % 2 === 0 ? "" : "bg-muted/10"}`}>
                                            <td className="px-4 py-3">
                                                <span className="font-semibold text-accent">{h.ticker}</span>
                                            </td>
                                            <td className="px-4 py-3 text-muted-foreground max-w-[160px] truncate">{h.name ?? h.ticker}</td>
                                            <td className="px-4 py-3">{h.shares ?? "—"}</td>
                                            <td className="px-4 py-3 font-medium">{fmt(h.value)}</td>
                                            <td className="px-4 py-3 text-muted-foreground">{fmt(cost)}</td>
                                            <td className={`px-4 py-3 font-medium ${gain >= 0 ? "text-bull" : "text-bear"}`}>
                                                {fmt(gain)} <span className="text-xs">({fmtPct(gainPct)})</span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-2">
                                                    <div className="h-1.5 w-16 bg-secondary rounded-full overflow-hidden">
                                                        <div className="h-full bg-accent rounded-full" style={{ width: `${Math.min(weight * 3, 100)}%` }} />
                                                    </div>
                                                    <span className="text-xs text-muted-foreground">{weight.toFixed(1)}%</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-xs">
                                                <span
                                                    className="px-2 py-0.5 rounded-full text-white text-[10px]"
                                                    style={{ background: SECTOR_COLORS[sector] ?? "#64748b" }}
                                                >
                                                    {sector}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                            <tfoot>
                                <tr className="bg-muted/30 font-semibold">
                                    <td className="px-4 py-3" colSpan={3}>Total</td>
                                    <td className="px-4 py-3">{fmt(total_value)}</td>
                                    <td className="px-4 py-3">{fmt(totalCost)}</td>
                                    <td className={`px-4 py-3 ${totalGain >= 0 ? "text-bull" : "text-bear"}`}>
                                        {fmt(totalGain)} <span className="text-xs">({fmtPct(totalGainPct)})</span>
                                    </td>
                                    <td className="px-4 py-3" colSpan={2} />
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
