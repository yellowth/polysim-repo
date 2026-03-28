import { useState } from "react";
import Header from "./components/Header";
import MapView from "./components/MapView";
import SidePanel from "./components/SidePanel";
import ScenarioInput from "./components/ScenarioInput";
// Stage A (region/segment config) commented out — defaulting to Singapore demographics
// import RegionConfigPanel from "./components/RegionConfigPanel";
import SimulationProgress from "./components/SimulationProgress";
import useSimulation from "./hooks/useSimulation";

// App flow:
//   "input"    — Stage B: scenario/policy input (ScenarioInput) — starts here (SG defaults)
//   "simulate" — simulation running/complete view
//
// Stage A (RegionConfigPanel — custom demographic segmentation) is temporarily disabled.
// The app defaults to Singapore demographics (config.py SINGAPORE + data/grc_profiles.json).
export default function App() {
  const [step, setStep] = useState("input"); // skip Stage A — start directly at input
  const [policyId, setPolicyId] = useState(null);
  const [provisions, setProvisions] = useState([]);
  const [scenarioFrame, setScenarioFrame] = useState(null);
  const [regionConfig, setRegionConfig] = useState(null); // null = use SG defaults
  const [selectedGrc, setSelectedGrc] = useState(null);
  const sim = useSimulation();

  // ── Stage A: region config (disabled — kept for future re-enable) ────────────
  // const handleConfigApply = (config) => {
  //   setRegionConfig(config);
  //   setStep("input");
  // };
  //
  // const handleConfigSkip = () => {
  //   setRegionConfig(null);
  //   setStep("input");
  // };

  // ── Stage B: upload PDF ──────────────────────────────────────────────────────
  const handleUpload = async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("http://localhost:8000/api/upload", { method: "POST", body: form });
    const data = await res.json();
    await _applyConfigAndProceed(data.policy_id, data.provisions, null);
  };

  // ── Stage B: paste text ──────────────────────────────────────────────────────
  const handleText = async (text) => {
    const res = await fetch("http://localhost:8000/api/upload-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    await _applyConfigAndProceed(data.policy_id, data.provisions, null);
  };

  // ── Stage B: NL scenario interpreted ────────────────────────────────────────
  const handleScenario = async (response) => {
    const pid = response.policy_id;
    if (!pid) return;
    await _applyConfigAndProceed(pid, response.provisions, response.frame);
  };

  // ── Attach region config if one was configured, then proceed ─────────────────
  const _applyConfigAndProceed = async (pid, provs, frame) => {
    if (regionConfig?.config_id) {
      await fetch(`http://localhost:8000/api/apply-config/${pid}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config_id: regionConfig.config_id }),
      });
    }
    setPolicyId(pid);
    setProvisions(provs || []);
    setScenarioFrame(frame);
    setStep("simulate");
  };

  // ── Simulation controls ──────────────────────────────────────────────────────
  const handleSimulate = () => {
    if (policyId) sim.connect(policyId);
  };

  const handleLeverChange = async (lever, value) => {
    const res = await fetch(
      `http://localhost:8000/api/adjust/${policyId}?lever=${lever}&value=${value}`,
      { method: "POST" }
    );
    const data = await res.json();
    setPolicyId(data.policy_id);
    sim.connect(data.policy_id);
  };

  const handleReset = () => {
    setStep("input"); // Stage A disabled — reset to input
    setPolicyId(null);
    setProvisions([]);
    setScenarioFrame(null);
    setRegionConfig(null);
    setSelectedGrc(null);
  };

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-100">
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <Header onReset={step === "simulate" ? handleReset : undefined} />

      {/* Stage A (RegionConfigPanel) disabled — using Singapore demographics by default */}
      {/* {step === "config" && (
        <RegionConfigPanel
          onApply={handleConfigApply}
          onSkip={handleConfigSkip}
        />
      )} */}

      {step === "input" && (
        <ScenarioInput
          onUpload={handleUpload}
          onText={handleText}
          onScenario={handleScenario}
          regionName={regionConfig?.config?.name}
        />
      )}

      {step === "simulate" && (
        <>
          <SimulationProgress
            status={sim.status}
            agentCount={sim.agentCount}
            totalAgents={sim.totalAgents}
            contagionRound={sim.contagionRound}
            onSimulate={handleSimulate}
            marketPrice={sim.marketPrice}
            scenarioTitle={scenarioFrame?.title}
          />
          <main className="flex-1 flex overflow-hidden">
            {/* Left: Map */}
            <MapView
              grcSentiment={sim.grcSentiment}
              selectedGrc={selectedGrc}
              onSelectGrc={setSelectedGrc}
              className="w-[57%]"
            />
            {/* Right: Market Chart + Stream + Details */}
            <SidePanel
              provisions={provisions}
              scenarioFrame={scenarioFrame}
              selectedGrc={selectedGrc}
              grcSentiment={sim.grcSentiment}
              votePrediction={sim.votePrediction}
              marketPrice={sim.marketPrice}
              priceHistory={sim.priceHistory}
              liveSentiment={sim.liveSentiment}
              onLeverChange={handleLeverChange}
              className="w-[43%]"
              chartData={sim.chartData}
              agentHistory={sim.agentHistory}
              status={sim.status}
              agentCount={sim.agentCount}
              totalAgents={sim.totalAgents}
              contagionRound={sim.contagionRound}
              predictionLog={sim.predictionLog}
            />
          </main>
        </>
      )}
    </div>
  );
}
