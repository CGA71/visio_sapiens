# Visio Sapiens — YouTube series plan

**English** · [Français](YouTube_Series.fr.md)

This document maps the project's documentation onto a sequence of videos. Each
episode has a source doc, a central question it answers, and a suggested
on-screen demo.

The series is organised into **four thematic blocks** plus a pilot. A block is
watched in order and stands on its own: somebody who came for the backups does
not have to watch nine interface episodes first. Inside a block the order
matters; between blocks it does not.

| Block | Subject | Episodes |
|---|---|---|
| — | Pilot | 1 |
| **A** | Environment & CI/CD | 5 |
| **B** | Backup | 4 |
| **C** | The safe | 4 |
| **D** | Home-automation interface | 10 |

The source docs cited below exist in `docs/` in both languages
(`X.md` / `X.fr.md`), unless marked *to write*.

> **Revised 14 September 2026.** This plan was re-read against the repository
> two days after it was laid out. The pilot was rewritten (its narration and
> subtitles regenerated), a D10 episode joins, and several sections described
> a state that no longer holds. The detail is in
> [What changed since 12 September](#what-changed-since-12-september); the
> affected sections are corrected in place.

---

## Block A — Environment & CI/CD

The foundation: the machine, the cluster, the pipeline, and what breaks when
one of the three lies. This block answers "where does this project run, and how
does code get there".

| # | Title | Source doc | Central question |
|---|---|---|---|
| A1 | The environment: where this actually runs | `Vision.md`, `mosquitto-k3s.md` | Why a k3s cluster for a house? |
| A2 | The CI/CD pipeline | `CI_CD.md` | How does one commit reach two very different targets? |
| A3 | Debugging sessions | `Troubleshooting.md` | What does hunting a "this should not be possible" bug look like? |
| A4 | HTTPS, and the proxy trap | `Https.md` | How do you encrypt without locking yourself out? |
| A5 | The UPDATES screen | `Updates.md` | How does a screen say what it does not know? |

---

## Block B — Backup

Four short episodes where there used to be half a video. The subject is not
"how to copy a file" but **what you owe someone before overwriting their
work** — and the block goes all the way to the only proof that counts, the
restore.

| # | Title | Source doc | Central question |
|---|---|---|---|
| B1 | Nothing is ever half-written | `Backup_Retention.md`, `Deployment.md` | How do you guarantee atomicity without transactions? |
| B2 | Rotation and retention | `Backup_Retention.md` | What is kept, for how long, and who decided? |
| B3 | Restoring: the test nobody runs | `Backup_Retention.md` | Does a backup never restored exist? |
| B4 | What the backup does not cover | `Security.md`, `Vision.md` | Where does "backed up" stop and "reproducible" start? |

> **An honest reservation about this block.** `Backup_Retention.md` is 79 lines
> today: enough for B2, not for B1, B3 and B4. By the project's own rule — *a
> doc is written before its episode, never after* — those three need their
> source written first. B3 in particular has **no documented restore
> procedure** yet, and that is the kind of gap you discover on the wrong day.

---

## Block C — The safe

The entire block postdates the first version of this plan: none of it existed
when the series was laid out. It is the most recent material, and the most
demonstrable.

| # | Title | Source doc | Central question |
|---|---|---|---|
| C1 | Why a safe rather than a file | `Vault.md` | What does a safe give you that a `0600` file does not? |
| C2 | The SAFE screen | `Vault.md` | What does a defensible secrets console look like? |
| C3 | Unsealing with one password, from an enrolled device | `Unseal.md` | How do you remove the manual step without removing its safety? |
| C4 | An honest security review | `Security.md` | What must be said about what is not protected? |

---

## Block D — Home-automation interface

The project's historical core: the interface itself, from the gauge to the
generator. Ten episodes: the first nine have their doc, D10 has to write its
own first.

| # | Title | Source doc | Central question |
|---|---|---|---|
| D1 | CORE — the system dashboard | `Core_Dashboard.md` | How does a static page turn metrics into live gauges? |
| D2 | The dashboard generator | `Dashboard_Generator.md` | Why generate the YAML rather than edit it? |
| D3 | Case study: wiring a whole room | `Integration_Case_Study.md` | What does "end to end" mean, concretely? |
| D4 | Case study: the device assignment wizard | `Deployment.md` | How do you turn a raw scan into a safe form? |
| D5 | Automating an OAuth setup | `Google_Calendar.md` | How far can it be automated — and where does that stop? |
| D6 | A chatbot in the dashboard | `Chatbot_Integration.md` | Four providers behind one card, with no backend? |
| D7 | The visual charter editor (GRAPHIC TEMPLATE) | `Design_System_Editor.md` | How do you make a brand editable without letting the UI break? |
| D8 | Bilingual by construction | `Google_Calendar.md` + `locales/` + `_header.j2` | What does it take to hold **one** language on **one** screen? |
| D9 | The scheduler | `Scheduler.md`, `AI_Assistant.md` | How does an interface avoid lying about the future? |
| D10 | The wall tablet: designing for 1194 × 834 | *to write* (`Tablet_Layout.md`) | Why does a screen that works on a desk break on the living-room tablet? |

---

## Mapping to the old numbering

All twelve original episodes are placed; none is lost. Old episode 12 is the
only one **cut in two** — its halves had nothing in common but their brevity.

| Old | Becomes | Note |
|---|---|---|
| 1 Vision & architecture | **Pilot** | script revised on 14 September, narration and subtitles regenerated |
| 2 CORE | **D1** | |
| 3 Generator | **D2** | |
| 4 Wiring a whole room | **D3** | |
| 5 Assignment wizard | **D4** | |
| 6 CI/CD pipeline | **A2** | |
| 7 Debugging sessions | **A3** | |
| 8 OAuth | **D5** | |
| 9 Chatbot | **D6** | |
| 10 Design system | **D7** | |
| 11 Bilingual | **D8** | |
| 12 Backups + security | **B2** *and* **C4** | cut in two |
| — | A1, A4, A5, B1, B3, B4, C1, C2, C3, D9, D10 | eleven new episodes |

---

## Pilot — Vision & architecture

The only episode belonging to no block, because it announces all of them. Its
full script: `episode-01-vision-architecture.md`, revised on 14 September
2026. Its narration (`episode-01-narration.en.txt`) and subtitles
(`episode-01.en.srt`) are **generated** from the script by
`scripts/build_episode_media.py` — regenerate them after any voice-over change
rather than editing them by hand.

**Goal:** give viewers the mental model before any code. What Visio Sapiens
*is* (an OS-like control-center UI layered on top of Home Assistant, not a
themed dashboard), why the project builds its own rendering engine instead of
assembling ready-made cards, and how the series is organised.

**Show on screen:**
- The diagrams in `Vision.md`: the system overview (§2), the generation chain
  (§4), the console's six-beat loop (§5). The old "CORE / Room Engine / IA
  Layer / …" diagram has not existed since `Vision.md` was rewritten on
  9 September.
- A live tour of HOME **at 1194 × 834** (the wall tablet): the navigation
  rail, the header band (screen + time, weather, calendar), the status row
  (system, energy, alarm, thermostat, updates light), the radar, the metered
  devices, the assistant bar.
- `dashboards/model/design_system.yaml` beside the GRAPHIC TEMPLATE screen: one
  text size changed, every screen following.
- The map of the four blocks, in motion design.

**Talking points:**
- The one rule that drives every other decision: "Home Assistant is a data
  engine now; the UI is entirely driven by VSSP."
- **What the engine stands on, said exactly:** three community foundations
  (`button-card`, `card-mod`, `layout-card`), a few specialised cards (charts,
  weather, calendar, history), and the VSSP templates on top. The old line —
  "no community dependency, no more card-mod patches" — was false for anyone
  who opens the repository.
- The naming migration (OSVision → VSSP): the 12 September sweep, the three
  bugs it surfaced, and the two traces left (`OSVisionEngine`, CORE's K3s
  path — D1's live fix).
- The "what has shipped" montage is built from the Git history: `Vision.md`
  has no changelog section any more.

**Don't film:** any live secret (Livebox password, values from the safe, the
unseal passphrase, chatbot keys) — kept for block C, D3 and D6. Long-lived
tokens have not been part of setting up a tablet since 14 September.

---

## A1 — The environment: where this actually runs

**Goal:** set the hardware and software scene before any pipeline. A viewer who
does not know where Home Assistant lives cannot understand why deployment has
two targets.

**On screen:**
- The `k3s-master` host: `kubectl get nodes`, `kubectl get pods -A`, and the
  Home Assistant pod among them.
- The two worlds side by side: **staging** in k3s (one pod, one PVC) and
  **production** on HAOS (an appliance, SSH on 22222). These are not two
  environments of the same product: they are two different products receiving
  the same code.
- Self-hosted GitLab on the same host, its runner inside the cluster — the
  whole loop fits on one machine.
- The Vault container beside it, to announce block C without opening it.

**Points to make:**
- Why k3s rather than Docker Compose: not "Kubernetes because it is modern",
  but the runner, the PVCs and the automatic restart.
- The honest cost: a cluster that never finishes booting blocks everything, and
  it happens — episode A3 demonstrates it.
- The rival-units trap: `k3s.service` and `k3s-agent.service` fight over
  `127.0.0.1:6444`, and the symptom is a host that starts without ever
  finishing. A textbook case of "the service is active" ≠ "the service works".

**Source:** `Vision.md`, `mosquitto-k3s.md`, `Updates.md` (k3s section).

---

## A2 — The CI/CD pipeline

**Goal:** one commit, two very different deployment targets — the dual-target
pipeline as its own subject, independent of any one feature.

**Show on screen:**
- The pipeline diagram: MR/master → build → `deploy:staging` (k3s, `kubectl
  cp`) vs. tag → `deploy:production` (HAOS, SSH) with a manual gate.
- A live GitLab pipeline run, stage by stage.
- One of `CI_CD.md`'s still-open gaps, fixed live. G1 (the CSS/JS URL
  mismatch, the most visual) and G4 (the old name) are **now closed**. G2, G3
  and G5 are still marked open — but the pipeline now deploys ADMIN and
  regenerates the dashboards on the pod, so G2 and G3 need re-checking
  against the current pipeline before they are demonstrated.

