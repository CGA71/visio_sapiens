# Visio Sapiens — Backup retention

**English** · [Français](Backup_Retention.fr.md)

## Why this exists

Several actions in this project write a timestamped backup before
overwriting something, on the principle that nothing destructive should
be a one-way trip:

| What creates the backup | Where it writes | Format |
|---|---|---|
| `shell_command.vssp_backup_dashboard` (HOME) | `/config/vssp/backups/` | `home_<YYYYMMDD>_<HHMMSS>.yaml` |
| `shell_command.vssp_backup_energy` | `/config/vssp/backups/` | `energy_<YYYYMMDD>_<HHMMSS>.yaml` |
| REGENERATE CORE (`vssp_admin_config.yaml`) | `/config/vssp/backups/` | `core_<YYYYMMDD>_<HHMMSS>.yaml` |
| `shell_command.vssp_backup_theme` (`packages/vssp_theme.yaml`) | `/config/vssp/backups/` | `theme_<YYYYMMDD>_<HHMMSS>.yaml` |
| `vssp_assign_apply.py`, before writing `house.yaml` | `dashboards/model/backups/` | `house_<YYYYMMDD>_<HHMMSS>.yaml` |
| `vssp_rooms_apply.py`, before writing `house.yaml` | `dashboards/model/backups/` | `house_<YYYYMMDD>_<HHMMSS>.yaml` |
| `vssp_theme_apply.py`, before writing `design_system.yaml` | `dashboards/model/backups/` | `design_system_<YYYYMMDD>_<HHMMSS>.yaml` |

None of them ever deleted an old one. Found on the first real instance
this was checked against: **62 files** in `/config/vssp/backups/`
going back three weeks, more than half of them written within a few
minutes of each other during a single testing session. Left alone,
this grows without bound.

## How rotation works

**`vssp/vssp_prune_backups.py`** groups the files in a directory by
prefix (the part before `_<YYYYMMDD>_<HHMMSS>.yaml` — `home`,
`energy`, `core`, `theme`, `house`, `design_system`, ...) and keeps
only the `--keep` most recent per prefix (default 5), sorted by file
modification time. A file that does not match that naming convention
is reported and left untouched — never guessed at or swept up by
accident.

**`home-assistant/packages/vssp_maintenance.yaml`** runs it once a day
(`04:45`, fifteen minutes after the existing ENERGY daily safety net in
`vssp_energy_totaux.yaml`, to avoid piling shell_command load on the
same minute) against both backup directories:

```
shell_command.vssp_prune_backups
  --dir /config/vssp/backups
  --dir /config/dashboards/model/backups
  --keep 5
```

No `persistent_notification` — same restraint as the ENERGY daily
sync: routine housekeeping that succeeds every day is not worth an
alert forever. The result of the last run is always readable at
`/local/vssp/prune_status.json` (per-directory, per-prefix breakdown
of what was kept and what was deleted).

## Running it by hand

```bash
# see what would be deleted, delete nothing
python3 vssp/vssp_prune_backups.py --dir /config/vssp/backups --keep 5 --dry-run

# actually prune
python3 vssp/vssp_prune_backups.py \
  --dir /config/vssp/backups \
  --dir /config/dashboards/model/backups \
  --keep 5
```

To change how many backups are kept, edit the `--keep` value in
`vssp_maintenance.yaml`'s `vssp_prune_backups` shell_command — there is
no ADMIN console control for it (it did not seem worth a UI toggle for
a number that is set once and rarely revisited).

## What this does NOT touch

- **`/config/backups`** — Home Assistant's own native snapshot system
  (`ha backups new`, used by `deploy:production` before every release).
  A completely different mechanism; this package has no opinion on its
  retention.
- **`home-assistant_v2.db`** — the live recorder database.
