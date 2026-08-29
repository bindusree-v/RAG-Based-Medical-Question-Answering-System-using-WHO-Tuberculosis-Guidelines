import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "bg-primary": "#0d0f14",
        "bg-secondary": "#13161e",
        "bg-card": "#1a1d27",
        "bg-elevated": "#1e2130",
        "accent-blue": "#4f8ef7",
        "accent-purple": "#a78bfa",
        "accent-green": "#34d399",
        "accent-red": "#f87171",
        "accent-yellow": "#fbbf24",
      },
    },
  },
  plugins: [],
};
export default config;
