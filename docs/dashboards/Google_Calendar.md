# Visio Sapiens — Google Calendar (ADMIN screen + header)

**English** · [Français](Google_Calendar.fr.md)

## Principle

The ADMIN console's **GOOGLE CALENDAR** screen replaces Home Assistant's
manual setup path (*Settings > Devices & services > Application
credentials*, then *Add integration > Google Calendar*), and then picks
which calendar the header of every dashboard shows.

```
GOOGLE CALENDAR screen (ADMIN console)
        │  iframe: /local/vssp/wizard/vssp_google.html
        │  POST (local_only webhook) → vssp_google_config
        ▼
packages/vssp_google.yaml  automation + scripts
        │  shell_command
        ▼
vssp/vssp_google_setup.py
        ├── websocket  ──▶ application_credentials/list + /create   (registers the OAuth client)
        ├── REST       ──▶ /api/config/config_entries/flow          (starts the flow, returns the consent URL)
        └── REST       ──▶ /api/states                              (lists calendar.* entities)
        │  writes
        ▼
/config/www/vssp/google_status.json   (read by the iframe and by 3 command_line sensors)
```

## What is automated, and what cannot be

| Step | Where | Automated? |
|---|---|---|
| Google Cloud project, enabling the Calendar API, consent screen, creating the OAuth client ID | Google Cloud Console | **No** — outside Home Assistant's reach |
| Registering the OAuth client in Home Assistant | `application_credentials/create` | **Yes** |
| Starting the `google` config flow | config-flow REST API | **Yes** |
| **Google consent click** | browser | **No — impossible by design** |
| Detecting the resulting `calendar.*` entities | `/api/states` | **Yes** |
| Feeding the calendar into the header | `--calendar-entity` at generate time | **Yes** |

The OAuth consent cannot be removed: OAuth exists precisely so the
account owner approves access in Google's own UI. The form therefore
ends by showing an **Authorize with Google** button; everything around
it is automated.

## Google-side prerequisites (once)

