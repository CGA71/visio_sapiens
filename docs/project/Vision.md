# Visio Sapiens

**English** · [Français](Vision.fr.md)

A home-automation OS with a futuristic interface comparable to a control
center.

The foundation rests on:

* button-card (HUD, navigation, widgets)
* card-mod (advanced CSS)
* layout-card (free-form layout)
* stack-in-card
* apexcharts-card
* mini-graph-card
* config-template-card
* browser_mod
* decluttering-card
* a CSS and JavaScript engine built in-house for Visio Sapiens

The goal is for Home Assistant to become nothing more than a data engine. The
entire interface is driven by VSSP.

## Architecture

```
Visio Sapiens

├── CORE
│      HUD
│      IA
│      Radar
│      Navigation
│
├── Room Engine
│      Living
│      Bedroom1
│      Bedroom2
│      Bathroom
│      Computer      ← shipped
│      Technical     ← shipped (desktop + mobile)
│      Secret
│      Garden
│      Energy        ← shipped (desktop + mobile)
│
├── IA Layer
│      Widgets
│      Alerts
│      Notifications
│      Assistant
│
├── Animation Engine
├── CSS Engine
├── JS Engine
└── Theme Engine
```

The HOME dashboard is no longer an assembly of cards: it is a single unified
interface.

# Visio Sapiens Framework

1. VSSP Core UI (HUD, navigation, layout)
2. CSS Engine (~800 lines dedicated to the visual identity)
3. JavaScript Engine (animations, radar, IA, interactions)
4. Button-Card Templates (library of reusable components, `vssp_` prefix)
5. Dashboards built on these components, with no visible native cards

**Rule:** stop using classic Lovelace cards, except for deliberate, documented
exceptions (`weather-forecast`, `logbook`, `apexcharts-card`).

The interface is composed of:
* animated HUD
* vertical navigation sidebar
* central radar
* IA Core
* translucent cards
* neon CPU / GPU / RAM / Storage / Network gauges
* CSS animations
* reusable components

---

# Actual repository structure

```
visio-sapiens/
├── .gitlab-ci.yml              dual-target pipeline (k3s staging / HAOS prod)
├── hacs.json                   HACS distribution (domains: theme)
├── repository.yaml
├── README.md
│
├── themes/                     ← ROOT, imposed by HACS
│      visio_sapiens.yaml       (theme name in dashboards: "Visio Sapiens")
│
├── docs/
│      project.md               this file
│      core.md                  how core.html works
│      CI_CD.md                 full pipeline reference
│      DIAGNOSTIC_staging.md
│      INTEGRATION_technical_room.md
│      Generator_templating.md
│
├── vssp/                       Python scripts + associated HA config
│      vssp_apply_config.py     idempotent patcher for configuration.yaml
│      vssp_ensure_packages.py  sets the homeassistant.packages key
│      vssp_sanitize_resources.py  deduplicates Lovelace resources
│      vssp_discovery.py        read-only scan by Area → report.json
│      vssp_upgrade.py          diff discoveries ↔ dashboard (non-destructive)
│      vssp_patch_dashboard.py  floor-plan overlays
│      vssp_lan_probe.py        LAN / Livebox / switch probe
│      vssp_admin_config.yaml   helpers, shell_command, ADMIN panel scripts
│      livebox.env              NON-secret box settings (versioned)
│      .livebox.env             secret, generated at deploy time — NEVER versioned
│
└── home-assistant/
    ├── config-fragment.yaml    desired state of the Visio Sapiens keys of configuration.yaml
    │
    ├── packages/               multi-domain HA packages
    │      vssp_technical_room.yaml
    │      spvs_energy_totaux.yaml
    │
    ├── templates/              target of the views' `!include ../templates/…`
    │      button_card_templates.yaml
    │      decluttering_templates.yaml
    │
    ├── dashboards/
    │      home.yaml            desktop overview (+ hidden ADMIN view)
    │      home_mobile.yaml     mobile overview
    │      views/
    │          core.yaml               iframe to core.html
    │          computer.yaml
    │          energy.yaml
    │          energy_mobile.yaml
    │          technical_room.yaml
    │          technical_room_mobile.yaml
    │
    └── www/
        └── vssp/               served by HA under /local/vssp/
            ├── core.html       standalone system dashboard (Glances + K3s)
            ├── css/
            │      vssp.css     CSS Engine
            ├── js/
            │      osvision.js  JS Engine (pub/sub bus + helpers)  ⚠️ to be renamed
            ├── components/
            │      osv-core.js
            │      osv-card.js
            │      osv-datetime-card.js
            │      osv-ad-banner-card.js
            ├── backgrounds/    core.png, home.png, energy.png (technical.png missing)
            ├── images/
            ├── icons/
            └── fonts/
```

