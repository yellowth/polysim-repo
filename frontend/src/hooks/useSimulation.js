import { useState, useRef, useCallback } from "react";

export default function useSimulation() {
  const [status, setStatus] = useState("idle"); // idle | connecting | simulating | complete
  const [grcSentiment, setGrcSentiment] = useState({});
  const [agentCount, setAgentCount] = useState(0);
  const [contagionRound, setContagionRound] = useState(-1);
  const [votePrediction, setVotePrediction] = useState(null);
  const wsRef = useRef(null);

  const connect = useCallback((policyId) => {
    if (wsRef.current) wsRef.current.close();

    setStatus("connecting");
    setGrcSentiment({});
    setAgentCount(0);
    setContagionRound(-1);
    setVotePrediction(null);

    const ws = new WebSocket(`ws://localhost:8000/ws/simulate/${policyId}`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("simulating");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "agent_result") {
        setAgentCount((c) => c + 1);
        // Incrementally update GRC sentiment
        const grc = msg.data.persona.grc;
        setGrcSentiment((prev) => {
          const existing = prev[grc] || { support: 0, neutral: 0, reject: 0, total: 0, agents: [] };
          const weight = msg.data.persona.weight || 1;
          return {
            ...prev,
            [grc]: {
              ...existing,
              [msg.data.sentiment]: existing[msg.data.sentiment] + weight,
              total: existing.total + weight,
              agents: [...existing.agents, msg.data],
              support_pct: null, // recalc below
            },
          };
        });
      }

      if (msg.type === "contagion_round") {
        setContagionRound(msg.round);
        setGrcSentiment(msg.data);
      }

      if (msg.type === "vote_prediction") {
        setVotePrediction(msg.data);
      }

      if (msg.type === "complete") {
        setStatus("complete");
      }
    };

    ws.onerror = () => setStatus("idle");
    ws.onclose = () => {};
  }, []);

  return { status, grcSentiment, agentCount, contagionRound, votePrediction, connect };
}
