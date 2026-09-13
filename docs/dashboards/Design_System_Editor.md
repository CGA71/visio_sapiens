# Visio Sapiens — Design system editor (ADMIN, THEME screen)

**English** · [Français](Design_System_Editor.fr.md)

## Principle

The visual charter (colors, header, sidebar, card/dialog shape) used to
live in one hand-edited file, `themes/visio_sapiens.yaml`. It is now
**generated**, the same way `views/energy.yaml` is generated (see
[Dashboard_Generator.md](Dashboard_Generator.md)), from:

- **`home-assistant/dashboards/model/design_system.yaml`** — the design
  tokens: palette, header, divider, icons, card/dialog shape, sidebar.
  This is the file a person (or the graphical editor below) edits.
- **`home-assistant/dashboards/templates_j2/theme.yaml.j2`** — the
  Jinja2 template that renders those tokens into the exact shape Home
  Assistant expects for a theme file.

```
model/design_system.yaml ──┐
                           ├── generate_dashboards.py --only theme
templates_j2/theme.yaml.j2 ┘            │
                                        ▼
                          themes/visio_sapiens.yaml
```

`themes/visio_sapiens.yaml` is **no longer hand-edited** — edit
`design_system.yaml` instead, then run
`python3 vssp/generate_dashboards.py --only theme`, or use the THEME
screen of the ADMIN console described below, which does the same thing
plus a live reload.

## Why this needs no dashboard regeneration

Every dashboard `generate_dashboards.py` produces reads its colors from
the **active Home Assistant theme** (`house.theme` in `house.yaml`),
never from a copy of its own. Changing the theme is therefore the
entire update: no `views/*.yaml` needs to change, so the THEME pipeline
never touches `dashboards/views/` and never calls `lovelace.reload`.
The single service that matters is `frontend.reload_themes`, which
reloads every `themes/*.yaml` file live. This is lighter than the
ENERGY/HOME/CORE pipelines, which do regenerate views and therefore do
take a dashboard backup and call `lovelace.reload`.

## The THEME screen — a graphical editor, not a text form

The ADMIN console's THEME screen (`/visio-sapiens-admin/theme`) follows
the exact same pattern already used by ROOMS and ASSIGN: a static HTML
page in an iframe, talking to Home Assistant through a **local-only
webhook** rather than the REST API — an iframe cannot reach the
parent page's `hass` object, and a long-lived REST token has no
business sitting in a browser for this. See
`home-assistant/www/vssp/wizard/vssp_theme_editor.html`.

The editor offers:
- a color picker per plain-hex token (primary/accent, backgrounds,
  text, header, icons, sidebar);
- a plain text field (with inline format hints) for the few tokens
  that carry an alpha channel (`card_background`, `dialog_scrim`,
  `sidebar_selected_background`, `bubble_backdrop`), since a native
  `<input type=color>` cannot represent `rgba(...)`;
- sliders for `card_radius`, `card_border_width`, `dialog_radius`;
- two font pickers, `font_display` and `font_body` (see *Typography*
  below), each with a sample line drawn in the chosen face;
- five size sliders by usage — clock, titles, values, text, labels —
  each showing its percentage and the resulting pixel size;
- a **live preview** — a small self-contained mock updated on every
  input, entirely client-side, no round trip;
- **Export** (downloads the current tokens as JSON) and **Import**
  (loads a previously exported file back into the form) — this is
  what `adminmenu.section.theme_hint` in the locale catalogues
  ("Import or export the CSS design system") already promised.

## Deployment: `design_system.yaml` is pod-side state

`.gitlab-ci.yml` replaces the whole `dashboards/` directory on every
deployment, then copies a short whitelist of files back from the
previous copy because they are written on the instance, not shipped by
the repository — `model/house_rooms.yaml` (the rooms wizard),
`model/energy_devices.yaml` (the energy sync), `views/home.yaml` (manual
Lovelace editing). `model/design_system.yaml` is now in that same
whitelist, since `vssp_theme_apply.py` writes it exactly the same way.
Without this, every deployment silently reverted any color applied from
the THEME screen back to the repository default — the very failure mode
this section exists to prevent. (Production has no pod-side dashboard
regeneration step at all yet, so its ENERGY/THEME data is only ever as
fresh as the last live edit made directly on that instance; staging
also re-renders `themes/visio_sapiens.yaml` from the preserved model
right after the deploy swap, mirroring the existing ENERGY pod-side
regeneration.)

## Reverting to the factory reference

