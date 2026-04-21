import MastercardLogo from "./MastercardLogo";

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-navbar flex items-center px-6 z-50">
      <MastercardLogo size={32} />
    </nav>
  );
}