1. [Google Cloud Console](https://console.cloud.google.com/) → create a
   project, then enable **Google Calendar API**.
2. OAuth consent screen: type `External`, then **publish** the app —
   otherwise the credentials expire after 7 days.
3. *Credentials* → create an **OAuth client ID**, type
   **Web application**.
4. Paste this authorized redirect URI into it, **exactly**:

   ```
   https://my.home-assistant.io/redirect/oauth
   ```

The form shows that URI in a light grey chip with a **Copy** button
next to it — it is the one value on the screen you copy *out* rather
than type in, so it is styled as a token instead of as a form field.

Official documentation:
<https://www.home-assistant.io/integrations/google/>

## Usage

1. ADMIN console → **GOOGLE CALENDAR**.
2. Paste the **client ID** and **client secret**, then
   *Save & connect*.
3. Click **Authorize with Google** and approve with the account that
   owns the calendar.
4. Click **REFRESH**: the `calendar.*` entities appear.
5. Pick the calendar you want, then **Use for the header**.
6. **APPLY TO HEADER** (regenerates HOME) so the header shows it.

(Button labels above are the English ones — the screen follows the
interface language, see below.)

## Interface language

This screen is assembled from three sources that each used to decide the
language on their own, which is how it ended up showing French and
English side by side on one page. All three now follow
`input_select.vssp_language`:

| Part of the screen | Language comes from | Mechanism |
|---|---|---|
| Console labels, buttons, nav (`admin.google_*`) | the generated locale | `t()` + `locales/<code>.yaml`, as everywhere else |
| The embedded form (`vssp_google.html`) | `?lang=` in the iframe URL | written by `admin.yaml.j2` from `{{ locale }}`, resolved by the page's `I18N` table |
| Status sentences (`sensor.vssp_google_message`, the form's status line) | `--locale` given to `vssp_google_setup.py` | `MESSAGES` / `STATE_LABELS` tables in the script |

The status file carries **both** forms of each message:

```json
{
  "state": "awaiting_consent",
  "state_label": "Consent required",
  "message_key": "awaiting_consent",
  "message_vars": {},
  "message": "Open the Google consent link to finish linking the account."
}
```

- `state` stays an untranslated machine token — it is what the form
  branches on. Only `state_label` is translated.
- `message` is rendered by the script in `--locale`, because a
  `command_line` sensor cannot translate anything by itself.
- `message_key` + `message_vars` let the form re-render the same sentence
  in **its** language, so a status file written by a run in the other
  language still displays correctly.
- Technical failure text (an HTTP body, a socket error) is never
  translated: it travels in `message_vars` and is framed by a translated
  sentence.

Two consequences worth knowing:

- **Changing the language needs a regeneration**, like everywhere else in
  the project: the `?lang=` parameter is baked into the dashboard YAML at
  generate time. APPLY LANGUAGE already does this.
- **`sensor.vssp_google_calendars` has no unit**. `unit_of_measurement`
  is not templatable, so any word there would be hardcoded in one
  language next to a label translated into the other. The row label
  ("Calendars found" / "Calendriers détectés") carries the meaning.

## Where the values live

| Data | Location | Note |
|---|---|---|
| OAuth client ID | `input_text.vssp_google_client_id` | public by design (it travels in the consent URL) |
| Client secret | `input_text.vssp_google_client_secret` → `/config/vssp/.google_client_secret` (0600) | **never** passed on a command line, same convention as `vssp_ha_token` and the chatbot keys |
| Header calendar | `input_text.vssp_google_calendar_entity` | passed to the generator through `--calendar-entity` |
| Model default | `house.calendar_entity` (`model/house.yaml`) | used when the flag is absent |
| Setup state | `/config/www/vssp/google_status.json` | read by `sensor.vssp_google_state` / `_message` / `_calendars` |

Header precedence:
`--calendar-entity` > `house.calendar_entity` > `calendar.calebar`
(the historical hardcoded default, kept so a model predating that key
still renders). An empty or `unknown` value — an `input_text` that was
never filled reads as `unknown` — never wins over the model.

## Implementation notes worth knowing

- **Why a hand-rolled websocket client** (`MiniWS` in
  `vssp_google_setup.py`): `application_credentials` exposes **no** REST
  endpoint; its CRUD commands are generated by Home Assistant's
  collection helper (`DictStorageCollectionWebsocket`, api prefix
  `application_credentials`), so they are websocket-only. Rather than add
  a dependency to the pod, the script speaks the few RFC 6455 frames it
  needs.
- **Admin token required**: the collection is registered with
  `admin_only=True`, so `input_text.vssp_ha_token` must hold a token from
  an administrator account.
- **A credential cannot be edited**: Home Assistant declares
  `UPDATE_FIELDS = {}`. Fixing a mistyped client ID therefore leaves the
  old credential in place and adds a second one, at which point the
  config flow asks which implementation to use. The script answers with
  **ours** (it keeps the `id` returned by `/list` or `/create`) instead
  of the first in the list, which would be the stale one.
- **The header is not dynamic**: the calendar entity is baked into the
  dashboard YAML at generate time. Changing calendars therefore requires
  a regeneration — that is what the **APPLY TO HEADER** button does
  (`vssp_regenerate_home_dashboard` script, HOME being the protected
  dashboard).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `state: error`, "token missing" | `input_text.vssp_ha_token` empty, or *SAVE TOKEN* never run |
| auth refused | non-admin token, or expired |
| Config flow aborted: `missing_credentials` | registering the OAuth client failed before the flow |
| `already_configured` | Google Calendar is already linked — nothing to do |
| The consent link leads nowhere | redirect URI missing or different on the Google side |
| No calendar after consenting | click **REFRESH** (sensors only rescan every 30 s) |
| Header still shows the old calendar | regenerate: **APPLY TO HEADER** |
| The form is in a different language than the labels around it | the dashboard was generated before `?lang=` existed, or the language was changed without regenerating — run APPLY LANGUAGE |
| A status line stays in the previous language | it was written by an earlier run; press **CONNECT** or **REFRESH** to rewrite `google_status.json` |

## Files

| File | Role |
|---|---|
| `vssp/vssp_google_setup.py` | websocket + REST client, writes `google_status.json` |
| `home-assistant/packages/vssp_google.yaml` | helpers, shell_commands, sensors, scripts, webhook |
| `home-assistant/www/vssp/wizard/vssp_google.html` | the form (iframe) |
| `home-assistant/dashboards/templates_j2/admin.yaml.j2` | GOOGLE CALENDAR screen, passes `?lang=` to the iframe |
| `home-assistant/dashboards/locales/{en,fr}.yaml` | `admin.google_*` labels of the screen |
| `home-assistant/dashboards/templates_j2/_header.j2` | header agenda cell |
| `vssp/generate_dashboards.py` | `--calendar-entity` option |
