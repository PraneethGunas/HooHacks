import { useCallback, useEffect, useReducer, useRef } from "react";
import { buildMockTimeline } from "@/lib/mockEvents";
import type { PipelineEvent, PipelineState } from "@/types/pipeline";

const DEFAULT_AGENTS = ["Labor", "Consumer", "Business", "Housing"];

function buildInitialSectorAgents(): PipelineState["sectorAgents"] {
  return DEFAULT_AGENTS.reduce<PipelineState["sectorAgents"]>((acc, agent) => {
    acc[agent] = { status: "pending", toolCalls: [], report: null };
    return acc;
  }, {});
}

const initialState: PipelineState = {
  status: "idle",
  query: "",
  elapsedMs: 0,
  classifier: null,
  analystToolCalls: [],
  analystComplete: null,
  lightningPayments: [],
  sectorAgents: buildInitialSectorAgents(),
  challenges: [],
  rebuttals: [],
  synthesis: null,
  error: null,
};

type PipelineAction =
  | { type: "pipeline/start"; query: string }
  | { type: "pipeline/elapsed"; elapsedMs: number }
  | { type: "pipeline/event"; event: PipelineEvent }
  | { type: "pipeline/error"; message: string };

function setAgentStatus(
  state: PipelineState,
  agent: string,
  updater: (prev: PipelineState["sectorAgents"][string]) => PipelineState["sectorAgents"][string],
): PipelineState {
  const prev = state.sectorAgents[agent] ?? { status: "pending" as const, toolCalls: [], report: null };
  return {
    ...state,
    sectorAgents: {
      ...state.sectorAgents,
      [agent]: updater(prev),
    },
  };
}

function applyEvent(state: PipelineState, event: PipelineEvent): PipelineState {
  switch (event.type) {
    case "classifier_complete":
      return { ...state, classifier: event.data };
    case "analyst_tool_call":
      return { ...state, analystToolCalls: [...state.analystToolCalls, event.data] };
    case "analyst_complete":
      return { ...state, analystComplete: event.data };
    case "lightning_payment":
      return { ...state, lightningPayments: [...state.lightningPayments, event.data] };
    case "sector_agent_started":
      return setAgentStatus(state, event.data.agent, (prev) => ({ ...prev, status: "running" }));
    case "sector_agent_tool_call":
      return setAgentStatus(state, event.data.agent, (prev) => ({
        ...prev,
        status: "running",
        toolCalls: [...prev.toolCalls, event.data],
      }));
    case "sector_agent_complete":
      return setAgentStatus(state, event.data.agent, (prev) => ({
        ...prev,
        status: "complete",
        report: event.data.report,
      }));
    case "debate_challenge":
      return { ...state, challenges: [...state.challenges, event.data.challenge] };
    case "revision_complete":
      return { ...state, rebuttals: [...state.rebuttals, event.data.rebuttal] };
    case "synthesis_complete":
      return { ...state, status: "complete", synthesis: event.data.report };
    case "error":
      return { ...state, status: "error", error: event.data.message };
    default:
      return state;
  }
}

function reducer(state: PipelineState, action: PipelineAction): PipelineState {
  switch (action.type) {
    case "pipeline/start":
      return {
        ...initialState,
        status: "running",
        query: action.query,
        sectorAgents: buildInitialSectorAgents(),
      };
    case "pipeline/elapsed":
      return { ...state, elapsedMs: action.elapsedMs };
    case "pipeline/event":
      return applyEvent(state, action.event);
    case "pipeline/error":
      return { ...state, status: "error", error: action.message };
    default:
      return state;
  }
}

export function usePipeline() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const esRef = useRef<EventSource | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mockTimeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const startRef = useRef<number>(0);

  const cleanup = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    mockTimeoutsRef.current.forEach((timeout) => clearTimeout(timeout));
    mockTimeoutsRef.current = [];
  }, []);

  const startTimer = useCallback(() => {
    startRef.current = Date.now();
    timerRef.current = setInterval(() => {
      dispatch({ type: "pipeline/elapsed", elapsedMs: Date.now() - startRef.current });
    }, 200);
  }, []);

  const dispatchEvent = useCallback(
    (event: PipelineEvent) => {
      dispatch({ type: "pipeline/event", event });
      if (event.type === "synthesis_complete" || event.type === "error") {
        cleanup();
      }
    },
    [cleanup],
  );

  const runMockPipeline = useCallback(
    (query: string) => {
      startTimer();
      const timeline = buildMockTimeline(query);
      mockTimeoutsRef.current = timeline.map(({ delayMs, event }) =>
        setTimeout(() => dispatchEvent(event), delayMs),
      );
    },
    [dispatchEvent, startTimer],
  );

  const startPipeline = useCallback(
    async (query: string) => {
      cleanup();
      dispatch({ type: "pipeline/start", query });

      // Demo mode: backend is temporarily disabled, so we always replay mock events.
      runMockPipeline(query);
    },
    [cleanup, runMockPipeline],
  );

  useEffect(() => cleanup, [cleanup]);

  return { state, startPipeline };
}
