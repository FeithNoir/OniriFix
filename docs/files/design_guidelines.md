# Design Guidelines

This document is the visual source of truth for **SeiryukoDojo**. The live language is the **JudoWeb** prototype: dark editorial canvas, Japanese-minimal contrast, gold accent, serif display type, and glass-dark technique cards. Tokens live only in `src/styles.css` and use **role names**, not pigment names, so the hex values can change later without renaming the system. Feature CSS and templates consume those tokens; they never hard-code hex (belt swatches are the only exception).

## Documentation rule

Canonical product, design, and setup writing lives in three files only:

- `docs/design_guidelines.md` — look, tokens, interaction
- `docs/architecture_guidelines.md` — structure, routes, data path
- `README.md` — purpose, stack, local setup, honesty of content

Do not add or restore `docs/DESIGN.md`, `docs/PRODUCT.md`, or `docs/setup.md`. Those files are redundant. New rules belong in the three files above.

## Product facts that shape the look

SeiryukoDojo is a study site for the judo promotion path (kyu colors through dan). Visitors read on phones in mixed light. The interface stays dark with high-contrast type and a single gold accent. The app does **not** publish class hours, street addresses, phone numbers, or exam calendars. Footer and hero never become a contact directory.

Principles:

1. The promotion path comes first. A visitor should find belts and techniques without hunting.
2. Japanese names sit next to romanized names; Noto Sans JP is for technical terms, not decoration everywhere.
3. Only real study assets are offered in the UI. Prototype placeholders are not product copy.
4. Claims stay honest. Difficulty pills and exam topics must match the catalog, not filler percentages.

## Rem scale

`html { font-size: 62.5%; }` so **1rem = 10px**. All token values assume that scale. Do not mix a 16px root with these rem numbers.

| Token intent | Typical rem |
| :--- | :--- |
| Body copy | `1.6rem` |
| UI / labels | `1.4rem`–`1.5rem` |
| Section title | `clamp(2.4rem, 4vw, 3.6rem)` |
| Hero display | `clamp(4rem, 8vw, 8rem)` |
| Control height | `var(--touch)` = `4.4rem` |

## Color tokens

Names describe **role**. Hex lives only in `:root`. Current values are a dark canvas with a gold accent (`#1a1a1a` / `#b08d57`), matching the SeiryukoDojo prototype balance of black, white, and gold.

| Token | Current hex | Role |
| :--- | :--- | :--- |
| `--color-main` / `--color-main-hot` / `--color-main-deep` | `#b08d57` / `#d4b483` / `#8e6f43` | Accent, CTA, hover fill, deep plates |
| `--color-canvas` / `--color-surface` / `--color-surface-raised` | `#1a1a1a` / `#2d2d2d` / `#3a3a3a` | Page ground and elevated blocks |
| `--color-panel` / `--color-panel-dark` / `--color-panel-light` | `#2d2d2d` / `#121212` / `#4a4a4a` | Controls, chrome, borders |
| `--color-trim` / `--color-trim-strong` / `--color-trim-soft` | `rgba(176, 141, 87, 0.28)` / `#ffffff` / `#6d6d6d` | Card stroke, strong type, muted strokes |
| `--color-text` / `--color-text-soft` | `#ffffff` / `#c8c8c8` | Primary and softened reading |
| `--shadow-main` / `--glow-main` | derived from `--color-main` | Accent glow |

Aliases: `--bg` → canvas, `--fg` → text, `--accent` and `--section-accent` → `--color-main`, `--highlight` → `--color-trim-strong`.

Belt pigments (white, yellow, orange, green, blue, brown, black) are **not** UI tokens. They live on `BeltGradeModel.colorHex` and paint the circular swatch only.

Difficulty pills may use a small semantic set (`--difficulty-beginner`, `--difficulty-intermediate`, `--difficulty-advanced`) defined once in `:root`, not per component.

### Semantic mapping (60 / 30 / 10)

| Role | Token | Use |
| :--- | :--- | :--- |
| **60% canvas** | `--color-canvas` | Page ground; hero may layer a darkened photograph |
| **30% structure** | `--color-surface`, `--color-panel` | Cards, topbar, exam panels |
| **10% accent** | `--color-main` / `--color-main-hot` | Primary CTA, Japanese names, active filters |
| **Trim** | `--highlight` | Focus, hover type, secondary chrome |
| **Ink** | `--color-text` | Headings and body |

## Page atmosphere

Body color is `--fg`. Background is stacked dark gradients on canvas, not a flat marketing white. The home hero may use a dojo photograph under a dark overlay plus a sparse particle field. Those particles belong on the home hero only. Honor `prefers-reduced-motion` by hiding them. Do not ship p5.js or Pixi.js for this effect.

Remote photographs must be **public domain** (for example Wikimedia Commons PD-Japan-oldphoto). Store every `src`, `alt`, and caption in `src/app/core/data/images.data.ts`. Do not scatter Wikimedia URLs in templates.

