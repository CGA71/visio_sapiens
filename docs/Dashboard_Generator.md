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

The visual charter itself follows the same generated-from-a-model
principle: `themes/visio_sapiens.yaml` is now rendered from
`model/design_system.yaml` by `templates_j2/theme.yaml.j2`, editable
graphically from the ADMIN console's THEME screen. See
[Design_System_Editor.md](Design_System_Editor.md).

## Room dashboard grid — dynamic slot layout (**proposed, not yet implemented**)

**Status: design agreed 2026-08-31, pending simulation before any code
is written.** Everything in this section describes a *target*
behaviour, not what `room.yaml.j2` currently does. Today's shipped
mechanism — a hand-drawn grid per `slot_set` in `DEFAULT_LAYOUTS`
(`generate_dashboards.py`), one of `default` / `toilet` / `garden` /
`utility` / `entrance` / `minimal` / `computer` — stays authoritative
until this is actually built and validated.

### Why change it

`DEFAULT_LAYOUTS` is a fixed grid per named preset: every room using
`default` gets the exact same proportions regardless of whether its
`appliances` slot holds nine devices or one. Growing the slot
vocabulary (five slots today, `computer`'s `infrastructure` slot
added on top) means hand-drawing a new grid for every new combination
that matters. The proposal replaces the *shape* of the grid with a
computation based on what a room actually contains, while
`slot_set` keeps deciding *which* slots are candidates at all (that
part is unchanged — see "Slot sets" earlier in this doc and
`vssp_assign_prepare.py`/`vssp_rooms_apply.py`'s `KNOWN_SLOT_SETS`).

### The algorithm

Terms:
- **default slot** — one of the room's five candidate slots, chosen
  per room (a new field, not yet added to `house.yaml`'s room schema).
  Always rendered, full width, top of the grid, even if empty.
- **secondary slots** — the other candidates. A secondary slot with
  zero assigned devices is **not rendered at all** (no `slot.empty`
  placeholder here — that's the one deliberate behaviour change from
  today's static grids, where an empty-but-in-set slot still shows
  "no device yet").
- **weight** — a secondary slot's device count (`len(slot.entities)`,
  already computed by `normalise_slots()`).

Steps:
1. Reserve the default slot → full-width band, fixed height, on top.
2. Drop every secondary slot with weight 0.
3. Sort the remaining secondaries by weight, descending.
4. Split them into at most two tiers:
   - **Tier A** — the top 2 by weight, sharing a fixed-height block
     (3 grid rows) below the default slot. 1 slot present → it fills
     the block alone; 2 present → split side by side, width
     proportional to weight.
   - **Tier B** — the next 2 by weight (only exists when 3 or 4
     secondaries are present), sharing one row at the bottom, same
     proportional-width rule. 1 slot in tier B → fills the row alone.

| Secondaries present | Tier A | Tier B |
|---|---|---|
| 1 | that slot, full block | — |
| 2 | both, split by weight | — |
| 3 | top 2, split by weight | 3rd, full row |
| 4 | top 2, split by weight | 3rd + 4th, split by weight |

Column-span formula for a tier member on a 12-column content grid:

```
col_span = round(12 × its_weight / tier_total_weight)
```

clamped so no member drops below a readable minimum (exact clamp
value: open question, see below).

### Worked example

A room with `switches` as its default slot, and four secondaries
present: `appliances` (9 devices), `sensors` (3), `security` (2),
`infrastructure` (2).

```
switches — default, full width, row 1
┌──────────────────────────────┬───────────────┐
│ appliances (9)                │ sensors (3)   │   tier A, 3 rows
│ 9/12 cols                     │ 3/12 cols     │
├───────────────────┬───────────┴───────────────┤
│ security (2)       │ infrastructure (2)        │   tier B, 1 row
│ 6/12 cols           │ 6/12 cols                 │
└───────────────────┴────────────────────────────┘
```

### Open questions to settle during tomorrow's simulations

- **Clamp value** for `col_span` — how thin can a tier member get
  before it stops being usable (a minimum column count, or a minimum
  percentage)?
- **Row heights** — are tier A's 3 rows and tier B's 1 row fixed
  pixel/`fr` values, or do they also scale with something?
- **Mobile format** — `room_mobile.yaml.j2` is single-column; does the
  weight-based *ordering* (default first, then secondaries heaviest to
  lightest) carry over there even without the 2-D tiering?
- **`switches`' existing "always full width" rule** — does the new
  default-slot mechanism replace it outright, or can `switches` still
  be forced full-width even when it isn't the chosen default?
- **Ties in weight** — when two secondaries have the same device
  count, what breaks the tie (slot order in `SLOTS`, alphabetical,
  something else)?
- **All-zero room** — a room where every secondary is empty (only the
  default slot has content, or nothing does at all): does the grid
  just shrink to the default band, or does something else fill the
  remaining space?