**Talking points:**
- The `workflow:` rule as "the number one diagnostic reflex" — a push to a
  feature branch without an open MR launches *nothing*, which is the kind of
  thing that wastes an hour if you don't know to check it first.
- Why `configuration.yaml` needing a full HA restart (not a hot reload) was
  the root cause of an entire "staging looks unchanged" class of bugs — ties
  directly into episode A3.
- Secrets never touch a command line or a log: positional shell arguments in
  staging, stdin in production. Worth a full explanation, it's reusable
  knowledge outside this project entirely.

**Optional split:** if A2 runs long, cut it into A2a (pipeline mechanics) and
A2b (the G1–G5 gaps as a "known issues" episode) — the source doc already
separates cleanly along that line.

---

## A3 — Debugging sessions

**Goal:** the "detective story" episode. Real bugs, real symptoms, real
commands run to narrow down the cause — the format that tends to perform
best because the payoff (the fix) is earned on screen instead of assumed.

**Show on screen — a pool of eight independent mini-cases. Pick four per
episode, or split into A3a / A3b:**
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
4. **Bonus, from the project's own history:** the ROOMS & FLOORS
   wizard staying in French despite the language selector reading `en` —
   traced to a missing cache-busting `?v=` token on one specific iframe URL,
   the one asset in the whole pipeline that wasn't covered by the existing
   cache-busting `sed` step. A good closing case because it shows that even
   a mature pipeline can have exactly one uncovered corner, and that "it's
   probably cached" is worth checking before assuming a deploy failed.
