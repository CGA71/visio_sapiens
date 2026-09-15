# Visio Sapiens — Chatbot integration (HOME card + ADMIN provider selector)

**English** · [Français](Chatbot_Integration.fr.md)

## Principle

The HOME dashboard's "Chatbot" card and the ADMIN console's GENERATION
provider selector (`input_select.vssp_chatbot_provider`) are wired to
**real** AI backends — Gemini, Claude, ChatGPT, or a self-hosted
("custom") model — instead of being static placeholders.

```
HOME chatbot bar / full chat popup (vssp_chatbot.html)
        │  POST /api/webhook/vssp_chatbot_send (local_only, base64 checked)
        ▼
packages/vssp_chatbot.yaml
        ├─ 1st choice: the provider's Home Assistant integration
        │     conversation.process (agent of Anthropic / Google Gemini / OpenAI / Ollama)
        │     └─ shell_command.vssp_chatbot_reply ─▶ vssp_chatbot_send.py --agent (files the answer)
        └─ fallback: shell_command.vssp_chatbot_send ─▶ vssp_chatbot_send.py ──HTTP──▶ provider API
                                                         (key file, or the custom form's endpoint)
        ▼  writes
/config/www/vssp/chatbot_status.json   (polled by the HOME bar and the popup)

ADMIN > DASHBOARDS: pick a provider ──▶ AI setup popup (wizard/vssp_ai_setup.html)
                    or tap SET UP THE AI     guided install of that integration, live status
```

This follows the same shape as the THEME screen
(see [Design_System_Editor.md](Design_System_Editor.md)): a static HTML
page in an iframe talks to Home Assistant through a **local-only
webhook**, never with a long-lived token in the browser.

## Setting up a provider — the AI setup popup

Picking a provider in the ADMIN > DASHBOARDS dropdown opens its guided
setup at once, in a `browser_mod` popup
(`home-assistant/www/vssp/wizard/vssp_ai_setup.html`). The **SET UP THE
AI** button under the dropdown opens the same popup for the current
choice, to come back to it later.

Each provider is set up through **Home Assistant's own integration**,
not a key typed into Visio Sapiens:

| Choice | Integration | API key from |
|---|---|---|
| Claude | Anthropic (`anthropic`) | console.anthropic.com › API Keys (API credits needed — Claude Pro does not include the API) |
| Gemini | Google Gemini (`google_generative_ai_conversation`) | aistudio.google.com › Get API key |
| ChatGPT | OpenAI (`openai_conversation`) | platform.openai.com › API keys (API credits needed — ChatGPT Plus does not include the API) |
| Custom | Ollama (`ollama`), a model running in the house | no key: the Ollama server's URL |

The popup walks through four steps: get the key, add the integration,
choose the model (the gear of the **Conversation agent**, untick
**Recommended model settings**; tick **Assist** under **Control Home
Assistant** to let it control devices), and, optionally, make it the
default agent in **Settings › Voice assistants**. Each step has a
button that opens the right Home Assistant screen (the add-integration
dialog directly, via `/config/integrations/dashboard/add?domain=…`),
and a live check read from the tablet's own session — installed or not,
agent entity, model, default Assist agent. The page only reads
(`config_entries/get`, the entity and device registries,
`assist_pipeline/pipeline/list`).

"Custom" also links to the older form for any other OpenAI-compatible
server (LM Studio, text-generation-webui, vLLM…), which Home Assistant
has no integration for.

