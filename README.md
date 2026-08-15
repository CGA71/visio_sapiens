# Visio Sapiens — Neural Home Interface

**English** · [Français](README.fr.md)

A futuristic Home Assistant interface inspired by OSVision, designed for
tablet and mobile. Each room becomes a system module; dashboards are
progressively **generated** from a domain model rather than hand-written.

## Concept

- CORE (Home) — HUD, central radar, AI Core, metrics
- LIVING / SLEEP MODULES — living spaces
- DATA CENTER / ENGINE ROOM — computer room, technical room
- POWER GRID — energy management (solar, grid, breaker panel)
- Shared navigation sidebar, neon/glassmorphism design system

## Stack

Home Assistant (Lovelace YAML), button-card, card-mod, layout-card,
stack-in-card, apexcharts-card, mini-graph-card, config-template-card,
decluttering-card, browser_mod — `Visio Sapiens` theme, in-house CSS/JS
engine (`www/vssp/`). GitLab CI/CD → k3s.

## Language

**English is the source of truth.** Every user-facing string lives in
`home-assistant/dashboards/locales/en.yaml`; other languages are overlays
merged on top of it, so a missing key falls back to English instead of
rendering an empty label. A partial translation is therefore safe to ship.

The language is chosen once, at generation time — never at runtime:

| Where | What it sets |
|---|---|
| Admin wizard, Phase 0 | writes `locale:` into `dashboards/model/house.yaml` |
| `generate_dashboards.py` | renders the Jinja2 templates with that catalogue |
| CI variable `VSSP_LOCALE` | renders `config-fragment.yaml` at build time |

Three consumers, one catalogue:

| Consumer | Syntax |
|---|---|
| Jinja2 templates | `{{ t('energy.tab.day') }}` |
| Plain files (`config-fragment.yaml`, JS, CSS) | `__T:dashboard.energy.title__` |
| Admin wizard | reads the merged catalogue as JSON |

Two rules keep this from breaking a working dashboard:

1. **Stored state stays English.** `input_select` option values remain
   `Day` / `Month` / `Year` in every language — they are identifiers
   compared inside JavaScript, and translating the stored state would
   break those comparisons. Only the displayed tab label is translated.
2. **Dates come from `Intl`, not from arrays.** Button-card JS blocks use
   `Intl.DateTimeFormat(LOCALE, …)` with `LOCALE` injected at generation,
   which yields `Mon` in English and `lun.` in French for free. The
   `date.*` arrays in the catalogues exist only as an override when exact
   wording control is needed.

```bash
python3 vssp/vssp_i18n.py check                    # validate every catalogue
python3 vssp/vssp_i18n.py dump --locale fr         # inspect the merged result
python3 vssp/vssp_i18n.py render --locale fr \
    --in home-assistant/config-fragment.yaml \
    --out /tmp/config-fragment.fr.yaml             # preview a rendering
```

Adding a language means dropping a `<code>.yaml` overlay into
`home-assistant/dashboards/locales/` and setting `VSSP_LOCALE` — no code
change anywhere.

## Conventions