5. **The cluster that died at every boot** *(11 September)* — `k3s.service`
   and `k3s-agent.service` fought over `127.0.0.1:6444`; the host started
   without ever finishing. "The service is active" ≠ "the service works".
   Films as a pair with A1.
6. **`set -e`: Illegal option** *(12 September)* — a shell script written from
   a Windows checkout, so in CRLF: `dash` reads `-e` followed by a carriage
   return. The fix is one line of `.gitattributes`, not the script.
7. **Pasting the token crashed CORE** *(12 September)* — with no token,
   `init()` replaced the whole page with the login form; `saveToken()` then
   called `init()` again on elements that no longer existed. The bug slept
   while everyone already had a token, and renaming the key woke it up.
   *(Since 14 September CORE asks for no token at all — the case still holds,
   the form is only a fallback now.)*
8. **Icons missing on one device only** *(14 September)* — on the iPad, only
   the ENERGY DEVICES icon showed in the ADMIN menu. Wrong first guess: lack
   of space. What settled it: Chromium at the same size showed all nine
   icons, and the server served all nine. The one visible icon was the only
   one the navigation rail already used, so it was already cached; the others
   failed to load from a stale frontend. Fix: reset the frontend cache. "Same
   screen size" ≠ "same browser".

**Talking points:**
- Each case follows the same shape: symptom → wrong first guess → the
  command that actually narrows it down → root cause → fix → the guard rail
  added afterward so it can't silently recur. Naming that shape explicitly
  makes the format replicable for future videos on new bugs.
- The "green pipeline, unchanged result" pattern is worth naming as its own
  concept — it recurs across cases 1, 2, and 4 in different disguises. Case 8
  is its cousin: **one client in the wrong**, while everything checkable from
  the workstation is right.

