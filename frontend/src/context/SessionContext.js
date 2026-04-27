import { createContext, useContext, useMemo, useState } from "react";

const SessionContext = createContext(null);

export const PY_API = process.env.REACT_APP_PY_API || "http://localhost:5001";
export const NODE_API = process.env.REACT_APP_REPORT_API || "http://localhost:4000";

export function SessionProvider({ children }) {
  const [sessionId, setSessionId] = useState(null);
  const [datasetName, setDatasetName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [dataPreview, setDataPreview] = useState(null);
  const [edaData, setEdaData] = useState(null);
  const [edaReport, setEdaReport] = useState("");
  const [taskInfo, setTaskInfo] = useState(null);
  const [chartRequests, setChartRequests] = useState([]);
  const [mlData, setMlData] = useState(null);
  const [selectedChartIds, setSelectedChartIds] = useState([1, 2, 3, 4]);
  const [narrativeMarkdown, setNarrativeMarkdown] = useState("");
  const [narrativeKey, setNarrativeKey] = useState("");
  const [pipelineError, setPipelineError] = useState(null);

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
        setSessionId(null);
        setDatasetName("");
        setInstructions("");
        setDataPreview(null);
        setEdaData(null);
        setEdaReport("");
        setTaskInfo(null);
        setChartRequests([]);
        setMlData(null);
        setSelectedChartIds([1, 2, 3, 4]);
        setNarrativeMarkdown("");
        setNarrativeKey("");
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