## Declared dashboards (`config-fragment.yaml`)

| url_path | Title | File | Sidebar |
|---|---|---|---|
| `visio-sapiens` | Visio-Sapiens | `dashboards/home.yaml` | ✔ |
| `visio-sapiens-m` | Visio-Sapiens | `dashboards/home_mobile.yaml` | ✔ |
| `visio-sapiens-core` | Core System | `dashboards/views/core.yaml` | — |
| `visio-sapiens-computer` | Computer Room | `dashboards/views/computer.yaml` | — |
| `visio-sapiens-energy` | Energy Management | `dashboards/views/energy.yaml` | — |
| `visio-sapiens-energy-m` | Energy Management | `dashboards/views/energy_mobile.yaml` | — |
| `visio-sapiens-technical` | Technical Room | `dashboards/views/technical_room.yaml` | — |
| `visio-sapiens-technical-m` | Technical Room | `dashboards/views/technical_room_mobile.yaml` | — |

The `visio-sapiens` prefix is not cosmetic: `vssp_apply_config.py` only merges
into `configuration.yaml` the keys that start with
`OSV_PREFIX = "visio-sapiens"`. **Any new entry must follow this
convention**, or it will be silently ignored at deploy time.

# Declared Lovelace resources

HACS cards: button-card, layout-card, card-mod, stack-in-card,
apexcharts-card, mini-graph-card, config-template-card, decluttering-card.

In-house engines, served from `/local/vssp/` with a cache-buster
`?v=__VTOKEN__` replaced at deploy time by the build version.

⚠️ **Known discrepancy** — the fragment currently declares
`/local/vssp/css/osvision.css` while the file is actually named `css/vssp.css`,
and the CI smoke test queries `/local/vssp/js/vssp.js` while the file is
actually named `js/osvision.js`. The CSS Engine therefore returns 404 and the
`test:staging` job fails. Detailed fix in **G1 of `CI_CD.md`**.

---

# CHANGELOG — Changes since the initial V2

## Navigation

* The original skeleton's horizontal HOME / ROOMS / SYSTEM / ENERGY bar has
  been replaced by a **full-height vertical sidebar** (logo at the top, items
  with icon + title + subtitle, active highlight, hover across the whole
  list, animated branding at the bottom of the sidebar).
* New templates: `vssp_sidebar_logo`, `vssp_nav_button` (reworked),
  `vssp_sidebar_brand_footer`.
* Mobile version: **single-row scrolling** navigation bar (fixed-width custom
  field + `overflow-x` + `touch-action: pan-x`), transposing the pattern
  from `energy_mobile.yaml`'s electrical panel.

## HUD banner (header)

* 5-cell banner reproducing the target mockup:
  1. Back chevron + page title + description (`vssp_page_header`)
  2. Outdoor weather — **native** `weather-forecast` card
  3. Live date/time — custom `osv-datetime-card` component
  4. Alarm status (generic skeleton, reacts to `entity.state` regardless of
     domain) — `vssp_alarm_status`
  5. Circular "OS" avatar — `vssp_os_avatar`

## Energy row (HOME view)

1. Solar production / consumption curve — `apexcharts-card` (2 series)
2. kW production / consumption summary — `vssp_metric`
3. Connected devices' events — **native** `logbook` card
4. Security/Alarm panel — reactive circular badge + 4 status lines
   (`vssp_security_badge`, `vssp_security_row`)

## ENERGY dashboard

* Standalone desktop view + dedicated mobile view.
* Panels: solar production, per-device consumption (8 lines), total
  consumption, operation diagram, surplus/EDF resale, electrical panel
  (12 `vssp_circuit_switch` circuits).
* `spvs_energy_totaux.yaml` package: sums up `*_energie` sensors into
  `sensor.home_energy_total`.

## TECHNICAL ROOM dashboard

* Desktop and mobile views, `vssp_technical_room.yaml` package, LAN probe
  `vssp_lan_probe.py` (Livebox + Netgear switch).
* The existing navigation links (`/visio-sapiens-technical/technical`,
  mobile TECH chip) were already in place: the integration brought them to
  life without touching the navigation.
* The box's secret is managed via a masked CI/CD variable, never versioned.

## CORE dashboard

* The view displayed gauges/charts/temperatures/K3s twice: native HA cards
  **and** an iframe to `core.html`, which already recreates all of it in JS.
  The native cards were removed; the view now contains only sidebar + first
  row of the banner + iframe + footer.