---

## A4 — HTTPS, and the proxy trap

**Goal:** add encryption to an interface that was sending passwords in clear,
without breaking the one way back in when the configuration is wrong.

**On screen:**
- The password crossing the network in clear on 8123 — captured, shown, then
  fixed. That is the argument, and it is visible.
- The Traefik ingress applied, the certificate served, the padlock appearing.
- **The trap, live:** apply the ingress *without* the `http:` block and get a
  site that answers nothing but 400s. Then the log line naming the exact
  address, and the fix.

**Points to make:**
- Additive, never a swap: 8123 stays open, because it is the way back in if
  `trusted_proxies` is wrong. Replacing instead of adding means locking
  yourself out with the key inside.
- `trusted_proxies` is a list of machines allowed to **assert who the client
  is**. Putting `0.0.0.0/0` there makes IP banning bypassable with a forged
  header.
- Mixed content: an HTTPS page can no longer call an `http://` address.
  Checked across the whole repository, and worth re-checking for every page
  added later.

**Source:** `Https.md`.

---

## A5 — The UPDATES screen: infrastructure updated from the interface

**Goal:** show a screen that knows what it does not know. Every row says what
its button would install, or explains why it cannot say.

**On screen:**
- The UPDATES screen and its eight rows: host, GitLab, k3s, containers,
  workloads, reboot required…
- **A sealed safe, and a screen that does not empty:** the rows go grey with
  "last measured …" instead of disappearing. That is the heart of the episode.
- A red row saying "current, but the service is not running" — the difference
  between reading a version number off a binary and checking that a service
  answers.

**Points to make:**
- `probed` / `stale` / `measured` / `health`: four fields for four different
  questions, where one boolean looked like enough.
- Why one row, and only one, refuses to be carried forward: after a restart,
  "reboot required" is false by construction — and that is precisely the moment
  the safe reseals, so the moment verification is impossible. The right answer
  is to show nothing rather than show yesterday.
- An installer that says "started, not finished" rather than "finished" when it
  cannot know.

**Source:** `Updates.md`.

---

## B1 — Nothing is ever half-written

**Goal:** open the BACKUP block with the invariant that makes it necessary,
before any question of rotation or retention.

**On screen:**
- A HOME regeneration launched live: the timestamped backup is written
  **before** the first byte of the new file exists.
- The three independent places the same invariant shows up: the assignment
  applier, the generator's protected dashboards, and the backup step itself.
- A failure forced mid-write — kill the generator while it writes — and the
  original file still intact.

**Points to make:**
- Atomicity in a system with no transactions: validate the whole payload before
  touching the disk, write beside then rename, never trust "it should not fail
  here".
- Why "re-running a scan does not reset previous work" is a guarantee that
  looks trivial while it holds and catastrophic when it breaks.

**Source:** `Backup_Retention.md`, `Deployment.md`, `Dashboard_Generator.md`.

---

## B2 — Rotation and retention: what is kept, and for how long

**Goal:** turn "I take backups" into a policy that can be stated, checked and
defended.

**On screen:**
- The backup directory after several weeks of real work: how many files, what
  size, what age.
- The "show me what you would delete" mode run before the real prune. A
  destructive tool that can rehearse before it plays.
- The rotation rule applied live, and the file disappearing.

**Points to make:**
- A retention policy is a trade between disk and regret, and it is better
  written down than left to the mood of manual `rm`s.
- What rotation **must never** take away, and how that is guaranteed.

**Source:** `Backup_Retention.md`.

---

## B3 — Restoring: the test nobody runs

**Goal:** the episode that gives the two before it their value. A backup never
restored is a hypothesis, not a backup.

**On screen:**
- Break a dashboard for real, on camera, with no prepared safety net.
- The full restore, timed: how long passes between "it is broken" and "it is
  back".
- The after-restore check: is the screen really the one from before, or only
  something that resembles it?

**Points to make:**
- Why a successful restore proves nothing if it was not performed from the
  actual failed state.
- What to write down the day it happens for real: the order of the steps, what
  must restart, what does not reload hot.

**Source:** `Backup_Retention.md`, `Troubleshooting.md`.

---

## B4 — What the backup does not cover

**Goal:** the short honest episode. Naming the blind spots beats discovering
them.

**On screen:**
- The Home Assistant registry: rooms and devices live **inside** HA, not in the
  repository — `house.yaml` is empty by design.
- Secrets: nothing encrypted is backed up by these scripts, and that is block
  C's subject.
