# Visio Sapiens — YouTube series plan

**English** · [Français](YouTube_Series.fr.md)

This document maps the project's documentation to a sequence of videos. Each
episode has one source doc (after the `docs/` consolidation), one central
question it answers, and a suggested on-screen demo. Episodes are ordered so
each one builds on what the previous one showed — but 2 through 7 can be
filmed out of order if a topic is more urgent or more visually ready.

Source docs referenced below are the **consolidated** names (see
`Manifest.md` for the old → new mapping during the transition).

---

## At a glance

| # | Title | Source doc | Central question | On-screen anchor |
|---|---|---|---|---|
| 1 | Vision & architecture | `Vision.md` | Why replace Lovelace's native cards with a custom engine? | Architecture diagram + a HOME dashboard walkthrough |
| 2 | CORE — the system dashboard | `Core_Dashboard.md` | How does a static HTML page turn Glances metrics into live gauges? | `core.html` live, DevTools network tab open |
| 3 | The dashboard generator | `Dashboard_Generator.md` | Why generate YAML from a model instead of hand-editing it? | `model/house.yaml` → regenerate → diff in the browser |
| 4 | Case study: wiring up a whole room | `Integration_Case_Study.md` | What does "add one feature end to end" actually take? | Technical Room dashboard, before/after |
| 5 | Case study: the device assignment wizard | `Device_Assignment_Wizard.md` | How do you turn a raw entity scan into a safe, reviewable form? | The assign.html iframe, live scan → assign → apply |
| 6 | The CI/CD pipeline | `CI_CD.md` | How does one commit reach two very different targets (k3s staging, HAOS production)? | GitLab pipeline graph, a live run |
| 7 | Debugging sessions | `Troubleshooting.md` | What does it actually look like to chase a bug that "shouldn't be possible"? | Terminal + browser DevTools, real postmortems |

---

## Episode 1 — Vision & architecture

**Goal:** give viewers the mental model before any code. What Visio Sapiens
*is* (an OS-like control-center UI layered on top of Home Assistant, not a
themed dashboard), and why the project refuses native Lovelace cards except
for a documented shortlist (`weather-forecast`, `logbook`, `apexcharts-card`).

**Show on screen:**
- The architecture diagram from `Vision.md` (CORE / Room Engine / IA Layer /
  Animation Engine / CSS Engine / JS Engine / Theme Engine).
- A live tour of the HOME dashboard, pointing at concrete pieces: the sidebar,
  the HUD header row (weather, clock, alarm status, avatar), the energy row.
- The repo tree, mapped live to what's on screen (`www/vssp/css/vssp.css` is
  literally what's painting this).

**Talking points:**
- The one rule that drives every other decision: "Home Assistant is a data
  engine now; the UI is entirely driven by VSSP."
- The naming migration (OSVision → VSSP) as a case study in how a project's
  history leaves traces — useful framing for why some file names still won't
  match until later episodes fix them.
- The changelog section of `Vision.md` is a ready-made "here's everything
  that's shipped" montage list — good for a fast-cut opening or closing
  summary.

**Don't film yet:** anything that depends on live secrets (Livebox
password, long-lived tokens) — save credential handling for episode 4/6.

---

## Episode 2 — CORE, the system dashboard

**Goal:** one page, end to end — from `psutil` on the host to an SVG gauge in
the browser — as a single, followable data path.

**Show on screen:**
- The chain diagram from `Core_Dashboard.md` (Glances → HA integration →
  `core.html`), redrawn or reused directly.
- DevTools Network tab open while `core.html` polls: viewers see the actual
  `GET /api/states` call and the 30-second interval in real time.
- The `findEntity()` fuzzy-matching function — a good "here's a subtle design
  decision" beat: why no hardcoded `entity_id`, and the cost (a renamed
  entity silently breaks a gauge).

**Talking points:**
- The two independent polling loops (Glances→HA at 60s, page→HA at 30s) and
  why that caps "real time" at ~90 seconds — a good place to invite viewer
  questions about trade-offs.
