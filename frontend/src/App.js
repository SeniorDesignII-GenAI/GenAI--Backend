import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import DataPreview from "./pages/DataPreview";
import Visualizations from "./pages/Visualizations";
import Narrative from "./pages/Narrative";
import AutoMLInsights from "./pages/AutoMLInsights";
import { SessionProvider } from "./context/SessionContext";
import "./App.css";

function HomeLayout() {
  return (
    <div className="min-h-screen bg-bg">
      <div className="fixed top-0 left-0 right-0 z-50">
        <nav className="h-16 bg-navbar flex items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <svg width={50} height={32} viewBox="0 0 50 32">
              <circle cx={16} cy={16} r={16} fill="#EB001B" />
              <circle cx={34} cy={16} r={16} fill="#F79E1B" opacity="0.9" />
            </svg>
            <span className="text-white font-semibold text-base tracking-wide">mastercard</span>
          </div>
        </nav>
      </div>
      <main className="pt-28">
        <Home />
      </main>
    </div>
  );
}

function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomeLayout />} />
          <Route element={<Layout />}>
            <Route path="/data-preview" element={<DataPreview />} />
            <Route path="/visualizations" element={<Visualizations />} />
            <Route path="/narrative" element={<Narrative />} />
            <Route path="/automl-insights" element={<AutoMLInsights />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SessionProvider>
  );
}

export default App;
