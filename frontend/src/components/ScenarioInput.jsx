import { useState } from "react";
import { Upload, FileText, Sparkles, ChevronRight, Loader2, AlertCircle } from "lucide-react";
import { httpUrl, apiConnectionErrorHint } from "../apiConfig";

const TABS = ["scenario", "text", "pdf"];

export default function ScenarioInput({ onUpload, onScenario, onText, regionName }) {
  const [tab, setTab] = useState("scenario");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [scenarioText, setScenarioText] = useState("");
  const [policyText, setPolicyText] = useState("");
  const [interpretation, setInterpretation] = useState(null);
  const [error, setError] = useState(null);

  // ── PDF upload ──────────────────────────────────────────────────────────────
  const handleFile = async (file) => {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "txt", "md"].includes(ext)) {
      setError("Please upload a PDF, TXT, or MD file");
      return;
    }
    setError(null);
    setBusy(true);
    await onUpload(file);
    setBusy(false);
  };

  // ── Policy text ──────────────────────────────────────────────────────────────
  const handleText = async () => {
    if (!policyText.trim()) return;
    setError(null);
    setBusy(true);
    await onText(policyText);
    setBusy(false);
  };

  // ── NL scenario: interpret then hand off ─────────────────────────────────────
  const handleInterpret = async () => {
    if (!scenarioText.trim()) return;
    setError(null);
    setBusy(true);
    setInterpretation(null);
    try {
      const res = await fetch(httpUrl("/api/interpret-scenario"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: scenarioText, region: regionName }),
      });
      const data = await res.json();
      if (data.error) { setError(data.error); return; }
      setInterpretation(data);
    } catch (e) {
      setError(apiConnectionErrorHint());
    } finally {
      setBusy(false);
    }
  };

  // Pass the full API response (includes policy_id, provisions, frame)
  const handleConfirm = () => {
    if (interpretation) onScenario(interpretation);
  };

  // ── Tab label helpers ────────────────────────────────────────────────────────
  const tabLabel = { scenario: "Any Scenario", text: "Paste Policy", pdf: "Upload PDF" };
  const tabIcon = {
    scenario: <Sparkles className="w-3.5 h-3.5" />,
    text: <FileText className="w-3.5 h-3.5" />,
    pdf: <Upload className="w-3.5 h-3.5" />,
  };

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-4">
        {/* Tab bar */}
        <div className="flex gap-1 bg-slate-900 rounded-xl p-1 border border-slate-800">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(null); setInterpretation(null); }}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                tab === t
                  ? "bg-slate-800 text-slate-100"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {tabIcon[t]}
              {tabLabel[t]}
            </button>
          ))}
        </div>

        {/* ── Any Scenario tab ── */}
        {tab === "scenario" && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500">
              Describe any question or scenario — political, economic, geopolitical, social. The AI will frame it as a prediction market and extract provisions for agents to evaluate.
            </p>
            <textarea
              className="w-full h-36 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:border-slate-500"
              placeholder={
                "Examples:\n• SG govt increasing GST but providing vouchers for first year\n• SEA region aligning closer to US in trade policy\n• What's the optimal approach to affordable housing in dense cities?"
              }
              value={scenarioText}
              onChange={(e) => { setScenarioText(e.target.value); setInterpretation(null); }}
            />

            {/* Interpretation result */}
            {interpretation && (
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{interpretation.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{interpretation.domain} · {interpretation.time_horizon}</p>
                  </div>
                  <span className="text-xs px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 shrink-0">
                    Interpreted
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-2">
                    <p className="text-emerald-400 font-medium mb-0.5">YES</p>
                    <p className="text-slate-400">{interpretation.yes_definition}</p>
                  </div>
                  <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-2">
                    <p className="text-red-400 font-medium mb-0.5">NO</p>
                    <p className="text-slate-400">{interpretation.no_definition}</p>
                  </div>
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Provisions extracted</p>
                  {interpretation.provisions.map((p) => (
                    <div key={p.id} className="flex gap-2 text-xs text-slate-400 bg-slate-800/50 rounded-lg px-3 py-2">
                      <span className="text-emerald-400 font-mono shrink-0">#{p.id}</span>
                      <span><span className="text-slate-300 font-medium">{p.title}:</span> {p.summary}</span>
                    </div>
                  ))}
                </div>

                <button
                  onClick={handleConfirm}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold rounded-lg text-sm transition-colors"
                >
                  Run Simulation <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}

            {!interpretation && (
              <button
                onClick={handleInterpret}
                disabled={busy || !scenarioText.trim()}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed text-slate-950 font-semibold rounded-lg text-sm transition-colors"
              >
                {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Interpreting…</> : <><Sparkles className="w-4 h-4" /> Interpret Scenario</>}
              </button>
            )}
          </div>
        )}

        {/* ── Paste Policy tab ── */}
        {tab === "text" && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500">
              Paste a policy document, proposal, or speech. The AI will extract structured provisions.
            </p>
            <textarea
              className="w-full h-48 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:border-slate-500"
              placeholder="Paste policy text here…"
              value={policyText}
              onChange={(e) => setPolicyText(e.target.value)}
            />
            <button
              onClick={handleText}
              disabled={busy || !policyText.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed text-slate-950 font-semibold rounded-lg text-sm transition-colors"
            >
              {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Parsing…</> : <><FileText className="w-4 h-4" /> Parse Policy</>}
            </button>
          </div>
        )}

        {/* ── PDF Upload tab ── */}
        {tab === "pdf" && (
          <div
            className={`border-2 border-dashed rounded-2xl p-16 text-center transition-colors ${
              dragging ? "border-emerald-400 bg-emerald-400/5" : "border-slate-700 hover:border-slate-600"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
          >
            {busy ? (
              <>
                <Loader2 className="w-10 h-10 mx-auto mb-3 text-emerald-400 animate-spin" />
                <p className="text-slate-400 text-sm">Parsing policy document…</p>
              </>
            ) : (
              <>
                <Upload className="w-10 h-10 mx-auto mb-3 text-slate-600" />
                <p className="text-slate-300 mb-1">Drop a PDF or document here</p>
                <p className="text-sm text-slate-600 mb-6">PDF · TXT · Markdown</p>
                <input
                  type="file"
                  accept=".pdf,.txt,.md"
                  className="hidden"
                  id="file-input"
                  onChange={(e) => handleFile(e.target.files[0])}
                />
                <label
                  htmlFor="file-input"
                  className="cursor-pointer px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold rounded-lg text-sm transition-colors"
                >
                  Select file
                </label>
              </>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
