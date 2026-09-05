# Visio Sapiens — Chatbot integration (HOME card + ADMIN provider selector)

**English** · [Français](Chatbot_Integration.fr.md)

## Principle

The HOME dashboard's "Chatbot" card and the ADMIN console's GENERATION
provider selector (`input_select.vssp_chatbot_provider`) are wired to
**real** AI backends — Gemini, Claude, ChatGPT, or a self-hosted
("custom") model — instead of being static placeholders.

```
HOME chatbot bar (types + sends directly)      ADMIN "Custom" button (shown when custom is selected)
        │  window.vsspChatbot.send() (js/vssp.js)     │  tap_action: browser_mod.popup
        │  fetch()                                     ▼
        │                            /local/vssp/wizard/vssp_chatbot.html (iframe — chat UI or config form)
        │                                               │  POST (local_only webhook)
        ▼                                               ▼
                    packages/vssp_chatbot.yaml  automations
                            │  shell_command
                            ▼
        vssp/vssp_chatbot_send.py  ──HTTP──▶  Gemini / Claude / ChatGPT / your server
                            │  writes
                            ▼
        /config/www/vssp/chatbot_status.json   (polled by both the HOME bar and the iframe)
```

This follows the same shape as the THEME screen
(see [Design_System_Editor.md](Design_System_Editor.md)): a static HTML
page in an iframe talks to Home Assistant through a **local-only
webhook**, never through the REST API, because an iframe cannot reach
the parent page's `hass` object and a long-lived token has no business
sitting in a browser for this.

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
message history the single-turn HOME bar doesn't keep. The ADMIN
"custom" provider tile reuses the exact same popup mechanism, in a
config-form mode instead of a chat mode (`?mode=custom`).

**`browser_mod` is a HACS integration and is not installed by this
repository.** It must be installed once on the live pod
(HACS → Integrations → search "browser_mod" → Install → restart Home
Assistant) before the full-conversation popup (or the ADMIN "custom"
config popup) will open — the HOME bar's inline send/reply does not
need it at all.

**Verify on deploy** — this repo has no working `browser_mod` example to
copy the exact popup call from (nothing else in the project used it
before this feature). The `browser_mod.popup` call in `js/vssp.js`
(`openFullChat()`) and `admin.yaml.j2` (`browser_id: this`, `size:
normal`, `content: {type: iframe, url: ...}`) is written from
browser_mod's documented convention, but its accepted keys can vary by
version. If the popup does not open after installing browser_mod,
check the exact service schema under Developer Tools → Actions →
`browser_mod.popup` on the live instance and adjust accordingly.

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

The three placeholder logo SVGs
(`home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`)
that an earlier version of this feature added for the (since-reverted)
ADMIN logo-button row are back, but for a different consumer: the HOME
bar's leading badge (see above), not the ADMIN selector, which stays
untouched.

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

- The HOME bar keeps no conversation history at all (each message
  stands alone) and the chat popup keeps history in memory only —
  closing and reopening it starts a fresh conversation. Nothing is
  persisted server-side beyond the single latest exchange
  (`chatbot_status.json`), by design (there is no chat-history store in
  this project).
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
- `home-assistant/packages/vssp_chatbot.yaml` — the send webhook and
  the custom-config webhook.
- `vssp/vssp_chatbot_send.py` — calls the real provider API.
- `home-assistant/dashboards/templates_j2/home.yaml.j2` — the HOME
  chatbot bar ("Cadre 2").
- `home-assistant/www/vssp/js/vssp.js` — `VsspChatbotBar`
  (`window.vsspChatbot`): send/poll/mic/openFullChat for the HOME bar.
- `home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`
  — the HOME bar's per-provider badge.
- `home-assistant/dashboards/templates_j2/admin.yaml.j2` — the
  conditional "Custom" config button below the (unchanged) selector.
- `home-assistant/www/vssp/wizard/vssp_chatbot.html` — the full
  conversation popup's content (chat UI + config form).
