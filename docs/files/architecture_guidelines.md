# Architecture Guidelines

This document defines the software architecture for **SeiryukoDojo**—an Angular home for the club’s judo promotion program—while it is refactored from the multi-page **JudoWeb** prototype (`docs/references/JudoWeb/`, gitignored) into this codebase.

The prototype is vanilla HTML / CSS / JS with Tailwind from a CDN, hash-less in-page sections on `index.html`, and extra pages (`tecnicas.html`, `recursos.html`). The Angular app keeps **standalone components and signals**. Feature routes use static `component` imports (no `loadComponent` Promises, no Observables). What we take from the prototype is information architecture, content shapes, and the visual recipes documented in [design_guidelines.md](design_guidelines.md).

Do not recreate `docs/DESIGN.md`, `docs/PRODUCT.md`, or `docs/setup.md`. Product purpose lives in the README; visual rules live here and in the design guidelines.

---

## 1. Core development principles

* **SOLID:** Components present dojo UI (belt tiles, technique cards, resource cards, exam panels). Services own filters, catalog lookup, and any local study progress. Models describe grades, techniques, resources, and exam topics.
* **DRY:** Technique cards, belt tiles, resource cards, section titles, and filter chips are built once under `shared/` (or as global CSS classes) and reused on Home, Techniques, Resources, and Exams.
* **KISS:** The path is Discover → Belt or category → Technique or resource → Detail. The catalog is a **fixed CSS card grid**. Do not add a shop, cart, checkout, or club directory.
* **Keep it lightweight (~200 line rule):** Split the prototype’s `main.js` (`initializeAnimations`, `filterTechniques`, `showBeltInfo`, `showTechniqueDetail`) into small components. Do **not** port Anime.js, ECharts, Splide, p5.js, Pixi.js, or the Tailwind CDN. Use Angular templates, CSS tokens, and native scroll.

**Out of scope (do not implement):** class schedules, venue addresses, phone numbers, social-contact blocks, “next exam date / Dojo Central” calendars, or any other operational club logistics. This app is a study and promotion guide, not a location listing.

---

## 2. Project structure

Keep a feature-driven tree. Map prototype pages and sections onto folders rather than inventing a second app.

**One component per folder.** The parent feature folder holds only that parent’s files (`belts.component.ts|html|css`). Every child lives in its own nested folder (`belts/belt-list/`, `belts/belt-detail/`). Do not place a child `*.component.ts` next to the parent in the same directory.

**Layout exception:** if `layout/` has a single shell, keep it at `layout/layout.component.*` — do not nest an extra `layout/layout/` folder.

```text
src/app/
├── core/
│   ├── config/
│   ├── data/           # catalogs + images.data.ts (public-domain URLs)
│   ├── models/
│   └── repositories/
├── features/
│   ├── home/
│   ├── belts/
│   │   ├── belts.component.*          # parent article
│   │   ├── belt-list/
│   │   └── belt-detail/
│   ├── techniques/
│   │   ├── techniques.component.*     # parent article
│   │   ├── technique-list/
│   │   └── technique-detail/
│   ├── history/
│   │   ├── history.component.*        # parent article
│   │   ├── history-chapters/
│   │   ├── history-timeline/
│   │   ├── history-pioneers/
│   │   ├── history-phases/
│   │   └── history-milestones/
│   ├── resources/
│   └── exams/
│       ├── exams.component.*          # parent article
│       └── exam-topics/
├── shared/
│   ├── article-block/
│   ├── card-grid/
│   ├── data-table/
│   ├── site-header/
│   ├── site-footer/
│   ├── technique-card/
│   └── …
├── layout/             # layout.component.* (no nested folder)
└── app.routes.ts
```

### Layer breakdown

#### `core/`

* **config:** Club identity that *is* allowed to live in code (name **Seiryuko Dojo**, tagline, logo path). Never store street address, phone, class timetable, or map pins.
* **models:** Belt grade, technique, technique category, study resource, exam topic.
* **services:** `CatalogService` (or repositories), optional `StudyProgressService` for local-only checklists. No cart, auth, or backend-status probe unless a later phase adds one.
* **repositories:** `BeltRepository`, `TechniqueRepository`, `ResourceRepository`. Components never inject `HttpClient` for catalog JSON; repositories own loading.
* **guards:** none required for the public study site. Add them only if a future private area appears.

Internal notes under `docs/` are not runtime URLs. The UI never links to those files.

#### `features/`

Prototype surface → Angular feature:

| Prototype | Angular feature | Route |
| :--- | :--- | :--- |
| `index.html` `#inicio` | `features/home` | `''` |
| `index.html` `#sistema` | `features/belts` | `'cinturones'` and `'cinturones/:id'` |
| `index.html` `#tecnicas` + `tecnicas.html` | `features/techniques` | `'tecnicas'` and `'tecnicas/:id'` |
| History milestones | `features/history` | `'historia'` |
| `index.html` `#recursos` + `recursos.html` | `features/resources` | `'recursos'` |
| `index.html` `#examenes` (without the date grid) | `features/exams` | `'examenes'` |
| Footer | layout, not a page | brand only |

