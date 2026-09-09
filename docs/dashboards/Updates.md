# Visio Sapiens — Updates (ADMIN, UPDATES screen)

**English** · [Français](Updates.fr.md)

## Principle

Home Assistant already knows about every pending update. Each one is an
`update.*` entity carrying `installed_version`, `latest_version`, its
release notes, and an install service. Settings → Updates lists them —
but only there, and mixed in with everything else that screen does.

The UPDATES screen adds **no data source at all**. It reads the entities
that already exist and adds the one thing a dashboard cannot work out on
its own: the **split into three families**.

| Family | What it is | How it is installed |
|---|---|---|
| **System** | Home Assistant itself, the Supervisor, the OS, add-ons | one row at a time |
| **Integrations & cards** | everything installed through HACS | one row at a time, **or all at once** |
| **Device firmware** | `device_class: firmware` — a physical device | one row at a time, never in bulk |

That split is the whole point of the screen. Settings → Updates shows a
Lovelace card download and the flash of a wall plug as the same kind of
line; they are not the same kind of risk, and that is the one distinction
that decides whether you click without thinking or read the release notes
first.

## Where each piece lives

```
update.* entities (Home Assistant, already there)
        │
        ▼
packages/vssp_updates.yaml       4 sensors — a count and an entity list
        │                        per family + one grand total
        ▼
templates_j2/admin.yaml.j2       the UPDATES screen renders those lists
```

The classification happens **in the package, not in the dashboard**.
Working out that `update.browser_mod_update` belongs to HACS requires
`integration_entities()`, a template function that exists on the Python
side only — a Lovelace card has no equivalent. So the sensors publish
each family as an `entity_ids` attribute, and the cards render the list
they are handed.

The system family is defined by **subtraction**: anything that is neither
HACS nor firmware. That is why the same file is right on this k3s
instance (where it catches the NAS) and on a HAOS production instance
(where it catches Core and the add-ons), with no edit.

### Entities created

| Entity | State | Attribute |
|---|---|---|
| `sensor.vssp_updates_pending` | total pending | `entity_ids` |
| `sensor.vssp_updates_system` | pending, system | `entity_ids` |
| `sensor.vssp_updates_hacs` | pending, HACS | `entity_ids` |
| `sensor.vssp_updates_firmware` | pending, firmware | `entity_ids` |
| `script.vssp_updates_check` | — | re-poll every update entity |
| `script.vssp_updates_install_hacs` | — | install every pending HACS update |

An update that has been **skipped** does not count, and that needs no
filter: Home Assistant reports such an entity as `off` for as long as the
skipped version is the latest one. Skipping from a row therefore empties
this screen exactly the way installing does.

## The screen

**UPDATE STATE** — the four counts, at a glance.

**TO INSTALL** — the inventory: every pending update, grouped by family,
with the two versions it sits between (`v3.2.2 → v3.2.3`). This is what
you read before deciding. A family with nothing pending shows an em dash.

**One card per family** — the actionable rows, and each card is absent
when its family is empty, so a fully up-to-date instance shows a screen
with nothing on it but the state and the maintenance controls.

Tapping a row opens **Home Assistant's own update dialog**: release
notes, the backup checkbox where the entity supports one, Install, and
Skip. That dialog is better than anything this console could rebuild, so
the console does not rebuild it.

**MAINTENANCE** — two buttons:

- **CHECK NOW** — integrations poll on their own schedule (HACS roughly
  hourly), so an empty screen means *nothing found last time we asked*.
  This button turns that into *nothing found just now*.
- **INSTALL EVERY INTEGRATION & CARD** — the one bulk install offered.

### Why the bulk install stops at HACS

Not a limitation — a decision.

A HACS update downloads files and is undone by reinstalling the previous
version from HACS. A Core or add-on update is not, and wants the backup
checkbox its own dialog offers — which a bulk call cannot tick, since
`update.install` refuses `backup: true` on any entity that does not
advertise BACKUP support, and would fail the whole call for a mixed list.
A firmware flash is undone by nothing at all.

So: HACS in bulk, everything else from its own row.

After a bulk HACS install a notification asks for a hard refresh
(Ctrl+Shift+R). A Lovelace card replaced on disk is still the old file in
this browser's cache, Home Assistant does not say so, and the symptom — a
card that keeps behaving like the version you just replaced — reads as a
failed update rather than a stale tab.

## Implementation notes

**No iframe, no token.** Unlike ROOMS & FLOORS, DETECTED DEVICES or the
SAFE, this screen is entirely native cards. An update is an `update.*`
entity, so native cards reach all of it, and the native more-info dialog
does the acting.

**`custom:config-template-card` builds the rows.** An `entities` card
cannot filter: its list is fixed in YAML written months before the update
existed. config-template-card evaluates a value that starts with `${` and
assigns whatever comes back — an array included — so the list is read
from the sensor at render time. It re-renders when an entity in its own
`entities:` changes, hence the family sensor listed there, whose count
moves the moment an install finishes.

Inside that expression the state map is called **`states`**; there is no
`hass`. The `&& … || []` guard is not superstition: the sensor does not
exist for the few seconds between a restart and the first template pass,
and an entities card handed `undefined` throws rather than rendering
empty.

**The conditions spell out `unavailable` and `unknown` one by one.**
`state_not: "0"` alone is true for both, so on a half-started instance
the card would appear, ask the sensor for a list, and get nothing.

**Two template engines on the markdown card.** The three family labels
are translated by the *generator*; the loop under them is executed by
*Home Assistant*. The boundary falls between them, so the set-tag is
emitted as text — `{{ '{%' }}` is an expression the generator evaluates
into two characters Home Assistant later reads as the start of a tag. An
expression is also immune to `lstrip_blocks`, which strips the
indentation in front of a *block* tag — the trap a raw block on that line
would have walked straight into, landing the template at column zero and
breaking the YAML. See [Troubleshooting.md](../ci-cd/Troubleshooting.md)
for the version of that mistake that shipped once already.

## Related

- [Dashboard_Generator.md](Dashboard_Generator.md) — the generator, slots
  and locales
- [Backup_Retention.md](../platform/Backup_Retention.md) — what a backup
  before a Core update actually retains
