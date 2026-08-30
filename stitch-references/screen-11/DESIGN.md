---
name: Deep Space Intelligence
colors:
  surface: '#131315'
  surface-dim: '#131315'
  surface-bright: '#39393b'
  surface-container-lowest: '#0e0e10'
  surface-container-low: '#1c1b1d'
  surface-container: '#201f21'
  surface-container-high: '#2a2a2c'
  surface-container-highest: '#353437'
  on-surface: '#e5e1e4'
  on-surface-variant: '#c3c6d7'
  inverse-surface: '#e5e1e4'
  inverse-on-surface: '#313032'
  outline: '#8d90a0'
  outline-variant: '#434655'
  surface-tint: '#b4c5ff'
  primary: '#b4c5ff'
  on-primary: '#002a78'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#0053db'
  secondary: '#ddb8ff'
  on-secondary: '#490080'
  secondary-container: '#7c03d3'
  on-secondary-container: '#dfbcff'
  tertiary: '#b3d17a'
  on-tertiary: '#243600'
  tertiary-container: '#5b762a'
  on-tertiary-container: '#dcfca0'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#f0dbff'
  secondary-fixed-dim: '#ddb8ff'
  on-secondary-fixed: '#2c0051'
  on-secondary-fixed-variant: '#6800b4'
  tertiary-fixed: '#ceee93'
  tertiary-fixed-dim: '#b3d17a'
  on-tertiary-fixed: '#131f00'
  on-tertiary-fixed-variant: '#364e03'
  background: '#131315'
  on-background: '#e5e1e4'
  surface-variant: '#353437'
typography:
  headline-xl:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  data-lg:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.05em
  data-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.1em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  grid_unit: 8px
  gutter: 24px
  margin_desktop: 64px
  margin_mobile: 16px
  max_width: 1440px
---

## Brand & Style

The design system is engineered for a high-stakes, technical environment where precision and deep-analysis are paramount. It targets developers, academic institutions, and high-end content houses who require an interface that feels like a mission-critical terminal.

The aesthetic follows a **Deep Space Cyber-Technical** direction. It blends **Glassmorphism** with **Neo-Brutalism** elements (visible grid lines) to create a sense of structured depth. The interface should feel like a holographic HUD (Heads-Up Display) floating in a void, utilizing high-contrast accents and glowing states to direct attention to critical data anomalies.

## Colors

This design system utilizes a "Deep Space" palette characterized by infinite depth and neon precision.

*   **Primary (Deep Tech Blue):** Used for navigation, primary calls to action, and "System Ready" states.
*   **Secondary (Electric Purple):** Reserved exclusively for "AI Detected" signatures and machine-generated content flags.
*   **Tertiary (Cyber Lime):** Represents "Good" data—high human-originality scores and verified authenticity.
*   **Neutral (Void Black):** The #0A0A0C background provides the canvas for light-emitting elements.

Surface layers use semi-transparent glass with a subtle blue-tinted stroke to maintain visibility against the near-black background.

## Typography

The typography strategy employs a hierarchy of "Human vs. Machine." 

**Hanken Grotesk** is used for all interface instructions and headings, providing a contemporary, high-end sans-serif feel that remains readable.

**JetBrains Mono** is utilized for all "System Output"—including plagiarism percentages, timestamps, code snippets, and status logs. This distinction ensures the user immediately recognizes what information is raw data versus interface guidance. All data-labels should be rendered in `label-caps` for a technical, blueprint-like appearance.

## Layout & Spacing

This design system uses a **Technical Grid** model. The background is overlaid with a subtle 32px or 64px grid pattern (1px stroke, 5% opacity) to reinforce the engineering theme.

*   **Grid:** 12-column fluid grid on desktop, 4-column on mobile.
*   **Rhythm:** 8px base unit for all margins and padding.
*   **Alignment:** Elements should align strictly to the background grid lines. Containers should feature "crosshair" details or reinforced corner borders where they intersect with major grid lines.
*   **Breakpoints:** 
    *   Mobile: < 768px (single column stack)
    *   Tablet: 768px - 1024px (reduced margins)
    *   Desktop: > 1024px (standard 12-column)

## Elevation & Depth

Depth is achieved through **Luminance and Opacity** rather than traditional shadows.

1.  **The Void:** The lowest layer is the solid #0A0A0C background with the faint technical grid.
2.  **The Glass Layer:** Cards and panels use `surface_glass` with a `backdrop-filter: blur(12px)`.
3.  **The Neon Stroke:** Elevated elements do not use drop shadows; instead, they use a 1px inner border and a very subtle outer glow (`box-shadow: 0 0 15px rgba(37, 99, 235, 0.15)`).
4.  **The Active State:** When a component is focused or "scanning," the glow intensity increases and moves (scanning line effect), simulating a hardware status light.

## Shapes

The shape language is **Technical and Precise**. We use small radius corners (`rounded-sm`) to avoid a "bubbly" consumer look. 

*   **Containers:** Use 4px (0.25rem) radius for a sharp, machined appearance.
*   **Buttons/Inputs:** Match the 4px radius. 
*   **Specialty Elements:** Use 45-degree clipped corners (chamfered edges) for high-level status badges or "AI Warning" flags to evoke military-grade hardware aesthetics.

## Components

### Buttons
Primary buttons use a solid Tech Blue with a "Scanning" hover effect—a subtle light beam that passes across the button gradient. Secondary buttons are ghost-style with Electric Purple or Cyber Lime borders.

### Cards (Analyzers)
Cards must feature a `backdrop-filter`. The top-left corner of each card should include a small monospaced ID or coordinate (e.g., `SEC_04 // 88%`) to maintain the technical narrative.

### Status Indicators
Use pulsing neon dots for "Live Scanning" states.
*   **Pulsing Purple:** AI analysis in progress.
*   **Steady Lime:** Human-verified content.

### Input Fields
Inputs are dark, inset boxes with a 1px bottom-border that glows Tech Blue when active. Use JetBrains Mono for all user-typed text.

### The "Scanner" Line
A horizontal Cyber Lime or Tech Blue line that moves vertically across documents during the analysis phase, utilizing a gradient fade to create a "sweeping" motion.