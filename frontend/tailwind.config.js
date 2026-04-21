/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        inter: ["Inter", "sans-serif"],
      },
      colors: {
        bg: "#F0EDE8",
        primary: "#F97316",
        "primary-light": "#FFF7ED",
        secondary: "#EAB308",
        navbar: "#0A0A0A",
        "text-primary": "#1A1A1A",
        "text-secondary": "#6B7280",
      },
    },
  },
  plugins: [],
};
