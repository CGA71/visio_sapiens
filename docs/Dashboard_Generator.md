# Visio Sapiens — Dashboard Generator (admin process step 5)

**English** · [Français](Dashboard_Generator.fr.md)

## Principle

`views/energy.yaml` is no longer edited by hand. It is **generated**
from:

- **`home-assistant/dashboards/model/house.yaml`** — the business model:
  rooms, devices, circuits, solar/grid sensors, navigation (desktop
  `path` and mobile `path_mobile`). This is the file that the admin
  process will feed (wizard Phase 1 = rooms, Phase 2 = scan +
  assignment).
- **`home-assistant/dashboards/templates_j2/energy.yaml.j2`** — the
  Jinja2 template, which carries the graphic charter, the grid layout,
  the fonts and the card model. Derived from the original `energy.yaml`
  with 100% fidelity (validated by structural comparison of the parsed
  YAML).

```
dashboards/model/house.yaml ──┐
                              ├── vssp/generate_dashboards.py
dashboards/templates_j2/*.j2 ─┘            │
                                           ▼
                          dashboards/views/energy.yaml
```

## Location in the repo (existing directories unchanged)

```
vssp/
├── vssp_discovery.py          EXISTING — scan by Area → report.json
├── vssp_upgrade.py            EXISTING — non-destructive diff
├── generate_dashboards.py     ← NEW
└── build_template.py          ← NEW (templates an existing dashboard)

home-assistant/
├── templates/                 EXISTING — button_card_templates.yaml, …
└── dashboards/
    ├── views/
    │   └── energy.yaml        ← GENERATED, do not edit
    ├── model/                 ← NEW
    │   └── house.yaml
    └── templates_j2/          ← NEW
        └── energy.yaml.j2
```

Note on `!include`: the `energy.yaml.j2` template keeps the path to
your working dashboard as-is
(`!include ../templates/button_card_templates.yaml`). If your includes
resolve to `home-assistant/templates/` in your deployment, nothing
needs to change; otherwise adapt this line in the `.j2` file once — it
will be carried through on every generation.

## Usage

From the root of the repo (the script's defaults point to these
paths):

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py
```

Then refresh the dashboard tab (Ctrl+Shift+R). No reload service is
needed: a dashboard in YAML mode is re-read by Home Assistant as soon
as the file changes (date comparison in the Lovelace cache). There is
in fact no `lovelace.reload` service — only `lovelace.reload_resources`
exists, and it only concerns JS/CSS resources.
In CI deployment, the generated file goes into the `dist/` package like
any other YAML file under `dashboards/` — nothing to change in the
pipeline.

## Adding a new connected device (manually, pending the wizard → model bridge)

1. Open `home-assistant/dashboards/model/house.yaml`
2. Add the device under the right room:

```yaml
rooms:
  - id: livingroom
    name: "Salon"
    devices:
      - name: "TV"
        icon: mdi:television
        model: "Shelly Plug S"
        power_entity: sensor.shelly_tv_power
        energy_entity: sensor.shelly_tv_energy_today
