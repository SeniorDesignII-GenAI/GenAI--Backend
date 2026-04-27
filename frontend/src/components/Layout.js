import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Check } from "lucide-react";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

const STAGES = [
  { path: "/data-preview", label: "Data Preview" },
  { path: "/automl-insights", label: "AutoML Insights" },
  { path: "/visualizations", label: "Visualizations" },
  { path: "/narrative", label: "Narrative" },
];

function ProgressBar({ pathname }) {
  const currentIdx = STAGES.findIndex((s) => s.path === pathname);
  if (currentIdx === -1) return null;

  return (
    <div className="bg-white border-b border-gray-200 px-4 sm:px-8 py-4">
      <div className="flex items-center max-w-4xl mx-auto">
        {STAGES.map((stage, idx) => {
          const isComplete = idx < currentIdx;
          const isActive = idx === currentIdx;
          return (
            <div key={stage.path} className="flex items-center flex-1 last:flex-none">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors shrink-0 ${
                    isComplete
                      ? "bg-primary text-white"
                      : isActive
                      ? "bg-primary text-white ring-4 ring-primary/20"
                      : "bg-gray-100 text-text-secondary"
                  }`}
                >
                  {isComplete ? <Check size={14} /> : idx + 1}
                </div>
                <span
                  className={`text-sm whitespace-nowrap hidden sm:inline ${
                    isActive
                      ? "font-semibold text-text-primary"
                      : isComplete
                      ? "text-text-primary"
                      : "text-text-secondary"
                  }`}
                >
                  {stage.label}
                </span>
              </div>
              {idx < STAGES.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-1.5 sm:mx-3 transition-colors ${
                    isComplete ? "bg-primary" : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-bg">
      <Navbar onToggle={() => setSidebarOpen((o) => !o)} sidebarOpen={sidebarOpen} />
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <main className="mt-16 lg:ml-[180px] min-h-[calc(100vh-4rem)]">
        <ProgressBar pathname={location.pathname} />
        <div className="p-4 sm:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
