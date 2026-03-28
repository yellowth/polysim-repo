import { useState, useRef, useCallback } from "react";

export default function useSimulation() {
  const [status, setStatus] = useState("idle"); // idle | connecting | simulating | complete
  const [grcSentiment, setGrcSentiment] = useState({});
  const [agentCount, setAgentCount] = useState(0);
  const [totalAgents, setTotalAgents] = useState(100);
  const [contagionRound, setContagionRound] = useState(-1);
  const [votePrediction, setVotePrediction] = useState(null);
  const [latestAgent, setLatestAgent] = useState(null);
  const [marketPrice, setMarketPrice] = useState(null);
  const [priceHistory, setPriceHistory] = useState([]);
  const [liveSentiment, setLiveSentiment] = useState(null);
  const wsRef = useRef(null);

  const connect = useCallback((policyId, agentCountOverride) => {
    if (wsRef.current) wsRef.current.close();

    setStatus("connecting");
    setGrcSentiment({});
    setAgentCount(0);
    setContagionRound(-1);
    setVotePrediction(null);
    setLatestAgent(null);
    setMarketPrice(null);
    setPriceHistory([]);
    setLiveSentiment(null);

    const agents = agentCountOverride || 100;
    const ws = new WebSocket(`ws://localhost:8000/ws/simulate/${policyId}?agents=${agents}`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("simulating");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "config") {
        setTotalAgents(msg.data.total_agents || 100);
      }

      if (msg.type === "agent_result") {
        setAgentCount((c) => c + 1);
        setLatestAgent(msg.data);
        const grc = msg.data.persona.grc;
        setGrcSentiment((prev) => {
          const existing = prev[grc] || { support: 0, neutral: 0, reject: 0, total: 0, agents: [], yes_bets: 0, no_bets: 0 };
          const weight = msg.data.persona.weight || 1;
          return {
            ...prev,
            [grc]: {
              ...existing,
              [msg.data.sentiment]: existing[msg.data.sentiment] + weight,
              total: existing.total + weight,
              agents: [...existing.agents, msg.data],
              yes_bets: existing.yes_bets + (msg.data.yes_bet || 0),
              no_bets: existing.no_bets + (msg.data.no_bet || 0),
            },
          };
        });
      }

      if (msg.type === "market_update") {
        setMarketPrice(msg.data);
        setPriceHistory((prev) => [...prev, { round: msg.round, ...msg.data }]);
      }

      if (msg.type === "live_sentiment") {
        setLiveSentiment(msg.data);
      }

      if (msg.type === "contagion_round") {
        setContagionRound(msg.round);
        setGrcSentiment(msg.data);
        if (msg.market) {
          setMarketPrice(msg.market);
          setPriceHistory((prev) => [...prev, { round: msg.round + 1, ...msg.market }]);
        }
      }

      if (msg.type === "vote_prediction") {
        setVotePrediction(msg.data);
        if (msg.data.market) {
          setMarketPrice(msg.data.market);
        }
        if (msg.data.price_history) {
          setPriceHistory(msg.data.price_history);
        }
      }

      if (msg.type === "complete") {
        setStatus("complete");
      }
    };

    ws.onerror = () => setStatus("idle");
    ws.onclose = () => {};
  }, []);

  return {
    status, grcSentiment, agentCount, totalAgents, contagionRound,
    votePrediction, latestAgent, marketPrice, priceHistory, liveSentiment,
    connect,
  };
}
