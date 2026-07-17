/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  corePlugins: {
    preflight: false, // Prevent Tailwind from breaking existing Vanilla CSS App styles
  },
  theme: {
    extend: {
      "colors": {
        "primary": "oklch(62% 0.20 295)",
        "primary-container": "oklch(32% 0.15 295)",
        "on-primary": "#ffffff",
        "secondary": "oklch(70% 0.10 145)",
        "on-secondary": "#111827",
        "surface": "oklch(11% 0.006 280)",
        "surface-container": "oklch(15% 0.008 280)",
        "surface-container-low": "oklch(13% 0.007 280)",
        "surface-container-lowest": "oklch(11% 0.006 280)",
        "on-surface": "#f3f4f6",
        "on-surface-variant": "#9ca3af",
        "outline": "#4b5563",
        "outline-variant": "#374151",
        "error": "#ef4444",
        "error-container": "#7f1d1d",
        "vet-charcoal": "oklch(11% 0.006 280)",
        "vet-violet": "oklch(62% 0.20 295)",
        "vet-sage": "oklch(70% 0.10 145)",
        "vet-card": "oklch(15% 0.008 280)"
      },
      "borderRadius": {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      "spacing": {
        "sm": "12px",
        "margin-mobile": "16px",
        "xs": "4px",
        "lg": "48px",
        "gutter": "24px",
        "margin-desktop": "40px",
        "md": "24px",
        "xl": "80px",
        "base": "8px"
      },
      "fontFamily": {
        "headline-md": ["DM Sans", "sans-serif"],
        "body-lg": ["Nunito Sans", "sans-serif"],
        "headline-lg-mobile": ["DM Sans", "sans-serif"],
        "headline-lg": ["DM Sans", "sans-serif"],
        "display-lg": ["DM Sans", "sans-serif"],
        "label-md": ["Nunito Sans", "sans-serif"],
        "label-sm": ["Nunito Sans", "sans-serif"],
        "body-md": ["Nunito Sans", "sans-serif"],
        "display": ["DM Sans", "sans-serif"],
        "body": ["Nunito Sans", "sans-serif"]
      },
      "fontSize": {
        "headline-md": ["24px", {"lineHeight": "32px", "fontWeight": "600"}],
        "body-lg": ["18px", {"lineHeight": "28px", "fontWeight": "400"}],
        "headline-lg-mobile": ["24px", {"lineHeight": "32px", "fontWeight": "600"}],
        "headline-lg": ["32px", {"lineHeight": "40px", "letterSpacing": "-0.01em", "fontWeight": "600"}],
        "display-lg": ["48px", {"lineHeight": "56px", "letterSpacing": "-0.02em", "fontWeight": "700"}],
        "label-md": ["14px", {"lineHeight": "20px", "letterSpacing": "0.02em", "fontWeight": "500"}],
        "label-sm": ["12px", {"lineHeight": "16px", "fontWeight": "600"}],
        "body-md": ["16px", {"lineHeight": "24px", "fontWeight": "400"}]
      }
    }
  },
  plugins: [],
}
