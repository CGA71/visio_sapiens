# Visio Sapiens — Security

**English** · [Français](Security.fr.md)

## Current state (honest assessment)

Access control today is minimal, and this document exists to say so
plainly rather than let it go unstated:

- The ADMIN console and every dashboard rely entirely on **Home
  Assistant's own authentication** (whoever is logged into the HA
  frontend can open `/visio-sapiens-admin`). There is no
  Visio-Sapiens-specific login screen.
- The only dedicated access gate today is the **DELETE DASHBOARD**
  button: `input_text.vssp_admin_pin` (the reference code, set once via
  the one-shot `vssp_set_admin_pin` script) compared against
  `input_text.vssp_pin_entry` (what the user types) — see
  `vssp_admin_config.yaml` and `docs/Troubleshooting.md`. It protects
  one destructive action, not the console itself.
- Every webhook this project adds (ASSIGN, ROOMS, THEME) is
  `local_only: true` — a network-level restriction, not an identity
  check. Anyone on the LAN who knows (or guesses) the webhook id can
  call it.
- The **MCP server** (`addons/vssp-mcp`, `kubernetes/mcp`) listens on
  port 8099 and, unlike everything above, does **not** sit behind Home
  Assistant's authentication: it is its own HTTP service. Its own
  `api_token` option is the only gate, it is empty by default, and the
  server prints a warning at every start when it is. Left empty, that
  port is an unauthenticated read of every entity state in the house —
  the tools are read-only, but reading is exactly what leaks. Set it.
  See [MCP_Server](MCP_Server.md).

None of this is a login system. This is the gap the design below is
meant to close.

## Planned: face recognition + 6-digit code (not yet implemented)

**Context that shapes the design**: this project is used exclusively
from a tablet or a phone — both devices share one relevant feature, a
front-facing camera. That is what makes face recognition viable as a
gate here, without adding hardware.

**The intended flow**, as specified by the project owner:

1. **Face recognition** via the device's front camera identifies the
   person.
2. **A 6-digit code** is required in addition to the face match —
   two factors, not one, before Visio Sapiens grants usage rights
   (i.e. unlocks the interface for normal use).
3. Separately, **one unique master security code** exists to unlock
   everything — a single override, distinct from the per-user 6-digit
   code above.

## Open design questions

Recorded here so the next implementation pass starts from a decision
list, not a blank page:

- **Where does face matching actually run?** Two very different paths:
  - the device's own biometric API (e.g. WebAuthn platform
    authenticator, Face ID / Android biometric prompt exposed to the
    browser) — no image ever leaves the device, but ties the check to
    "this specific enrolled device/user," not literally to a face
    Visio Sapiens compares on its own;
  - a captured photo compared against a reference by a recognition
    model — works across devices, but means deciding where the model
    runs (locally on the HA pod vs. an external service) and where the
    reference photo is stored.
- **Is the 6-digit code per person or shared?** The current
  `vssp_admin_pin` model is a single shared secret. A per-user code
  implies a small user registry that does not exist yet.
- **What exactly does the master code unlock?** Candidates: bypass
  face+code entirely for that session, grant one-time admin rights, or
  disable the lock altogether until re-armed. These have very
  different blast radii and probably need different confirmation
  flows (compare with the existing DELETE DASHBOARD confirmation
  pattern).
- **Where is this gate enforced?** At the ADMIN console entry point
  only, or on every dashboard (HOME, room dashboards, ENERGY too)?
  The iframe + webhook pattern used by ASSIGN/ROOMS/THEME
  (`local_only: true`, no bearer token in the browser — see
  `docs/Design_System_Editor.md`) is the closest existing precedent
  for "check something server-side without trusting the browser," and
  whatever this becomes should follow it rather than inventing a new
  trust model.
- **Failure handling**: what happens when face recognition fails
  repeatedly (lighting, camera angle) — a fallback to code-only after
  N attempts, or a hard lockout? An unattended lockout on the one
  device used to control the home is its own outage.

This section will be replaced by an implementation write-up (model,
data flow, package/script names) once these are settled — the shape
already used for THEME (`docs/Design_System_Editor.md`) is the
template to follow: a plain document of the pipeline, not just a list
of intentions.
