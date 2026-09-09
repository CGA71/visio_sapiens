# Visio Sapiens — Scheduling (SWITCHES panel)

**English** · [Français](Scheduler.fr.md)

## Principle

A clock icon on a room's **SWITCHES** panel title opens a popup where you
say:

- "turn this socket off every evening at 22:00"
- "open the shutter on Saturday morning"
- "cut the socket for forty minutes"

Without opening the automation editor, and without leaving the room's
dashboard.

## The three tabs

| Tab | What you enter | Example |
|---|---|---|
| **Recurring** | a time + weekdays | every Monday–Friday at 22:00 |
| **One-off** | a date + a time | 12 September at 18:30 |
| **Countdown** | a number of minutes | in 45 minutes |

## The three actions

| Action | What happens |
|---|---|
| **On** | `homeassistant.turn_on` |
| **Off** | `homeassistant.turn_off` |
| **Pause** | cut, **then switch back on** after N minutes |

`homeassistant.turn_on` / `turn_off` serve the whole panel with no
per-domain branch, because on a cover they mean **open** and **close**. A
light, a socket, a fan and a shutter all go through the same call.

**Pause** is one gesture that schedules two actions. Its resume is not a
countdown running somewhere: it is a second moment, computed and written
down when the rule is saved.

## Where each piece lives

```
the popup           vssp_schedule.html
   │                (the form, no token)
   ▼ webhook vssp_schedule
packages/vssp_schedule.yaml
   │
   ▼ shell_command
vssp/vssp_schedule_apply.py     ← all the date arithmetic lives here
   │
   ▼
www/vssp/schedules.json          the store
   │
   ▼ command_line sensor
sensor.vssp_schedules
   │
   ▼ the "tick" automation, once a minute
homeassistant.turn_on / turn_off
```

### Why a webhook, and not real automations

Creating a genuine Home Assistant automation goes through the
authenticated API. This popup opens from a **room** dashboard, on a wall
tablet: asking someone to paste a long-lived token to schedule a lamp
would be absurd. The webhook needs no token and `local_only: true` keeps
it on the LAN — the same trade `assign.html` and the chatbot already
make.

The price: these rules do not appear in Home Assistant's automation list
and have no individual trace. The only visible automation is the tick.

### Why the tick is so dumb

The Python script reduces **every rule to absolute moments**: a
wall-clock time plus weekdays, or a dated timestamp. The Home Assistant
side then does **no date arithmetic at all**. It wakes once a minute and
compares strings.

What that buys:

- **no timer to lose across a restart.** A restart mid-pause is a
  non-event: the resume moment was written down when the rule was saved
  and is still sitting there.
- **no running script holding a `delay`.** A thirty-minute `delay` does
  not survive a reload; a timestamp in a file does.
- **one source of truth.** The file says everything; nothing can drift
  out of step with it.

The trickiest calculation is done once, in Python, where it can be
tested: the **midnight rollover**. A pause starting at 23:50 for 30
minutes resumes at 00:20 the *next* day, so the resume weekdays are the
start weekdays shifted by one. Get it wrong and a device stays off until
someone notices.

## What the popup shows

**The list of rules in place** for that panel, each with a sentence
rebuilt from the **stored** fields — not from what was typed. What the
list says is therefore what the engine will read.

Each rule carries two buttons: **Suspend** (the rule stays written but no
longer fires) and **Delete**.

A dated rule stays visible for **24 hours** after it ran, greyed and
labelled *done*: reopening the popup to check that last night's rule
fired is exactly what someone does. The daily prune then drops it.
Recurring rules are never pruned.

## Details that matter

**Where the names come from.** The generator hands the popup entity
*ids* — that is all the room model holds. Friendly names are looked up in
`assign_data.json`, the file the ASSIGN wizard already builds. When it is
missing the page prettifies the id (`switch.prise_salon` → "Prise Salon")
rather than showing nothing.

**Which devices are offered.** Those in the panel whose domain is in
`ALLOWED_DOMAINS` — light, switch, cover, fan, media player, input
boolean, climate, humidifier, siren. The template's list is kept in step
with the script's: offering a device the engine will refuse on save is
worse than not offering it. A panel with nothing schedulable gets a plain
title and **no clock**.

**Same-minute collision.** A pause resuming at 22:00 next to a rule
switching the same device on at 22:00: `off` is applied first, `on`
second. The collision therefore resolves in favour of on. That is a
decision, not an accident.

**The engine does not catch up.** A rule whose minute passed during a
restart does not fire late. Catching up would mean deciding how late is
too late to still turn someone's lights on, and nobody wants a 03:00 rule
firing at 07:00 because the pod bounced.

**The store is readable on the LAN.** `schedules.json` lives under
`/config/www` so the popup can read it back with no token, and `/local`
is served **without authentication**. It holds entity ids and times — no
secret — but treat it as readable by anything on the local network,
exactly as `assign_data.json` already is. See
[Security.md](../platform/Security.md).

**`browser_mod` is required** (HACS), as for every popup in this project.
Registering the browser is **not** required — that was the first wrong
guess when the popup would not open.

**The tap uses `fire-dom-event`, never `perform-action`,** and that is the
whole difference between a popup and nothing at all. `browser_id: this`
can only be resolved by the *frontend*: "this browser" is a fact the
backend cannot know. A `perform-action` tap sends a plain service call
over the WebSocket, the backend receives the literal string `"this"`, and
nothing happens — while the call reports success, which is exactly why
such a mistake goes unnoticed. `fire-dom-event` raises the `ll-custom`
event browser_mod's own frontend listens for; it substitutes its own
browser id and takes it from there, so no `browser_id` key is needed at
all.

This was found by spying on the outgoing service call: the payload left
the card perfectly formed and no dialog ever appeared. The ADMIN
chatbot's "custom provider" tile carried the same defect from the day it
was written and has been fixed alongside.

## Related

- [Dashboard_Generator.md](Dashboard_Generator.md) — the generator, slots
  and locales
- [Updates.md](Updates.md) — the other screen that schedules something,
  and why it goes about it differently
