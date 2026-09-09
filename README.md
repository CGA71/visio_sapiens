# Visio Sapiens — Neural Home Interface

**English** · [Français](README.fr.md)

Visio Sapiens builds **predefined Home Assistant dashboard templates**. You
describe your home once in an admin console — language, format, rooms —
and the whole interface is generated from that description, then kept in
sync as the home changes. Each room becomes a system module in a
futuristic HUD inspired by Visio Sapiens.

## Concept

- CORE (Home) — HUD, central radar, AI Core, metrics
- ROOM MODULES — one generated dashboard per declared room
- POWER GRID — energy management (solar, grid, breaker panel)
- Dynamic navigation rail, neon/glassmorphism design system

Dashboards are **generated**, not hand-written, and **dynamic**: they
follow the home model in real time rather than being a one-off export.

## Stack

Home Assistant (Lovelace YAML), button-card, card-mod, layout-card,
stack-in-card, apexcharts-card, mini-graph-card, config-template-card,
decluttering-card, browser_mod — `Visio Sapiens` theme, in-house CSS/JS
engine (`www/vssp/`), Jinja2 generator. GitLab CI/CD → k3s.

## Dashboard catalogue

### Header band

Every dashboard — room and system alike — opens with the same horizontal
band, rendered from a shared `header.j2` partial: **dashboard name,
weather, date and time**. The name comes from `t('room.kitchen')` or
`t('system.energy')`, so it follows the selected language; the date and
time come from `Intl` with the locale tag. One partial, included by every
template — the band is never duplicated.

### Room dashboards

The admin console offers a closed catalogue of rooms. Each declared room
produces one dashboard from the same predefined template.

| Room | Multiple instances |
|---|---|
| Kitchen | — |
| Living room | — |
| Dining room | — |
| Entrance hall | — |
| Laundry room | — |
| Technical room | — |
| Garage | — |
| Cellar | — |
| Bedroom | ✅ *(n)* |
| Bathroom | ✅ *(n)* |
| Toilet | ✅ *(n)* |
| Garden | — |
| Swimming pool | — |
| Jacuzzi | — |
| Roof | — |

Rooms marked *(n)* can be instantiated several times; the generator
appends the index (`Bedroom 1`, `Bedroom 2`, …). The room identifier
(`bedroom`, `living_room`, …) stays in English in every language — it
feeds `entity_id`s, navigation paths and file names.

### Room slots

Below the band, a room dashboard lays out a **fixed number of panels**,
called slots. The count is fixed so the HUD grid is drawn once and never
deformed by a room holding more devices than another.

| # | id | Holds |
|---|---|---|
| 1 | `climate` | temperature, heating, air conditioning, thermostat |
| 2 | `lights` | lighting |
| 3 | `appliances` | white goods, TV, home cinema, console, wine fridge, spa, HRV, towel rail |
| 4 | `shutters` | roller shutters |
| 5 | `security` | alarm, intercom, camera |
| 6 | `audio` | audio stream |

The slot id is **normalised**: the same string is used as the key in
`house.yaml`, as the CSS `grid-area`, and as the section name in the
template. It is never translated — only its label is, through `slot.*`.

Two rooms use a reduced slot set. This does not fork the template: it only
says which slots are candidates.

| Slot set | Slots |
|---|---|
| `default` | climate, lights, appliances, shutters, security, audio |
| `toilet` | climate, lights, shutters, audio |
| `garden` | climate, lights, appliances, security, audio |

Garden equipment (pool, jacuzzi, sauna, robot mower, pool robot) falls into
`appliances` — no special rule.

**Empty slots.** A slot outside the room's set is not rendered at all: it
collapses and its neighbours expand across the grid. A slot inside the set
but holding no device yet shows `slot.empty` — the distinction matters,
because a toilet will never have shutters whereas a living room may simply
not have integrated them yet. The Visio Sapiens animation fills at most one
slot per dashboard, `shutters` first.

**Slot height is fixed.** A kitchen may hold twelve devices in
`appliances` and a hallway one. Lists scroll inside their panel rather
than stretching it, so every room dashboard keeps the same footprint.

**The audio slot has three states**, because a stream exists independently
of its output:

| State | Rendering |
|---|---|
| stream + speakers | media player with an output selector |
| stream, no speaker | media player + `slot.audio_no_speaker` |
| nothing at all | collapsed |

