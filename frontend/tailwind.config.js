/** @type {import('tailwindcss').Config} */
//
// "Deep Space Intelligence" — tokens transcribed from
// stitch-references/*/DESIGN.md (all 13 share one system).
//
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    // Replaced (not extended): the shape language is deliberately sharp.
    // "Containers: 4px radius for a sharp, machined appearance."
    borderRadius: {
      none: "0",
      sm: "2px",
      DEFAULT: "4px",
      md: "6px",
      lg: "8px",
      xl: "12px",
      full: "9999px",
    },
    extend: {
      colors: {
        void: "#0a0a0b",
        surface: "#131315",
        "surface-dim": "#131315",
        "surface-bright": "#39393b",
        "surface-lowest": "#0e0e10",
        "surface-low": "#1c1b1d",
        "surface-container": "#201f21",
        "surface-high": "#2a2a2c",
        "surface-highest": "#353437",
        "surface-variant": "#353437",
        "on-surface": "#e5e1e4",
        "on-surface-variant": "#c3c6d7",
        outline: "#8d90a0",
        "outline-variant": "#434655",

        // Deep Tech Blue — navigation, primary actions, "system ready".
        primary: "#b4c5ff",
        "on-primary": "#002a78",
        "primary-container": "#2563eb",
        "on-primary-container": "#eeefff",
        "primary-dim": "#8fa5eb",

        // Electric Purple — reserved for AI / machine-generated signals.
        secondary: "#ddb8ff",
        "on-secondary": "#490080",
        "secondary-container": "#7c03d3",
        "on-secondary-container": "#dfbcff",

        // Cyber Lime — human-origin, verified, "good" data.
        tertiary: "#b3d17a",
        "on-tertiary": "#243600",
        "tertiary-container": "#5b762a",
        "on-tertiary-container": "#dcfca0",

        error: "#ffb4ab",
        "on-error": "#690005",
        "error-container": "#93000a",
        "on-error-container": "#ffdad6",
      },
      fontFamily: {
        sans: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
        display: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "headline-xl": ["48px", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "800" }],
        "headline-lg": ["32px", { lineHeight: "1.2", fontWeight: "700" }],
        "headline-md": ["24px", { lineHeight: "1.2", fontWeight: "700" }],
        "body-md": ["16px", { lineHeight: "1.6", fontWeight: "400" }],
        "data-lg": ["16px", { lineHeight: "1.4", letterSpacing: "0.03em", fontWeight: "500" }],
        "data-md": ["13px", { lineHeight: "1.5", fontWeight: "400" }],
        "data-sm": ["12px", { lineHeight: "1.4", fontWeight: "400" }],
        "data-xs": ["11px", { lineHeight: "1.4", fontWeight: "400" }],
        "label-caps": ["10px", { lineHeight: "1", letterSpacing: "0.1em", fontWeight: "700" }],
      },
      spacing: {
        gutter: "24px",
        page: "40px",
        "page-lg": "64px",
      },
      maxWidth: {
        shell: "1440px",
        content: "1180px",
      },
      boxShadow: {
        neon: "0 0 15px rgba(37,99,235,0.15)",
        "neon-lg": "0 0 30px rgba(37,99,235,0.18), inset 0 0 12px rgba(180,197,255,0.04)",
        "glow-primary": "0 0 18px rgba(180,197,255,0.28)",
        "glow-secondary": "0 0 18px rgba(221,184,255,0.30)",
        "glow-tertiary": "0 0 18px rgba(179,209,122,0.28)",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(124,3,211,0.55)" },
          "70%": { boxShadow: "0 0 0 9px rgba(124,3,211,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(124,3,211,0)" },
        },
        blink: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0" } },
        rise: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
      },
      animation: {
        // NOTE: `scan-y` and `shimmer` are declared in src/index.css because
        // they are driven by component classes rather than these utilities.
        "pulse-ring": "pulse-ring 1.8s ease-out infinite",
        blink: "blink 1.1s step-end infinite",
        rise: "rise 0.42s cubic-bezier(0.22,1,0.36,1) both",
        "fade-in": "fade-in 0.35s ease both",
        "spin-slow": "spin 3s linear infinite",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.22,1,0.36,1)",
      },
    },
  },
  plugins: [],
};