- Long history: Home Assistant's state database, what it holds in clear, and
  what that implies.

**Points to make:**
- The difference between "backed up" and "reproducible": the repository rebuilds
  the interface, it does not rebuild the installation.
- Publishing your blind spots is a feature, not a confession.

**Source:** `Backup_Retention.md`, `Security.md`, `Vision.md`.

---

## C1 — Why a safe rather than a file

**Goal:** open the SAFE block with the argument, not the installation. What
does a safe give you that a `0600` file does not?

**On screen:**
- The previous secrets file, opened on screen, and the question asked plainly:
  who can read this, and what stops them?
- Vault running, its KV paths, one write then one read.
- The two installations — staging and production — and why they differ.

**Points to make:**
- What a safe **is not**: it does not protect you from an administrator of the
  machine, and saying so early avoids false security.
- Sealing as a design choice: the safe reseals on every restart, deliberately.
  It is a constraint, and the whole block turns around it.

**Source:** `Vault.md`.

---

## C2 — The SAFE screen

**Goal:** a secrets console inside the dashboard, and the decisions that make
it defensible.

**On screen:**
- ADMIN → SAFE: log in, the three branches, reveal a secret, hide it, edit it.
- The token in `sessionStorage` and never `localStorage` — and the difference
  demonstrated: closing the tab ends the session.
- The screen while the safe is sealed: what it can still say, and what it can
  no longer say.

**Points to make:**
- A page talking to Vault from the browser is a CORS problem, and an address
  written twice is an address that will eventually disagree with itself — hence
  a URL derived from the page's own hostname.
- What is never displayed, even to the legitimate user, and why.

**Source:** `Vault.md`.

---

## C3 — Unsealing with one password, from an enrolled device

**Goal:** the densest episode of the block. Remove the "`docker exec` and three
keys by hand" without removing what made it safe.

**On screen:**
- The safe sealed on purpose, the SAFE screen showing the field and the
  **UNSEAL** button, and the browser asking **which certificate to present**.
- The same click from a device that was never enrolled: refused during the
  handshake, before the passphrase is even read.
- The service log: timestamp, certificate name, IP, MAC seen, outcome — and
  **never** the passphrase or a share.

**Points to make:**
- What actually authenticates: the client certificate and the passphrase. The
  MAC address does not count — it changes with one command and does not survive
  a router. Saying so is more useful than pretending.
- Why the service cannot live inside Home Assistant: a passphrase must not
  become an entity.
- The CORS wildcard and the client certificate cannot coexist: a browser only
  presents a certificate if the page asks for `credentials: "include"`, and it
  then refuses `Access-Control-Allow-Origin: *`. A specification constraint that
  dictated the service's design.
- `scrypt` with its parameters **stored in the file** rather than hard-coded,
  so they can be raised later without orphaning the data.
- Five failures, fifteen minutes of shut door, counter persisted.

**Source:** `Unseal.md`.

---

## C4 — An honest security review

**Goal:** close the block by reading out, on screen, what is **not** protected.

**On screen:**
- `Security.md` opened and read, including the uncomfortable passages.
- The open design questions, as they stand.
- What has changed since the document was first written — the safe and the
  unseal service are precisely answers to two of those points.
- **The long-lived token removed from tablets** *(14 September)*: the console
  pages (ROOMS & FLOORS, DETECTED DEVICES, CORE) borrow the Home Assistant
  session of the dashboard around them, instead of a pasted token kept in
  clear in `localStorage`. `Security.md` does not mention that token at all —
  a gap to fill before filming.

**Points to make:**
- The difference between a project that has a threat model and a project that
  has a vibe.
- Why this is the episode that will age best, and why the document must be
  re-checked on the day of filming: it is the doc that goes stale most quietly.

**Source:** `Security.md`.

---

## D1 — CORE, the system dashboard

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
  redeploy, show the K3s panel come alive. *Still present in `core.html` on
  14 September.*
- **Authentication has changed** *(14 September)*: `core.html` no longer asks
  for a token, it borrows the CORE dashboard's session (`hass.auth`, a
  short-lived token refreshed on demand), and its URL now carries `?v=` like
  the other iframes. In the Network tab, the `Authorization` header carries
  that short-lived token. `Core_Dashboard.md` still describes the old token
  under the old key (`osv_ha_token`): rewrite it before filming.
- `esc()` and the XSS angle — a 90-second aside on why you escape data from
  your *own* backend, not just "untrusted" input.