Home owns: full-bleed hero, two CTAs, a short public-domain archive strip, and shortcut cards. No belt grid, no technique catalog, no history timeline.

**Parent article screens:** `cinturones`, `tecnicas`, `historia`, and `examenes` are parent components that render extended article copy (via `<app-article-block>`) and then nest the previous list/detail UI underneath.

Belts parent owns the article. Child `belt-list` renders **Kyu** and **Dan** as separate tile groups on `'cinturones'`. Child `belt-detail` on `'cinturones/:id'` keeps grade summary, kata, theory, and linked waza.

Techniques parent owns the Kodokan article. Child `technique-list` owns chips and the card grid. Child `technique-detail` owns romaji, kanji, gloss, key points, related grades.

History parent owns the narrative. Children: `history-chapters` (long-form sections), `history-timeline`, `history-pioneers`, `history-phases`, and `history-milestones` (card recap of the same spine).

Resources owns: the shared data table (search, kind combobox, pagination) with in-app study routes, institutional links, and bibliography transcribed from internal notes. Drop prototype claims such as “150 pages” or “100+ videos”.

Exams parent owns etiquette/philosophy copy. Child `exam-topics` owns the filtered topic cards. **Omit** exam calendars and venues.

#### `shared/`

* `<app-technique-card>` (prototype `.technique-card` + Japanese name line).
* `<app-belt-tile>` (color disc + kyu/dan label).
* `<app-card-grid>` (signal `minCard` / `gap` / `mode` / `maxColumns`, `layoutChange` output).
* `<app-data-table>` (columns, rows, input filter, combobox, pagination).
* `<app-site-header>` and `<app-site-footer>`.
* Resource card.
* Section title (kicker + heading + lede).
* Filter chips.
* Buttons remain **global classes** (`.btn`, `.btn-primary`, `.btn-ghost`) in `src/styles.css`.

#### `layout/`

Files live directly in `src/app/layout/` (`layout.component.ts|html|css`). Do not add `layout/layout/`.

* **Topbar:** sticky dark header with backdrop blur. Wordmark **Seiryuko Dojo** (Playfair Display). Public nav: Inicio, Cinturones, Técnicas, Historia, Recursos, Exámenes. Right: hamburger on small screens. No cart, auth, or profile.
* **Mobile nav:** full-screen sheet (prototype `#mobile-menu`), not a second information architecture.
* **Footer:** brand, short program line, copyright. No address, phone, hours, or social-as-contact.
* **Main layout:** fixed-height `app-shell` grid (`auto 1fr`). `html` / `body` / `app-root` do not scroll. `<main>` has `overflow-y: scroll` and owns the footer.

---

## 3. Angular 22+ standards

Standalone, signal-first. Prefer CSS and Angular control flow over extra animation SDKs. If a toast or dialog library is added later, restyle it to panel / `--color-main` per the design guidelines.

Routes bind `component:` to already-imported classes. Do **not** use `loadComponent`, `HttpClient`, Observables, or Promises in application logic. Catalogs are TypeScript modules; repositories expose signals. Any hero particle field stays small and `contain: strict` so it does not tax other routes.

* **Standalone:** every component `standalone: true`.
* **`inject()`** instead of constructor injection.
* **Control flow:** `@if`, `@for`, `@else`.
* **Signals:** active category filter, selected belt, catalog lists. The prototype’s mutable globals (`currentTechniqueFilter`) become signals + computed filtered lists.

```typescript
private catalog = inject(TechniqueRepository);
```

```angular-html
@if (technique(); as t) {
  <h2 class="font-display">{{ t.name }}</h2>
  <p class="font-japanese">{{ t.nameJa }}</p>
} @else {
  <p>Technique not found.</p>
}
```

---

## 4. Routing

* Use static `component` imports (no Promises).
* Prototype multi-file navigation (`index.html`, `tecnicas.html`, `recursos.html`) becomes the Angular router. Do not keep show/hide `.section.is-active` as the primary navigation after the refactor (it is acceptable only as an animation hook on the activated route).
* Nested children: `'cinturones'` / `'tecnicas'` render the parent article and a `router-outlet` for list or `:id` detail.

```typescript
export const routes: Routes = [
  {
    path: '',
    component: LayoutComponent,
    children: [
      { path: '', component: HomeComponent },
      {
        path: 'cinturones',
        component: BeltsComponent,
        children: [
          { path: '', component: BeltListComponent },
          { path: ':id', component: BeltDetailComponent },
        ],
      },
      {
        path: 'tecnicas',
        component: TechniquesComponent,
        children: [
          { path: '', component: TechniqueListComponent },
          { path: ':id', component: TechniqueDetailComponent },
        ],
      },
      { path: 'historia', component: HistoryComponent },
      { path: 'recursos', component: ResourcesComponent },
      { path: 'examenes', component: ExamsComponent },
      { path: '**', component: NotFoundComponent },
    ],
  },
];
```

---

## 5. Data and persistence

