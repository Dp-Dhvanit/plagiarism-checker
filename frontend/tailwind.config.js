/** @type {import('tailwindcss').Config} */
//
// Clean, off-white SaaS theme. Token NAMES are unchanged from the previous
// dark theme on purpose — every component references these same names, so
// recoloring them here cascades the whole redesign without touching class
// strings in ~50 component files. Only the semantic-color usages that
// genuinely needed a different token (see app/data/constants.js TONE map)
// were changed at the call site.
//
// Neutral tokens are CSS variables (defined for light and dark in src/index.css) so the
// whole palette swaps with the .dark class. Stored as RGB channels so Tailwind's
// opacity utilities (bg-outline-variant/40, ...) still work. Accent hues below stay
// fixed hex: they were chosen as mid-tones that read on both backgrounds.
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    // Rounded, modern shape language — replaces the old sharp 2-4px scale.
    borderRadius: {
      none: "0",
      sm: "6px",
      DEFAULT: "10px",
      md: "12px",
      lg: "16px",
      xl: "20px",
      full: "9999px",
    },
    extend: {
      colors: {
        // ── Neutrals — warm off-white, not stark white/gray ─────────────
        void: v("void"),                   // page background
        surface: v("surface"),                // cards
        "surface-dim": v("surface"),
        "surface-bright": v("surface"),
        "surface-lowest": v("surface-lowest"), // recessed areas: inputs, code blocks
        "surface-low": v("surface-low"),       // secondary card bg, hover states
        "surface-container": v("surface-container"),
        "surface-high": v("surface-high"),     // icon chips, pill backgrounds
        "surface-highest": v("surface-highest"),
        "surface-variant": v("surface-highest"),
        "on-surface": v("on-surface"),         // primary text
        "on-surface-variant": v("on-surface-variant"), // secondary text
        outline: v("outline"),              // muted icons / de-emphasized text
        "outline-variant": v("outline-variant"), // borders (picked deliberately darker
                                          // than a "final" light gray — most
                                          // borders in this app are drawn at
                                          // 20-50% opacity, and a paler base
                                          // would wash out to invisible on a
                                          // white card at that opacity)

        // ── Brand accent — muted lavender, used for actions/nav/links ───
        primary: "#7C6EEA",
        "on-primary": "#FFFFFF",
        "primary-container": "#7C6EEA",
        "on-primary-container": "#FFFFFF",
        "primary-dim": "#6357C9",

        // ── Result semantics — restrained, one hue each ─────────────────
        // "higher concern" (AI-likely, unverified-but-flagged, etc.)
        secondary: "#D97862",
        "on-secondary": "#FFFFFF",
        "secondary-container": "#D97862",
        "on-secondary-container": "#FFFFFF",

        // "lower concern" (human-likely, verified-clean, success)
        tertiary: "#6FAF7C",
        "on-tertiary": "#FFFFFF",
        "tertiary-container": "#6FAF7C",
        "on-tertiary-container": "#FFFFFF",

        // "uncertain" — its own family so it never collides visually with
        // the lavender brand color used for navigation/actions.
        warning: "#D99A3C",
        "on-warning": "#FFFFFF",
        "warning-container": "#D99A3C",
        "on-warning-container": "#FFFFFF",

        // genuine faults (request failed, service unavailable) — distinct
        // from the softer AI-concern coral above.
        error: "#D6544A",
        "on-error": "#FFFFFF",
        "error-container": "#D6544A",
        "on-error-container": "#FFFFFF",
      },
      fontFamily: {
        sans: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
        display: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "headline-xl": ["44px", { lineHeight: "1.15", letterSpacing: "-0.015em", fontWeight: "700" }],
        "headline-lg": ["30px", { lineHeight: "1.25", letterSpacing: "-0.01em", fontWeight: "700" }],
        "headline-md": ["22px", { lineHeight: "1.3", fontWeight: "600" }],
        "body-md": ["15px", { lineHeight: "1.6", fontWeight: "400" }],
        "data-lg": ["16px", { lineHeight: "1.4", fontWeight: "500" }],
        "data-md": ["13px", { lineHeight: "1.5", fontWeight: "400" }],
        "data-sm": ["12.5px", { lineHeight: "1.5", fontWeight: "400" }],
        "data-xs": ["11.5px", { lineHeight: "1.4", fontWeight: "400" }],
        "label-caps": ["11px", { lineHeight: "1.3", letterSpacing: "0.02em", fontWeight: "600" }],
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
        // Soft, physical, close-in shadows — no glow/neon.
        soft: "0 1px 2px rgba(43,42,39,0.05)",
        card: "0 1px 2px rgba(43,42,39,0.04), 0 6px 16px -4px rgba(43,42,39,0.06)",
        "card-hover": "0 2px 6px rgba(43,42,39,0.06), 0 12px 28px -6px rgba(43,42,39,0.10)",
        dropdown: "0 8px 24px -4px rgba(43,42,39,0.14)",
        "focus-ring": "0 0 0 3px rgba(124,110,234,0.18)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.97)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "150% 0" },
          "100%": { backgroundPosition: "-50% 0" },
        },
      },
      animation: {
        rise: "rise 0.4s cubic-bezier(0.22,1,0.36,1) both",
        "fade-in": "fade-in 0.3s ease both",
        "scale-in": "scale-in 0.25s cubic-bezier(0.22,1,0.36,1) both",
        "spin-slow": "spin 3s linear infinite",
        shimmer: "shimmer 1.8s linear infinite",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.22,1,0.36,1)",
      },
    },
  },
  plugins: [],
};
