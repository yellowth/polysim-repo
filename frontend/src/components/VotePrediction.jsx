import { Vote } from "lucide-react";

export default function VotePrediction({ data }) {
  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-700">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
        <Vote className="w-3.5 h-3.5" /> Vote Prediction
      </h3>
      <div className="text-center mb-3">
        <span className={`text-3xl font-bold ${data.call === "PASS" ? "text-emerald-400" : "text-red-400"}`}>
          {data.call}
        </span>
      </div>
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
      <div className="text-center mt-2 text-xs text-slate-600">{data.total_agents} agents evaluated</div>
    </div>
  );
}
