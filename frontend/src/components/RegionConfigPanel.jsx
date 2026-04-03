import { useState, useRef, useEffect } from "react";
import { httpUrl } from "../apiConfig";
import { Loader2, Globe, ChevronRight, RotateCcw, AlertCircle, Info, Search, CheckCircle, Zap } from "lucide-react";

const PRESETS = [
  { label: "Singapore (default)", value: "Singapore demographics — Chinese, Malay, Indian, Others segments by GRC constituency" },
  { label: "US by state", value: "United States segmented by major states/regions — research actual state populations, income distributions, and demographics" },
  { label: "Southeast Asia", value: "Southeast Asia: Singapore, Malaysia, Thailand, Philippines, Indonesia, Vietnam — research population shares and demographics" },
  { label: "Income class", value: "Singapore segmented by income class: lower class, working class, middle class, upper middle, elite — with real income distribution data" },
  { label: "Political ideology", value: "Segment by political leaning: progressive, centre-left, centrist, centre-right, conservative — Singapore context" },
  { label: "Life stage", value: "Segment by life stage: Gen Z (18-25), young professionals (26-35), families (36-50), pre-retirement (51-65), seniors (65+)" },
];

// Parse SSE stream from fetch response
async function* readSSE(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // keep incomplete last line
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try { yield JSON.parse(line.slice(6)); } catch {}
      }
    }
  }
}

// ── Console log entry types ──────────────────────────────────────────────────
function LogLine({ entry }) {
  if (entry.type === "plan") return (
    <div className="flex gap-2 text-xs">
      <Globe className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
      <span className="text-emerald-300">{entry.message}</span>
      {!entry.has_tinyfish && (
        <span className="text-amber-500 ml-1">(knowledge-only mode)</span>
      )}
    </div>
  );

  if (entry.type === "search_start") return (
    <div className="flex gap-2 text-xs items-start">
      <Search className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5 animate-pulse" />
      <div>
        <span className="text-amber-300 font-medium">{entry.label}</span>
        <span className="text-slate-600 ml-2 font-mono truncate max-w-xs inline-block align-bottom">
          {entry.url}
        </span>
      </div>
    </div>
  );

  if (entry.type === "search_result") return (
    <div className="flex gap-2 text-xs items-start ml-5">
      {entry.success
        ? <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
        : <AlertCircle className="w-3 h-3 text-red-500 shrink-0 mt-0.5" />}
      <span className={entry.success ? "text-slate-400" : "text-red-400"}>
        {entry.snippet}
      </span>
    </div>
  );

  if (entry.type === "narrate") return (
    <div className="flex gap-2 text-xs items-start ml-5">
      {entry.is_error
        ? <AlertCircle className="w-3 h-3 text-red-400 shrink-0 mt-0.5" />
        : <Zap className="w-3 h-3 text-sky-400 shrink-0 mt-0.5" />}
      <span className={entry.is_error ? "text-red-400" : "text-sky-300 italic"}>{entry.text}</span>
    </div>
  );

  if (entry.type === "synthesis_start") return (
    <div className="flex gap-2 text-xs items-center">
      <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin shrink-0" />
      <span className="text-purple-300">
        Synthesising{entry.live_results > 0 ? ` ${entry.live_results} live result${entry.live_results > 1 ? "s" : ""}` : " (no live data — using GPT-4o knowledge)"}…
        {entry.failed > 0 && <span className="text-red-400 ml-1">{entry.failed} search{entry.failed > 1 ? "es" : ""} failed.</span>}
      </span>
    </div>
  );

  return null;
}