This is the one slot where the form distinguishes two roles — **source**
and **output** — instead of holding a flat list.

### System dashboards

Four dashboards are always present. Each has its **own predefined
template**, each is generated when the home is created, and **none is tied
to a room name**:

| Dashboard | Role | Template |
|---|---|---|
| `HOME` | entry point, HUD and central radar | `home.yaml.j2` |
| `CORE` | central system monitoring | `core.yaml.j2` |
| `ENERGY` | production, consumption, breaker panel | `energy.yaml.j2` |
| `ADMIN` | the creation console itself | `admin.yaml.j2` |

They exist as soon as a home is created, whatever rooms were declared —
declaring zero room still yields these four. Room dashboards are then
added on top, from a single shared room template.

### Navigation rail

The right-hand navigation rail is a **dynamic template**. It starts from
the four fixed system entries and **completes itself with the declared
rooms**, so its length always equals:

```
4 system dashboards (HOME, CORE, ENERGY, ADMIN)  +  declared rooms
```

Adding a bathroom in the console adds its entry to the rail on every
dashboard at once. No navigation block is maintained by hand anywhere in
the repository.

## Admin console

The console (`ADMIN` dashboard) is the single entry point for creating and
maintaining the home. It drives generation through three inputs:

| Input | Values | Effect |
|---|---|---|
| Language selector | English / French | picks the locale catalogue used for every generated label |
| Format selector | Mobile / Tablet | picks the layout variant of the template |
| Room form | the catalogue above, with a count for *(n)* rooms | determines how many room dashboards are generated and how long the navigation rail is |
| Device assignment | every discovered device → a room **and** a slot | fills the six panels of each room dashboard |

Those three answers are written into `dashboards/model/house.yaml`, which
is the single source of truth. The form also assigns every device to a
room **and to a slot**, so the model is flat and the template routes
nothing:

```yaml
rooms:
  - id: living_room
    slot_set: default
    slots:
      climate:    [climate.living_room_ac]
      lights:     [light.living_room_ceiling, light.living_room_strip]
      appliances: [media_player.tv, media_player.ps5]
      shutters:   [cover.living_room]
      security:   []
      audio:
        source: [media_player.spotify]
        output: [media_player.sonos_living]
```

Order within a list is the order set in the form, not an alphabetical
sort — you decide the TV comes before the console without renaming an
entity. Regenerating from that model is idempotent: rooms added later are
created, the rail is re-rendered, and existing dashboards are refreshed
rather than duplicated.

## Language

**English is the source of truth.** Every user-facing string lives in
`home-assistant/dashboards/locales/en.yaml`; other languages are overlays
merged on top of it, so a missing key falls back to English instead of
rendering an empty label. A partial translation is therefore safe to ship.

The language is chosen once, at generation time — never at runtime:

| Where | What it sets |
|---|---|
| Admin console, language selector | writes `locale:` into `dashboards/model/house.yaml` |
| `generate_dashboards.py` | renders the Jinja2 templates with that catalogue |
| CI variable `VSSP_LOCALE` | renders `config-fragment.yaml` at build time |

Three consumers, one catalogue:

| Consumer | Syntax |
|---|---|
| Jinja2 templates | `{{ t('room.bedroom') }}` |
| Plain files (`config-fragment.yaml`, JS, CSS) | `__T:dashboard.energy.title__` |
| Admin console | reads the merged catalogue as JSON |

Two files look like they should hold translations and cannot. `templates/button_card_templates.yaml` and `decluttering_templates.yaml` are read as-is by Home Assistant through `!include`, so `t()` does not work there — displayed text must be passed in by the calling dashboard, already translated. Likewise, anything a dashboard *references* must be declared in `packages/`, which Home Assistant loads, and not in `vssp/`, which it never reads.

Two rules keep this from breaking a working dashboard:

1. **Stored state stays English.** `input_select` option values remain
   `Day` / `Month` / `Year` in every language — they are identifiers
   compared inside JavaScript, and translating the stored state would
   break those comparisons. Only the displayed label is translated.
2. **Dates come from `Intl`, not from arrays.** Button-card JS blocks use
   `Intl.DateTimeFormat(LOCALE, …)` with `LOCALE` injected at generation,
   which yields `Mon` in English and `lun.` in French for free.

