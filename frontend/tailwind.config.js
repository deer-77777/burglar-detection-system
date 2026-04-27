/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#1F3864",
        alert: "#C0392B",
        ok: "#1E8449",
        surface: "#FFFFFF",
        surfaceAlt: "#F5F7FB",
        textPrimary: "#1A1A1A",
        textSecondary: "#595959",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