```

3. Re-run `vssp/generate_dashboards.py` → the row appears in the
   "Consumption by device" panel of ENERGY.

If the room doesn't exist yet, add it under `rooms:` (and under `nav:`
if it should appear in the sidebars — each `nav` entry carries `path`
for desktop and `path_mobile` for the `-m` dashboards).

## System dashboards (ENERGY, CORE) — outside the room lifecycle

ENERGY and CORE are not attached to any Home Assistant room. They
therefore do not go through the wizard's create / modify / delete form,
which reasons per room: they have their own lifecycle, driven from the
ADMIN panel.

The card lives in its own file,
`home-assistant/dashboards/admin/system_dashboards.yaml`, loaded by
`home.yaml` via `- !include admin/system_dashboards.yaml` — the same
mechanism as your views.

The panel displays **a single two-state slot**, so that no mishandling
can overwrite an in-place dashboard:

| State of the `views/energy.yaml` file | Button shown | Action |
|---|---|---|
| absent | **CREATE ENERGY** | fleet sync + generation (`--only energy --if-missing`) |
| present | **REGENERATE ENERGY** | backup + sync + full generation |
| (always) | **SYNC ENERGY** | updates the tables without regenerating everything |

The toggle relies on `binary_sensor.vssp_dashboard_energy_present`, a
`command_line` sensor that checks the file's existence every 60 s. The
REGENERATE button's label shows the date of the last generation and the
number of measured devices detected.

Double safety on the generator side: `--if-missing` means the create
action **cannot** overwrite an existing file, even if the button is
clicked by mistake or the sensor is one cycle behind.

CORE appears in the panel for consistency, but its button stays
inactive as long as `core.yaml.j2` doesn't exist. Once the template is
written, it will be enough to uncomment the `core` entry in
`DASHBOARDS` (`generate_dashboards.py`) and duplicate ENERGY's
conditional pair.

## ENERGY — a dynamic, two-speed dashboard

ENERGY is not a room dashboard: it lists every measured device in the
house. It updates at two different levels, and it's important to know
which one applies to what.

| Panel | Mechanism | Regeneration needed? |
|---|---|---|
| Total consumption (day / month / year) | **live scan** — `packages/vssp_energy_totaux.yaml` sums all `*_puissance` and `*_energie` sensors | **No** — automatic |
| Instantaneous house power | live scan (same) | **No** |
| Consumption by device (rows) | Jinja loop over `model/energy_devices.yaml` | Yes |
| Electrical panel (cells) | Jinja loop over `circuits` | Yes |

The reason for this asymmetry: Lovelace cannot loop over a list of
entities. A sum, it can — hence totals that are genuinely live, and
tables that require a generation pass.

### The automatic loop

```
pairing / removal of a Shelly
        │
        ├─► totals: updated immediately (scan)
        │
        └─► entity_registry_updated event
                │  (vssp_energy_autosync automation, 5-min debounce)
                ├─► vssp_energy_sync.py    → updates energy_devices.yaml
                ├─► generate_dashboards.py → regenerates views/energy.yaml
                └─► lovelace.reload
```

A daily pass at 04:30 acts as a safety net, in case an event was
missed (a restart during pairing, for example).

### vssp_energy_sync.py — non-destructive merge

The script pairs up a device's sensors by entity radical
(`sensor.shelly_bureau_power` + `sensor.shelly_bureau_energy_today`),
detects `switch.*` entities for the electrical panel, then merges with
the existing data:

- **new device** → appended to the end of the list;
- **already known device** → kept as-is, with your customizations
  (name, icon, model, amperage, display order) preserved;
- **device gone from HA** → *flagged but not removed*. An offline
  Shelly must not make its row disappear. Actual removal requires
  `--prune` (the ADMIN panel's PRUNE button);
- **`keep: true`** on a device → never removed, even with `--prune`
  (useful for seasonal equipment).

A device only enters the table if it has **both** sensors (power AND
energy): a row without its energy column wouldn't make sense.
Aggregates (`sensor.home_*`, `sensor.solar_*`, `sensor.grid_*`,
`*_room_power`) are excluded to avoid double counting.

### Naming convention (the key to everything)

| Suffix | Meaning | Enters the scans |
|---|---|---|
| `*_puissance` / `*_power` | instantaneous power | yes (power total) |
| `*_energie` / `*_energy` | cumulative (lifetime) counter | yes (energy total) |
| `*_energie_jour` / `*_energy_today` | daily counter | no — otherwise lifetime kWh and today's kWh would get mixed together |

The `sensor.vssp_appareils_mesures` sensor counts the detected devices:
if its value exceeds the number of rows in the table, a resync is
pending.

## Preview — iterating without touching staging

The wizard (phase 4) and the generator know how to produce an
**isolated test** dashboard. Three levels, from most cautious to most
committal:

| Mode | Command | What it writes |
|---|---|---|
| Validation only | `--dry-run` | nothing (just the JSON report) |
| Preview | `--preview` | `views/energy_preview.yaml` (url `vssp-energy-preview`) |
| Publish | *(no flag)* | `views/energy.yaml` (staging) |

Isolation relies on three things happening simultaneously: a
**suffixed output file** (`_preview.yaml`), a **distinct url_path**
(`vssp-energy-preview`, i.e. a separate Lovelace entry declared once
and for all), and a **separate model**
(`model/house_rooms.preview.yaml`). No staging path appears anywhere
in the preview chain — this isn't a naming convention, it's
structural.

Typical iteration loop:

```bash
# 1. test
python3 vssp/generate_dashboards.py --preview
# 2. open /vssp-energy-preview/energy, fix the model or the template
# 3. re-run as many times as needed… then, and only then:
python3 vssp/generate_dashboards.py
```

The generator writes a JSON report (`--status-file`) that the wizard
reads via `/local/vssp/preview_status.json`: number of rooms, devices,
circuits, devices in TODO state, and validation errors if any.

Declaration of the preview dashboard: see
`config-fragment-preview.yaml` (to be merged once into
`home-assistant/config-fragment.yaml`). Remember to add the
`*_preview.yaml`, `*.preview.yaml` and `preview_status.json` files to
`.gitignore` so they never get committed in CI.

## Guardrails built into the generator

- **Model validation** before rendering: required fields present, no
  entity assigned to two rooms at once.
- **`StrictUndefined`**: a missing variable in the model makes
  generation fail instead of producing a silent hole.
- **YAML validation of the render before writing**: a broken template
  never replaces a working dashboard.

This is complementary to `vssp_upgrade.py`: upgrade compares what
exists against what was discovered (diagnosis), the generator produces
the target state (construction).

## Home Assistant integration — to add to `vssp/vssp_admin_config.yaml`

In the same style as `vssp_discovery` / `vssp_upgrade` (the repo being
deployed under `/config` on the pod):

```yaml
shell_command:
  vssp_generate_dashboards: >-
    python3 /config/vssp/generate_dashboards.py
    --model /config/dashboards/model/house.yaml
    --templates /config/dashboards/templates_j2
    --out /config/dashboards/views

