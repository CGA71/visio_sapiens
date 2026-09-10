# EPISODE 1 — Vision & Architecture
## "Visio Sapiens: why I threw out the native Lovelace cards"

**Source doc:** `Vision.md`
**Central question of the episode:** Why replace Home Assistant's native Lovelace cards with an in-house engine?
**Visual anchor:** architecture diagram + live tour of the HOME dashboard
**Estimated length:** 11-13 min
**Shooting format:** no face on camera at any point. The channel runs on **voice-over + screen capture + hands-only shots** (keyboard, mouse, optionally a stylus on a tablet to annotate the diagram). Every "to camera" direction from earlier drafts is replaced below.

**Goal:** give viewers the mental model before any code. What Visio Sapiens is — a control-center-style interface sitting on top of Home Assistant, **not** a dashboard with a nice skin — and why the project refuses native Lovelace cards, save for documented exceptions (`weather-forecast`, `logbook`, `apexcharts-card`).

**⚠️ Do not film yet:** anything involving live secrets (Livebox password, long-lived tokens) — keep secret handling for episode 4 or 6.

---

## 0. COLD OPEN — THE DOUBLE PROBLEM (0:00 - 1:00)

**Visual:** montage of Reddit/HACS screenshots — gorgeous community dashboards, animations, custom gauges. No camera, screens only.

**Voice-over:**
> "I think these dashboards are beautiful. The Home Assistant community turns out cards that are genuinely stunning to look at."

**Visual (cut):** real capture of the community forum — the "Bar-Card Repo Removed in 2025.6.2" thread — then that same card showing red in a dashboard with "Custom element doesn't exist".

**Voice-over:**
> "Bar Card, one of the most widely used cards for animated energy bars, lost its repository on HACS in 2025 — no official maintainer left. The result: thousands of dashboards with a broken red card, overnight, with no warning to anyone. 'Beautiful' and 'maintained' are two different things."

**Visual (cut):** padlock icon in motion design, then a simple diagram — a house, an "Internet" arrow, a red question mark on the arrow.

**Voice-over:**
> "And there's a second problem, and this one is more serious: if you want to reach that dashboard from your phone when you're away from home, it has to be exposed to the internet. And it isn't just cards you're exposing — it's your personal data. Your presence patterns, your cameras, sometimes your locks. A poorly secured dashboard on a platform reachable from outside is an open door into your house."

**Animated title:** VISIO SAPIENS — Episode 1: Vision & Architecture

---

## 1. MY APPROACH: SIMPLE, EFFECTIVE, SECURE (1:00 - 2:30)

**Visual:** hands on keyboard/mouse, terminal or code editor blurred in the background. No face at any point.

**Voice-over:**
> "Faced with those two problems — maintenance that gives out, and security that gets neglected — I made one decision up front, and it's the one that defines the whole project: build something **simple and effective**, that ships with as much security as possible **by default**, not as an option you bolt on later if you happen to think of it.
>
> In practice that means: as few external dependencies I have no control over as possible, an architecture designed from day one to be exposed to the internet without that being a gamble, and an environment that lets me roll back cleanly when something breaks — because it will break, sooner or later, on any project.
>
> Concretely, that translates into a CI/CD setup that lets **one self-taught person** — not a DevOps team, just someone motivated — grow the product step by step, or simply **restore a previous version straight into HAOS** when an update goes wrong. We'll go deep on that pipeline in episode 6, but I wanted you to know, right here in episode 1, that this safety net exists and that it's part of the foundation, not a side feature."

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
> And that distinction has a very concrete consequence, one you'll see at work in every episode: the interface isn't assembled by hand, it's **generated**. You describe your home once — the language, the format, the rooms — and every screen is produced from that description, then kept in step as the home changes. Adding a room isn't drawing a new dashboard: it's declaring a room, and letting the generator do the rest. A dashboard you assemble by hand ages. A dashboard that's generated keeps up.
>
> And that leads to the single rule that drives absolutely every technical decision in this project, the one you'll meet again in every episode:
>
> **Home Assistant is nothing more than a data engine. The interface is driven entirely by VSSP.**"

**On-screen text (boxed):**
> 🧠 HA = data engine
> 🎛️ VSSP = the interface, all of it

---

## 4. WHY NOT THE NATIVE LOVELACE CARDS? (5:00 - 7:30)

**Visual:** split screen — native Lovelace editor with its standard cards on the left, the Visio Sapiens HOME dashboard on the right. Still no camera.