**Good pairing:** this episode's live bug fix is a light version of what
episode A3 does at length — consider cross-linking.

---

## D2 — The dashboard generator

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
- The wizard → model bridge, which `Dashboard_Generator.md` still announces
  as `vssp_model_sync.py`, **now exists in another form**: the console's
  appliers (`vssp_rooms_apply.py`, `vssp_assign_apply.py`) write the model
  and then regenerate. A natural hook into D4 — and a section of the doc to
  update before filming.

---

## D3 — Case study: wiring up a whole room

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

## D4 — Case study: the device assignment wizard

**Goal:** a second, contrasting case study — an interactive tool instead of a
static dashboard, and a good moment to show the whole discover → decide →
apply shape that recurs across the project (it's the same shape as the
ROOMS & FLOORS screen).

**Show on screen:**
- The pipeline from `Deployment.md`:
  `DISCOVERY SCAN → report.json → prepare → assign_data.json → the form →
  webhook → apply → house.yaml → the generator → dashboards/views/`.
- A live scan → assignment → apply cycle in the browser.
- The MD5-checked file table as a "how we made sure the right files shipped"
  beat — pairs well with episode A3's caching postmortem.

**Talking points:**
- "Nothing is ever half-written": the applier validates the whole payload
  before touching `house.yaml`, and backs it up first — a good discussion of
  atomicity in a system with no real transactions.
- Re-running a scan doesn't reset prior work — a subtle but important
  guarantee to call out explicitly, since it's exactly the kind of thing that
  looks unremarkable when it works and catastrophic when it doesn't.

---

## D5 — Automating an OAuth setup

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
  reaches a command line, exactly like the Livebox password and the chatbot
  keys.

**Good pairing:** episode D8 uses this same screen as its worked example —
film them back to back while the material is fresh.

---

## D6 — A chatbot inside the dashboard

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

## D7 — The visual charter editor (GRAPHIC TEMPLATE)

**Goal:** a visual charter that used to be one hand-edited theme file,
turned into a model plus a generator plus an editing screen — the same
model→template→generated shape as episode D2, applied to appearance instead
of structure.

> **Status reset on 13 September** (rule 2 of the action plan): the screen
> gained the typeface, text sizes by usage and the replaceable logo. Nothing
> filmed before would still be right.

**Show on screen:**
- `model/design_system.yaml` next to the generated theme, one color changed
  live, regenerate, and the whole interface following.
- **Text sizes by usage** — clock, titles, values, text, labels, each from 50
  to 200 %: one slider, and every value on every screen follows. It is also
  the pilot's demo (section 6).
- **The typeface joining the charter**, and the trap of its stylesheet:
  `/local` is cached for a month by the browser, so a changed typeface does
  not arrive until the stylesheet's URL carries a version.
- **The replaceable square logo** of the navigation rail (default, uploaded,
  or none), in a rail only as wide as its longest entry.
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
- **A model older than the code**: the pod's live model does not know the
  tokens added after it was created. Rather than falling back to nothing, the
  generator fills each missing token from the factory reference
  (`design_system.default.yaml`). A transferable rule: data the user wrote
  ages more slowly than the code that reads it.

**Good pairing:** D10 — the same week of work, seen from the tablet: the rail
fitted to its entries and the header band brought back to its height were
born there.

---

## D8 — Bilingual by construction

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

**Second case — third-party cards speaking the browser's language**
*(12 September)*: with dashboards generated in English, the header's calendar
and weather stayed in French. Those cards read `hass.language` — the
browser's language (fr-FR) — not the generated one. Fix: the `language:`
option where the card has one (calendar-card-pro), otherwise card-mod hiding
the text and rewriting it (simple-weather-card) — the patch owned up to in
section 4 of the pilot. A fr→en switch that "doesn't work" can mean "one
third-party card stayed French".

**Good pairing:** episode A3's fourth case (a wizard stuck in French because
one iframe URL lacked a cache-buster) is the same screen's earlier
mistranslation, from a completely different cause. Shown together — with the
second case above — they make the point that "wrong language on screen" is a
symptom, not a diagnosis.

---

## D9 — The scheduler

**Goal:** finish the interface block with the screen that makes the house act
over time rather than on command.

**On screen:**
- The scheduler screen, a slot created then edited, and the real effect on a
  device.
- The model behind it: what is generated, what is read at run time.

**Points to make:**
- Why scheduling is a case where the interface cannot lie: a mistake is not
  visible at the moment of the click but three hours later.
- The AI assistant as the natural extension of the same screen.

**Source:** `Scheduler.md`, `AI_Assistant.md`.

