import { Fragment, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getChartRegistry, REPORT_COLORS } from "./ChartRegistry";

/**
 * Splits markdown on <chart id="N" /> markers and interleaves the
 * matching chart component (from getChartRegistry) between markdown segments.
 *
 *   "## Hello\n<chart id=\"1\" />\nMore text"
 *      → [ {type:"md", value:"## Hello"},
 *          {type:"chart", id:1},
 *          {type:"md", value:"More text"} ]
 */
function splitOnChartMarkers(md) {
  const re = /<chart\s+id=["'](\d+)["']\s*\/?>/gi;
  const parts = [];
  let lastIdx = 0;
  let m;
  while ((m = re.exec(md)) !== null) {
    if (m.index > lastIdx) parts.push({ type: "md", value: md.slice(lastIdx, m.index) });
    parts.push({ type: "chart", id: Number(m[1]) });
    lastIdx = re.lastIndex;
  }
  if (lastIdx < md.length) parts.push({ type: "md", value: md.slice(lastIdx) });
  return parts;
}

const mdComponents = {
  h1: ({ node, ...p }) => (
    <h1
      className="text-3xl font-bold text-text-primary mt-2 mb-4 pb-2 border-b-2"
      style={{ borderColor: REPORT_COLORS.COLOR_PRIMARY }}
      {...p}
    />
  ),
  h2: ({ node, ...p }) => (
    <h2
      className="text-2xl font-bold text-text-primary mt-8 mb-3 pb-1 border-b"
      style={{ borderColor: REPORT_COLORS.COLOR_PRIMARY, color: "#2A2A2A" }}
      {...p}
    />
  ),
  h3: ({ node, ...p }) => (
    <h3 className="text-lg font-semibold text-text-primary mt-10 mb-2" {...p} />
  ),
  h4: ({ node, ...p }) => (
    <h4 className="text-base font-semibold text-text-primary mt-4 mb-2" {...p} />
  ),
  p: ({ node, ...p }) => (
    <p className="text-sm text-text-primary leading-relaxed mb-4" {...p} />
  ),
  ul: ({ node, ...p }) => <ul className="list-disc pl-6 mb-4 text-sm text-text-primary space-y-1" {...p} />,
  ol: ({ node, ...p }) => <ol className="list-decimal pl-6 mb-4 text-sm text-text-primary space-y-1" {...p} />,
  strong: ({ node, ...p }) => <strong className="font-semibold text-text-primary" {...p} />,
  em: ({ node, ...p }) => <em className="italic" {...p} />,
  blockquote: ({ node, ...p }) => (
    <blockquote
      className="border-l-4 pl-4 my-4 text-sm italic text-text-secondary"
      style={{ borderColor: REPORT_COLORS.COLOR_PRIMARY }}
      {...p}
    />
  ),
  // Column / identifier references come through as `foo_bar` in Claude's
  // markdown. Always render inline — no block wrapper, no background box,
  // no monospace — just orange-tinted text that flows with the paragraph.
  // (react-markdown v9 drops the `inline` prop, so we treat every `code`
  // node as inline to keep column references from breaking the line.)
  code: ({ node, inline, ...p }) => (
    <span
      style={{
        color: REPORT_COLORS.COLOR_PRIMARY,
        fontWeight: 500,
        display: "inline",
      }}
      {...p}
    />
  ),
  // Pre wrapper for Claude's occasional fenced block — strip the usual
  // <pre> styling so it still reads as flowing prose (edge case; Claude
  // shouldn't use fences here but we guard against it).
  pre: ({ node, ...p }) => <span {...p} />,
  table: ({ node, ...p }) => (
    <div className="overflow-x-auto rounded-lg border border-gray-200 my-4">
      <table className="w-full text-sm border-collapse" {...p} />
    </div>
  ),
  thead: ({ node, ...p }) => (
    <thead style={{ background: REPORT_COLORS.COLOR_LIGHT }} {...p} />
  ),
  tbody: ({ node, ...p }) => <tbody {...p} />,
  tr: ({ node, children, ...p }) => {
    const getNodeText = (n) => !n ? "" : n.type === "text" ? n.value : (n.children || []).map(getNodeText).join("");
    const firstCell = (node?.children || []).find((n) => n.type === "element");
    const firstCellText = getNodeText(firstCell).trim();
    const isTotal = /^total$/i.test(firstCellText);
    return (
      <tr
        className={isTotal ? "font-semibold" : "border-t border-gray-100"}
        style={isTotal ? { borderTop: "2px solid #F97316", background: "#FFF7ED" } : {}}
        {...p}
      >
        {children}
      </tr>
    );
  },
  th: ({ node, ...p }) => (
    <th
      className="text-left font-semibold py-2.5 px-4 text-text-primary border-b border-gray-200 [&>p]:mb-0"
      {...p}
    />
  ),
  td: ({ node, ...p }) => (
    <td className="py-2 px-4 text-text-primary align-top [&>p]:mb-0" {...p} />
  ),
};

export default function InlineNarrative({ markdown, mlData }) {
  const segments = useMemo(() => splitOnChartMarkers(markdown || ""), [markdown]);
  // Stable registry across re-renders — see note in Visualizations.js.
  const registry = useMemo(() => (mlData ? getChartRegistry(mlData) : {}), [mlData]);

  return (
    <div className="report-body">
      {segments.map((seg, i) => {
        if (seg.type === "md") {
          return (
            <ReactMarkdown key={i} remarkPlugins={[remarkGfm]} components={mdComponents}>
              {seg.value}
            </ReactMarkdown>
          );
        }
        const ChartComp = registry[seg.id];
        if (!ChartComp) {
          return (
            <div
              key={i}
              className="my-4 p-3 rounded border border-red-200 bg-red-50 text-sm text-red-700"
            >
              Unknown chart id: {seg.id}
            </div>
          );
        }
        return (
          <Fragment key={i}>
            <ChartComp mlData={mlData} />
          </Fragment>
        );
      })}
    </div>
  );
}