- The still-open K3s path bug (`/local/osvision_v2/...` 404) as a live fix:
  find it, explain why the `catch` swallows it silently, patch the one line,
  redeploy, show the K3s panel come alive.
- `esc()` and the XSS angle — a 90-second aside on why you escape data from
  your *own* backend, not just "untrusted" input.

**Good pairing:** this episode's live bug fix is a light version of what
episode 7 does at length — consider cross-linking.

---

## Episode 3 — The dashboard generator

**Goal:** explain the model → template → generated-YAML pipeline that
replaced hand-edited dashboards — and connect it to the ROOMS & FLOORS wizard
work, which is the freshest, most demoable material in the whole project.

**Show on screen:**
- `model/house.yaml` open next to `templates_j2/energy.yaml.j2`, with one
  value changed live (add a device) and the generator re-run.
- The preview mode (`--preview`) generating an isolated
  `energy_preview.yaml` at its own `url_path` — a good demonstration of "safe
  to break" tooling.
- The ROOMS & FLOORS admin screen (language/format row + live iframe) as the
  newest, most polished expression of this same idea — a natural bridge from
  "here's the engine" to "here's what it looks like when it's finished."

**Talking points:**
- Why Lovelace can't loop over a list of entities, and how that forces the
  ENERGY dashboard's two-speed design (live scan totals vs. generated
  per-device rows).
- `vssp_energy_sync.py`'s non-destructive merge rules (new device appended,
  known device preserved, missing device flagged not deleted, `keep: true`
  as an escape hatch) — good material for "here's how you avoid a script
  eating someone's manual customization."
- The still-open bridge (`vssp_model_sync.py`, wizard → model) as a "coming
  in a future episode" hook.

---

## Episode 4 — Case study: wiring up a whole room

**Goal:** show that "add a feature end to end" is a repeatable checklist, not
a one-off improvisation — using the Technical Room integration as the worked
example.

**Show on screen:**
- The file table from `Integration_Case_Study.md`: dashboard views, HA
  package, LAN probe script, secret handling — each one opened briefly.
- The secret-handling pattern for `LIVEBOX_PASSWORD`: masked CI/CD variable,
  passed as a positional shell argument (never on a visible command line),
  written with `umask 077`. This is genuinely instructive content, not
  project-specific trivia — frame it that way.
- The two still-open arbitrations (the `_energie` vs `_energie_jour`
  ambiguity, the missing `technical.png`) as an honest "here's what we
  haven't decided yet" beat — good for authenticity.

**Talking points:**
- Why the CI/CD `Protected` flag on a variable is a trap for staging
  deployments from unprotected branches — a concrete, transferable GitLab
  lesson.
- The navigation trick: the Technical Room links already existed as dead
  links elsewhere in the UI, so integrating it made existing links work
  rather than adding new ones.

---

## Episode 5 — Case study: the device assignment wizard

**Goal:** a second, contrasting case study — an interactive tool instead of a
static dashboard, and a good moment to show the whole discover → decide →
apply shape that recurs across the project (it's the same shape as the
ROOMS & FLOORS wizard from this session).

**Show on screen:**
- The pipeline from `Device_Assignment_Wizard.md`:
  `DISCOVERY SCAN → report.json → prepare → assign_data.json → the form →
  webhook → apply → house.yaml → the generator → dashboards/views/`.
- A live scan → assignment → apply cycle in the browser.
- The MD5-checked file table as a "how we made sure the right files shipped"
  beat — pairs well with episode 7's caching postmortem.

**Talking points:**
- "Nothing is ever half-written": the applier validates the whole payload
  before touching `house.yaml`, and backs it up first — a good discussion of
  atomicity in a system with no real transactions.
- Re-running a scan doesn't reset prior work — a subtle but important
  guarantee to call out explicitly, since it's exactly the kind of thing that
  looks unremarkable when it works and catastrophic when it doesn't.

---

## Episode 6 — The CI/CD pipeline

