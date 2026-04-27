import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ChevronLeft, ChevronRight, ChevronDown, ChevronUp,
  CheckCircle2, Sparkles, Grid3X3, ArrowRight, Database, Layers, Columns, AlertTriangle, Tag,
} from "lucide-react";
import { useSession } from "../context/SessionContext";

export default function DataPreview() {
  const navigate = useNavigate();
  const { sessionId, datasetName, dataPreview, edaData } = useSession();
  const [expandedIdxs, setExpandedIdxs] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);

  // Without a session there's nothing to display — bounce home.
  useEffect(() => {
    if (!sessionId) navigate("/", { replace: true });
  }, [sessionId, navigate]);

  if (!sessionId || !dataPreview || !edaData) return null;

  const {
    columns = [],
    rawColumns = [],
    cleanedRows = [],
    preprocessingItems = [],
    meta = { totalRows: 0, pageSize: 7, qualityScore: 100 },
  } = dataPreview;

  const rows = cleanedRows;
  const { totalRows, pageSize, qualityScore } = meta;
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const pagedRows = rows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const prettyCell = (v) => {
    if (v === null || v === undefined || v === "") {
      return <span className="text-primary font-medium italic">null</span>;
    }
    if (typeof v === "number") return Number.isInteger(v) ? v : v.toFixed(2);
    return String(v);
  };

  return (
    <div>
      <h1 className="text-3xl font-bold text-text-primary mb-2">Data Preview</h1>
      <p className="text-text-secondary mb-6">
        Review your uploaded dataset, preprocessing steps, and exploratory analysis before proceeding.
      </p>

      <div className="flex flex-col lg:flex-row gap-6 mb-6">
        <div className="flex-1 min-w-0">
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="flex items-center justify-between px-6 py-4">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-primary shrink-0">
                  <Grid3X3 size={20} />
                </div>
                <div className="space-y-1">
                  <p className="text-base font-semibold text-text-primary leading-tight">Dataset Preview</p>
                  {datasetName && (
                    <p className="text-xs font-medium text-primary truncate max-w-[220px] leading-tight">{datasetName}</p>
                  )}
                </div>
              </div>
              <p className="text-sm text-text-secondary">
                {totalRows.toLocaleString()} records &bull; {pageSize} per page
              </p>
            </div>

            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="overflow-x-auto rounded-lg bg-white">
              <div className="inline-block min-w-full">
              <table className="min-w-full">
                <thead>
                  <tr>
                    {columns.map((col) => (
                      <th key={col} className="text-left text-xs font-semibold text-text-secondary tracking-wider py-3 pr-4 last:pr-6">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pagedRows.map((row, i) => (
                    <tr key={i} className="border-t border-gray-50">
                      {rawColumns.map((key) => (
                        <td key={key} className="py-3.5 pr-4 text-sm text-text-primary whitespace-nowrap last:pr-6">
                          {prettyCell(row[key])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              </div>
            </div>

            <div className="flex items-center justify-between px-6 py-3 border-t border-gray-100">
              <p className="text-sm text-text-secondary">
                Showing{" "}
                <span className="font-medium text-text-primary">
                  {rows.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}
                  {"–"}
                  {Math.min(currentPage * pageSize, rows.length)}
                </span>
                {" "}of{" "}
                <span className="font-medium text-text-primary">{totalRows.toLocaleString()}</span> rows
              </p>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-200 text-text-secondary hover:bg-gray-50"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-sm font-medium text-text-primary px-2">
                  {currentPage} / {pageCount}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(pageCount, p + 1))}
                  className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-200 text-text-secondary hover:bg-gray-50"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="w-full lg:w-[280px] lg:shrink-0">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                <Sparkles size={20} />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">Preprocessing</p>
                <p className="text-sm text-text-secondary">Click to see impact</p>
              </div>
            </div>

            <div className="space-y-3">
              {preprocessingItems.length === 0 && (
                <p className="text-xs text-text-secondary italic px-1">
                  No preprocessing steps were required — the dataset was already clean.
                </p>
              )}
              {preprocessingItems.map((item, idx) => (
                <div
                  key={idx}
                  className={`rounded-xl border transition-colors ${
                    expandedIdxs.includes(idx) ? "border-primary bg-orange-50/30" : "border-gray-100"
                  }`}
                >
                  <button
                    onClick={() =>
                      setExpandedIdxs((prev) =>
                        prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx],
                      )
                    }
                    className="w-full flex items-center justify-between p-3 text-left"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <CheckCircle2 size={18} className="text-green-500 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-text-primary">{item.title}</p>
                        <p className="text-xs text-text-secondary">
                          {item.count} &bull; {item.detail}
                        </p>
                      </div>
                    </div>
                    {expandedIdxs.includes(idx) ? (
                      <ChevronUp size={16} className="text-text-secondary shrink-0" />
                    ) : (
                      <ChevronDown size={16} className="text-text-secondary shrink-0" />
                    )}
                  </button>
                  {expandedIdxs.includes(idx) && (
                    <div className="px-3 pb-3 space-y-2">
                      <p className="text-xs text-text-secondary leading-relaxed">{item.expandedText}</p>
                      {item.nullVal && item.newVal && (
                        <div className="flex items-center gap-2 text-xs">
                          <span className="px-2 py-1 bg-red-50 text-red-500 rounded font-mono">{item.nullVal}</span>
                          <span className="text-text-secondary">→</span>
                          <span className="px-2 py-1 bg-green-50 text-green-600 rounded font-mono">{item.newVal}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-5 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-text-secondary">Data Quality Score</p>
                <p className={`text-sm font-semibold ${qualityScore >= 80 ? "text-green-500" : qualityScore >= 50 ? "text-amber-500" : "text-red-500"}`}>
                  {qualityScore}%
                </p>
              </div>
              <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${qualityScore}%`, background: "linear-gradient(to right, #ef4444, #eab308, #22c55e)" }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <div className="h-px flex-1 bg-gray-200" />
        <div className="flex items-center gap-2">
          <Database size={13} className="text-text-secondary" />
          <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Exploratory Data Analysis
          </span>
        </div>
        <div className="h-px flex-1 bg-gray-200" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 px-6 py-4 mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
            <Database size={20} />
          </div>
          <div>
            <p className="text-base font-semibold text-text-primary">Dataset Overview</p>
            <p className="text-sm text-text-secondary">Structure and quality of your data</p>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { label: "Total Rows", value: edaData.datasetOverview.totalRows.toLocaleString() },
            { label: "Total Columns", value: edaData.datasetOverview.totalColumns },
            { label: "Duplicate Rows", value: edaData.datasetOverview.duplicateRows },
            { label: "Missing Values", value: edaData.datasetOverview.totalMissingValues },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-xs text-text-secondary mb-1">{label}</p>
              <p className="text-lg font-bold text-text-primary">{value}</p>
            </div>
          ))}
        </div>
        {edaData.datasetOverview.totalMissingValues === 0 && (
          <p className="text-xs text-green-600 font-medium mt-3">No missing values detected.</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
              <Columns size={20} />
            </div>
            <div>
              <p className="text-base font-semibold text-text-primary">Column Information</p>
              <p className="text-sm text-text-secondary">Types and breakdown by column</p>
            </div>
          </div>
          <p className="text-xs text-text-secondary mb-3">Column type summary</p>
          <div className="space-y-3 mb-5">
            {[
              { label: "Numerical", value: edaData.columnTypeSummary.numerical, color: "bg-primary" },
              { label: "Categorical", value: edaData.columnTypeSummary.categorical, color: "bg-yellow-400" },
              { label: "Datetime", value: edaData.columnTypeSummary.datetime, color: "bg-gray-300" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-sm text-text-secondary w-24">{label}</span>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${color} rounded-full`}
                    style={{
                      width: `${edaData.datasetOverview.totalColumns
                        ? (value / edaData.datasetOverview.totalColumns) * 100
                        : 0}%`,
                    }}
                  />
                </div>
                <span className="text-sm font-semibold text-text-primary w-6 text-right">{value}</span>
              </div>
            ))}
          </div>
          <div className="pt-4 border-t border-gray-100">
            <p className="text-xs text-text-secondary mb-3">Column details</p>
            <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
              {edaData.columnDetails.map((col) => (
                <div key={col.name} className="grid grid-cols-4 items-center text-xs px-2 py-1.5 bg-gray-50 rounded-lg gap-2">
                  <span className="font-medium text-text-primary truncate">{col.name}</span>
                  <span className={`justify-self-start px-2 py-0.5 rounded text-xs font-medium ${
                    col.type === "Numerical"
                      ? "bg-orange-100 text-primary"
                      : col.type === "Datetime"
                      ? "bg-gray-200 text-text-secondary"
                      : "bg-yellow-100 text-yellow-700"
                  }`}>{col.type}</span>
                  <span className="text-text-secondary text-center">{col.unique} unique</span>
                  <span className={`text-right ${col.nulls > 0 ? "text-red-500" : "text-green-600"}`}>{col.nulls} nulls</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {edaData.outlierDetection && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
                <AlertTriangle size={20} />
              </div>
              <div>
                <p className="text-base font-semibold text-text-primary">Outlier Detection</p>
                <p className="text-sm text-text-secondary">IQR-based outlier analysis per numerical column</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100">
                    {["Column", "Outliers Found", "Lower Bound", "Upper Bound", "IQR"].map((h) => (
                      <th key={h} className="text-left text-xs text-text-secondary py-2 pr-4 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {edaData.outlierDetection.map((row) => (
                    <tr key={row.column} className="border-t border-gray-50">
                      <td className="py-2.5 pr-4 text-sm font-medium text-text-primary">{row.column}</td>
                      <td className="py-2.5 pr-4 text-sm">
                        <span className={`font-semibold ${row.outliers > 0 ? "text-amber-600" : "text-green-600"}`}>
                          {row.outliers}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-sm text-text-secondary font-mono">{row.lowerBound}</td>
                      <td className="py-2.5 pr-4 text-sm text-text-secondary font-mono">{row.upperBound}</td>
                      <td className="py-2.5 pr-4 text-sm text-text-secondary font-mono">{row.iqr}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 px-6 py-4 mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
            <Layers size={20} />
          </div>
          <div>
            <p className="text-base font-semibold text-text-primary">Statistical Summary</p>
            <p className="text-sm text-text-secondary">Key statistics for numerical columns</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                {["Column", "Count", "Mean", "Std Dev", "Min", "Median", "Max", "Skewness", "Kurtosis"].map((h) => (
                  <th key={h} className="text-left text-xs text-text-secondary py-2 pr-4 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {edaData.statisticalSummary.map((row) => (
                <tr key={row.column} className="border-t border-gray-50">
                  <td className="py-2.5 pr-4 text-sm font-medium text-text-primary whitespace-nowrap">{row.column}</td>
                  <td className="py-2.5 pr-4 text-sm text-text-secondary">{row.count}</td>
                  <td className="py-2.5 pr-4 text-sm text-text-secondary">{row.mean}</td>
                  <td className="py-2.5 pr-4 text-sm text-text-secondary">{row.std}</td>
                  <td className="py-2.5 pr-4 text-sm text-text-secondary">{row.min}</td>
                  <td className="py-2.5 pr-4 text-sm text-text-secondary">{row.median}</td>
                  <td className="py-2.5 pr-4 text-sm text-text-secondary">{row.max}</td>
                  <td className={`py-2.5 pr-4 text-sm ${Math.abs(parseFloat(row.skewness)) > 1 ? "text-amber-600 font-medium" : "text-text-secondary"}`}>{row.skewness}</td>
                  <td className={`py-2.5 pr-4 text-sm ${parseFloat(row.kurtosis) > 3 ? "text-amber-600 font-medium" : "text-text-secondary"}`}>{row.kurtosis}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {edaData.categoricalAnalysis && (
        <div className="bg-white rounded-xl border border-gray-200 px-6 py-4 mb-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-primary">
              <Tag size={20} />
            </div>
            <div>
              <p className="text-base font-semibold text-text-primary">Categorical Feature Analysis</p>
              <p className="text-sm text-text-secondary">Value frequency distribution for categorical columns</p>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {edaData.categoricalAnalysis.map((cat) => (
              <div key={cat.column}>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{cat.column}</p>
                  {typeof cat.uniqueValues === "number" && (
                    <span className="text-[10px] text-text-secondary">{cat.uniqueValues} unique</span>
                  )}
                </div>
                <div className="space-y-2">
                  {cat.topValues.map(({ value, count, pct }) => (
                    <div key={value}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-text-primary font-medium truncate max-w-[140px]">{value}</span>
                        <span className="text-text-secondary shrink-0 ml-2">{count.toLocaleString()} ({pct})</span>
                      </div>
                      <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-primary rounded-full" style={{ width: pct }} />
                      </div>
                    </div>
                  ))}
                </div>
                {cat.imbalance && (
                  <p className="mt-2 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    Class imbalance — "{cat.dominantValue}" dominates at {cat.dominantPct}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={() => navigate("/automl-insights")}
          className="py-3.5 px-8 bg-primary hover:bg-orange-600 text-white font-medium text-sm rounded-full flex items-center gap-2 transition-colors"
        >
          Continue to AutoML Insights <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
