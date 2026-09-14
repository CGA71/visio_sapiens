# PILOT EPISODE — Vision & Architecture
## "Visio Sapiens: why I threw out the native Lovelace cards"

**Source doc:** `Vision.md`
**Central question of the episode:** Why replace Home Assistant's native Lovelace cards with an in-house engine?
**Visual anchor:** architecture diagram + live tour of the HOME dashboard
**Length:** 20 min — the format of the whole series
**Revision:** 14 September 2026 — see [Revision of 14 September](#revision-of-14-september-2026) at the end for what changed and why.
**Shooting format:** no face on camera at any point. The channel runs on **voice-over + screen capture + hands-only shots** (keyboard, mouse, optionally a stylus on a tablet to annotate the diagram).

**Goal:** give viewers the mental model before any code. What Visio Sapiens is — a control-center-style interface sitting on top of Home Assistant, **not** a dashboard with a nice skin — why the project builds its own rendering engine instead of assembling ready-made cards, what the console and "secure by default" look like once demonstrated, and how the rest of the series is organised.

**⚠️ Do not film:** any live secret — Livebox password, values from the safe, the unseal passphrase, the chatbot providers' keys. Their handling has its own episodes: block C (the safe), D3 (Livebox), D6 (chatbot). A new tablet no longer asks for a long-lived access token: logging in to Home Assistant is enough, so there is nothing to hide on that front.

---

## 0. COLD OPEN — THE DOUBLE PROBLEM (0:00 - 1:00)

**Visual:** the animated power meter posted by seanblanchfield on the Home Assistant forum ("Dashboard real-time power meter with device-level detail", May 2022) — built, as it happens, with Bar Card. No camera, screens only. Credit on screen.

**Voice-over:**
> "I think these dashboards are beautiful. The Home Assistant community turns out cards that are genuinely stunning to look at."

**Visual (cut):** real capture of the "Bar-Card Repo Removed in 2025.6.2" thread (Home Assistant forum, June 2025): the "Repository removed from HACS" warning posted by the thread's author, then the reply "The bar-card still works". Credit on screen.

**Voice-over:**
> "Bar Card, one of the most widely used cards for animated energy bars, was removed from HACS in June 2025: no longer maintained. Everyone using it got the same warning: go and remove it. It still works — but the day an update breaks it, nobody will fix it. 'Beautiful' and 'maintained' are two different things."

**Visual (cut):** padlock icon in motion design, then a simple diagram — a house, an "Internet" arrow, a red question mark on the arrow.

**Voice-over:**
> "And there's a second problem, and this one is more serious: if you want to reach that dashboard from your phone when you're away from home, it has to be exposed to the internet. And it isn't just cards you're exposing — it's your personal data. Your presence patterns, your cameras, sometimes your locks. A poorly secured dashboard on a platform reachable from outside is an open door into your house."

**Animated title:** VISIO SAPIENS — Pilot: Vision & Architecture

---

## 1. MY APPROACH: SIMPLE, EFFECTIVE, SECURE (1:00 - 2:30)

**Visual:** hands on keyboard/mouse, terminal or code editor blurred in the background. No face at any point.

**Voice-over:**
> "Faced with those two problems — maintenance that gives out, and security that gets neglected — I made one decision up front, and it's the one that defines the whole project: build something **simple and effective**, that ships with as much security as possible **by default**, not as an option you bolt on later if you happen to think of it.
>
> In practice that means: as few external dependencies I have no control over as possible, an architecture designed from day one to be exposed to the internet without that being a gamble, and an environment that lets me roll back cleanly when something breaks — because it will break, sooner or later, on any project.
>
> Concretely, that translates into a CI/CD setup that lets **one self-taught person** — not a DevOps team, just someone motivated — grow the product step by step, or simply **restore a previous version straight into HAOS** when an update goes wrong. We'll go deep on that pipeline in block A of the series, and backups have a block of their own, block B. But I wanted you to know, right here in the first episode, that this safety net exists and that it's part of the foundation."

**On-screen text (boxed):**
> 🔧 Few external dependencies outside my control
> 🔒 Security designed in, not added later
> ↩️ Version rollback inside HAOS, reachable even self-taught

---

## 2. THE OTHER PROBLEM NOBODY SEES: HA'S COMPLEXITY (2:30 - 3:30)

**Visual:** screen capture of the standard Home Assistant interface — menus, config panels, YAML — mouse navigating to illustrate the complexity, no camera.

**Voice-over:**
> "There's a third reason behind all this, simpler to state but just as central: Home Assistant's native interface is **very complex**. Powerful, yes — but complex. Between the configuration menus, the entities, the areas, the nested dashboards, it's easy to get lost, especially when you're starting out.
>
> What Visio Sapiens sets out to do is **simplify that experience** — not hide Home Assistant's power, but make it reachable through a coherent interface, designed for daily use rather than for technical configuration."

**On-screen text (boxed):**
> 🎯 Project goal: simplify the experience, without giving up HA's power

---

## 3. WHAT VISIO SAPIENS ACTUALLY IS (3:30 - 5:00)

**Visual:** Visio Sapiens HOME dashboard full screen, mouse moving slowly across the areas being described. No face.

**Voice-over:**
> "So what is it, concretely? Visio Sapiens is not a dashboard. It's a **control-center-style interface**, sitting on top of Home Assistant.
>
> The distinction matters. A dashboard is a collection of cards you assemble. A control center is a coherent system, with its own rendering engine, its own visual logic, its own identity — and it simply goes to Home Assistant to fetch the data.
>
> And that distinction has a very concrete consequence, one you'll see at work in every episode: the interface isn't assembled by hand, it's **generated**. You describe your home once, in an admin console — the language, the format, the rooms, the look — and every screen is produced from that description, then kept in step as the home changes. Adding a room isn't drawing a new dashboard: it's declaring a room, and letting the generator do the rest. A dashboard you assemble by hand ages. A dashboard that's generated keeps up.
>
> And that leads to the single rule that drives every technical decision in this project, the one you'll meet again in every episode:
>
> **Home Assistant is nothing more than a data engine. The interface is driven entirely by VSSP.**"

**On-screen text (boxed):**
> 🧠 HA = data engine
> 🎛️ VSSP = the interface, all of it

---

## 4. WHY NOT THE NATIVE LOVELACE CARDS? (5:00 - 7:30)

**Visual:** split screen — native Lovelace editor with its standard cards on the left, the Visio Sapiens HOME dashboard on the right. On the three foundations, overlay their names on the right-hand screen. On card-mod, show the header's weather card, then the `::after` rule in `_header.j2` that rewrites its text. Still no camera.

**Voice-over:**
> "So here's the question that comes up straight away: why not just use the native Lovelace cards? They exist, they're maintained by the Home Assistant core, they work perfectly well.
>
> Exactly — they work perfectly well **for what they are**: a system of stacked cards. But the moment you want a coherent visual identity and a HUD that behaves like a real system interface rather than a grid of widgets, you hit Lovelace's glass ceiling.
>
> So the project made a call: don't assemble ready-made cards, build a rendering engine of its own. And I want to be precise, because the short version would be wrong: this engine doesn't start from nothing. It stands on three community building blocks — **button-card, card-mod and layout-card**. Foundations, not widgets: one draws, one styles, one places. Everything you see on top — the navigation, the header band, the gauges, the rooms — is templates I write, generated and versioned in the repository. And a handful of specialised cards do what it would be absurd to rewrite: the charts, the weather, the calendar, the history.
>
> The difference from a typical community dashboard is the exposed surface. Three foundations and a handful of cards, which the updates screen watches as a family of their own — not thirty widgets with thirty maintainers. The day a building block gives out, it's one block to replace, not thirty cards to track down.
>
> The price of that choice is real, let's be honest: for everything above the foundations, **I become the maintainer**. But that cost is one I **control**: a bug in my templates, I fix it that same evening.
>
> And card-mod deserves a word. On my own templates, it's a tool. Inside the shadow DOM of a card I don't control, it's a patch — and I still have one: to force the language of a third-party weather card, I hide its text and write another one over it. It holds until the update that renames a class. That's why that kind of patch stays an exception, and why it's documented."

**On-screen text (boxed):**
> 🧱 Foundations: `button-card` · `card-mod` · `layout-card`
> 📊 Specialised cards: charts · weather · calendar · history
> 🔧 On top: the VSSP templates, generated and versioned

---

## 5. THE ARCHITECTURE DIAGRAM (7:30 - 9:30)

**Visual:** full screen on the "System overview" diagram from `Vision.md` (§2), redrawn at recording resolution. Hands-only shot with stylus/graphics tablet highlighting each block in turn — this is the episode's only moment of "physical presence", limited to hands. Move on to the generation chain (§4), then to the console's six-beat loop (§5).

**Voice-over:**
> "Here's what the full architecture looks like. I'm showing it to you once, in full, because it's the map you'll need to follow the whole series."

**Diagram walkthrough, block by block (highlighted in turn with the stylus):**

> "Five places hold something, and they are not interchangeable. The **Git repository**, on my workstation: the model, the templates, the translations, the tooling. The **GitLab pipeline**, which validates, builds and deploys. **Two targets**, receiving the same package: a k3s cluster for staging, Home Assistant OS for production. And the **browser** — the tablet, the phone — where the dashboards appear.
>
> In the middle, one single command: **the generator**. It takes the description of the house, the templates and the language, and it produces every dashboard and the theme. Nobody writes a dashboard by hand.
>
> And every screen of the admin console follows **the same loop**: a form sends what you decided, a script backs up first, writes the model, regenerates, then reports what it did."

**Voice-over (walkthrough close):**
> "Take one thing away from this diagram: every piece has one precise responsibility, and none of them does another one's job. That's what lets the project hold up over time instead of turning into a plate of YAML spaghetti — and it's what makes the rest of the series possible: you can only version, back up and restore cleanly what is structured in the first place."

---

## 6. LIVE TOUR OF THE HOME DASHBOARD (9:30 - 11:30)

**Visual:** live capture at **1194 × 834** — the actual wall tablet (11-inch iPad, landscape), Home Assistant's sidebar hidden. Mouse pointing at each element as the narration reaches it. No face.

**Voice-over:**
> "Enough theory, let's look at the result. This is HOME, the landing screen, as it appears on the living-room tablet."

**Pointing in turn (mouse cursor):**
> "On the left, the **navigation rail**: one entry per declared room, plus the system screens. It's generated too — add a room, and its entry appears on every screen at once.
>
> At the top, the **header band**: the screen's name and the time, the weather, the calendar. The same band on every dashboard, because it comes from a single template.
>
> Just below, the **status row**: the system, the energy, the alarm with its modes and its panic button, the thermostat — and this updates light, which turns orange when something is waiting, and leads to the screen that says exactly what.
>
> In the centre, the **protocol radar**, and next to it, the metered devices with what they draw. Then the **assistant bar**, and the house's latest events."

**Transition to the repo:**
> "And now the part I most enjoy showing, because it makes all of this concrete: where this screen's look comes from."

**Visual:** split screen — `dashboards/model/design_system.yaml` in a code editor on the left, the ADMIN → GRAPHIC TEMPLATE screen on the right, then HOME. Raise the "Values" slider in the Text sizes group, apply, go back to HOME.

**Voice-over:**
> "On the left, a file in the repository, `design_system.yaml`: every colour, the typeface, the size of each kind of text. On the right, the console screen that edits it. I raise the size of the values — and every screen follows at once, because there's only one source. Not ten cards to touch up one by one, hoping you didn't miss any. The code and the interface speak the same language — and so they're versioned like a real software project."

---

## 7. THE CONSOLE: DESCRIBE THE HOUSE ONCE (11:30 - 14:00)

**Visual:** capture at 1194 × 834. The ADMIN menu and its nine rows, then ROOMS & FLOORS: declare a demo room ("Laundry", ground floor), APPLY, the status message appearing. Back to HOME, close-up on the rail; then ENERGY and CORE to show the same entry everywhere.

**Voice-over:**
> "I told you the interface is generated from a description of the house. Here's where you write it: the **admin console**.
>
> Nine screens, one per decision. The rooms and the floors. The devices the network has just discovered. Which room each device belongs to. The Google calendar, the visual charter, the dashboards themselves, the updates, and the safe.
>
> Let's declare a room, live. A laundry room, on the ground floor. I apply.
>
> What happens during those few seconds is the loop I showed you on the diagram. The form sends what I decided. A script **backs up** the current state **first** — always, before writing anything. It writes the model, reruns the generator, and reports back: that message, up there, is the report.
>
> I go back to HOME. The laundry is in the rail. And it's there on every screen at once — the energy, the system, the console — because the rail isn't written by hand anywhere.
>
> One honest detail: the room's own screen is declared in Home Assistant's configuration, and Home Assistant only rereads that configuration at startup. Its entry appears straight away; its screen, at the next restart. I'd rather tell you than cut it in the edit.
>
> And it's the same gesture for everything else. You never draw a dashboard. You decide, and the console writes."

---

## 8. SECURE BY DEFAULT, CONCRETELY (14:00 - 16:30)

**Visual:** four tiles in motion design, each opening onto proof on screen: a webhook automation with `local_only: true`; the DevTools of a console iframe, `localStorage` holding no token; the SAFE screen with **demo** secrets (names visible, values hidden); a `0600` file and a deploy log with no password in it. Then `Https.md` on screen for the "not done yet" part.

**Voice-over:**
> "At the start I promised you security by default. A promise can be checked — so here's what it means concretely, including what isn't done yet.
>
> **One**: the console's forms send nothing with a password. They go through entry points Home Assistant only accepts from the local network. From the internet, they don't exist.
>
> **Two**: a new tablet keeps no permanent credential. The console screens borrow the session you logged in with, a short-lived token Home Assistant renews by itself. Losing the tablet isn't losing a key.
>
> **Three**: secrets live in a safe, not in files. Home Assistant can read the name of every secret there, never its value — because everything Home Assistant reads ends up in clear in its history database. The safe closes at every restart, and you reopen it with one passphrase, from a device you've enrolled.
>
> **Four**: no password ever goes through a command line or into a log — not the router's, not the assistants' keys.
>
> And now, what isn't done. Today, on the local network, the Home Assistant password still travels in clear. The move to HTTPS is written and documented; it isn't in place yet. It has its own episode, in block A.
>
> That's what security by default means to me: not a list of promises, but a list of things you can check — and, published right beside it, the list of the ones still missing."

**On-screen text (boxed):**
> 🏠 Webhooks: local network only
> 📱 Tablets: the session, never a permanent token
> 🔐 Secrets: in the safe — HA reads the names, never the values
> 🚫 No password on a command line or in a log
> ⏳ HTTPS: documented, not in place yet

---

## 9. A NOTE ON NAMES (16:30 - 17:15)

**Visual:** the commit of 12 September (`refactor: the old name is gone from the code…`) on screen, then the two remaining traces: `class OSVisionEngine` in `www/vssp/js/vssp.js`, and the `/local/osvision_v2/k3s_stats.json` path in `core.html`. Voice-over alone.

**Voice-over:**
> "A quick aside before we wrap up, because you're going to run into this: the project was originally called **OSVision**, before it became **VSSP**. In September, a big sweep removed the old name from the identifiers, the components and the stylesheets — and that sweep surfaced three real bugs, including a dead link nobody had noticed. But some traces remain: the JavaScript engine still carries the old name, and the K3s panel on the CORE screen still looks for its file under the old path. A good project doesn't hide those marks, it documents them. That one, we'll fix live in episode D1."

---

## 10. QUICK MONTAGE — WHAT HAS SHIPPED (17:15 - 18:00)

**Visual:** fast-cut montage timed to the music, one shot per milestone: the generator regenerating, the ROOMS & FLOORS screen, the safe's UNSEAL button, the UPDATES screen, the GRAPHIC TEMPLATE changing the typeface. Milestones sourced from the Git history (`git log --oneline`): `Vision.md` has had no changelog section since it was rewritten on 9 September.

**Voice-over (short, punchy):**
> "None of what you've just seen existed a few months ago. A generator that produces every screen. A console that declares the rooms. A safe that unseals from an enrolled device. An updates screen that knows what it doesn't know. A visual charter that changes right down to the typeface. This isn't a frozen project — it's a system with a history, and it's still writing one."

*(Prod note: this block can double as an alternative opener if the final edit wants a more energetic cold open.)*

---

## 11. THE MAP OF THE SERIES (18:00 - 19:00)

**Visual:** motion design — four tiles lighting up one after another (A · B · C · D), each with its block's title and episode count (6 · 2 · 3 · 10), then all four together, with "20 min" under each tile.

**Voice-over:**
> "The rest of the series is organised into four blocks, and you choose your way in. Every episode runs about twenty minutes: time to show, not just to tell.
>
> **Block A** is the foundation: the machine, the cluster, the pipeline, and what breaks when one of the three lies.
>
> **Block B** is backup — all the way to the only proof that counts: the restore.
>
> **Block C** is the safe: where the secrets live, and how you unseal it without typing three keys by hand.
>
> And **block D** is the interface itself, from the gauge to the generator.
>
> Inside a block, the order matters. Between blocks, it doesn't: if you came for the backups, you don't have to sit through ten interface episodes first."

**On-screen text (boxed):**
> A · Environment & CI/CD — B · Backup — C · The safe — D · Interface

---

## 12. CLOSE (19:00 - 20:00)

**Visual:** back to the HOME dashboard full screen, or animated channel logo. Voice-over alone. The last twenty seconds carry the YouTube end screen (subscribe + D1 + a block C episode).

**Voice-over:**
> "What to take away: Visio Sapiens isn't a dashboard, it's a control center, simple, effective and secure by default. Home Assistant supplies the data, VSSP supplies the interface — on a small number of watched foundations, with a pipeline that lets you roll back.
>
> If you don't know where to start, take D1: we follow a single piece of data, from the host machine all the way to a gauge in your browser.
>
> Subscribe, and tell me in the comments: is your Home Assistant still a stack of cards, or have you started climbing out? See you very soon."

---

## PRODUCTION NOTES

- **Faceless format:** no shot to camera is to be filmed. The voice-over carries the whole narrative. The only "human presence" shots allowed are hands-only (keyboard, mouse, stylus on tablet to annotate the architecture diagram, section 5). Everything else is 100% screen capture, motion design, and on-screen text.
- **Voice recording:** one section = one audio file, placed at the start of its slot. The narration-only text, split by section, lives in `episode-01-narration.en.txt`; the subtitles in `episode-01.en.srt`. Both are **generated from this script** — regenerate them after any voice-over change rather than editing them by hand.
- **Overall tone:** explanatory, and assertive on the "in-house engine vs native Lovelace" call and on security — that's the thesis of the episode, it should be argued clearly. But section 4 says exactly what the engine stands on: that is what keeps the thesis defensible in front of a viewer who opens the repository.
- **Through-line of the intro:** double problem (community maintenance giving out + unsecured internet exposure) → the project's answer (simple/effective/secure product + CI/CD restorable in HAOS) → HA's native complexity → simplification.
- **Captures:** all at **1194 × 834** (11-inch iPad, landscape — the actual wall tablet), Home Assistant's sidebar hidden. Any HOME capture made before 14 September 2026 is stale: the header band, the status row and the device list have changed since.
- **Architecture diagram:** the diagrams in `Vision.md` (§2, §4, §5) are mermaid; redraw them at recording resolution before shooting.
- **B-roll:** seanblanchfield's animated power meter and the "Bar-Card Repo Removed in 2025.6.2" thread (Home Assistant forum — see "Chapter 0 montage" below), internet exposure diagram, native HA interface (complexity), live HOME dashboard, `design_system.yaml` and the GRAPHIC TEMPLATE screen, Git history for the montage.
- **Chapter 0 montage:** rendered on 14 September 2026 (60 s, 1920 × 1080, 30 fps, no sound), timed on the FR subtitles; a version with the FR subtitles burned in serves as a preview. The three captures come from the Home Assistant forum and are **quotations**: keep the on-screen credits, link the threads in the description, and ask seanblanchfield's permission for the GIF before publishing. Kept in `media/pilote/chapitre-00/`, which git ignores: the videos, `pilote_chap00_SOURCES.txt` (running order, sources, credits) and, in `sources/`, the captures and the script that re-renders it.
- **Do not film:** any live secret → block C, D3, D6. In section 8 the safe shows demo secrets only.
- **The demo room (section 7):** declare it, apply, film the rail; its own screen only exists once the configuration fragment is merged and Home Assistant restarted — do that off camera if you want to open it. Delete it after the take (ROOMS & FLOORS), or it stays in the rail of every screen.
- **Cross-references:** CI/CD pipeline → A2; HTTPS → A4; backup and restore → block B; the safe → C1, C2; security review → C3; CORE and the old-path K3s bug → D1; generator → D2; assignment → D4; chatbot → D6; visual charter → D7; the wall tablet → D10.

---

## NARRATION TIMING

Measured against the slots above, at 140 words per minute. The narration-only text, split by section, lives in `episode-01-narration.en.txt`.

<!-- TIMING-TABLE -->
| # | Section | Slot | Narration | Delta |
|---|---|---|---|---|
| 0 | Cold open | 60 s | 62 s | +2 s |
| 1 | My approach | 90 s | 85 s | −5 s |
| 2 | HA's complexity | 60 s | 34 s | −26 s |
| 3 | What Visio Sapiens is | 90 s | 82 s | −8 s |
| 4 | Why not native cards | 150 s | 144 s | −6 s |
| 5 | Architecture diagram | 120 s | 92 s | −28 s |
| 6 | HOME tour | 120 s | 105 s | −15 s |
| 7 | The console | 150 s | 93 s | −57 s |
| 8 | Secure by default | 150 s | 99 s | −51 s |
| 9 | A note on names | 45 s | 44 s | −1 s |
| 10 | Montage — what has shipped | 45 s | 28 s | −17 s |
| 11 | The map of the series | 60 s | 53 s | −7 s |
| 12 | Close | 60 s | 42 s | −18 s |
| | **Total** | **20:00** | **16:03** | **−237 s** |

Sections deliberately short, where the picture carries the time: 2, 5, 6, 7, 8, 10, 12. Everywhere else the narration fills its slot.
<!-- /TIMING-TABLE -->

---

## Revision of 14 September 2026

The script of 10 September had been written against a project that had already moved under it, and the project has moved again since. What changed, and why:

| Section | Before | Now | Why |
|---|---|---|---|
| 0 | "thousands of dashboards with a broken red card, overnight" | HACS's real warning, and a card that still works with no maintainer | the thread the script cites shows the "Repository removed from HACS" warning and a reply "The bar-card still works" — no red card. The "beautiful ≠ maintained" point holds without the exaggeration |
| Whole script | pointers to "episode 2, 3, 6, 9, 12" | block codes (A2, D1, D2, D6, C4…) | the series was regrouped into four blocks on 12 September; the old numbers no longer exist |
| 4 | "no dependency on a community maintainer", "no more card-mod patches", exceptions `weather-forecast` · `logbook` · `apexcharts-card` | three named foundations (button-card, card-mod, layout-card), specialised cards, one card-mod patch owned up to | the templates hold 173 `custom:button-card`, 10 `grid-layout` and 95 `card_mod` blocks; `weather-forecast` is used nowhere (the weather goes through `dynamic-weather-card` and `simple-weather-card`). The old wording was false for anyone who opens the repository |
| 5 | "CORE / Room Engine / AI Layer / Animation / CSS / JS / Theme Engine" diagram | `Vision.md`'s system overview (§2), generation chain (§4), console loop (§5) | `Vision.md` was rewritten on 9 September; the old diagram is no longer in it |
| 6 | "HUD row: weather, clock, alarm status, avatar", "energy row", `vssp.css` as the source of the look | header band (screen + time, weather, calendar), status row (system, energy, alarm, thermostat, updates light), radar, metered devices, assistant; `design_system.yaml` + GRAPHIC TEMPLATE screen | that is what HOME shows today; since 13 September the typeface and text sizes are charter settings |
| 9 | "you'll come across old file names" | the 12 September sweep, its three bugs, and the two traces left | the old name was removed from the code on 12 September, except `OSVisionEngine` and CORE's K3s path |
| 10 | placeholder "[3-4 milestones, to be picked from Vision.md]" | five milestones written out | `Vision.md` has no changelog section any more |
| 7 | — | **new section**: the console, and a room declared live | move to the 20-minute format; it is the proof of "the interface is generated", section 3's thesis |
| 8 | — | **new section**: secure by default, four checkable measures and what is missing | move to the 20-minute format; the cold open promises security, nothing showed it |
| 11 | — | **new section**: the map of the four blocks (6 · 2 · 3 · 10 episodes of 20 min) | the series plan says the pilot "announces all of them"; the script did not |
| 12 | "the next episode follows a piece of data from psutil" | D1 offered as a way in, not as the mandatory next step | between blocks, order no longer matters |
| Length | 11-13 then 13-15 min | **20 min** | the format common to the whole series, decided on 14 September |
| Warning | "do not film: long-lived tokens" | secrets listed; no more long-lived token on tablets | since 14 September, the console pages borrow the tablet's Home Assistant session |