* **Repository pattern** for belts, techniques, history, exams, and resources. Prefer TypeScript catalogs in `src/app/core/data`. Public-domain image URLs live only in `images.data.ts`. No hybrid Supabase stack is required for v1.
* **Study progress (optional):** LocalStorage checklists only. Never imply a live federation record.
* **Honesty:** technique lists follow Kodokan Nage-waza / Katame-waza taxonomy. Prototype filler (placeholder exam dates, inflated video counts, fictional “Dojo Central”) is not product data.

---

## 6. View architecture (from the prototype)

### Home

* Full-bleed hero: cinematic title, accent on a key word, lede about the promotion path, two CTAs (belts / techniques). Optional sparse particles; honor `prefers-reduced-motion`.
* Shortcut cards into Cinturones, Técnicas, Historia, and Exámenes. No duplicated catalogs.

### Belts

* Tiles for 6° Kyu through 8° Dan on `/cinturones`.
* Detail on `/cinturones/:id`: grade name, color, focus summary, kata, theory, linked waza. No exam appointment UI.

### Techniques

* Filter chips: principal Kodokan branch, then subcategory (Te-waza, Koshi-waza, … / Osaekomi, Shime, Kansetsu).
* Grid of technique cards (romaji, kanji, Spanish gloss, subcategory).
* Detail: key points, Kodokan flag, minimum grade, related grades. Media is optional.

### Technique model

```typescript
export type CategoriaPrincipal = 'Nage-waza' | 'Katame-waza';
export type SubcategoriaNage = 'Te-waza' | 'Koshi-waza' | 'Ashi-waza' | 'Ma-sutemi-waza' | 'Yoko-sutemi-waza';
export type SubcategoriaKatame = 'Osaekomi-waza' | 'Shime-waza' | 'Kansetsu-waza';

export interface TecnicaJudo {
  id: string;
  nombreJapones: string;
  kanji: string;
  traduccionEspanol: string;
  categoriaPrincipal: CategoriaPrincipal;
  subcategoria: SubcategoriaNage | SubcategoriaKatame;
  esOriginalKodokan: boolean;
  gradoMinimoRequerido: string;
  descripcion: string;
  puntosClaveEjecucion: string[];
  gradeIds: string[];
}
```

### Belt model

```typescript
export interface BeltGradeModel {
  id: string;
  rankLabel: string; // e.g. '6° Kyu', '1° Dan'
  name: string;      // e.g. 'Cinturón Blanco'
  colorHex: string;  // belt pigment for the swatch only — not a UI token
  summary: string;
  techniqueIds: string[];
}
```

Belt disc colors are **domain data** on the model. UI chrome still uses role-based tokens (`--color-main`, `--color-canvas`, …).

### Resources

```typescript
export interface ResourceModel {
  id: string;
  title: string;
  description: string;
  kind: 'article' | 'external' | 'bibliography';
  href?: string;
}
```

Link in-app routes or real institutional sources. Do not add download buttons for missing files.

### Exams

```typescript
export interface ExamTopicModel {
  id: string;
  title: string;
  kind: 'technical' | 'theory';
  summary: string;
  relatedGradeIds: string[];
}
```

No `date`, `location`, or `venue` fields.

---

## 7. CSS architecture (implementation)

* Tokens and button/surface/utility classes live only in `src/styles.css`. Feature files compose those tokens; they do not declare hex colors or extra palettes (belt swatches are the exception: they read `colorHex` from the grade model).
* Each component has a `styleUrl` CSS file. That file owns **only** its responsive breakpoints (`@media`) and **exclusive** `@keyframes`. Shared look (cards, buttons, type) stays in `src/styles.css` so that file stays lighter.
* **Tokens are role-based.** `--color-main`, `--color-main-hot`, and `--color-main-deep` hold the accent. Surfaces use `--color-canvas`, `--color-surface`, `--color-panel`. Type uses `--color-text`. There is no pigment-named token (`japan-red`, `sumi`, `gold`).
* **Highlight** is `--highlight` (strong trim / hover type on dark canvas).
* Semantic aliases: `--accent` and `--section-accent` resolve to `--color-main`. `--fg` is `--color-text`.
* Shared utilities: `.shell`, `.surface`, `.btn-primary`, `.btn-ghost`, `.font-display`, `.font-japanese`, `.section-kicker`, `.section-title`, `.sr`.
* `html { font-size: 62.5%; }` so `1rem` equals `10px`.
* Do not keep Tailwind utility classes as the design system. Rebuild the look with tokens and a small set of global classes.

---

## 8. Scrollbar and chrome

Theme leftover browser chrome from tokens (accent thumb on dark track). Example:

```css
main {
  scrollbar-width: thin;
  scrollbar-color: var(--color-main) var(--color-canvas);
}
```

Form caret, `accent-color`, primary buttons, and hero particles (if any) use `--color-main`. Focus-visible rings use `--color-main-hot` or `--highlight`.

---

## 9. Documentation

Keep only `docs/design_guidelines.md`, `docs/architecture_guidelines.md`, and `README.md` as product docs. Do not recreate `DESIGN.md`, `PRODUCT.md`, or `setup.md`. Internal notes under `docs/` are not cited in the README. `docs/references/` and `docs/files/` are gitignored.
