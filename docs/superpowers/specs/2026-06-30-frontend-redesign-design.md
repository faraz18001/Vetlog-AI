# Vetlog Frontend Redesign — Design Spec

**Date:** 2026-06-30
**Status:** Approved (Approach A — Token-first refinement)
**Scope:** Full visual polish across all surfaces + one signature brand moment. No backend changes, no new dependencies.

## Goal

Make the Vetlog AI frontend look as good and unique as possible — professional, warm, and distinctly "veterinary" rather than generic AI dark mode.

## Locked decisions

| Decision | Choice |
|---|---|
| Direction | Elevate the existing dark "Vet Terracotta" theme |
| Personality | Warm & tactile / organic |
| Scope | Full visual polish, all surfaces |
| Brand | Keep DM Sans + Nunito Sans + lucide-react; add a custom Vetlog logo mark |
| Execution | A — Token-first refinement |
| Copy button | Include a hover copy button on AI messages (frontend-only) |

## Design pillars

1. **Tactile paper grain** — one low-opacity SVG noise overlay across the whole app. Highest-impact move away from "flat AI dark mode." Performant (single fixed pseudo-element, `mix-blend-mode: overlay`).
2. **Warm-tinted depth** — shadows tinted with the terracotta hue instead of pure black, plus a soft warm focus glow. Everything feels lit by warm light.
3. **Sage as the healthy/positive semantic** — a soft sage/olive green paired with terracotta. On-brand for a vet product (health); replaces the generic `#22c55e` on step-done dots.
4. **The logo mark** — a custom SVG monogram fusing a paw print with a heart-pulse line. Used in topbar, AI avatar, empty-state hero, favicon. The signature brand element.
5. **Hero empty-state glow** — a soft radial terracotta glow behind the logo mark. The "wow" first impression.
6. **Editorial restraint** — generous whitespace, refined type scale, tracked small-caps metadata, gentle motion. Calm and expensive, not busy.

## Token system changes (`frontend/tokens.css`)

Add (do not remove existing tokens unless noted):

- `--color-positive: oklch(70% 0.10 145)` + `--color-positive-subtle` — sage for done/success states.
- `--shadow-sm / --shadow-md / --shadow-lg` — **replace** the pure-black shadows with warm-tinted: `oklch(20% 0.02 25 / 0.x)`.
- `--text-display: 2.25rem` — for the hero empty-state title; keep existing `--text-3xl`.
- `--glow-accent` — radial terracotta at ~12% alpha, used by hero + focus-within on inputs.
- `--grain-opacity: 0.04` — controls the global noise overlay strength.
- Keep existing radii, spacing, motion, type scale; document intent in comments.

## Surface-by-surface treatment

### Topbar
- Logo mark + "Vetlog AI" wordmark (tighter tracking).
- Faint warm top-down gradient on the bar.
- Usage chip: tiny lucide icon + tabular nums (already present, refine).

### Sidebar (`Sidebar.jsx` + `Sidebar.css`)
- Slightly darker paper tone than the chat area for depth.
- "New Chat" → inviting filled accent-tinted action (not just outline).
- History items: terracotta left-accent on hover/active.
- Footer profile card refined.
- History stays dummy data — no backend changes.

### Chat window
- Warm thin scrollbar.
- Refined message gap.
- Warm radial glow renders at the top **only** in the empty state.

### Message bubbles (`MessageBubble.jsx`)
- **AI:** keep the premium "no-bubble, just text" treatment; avatar → logo mark; refine markdown prose (tables, code, blockquote) toward editorial.
- **User:** warmed pill, refined asymmetric corner, soft border.
- **New:** hover copy button on AI messages (frontend-only; `navigator.clipboard`). Hidden during streaming/errors.

### Empty state — the signature moment (`ChatWindow.jsx`)
- Large logo mark centered in a soft warm radial glow.
- Display-size "How can I help?".
- Refined sub-copy.
- Suggested prompts as tactile 2-col cards with staggered fade-in and warm hover-lift + tiny arrow reveal.

### Step chain (`StepChain.jsx`)
- Per-step lucide icons (database for SQL, file for report, etc.).
- Done dot → sage (`--color-positive`).
- Warmer connector line.
- Refined live pulse.
- Keep auto-collapse behavior.

### Report card (`ReportCard.jsx`)
- Tactile card with warm shadow + subtle top accent stripe.
- Refined header, toggle pill, button hierarchy (primary filled terracotta, secondary ghost).

### Settings modal (`SettingsModal.jsx` + `.css`)
- Warm shadow + blur backdrop (already present).
- Refined inputs with warm focus ring.
- Consistent button system.
- Better spacing.

### Input bar
- Warm focus-within glow ring.
- Send button: soft warm shadow + gentle hover lift.
- Subtle inner depth.
- Placeholder/hint copy unchanged.

## Motion
Keep Framer Motion. Refine:
- Message entrance: soft fade + slight up + 0.98→1 scale for tactility.
- Staggered empty-state cards.
- Send-button hover lift.
- Hero glow gentle breathe-in on mount.
- All new animations gated behind existing `prefers-reduced-motion`.

## Preserved (no regressions)
- All `focus-visible` rings, aria labels, `prefers-reduced-motion`, responsive breakpoints (320/375/414/768).
- No backend changes; no new npm dependencies (SVG mark is inline; grain is a data-URI).

## Files touched
- `frontend/tokens.css` — token additions.
- `frontend/src/App.css` — bulk restyle across all surfaces + grain overlay + hero glow.
- `frontend/index.html` — favicon (logo mark).
- **New** `frontend/src/components/LogoMark.jsx` — reusable SVG paw/heart-pulse monogram.
- `frontend/src/App.jsx` — mount `LogoMark` in topbar + grain overlay div.
- `frontend/src/components/ChatWindow.jsx` — hero empty state.
- `frontend/src/components/MessageBubble.jsx` — logo avatar + copy button.
- `frontend/src/components/Sidebar.jsx` + `Sidebar.css`.
- `frontend/src/components/StepChain.jsx`.
- `frontend/src/components/ReportCard.jsx`.
- `frontend/src/components/SettingsModal.jsx` + `SettingsModal.css`.

## Verification
- `npm run build` in `frontend/` — no JSX/import errors.
- Manual: `npm run dev` + backend, click through empty state → chat → report → settings.
- Responsive at 320 / 375 / 414 / 768.
- Reduced-motion path.
