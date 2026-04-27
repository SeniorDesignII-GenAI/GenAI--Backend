import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, Loader2 } from "lucide-react";
import html2canvas from "html2canvas";
import InlineNarrative from "../components/report/InlineNarrative";
import { REPORT_COLORS } from "../components/report/ChartRegistry";
import { mockMLData, mockNarrative } from "../data/mockMLData";
import { useSession, NODE_API } from "../context/SessionContext";

/**
 * Remove any <chart id="N" /> marker Claude inserts for a chart id the
 * user did not include in their 4-chart selection. Keeps the narrative
 * consistent with the Visualizations confirmation gate.
 */
function filterMarkers(markdown, allowed) {
  const set = new Set(allowed.map(Number));
  return (markdown || "").replace(
    /<chart\s+id=["'](\d+)["']\s*\/?>\s*/gi,
    (full, id) => (set.has(Number(id)) ? full : ""),
  );
}

export default function Narrative() {
  const navigate = useNavigate();
  const {
    sessionId,
    mlData: ctxMlData,
    selectedChartIds,
    instructions,
    narrativeMarkdown,
    setNarrativeMarkdown,
    narrativeKey,
    setNarrativeKey,
  } = useSession();

  // Fall back to the mock if the user somehow landed here without a
  // live session (e.g. opening the URL directly during dev).
  const mlData = ctxMlData || mockMLData;
  const allowedIds = selectedChartIds?.length === 4 ? selectedChartIds : [1, 2, 3, 4];

  // Cache key: tied to the current session + chart selection. If either changes
  // (new upload, different charts), we regenerate; otherwise re-use the cached text.
  // The "v" suffix is a prompt-version bump — bump it whenever the server-side
  // narrative prompt changes in a way that should invalidate cached outputs
  // (e.g. adding/removing sections, changing table columns).
  const cacheKey = useMemo(
    () => `${sessionId || "mock"}|${[...allowedIds].sort().join(",")}|v=devsec3`,
    [sessionId, allowedIds],
  );
  const cachedValid = narrativeMarkdown && narrativeKey === cacheKey;

  // Local display state is seeded from the context cache so the report
  // shows instantly when the user returns to this page.
  const [markdown, setMarkdown] = useState(cachedValid ? narrativeMarkdown : "");
  const [streaming, setStreaming] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const reportRef = useRef(null);

  useEffect(() => {
    if (sessionId && !ctxMlData) {
      navigate("/automl-insights", { replace: true });
    }
  }, [sessionId, ctxMlData, navigate]);

  useEffect(() => {
    // Already have a completed narrative for this cache key — skip the
    // regenerate call entirely. This is what makes the report persistent
    // across route changes.
    if (cachedValid) {
      setMarkdown(narrativeMarkdown);
      return;
    }

    const ctrl = new AbortController();
    (async () => {
      try {
        setStreaming(true);
        setError(null);
        const res = await fetch(`${NODE_API}/api/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mlData,
            target_column: mlData.targetColumn,
            problem_type: mlData.problemType,
            customInstructions: instructions || "",
            allowedChartIds: allowedIds,
          }),
          signal: ctrl.signal,
        });
        if (!res.ok || !res.body) throw new Error(`status ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        setMarkdown("");
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          setMarkdown(buf);
        }
        // Ensure every selected chart marker is present — Claude occasionally
        // omits one. Inject any missing markers just before the Developer Section.
        const missingIds = allowedIds.filter(
          (id) => !new RegExp(`<chart\\s+id=["']${id}["']`).test(buf)
        );
        if (missingIds.length > 0) {
          const inject = missingIds.map((id) => `\n\n<chart id="${id}" />\n`).join("");
          const devIdx = buf.search(/^##\s+(?:3\.?\s+)?Developer Section/im);
          buf = devIdx !== -1
            ? buf.slice(0, devIdx) + inject + buf.slice(devIdx)
            : buf + inject;
        }

        // Stream completed successfully — persist the completed markdown to
        // the session context so subsequent mounts short-circuit above.
        setNarrativeMarkdown(buf);
        setNarrativeKey(cacheKey);
      } catch (e) {
        if (e.name !== "AbortError") {
          setError("Live narrative unavailable — showing cached preview.");
          setMarkdown(mockNarrative);
        }
        // On AbortError we simply stop; the next mount with cachedValid=false
        // will try again. We do NOT cache incomplete / mock output.
      } finally {
        setStreaming(false);
      }
    })();
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cacheKey]);

  const filteredMarkdown = useMemo(
    () => filterMarkers(markdown, allowedIds),
    [markdown, allowedIds],
  );

  const handleExport = async () => {
    if (!reportRef.current) return;
    setExporting(true);
    try {
      const blocks = reportRef.current.querySelectorAll(".chart-block");
      const captures = [];
      for (const el of blocks) {
        const titleEl = el.querySelector("h4");
        if (titleEl) titleEl.style.fontSize = "20px";
        const canvas = await html2canvas(el, { backgroundColor: "#ffffff", scale: 2 });
        if (titleEl) titleEl.style.fontSize = "";
        captures.push(canvas.toDataURL("image/png"));
      }
      const res = await fetch(`${NODE_API}/api/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          markdown: filteredMarkdown,
          mlData,
          chartImages: captures,
          target_column: mlData.targetColumn,
          problem_type: mlData.problemType,
        }),
      });
      if (!res.ok) throw new Error(`Export failed (status ${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${mlData.targetColumn || "report"}_analysis.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message || "Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">AI Narrative</h1>
          <p className="text-text-secondary mt-1">
            Inline report — narrative interleaved with your {allowedIds.length} confirmed charts.
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting || streaming}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ background: REPORT_COLORS.COLOR_PRIMARY }}
        >
          {exporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
          {exporting ? "Generating PDF…" : "Export PDF"}
        </button>
      </div>

      {streaming && (
        <div className="text-xs text-text-secondary mb-4 px-3 py-2 rounded bg-primary-light border border-primary-200 flex items-center gap-2">
          <Loader2 size={14} className="animate-spin text-primary" />
          Claude is writing the narrative…
        </div>
      )}

      {error && (
        <div className="text-xs text-text-secondary mb-4 px-3 py-2 rounded bg-primary-light border border-primary-200">
          {error}
        </div>
      )}

      <div
        ref={reportRef}
        className="bg-white rounded-xl border border-gray-200 px-4 sm:px-10 py-8"
      >
        <InlineNarrative markdown={filteredMarkdown} mlData={mlData} />
      </div>
    </div>
  );
}

