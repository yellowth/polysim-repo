import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

const PHASE_COLORS = {
  agents: "#64748b",
  market: "#f59e0b",
  round1: "#6366f1",
  round2: "#8b5cf6",
  round3: "#a78bfa",
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-slate-400 mb-1">{d.label}</div>
      <div className={`font-mono font-bold text-lg ${d.price >= 50 ? "text-emerald-400" : "text-red-400"}`}>
        {d.price.toFixed(1)}%
      </div>
      {d.phase !== "agents" && (
        <div className="text-slate-500 mt-0.5">
          {d.phase === "market" ? "Initial market" : `Contagion ${d.phase.replace("round", "round ")}`}
        </div>
      )}
    </div>
  );
}

function CustomDot({ cx, cy, payload }) {
  if (payload.phase === "agents") return null;
  const color = PHASE_COLORS[payload.phase] || "#64748b";
  return (
    <circle cx={cx} cy={cy} r={5} fill={color} stroke="#0f172a" strokeWidth={2} />
  );
}

export default function LiveMarketChart({ chartData, marketPrice, status, contagionRound }) {
  const current = marketPrice?.market_price != null ? marketPrice.market_price * 100 : null;
  const prev = chartData.length >= 2 ? chartData[chartData.length - 2]?.price : null;
  const trend = current != null && prev != null ? current - prev : 0;

  const isPass = current != null && current >= 50;

  return (
    <div className="flex flex-col h-full bg-slate-900/80 border-b border-slate-800">
      {/* Hero price */}
      <div className="flex items-start justify-between px-4 pt-3 pb-1 shrink-0">
        <div>
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-0.5">
            Market Price
          </div>
          <div className="flex items-baseline gap-2">
            {current != null ? (
              <>
                <span className={`text-3xl font-black font-mono tabular-nums ${isPass ? "text-emerald-400" : "text-red-400"}`}>
                  {current.toFixed(1)}%
                </span>
                <span className={`text-sm font-mono flex items-center gap-0.5 ${trend > 0 ? "text-emerald-400" : trend < 0 ? "text-red-400" : "text-slate-500"}`}>
                  {trend > 0 ? <TrendingUp className="w-3.5 h-3.5" /> : trend < 0 ? <TrendingDown className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" />}
                  {trend !== 0 ? `${trend > 0 ? "+" : ""}${trend.toFixed(1)}` : "—"}
                </span>
              </>
            ) : (
              <span className="text-3xl font-black font-mono text-slate-700">—.—%</span>
            )}
          </div>
        </div>

        <div className="text-right">
          {marketPrice && (
            <>
              <div className={`text-sm font-bold px-2.5 py-0.5 rounded-full border ${
                isPass
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : "bg-red-500/10 border-red-500/30 text-red-400"
              }`}>
                {isPass ? "PASS" : "FAIL"}
              </div>
              <div className="text-[10px] text-slate-600 mt-1">{marketPrice.confidence_level}</div>
            </>
          )}
          {status === "simulating" && contagionRound >= 0 && (
            <div className="text-[10px] text-indigo-400 mt-1 font-mono">
              Round {contagionRound + 1}/3 propagating
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 min-h-0 px-1 pb-2">
        {chartData.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-slate-700 text-xs">Awaiting agent data…</div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
              <defs>
                {/* Vertical stroke gradient: green at top (100%), amber at 50%, red at bottom (0%) */}
                <linearGradient id="priceStrokeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" />
                  <stop offset="50%" stopColor="#f59e0b" />
                  <stop offset="100%" stopColor="#ef4444" />
                </linearGradient>
                {/* Area fill: subtle version of the same */}
                <linearGradient id="priceAreaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.22} />
                  <stop offset="50%" stopColor="#f59e0b" stopOpacity={0.08} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0.18} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 9, fill: "#475569" }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 9, fill: "#475569" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={50}
                stroke="#334155"
                strokeDasharray="4 4"
                strokeWidth={1}
                label={{ value: "50%", fontSize: 9, fill: "#475569", position: "insideTopLeft" }}
              />
              <Area
                type="monotoneX"
                dataKey="price"
                stroke="url(#priceStrokeGradient)"
                strokeWidth={2.5}
                fill="url(#priceAreaGradient)"
                dot={<CustomDot />}
                activeDot={{ r: 4, stroke: "#0f172a", strokeWidth: 2 }}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Round legend */}
      {chartData.some((d) => d.phase !== "agents") && (
        <div className="flex items-center gap-3 px-4 pb-2 shrink-0">
          {[
            { phase: "market", label: "Market" },
            { phase: "round1", label: "R1" },
            { phase: "round2", label: "R2" },
            { phase: "round3", label: "R3" },
          ]
            .filter((l) => chartData.some((d) => d.phase === l.phase))
            .map((l) => (
              <div key={l.phase} className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full" style={{ background: PHASE_COLORS[l.phase] }} />
                <span className="text-[9px] text-slate-600">{l.label}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