**Voice-over:**
> "So here's the question that comes up straight away: why not just use the native Lovelace cards? They exist, they're maintained by the Home Assistant core, they work perfectly well.
>
> Exactly — they work perfectly well **for what they are**: a system of stacked cards. But the moment you want a coherent visual identity, animations that respond in real time, a HUD that behaves like a real system interface rather than a grid of widgets, you hit Lovelace's glass ceiling.
>
> So the project made a radical call: **refuse the native Lovelace cards**, and build its own rendering engine on top. With three exceptions, deliberate and documented, because it would be stupid to reinvent what already works well: `weather-forecast`, `logbook`, and `apexcharts-card`.
>
> Everything else — the sidebar, the HUD, the gauges, the energy rows, the rooms — is the in-house engine, which **I** maintain, through the same CI/CD pipeline I mentioned a moment ago. No dependency on a community maintainer who can vanish overnight.
>
> Now let's be honest about the price of that choice, because there is one: by refusing the community cards, **I become the maintainer**. If a gauge breaks, nobody else is coming to fix it. That's a real cost, and I take it on for a precise reason: that cost is one I **control**. When a community card disappears, I control nothing — not the timing, not the decision, not the migration. A bug in my own engine, I can fix that same evening and ship it straight out.
>
> And there's a side effect I hadn't seen coming. Once you write your own engine, you stop piling up patches. The famous `card-mod`, with its CSS selectors reaching into the shadow DOM of a card you don't control — it works, sure, right up until the update that renames a class. At that point there's no patch left to write: there's CSS I wrote, sitting on HTML I produced."

**On-screen text (boxed):**
> ✅ Documented exceptions: `weather-forecast` · `logbook` · `apexcharts-card`
> 🔧 Everything else: VSSP engine, maintained in-house

---

## 5. THE ARCHITECTURE DIAGRAM (7:30 - 9:30)

**Visual:** full screen on the architecture diagram from `Vision.md`. Hands-only shot with stylus/graphics tablet highlighting each block in turn — this is the episode's only moment of "physical presence", limited to hands.

**Voice-over:**
> "Here's what the full architecture looks like. I'm showing it to you once, in full, because it's the mental map you'll need to follow every episode that comes after."

**Diagram walkthrough, block by block (highlighted in turn with the stylus):**

> "**CORE**: the system foundation — this is what exposes the metrics, the machine state, the thing everything else leans on. We'll come back to it in detail in episode 2.
>
> **Room Engine**: the logic that turns a room definition into an interface — the heart of the dashboard generator, episode 3.
>
> **AI Layer**: the layer that wires intelligence into the interface — the chatbot, the automations. Episode 9.
>
> **Animation Engine, CSS Engine, JS Engine, Theme Engine**: the four layers that give Visio Sapiens its visual identity and its behaviour — this is what makes a room feel like a living interface rather than a Lovelace card wearing a nice theme."

**Voice-over (walkthrough close):**
> "Take just one thing away from this diagram: every layer has one precise responsibility, and none of them does another one's job. That's what lets the project hold up over time instead of turning into a plate of YAML spaghetti — and it's also what makes the CI/CD pipeline possible: you can only version and restore cleanly what is structured in the first place."

---

## 6. LIVE TOUR OF THE HOME DASHBOARD (9:30 - 11:30)

**Visual:** live screen, mouse pointing at each element as the narration reaches it. No face.

**Voice-over:**
> "Enough theory, let's look at the result. This is HOME, the landing screen of Visio Sapiens."

**Pointing in turn (mouse cursor):**
> "The **sidebar** — navigation between the screens of the control center.
>
> The **HUD row** in the header: weather, clock, alarm status, avatar — everything you want to take in at a glance as you walk into the house.
>
> The **energy row** — production, consumption, what the house is doing right now, not a history you have to go digging for.
>
> The **room modules** — one screen per declared room, all produced by the same generator, from the same template. These aren't ten dashboards written ten times: it's one template, and ten rooms.
>
> And the **navigation rail**, here, which rebuilds itself when a room appears or disappears — because it's generated too, not maintained by hand in some corner of YAML that you always end up forgetting."

**Transition to the repo:**
> "And now the part I most enjoy showing, because it makes all of this concrete: the repository tree, live, side by side with what's on screen."

**Visual:** split screen — repo tree on the left (in a code editor such as VS Code), HOME dashboard on the right.

**Voice-over:**
> "This file — `www/vssp/css/vssp.css` — is **literally** what paints that screen. Not a metaphor: every colour, every bit of spacing you see on the right comes from that file on the left. That's what having an in-house engine means, rather than a theme laid over generic cards: the code and the interface speak the same language — and so they're versionable like a real software project.
>
> And if I change a colour here, on the left, it changes on the right at the next deployment. On every screen at once, because there's only one source. Not ten cards to touch up one by one, hoping you didn't miss any."

