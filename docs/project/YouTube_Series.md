# Visio Sapiens — YouTube series plan

**English** · [Français](YouTube_Series.fr.md)

This document maps the project's documentation to a sequence of videos. Each
episode has one source doc (after the `docs/` consolidation), one central
question it answers, and a suggested on-screen demo. Episodes are ordered so
each one builds on what the previous one showed — but 2 through 12 can be
filmed out of order if a topic is more urgent or more visually ready.

Source docs referenced below are the **consolidated** names, and every
one of them exists in `docs/` in both languages (`X.md` / `X.fr.md`).
Episodes 8 to 12 cover the documents written after the first pass of this
plan; they are the newest material and, for that reason, the most
demoable.

---

## At a glance

| # | Title | Source doc | Central question | On-screen anchor |
|---|---|---|---|---|
| 1 | Vision & architecture | `Vision.md` | Why replace Lovelace's native cards with a custom engine? | Architecture diagram + a HOME dashboard walkthrough |
| 2 | CORE — the system dashboard | `Core_Dashboard.md` | How does a static HTML page turn Glances metrics into live gauges? | `core.html` live, DevTools network tab open |
| 3 | The dashboard generator | `Dashboard_Generator.md` | Why generate YAML from a model instead of hand-editing it? | `model/house.yaml` → regenerate → diff in the browser |
| 4 | Case study: wiring up a whole room | `Integration_Case_Study.md` | What does "add one feature end to end" actually take? | Technical Room dashboard, before/after |
| 5 | Case study: the device assignment wizard | `Deployment.md` | How do you turn a raw entity scan into a safe, reviewable form? | The assign.html iframe, live scan → assign → apply |
| 6 | The CI/CD pipeline | `CI_CD.md` | How does one commit reach two very different targets (k3s staging, HAOS production)? | GitLab pipeline graph, a live run |
| 7 | Debugging sessions | `Troubleshooting.md` | What does it actually look like to chase a bug that "shouldn't be possible"? | Terminal + browser DevTools, real postmortems |
| 8 | Automating an OAuth setup | `Google_Calendar.md` | How much of a third-party OAuth setup can you automate — and where does it stop? | The CALENDAR screen: paste a client ID, land on Google's consent page |
| 9 | A chatbot inside the dashboard | `Chatbot_Integration.md` | How do you plug four different LLM providers behind one card without a backend? | The HOME chatbot bar answering inline, provider switched live in ADMIN |
| 10 | The design system editor | `Design_System_Editor.md` | How do you make a visual charter editable without letting anyone break the UI? | THEME screen: change a color, regenerate, watch the whole UI follow |
| 11 | Bilingual by construction | `Google_Calendar.md` (Interface language) + `locales/` | What does it take for a generated interface to hold **one** language on **one** screen? | The same screen in EN and FR, side by side — and the version that mixed both |
| 12 | Backups, retention, and an honest security review | `Backup_Retention.md` + `Security.md` | What do you owe a user before you overwrite their file — and what do you owe them about what isn't secured? | A backup written live, then the real threat model, stated plainly |

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
- The pipeline from `Deployment.md`:
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

## Episode 8 — Automating an OAuth setup

**Goal:** take a setup that Home Assistant documents as a nine-step manual
walk through *Settings > Devices & services* and show it collapsing into one
form — then stop honestly at the one step that cannot collapse.

**Show on screen:**
- The two paths side by side: the native path (Application credentials → Add
  integration → Google Calendar → consent → pick calendar) against the
  CALENDAR screen (paste two values → one button → consent → pick calendar).
- The websocket detour, live in a terminal: `application_credentials` has
  **no** REST endpoint, so `vssp_google_setup.py` speaks ~90 lines of RFC
  6455 by hand rather than adding a dependency to the pod. Show the frames.
- The consent click itself, on Google's own page — filmed rather than
  hidden, because it's the point.

**Talking points:**
- "Automate everything around the thing you cannot automate" is a
  transferable design rule, and OAuth is the clearest possible example: the
  consent screen exists *precisely* so that no script can sign for the
  account owner. Naming that out loud is more useful than pretending the
  automation is total.
