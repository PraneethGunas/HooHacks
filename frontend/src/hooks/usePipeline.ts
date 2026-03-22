import { useCallback, useEffect, useReducer, useRef } from "react";
import { buildMockTimeline } from "@/lib/mockEvents";
import type { PipelineEvent, PipelineState, ThinkingStep } from "@/types/pipeline";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_AGENTS = ["Labor", "Consumer", "Business", "Housing"];

let _thinkingIdCounter = 0;

function buildInitialSectorAgents(): PipelineState["sectorAgents"] {
  return DEFAULT_AGENTS.reduce<PipelineState["sectorAgents"]>((acc, agent) => {
    acc[agent] = { status: "pending", toolCalls: [], report: null, agentMode: null, currentPhase: null, phaseLabel: null, thinkingSteps: [] };
    return acc;
  }, {});
}

const initialState: PipelineState = {
  status: "idle",
  query: "",
  elapsedMs: 0,
  classifierThinkingSteps: [],
  classifier: null,
  analystToolCalls: [],
  analystComplete: null,
  analystThinkingSteps: [],
  lightningPayments: [],
  sectorAgents: buildInitialSectorAgents(),
  synthesisPhase: null,
  synthesisThinkingSteps: [],
  synthesis: null,
  error: null,
  evalScores: {},
  evalPipeline: null,
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
  const prev = state.sectorAgents[agent] ?? { status: "pending" as const, toolCalls: [], report: null, agentMode: null, currentPhase: null, phaseLabel: null, thinkingSteps: [] };
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
    case "classifier_thinking": {
      const cd = event.data as any;
      const step: ThinkingStep = {
        id: ++_thinkingIdCounter,
        stepType: cd.step_type ?? "reasoning",
        content: cd.content ?? "",
        phase: cd.phase ?? "0",
        tool: cd.tool,
        timestamp: Date.now(),
      };
      return { ...state, classifierThinkingSteps: [...state.classifierThinkingSteps, step] };
    }
    case "classifier_complete":
      return { ...state, classifier: event.data };
    case "analyst_tool_call":
      return { ...state, analystToolCalls: [...state.analystToolCalls, event.data] };
    case "analyst_complete":
      return { ...state, analystComplete: event.data };
    case "analyst_thinking": {
      const ad = event.data as any;
      const step: ThinkingStep = {
        id: ++_thinkingIdCounter,
        stepType: ad.step_type ?? "reasoning",
        content: ad.content ?? "",
        phase: ad.phase ?? "0",
        tool: ad.tool,
        timestamp: Date.now(),
      };
      return { ...state, analystThinkingSteps: [...state.analystThinkingSteps, step] };
    }
    case "lightning_payment":
      return { ...state, lightningPayments: [...state.lightningPayments, event.data] };
    case "sector_agent_started":
      return setAgentStatus(state, event.data.agent, (prev) => ({
        ...prev,
        status: "running",
        agentMode: (event.data as any).agent_mode ?? prev.agentMode,
      }));
    case "sector_agent_tool_call": {
      const d = event.data as any;
      return setAgentStatus(state, event.data.agent, (prev) => ({
        ...prev,
        status: "running",
        toolCalls: [...prev.toolCalls, event.data],
        currentPhase: d.phase ?? prev.currentPhase,
        phaseLabel: d.phase_detail ?? d.query ?? prev.phaseLabel,
      }));
    }
    case "sector_agent_complete":
      return setAgentStatus(state, event.data.agent, (prev) => ({
        ...prev,
        status: "complete",
        report: event.data.report,
        agentMode: (event.data as any).agent_mode ?? event.data.report?.agent_mode ?? prev.agentMode,
      }));
    case "sector_agent_thinking": {
      const td = event.data as any;
      const step: ThinkingStep = {
        id: ++_thinkingIdCounter,
        stepType: td.step_type ?? "reasoning",
        content: td.content ?? "",
        phase: td.phase ?? "0",
        tool: td.tool,
        timestamp: Date.now(),
      };
      return setAgentStatus(state, td.agent, (prev) => ({
        ...prev,
        thinkingSteps: [...prev.thinkingSteps, step],
        currentPhase: td.phase ?? prev.currentPhase,
      }));
    }
    case "synthesis_thinking": {
      const sd = event.data as any;
      const synthStep: ThinkingStep = {
        id: ++_thinkingIdCounter,
        stepType: sd.step_type ?? "reasoning",
        content: sd.content ?? "",
        phase: sd.phase ?? "0",
        tool: sd.tool,
        timestamp: Date.now(),
      };
      return { ...state, synthesisThinkingSteps: [...state.synthesisThinkingSteps, synthStep] };
    }
    case "synthesis_phase":
      return { ...state, synthesisPhase: event.data };
    case "synthesis_complete":
      return { ...state, status: "complete", synthesis: event.data.report };
    case "pipeline_complete":
      return { ...state, status: "complete" };
    case "pipeline_error":
      return { ...state, status: "error", error: event.data.error || "Pipeline failed" };
    case "eval_score": {
      const ed = event.data as any;
      return {
        ...state,
        evalScores: {
          ...state.evalScores,
          [ed.agent]: ed,
        },
      };
    }
    case "eval_pipeline":
      return { ...state, evalPipeline: event.data as any };
    case "agent_start":
      return state;
    case "agent_result":
      return state;
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
      startTimer();

      const url = `${API_BASE}/stream?query=${encodeURIComponent(query)}`;
      let receivedAnyEvents = false;

      try {
        const es = new EventSource(url);
        esRef.current = es;

        es.addEventListener("message", (event: MessageEvent) => {
          receivedAnyEvents = true;
          try {
            const data = JSON.parse(event.data);
            dispatchEvent(data);
          } catch (err) {
            console.error("Failed to parse SSE event:", err, event.data);
          }
        });

        es.addEventListener("error", () => {
          if (!receivedAnyEvents) {
            console.log("Backend unreachable, falling back to mock events");
            if (esRef.current) {
              esRef.current.close();
              esRef.current = null;
            }
            runMockPipeline(query);
          } else {
            dispatch({ type: "pipeline/error", message: "Connection lost to backend" });
          }
        });
      } catch (err) {
        console.error("Failed to create EventSource:", err);
        runMockPipeline(query);
      }
    },
    [cleanup, startTimer, dispatchEvent, runMockPipeline],
  );

  useEffect(() => cleanup, [cleanup]);

  return { state, startPipeline };
}
