import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        powder: {
          DEFAULT: "#B0E0E6",
          hover: "#9AD4DC",
          dark: "#7EC8D4",
        },
        body: "#4A4A4A",
      },
      boxShadow: {
        card: "0 2px 8px rgba(0, 0, 0, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
