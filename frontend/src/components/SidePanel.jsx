import DemographicBreakdown from "./DemographicBreakdown";
import AgentVoice from "./AgentVoice";
import LeverControls from "./LeverControls";
import VotePrediction from "./VotePrediction";
import { TrendingUp, Radio } from "lucide-react";

export default function SidePanel({ provisions, scenarioFrame, selectedGrc, grcSentiment, votePrediction, marketPrice, priceHistory, liveSentiment, onLeverChange, className }) {
  const grcData = selectedGrc ? grcSentiment[selectedGrc] : null;

  return (
    <div className={`${className} border-l border-slate-800 overflow-y-auto p-4 space-y-4`}>

      {/* Scenario frame — YES/NO outcome definitions */}
      {scenarioFrame && (
        <div className="space-y-1.5">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Scenario
          </h3>
          <p className="text-sm font-medium text-slate-200">{scenarioFrame.title}</p>
          {scenarioFrame.context && (
            <p className="text-xs text-slate-500 leading-relaxed">{scenarioFrame.context}</p>
          )}
          <div className="grid grid-cols-2 gap-1.5 mt-2">
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg px-2.5 py-2">
              <p className="text-xs font-medium text-emerald-400 mb-0.5">YES</p>
              <p className="text-xs text-slate-400 leading-relaxed">{scenarioFrame.yes_definition}</p>
            </div>
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg px-2.5 py-2">
              <p className="text-xs font-medium text-red-400 mb-0.5">NO</p>
              <p className="text-xs text-slate-400 leading-relaxed">{scenarioFrame.no_definition}</p>
            </div>
          </div>
        </div>
      )}

      {/* Policy Provisions */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
          {scenarioFrame ? "Provisions" : "Policy Provisions"}
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

      {/* Live Sentiment (from TinyFish) */}
      {liveSentiment && (
        <div className="bg-slate-900 rounded-xl p-3 border border-amber-500/20">
          <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5" /> Live Sentiment
          </h3>
          <div className="text-xs text-slate-400">
            {liveSentiment.sources_scraped} sources scraped
            <span className={`ml-2 font-mono ${liveSentiment.price_adjustment > 0 ? "text-emerald-400" : "text-red-400"}`}>
              {liveSentiment.price_adjustment > 0 ? "+" : ""}{(liveSentiment.price_adjustment * 100).toFixed(1)}%
            </span>
          </div>
          {liveSentiment.sentiments?.slice(0, 3).map((s, i) => (
            <div key={i} className="mt-1.5 text-xs text-slate-500 truncate">
              <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${
                s.sentiment === "positive" ? "bg-emerald-500" :
                s.sentiment === "negative" ? "bg-red-500" : "bg-amber-500"
              }`} />
              [{s.source}] {s.text}
            </div>
          ))}
        </div>
      )}

      {/* Market Price Overview */}
      {marketPrice && !votePrediction && (
        <div className="bg-slate-900 rounded-xl p-3 border border-slate-700">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5" /> Market Price
          </h3>
          <div className="text-center">
            <span className={`text-2xl font-bold font-mono ${
              marketPrice.market_price > 0.5 ? "text-emerald-400" : "text-red-400"
            }`}>
              {marketPrice.implied_probability_pct}%
            </span>
            <div className="text-xs text-slate-500 mt-1">{marketPrice.confidence_level} confidence</div>
          </div>
        </div>
      )}

      {/* Selected GRC Detail */}
      {grcData && (
        <>
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              {selectedGrc}
            </h3>
            {grcData.market_price != null && (
              <div className="text-xs text-slate-400 mb-2">
                GRC market price: <span className="text-emerald-400 font-mono">{(grcData.market_price * 100).toFixed(1)}%</span>
              </div>
            )}
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