- The un-editable credential (`UPDATE_FIELDS = {}`): fixing a typo doesn't
  correct a credential, it adds a second one, and from then on the config
  flow asks which implementation to use. A great "the API's constraint
  changed my design" beat — the script answers with the id it just
  registered, not the first in the list.
- Secret handling once more, now as a recognisable project pattern rather
  than a one-off: the client secret is written to a 0600 file and never
  reaches a command line, exactly like `vssp_ha_token` and the chatbot keys.

**Good pairing:** episode 11 uses this same screen as its worked example —
film them back to back while the material is fresh.

---

## Episode 9 — A chatbot inside the dashboard

**Goal:** four LLM providers (Gemini, Claude, ChatGPT, plus a custom
endpoint) behind a single card, with no backend service of the project's
own — and the constraints that shape such a thing.

**Show on screen:**
- The HOME chatbot bar answering inline, then the ADMIN provider selector
  switched live and the same question asked again.
- The key storage path: each provider's key into its own protected file,
  same convention as everywhere else.
- The custom-provider form — the moment the feature stops being "three
  hardcoded vendors" and becomes an interface.

**Talking points:**
- Why the reply comes back *inline* rather than in a popup, and what that
  changed in the card's design.
- The shadow-DOM gotcha that any `button-card` custom_fields work runs
  into: the HTML lives in a shadow root, so `document.getElementById` finds
  nothing and the handler has to be passed `this` instead. Short, concrete,
  and it will save a viewer an evening.

---

## Episode 10 — The design system editor

**Goal:** a visual charter that used to be one hand-edited theme file,
turned into a model plus a generator plus an editing screen — the same
model→template→generated shape as episode 3, applied to appearance instead
of structure.

**Show on screen:**
- `model/design_system.yaml` next to the generated theme, one color changed
  live, regenerate, and the whole interface following.
- The reset-to-default path (`design_system.default.yaml`), which is what
  makes experimenting safe enough to do on camera.
- A live CSS trap worth its own beat: `color-mix()` is parsed but silently
  drops borders on this renderer, so the project computes `rgba()` values
  ahead of time instead. "It's valid CSS and it still doesn't work" is a
  good, honest lesson.

**Talking points:**
- Where the line sits between "themable" and "breakable", and why a default
  model in the repo is the guard rail that lets the editor stay permissive.
- The design tokens as a contract between the generator and the CSS — the
  reason a single value can move the entire UI.

---

## Episode 11 — Bilingual by construction

**Goal:** the episode about a problem most projects discover far too late —
an interface in two languages is not a translation task, it's an
architecture constraint. Worked entirely on the CALENDAR screen, which is
the case that made it obvious.

**Show on screen:**
- **The bug first**, because it is instantly legible on camera: one screen
  showing translated labels around a form hardcoded in the other language,
  with `not_configured` sitting under a translated caption for good measure.
- The three sources of language that met on that one screen, each of which
  had been decided independently: the generated labels (`t()` +
  `locales/<code>.yaml`), the embedded form (its own hardcoded strings), and
  the Python script's status sentences.
- The fix, live: `?lang=` carried into the iframe from the generated locale,
  an `I18N` table in the page, `--locale` passed to the script — then the
  same screen rendered EN and FR side by side.
- The status file as the interesting artifact: it publishes `state`
  (untranslated machine token), `state_label` (translated), and
  `message_key` + `message_vars` **next to** the rendered `message`.

**Talking points:**
- The rule that falls out of it: **translate at the last possible moment,
  and never translate what a machine reads.** A status token you branch on
  and a sentence a human reads are two different values that happen to look
  alike — the whole bug is treating them as one.
- Why `unit_of_measurement: "calendriers"` could not be saved by any amount
  of care: it isn't templatable, so the only correct move was to delete it
  and let the translated row label carry the meaning. Knowing which knobs
  *cannot* be localised is half the work.
- The consequence users feel: changing the language requires a regeneration,
  because the language is baked in at generate time. That's a deliberate
  trade — and worth defending on camera rather than glossing over.

**Good pairing:** episode 7's fourth case (a wizard stuck in French because
one iframe URL lacked a cache-buster) is the same screen's earlier
mistranslation, from a completely different cause. Shown together they make
the point that "wrong language on screen" is a symptom, not a diagnosis.