```bash
python3 vssp/vssp_i18n.py check                    # validate every catalogue
python3 vssp/vssp_i18n.py dump --locale fr         # inspect the merged result
python3 vssp/vssp_i18n.py render --locale fr \
    --in home-assistant/config-fragment.yaml \
    --out /tmp/config-fragment.fr.yaml             # preview a rendering
```

Adding a language means dropping a `<code>.yaml` overlay into
`home-assistant/dashboards/locales/` and offering it in the console — no
code change anywhere.

## Conventions

| Item | Rule |
|---|---|
| Code comments (YAML, Python, JS, CSS) | one file, comments in both languages, prefixed `# EN \|` and `# FR \|` |
| User-facing strings | never hardcoded — they live in the locale catalogues |
| Documentation (`.md`) | one file per language: `X.md` (English) + `X.fr.md`, with a language switch line at the top |
| CI job logs, commit messages, branch names | English only — developer-facing, not part of the localized product |
| Identifiers | English only, never translated: room keys, slot ids, `entity_id`, `path` / `navigation_path`, button-card template names, `input_select` option values, `grid-area` names, file names |

## Repository layout

Existing directories are kept as-is; only those marked **NEW** are added
by the dashboard generator and the i18n layer.

```
.
├── .gitlab-ci.yml               validate / build / deploy:staging (k3s)
│                                + smoke tests (/local/vssp/*, __VTOKEN__ cache-busting)
├── hacs.json
├── repository.yaml
├── README.md                    ← this file (English, rendered by default)
├── README.fr.md                 ← NEW — French version
│
├── docs/                        every document exists in both languages
│   │                            (X.md / X.fr.md) — see docs/README.md
│   ├── dashboards/              the interface and how it is generated
│   ├── platform/                the foundation: install, services, security
│   ├── ci-cd/                   the pipeline, and the postmortems
│   └── project/                 vision, case study, YouTube series
│
├── kubernetes/                  k3s manifests (staging target)
├── scripts/                     package.sh / deploy.sh / reload.sh / validate.sh
│
├── themes/
│   └── visio_sapiens.yaml
│
├── vssp/                        Python tooling for the admin process + HA config
│   ├── vssp_discovery.py        scans entities per Area → report.json
│   ├── vssp_upgrade.py          diff report.json ↔ dashboard (non-destructive)
│   ├── vssp_apply_config.py     configuration.yaml patcher (ruamel)
│   ├── vssp_ensure_packages.py
│   ├── vssp_sanitize_resources.py
│   ├── vssp_lan_probe.py
│   ├── vssp_admin_config.yaml   ADMIN helpers / shell_command / scripts
│   ├── vssp_energy_sync.py      measured ENERGY device set (add/remove)
│   ├── generate_dashboards.py   renders the Jinja2 templates
│   ├── build_template.py        turns an existing dashboard into a template
│   └── vssp_i18n.py             ← NEW — i18n engine (load, render, check)
│
└── home-assistant/
    ├── config-fragment.yaml     desired state of the Visio Sapiens keys
    │                            (lovelace, resources) — uses __VTOKEN__ and __T:key__
    ├── config-fragment-rooms.yaml   ← GENERATED — room dashboard declarations
    ├── packages/                loaded by !include_dir_named — ANYTHING the
    │   │                        dashboards reference must live here
    │   ├── vssp_admin.yaml          ADMIN helpers, scripts, shell_command
    │   ├── vssp_energy_totaux.yaml  dynamic totals
    │   └── vssp_generation.yaml ← NEW — language and format selectors,
    │                                deployed-locale and placeholder sensors
    ├── templates/               button_card_templates.yaml, decluttering_templates.yaml
    ├── dashboards/
    │   ├── admin/
    │   │   └── system_dashboards.yaml   ADMIN "system dashboards" card
    │   │                                (CORE/ENERGY, outside the room cycle)
    │   ├── locales/
    │   │   ├── en.yaml            reference catalogue — the contract
    │   │   └── fr.yaml            French overlay
    │   ├── model/
    │   │   └── house.yaml         source of truth: locale, format, rooms, slots, nav
    │   ├── templates_j2/        one template per dashboard AND per format
    │   │   ├── _header.j2         shared header band (tablet)
    │   │   ├── _header_mobile.j2  compact header, title + clock in one card
    │   │   ├── _nav.j2            dynamic vertical rail
    │   │   ├── _nav_mobile.j2     scrolling chip bar
    │   │   ├── home.yaml.j2       main dashboard — holds BOTH the HOME and
    │   │   │                      ADMIN views, hence no admin.yaml.j2
    │   │   ├── home_mobile.yaml.j2  HOME only; the console is a desk task
    │   │   ├── energy.yaml.j2
    │   │   ├── room.yaml.j2       shared template, one render per room
    │   │   └── room_mobile.yaml.j2  single column, one slot per row
    │   └── views/              ← GENERATED — do not edit by hand
    │                              every rendered dashboard lands here, so a
    │                              single include convention (../templates/)
    └── www/vssp/                CSS/JS engine, components, admin console, assets
        ├── css/  js/  components/  fonts/  icons/
        ├── wizard/              web form backing the admin console
        ├── backgrounds/
        └── images/
```

