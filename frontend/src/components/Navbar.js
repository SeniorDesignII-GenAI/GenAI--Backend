import { Menu, X } from "lucide-react";
import MastercardLogo from "./MastercardLogo";

export default function Navbar({ onToggle, sidebarOpen }) {
  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-navbar flex items-center px-4 sm:px-6 z-50 gap-3">
      <button
        onClick={onToggle}
        className="lg:hidden p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors"
        aria-label="Toggle menu"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
      <MastercardLogo size={32} />
    </nav>
  );
}
