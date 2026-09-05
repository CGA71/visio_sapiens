# Visio Sapiens — Chatbot integration (HOME card + ADMIN provider selector)

**English** · [Français](Chatbot_Integration.fr.md)

## Principle

The HOME dashboard's "Chatbot" card and the ADMIN console's GENERATION
provider selector (`input_select.vssp_chatbot_provider`) are wired to
**real** AI backends — Gemini, Claude, ChatGPT, or a self-hosted
("custom") model — instead of being static placeholders.

```
HOME chatbot card / ADMIN "Custom" button (shown when custom is selected)
        │  tap_action: browser_mod.popup
        ▼
/local/vssp/wizard/vssp_chatbot.html   (iframe — real chat UI or config form)
        │  POST (local_only webhook)
        ▼
packages/vssp_chatbot.yaml  automations
        │  shell_command
        ▼
vssp/vssp_chatbot_send.py  ──HTTP──▶  Gemini / Claude / ChatGPT / your server
        │  writes
        ▼
/config/www/vssp/chatbot_status.json   (polled by the iframe)
```

This follows the same shape as the THEME screen
(see [Design_System_Editor.md](Design_System_Editor.md)): a static HTML
page in an iframe talks to Home Assistant through a **local-only
webhook**, never through the REST API, because an iframe cannot reach
the parent page's `hass` object and a long-lived token has no business
sitting in a browser for this.

## Why a popup, not an on-card input field

The HOME chatbot card has a fixed size (the right column of the HOME
grid) that must not change. `custom:button-card`'s `custom_fields`
cannot host a real, typable `<input>` — so the card itself
(`home.yaml.j2`, "Cadre 2") is only a **static visual trigger** styled
to look like a chat app's own input bar (icon / greyed placeholder /
mic / send). Tapping anywhere on it opens a
[browser_mod](https://github.com/thomasloven/hass-browser_mod) popup
whose content is `vssp_chatbot.html` in an iframe — that page has the
real input, the message list and the send button. The same popup
mechanism is reused by the ADMIN "custom" provider tile, in a
config-form mode instead of a chat mode (`?mode=custom`).

**`browser_mod` is a HACS integration and is not installed by this
repository.** It must be installed once on the live pod
(HACS → Integrations → search "browser_mod" → Install → restart Home
Assistant) before either popup will open. Nothing else in this feature
depends on it — the rest of the wiring (secrets, the webhook
automations, the provider tabs) works regardless.

**Verify on deploy** — this repo has no working `browser_mod` example to
copy the exact popup call from (nothing else in the project used it
before this feature). The `browser_mod.popup` call in `home.yaml.j2`
and `admin.yaml.j2` (`browser_id: this`, `size: normal`, `content:
{type: iframe, url: ...}`) is written from browser_mod's documented
convention, but its accepted keys can vary by version. If the popup
does not open after installing browser_mod, check the exact service
schema under Developer Tools → Actions → `browser_mod.popup` on the
live instance and adjust the two `tap_action` blocks accordingly.

## Provider selector — visual unchanged

`input_select.vssp_chatbot_provider` (`gemini` / `claude` / `chatgpt` /
`custom`, `packages/vssp_generation.yaml`) still renders exactly as
before: a `type: tile` + `select-options` feature, plain text options,
same `card_mod` background as the language/format selectors next to it
(`admin.yaml.j2`). An earlier version of this feature replaced it with
a row of logo buttons; that was reverted at the user's request — the
selector's look was intentionally left untouched.

What *is* new: a small **"Custom" button appears below the selector
row, only when `custom` is the selected option** (`type: conditional`,
same pattern as the CREATE/REGENERATE HOME buttons in
`system_dashboards.yaml`). Tapping it opens the same config popup as
before, for the local/self-hosted model's fields.

## Secrets

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

- The chat popup keeps conversation history in memory only — closing
  and reopening it starts a fresh conversation. Nothing is persisted
  server-side beyond the single latest exchange
  (`chatbot_status.json`), by design (there is no chat-history store in
  this project).
- The custom-model config form always opens blank; it does not
  pre-fill from the currently saved values. Re-check
  `input_text.vssp_chatbot_custom_*` in Developer Tools → States if you
  need to see what is currently saved.
- No microphone input yet — the mic icon in both the card and the
  popup is decorative.

## Files

- `home-assistant/packages/vssp_admin.yaml` — API key / model helpers,
  key-writing `shell_command`s, save scripts.
- `home-assistant/packages/vssp_chatbot.yaml` — the send webhook and
  the custom-config webhook.
- `vssp/vssp_chatbot_send.py` — calls the real provider API.
- `home-assistant/dashboards/templates_j2/home.yaml.j2` — the HOME
  chatbot card ("Cadre 2").
- `home-assistant/dashboards/templates_j2/admin.yaml.j2` — the
  conditional "Custom" config button below the (unchanged) selector.
- `home-assistant/www/vssp/wizard/vssp_chatbot.html` — the popup's
  content (chat UI + config form).
