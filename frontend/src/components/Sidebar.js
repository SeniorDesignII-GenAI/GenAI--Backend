import { NavLink } from "react-router-dom";
import {
  ArrowLeft,
  Table,
  BarChart3,
  FileText,
  BrainCircuit,
} from "lucide-react";

const navItems = [
  { to: "/data-preview", label: "Data Preview", icon: Table },
  { to: "/automl-insights", label: "AutoML Insights", icon: BrainCircuit },
  { to: "/visualizations", label: "Visualizations", icon: BarChart3 },
  { to: "/narrative", label: "Narrative", icon: FileText },
];

export default function Sidebar() {
  return (
    <aside className="fixed top-16 left-0 w-[180px] h-[calc(100vh-4rem)] bg-white border-r border-gray-200 flex flex-col z-40">
      <NavLink
        to="/"
        className="flex items-center gap-2 px-4 py-3 text-sm text-text-secondary hover:text-text-primary transition-colors"
      >
        <ArrowLeft size={16} />
        back to home
      </NavLink>

      <div className="border-t border-gray-100" />

      <nav className="flex flex-col py-2">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 text-sm transition-colors border-l-3 ${
                isActive
                  ? "border-primary bg-primary-light text-text-primary font-medium"
                  : "border-transparent text-text-secondary hover:text-text-primary hover:bg-gray-50"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