---

## D10 — The wall tablet: designing for 1194 × 834

**Goal:** the device that matters is not the desktop screen you develop on,
it is the 11-inch iPad in landscape hanging on the wall. An episode about
everything a desktop screen does not show — and about the rule that came out
of it: **every test runs at 1194 × 834**.

**On screen, four cases from 14 September:**
1. **Device names 0 px wide.** In PER-DEVICE CONSUMPTION a row gets 272 px,
   and its fixed columns (icon, room, power, energy, chevron, gaps) asked for
   358. The name column fell to zero — while the room column only printed a
   dash. Dropping the column was not enough (18 px); every column had to be
   fitted to its real content.
2. **A 246 px header band instead of 76.** The navigation rail spans both
   grid rows; with `auto auto` rows and a short body, the grid spreads the
   rail's height over both — the header swells. Nine screens out of ten got
   away with it only because their body was taller than the rail. `auto 1fr`
   everywhere.
3. **A new tablet = one login.** The console pages (iframes) asked for a
   long-lived token to paste. They now borrow the tablet's own session:
   nothing to paste, nothing permanent stored in the browser.
4. **What the test workstation does not see.** Icons missing on the iPad
   only: Chromium at the same size showed them all. Screen size can be
   simulated; the browser engine cannot (see A3, case 8).

**Points to make:**
- Measure rather than look: every case was settled by a width or a height
  read from the DOM, not by a screenshot.
- A rail as wide as its longest entry, a header as tall as its content: let
  the content size the layout rather than the other way round.
- Why the tests run in a browser that is not the tablet's, and how to say so
  honestly in every report.

**Source:** *to write* — `docs/dashboards/Tablet_Layout.md`. The four cases are
recorded in their commits of 14 September; write them up while they are
fresh.

---

## What changed since 12 September

The plan was laid out on 12 September; what follows has moved since, or was
already wrong that day.

| Date | What changed | Episodes affected |
|---|---|---|
| 9 Sep | `Vision.md` rewritten: the old "Room Engine / IA Layer" diagram and the changelog section disappear | Pilot |
| 12 Sep | The old name removed from the code — except `OSVisionEngine` and CORE's K3s path | Pilot, D1, A3 |
| 12 Sep | The header's calendar and weather follow the generated language, no longer the browser's | D8 |
| 13 Sep | The typeface, text sizes by usage and the replaceable logo join the GRAPHIC TEMPLATE; missing tokens are filled from the factory reference | D7 (status reset), Pilot |
| 13-14 Sep | The navigation rail and header band fit their content; the ENERGY panels line up in height; the room column leaves PER-DEVICE CONSUMPTION | D10, Pilot |
| 14 Sep | The console pages borrow the tablet's session: no more long-lived token | C4, D1, D10, Pilot |
| 14 Sep | The ENERGY DEVICES header brought back to the standard (76 px) | D10 |
| — | Already wrong on the 12th: G1 and G4 closed in `CI_CD.md`; the `vssp_model_sync.py` bridge built in another form; `weather-forecast` used nowhere; "everything else is the in-house engine" contradicted by 173 `button-card` and 95 `card_mod` blocks | A2, D2, Pilot |

Three source docs still describe the earlier state and must be updated
**before** their episode (rule 1): `Core_Dashboard.md` (the old token, D1),
`Dashboard_Generator.md` (the bridge, D2), `CI_CD.md` (the status of G2/G3,
A2).

---

## Action plan — what to film next

Status is about **filmability**, not about whether the feature works: a row is
"ready" only if the documentation and a demo that survives one take both exist
today.