---

## Episode 12 — Backups, retention, and an honest security review

**Goal:** two short subjects that belong together because both are about
what you owe the person on the other side of the software.

**Show on screen:**
- A destructive action taken live — regenerate HOME — with the timestamped
  backup written first, then restored from.
- The retention rules: what is kept, for how long, and why the answer is a
  policy rather than an accident.
- `Security.md` opened and read on camera, including the parts that say what
  is *not* protected today.

**Talking points:**
- "Nothing is ever half-written" as a project-wide invariant, and the three
  independent places it shows up (the assignment applier, the generator's
  protected dashboards, the backup step).
- Why publishing an honest limitations section is a feature: it is the
  difference between a project that has a threat model and one that has a
  vibe. This is the episode that will age best.
- A natural closing beat for the series as a whole, if you want one.

---

## Action plan — what to film next

Status is about **shootability**, not about whether the feature works: a row
is only "ready" when the documentation and a demo that survives a take both
exist today.

| # | Episode | Source doc | Demo readiness | Next concrete step |
|---|---|---|---|---|
| 8 | Automating an OAuth setup | `Google_Calendar.md` ✔ | **Ready** — screen shipped, doc complete in both languages | Record a clean Google Cloud project from scratch so the consent page is filmable without cutting |
| 11 | Bilingual by construction | `Google_Calendar.md` + `locales/` ✔ | **Ready** — and the before/after exists in git history | Capture the two screenshots (EN/FR) and the pre-fix commit before the material ages out |
| 1 | Vision & architecture | `Vision.md` ✔ | Ready | Re-shoot the architecture diagram at recording resolution |
| 3 | The dashboard generator | `Dashboard_Generator.md` ✔ | Ready | Pick the one live model change to demo (adding a device reads best) |
| 10 | The design system editor | `Design_System_Editor.md` ✔ | Ready | Decide whether the `color-mix()` trap is a beat here or its own short |
| 9 | A chatbot inside the dashboard | `Chatbot_Integration.md` ✔ | Ready, with one caveat | Confirm which provider keys can be on camera; blur or use a throwaway key |
| 2 | CORE — the system dashboard | `Core_Dashboard.md` ✔ | Blocked on a fix | The K3s `/local/osvision_v2/…` 404 is the live fix — verify it still reproduces before filming |
| 5 | The device assignment wizard | `Deployment.md` ✔ | Ready | Source doc was renamed; re-read it end to end before scripting |
| 4 | Wiring up a whole room | `Integration_Case_Study.md` ✔ | Partly blocked | Two arbitrations still open (`_energie` vs `_energie_jour`, missing `technical.png`) — decide, or film them as open questions |
| 6 | The CI/CD pipeline | `CI_CD.md` ✔ | Ready | Choose which of G1–G5 gets fixed on camera (G1 is the most visual) |
| 12 | Backups + security | `Backup_Retention.md` + `Security.md` ✔ | Ready | Confirm `Security.md` still matches reality on the day of filming — it is the one doc that goes stale silently |
| 7 | Debugging sessions | `Troubleshooting.md` ✔ | Ready, best filmed last | Add the FR/EN mix as a fifth case once episode 11 has shipped |

Two standing rules for this plan:

1. **A doc is written before its episode, never after.** Every episode above
   has its source doc in `docs/`, in both languages — that is what makes the
   scripting step short.
2. **When a screen changes, its episode's status resets.** The CALENDAR
   screen shipped and was then reworked for language within days; anything
   filmed in between would already be wrong.

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
  content doesn't exist yet and would need to be written first. Episode 10
  now covers part of that ground from the editor's side.
- **8 → 11** is the strongest new pair: the same screen, first as a feature
  and then as a language problem. Film them in that order and in one
  session — episode 11's before/after only exists while the pre-fix version
  is still recent in the history.
- **9, 10, 12** are self-contained like 2, 4, 6 and 7, and can be slotted
  wherever a week needs an episode.
- The ADMIN console now has enough screens (ROOMS & FLOORS, ASSIGN, ENERGY,
  CALENDAR, THEME, GENERATION) that a short "tour of the console" cut could
  serve as a trailer or a channel intro, assembled from footage the other
  episodes already produce.
