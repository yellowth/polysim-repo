import { useState } from "react";
import Header from "./components/Header";
import MapView from "./components/MapView";
import SidePanel from "./components/SidePanel";
import PolicyUpload from "./components/PolicyUpload";
import SimulationProgress from "./components/SimulationProgress";
import useSimulation from "./hooks/useSimulation";

export default function App() {
  const [policyId, setPolicyId] = useState(null);
  const [provisions, setProvisions] = useState([]);
  const [selectedGrc, setSelectedGrc] = useState(null);
  const sim = useSimulation();

  const handleUpload = async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("http://localhost:8000/api/upload", { method: "POST", body: form });
    const data = await res.json();
    setPolicyId(data.policy_id);
    setProvisions(data.provisions);
  };

  const handleSimulate = () => {
    if (policyId) sim.connect(policyId);
  };

  const handleLeverChange = async (lever, value) => {
    const res = await fetch(`http://localhost:8000/api/adjust/${policyId}?lever=${lever}&value=${value}`, { method: "POST" });
    const data = await res.json();
    setPolicyId(data.policy_id);
    sim.connect(data.policy_id);
  };

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-100">
      <Header />
      {!policyId ? (
        <PolicyUpload onUpload={handleUpload} />
      ) : (
        <>
          <SimulationProgress
            status={sim.status}
            agentCount={sim.agentCount}
            contagionRound={sim.contagionRound}
            onSimulate={handleSimulate}
          />
          <main className="flex-1 flex overflow-hidden">
            <MapView
              grcSentiment={sim.grcSentiment}
              selectedGrc={selectedGrc}
              onSelectGrc={setSelectedGrc}
              className="w-2/3"
            />
            <SidePanel
              provisions={provisions}
              selectedGrc={selectedGrc}
              grcSentiment={sim.grcSentiment}
              votePrediction={sim.votePrediction}
              onLeverChange={handleLeverChange}
              className="w-1/3"
            />
          </main>
        </>
      )}
    </div>
  );
}
