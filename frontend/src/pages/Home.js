import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FilePlus2, Loader2 } from "lucide-react";
import { homeFeatures } from "../data/mockData";
import { useSession, PY_API } from "../context/SessionContext";

export default function Home({ features = homeFeatures }) {
  const [file, setFile] = useState(null);
  const [instructionsLocal, setInstructionsLocal] = useState("");
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef();
  const navigate = useNavigate();

  const {
    setSessionId, setDatasetName, setInstructions, setDataPreview, setEdaData, setEdaReport,
    setTaskInfo, setChartRequests, setMlData, setSelectedChartIds, setPipelineError, reset,
  } = useSession();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleAnalyze = async () => {
    if (!file || uploading) return;

    // Fresh session per upload — clear any stale state from a prior run.
    reset();
    setError(null);
    setUploading(true);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("instructions", instructionsLocal || "");

      const res = await fetch(`${PY_API}/api/upload`, { method: "POST", body: form });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || `Upload failed (status ${res.status})`);

      setSessionId(body.session_id);
      setDatasetName(file.name);
      setInstructions(instructionsLocal || "");
      setDataPreview(body.dataPreview);
      setEdaData(body.edaData);
      setEdaReport(body.edaReport || "");
      setTaskInfo(body.taskInfo);
      setChartRequests(body.chartRequests || []);
      setMlData(null);
      setSelectedChartIds([1, 2, 3, 4]);
      setPipelineError(null);

      navigate("/data-preview");
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-7rem)]">
      <div className="max-w-3xl w-full mx-auto text-center">
        <h1 className="text-4xl md:text-6xl font-extrabold text-text-primary leading-tight mb-4">
          GenAI Automated{" "}
          <span className="bg-gradient-to-r from-primary to-yellow-500 bg-clip-text text-transparent">Analytical{"\n"}Report</span> Creator
        </h1>

        <p className="text-text-secondary text-lg mb-8">
          Upload your dataset, explore insights, and generate AI powered
          narrative reports.
        </p>

        <div className="flex flex-wrap justify-center gap-4 mb-10">
          {features.map(({ icon: Icon, title, desc, color }) => (
            <div
              key={title}
              className="flex items-center gap-3 bg-[#EBE8E3] rounded-xl px-5 py-3"
            >
              <div className={`p-2 rounded-lg ${color}`}>
                <Icon size={20} />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-text-primary">{title}</p>
                <p className="text-xs text-text-secondary">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-8">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-10 mb-6 transition-colors ${
              file
                ? "border-primary bg-primary-light"
                : dragging
                ? "border-primary bg-primary-light cursor-pointer"
                : "border-gray-300 hover:border-primary cursor-pointer"
            }`}
            onClick={() => !file && fileRef.current.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="flex flex-col items-center gap-3">
              {file ? (
                <>
                  <div className="w-12 h-12 rounded-full bg-primary-light flex items-center justify-center text-primary">
                    <FilePlus2 size={24} />
                  </div>
                  <p className="text-base font-semibold text-text-primary">{file.name}</p>
                  <p className="text-sm text-text-secondary">File Ready For Analysis</p>
                  <button
                    className="mt-1 px-4 py-1.5 border border-gray-300 rounded-md text-sm text-text-primary hover:bg-gray-50 transition-colors"
                    onClick={(e) => { e.stopPropagation(); fileRef.current.click(); }}
                  >
                    Choose Different File
                  </button>
                </>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-full bg-primary-light flex items-center justify-center text-primary">
                    <Upload size={24} />
                  </div>
                  <p className="text-base font-medium text-text-primary">Drag and drop your file here</p>
                  <p className="text-sm text-text-secondary">Supports CSV and Excel files up to 50MB</p>
                  <button
                    className="mt-1 px-4 py-1.5 border border-gray-300 rounded-md text-sm text-text-primary hover:bg-gray-50 transition-colors"
                    onClick={(e) => { e.stopPropagation(); fileRef.current.click(); }}
                  >
                    Browse Files
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="border-t border-gray-100 pt-5">
            <label className="flex items-center gap-1.5 text-sm font-medium text-text-primary mb-2 text-left">
              <span>✨</span> Custom Analysis Instructions (Optional)
            </label>
            <textarea
              value={instructionsLocal}
              onChange={(e) => setInstructionsLocal(e.target.value)}
              placeholder="Describe what insights you're looking for... (e.g., 'target: Attrition, show bar and scatter charts')"
              className="w-full h-24 px-4 py-3 border border-gray-200 rounded-xl text-sm text-text-primary placeholder:text-text-secondary resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {error && (
            <div className="mt-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700 text-left">
              {error}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={!file || uploading}
            className="w-full mt-4 py-3.5 rounded-xl text-white font-medium text-base bg-primary hover:bg-primary-600 cursor-pointer transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {uploading ? <Loader2 size={18} className="animate-spin" /> : null}
            {uploading ? "Processing pipeline..." : "Analyze Data"}
          </button>
        </div>
      </div>
    </div>
  );
}
