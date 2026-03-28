import { Vote, TrendingUp, TrendingDown } from "lucide-react";

export default function VotePrediction({ data }) {
  const market = data.market;
  const history = data.price_history || [];

  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
        <Vote className="w-3.5 h-3.5" /> Market Prediction
      </h3>

      {/* Market Price (hero) */}
      {market && (
        <div className="text-center mb-3">
          <div className="text-xs text-slate-500 mb-1">Market Clearing Price</div>
          <span className={`text-4xl font-bold font-mono ${
            market.market_price > 0.5 ? "text-emerald-400" : "text-red-400"
          }`}>
            {market.implied_probability_pct}%
          </span>
          <div className="text-xs text-slate-500 mt-1">
            {market.confidence_level} confidence · {market.active_bettors} bettors
          </div>
        </div>
      )}

      {/* Price History mini-chart */}
      {history.length > 1 && (
        <div className="mb-3">
          <div className="text-xs text-slate-500 mb-1.5">Price Evolution</div>
          <div className="flex items-end gap-1 h-12">
            {history.map((h, i) => {
              const pct = (h.market_price || 0.5) * 100;
              const height = Math.max(10, pct);
              const isLast = i === history.length - 1;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                  <div
                    className={`w-full rounded-t transition-all ${
                      pct > 50 ? "bg-emerald-500/60" : "bg-red-500/60"
                    } ${isLast ? "ring-1 ring-emerald-400" : ""}`}
                    style={{ height: `${height}%` }}
                    title={`Round ${h.round}: ${pct.toFixed(1)}%`}
                  />
                  <span className="text-[9px] text-slate-600">R{h.round}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Call */}
      <div className="text-center mb-3">
        <span className={`text-2xl font-bold ${data.call === "PASS" ? "text-emerald-400" : "text-red-400"}`}>
          {data.call}
        </span>
      </div>

      {/* Vote breakdown */}
      <div className="flex gap-2 text-center text-sm">
        <div className="flex-1 bg-emerald-500/10 rounded-lg py-2">
          <div className="text-emerald-400 font-semibold">{data.for_pct}%</div>
          <div className="text-slate-500 text-xs">For</div>
        </div>
        <div className="flex-1 bg-red-500/10 rounded-lg py-2">
          <div className="text-red-400 font-semibold">{data.against_pct}%</div>
          <div className="text-slate-500 text-xs">Against</div>
        </div>
        <div className="flex-1 bg-slate-700/30 rounded-lg py-2">
          <div className="text-slate-300 font-semibold">{data.undecided_pct}%</div>
          <div className="text-slate-500 text-xs">Undecided</div>
        </div>
      </div>

      {/* Volume info */}
      {market && (
        <div className="mt-2 flex justify-between text-xs text-slate-600">
          <span>{data.total_agents} agents</span>
          <span>Vol: {market.total_volume?.toLocaleString() || 0} tokens</span>
        </div>
      )}
    </div>
  );
}