`design_system.yaml` is pod-side state now (see above), so once someone edits a color from the THEME screen, nothing
in the repository can silently overwrite it again — that is the whole
point. But it also means there needs to be an explicit way back.

**`home-assistant/dashboards/model/design_system.default.yaml`** is a
second, frozen copy of the same `design:` structure, never written by
`vssp_theme_apply.py` and never listed in `.gitlab-ci.yml`'s
preserved-pod-state whitelist — it always ships with whatever the
repository currently declares as the reference, refreshed on every
deployment like any other template.

The THEME screen's **RESTORE REFERENCE** button (next to the iframe,
with a confirmation dialog, the same shape as REGENERATE HOME/ENERGY)
calls `vssp_theme_apply.py --restore-reference
design_system.default.yaml`, which builds a normal `{"tokens": {...}}`
payload straight out of that file and pushes it through the exact same
`validate()` / `apply()` / backup code path as a real editor
submission — no separate reset logic to keep in sync. It then
regenerates the theme and reloads it live, exactly like a normal
APPLY.

To change the factory reference itself (a deliberate rebrand, not a
day-to-day edit), update `design_system.default.yaml` and commit it —
`design_system.yaml` is untouched by that change until someone
actually clicks RESTORE REFERENCE.

## Pipeline triggered by APPLY

```
vssp_theme_editor.html (iframe)
        │  POST base64 tokens, no auth token, local network only
        ▼
webhook `vssp_theme`  (home-assistant/packages/vssp_theme.yaml)
        ▼
vssp/vssp_theme_apply.py
        │  validates every token (vssp_design_fields.py: color/rgba/length
        │  format, radius bounds) — a bad payload writes NOTHING
        │  writes into model/design_system.yaml (ruamel.yaml, comments kept)
        │  backs up the previous design_system.yaml first
        ▼
generate_dashboards.py --only theme
        │  renders theme.yaml.j2, validates the YAML, backs up the
        │  previous themes/visio_sapiens.yaml, writes the new one
        │  also writes design_system_status.json (flat values, read by
        │  the editor on next load)
        ▼
service frontend.reload_themes   ← the dynamic update
```

Every step that can reject a bad input does — an invalid color or an
out-of-range radius is refused by `vssp_theme_apply.py` before it ever
reaches `design_system.yaml`, exactly like `vssp_assign_apply.py`
refuses an impossible device assignment before it reaches
`house.yaml`.

## `vssp/vssp_design_fields.py` — the single source of truth for tokens

One small, dependency-free module lists every editable token, its path
inside `design:`, and its validation rule (`FIELDS` dict). It is
imported by:
- `vssp_theme_apply.py` (validates a submitted payload against it —
  needs `ruamel.yaml`, which this module deliberately does **not**
  depend on);
- `generate_dashboards.py` (writes `design_system_status.json` from it
  — this script's only dependencies stay `jinja2` + `pyyaml`, see
  [Dashboard_Generator.md](Dashboard_Generator.md)).

Splitting the vocabulary out this way means the editor's form, the
webhook's validation and the status file it reads back can never drift
from one another — there is exactly one list of token names.

## `selector_background` — one look for every selector

The ADMIN console holds five `input_select` controls: language and
format appear twice (ROOMS & FLOORS and GENERATION), plus the chatbot
provider. All five render the same way, and `selector_background` is the
token that colors them.

The rule behind it: **an `input_select` in this console is always a
`tile` card with an inline `select-options` feature, never a row inside
an `entities` card.** The native Material picker an entities row falls
back to renders as a wide white fill until every MDC theme variable is
defined, and it stays a full-width inline picker rather than the compact
chip row the console uses everywhere else.

In `admin.yaml.j2` the look is emitted by a `selector_card_mod()` Jinja
macro rather than a YAML anchor. Every screen lands in **one** generated
document, in `screens` order, so an anchor defined on one screen and
aliased from another silently depends on which of the two is emitted
first — reordering `screens` would break it. A macro has no such
coupling.

Pointing the background at `selector_background` rather than
`card-background-color` is deliberate: it keeps the selectors adjustable
from the THEME screen independently of every other card in the console.

## Text fields — `input_background` / `input_ink` / `input_label`

The editable box an `input_text` row renders as (CALENDAR's *Calendar
shown in the header*) is the one text field in the whole console, and it
arrived as a white box holding a pale cyan label and a white value —
both unreadable on a dark screen.

The cause is worth recording, because two plausible answers are wrong.
Home Assistant has shipped three generations of form components, and a
theme can set the names of all three while affecting nothing:

| Generation | Fill variable | Read by this widget? |
|---|---|---|
| Material (MDC) | `--mdc-text-field-fill-color` | no |
| HA's own wrapper | `--input-fill-color` | no |
| **Web Awesome** (`ha-input` > `wa-input`) | **`--ha-color-form-background`** | **yes** |

The theme already set the first two. Measured on the live console, the
field was `rgb(243,243,243)` with `rgb(255,255,255)` text while
`--mdc-text-field-fill-color` was correctly dark — the widget simply
never reads it. The winning declaration is `.input::part(base)` inside
`ha-input`'s shadow root.

The field is now a deliberate light grey with dark ink: a place you type
reads better as a light surface than as one more dark panel. That needs
three tokens, not one — the fill plus the two texts that sit on it, the
value and a softer label.

**These are applied by `admin.yaml.j2` as a card-scoped `card_mod`, not
through the theme.** The floating label reads `--secondary-text-color`,
which is a *global* token and is correct everywhere else in the
interface. Flipping it to a dark ink theme-wide to suit one field would
break secondary text across the whole UI, so it is flipped only where a
light field actually sits.

If a second text field ever appears on another screen, it needs the same
three lines — that is the cost of scoping, and it is the cheaper side of
the trade.

## Typography — `font_display` / `font_body`

Two faces, stored under `design.typography` as a family **name** picked
from a closed list (`FONTS` in `vssp_design_fields.py`): Orbitron,
Rajdhani, Exo 2, Oxanium, Chakra Petch, Share Tech Mono, Roboto, System.
The theme receives the full CSS stack for each, never the bare name.

| Token | Theme variables | Reaches |
|---|---|---|
| `font_display` (default Orbitron) | `--vssp-font-display` | everything the templates used to hardcode as `Orbitron`: nav chips and mobile nav, header title and clock, page/section titles, room headers, energy values, circuit amps |
| `font_body` (default Roboto) | `--vssp-font-body`, `--ha-font-family-body`, `--primary-font-family`, `--paper-font-common-base_-_font-family`, `--mdc-typography-font-family` | all other text — desktop nav entries, card contents, native rows, dialogs |

Every template writes `var(--vssp-font-display, Orbitron, sans-serif)`,
so a dashboard shown without the Visio Sapiens theme keeps its old look.
The body face needs no template change at all: it rides Home
Assistant's own font variables, which the dashboard theme sets on
`<html>` (measured on 2026.8: overriding `--ha-font-family-body` there
re-fonts the nav entries immediately).

**Why a closed list and not free text.** A family name is half a font —
the file has to be served too. Until this change no page loaded
Orbitron at all: `document.fonts` on the live dashboard held only
Roboto, so every `font-family: Orbitron` fell back to sans-serif except
on machines where the font happened to be installed. The faces are now
self-hosted under `www/vssp/fonts/` (latin subset, woff2, SIL OFL 1.1 —
licence texts alongside) and declared in `www/vssp/css/vssp_fonts.css`,
which `vssp.css` `@import`s and the THEME editor links directly. No
request goes to Google Fonts, so a wall tablet renders the same with the
internet down. Adding a face means dropping its woff2 there, declaring
it in `vssp_fonts.css`, and adding it to `FONTS` and to the editor's
`FONT_STACKS` mirror.

### Text sizes by usage — `size_clock` / `size_title` / `size_value` / `size_text` / `size_label`

Five **scales**, not five sizes, stored as `"NNN%"` (50–200 %) under
`design.typography.size`. A role spans several sizes on purpose — a
title is 20px in the header, 15px on a section, 11px on a subsection —
so one pixel value per role would flatten the hierarchy. Every literal
`font-size` in `button_card_templates.yaml` and `templates_j2/*.j2`
(201 of them, plus the two sizes button-card computes in JS) is now
`calc(<px> * var(--vssp-scale-<role>, 1))`, classified by what the text
*is*:

| Role | What | Examples |
|---|---|---|
| `clock` | the header clock digits | 24px desktop, 20px mobile |
| `title` | header title, sidebar logo, page/section/card headings | "HOME", "VISIO SAPIENS", "TOP 10 CONSUMPTION" |
| `value` | a reading or a device state | W, kWh, °C, circuit amps, thermostat, alarm state |
| `text` | names and Home Assistant's own text | nav entries, device names, rows |
| `label` | captions, units, hints, column headers, legends, badges | "Smart Home OS", "kW", "CPU 6%" |