**Why the dropdown opens it on its own:** the tile's `select-options`
feature cannot run code. `VsspAiSetup` in `js/vssp.js` watches
`input_select.vssp_chatbot_provider` and opens the popup when it
changes, **by the signed-in user** (`context.user_id`), **while this
screen shows ADMIN > DASHBOARDS**. A change made by an automation (the
custom form's own save) or on another tablet opens nothing.

## Which path answers a message

1. **The provider's integration, when it is installed** — the webhook
   automation finds its `conversation.*` entity
   (`integration_entities`) and calls `conversation.process`. The key
   stays in Home Assistant; the agent keeps the conversation under a
   `conversation_id` that the status file hands back to the full chat
   popup, which sends it with the next message. For "custom", the form's
   endpoint, when filled in, comes before Ollama.
2. **Otherwise, the fallback** — `vssp_chatbot_send.py` calls the
   provider's API with the key saved in Visio Sapiens (see
   [Secrets](#secrets)), or the custom form's endpoint.

The CORE SCAN follows the same preference: the AI task
(`ai_task.*`) of the selected provider's integration first, then any
other one.

## The HOME bar — real input, no popup to send

The HOME chatbot card (`home.yaml.j2`, "Cadre 2") is a real, typable
`<input>` plus mic and send icons, rendered by a `custom:button-card`
`custom_fields` template. Since that raw HTML cannot carry a working
`<script>` (a browser never executes one inserted via `innerHTML`),
the input/mic/send elements call plain global functions
(`window.vsspChatbot.*`) through inline `onclick`/`onkeydown`
attributes. Those functions live in `home-assistant/www/vssp/js/vssp.js`
— loaded once as a Lovelace resource (`type: module`, already declared
in `config-fragment.yaml`) — and run in the top-level frontend, not a
sandboxed iframe, which is what lets them call `hass.callService(...)`
directly.

Sending: `window.vsspChatbot.send()` posts straight to the
`/api/webhook/vssp_chatbot_send` webhook and polls
`chatbot_status.json`, exactly like `vssp_chatbot.html` does — no popup
is involved. The reply (or error) shows in a small floating bubble
anchored under the input (`position: fixed`, appended to `<body>` so a
card re-render can't wipe it mid-poll). The card's `entity:` is
`input_select.vssp_chatbot_provider`, so the leading badge — each
provider's logo, or a generic icon for "custom" — only re-renders (and
only then risks resetting whatever is mid-typing) when the active
provider actually changes, not on unrelated Home Assistant state
updates.

Voice input uses the browser's Web Speech API
(`webkitSpeechRecognition`) to fill the input with the transcript; it
does not auto-send, same as typing by hand. Chromium-only — browsers
without it get a small "not available" bubble instead of a silent
failure.

Tapping the **leading provider badge**, not the input, is what still
opens the full conversation popup (`vssp_chatbot.html?mode=chat` via
[browser_mod](https://github.com/thomasloven/hass-browser_mod)) — for
message history the single-turn HOME bar doesn't keep.

**`browser_mod` is a HACS integration and is not installed by this
repository.** It must be installed once on the live pod (HACS →
Integrations → search "browser_mod" → Install → restart Home Assistant)
before the popups (full conversation, AI setup) will open — the HOME
bar's inline send/reply does not need it at all.

**How the popups are opened** — never with a backend service call:
`browser_id: this` only means something to the frontend, so a
`hass.callService('browser_mod', 'popup', {browser_id: 'this'})`
reaches a server that cannot tell which browser "this" is, reports
success and opens nothing. From JavaScript, `js/vssp.js` calls
browser_mod's frontend service (`window.browser_mod.service('popup',
…)`, no `browser_id`: this screen); from a dashboard,
`tap_action: fire-dom-event` with a `browser_mod:` block. Checked on
browser_mod 3.2.3.

## Provider selector — visual unchanged

`input_select.vssp_chatbot_provider` (`gemini` / `claude` / `chatgpt` /
`custom`, `packages/vssp_generation.yaml`) still renders exactly as
before: a `type: tile` + `select-options` feature, plain text options,
same `card_mod` background as the language/format selectors next to it
(`admin.yaml.j2`). An earlier version of this feature replaced it with
a row of logo buttons; that was reverted at the user's request — the
selector's look was intentionally left untouched.

What *is* new: picking an option opens its AI setup popup, and a
**SET UP THE AI** button below the selector row reopens it (see
[Setting up a provider](#setting-up-a-provider--the-ai-setup-popup)).
It replaces the former "Custom" button, shown only for `custom`: the
custom form is now reached from the Custom setup popup.

The three placeholder logo SVGs
(`home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`)
that an earlier version of this feature added for the (since-reverted)
ADMIN logo-button row are back, but for a different consumer: the HOME
bar's leading badge (see above), not the ADMIN selector, which stays
untouched.

## Secrets

With the integration path, the key lives in Home Assistant's own config
entry, typed into its native form — Visio Sapiens never sees it. The
helpers below only serve the fallback path.

Same convention as the existing `input_text.vssp_ha_token`
(`packages/vssp_admin.yaml`): each API key is a
`mode: password` `input_text` helper, written by a
`shell_command.vssp_write_<provider>_key` to a gitignored file under
`/config/vssp/`, never passed as a CLI argument or exposed to a
browser. Run `script.vssp_save_<provider>_key` once after pasting a key
(and again each time you change it):

| Provider | Helper | Save script |
|---|---|---|
| Gemini | `input_text.vssp_gemini_api_key` | `script.vssp_save_gemini_key` |
| Claude | `input_text.vssp_claude_api_key` | `script.vssp_save_claude_key` |
| ChatGPT | `input_text.vssp_chatgpt_api_key` | `script.vssp_save_chatgpt_key` |
| Custom | `input_text.vssp_chatbot_custom_api_key` (optional) | handled automatically by the config popup's Save |

The model used per provider is also an editable `input_text`
(`vssp_gemini_model`, `vssp_claude_model`, `vssp_chatgpt_model`), so
switching models needs no code change — just edit the helper.

## The "custom" provider's contract

A self-hosted endpoint must speak an OpenAI-compatible
`POST /chat/completions` (`{"model", "messages":[...]}` →
`{"choices":[{"message":{"content": "..."}}]}`) — the common contract
exposed by Ollama, LM Studio and text-generation-webui in "OpenAI API"
mode. A server speaking a different protocol is not supported without
editing `build_custom_request()`/`parse_custom_response()` in
`vssp/vssp_chatbot_send.py`.

## Known v1 limitations

- The HOME bar keeps no conversation history at all (each message
  stands alone). The chat popup keeps its conversation until it is
  closed: through the agent's `conversation_id` on the integration
  path, in memory on the fallback path. Nothing is persisted by Visio
  Sapiens beyond the single latest exchange (`chatbot_status.json`).
- One status file for the whole house: two tablets sending at the same
  second can read each other's answer.
- The custom-model config form always opens blank; it does not
  pre-fill from the currently saved values. Re-check
  `input_text.vssp_chatbot_custom_*` in Developer Tools → States if you
  need to see what is currently saved.
- The mic icon inside the full-conversation popup (`vssp_chatbot.html`)
  is still decorative — only the HOME bar's mic is wired to the Web
  Speech API so far.

## Files

- `home-assistant/packages/vssp_admin.yaml` — API key / model helpers,
  key-writing `shell_command`s, save scripts.
- `home-assistant/packages/vssp_chatbot.yaml` — the send webhook
  (integration agent first, then the fallback) and the custom-config
  webhook.
- `vssp/vssp_chatbot_send.py` — files the integration agent's answer
  (`--agent`), or calls the provider API itself (fallback).
- `home-assistant/www/vssp/wizard/vssp_ai_setup.html` — the AI setup
  popup, one guided setup per provider.
- `home-assistant/dashboards/templates_j2/home.yaml.j2` — the HOME
  chatbot bar ("Cadre 2").
- `home-assistant/www/vssp/js/vssp.js` — `VsspChatbotBar`
  (`window.vsspChatbot`): send/poll/mic/openFullChat for the HOME bar;
  `VsspAiSetup` (`window.vsspAiSetup`): opens the AI setup popup when the
  provider changes.
- `home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`
  — the HOME bar's per-provider badge.
- `home-assistant/dashboards/templates_j2/admin.yaml.j2` — the SET UP
  THE AI button below the (unchanged) selector.
- `home-assistant/www/vssp/wizard/vssp_chatbot.html` — the full
  conversation popup's content (chat UI + config form).
