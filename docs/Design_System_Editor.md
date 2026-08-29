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

## Scope of this phase (MVP)

Only the Home Assistant **native theme tokens** are covered: the ones
already declared in `themes/visio_sapiens.yaml` before this change
(palette, header, divider, icons, card/dialog shape, sidebar). These
drive button-card, mushroom and card_mod styling wherever they use
`var(--...)` from the active theme.

**Not covered yet** — the neon glass-panel look (borders, blur,
box-shadow) baked directly as literal values into `card_mod` blocks
across `templates_j2/*.j2` (67 occurrences across 8 templates as of
this writing), and duplicated again in the wizard pages' own
`<style>` blocks (`assign.html`, `vssp_rooms_floors.html`, etc.).
Editing a color in the THEME screen today changes every native token
consumer, but not those hardcoded blocks.

### Phase 2 (future work, not implemented here)

Refactor every hardcoded `rgba(0,229,255,...)` / `border-radius: 18px`
/ `backdrop-filter: blur(12px)` / `Orbitron` occurrence in
`templates_j2/*.j2` and in the wizard HTML pages to consume
`var(--vssp-*)` custom properties instead — properties this phase's
`theme.yaml.j2` can already emit once decided. At that point, a THEME
screen edit changes literally everything visual in the product, not
just the tokens Home Assistant's own components already understand.
This is a larger, higher-risk change (regression-testing 8 templates'
worth of visual styling) and is intentionally out of scope for the
MVP described in this document.

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