**Goal:** one commit, two very different deployment targets — the dual-target
pipeline as its own subject, independent of any one feature.

**Show on screen:**
- The pipeline diagram: MR/master → build → `deploy:staging` (k3s, `kubectl
  cp`) vs. tag → `deploy:production` (HAOS, SSH) with a manual gate.
- A live GitLab pipeline run, stage by stage.
- One of the G1–G5 open gaps, fixed live (G1, the CSS/JS URL mismatch, is the
  most visual: a 404'd stylesheet turning into a styled page on screen).

**Talking points:**
- The `workflow:` rule as "the number one diagnostic reflex" — a push to a
  feature branch without an open MR launches *nothing*, which is the kind of
  thing that wastes an hour if you don't know to check it first.
- Why `configuration.yaml` needing a full HA restart (not a hot reload) was
  the root cause of an entire "staging looks unchanged" class of bugs — ties
  directly into episode 7.
- Secrets never touch a command line or a log: positional shell arguments in
  staging, stdin in production. Worth a full explanation, it's reusable
  knowledge outside this project entirely.

**Optional split:** if 6 runs long, cut it into 6a (pipeline mechanics) and
6b (the G1–G5 open gaps as a "known issues" episode) — the source doc
already separates cleanly along that line.

---

## Episode 7 — Debugging sessions

**Goal:** the "detective story" episode. Real bugs, real symptoms, real
commands run to narrow down the cause — the format that tends to perform
best because the payoff (the fix) is earned on screen instead of assumed.

**Show on screen, as three (or four) independent mini-cases from
`Troubleshooting.md`:**
1. **Staging looks unchanged after a green pipeline** — the `deploy:staging`
   job never restarted Home Assistant, so `lovelace.dashboards` and
   `homeassistant.packages` kept serving stale config even though the files
   on disk were correct. Fixed by adding the restart + readiness wait.
2. **`OSV_PREFIX` silently dropping every dashboard** — `"visio-sapiens"
   .startswith("vssp")` is `False`, so the patcher wrote nothing, while
   `resources` (unfiltered) updated fine — a classic "half the deploy worked,
   which made it harder to notice" bug.
3. **Energy tables empty after a sync that claimed success** — an empty
   long-lived token produced a silent 401, and `continue_on_error: true`
   let the generator run anyway on an empty model, overwriting a working
   dashboard with a blank one.
4. **Bonus, from this project's own session logs:** the ROOMS & FLOORS
   wizard staying in French despite the language selector reading `en` —
   traced to a missing cache-busting `?v=` token on one specific iframe URL,
   the one asset in the whole pipeline that wasn't covered by the existing
   cache-busting `sed` step. A good closing case because it shows that even
   a mature pipeline can have exactly one uncovered corner, and that "it's
   probably cached" is worth checking before assuming a deploy failed.

**Talking points:**
- Each case follows the same shape: symptom → wrong first guess → the
  command that actually narrows it down → root cause → fix → the guard rail
  added afterward so it can't silently recur. Naming that shape explicitly
  makes the format replicable for future videos on new bugs.
- The "green pipeline, unchanged result" pattern is worth naming as its own
  concept — it recurs across cases 1, 2, and 4 in different disguises.

---

## Sequencing notes

- **1 → 3 → 5** is the natural "here's the wizard flow, start to finish"
  thread — filmable as a mini-arc even if the other episodes ship later.
- **2, 4, 6, 7** are each self-contained and can be reordered based on what's
  visually ready or what a bug report makes topical that week.
- Episode 7 benefits from being filmed *last* chronologically per bug (i.e.,
  after the fix is deployed and confirmed), but can be *released* earlier if
  a case is already fully resolved and documented, as three of the four
  currently are.
- `Vision.md`'s three source stubs (`vision.md`, `design-system.md`,
  `modules.md`) were empty before this consolidation — if a future episode
  wants a dedicated deep dive on the CSS design system specifically, that
  content doesn't exist yet and would need to be written first.
