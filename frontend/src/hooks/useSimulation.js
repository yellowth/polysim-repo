import { useState, useRef, useCallback } from "react";
import { wsUrl } from "../apiConfig";

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
  // New: live agent feed and unified chart data
  const [agentHistory, setAgentHistory] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [predictionLog, setPredictionLog] = useState([]);
  // Discourse state
  const [discourseMessages, setDiscourseMessages] = useState([]);
  const [discourseRound, setDiscourseRound] = useState(-1);
  const wsRef = useRef(null);

  // Running bet totals for live price estimate during agent evaluation
  const yesBetsRef = useRef(0);
  const noBetsRef = useRef(0);
  const agentCountRef = useRef(0);

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
    setAgentHistory([]);
    setChartData([]);
    setPredictionLog([]);
    setDiscourseMessages([]);
    setDiscourseRound(-1);
    yesBetsRef.current = 0;
    noBetsRef.current = 0;
    agentCountRef.current = 0;

    const agents = agentCountOverride || 100;
    const ws = new WebSocket(wsUrl(`/ws/simulate/${policyId}?agents=${agents}`));
    wsRef.current = ws;

    ws.onopen = () => setStatus("simulating");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "config") {
        setTotalAgents(msg.data.total_agents || 100);
      }

      if (msg.type === "scraping_start") {
        setAgentHistory((prev) => [
          { _streamType: "scraping_start", topic: msg.data?.topic },
          ...prev,
        ]);
      }

      if (msg.type === "scraping_complete") {
        // Replace the scraping_start placeholder with the full result
        setAgentHistory((prev) => [
          { _streamType: "scraping_complete", data: msg.data },
          ...prev.filter((e) => e._streamType !== "scraping_start"),
        ]);
      }

      if (msg.type === "scraping_error") {
        setAgentHistory((prev) => [
          { _streamType: "scraping_error", message: msg.data?.message },
          ...prev.filter((e) => e._streamType !== "scraping_start"),
        ]);
      }

      if (msg.type === "agent_result") {
        // Accumulate running bet totals for live price estimate
        yesBetsRef.current += msg.data.yes_bet || 0;
        noBetsRef.current += msg.data.no_bet || 0;
        agentCountRef.current += 1;
        const count = agentCountRef.current;

        setAgentCount(count);
        setLatestAgent(msg.data);

        // Keep rolling history of last 60 agents (newest first)
        setAgentHistory((prev) => [msg.data, ...prev].slice(0, 60));

        // Update GRC sentiment
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

        // Sample live price every 4 agents
        if (count % 4 === 0 || count === 1) {
          const total = yesBetsRef.current + noBetsRef.current;
          if (total > 0) {
            const price = (yesBetsRef.current / total) * 100;
            setChartData((prev) => [
              ...prev,
              { x: count, price: Math.round(price * 10) / 10, phase: "agents", label: `${count}` },
            ]);
          }
        }
      }

      if (msg.type === "market_update") {
        setMarketPrice(msg.data);
        setPriceHistory((prev) => [...prev, { round: msg.round, ...msg.data }]);
        setPredictionLog((prev) => [
          ...prev,
          {
            type: "market_update",
            round: msg.round,
            market: msg.data,
          },
        ]);
        // Add initial market price as a named point
        setChartData((prev) => [
          ...prev,
          {
            x: agentCountRef.current + 1,
            price: Math.round(msg.data.market_price * 1000) / 10,
            phase: "market",
            label: "Market",
          },
        ]);
      }

      if (msg.type === "live_sentiment") {
        setLiveSentiment(msg.data);
        setPredictionLog((prev) => [
          ...prev,
          {
            type: "live_sentiment",
            data: msg.data,
          },
        ]);
      }

      if (msg.type === "discourse_start") {
        setPredictionLog((prev) => [
          ...prev,
          { type: "discourse_start", data: msg.data },
        ]);
      }

      if (msg.type === "discourse_round_start") {
        setDiscourseRound(msg.round);
        setPredictionLog((prev) => [
          ...prev,
          { type: "discourse_round_start", round: msg.round },
        ]);
      }

      if (msg.type === "discourse_message") {
        setDiscourseMessages((prev) => [msg.data, ...prev]);
      }

      if (msg.type === "discourse_debug") {
        const d = msg.data || {};
        const log =
          d.phase === "discourse_error" ? console.error.bind(console) : console.info.bind(console);
        log("[polysim:discourse]", d.phase, d.message, d);
      }

      if (msg.type === "error" && msg.phase === "simulate") {
        console.error("[polysim:simulate error]", msg.message, msg.detail || "");
      }

      if (msg.type === "contagion_round") {
        setContagionRound(msg.round);
        setGrcSentiment(msg.data);
        if (msg.market) {
          setMarketPrice(msg.market);
          setPriceHistory((prev) => [...prev, { round: msg.round + 1, ...msg.market }]);
          setChartData((prev) => [
            ...prev,
            {
              x: agentCountRef.current + 2 + msg.round,
              price: Math.round(msg.market.market_price * 1000) / 10,
              phase: `round${msg.round + 1}`,
              label: `R${msg.round + 1}`,
            },
          ]);
        }
        setPredictionLog((prev) => [
          ...prev,
          {
            type: "contagion_round",
            round: msg.round,
            market: msg.market,
          },
        ]);
      }

      if (msg.type === "vote_prediction") {
        setVotePrediction(msg.data);
        if (msg.data.market) {
          setMarketPrice(msg.data.market);
        }
        if (msg.data.price_history) {
          setPriceHistory(msg.data.price_history);
        }
        setPredictionLog((prev) => [
          ...prev,
          {
            type: "vote_prediction",
            data: msg.data,
          },
        ]);
      }

      if (msg.type === "complete") {
        setStatus("complete");
        setPredictionLog((prev) => [...prev, { type: "complete" }]);
      }
    };

    ws.onerror = () => setStatus("idle");
    ws.onclose = () => setStatus((s) => s === "simulating" ? "complete" : s);
  }, []);

  return {
    status, grcSentiment, agentCount, totalAgents, contagionRound,
    votePrediction, latestAgent, marketPrice, priceHistory, liveSentiment,
    agentHistory, chartData, predictionLog,
    discourseMessages, discourseRound,
    connect,
  };
}
