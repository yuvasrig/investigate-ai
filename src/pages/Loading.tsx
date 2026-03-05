import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target, Loader2 } from "lucide-react";

const agents = [
  { name: "Bull Analyst", desc: "Finding growth potential...", icon: TrendingUp, color: "border-bull", bg: "bg-bull", barBg: "bg-bull" },
  { name: "Bear Analyst", desc: "Assessing risks...", icon: AlertTriangle, color: "border-bear", bg: "bg-bear", barBg: "bg-bear" },
  { name: "Portfolio Strategist", desc: "Analyzing portfolio fit...", icon: Target, color: "border-strategist", bg: "bg-strategist", barBg: "bg-strategist" },
];

const Loading = () => {
  const navigate = useNavigate();
  const [progress, setProgress] = useState([0, 0, 0]);

  useEffect(() => {
    const timers = agents.map((_, i) =>
      setTimeout(() => {
        const interval = setInterval(() => {
          setProgress((prev) => {
            const next = [...prev];
            next[i] = Math.min(next[i] + Math.random() * 15, 100);
            return next;
          });
        }, 200);
        setTimeout(() => clearInterval(interval), 2800);
        return interval;
      }, i * 800)
    );

    const nav = setTimeout(() => navigate("/results"), 4500);
    return () => {
      timers.forEach((t) => clearTimeout(t));
      clearTimeout(nav);
    };
  }, [navigate]);

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 animate-fade-in">
      <Loader2 className="text-accent animate-spin mb-6" size={40} />
      <h2 className="text-2xl font-bold text-foreground mb-2">Analyzing Investment...</h2>
      <p className="text-muted-foreground text-sm mb-10">Our AI agents are debating your investment</p>

      <div className="flex flex-col sm:flex-row gap-4 w-full max-w-3xl">
        {agents.map((a, i) => (
          <div key={a.name} className={`flex-1 bg-card rounded-lg border-l-4 ${a.color} border border-border p-5 shadow-sm`}>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-8 h-8 rounded-full ${a.bg} flex items-center justify-center`}>
                <a.icon className="text-white" size={16} />
              </div>
              <span className="text-sm font-semibold text-foreground">{a.name}</span>
            </div>
            <p className="text-xs text-muted-foreground mb-3">{a.desc}</p>
            <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
              <div
                className={`h-full rounded-full ${a.barBg} transition-all duration-300`}
                style={{ width: `${progress[i]}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground mt-8">~10-15 seconds</p>
    </div>
  );
};

export default Loading;