## Generation pipeline

| Step | Status | Where |
|---|---|---|
| 0. Language and format selectors | 🟡 catalogues and engine ready, console step to wire up | `dashboards/locales/` + `vssp/vssp_i18n.py` |
| 1. Room form | 🟡 rooms declared, count for *(n)* rooms to wire up | `www/vssp/wizard/` |
| 2. Connected device scan | ✅ `vssp_discovery.py` (DISCOVERY SCAN button) → `report.json` | `vssp/` |
| 3. Device → room assignment | ✅ per-entity room selector | `www/vssp/wizard/` |
| 4. Write the home model | 🔴 to build — the console must write `house.yaml`, not just `report.json` | `dashboards/model/` |
| 5. Dashboard generation | 🟡 **done for ENERGY** — `energy.yaml.j2` + `generate_dashboards.py` (100% fidelity confirmed by structural comparison); to be extended to every room template | `dashboards/templates_j2/` + `vssp/` |
| 6. Dynamic navigation rail | 🔴 to build — render the rail from the room list rather than maintaining it by hand | `dashboards/templates_j2/` |

Step 4 is the missing link: writing the console's answers (locale, format,
rooms, device assignment) into `dashboards/model/house.yaml`, then calling
`generate_dashboards.py`. `vssp_upgrade.py` remains the non-destructive
diff tool for checking discrepancies before regenerating.

## Generating the dashboards

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py    # defaults aligned with this repo
```

The generator reads `locale:`, `format:` and the room list from
`house.yaml`, and injects `t()`, `locale` and `locale_tag` into the Jinja2
environment. Details, safety rails and `shell_command` integration: see
`docs/dashboards/Dashboard_Generator.md`.

## CI/CD

GitLab pipeline (`.gitlab-ci.yml`), five stages:

| Stage | What it does |
|---|---|
| `validate` | repo structure, YAML syntax, locale catalogue consistency, `__T:` placeholder resolution, `OSV_PREFIX` coverage, committed-secret check |
| `build` | `dist/` package, locale rendering of `config-fragment.yaml`, unrendered-placeholder guard, `__VTOKEN__` cache-busting, `!include` resolution, whitelist guard |
| `deploy` | staging on k3s (branches/MR) or production on HAOS over SSH (tags, manual gate), placeholder guard before patching, `check_config` and automatic rollback |
| `test` | HTTP smoke tests on `/local/vssp/*` and the HA API |
| `release` | HACS package (including every `README.*.md`) and GitLab release |

Set `VSSP_LOCALE` (Settings > CI/CD > Variables, or per pipeline run) to
build a deliverable in another language. `en` is the default and produces
the untouched reference wording. A locale with no catalogue fails
`validate` rather than shipping unreplaced placeholders to the Home
Assistant sidebar.

## Documentation

Everything lives in [`docs/`](docs/README.md), in both languages (`X.md` /
`X.fr.md`, side by side). Four areas, answering four different questions:

| | |
|---|---|
| [`docs/dashboards/`](docs/dashboards) | the interface and how it is generated — generator, design system, CORE, chatbot, calendar, updates |
| [`docs/platform/`](docs/platform) | the foundation — deployment, the Vault safe, security, backups, MQTT on k3s |
| [`docs/ci-cd/`](docs/ci-cd) | the pipeline, and the field postmortems |
| [`docs/project/`](docs/project) | vision, case study, YouTube series |

Start at [`docs/README.md`](docs/README.md) for the annotated index.

## Status

🚧 Under active development — see `docs/project/Vision.md` and `docs/ci-cd/Troubleshooting.md` for the
iteration details.