| Item | Rule |
|---|---|
| Code comments (YAML, Python, JS, CSS) | one file, comments in both languages, prefixed `# EN \|` and `# FR \|` |
| User-facing strings | never hardcoded — they live in the locale catalogues |
| Documentation (`.md`) | one file per language: `X.md` (English) + `X.fr.md`, with a language switch line at the top |
| CI job logs, commit messages, branch names | English only — developer-facing, not part of the localized product |
| Identifiers | English only, never translated: `entity_id`, `path` / `navigation_path`, button-card template names, `input_select` option values, `grid-area` names, file names |

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
├── docs/
│   ├── project.md               architecture, iteration changelog
│   ├── modules.md
│   ├── desygn-system.md         design system
│   ├── osvision.md
│   ├── CI_INTEGRATION.md        configuration.yaml patch in the pipeline
│   └── Generator_templating.md  dashboard generator (step 5)
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
    ├── packages/                vssp_energy_totaux.yaml (dynamic totals), …
    ├── templates/               button_card_templates.yaml, decluttering_templates.yaml
    ├── dashboards/
    │   ├── home.yaml            main dashboard /visio-sapiens (+ ADMIN view)
    │   ├── home_mobile.yaml     mobile variant /visio-sapiens-m
    │   ├── admin/
    │   │   └── system_dashboards.yaml   ADMIN "system dashboards" card
    │   │                                (ENERGY/CORE, outside the room cycle)
    │   ├── locales/            ← NEW
    │   │   ├── en.yaml            reference catalogue — the contract
    │   │   └── fr.yaml            French overlay
    │   ├── views/               views and standalone dashboards
    │   │   ├── core.yaml
    │   │   ├── computer.yaml
    │   │   ├── energy.yaml          ← GENERATED — do not edit by hand
    │   │   ├── energy_mobile.yaml
    │   │   ├── technical_room.yaml
    │   │   └── technical_room_mobile.yaml
    │   ├── model/
    │   │   └── house.yaml         domain model (rooms, devices, circuits, nav, locale)
    │   └── templates_j2/
    │       └── energy.yaml.j2     Jinja2 template (ENERGY design system)
    └── www/vssp/                CSS/JS engine, components, wizard, assets
        ├── css/  js/  components/  fonts/  icons/
        ├── wizard/              web form (phases 0-4 of the admin process)
        ├── backgrounds/
        └── images/
```

## Admin process — automatic dashboard generation

| Step | Status | Where |
|---|---|---|
| 0. Language selection | 🟡 catalogues and engine ready, wizard step to wire up | `dashboards/locales/` + `vssp/vssp_i18n.py` |
| 1. Tablet / mobile | ✅ `home.yaml` + `home_mobile.yaml` dashboards (`-m` variants declared in `config-fragment.yaml`) | `dashboards/` |
| 2. Rooms / floors form | ✅ wizard Phase 1 | `www/vssp/wizard/` |
| 3. Connected device scan | ✅ `vssp_discovery.py` (DISCOVERY SCAN button in the ADMIN panel, or wizard Phase 2) → `report.json` | `vssp/` |
| 4. Device → room assignment | ✅ wizard Phase 2 (per-entity room selector) | `www/vssp/wizard/` |
| 5. Dashboard generation | 🟡 **done for ENERGY** — `energy.yaml.j2` + `generate_dashboards.py` (100% fidelity confirmed by structural comparison); to be extended to the other views | `dashboards/templates_j2/` + `vssp/` |

The remaining link between 4 and 5: write the wizard's assignment result
into `dashboards/model/house.yaml` (instead of `report.json` alone),
together with the language chosen at step 0, then call
`generate_dashboards.py`. `vssp_upgrade.py` remains the non-destructive
diff tool for checking discrepancies before regenerating.

## Generating the dashboards

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py    # defaults aligned with this repo
```

The generator reads `locale:` from `house.yaml` and injects `t()`,
`locale` and `locale_tag` into the Jinja2 environment. Details, safety
rails and `shell_command` integration: see `docs/Generator_templating.md`.

## CI/CD

GitLab pipeline (`.gitlab-ci.yml`), five stages:

| Stage | What it does |
|---|---|
| `validate` | repo structure, YAML syntax, locale catalogue consistency, `__T:` placeholder resolution, `OSV_PREFIX` coverage, committed-secret check |
| `build` | `dist/` package, locale rendering of `config-fragment.yaml`, `__VTOKEN__` cache-busting, `!include` resolution, whitelist guard |
| `deploy` | staging on k3s (branches/MR) or production on HAOS over SSH (tags, manual gate), with `check_config` and automatic rollback |
| `test` | HTTP smoke tests on `/local/vssp/*` and the HA API |
| `release` | HACS package (including every `README.*.md`) and GitLab release |

Set `VSSP_LOCALE` (Settings > CI/CD > Variables, or per pipeline run) to
build a deliverable in another language. `en` is the default and produces
the untouched reference wording. A locale with no catalogue fails
`validate` rather than shipping unreplaced placeholders to the Home
Assistant sidebar.

## Status

🚧 Under active development — see `docs/project.md` (changelog) for the
iteration details.
