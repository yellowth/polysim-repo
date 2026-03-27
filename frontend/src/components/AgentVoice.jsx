import { MessageSquareQuote } from "lucide-react";

export default function AgentVoice({ agents }) {
  // Show up to 3 sample agent quotes
  const samples = agents.filter((a) => a.reason).slice(0, 3);

  if (!samples.length) return null;

  return (
    <div>
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <MessageSquareQuote className="w-3.5 h-3.5" /> Agent Voices
      </h3>
      <div className="space-y-2">
        {samples.map((a, i) => (
          <div key={i} className="bg-slate-900 rounded-lg px-3 py-2 text-sm">
            <div className="text-slate-500 text-xs mb-1">
              {a.persona.race} · {a.persona.age} · {a.persona.occupation}
            </div>
            <p className="text-slate-300 italic">"{a.reason}"</p>
            <span className={`text-xs mt-1 inline-block px-1.5 py-0.5 rounded ${
              a.sentiment === "support" ? "bg-emerald-500/20 text-emerald-400" :
              a.sentiment === "reject" ? "bg-red-500/20 text-red-400" :
              "bg-amber-500/20 text-amber-400"
            }`}>{a.sentiment}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
