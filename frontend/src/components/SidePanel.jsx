import DemographicBreakdown from "./DemographicBreakdown";
import AgentVoice from "./AgentVoice";
import LeverControls from "./LeverControls";
import VotePrediction from "./VotePrediction";

export default function SidePanel({ provisions, selectedGrc, grcSentiment, votePrediction, onLeverChange, className }) {
  const grcData = selectedGrc ? grcSentiment[selectedGrc] : null;

  return (
    <div className={`${className} border-l border-slate-800 overflow-y-auto p-4 space-y-4`}>
      {/* Policy Summary */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
          Policy Provisions
        </h3>
        <div className="space-y-1.5">
          {provisions.length === 0 && (
            <p className="text-xs text-slate-600 italic">Upload a policy to see provisions</p>
          )}
          {provisions.map((p, i) => (
            <div key={i} className="text-sm text-slate-300 bg-slate-900 rounded-lg px-3 py-2">
              <span className="text-emerald-400 font-mono mr-2">#{p.id}</span>
              {p.title}
            </div>
          ))}
        </div>
      </div>

      {/* Selected GRC Detail */}
      {grcData && (
        <>
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              {selectedGrc}
            </h3>
            <DemographicBreakdown data={grcData} />
          </div>
          <AgentVoice agents={grcData.agents || []} />
        </>
      )}

      {/* Levers */}
      <LeverControls onLeverChange={onLeverChange} />

      {/* Vote Prediction */}
      {votePrediction && <VotePrediction data={votePrediction} />}
    </div>
  );
}
