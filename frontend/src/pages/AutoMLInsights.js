import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight, Sparkles, Lightbulb, BarChart2,
  Loader2, Target, X, Trophy, ChevronDown, ChevronUp,
} from "lucide-react";
import { useSession, PY_API } from "../context/SessionContext";

function TargetPickerModal({ candidates, onPick, onClose, autoTarget }) {
  const [choice, setChoice] = useState(autoTarget || candidates?.[0]?.column);
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl max-w-lg w-full mx-4 border border-gray-200">
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-lg font-semibold text-text-primary">Confirm target column</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Multiple candidates scored similarly. Pick the column you want to predict.
            </p>
          </div>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary">
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-4 space-y-2 max-h-80 overflow-y-auto">
          {candidates.map((c) => (
            <label
              key={c.column}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer ${
                choice === c.column ? "border-primary bg-orange-50/50" : "border-gray-100"
              }`}
            >
              <input
                type="radio"
                name="target"
                checked={choice === c.column}
                onChange={() => setChoice(c.column)}
                className="mt-1 accent-primary"
              />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-text-primary">{c.column}</span>
                  <span className="text-xs text-text-secondary">
                    score {Number(c.score || 0).toFixed(2)} &bull; {c.problem_type}
                  </span>
                </div>
                {Array.isArray(c.reasons) && c.reasons.length > 0 && (
                  <ul className="text-xs text-text-secondary mt-1 list-disc list-inside">
                    {c.reasons.slice(0, 3).map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                )}
              </div>
            </label>
          ))}
        </div>
        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-text-primary border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onPick(choice)}
            className="px-4 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-orange-600"
          >
            Use {choice}
          </button>
        </div>
      </div>
    </div>
  );
}

function DirectionPill({ direction }) {
  const map = {
    positive: { cls: "bg-red-50 text-red-600 border-red-100", label: "Pushes up" },
    negative: { cls: "bg-green-50 text-green-700 border-green-100", label: "Pushes down" },
    mixed:    { cls: "bg-gray-50 text-text-secondary border-gray-200", label: "Mixed" },
    "varies by category": { cls: "bg-orange-50 text-primary border-orange-100", label: "Varies by category" },
  };
  const m = map[direction] || map.mixed;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${m.cls}`}>
      {m.label}
    </span>
  );
}

export default function AutoMLInsights() {
  const navigate = useNavigate();
  const { sessionId, taskInfo, mlData, setMlData, pipelineError, setPipelineError } = useSession();

  const [loading, setLoading] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [tournamentOpen, setTournamentOpen] = useState(false);

  // Guard: React 18 strict mode double-mounts effects in dev — without
  // this, /api/automl gets posted twice and the tournament runs twice.
  const autoMLFiredRef = useRef(false);

  const runAutoML = async (target) => {
    if (autoMLFiredRef.current) return;
    autoMLFiredRef.current = true;
    setLoading(true);
    setPipelineError(null);
    try {
      const res = await fetch(`${PY_API}/api/automl`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, target_column: target }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || `AutoML failed (status ${res.status})`);
      setMlData(body.mlData);
    } catch (e) {
      setPipelineError(e.message || "AutoML failed");
      autoMLFiredRef.current = false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!sessionId) {
      navigate("/", { replace: true });
      return;
    }
    if (mlData) return;

    const needsPick =
      taskInfo &&
      taskInfo.confidence === "low" &&
      !taskInfo.overrideFromInstructions;

    if (needsPick) {
      setPickerOpen(true);
    } else if (taskInfo?.target) {
      runAutoML(taskInfo.target);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, taskInfo, mlData]);

  if (!sessionId || !taskInfo) return null;

  const winner = mlData?.leaderboard?.[0];
  const topDrivers = (mlData?.featureImportance || []).slice(0, 3).map((f) => f.feature);
  const topInsights = (mlData?.statisticalInsights || []).slice(0, 3);
  const topDirectional = (mlData?.shapExplanations || []).slice(0, 3);
  const shapLabel =
    topDirectional.length > 0 && topDirectional[0].method === "SHAP"
      ? "SHAP"
      : "Permutation-based directional analysis";

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-text-primary">AutoML Insights</h1>
        {mlData && (
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <Target size={14} className="text-primary" />
            Target: <span className="font-semibold text-text-primary">{mlData.targetColumn}</span>
            &nbsp;·&nbsp;
            <span className="text-text-primary">{mlData.problemType}</span>
            <button
              onClick={() => setPickerOpen(true)}
              className="ml-2 text-xs text-primary underline"
            >
              change
            </button>
          </div>
        )}
      </div>
      <p className="text-text-secondary mb-8">
        Model selection, feature importances, directional explanations and data-driven insights.
      </p>

      {pipelineError && (
        <div className="mb-6 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
          {pipelineError}
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-3 px-4 py-6 rounded-xl bg-white border border-gray-200 mb-6 text-text-secondary">
          <Loader2 size={18} className="animate-spin text-primary" />
          Running AutoML tournament and generating insights…
        </div>
      )}

      {mlData && (
        <>
          {/* ── 1. Summary ─────────────────────────────────────────── */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                <Sparkles size={18} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-text-primary">Summary</h3>
                <p className="text-sm text-text-secondary">Model selection and key takeaways</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
              <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Target</p>
                <p className="text-sm font-semibold text-text-primary truncate">{mlData.targetColumn}</p>
              </div>
              <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Problem Type</p>
                <p className="text-sm font-semibold text-text-primary">{mlData.problemType}</p>
              </div>
              <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Best Model</p>
                <p className="text-sm font-semibold text-text-primary truncate">{winner?.model || "—"}</p>
              </div>
              <div className="p-3 rounded-lg bg-orange-50 border border-orange-100">
                <p className="text-[11px] text-primary uppercase tracking-wider mb-1">Score ({winner?.metric})</p>
                <p className="text-sm font-semibold text-primary">
                  {winner ? winner.score.toFixed(4) : "—"}
                  {winner && typeof winner.scoreStd === "number" && winner.scoreStd > 0 && (
                    <span className="text-xs text-primary/80 font-normal"> ± {winner.scoreStd.toFixed(4)}</span>
                  )}
                </p>
              </div>
            </div>

            <div className="pt-5 border-t border-gray-100">
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">Key Takeaways</p>
              {topDrivers.length > 0 && (
                <p className="text-sm text-text-primary mb-3">
                  The top 3 drivers of <span className="font-semibold">{mlData.targetColumn}</span> are:{" "}
                  <span className="font-semibold">{topDrivers.join(", ")}</span>.
                </p>
              )}
              {topInsights.length > 0 && (
                <ul className="space-y-2">
                  {topInsights.map((ins, i) => (
                    <li key={i} className="flex gap-2 text-sm text-text-primary leading-relaxed">
                      <span className="text-primary shrink-0">•</span>
                      <span>{ins.desc}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* ── 2 + 3. Feature Importance (left) & Directional Explanations (right) ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6 items-start">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                  <BarChart2 size={18} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-text-primary">Feature Importance</h3>
                  <p className="text-sm text-text-secondary">Full ranking of features by contribution to the model</p>
                </div>
              </div>
              <table className="w-full table-auto">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left text-xs text-text-secondary py-2 pr-4 w-12">Rank</th>
                    <th className="text-left text-xs text-text-secondary py-2 pr-4">Feature</th>
                    <th className="text-right text-xs text-text-secondary py-2 pr-4">Importance</th>
                    <th className="text-right text-xs text-text-secondary py-2">Relative</th>
                  </tr>
                </thead>
                <tbody>
                  {(mlData.featureImportance || []).map((f, i) => (
                    <tr key={f.feature} className="border-t border-gray-50">
                      <td className="py-2.5 pr-4 text-sm font-medium text-text-primary">{f.rank || i + 1}</td>
                      <td className="py-2.5 pr-4 text-sm text-text-primary whitespace-nowrap">{f.feature}</td>
                      <td className="py-2.5 pr-4 text-sm text-text-secondary font-mono text-right">
                        {f.importance.toFixed(4)}
                      </td>
                      <td className="py-2.5 text-sm text-text-secondary font-mono text-right">
                        {Math.round(f.importancePct || 0)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {topDirectional.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                    <Lightbulb size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-text-primary">Directional Explanations</h3>
                    <p className="text-sm text-text-secondary">
                      How the top features move predictions — method: <span className="font-medium text-text-primary">{shapLabel}</span>
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  {topDirectional.map((exp) => (
                    <div key={exp.feature} className="p-4 border border-gray-100 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-semibold text-text-primary">
                          {exp.feature}
                          <span className="ml-2 text-xs font-normal text-text-secondary">({exp.feature_type})</span>
                        </p>
                        <DirectionPill direction={exp.direction} />
                      </div>
                      <p className="text-sm text-text-secondary leading-relaxed">{exp.explanation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ── 4. Data-Driven Insights ───────────────────────────── */}
          {(mlData.statisticalInsights || []).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                  <BarChart2 size={18} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-text-primary">Data-Driven Insights</h3>
                  <p className="text-sm text-text-secondary">Patterns found in the data, ranked by feature importance</p>
                </div>
              </div>
              <div className="space-y-4">
                {mlData.statisticalInsights.slice(0, 3).map((ins, i) => (
                  <div key={i} className="p-4 border border-gray-100 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-semibold text-text-primary">
                        {ins.rank ? `#${ins.rank} · ` : ""}{ins.title}
                      </p>
                      {ins.featureType && (
                        <span className="text-[11px] px-2 py-0.5 rounded bg-gray-50 text-text-secondary border border-gray-100">
                          {ins.featureType}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-text-primary leading-relaxed mb-3">{ins.desc}</p>
                    {Array.isArray(ins.findings) && ins.findings.length > 0 && (
                      <ul className="space-y-1 pl-2 border-l-2 border-orange-100">
                        {ins.findings.map((f, j) => (
                          <li key={j} className="text-xs text-text-secondary leading-relaxed pl-3">
                            {f}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Tournament Details (single collapsible, two inner boxes) ─ */}
          <div className="bg-white rounded-xl border border-gray-200 mb-6">
            <button
              onClick={() => setTournamentOpen(!tournamentOpen)}
              className="w-full flex items-center justify-between p-5 text-left"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                  <Trophy size={18} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-text-primary">Tournament Details</h3>
                  <p className="text-sm text-text-secondary">
                    Task identification and full model leaderboard
                  </p>
                </div>
              </div>
              {tournamentOpen ? (
                <ChevronUp size={20} className="text-text-secondary" />
              ) : (
                <ChevronDown size={20} className="text-text-secondary" />
              )}
            </button>

            {tournamentOpen && (
              <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-5">
                {/* ── Inner box 1: Task Identification ── */}
                <div className="rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                      <Target size={18} />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-text-primary">Task Identification</h4>
                      <p className="text-xs text-text-secondary">Target column, problem type, and candidate ranking</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                      <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Target</p>
                      <p className="text-sm font-semibold text-text-primary truncate">{mlData.targetColumn}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                      <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Problem Type</p>
                      <p className="text-sm font-semibold text-text-primary">{mlData.problemType}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                      <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Confidence</p>
                      <p className="text-sm font-semibold text-text-primary capitalize">{taskInfo.confidence}</p>
                      {taskInfo.overrideFromInstructions && (
                        <p className="text-[10px] text-primary font-medium mt-0.5">user override</p>
                      )}
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                      <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Schema Hash</p>
                      <p className="text-xs font-mono text-text-primary truncate" title={taskInfo.schemaHash}>
                        {taskInfo.schemaHash || "—"}
                      </p>
                    </div>
                  </div>

                  {Array.isArray(taskInfo.candidates) && taskInfo.candidates.length > 0 && (
                    <div>
                      <p className="text-xs text-text-secondary mb-2">Top target candidates</p>
                      <table className="w-auto">
                        <thead>
                          <tr className="border-b border-gray-100">
                            <th className="text-left text-xs text-text-secondary py-2 pr-8">#</th>
                            <th className="text-left text-xs text-text-secondary py-2 pr-8">Column</th>
                            <th className="text-right text-xs text-text-secondary py-2 pr-8">Score</th>
                            <th className="text-left text-xs text-text-secondary py-2">Type</th>
                          </tr>
                        </thead>
                        <tbody>
                          {taskInfo.candidates.slice(0, 5).map((c, i) => (
                            <tr key={c.column} className="border-t border-gray-50">
                              <td className="py-2 pr-8 text-sm text-text-primary">{i + 1}</td>
                              <td className="py-2 pr-8 text-sm font-medium text-text-primary">
                                {c.column}
                                {c.column === mlData.targetColumn && (
                                  <span className="ml-2 text-[10px] text-primary font-semibold">SELECTED</span>
                                )}
                              </td>
                              <td className="py-2 pr-8 text-sm text-text-secondary font-mono text-right">
                                {Number(c.score || 0).toFixed(2)}
                              </td>
                              <td className="py-2 text-sm text-text-secondary capitalize">{c.problem_type}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* ── Inner box 2: AutoML Tournament ── */}
                <div className="rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                      <Trophy size={18} />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-text-primary">AutoML Tournament</h4>
                      <p className="text-xs text-text-secondary">Full leaderboard and winner-selection rationale</p>
                    </div>
                  </div>

                  {mlData.tournamentMeta && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                      <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                        <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Primary Metric</p>
                        <p className="text-sm font-semibold text-text-primary">{mlData.tournamentMeta.primaryMetric || "—"}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                        <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Cross-Validation</p>
                        <p className="text-sm font-semibold text-text-primary">{mlData.tournamentMeta.cvFolds}-fold</p>
                      </div>
                      <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                        <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Models Tested</p>
                        <p className="text-sm font-semibold text-text-primary">
                          {mlData.tournamentMeta.successfulModels}/{mlData.tournamentMeta.totalModelsTested}
                          {mlData.tournamentMeta.failedModels > 0 && (
                            <span className="text-xs text-text-secondary font-normal"> ({mlData.tournamentMeta.failedModels} failed)</span>
                          )}
                        </p>
                      </div>
                      <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                        <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">Total Time</p>
                        <p className="text-sm font-semibold text-text-primary">
                          {mlData.tournamentMeta.totalTimeSec.toFixed(1)}s
                          {mlData.tournamentMeta.fromCache && (
                            <span className="ml-1 text-[10px] text-primary font-medium">cached</span>
                          )}
                        </p>
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-text-secondary mb-2">Full leaderboard</p>
                  <table className="w-auto">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left text-xs text-text-secondary py-2 pr-8">Rank</th>
                        <th className="text-left text-xs text-text-secondary py-2 pr-8">Model</th>
                        <th className="text-right text-xs text-text-secondary py-2 pr-8">Score (mean ± std)</th>
                        <th className="text-right text-xs text-text-secondary py-2">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(mlData.fullLeaderboard || mlData.leaderboard || []).map((m) => {
                        const failed = typeof m.status === "string" && m.status !== "success";
                        return (
                          <tr key={m.rank} className={`border-t border-gray-50 ${m.isWinner ? "bg-orange-50/40" : ""}`}>
                            <td className="py-2 pr-8 text-sm font-medium text-text-primary">
                              {m.rank}{m.isWinner && <span className="ml-1 text-[10px] text-primary font-semibold">★</span>}
                            </td>
                            <td className="py-2 pr-8 text-sm text-text-primary whitespace-nowrap">{m.model}</td>
                            <td className="py-2 pr-8 text-sm text-text-secondary font-mono text-right">
                              {failed
                                ? <span className="text-red-500">FAILED</span>
                                : `${Number(m.score || 0).toFixed(4)} ± ${Number(m.scoreStd || 0).toFixed(4)}`}
                            </td>
                            <td className="py-2 text-sm text-text-secondary font-mono text-right">{Number(m.trainTimeSec || 0).toFixed(1)}s</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  {/* ── Top 3 Models — Selected for Downstream Training ── */}
                  {Array.isArray(mlData.leaderboard) && mlData.leaderboard.length > 0 && (
                    <div className="mt-6 pt-5 border-t border-gray-100">
                      <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
                        Top 3 Models
                      </p>
                      <p className="text-xs text-text-secondary mb-4">Selected for downstream training</p>
                      <div className="space-y-4">
                        {mlData.leaderboard.slice(0, 3).map((m, i) => {
                          const primaryMetric = mlData.tournamentMeta?.primaryMetric || m.metric;
                          return (
                            <div key={m.rank ?? i} className={`p-4 rounded-xl border ${m.isWinner ? "border-primary bg-orange-50/40" : "border-gray-100"}`}>
                              <div className="flex items-center justify-between mb-2">
                                <p className="text-sm font-semibold text-text-primary">
                                  #{i + 1} — {m.model}
                                  {m.isWinner && (
                                    <span className="ml-2 text-[10px] text-primary font-semibold">WINNER</span>
                                  )}
                                </p>
                                <p className="text-xs text-text-secondary font-mono">
                                  {Number(m.trainTimeSec || 0).toFixed(1)}s
                                </p>
                              </div>

                              <p className="text-xs text-text-secondary mb-1">
                                <span className="font-medium text-text-primary">Primary score</span>
                                {primaryMetric ? ` (${primaryMetric})` : ""}:{" "}
                                <span className="font-mono text-text-primary">
                                  {Number(m.score || 0).toFixed(4)} ± {Number(m.scoreStd || 0).toFixed(4)}
                                </span>
                              </p>

                              {Array.isArray(m.cvFoldScores) && m.cvFoldScores.length > 0 && (
                                <p className="text-xs text-text-secondary mb-1">
                                  <span className="font-medium text-text-primary">CV fold scores:</span>{" "}
                                  <span className="font-mono">
                                    [{m.cvFoldScores.map((v) => Number(v).toFixed(4)).join(", ")}]
                                  </span>
                                </p>
                              )}

                              {m.allMetrics && Object.keys(m.allMetrics).length > 0 && (
                                <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
                                  {Object.entries(m.allMetrics).map(([name, vals]) => (
                                    <p key={name} className="text-xs text-text-secondary">
                                      <span className="font-medium text-text-primary">{name}:</span>{" "}
                                      <span className="font-mono">
                                        {Number(vals.mean || 0).toFixed(4)} ± {Number(vals.std || 0).toFixed(4)}
                                      </span>
                                    </p>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* ── Winner Selection Rationale ── */}
                  {Array.isArray(mlData.leaderboard) && mlData.leaderboard.length > 0 && (() => {
                    const w = mlData.leaderboard[0];
                    const runner = mlData.leaderboard[1];
                    const primaryMetric = mlData.tournamentMeta?.primaryMetric || w.metric;
                    let gap = 0, gapPct = 0;
                    if (runner) {
                      gap = w.score - runner.score;
                      gapPct = runner.score !== 0 ? (gap / Math.abs(runner.score)) * 100 : 0;
                    }
                    return (
                      <div className="mt-6 pt-5 border-t border-gray-100">
                        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
                          Winner Selection Rationale
                        </p>
                        <div className="space-y-2 text-sm text-text-secondary leading-relaxed">
                          <p>
                            <span className="font-semibold text-text-primary">'{w.model}'</span> was selected as
                            the tournament winner with a {primaryMetric} score of{" "}
                            <span className="font-mono text-text-primary">{Number(w.score || 0).toFixed(4)}</span>.
                          </p>
                          {runner && (
                            <p>
                              It outperformed the runner-up{" "}
                              <span className="font-semibold text-text-primary">'{runner.model}'</span> by{" "}
                              <span className="font-mono text-text-primary">{gap.toFixed(4)}</span>{" "}
                              ({gapPct.toFixed(1)}% relative improvement).
                            </p>
                          )}
                          <p>
                            All three models will proceed to the insight generation phase. The top model will
                            be used for insight generation.
                          </p>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => navigate("/visualizations")}
              className="py-3.5 px-8 bg-primary hover:bg-orange-600 text-white font-medium text-sm rounded-full flex items-center gap-2 transition-colors"
            >
              Continue to Visualizations <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}

      {pickerOpen && (
        <TargetPickerModal
          candidates={taskInfo.candidates || [{ column: taskInfo.target, score: 1, problem_type: taskInfo.problemType, reasons: [] }]}
          autoTarget={mlData?.targetColumn || taskInfo.target}
          onPick={(target) => { setPickerOpen(false); runAutoML(target); }}
          onClose={() => setPickerOpen(false)}
        />
      )}
    </div>
  );
}
