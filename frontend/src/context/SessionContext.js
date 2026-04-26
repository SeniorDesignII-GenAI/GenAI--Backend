/**
 * SessionContext — shared state across the pipeline pages.
 *
 * Only lightweight scalar fields are persisted to sessionStorage to avoid
 * hitting the ~5MB limit with large mlData / dataPreview blobs.
 * Heavy data (dataPreview, edaData, mlData, narrativeMarkdown) lives in
 * memory only — a full page refresh will require re-running the pipeline.
 */
import { createContext, useContext, useMemo, useState } from "react";

const SessionContext = createContext(null);

export const PY_API = process.env.REACT_APP_PY_API || "http://localhost:5001";
export const NODE_API = process.env.REACT_APP_REPORT_API || "http://localhost:4000";

const SS_KEY = "genai_session";

function loadSession() {
  try {
    const raw = sessionStorage.getItem(SS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveSession(patch) {
  try {
    const current = loadSession();
    sessionStorage.setItem(SS_KEY, JSON.stringify({ ...current, ...patch }));
  } catch {}
}

function persist(setter, key) {
  return (val) => {
    setter(val);
    saveSession({ [key]: val });
  };
}

export function SessionProvider({ children }) {
  const s = loadSession();

  // Lightweight — persisted to sessionStorage
  const [sessionId, _setSessionId] = useState(s.sessionId ?? null);
  const [datasetName, _setDatasetName] = useState(s.datasetName ?? "");
  const [instructions, _setInstructions] = useState(s.instructions ?? "");
  const [selectedChartIds, _setSelectedChartIds] = useState(s.selectedChartIds ?? [1, 2, 3, 4]);
  const [narrativeKey, _setNarrativeKey] = useState(s.narrativeKey ?? "");

  // Heavy blobs — memory only, cleared on full page refresh
  const [dataPreview, setDataPreview] = useState(null);
  const [edaData, setEdaData] = useState(null);
  const [edaReport, setEdaReport] = useState("");
  const [taskInfo, setTaskInfo] = useState(null);
  const [chartRequests, setChartRequests] = useState([]);
  const [mlData, setMlData] = useState(null);
  const [narrativeMarkdown, setNarrativeMarkdown] = useState("");
  const [pipelineError, setPipelineError] = useState(null);

  const setSessionId = persist(_setSessionId, "sessionId");
  const setDatasetName = persist(_setDatasetName, "datasetName");
  const setInstructions = persist(_setInstructions, "instructions");
  const setSelectedChartIds = persist(_setSelectedChartIds, "selectedChartIds");
  const setNarrativeKey = persist(_setNarrativeKey, "narrativeKey");

  const value = useMemo(
    () => ({
      sessionId, setSessionId,
      datasetName, setDatasetName,
      instructions, setInstructions,
      dataPreview, setDataPreview,
      edaData, setEdaData,
      edaReport, setEdaReport,
      taskInfo, setTaskInfo,
      chartRequests, setChartRequests,
      mlData, setMlData,
      selectedChartIds, setSelectedChartIds,
      narrativeMarkdown, setNarrativeMarkdown,
      narrativeKey, setNarrativeKey,
      pipelineError, setPipelineError,
      reset: () => {
        sessionStorage.removeItem(SS_KEY);
        _setSessionId(null);
        _setDatasetName("");
        _setInstructions("");
        _setSelectedChartIds([1, 2, 3, 4]);
        _setNarrativeKey("");
        setDataPreview(null);
        setEdaData(null);
        setEdaReport("");
        setTaskInfo(null);
        setChartRequests([]);
        setMlData(null);
        setNarrativeMarkdown("");
        setPipelineError(null);
      },
    }),
    [sessionId, datasetName, instructions, dataPreview, edaData, edaReport, taskInfo, chartRequests, mlData, selectedChartIds, narrativeMarkdown, narrativeKey, pipelineError],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside <SessionProvider>");
  return ctx;
}