script:
  vssp_run_generate:
    alias: "Visio Sapiens — Regenerate dashboards"
    sequence:
      - service: shell_command.vssp_backup_dashboard
      - service: shell_command.vssp_generate_dashboards
      - service: persistent_notification.create
        data:
          title: "Visio Sapiens — Dashboards regenerated"
          message: >
            energy.yaml has been regenerated from model/house.yaml.
            Reload Lovelace to see the result.
```

A GENERATE button can join the DISCOVERY / UPGRADE / DELETE row of the
ADMIN panel (`template: vssp_admin_button`,
`service: script.vssp_run_generate`).

## Wizard → model bridge (the missing link between steps 4 and 5)

The wizard (Phase 2) already knows `{entity_id, friendly_name, room}`;
`vssp_discovery.py` produces `report.json` grouped by Area and
device_class. Next building block: a small
`vssp/vssp_model_sync.py` that

1. reads `report.json` + the wizard's assignments,
2. maps `power`/`energy` entities per device (icon inferred from the
   device_class, model taken from the device registry),
3. merges into `model/house.yaml` **without overwriting** fields already
   customized (name, icon),
4. calls `generate_dashboards.py`.

`vssp_upgrade.py` then acts as the final check: zero expected gap
between the assigned discovered entities and the generated dashboard.

## Templating the other dashboards

`vssp/build_template.py` demonstrates the method: exact replacement of
repetitive blocks with Jinja loops + entity substitution. Next
candidates, in order of return on effort:

1. **`views/energy_mobile.yaml`** — same `house.yaml` model, mobile
   layout (dashboard `visio-sapiens-energy-m` already declared in
   `config-fragment.yaml`).
2. **`home_mobile.yaml`** — the 12 nav tiles are generated from `nav:`
   with `path_mobile`.
3. **`home.yaml`** — sidebar + KPIs + view includes driven by the
   model.
4. **`room.yaml.j2`** — a single per-room template that generates
   `views/livingroom.yaml`, `views/bedroom1.yaml`, etc. from `rooms:`
   (the views still commented out at the end of `home.yaml`).
