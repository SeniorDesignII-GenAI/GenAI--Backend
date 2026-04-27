import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, CheckCircle2, Circle, AlertCircle } from "lucide-react";
import { getChartRegistry, chartMeta } from "../components/report/ChartRegistry";
import { useSession } from "../context/SessionContext";
import { mockMLData } from "../data/mockMLData";

const CHART_IDS = [1, 2, 3, 4, 5, 6];
const REQUIRED_SELECTIONS = 4;

export default function Visualizations() {
  const navigate = useNavigate();
  const { sessionId, mlData, selectedChartIds, setSelectedChartIds } = useSession();

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    if (!mlData) {
      // Tournament hasn't run yet — send user back one step.
      navigate("/automl-insights", { replace: true });
    }
  }, [sessionId, mlData, navigate]);

  const toggle = (id) => {
    setSelectedChartIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= REQUIRED_SELECTIONS) return prev;
      return [...prev, id];
    });
  };

  const orderedSelection = useMemo(
    () => CHART_IDS.filter((id) => selectedChartIds.includes(id)),
    [selectedChartIds],
  );

  // Memoise so chart components keep stable identity across re-renders —
  // selectChartSet() rebuilds bound functions each call, which otherwise
  // forces Recharts to unmount/remount (losing hover + animation state).
  const effectiveMlData = mlData || mockMLData;
  const registry = useMemo(() => getChartRegistry(effectiveMlData), [effectiveMlData]);

  const canContinue = orderedSelection.length === REQUIRED_SELECTIONS;

  return (
    <div>
      <div className="flex items-end justify-between mb-2">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Visualizations</h1>
          <p className="text-text-secondary mt-1">
            Six charts generated from the ML pipeline. Pick <strong>exactly {REQUIRED_SELECTIONS}</strong> to include in the narrative report.
          </p>
        </div>
        <div className="text-sm text-text-secondary">
          {orderedSelection.length}/{REQUIRED_SELECTIONS} selected
        </div>
      </div>

      {!canContinue && orderedSelection.length > 0 && (
        <div className="my-4 px-4 py-3 rounded-lg bg-primary-light border border-primary-200 text-sm text-text-primary flex items-center gap-2">
          <AlertCircle size={16} className="text-primary" />
          Select {REQUIRED_SELECTIONS - orderedSelection.length} more to continue.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 mt-4">
        {CHART_IDS.map((id) => {
          const Comp = registry[id];
          const meta = chartMeta(id, effectiveMlData);
          const isSelected = selectedChartIds.includes(id);
          return (
            <div
              key={id}
              onClick={() => toggle(id)}
              className={`relative rounded-xl transition-all cursor-pointer border-2 ${
                isSelected
                  ? "border-primary bg-primary/5"
                  : "border-transparent hover:border-gray-200"
              }`}
            >
              <div className="flex items-center justify-between px-5 pt-3 pb-2">
                <p className="text-xs uppercase tracking-wider text-text-secondary font-semibold">
                  Chart {id} · {meta.kind}
                </p>
                <div className="bg-white rounded-full shadow-sm">
                  {isSelected ? (
                    <CheckCircle2 size={22} className="text-primary fill-primary/10" />
                  ) : (
                    <Circle size={22} className="text-gray-300" />
                  )}
                </div>
              </div>
              {Comp ? (
                <Comp mlData={effectiveMlData} />
              ) : (
                <div className="p-6 text-xs text-text-secondary italic">
                  Chart {id} is not available for this dataset.
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-text-secondary">
          Selected order: {orderedSelection.map((id) => `#${id}`).join(" → ") || "—"}
        </div>
        <button
          onClick={() => navigate("/narrative")}
          disabled={!canContinue}
          className="py-3.5 px-8 bg-primary hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm rounded-full flex items-center gap-2 transition-colors"
        >
          Continue to Narrative <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
