/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#b8d0ff",
          300: "#8bb1ff",
          400: "#5c8bff",
          500: "#3763f4",
          600: "#2748d8",
          700: "#2038ae",
          800: "#1f318a",
          900: "#1e2c6e",
          950: "#141b40",
        },
      },
    },
  },
  plugins: [],
};
