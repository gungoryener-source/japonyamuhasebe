import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#1E293B", 900: "#0F172A", 800: "#1E293B", 700: "#334155" },
        mint: { DEFAULT: "#10B981", 50: "#ECFDF5", 100: "#D1FAE5", 600: "#059669", 700: "#047857" },
      },
      fontFamily: {
        sans: ['"Hiragino Sans"', '"Hiragino Kaku Gothic ProN"', '"Noto Sans JP"', '"Yu Gothic UI"', "Meiryo", "system-ui", "sans-serif"],
        mono: ['"SF Mono"', "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
