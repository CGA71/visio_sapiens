# Documentation — Visio Sapiens

**English** · [Français](README.fr.md)

Every document exists in both languages: `X.md` in English, `X.fr.md` in
French, side by side in the same directory, with a language switcher at the
top of each.

The four areas below answer four different questions. Pick by what you are
doing, not by what a file is called.

---

## `dashboards/` — the interface, and how it is generated

What a user sees, and the machinery that produces it.

| | |
|---|---|
| [Dashboard_Generator](dashboards/Dashboard_Generator.md) | the Jinja2 generator: model, slots, room grids, locale |
| [Design_System_Editor](dashboards/Design_System_Editor.md) | the ADMIN THEME screen and the design system it edits |
| [Core_Dashboard](dashboards/Core_Dashboard.md) | `core.html`, the system dashboard |
| [Chatbot_Integration](dashboards/Chatbot_Integration.md) | the HOME chat card and the ADMIN provider selector |
| [Google_Calendar](dashboards/Google_Calendar.md) | the Google Calendar screen and the header band |
| [AI_Assistant](dashboards/AI_Assistant.md) | **specification, not yet built** — voice diagnostics, guided repair |

## `platform/` — the foundation

Installing and running what the dashboards sit on. Read these when you are
setting the instance up, or when something below the interface is wrong.

| | |
|---|---|
| [Deployment](platform/Deployment.md) | deploying the device assignment feature, end to end |
| [Vault](platform/Vault.md) | the HashiCorp Vault safe: Docker on k3s, add-on on HAOS |
| [Security](platform/Security.md) | the honest posture: what is protected, what is not |
| [Backup_Retention](platform/Backup_Retention.md) | what writes backups, and what prunes them |
| [mosquitto-k3s](platform/mosquitto-k3s.md) | installing the MQTT broker on k3s *(French only)* |

## `ci-cd/` — the pipeline

| | |
|---|---|
| [CI_CD](ci-cd/CI_CD.md) | complete reference: stages, guards, variables |
| [Troubleshooting](ci-cd/Troubleshooting.md) | field postmortems and the ADMIN panel FAQ |

## `project/` — the project itself

| | |
|---|---|
| [Vision](project/Vision.md) | what this is for |
| [Integration_Case_Study](project/Integration_Case_Study.md) | integrating TECHNICAL ROOM into the repo |
| [YouTube_Series](project/YouTube_Series.md) | the series plan |
| [Manifest](project/Manifest.md) | ⚠ **stale** — a session deliverables list naming files that no longer exist, kept as history rather than guidance |

## `assets/`

Images referenced by the documents. `frame_dashboard.png` is currently
referenced by none of them.

---

## Conventions

- **Bilingual pairs.** `X.md` and `X.fr.md` always travel together and always
  live in the same directory, so the switcher at the top of each stays a plain
  sibling link.
- **Shipped behaviour, not plans.** Every document here describes what the code
  actually does. The one exception says so in its own first paragraph, in bold:
  `AI_Assistant`.
- **Links from code.** Comments in `.gitlab-ci.yml`, the packages and the Python
  tooling point at documents by full path (`docs/platform/Security.md`). Moving
  a document means updating those too — they are prose, but a pointer that no
  longer resolves is worse than no pointer.
