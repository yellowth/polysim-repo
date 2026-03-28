function ArcGauge({ pct, isPass }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const filled = (pct / 100) * circumference;
  const color = isPass ? "#22c55e" : "#ef4444";

  return (
    <svg width="72" height="72" className="shrink-0" style={{ transform: "rotate(-90deg)" }}>
      <circle cx="36" cy="36" r={radius} fill="none" stroke="#1e293b" strokeWidth="7" />
      <circle
        cx="36" cy="36" r={radius}
        fill="none"
        stroke={color}
        strokeWidth="7"
        strokeLinecap="round"
        strokeDasharray={`${filled} ${circumference - filled}`}
        style={{ transition: "stroke-dasharray 0.8s ease" }}
      />
      <text
        x="36" y="40"
        textAnchor="middle"
        fill={color}
        fontSize="13"
        fontWeight="800"
        fontFamily="monospace"
        style={{ transform: "rotate(90deg)", transformOrigin: "36px 36px" }}
      >
        {pct}%
      </text>
    </svg>
  );
}

export default function VotePrediction({ data }) {
  const market = data.market;
  const pct = market ? Math.round(market.market_price * 1000) / 10 : 0;
  const isPass = pct >= 50;

  return (
    <div className="bg-slate-900/80 rounded-xl border border-slate-700/60 overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 border-b border-slate-800/50">
        <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
          Final Prediction
        </div>
      </div>

      {/* Market price + gauge */}
      {market && (
        <div className="flex items-center gap-4 px-4 py-3">
          <ArcGauge pct={pct} isPass={isPass} />
          <div>
            <div className={`text-4xl font-black font-mono tabular-nums leading-none ${isPass ? "text-emerald-400" : "text-red-400"}`}>
              {pct}%
            </div>
            <div className={`text-sm font-bold mt-1 ${isPass ? "text-emerald-400" : "text-red-400"}`}>
              {isPass ? "PASS" : "FAIL"}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              {market.confidence_level} · {market.active_bettors} bettors
            </div>
          </div>
        </div>
      )}

      {/* Vote breakdown */}
      <div className="px-4 pb-3">
        <div className="flex gap-1.5 text-center text-xs mb-2">
          <div className="flex-1 bg-emerald-500/10 rounded-lg py-2 border border-emerald-500/20">
            <div className="text-emerald-400 font-bold font-mono">{data.for_pct}%</div>
            <div className="text-slate-600 text-[9px] mt-0.5">For</div>
          </div>
          <div className="flex-1 bg-red-500/10 rounded-lg py-2 border border-red-500/20">
            <div className="text-red-400 font-bold font-mono">{data.against_pct}%</div>
            <div className="text-slate-600 text-[9px] mt-0.5">Against</div>
          </div>
          <div className="flex-1 bg-slate-800/40 rounded-lg py-2 border border-slate-700/40">
            <div className="text-slate-400 font-bold font-mono">{data.undecided_pct}%</div>
            <div className="text-slate-600 text-[9px] mt-0.5">Undecided</div>
          </div>
        </div>

        {/* Stacked bar */}
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden flex">
          <div className="bg-emerald-500 h-full transition-all duration-700" style={{ width: `${data.for_pct}%` }} />
          <div className="bg-slate-600 h-full transition-all duration-700" style={{ width: `${data.undecided_pct}%` }} />
          <div className="bg-red-500 h-full transition-all duration-700" style={{ width: `${data.against_pct}%` }} />
        </div>

        {market && (
          <div className="mt-2 flex justify-between text-[9px] text-slate-700">
            <span>{data.total_agents} agents</span>
            <span>Vol: {market.total_volume?.toLocaleString() || 0} tokens</span>
          </div>
        )}
      </div>
    </div>
  );
}