* See [Core_Dashboard.md](../dashboards/Core_Dashboard.md) for the full Glances → HA → page chain.

## JS components

* `osv-card.js` (footer) and `osv-datetime-card.js` were made **self-sufficient**:
  they now compute time/date natively instead of depending on the engine,
  following a bug where that dependency silently failed on certain
  deployments.
* The JS engine is kept for its pub/sub bus and color/threshold helpers
  (`clamp`, `colorForValue`), reusable by future components. It is still
  exposed as `window.osvision` — to be renamed together with the file.

## ADMIN panel

* Hidden view `/visio-sapiens/admin` (desktop) and `/visio-sapiens-m/admin`
  (mobile), not linked in the menu, restricted to a specific HA user via
  `visible:`.
* Three actions:
  - **DISCOVERY** — runs `vssp_discovery.py` (read-only scan of entities by
    Area).
  - **UPGRADE** — runs `vssp_upgrade.py` (compares the discovery report to
    the current dashboard, lists discrepancies — never modifies the YAML).
  - **DELETE DASHBOARD** — protected by PIN code + native confirmation +
    automatic backup. Visual feedback via `browser_mod.popup`.
* ⚠️ **Two open defects in `vssp_admin_config.yaml`**:
  the backup and delete `shell_command`s target
  `/config/home-assistant/dashboards/home.yaml`, a path that does not exist
  on the pod (deployment installs the dashboards under `/config/dashboards/`)
  — so the DELETE button's backup is a no-op; and `input_text.vssp_ha_token`
  is used without being declared. Details in [Dashboard_Generator.md](../dashboards/Dashboard_Generator.md).
* ⚠️ The `vssp_discovery.py` / `vssp_upgrade.py` scripts **are not copied into
  the deployment package**: the buttons are inert in both staging and
  production until fix G2 of `CI_CD.md` is applied.

## Industrialization (deployment)

* `config-fragment.yaml`: desired state of the Visio Sapiens keys of
  `configuration.yaml`, applied by an idempotent patcher that **preserves
  everything else** in the file (third-party keys, order, comments,
  `!include` tags) and creates a timestamped backup before any write.
* Dual-target GitLab pipeline: MR/`master` → k3s (staging), tag → HAOS
  (production, manual gate). Checks `!include`s, resource cache-busting,
  smoke tests, automatic rollback if `check_config` fails.
* See `docs/CI_CD.md` for details and the five holes still open.

## OSVision → VSSP naming migration — status

| Item | Status |
|---|---|
| Project name, README, `hacs.json`, `repository.yaml` | ✅ |
| `vssp/` folder, `vssp_*.py` scripts | ✅ |
| `home-assistant/www/vssp/`, `/local/vssp/` URL | ✅ |
| `vssp_*` button-card templates | ✅ |
| `visio-sapiens-*` dashboard keys + `OSV_PREFIX` | ✅ |
| `themes/visio_sapiens.yaml` theme | ✅ |
| `css/vssp.css` | ✅ file renamed, ❌ fragment URL not updated |
| `js/osvision.js`, global `window.osvision` | ❌ to be renamed |
| `OSVISION_VERSION` version file produced by CI | ❌ to be renamed to `VSSP_VERSION` |
| `core.html`'s `osv_ha_token` `localStorage` key | ⏸ to be migrated carefully (breaks sessions) |
| K3s path `/local/osvision_v2/k3s_stats.json` in `core.html` | ❌ broken, fix to `/local/vssp/` |
| Internal `osvision_*` comments in `vssp.css` | ⏸ cosmetic |
| `OSV_PREFIX`, `OSV_VERSION`, `.osv_stage` prefixes (internal CI) | ⏸ no functional impact |

## Identified next steps

* Apply fixes G1 → G5 of `CI_CD.md` (in this order: resources, admin scripts,
  version, generator, robustness).
* Model-driven dashboard generator (`model/house.yaml` + `templates_j2/*.j2`)
  — see [Dashboard_Generator.md](../dashboards/Dashboard_Generator.md). Next step: `vssp_model_sync.py`, a bridge
  between the discovery report and the model.
* Switch the **Discovery** and **Upgrade** popups to `browser_mod.popup`
  (currently still on `persistent_notification`).
* Automation to detect a new entity not assigned to an Area, with an
  actionable notification offering to assign it.
* Remaining room views (Living, Bedroom1/2, Bathroom, Secret, Garden), ideally
  generated from a single `room.yaml.j2` rather than hand-written.