Cinturones, Técnicas, Historia, and Exámenes open with an editorial article masthead (display title + figure) before nested lists. Historia also includes a vertical timeline: gold nodes on a trim spine; motion is opacity only.

A thin **belt-gradient** rule (white → yellow → orange → green → blue → brown → black) is allowed as a section ornament under “Sistema de Cinturones”, not as a site-wide rainbow.

## Typography

Load Playfair Display, Inter, and Noto Sans JP from a first-party or self-hosted source in `index.html` / Angular styles—not a scatter of CDN tags per page.

| Role | Face | Usage |
| :--- | :--- | :--- |
| Display | Playfair Display | Wordmark, hero, section titles |
| Body | Inter | Copy, forms, nav |
| Japanese | Noto Sans JP | Kanji / kana technique names only |

`.font-display` and `.font-japanese` are global classes in `src/styles.css`.

## Interaction (hover)

Hover effects change **color, background, or border only**. Do not use `transform`, `translate`, `scale`, or any layout shift on `:hover`. The prototype lifted cards (`translateY(-8px)`); the Angular app replaces that with a stronger `--color-main` border and `--glow-main`. Buttons, cards, and nav links stay in place.

Allowed motion that is not hover: skip-link reveal on focus, mobile nav sheet, hero particles, route enter fade, loading shimmer. Respect `prefers-reduced-motion`.

## Layout and scroll

`html`, `body`, and `app-root` are `height: 100%` with `overflow: hidden`. The main layout shell is a **fixed-height grid** (`auto 1fr`). `<main>` owns vertical scroll with `overflow-y: scroll`. The window itself does not scroll. The footer lives at the end of `<main>`.

Page content sits in `.shell` (`max-width: var(--page-width)`). Technique and resource cards use `<app-card-grid>`: `repeat(auto-fill, minmax(min(100%, var(--card-min)), 1fr))` with equal row height. Card media rows share a fixed aspect-ratio so tiles stay even.

Component tokens use `html { font-size: 62.5% }` so **1rem = 10px** in layout. **Media queries** resolve `rem` against the UA root (16px), so the 900px editorial/nav threshold is `@media (min-width: 56.25rem)`. Hamburger below that. Other component queries stay at 32rem / 48rem / 64rem.

Component CSS files handle those breakpoints for that component only, plus any keyframes unique to it. Global tokens and shared surfaces stay in `src/styles.css`.

## Surfaces

**Cards** (`.surface` / technique card): panel at ~90% opacity, light backdrop blur, 1px stroke from `--color-trim`, generous radius (`1.2rem`). Hover: border to `--color-main`, optional glow. No lift.

**Buttons:** global `.btn`, `.btn-primary`, `.btn-ghost`. Primary uses `--color-main` and a `--color-main-hot` hover fill. Ghost is a 2px `--color-text` outline that fills to text-on-canvas on hover (prototype outline CTA).

**Filters:** pill buttons. Active state is `--color-main` fill. Inactive is `--color-panel` with a lighter panel hover.

**Forms:** min-height `var(--touch)`, panel inset field, `--color-text` copy. Focus: `--color-main` border plus a 0.2rem `--glow-main` ring.

Focus-visible rings use `--color-main-hot` (2px). Never leave the browser default on dark canvas.

## Topbar and footer

Sticky header: solid `--color-canvas` (`#1a1a1a`) and a drop shadow, like the SeiryukoDojo prototype. Wordmark in Playfair Display as **SEIRYUKO** plus gold **DOJO**. Public nav only: Inicio, Cinturones, Técnicas, Historia, Recursos, Exámenes. Active route and hover use `--color-main`. **No cart, login, hours, address, or contact icons.**

**Footer:** centered brand, one-line program description, copyright. No venue, timetable, telephone, or social-contact row. Type stays at `--text-small` or larger; any links that remain (e.g. Recursos) keep `--touch` targets.

## Motion that remains

| Token / keyframe | Use |
| :--- | :--- |
| `--transition-fast` (180ms) | Color, background, border |
| `--transition-medium` (300ms) | Mobile nav sheet (not hover) |
| Hero particle drift | Home only; hide under `prefers-reduced-motion` |
| Route / list fade | Opacity only; no card leap on hover |

Do not add Anime.js timelines, ECharts rings, or Splide carousels unless a later phase proves a native CSS/Angular solution is insufficient.

## What not to do

- Name tokens after a pigment (`japan-red`, `sumi`, `gold`) instead of a role (`main`, `canvas`, `trim`)
- Put hours, address, phone, map, or exam-date grids anywhere in the UI
- Keep Tailwind utility soup or CDN animation libraries as the design system
- Show hover lifts, slides, or scales
- Treat belt colors as global UI tokens
- Scroll the `body`; scroll `<main>` instead
- Offer downloads or video libraries that do not exist in the repo
- Create `docs/DESIGN.md`, `docs/PRODUCT.md`, or `docs/setup.md`