---

## 7. A NOTE ON NAMES (11:30 - 12:00)

**Visual:** capture of the Git history / old file names on screen (`osvision_v2/...`), voice-over alone, no hands shot needed here.

**Voice-over:**
> "A quick aside before we wrap up, because you're going to run into this in later episodes: the project was originally called **OSVision**, and was renamed to **VSSP**. You'll come across old file names and old paths dating from that era.
>
> I'm mentioning it now for a simple reason: a project's history leaves marks. A good project doesn't hide those marks, it documents them. You'll see this renaming scar again later, notably in the K3s bug in episode 2 — and now you'll know why it's there."

---

## 8. QUICK MONTAGE — CHANGELOG (12:00 - 12:30)

**Visual:** fast-cut montage, `Vision.md` changelog scrolling, screenshots cutting in time with the music. No camera, screens and music only.

**Voice-over (short, punchy):**
> "None of what you've just seen existed a few months ago. [quick list of 3-4 changelog milestones, to be picked from `Vision.md`]. This isn't a frozen project — it's a system with a history, and it's still writing one."

*(Prod note: this block can double as an alternative opener if the final edit wants a more energetic cold open.)*

---

## 9. TRANSITION TO EPISODE 2 (12:30 - 13:15)

**Visual:** back to the HOME dashboard full screen, or animated channel logo. Voice-over alone.

**Voice-over:**
> "What to take away from this episode: Visio Sapiens isn't a dashboard, it's a control center, built to be simple, effective and secure by default. Home Assistant supplies the data, VSSP supplies everything else — without depending on community cards that can give out without warning, and with a pipeline that lets you roll back when you need to, even self-taught.
>
> In the next episode we go down a level: we follow a single piece of data, from `psutil` on the host machine all the way to an SVG gauge in your browser, with DevTools open so you can watch every step go past.
>
> Subscribe, hit the bell, and tell me in the comments: does your Home Assistant install still look like a stack of Lovelace cards, or have you already started climbing out?
>
> See you very soon."

---

## PRODUCTION NOTES

- **Faceless format:** no shot to camera is to be filmed. The voice-over carries the whole narrative. The only "human presence" shots allowed are hands-only (keyboard, mouse, stylus on tablet to annotate the architecture diagram, section 5). Everything else is 100% screen capture, motion design, and on-screen text.
- **Voice recording:** plan a clean voice-over take, recorded separately from the screen capture, so it can be resynced easily in the edit.
- **Overall tone:** explanatory, and assertive on the "in-house engine vs native Lovelace" call and on security — that's the thesis of the episode, it should be argued clearly, not merely stated.
- **Through-line of the intro:** double problem (community maintenance giving out + unsecured internet exposure) → the project's answer (simple/effective/secure product + CI/CD restorable in HAOS) → HA's native complexity → simplification.
- **Architecture diagram:** to be redrawn at recording resolution before shooting.
- **B-roll:** community dashboards (before/after the break — capture of the "Bar-Card Repo Removed in 2025.6.2" forum thread), internet exposure diagram, native HA interface (complexity), live HOME dashboard, repo tree, `Vision.md` changelog.
- **Do not film:** any live secret (Livebox password, long-lived tokens) → episodes 4/6.
- **Cross-references:** CI/CD pipeline in detail in episode 6; K3s bug and the OSVision → VSSP scar in episode 2; security in depth in episode 12.

---

## NARRATION TIMING

Measured against the slots above, at 140 words per minute. The narration-only text, split by section, lives in `episode-01-narration.en.txt`.

| # | Section | Slot | Narration | Delta |
|---|---|---|---|---|
| 0 | Cold open | 60 s | 61 s | +1 s |
| 1 | My approach | 90 s | 86 s | −4 s |
| 2 | HA's complexity | 60 s | 39 s | −21 s |
| 3 | What Visio Sapiens is | 90 s | 87 s | −3 s |
| 4 | Why not native cards | 150 s | 153 s | +3 s |
| 5 | Architecture diagram | 120 s | 92 s | −28 s |
| 6 | Live dashboard tour | 120 s | 121 s | +1 s |
| 7 | A note on names | 30 s | 39 s | +9 s |
| 8 | Changelog montage | 30 s | 19 s | −11 s |
| 9 | Transition to episode 2 | 45 s | 58 s | +13 s |
| | **Total** | **13:15** | **12:36** | **−39 s** |

Section 5 runs deliberately short: the stylus walkthrough of the diagram carries the time visually. Section 8 is a music-led montage. Everywhere else the narration fills its slot.