| # | Episode | Ready to film? | Concrete next step |
|---|---|---|---|
| — | Pilot | **Script revised — voice and captures to redo** | Recapture HOME at 1194 × 834; re-record the voice section by section; rerun `scripts/build_episode_media.py` after any script change |
| C3 | Unsealing from an enrolled device | **Ready, and the freshest** | Seal the safe on purpose for the take; have a second, unenrolled device to film the refusal |
| A5 | The UPDATES screen | **Ready** | Capture the grey "last measured …" rows while the safe is sealed — that only happens there |
| C2 | The SAFE screen | **Ready** | Prepare demo secrets; nothing real on screen |
| D5 | Automating an OAuth setup | **Ready** | A blank Google Cloud project, so consent is filmable without a cut |
| D8 | Bilingual by construction | **Ready** | Capture EN/FR side by side; the second case (the header's third-party cards) only exists in history now — replay the commit from before 12 September |
| D2 | The dashboard generator | Ready, doc to touch up | Pick the single model change to demonstrate; update the "bridge" section of `Dashboard_Generator.md` |
| D7 | The visual charter editor | **Screen changed — status reset** | Refilm with the typeface, text sizes and logo; decide whether the `color-mix()` trap is a moment here or its own short |
| D6 | A chatbot in the dashboard | Ready, with a caveat | Confirm which provider keys can be on screen; blur or use a throwaway |
| A4 | HTTPS and the proxy trap | Ready, not applied | The ingress is not in place yet: do it once **off camera**, then replay it |
| A2 | The CI/CD pipeline | Ready, demo to re-pick | G1 is closed: re-check G2/G3/G5 against the current pipeline, then pick the one fixed on screen |
| C1 | Why a safe | Ready | Find the previous secrets file in git history |
| D1 | CORE | Blocked on a fix, doc to rewrite | The `/local/osvision_v2/…` 404 still reproduces (checked in the code on 14 September); rewrite the authentication part of `Core_Dashboard.md` |
| D4 | The assignment wizard | Ready | Re-read the source doc end to end before writing the script |
| D3 | Wiring a whole room | Partly blocked | Two open calls — settle them, or film them as open questions |
| B2 | Rotation and retention | Ready | Let the directory age: a folder with three files shows nothing |
| C4 | Honest security review | Ready, doc to complete | Add the removal of the tablets' long-lived token to `Security.md`; re-check the document on the day |
| A3 | Debugging sessions | Ready, film last | Eight cases in the pool: pick four, or split into A3a / A3b |
| D10 | The wall tablet | **Doc to write** | `Tablet_Layout.md`: four fresh cases from 14 September, to write while they are |
| A1 | The environment | **Doc to write** | No document describes the host itself; write it first |
| D9 | The scheduler | **Doc to re-read** | `Scheduler.md` predates the latest screens |
| B1 | Nothing is ever half-written | **Doc to write** | The invariant is enforced in three places and documented in none |
| B3 | Restoring | **Doc to write — priority** | No restore procedure exists. That is a gap, not just a missing episode |
| B4 | What the backup does not cover | **Doc to write** | Depends on B3 |

Three standing rules for this plan:

1. **A doc is written before its episode, never after.** That is what keeps the
   scripting step short — and it is the rule that files three block-B
   episodes, A1 and D10 under "doc to write" rather than "ready".
2. **When a screen changes, its episode's status resets.** The SAFE screen got
   its UNSEAL button after this plan was written: anything filmed before would
   already be wrong. The same happened on 13 September to the GRAPHIC TEMPLATE
   (D7), and on the 14th to HOME (the pilot).
3. **A block is published in order, blocks are published in any order.** That is
   what allows C3 to go out while it is fresh, without waiting for block B to be
   written.

---

## Sequencing notes

- **Block C is the readiest**, which is counter-intuitive: it is the newest. C3
  in particular should be shot soon — an episode about a mechanism you have just
  built tells better than one about a mechanism from six months ago.
- **Block B is the least ready**, and knowing that is useful: three of its four
  episodes need a doc first. B3 is the most important of the three, because
  writing its doc means acquiring a restore procedure that does not yet exist.
- **A1 → A2 → A3** is the natural "here is the machine, here is how code reaches
  it, here is what breaks" thread. Filmable as a mini-arc.
- **D5 → D8** is still the best pairing: the same screen, first as a feature then
  as a language problem. Same session, that order — D8's before/after only
  exists while the pre-fix version is recent in history.
- **A3 is best filmed last** for each bug — once the fix is deployed and
  confirmed — but can be **published** earlier if a case is already fully
  resolved.
- **C1 → C2 → C3 → C4** is the one block that really watches as a story: a
  problem, a tool, an automation, an honest reckoning.
- **The pilot is published first**, and it is the one that has to be right
  before everything else: it cites episodes from every block. Redoing it
  after D7 or D10 would mean redoing it a third time.
- **D7 → D10**: the same week of work — the charter, then the tablet that
  shows it. Film them in that order, while the screens are stable.
- The ADMIN console now has nine screens (ROOMS & FLOORS, DETECTED DEVICES,
  DEVICE ASSIGNMENT, ENERGY DEVICES, GOOGLE CALENDAR, GRAPHIC TEMPLATE,
  DASHBOARDS, UPDATES, SAFE) — enough for a short "console tour" to serve as a
  trailer, cut from footage the other episodes already produce. ENERGY DEVICES
  still reads "not built yet": show it as it is, or cut it.