The theme writes each scale as a unitless multiplier (`120%` →
`vssp-scale-value: "1.2"`); the `text` scale also drives
`ha-font-size-scale`, Home Assistant's own multiplier, so native cards
and rows follow. The editor shows each slider as a percentage and as the
resulting pixel size of one reference text of that role.

**Pod-side `design_system.yaml` predates the section.** The pod keeps
its own copy across deploys, so it has no `typography:` until the first
APPLY. `generate_dashboards.py` therefore lays the pod file over
`design_system.default.yaml` before rendering: every token the pod file
has wins, every token it lacks comes from the reference, and the run
prints which ones. Before this, one missing token
(`palette.selector_background` on staging) failed the whole pod-side
theme render on every deploy — the theme stayed at the repository
default and `design_system_status.json` was never written, so the
editor opened on factory values. `font_stack()` / `size_scale()` still
fall back on their own, and `vssp_theme_apply.py` creates a missing
section on write instead of failing on it.

**`/local` is cached for 31 days.** Home Assistant serves `/local` with
`max-age=2678400`, and on this instance the Lovelace resources are in
**storage** mode, so the `?v=` token the deploy writes into
`configuration.yaml` never reaches the browser: the `vssp.css` resource
stayed at `?v=4` and browsers kept a months-old copy. The resource was
bumped by hand (`lovelace/resources/update`) to ship the fonts; until
the deploy bumps storage-mode resources itself, any `vssp.css` change
needs the same. `vssp_fonts.css` is imported as `?v=1` — bump it with
any change to the sheet or a font file.

## Scope of this phase (MVP)

Only the Home Assistant **native theme tokens** are covered: the ones
already declared in `themes/visio_sapiens.yaml` before this change
(palette, header, divider, icons, card/dialog shape, sidebar). These
drive button-card, mushroom and card_mod styling wherever they use
`var(--...)` from the active theme.

**Now covered** — the neon border/glow color. Every `card_mod` border,
box-shadow and scrollbar-color across `templates_j2/*.j2` (120
occurrences, 11 templates) hardcoded `rgba(0,229,255,ALPHA)`, the exact
hex of the default Primary token, without ever reading it. These now
read `color-mix(in srgb, var(--primary-color, #00E5FF) N%, transparent)`
instead — same alpha per occurrence, so nothing changes until Primary
is actually edited, but a THEME screen APPLY now visibly changes every
neon border and glow in the product.

**Still not covered** — `border-radius` and `backdrop-filter: blur`
baked directly as literal values into the same `card_mod` blocks, plus
everything (borders, blur, box-shadow, radius) duplicated again in the
wizard pages' own `<style>` blocks (`assign.html`,
`vssp_rooms_floors.html`, etc.). `border-radius` specifically was left
alone rather than mechanically mapped: the literals `18px` and `20px`
are used inconsistently as both card and dialog radii across templates
(e.g. several `energy.yaml.j2` cards use `20px` as their own card
radius, not a dialog), so wiring them to `--ha-card-border-radius` vs
`--ha-dialog-border-radius` needs a per-occurrence read, not a
find/replace — a correctness risk a mechanical pass could get wrong
silently.

### Phase 2 (remaining work)

Refactor the remaining hardcoded `border-radius` / `backdrop-filter:
blur(12px)` occurrences in `templates_j2/*.j2` (per occurrence, card vs
dialog) and every duplicate in the wizard HTML pages, to consume
`var(--ha-card-border-radius)` / `var(--ha-dialog-border-radius)` — both
already emitted by `theme.yaml.j2` — instead of literals. The blur
radius has no corresponding `design_system.yaml` field yet, so wiring it
means deciding whether it becomes an editable token first. (The font is
done — see *Typography*; the wizard pages' own `<style>` blocks still
name Orbitron directly, like their colors.)

## Verification

- `python3 vssp/generate_dashboards.py --only theme` renders
  `themes/visio_sapiens.yaml` from the shipped `design_system.yaml` —
  the very first run produces a file identical to the one it replaces,
  since the model was built as a 1:1 mapping of the previous hand-written
  values.
- Changing one value in `design_system.yaml` and re-running `--only
  theme` changes only that value in the rendered file.
- `python3 vssp/vssp_theme_apply.py --dry-run --json-file <sample>`
  reports which tokens would be written/rejected without touching
  `design_system.yaml`.
- The webhook → `frontend.reload_themes` round trip can only be
  exercised on a deployed Home Assistant pod, like ROOMS/ASSIGN before
  it.