export default function RegionConfigPanel({ onApply, onSkip }) {
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState([]);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

  const handleGenerate = async () => {
    if (!description.trim() || busy) return;
    setError(null);
    setConfig(null);
    setLog([]);
    setBusy(true);

    try {
      const response = await fetch(httpUrl("/api/configure-region/stream"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      });

      if (!response.ok) {
        setError(`Server error: ${response.status}`);
        return;
      }

      for await (const event of readSSE(response)) {
        if (event.type === "error") {
          setError(event.message);
          break;
        }
        if (event.type === "complete") {
          setConfig(event);
          // Don't add to log — show as the result panel below
        } else {
          setLog((prev) => [...prev, event]);
        }
      }
    } catch (e) {
      setError("Could not reach the server");
    } finally {
      setBusy(false);
    }
  };

  const handleReset = () => {
    setConfig(null);
    setLog([]);
    setError(null);
  };

  const handleApply = () => {
    if (config) onApply({ config_id: config.config_id, config: config.config });
  };

  const segmentsMeta = config?.config?._segments_meta || [];
  const totalWeight = segmentsMeta.reduce((s, seg) => s + (seg.weight || 0), 0);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl w-full mx-auto space-y-4 px-8 py-8">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Globe className="w-4 h-4 text-emerald-400" />
            <h2 className="text-base font-semibold text-slate-100">Stage A — Configure Segments</h2>
            <span className="text-xs text-slate-600 ml-auto">optional</span>
          </div>
          <p className="text-xs text-slate-500">
            Describe the population or segmentation approach. TinyFish researches real demographic data from the web, then GPT-4o synthesises into agent segments.
          </p>
        </div>

        {/* Presets */}
        <div className="flex flex-wrap gap-1.5">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => { setDescription(p.value); handleReset(); }}
              className="text-xs px-2.5 py-1 rounded-full border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-300 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Input */}
        <textarea
          className="w-full h-20 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:border-slate-500"
          placeholder="e.g. US segmented by state, Southeast Asia by country, Singapore income classes…"
          value={description}
          onChange={(e) => { setDescription(e.target.value); handleReset(); }}
        />

        <button
          onClick={handleGenerate}
          disabled={busy || !description.trim()}
          className="w-full flex items-center justify-center gap-2 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-100 font-medium rounded-lg text-sm transition-colors border border-slate-700"
        >
          {busy
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Researching…</>
            : <><Globe className="w-4 h-4" /> Research &amp; Generate</>}
        </button>

        {/* Live research console */}
        {log.length > 0 && (
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2 font-mono">
            <p className="text-xs text-slate-600 mb-2 font-sans">Research console</p>
            {log.map((entry, i) => <LogLine key={i} entry={entry} />)}
            {busy && (
              <div className="flex gap-2 items-center text-xs text-slate-600">
                <span className="inline-block w-1.5 h-3 bg-slate-600 animate-pulse rounded-sm" />
              </div>
            )}
            <div ref={logEndRef} />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
          </div>
        )}

        {/* Generated config result */}
        {config && (
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-100">{config.config?.name}</p>
                {config.config?.confidence_note && (
                  <p className="text-xs text-slate-500 mt-0.5">{config.config.confidence_note}</p>
                )}
              </div>
              <button onClick={handleReset} className="text-slate-600 hover:text-slate-400 shrink-0" title="Reset">
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Segment cards */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                {segmentsMeta.length} segments
              </p>
              {segmentsMeta.map((seg) => (
                <div key={seg.key} className="bg-slate-800/60 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-200">{seg.label}</span>
                    <span className="text-xs text-slate-500 font-mono">
                      {totalWeight > 0 ? ((seg.weight / totalWeight) * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                  <div className="w-full h-1 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: totalWeight > 0 ? `${(seg.weight / totalWeight) * 100}%` : "0%" }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>Risk: <span className="text-slate-400 font-mono">{seg.risk_appetite?.toFixed(2)}</span></span>
                    {seg.description && (
                      <span className="text-slate-600 text-right max-w-xs truncate">{seg.description}</span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {(seg.concerns || []).slice(0, 4).map((c) => (
                      <span key={c} className="text-xs px-1.5 py-0.5 bg-slate-700 text-slate-400 rounded">{c}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {config.config?.confidence_note && (
              <div className="flex gap-2 text-xs text-slate-500 bg-amber-500/5 border border-amber-500/15 rounded-lg px-3 py-2">
                <Info className="w-3.5 h-3.5 text-amber-500/60 shrink-0 mt-0.5" />
                {config.config.confidence_note}
              </div>
            )}

            <button
              onClick={handleApply}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold rounded-lg text-sm transition-colors"
            >
              Apply &amp; Continue <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Skip */}
        <button
          onClick={onSkip}
          className="w-full text-xs text-slate-600 hover:text-slate-400 transition-colors py-1"
        >
          Skip — use Singapore defaults →
        </button>
      </div>
    </div>
  );
}
