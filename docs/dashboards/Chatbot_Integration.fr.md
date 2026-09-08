# Visio Sapiens — Intégration chatbot (carte HOME + sélecteur ADMIN)

**Français** · [English](Chatbot_Integration.md)

## Principe

La carte « Chatbot » du dashboard HOME et le sélecteur de fournisseur
du panneau GENERATION de l'ADMIN (`input_select.vssp_chatbot_provider`)
sont désormais branchés à de **vrais** backends IA — Gemini, Claude,
ChatGPT, ou un modèle auto-hébergé (« custom ») — au lieu d'être de
simples cadres d'accueil.

```
Barre Chatbot HOME (saisit + envoie directement)   Bouton "Custom" de l'ADMIN (si custom est sélectionné)
        │  window.vsspChatbot.send() (js/vssp.js)          │  tap_action : browser_mod.popup
        │  fetch()                                          ▼
        │                        /local/vssp/wizard/vssp_chatbot.html (iframe — chat ou formulaire)
        │                                                    │  POST (webhook local_only)
        ▼                                                    ▼
                    packages/vssp_chatbot.yaml  automatisations
                            │  shell_command
                            ▼
        vssp/vssp_chatbot_send.py  ──HTTP──▶  Gemini / Claude / ChatGPT / votre serveur
                            │  écrit
                            ▼
        /config/www/vssp/chatbot_status.json   (interrogé par la barre HOME et par l'iframe)
```

Même forme que l'écran THEME
(voir [Design_System_Editor.md](Design_System_Editor.fr.md)) : une page
HTML statique dans une iframe parle à Home Assistant via un **webhook
local uniquement**, jamais via l'API REST, car une iframe ne peut pas
atteindre l'objet `hass` de la page parente, et un jeton longue durée
n'a rien à faire dans un navigateur pour cela.

## La barre HOME — vraie saisie, aucun popup pour envoyer

La carte Chatbot de HOME (`home.yaml.j2`, « Cadre 2 ») est un vrai
`<input>` saisissable, plus des icônes micro et envoi, rendus par un
template `custom_fields` de `custom:button-card`. Comme ce HTML brut ne
peut pas porter de `<script>` qui s'exécute (un navigateur n'exécute
jamais un `<script>` inséré via `innerHTML`), les éléments
input/micro/envoi appellent de simples fonctions globales
(`window.vsspChatbot.*`) via des attributs `onclick`/`onkeydown` en
ligne. Ces fonctions vivent dans
`home-assistant/www/vssp/js/vssp.js` — chargé une fois comme ressource
Lovelace (`type: module`, déjà déclaré dans `config-fragment.yaml`) —
et s'exécutent dans le frontend de premier niveau, pas dans une iframe
sandboxée, ce qui leur permet d'appeler `hass.callService(...)`
directement.

Envoi : `window.vsspChatbot.send()` poste directement au webhook
`/api/webhook/vssp_chatbot_send` et interroge `chatbot_status.json`,
exactement comme le fait `vssp_chatbot.html` — aucun popup n'est
impliqué. La réponse (ou l'erreur) s'affiche dans une petite bulle
flottante ancrée sous le champ (`position: fixed`, ajoutée à `<body>`
pour qu'un re-rendu de la carte ne puisse pas l'effacer en cours
d'interrogation). Le `entity:` de la carte est
`input_select.vssp_chatbot_provider`, donc le badge de tête — le logo
de chaque fournisseur, ou une icône générique pour « custom » — ne se
re-rend (et ne risque d'effacer une saisie en cours) que lorsque le
fournisseur actif change réellement, pas à chaque mise à jour d'état
Home Assistant sans rapport.

La saisie vocale utilise la Web Speech API du navigateur
(`webkitSpeechRecognition`) pour remplir le champ avec la
transcription ; elle n'envoie pas automatiquement, comme une saisie
manuelle. Chromium uniquement — les navigateurs sans cette API
affichent une petite bulle « non disponible » plutôt qu'un échec
silencieux.

Taper le **badge de fournisseur en tête**, pas le champ de saisie, est
ce qui ouvre encore le popup de conversation complète
(`vssp_chatbot.html?mode=chat` via
[browser_mod](https://github.com/thomasloven/hass-browser_mod)) — pour
l'historique de messages que la barre HOME (un tour à la fois) ne
garde pas. La tuile fournisseur « custom » de l'ADMIN réutilise
exactement le même mécanisme de popup, en mode formulaire de
configuration plutôt qu'en mode chat (`?mode=custom`).

**`browser_mod` est une intégration HACS et n'est pas installée par ce
dépôt.** Elle doit être installée une fois sur le pod en production
(HACS → Intégrations → rechercher « browser_mod » → Installer →
redémarrer Home Assistant) avant que le popup de conversation complète
(ou le popup de configuration « custom » de l'ADMIN) ne s'ouvre — la
saisie/réponse en ligne de la barre HOME n'en a besoin en rien.

**À vérifier au déploiement** — ce dépôt n'a aucun exemple `browser_mod`
fonctionnel dont copier l'appel exact du popup (rien d'autre dans le
projet ne l'utilisait avant cette fonctionnalité). L'appel
`browser_mod.popup` dans `js/vssp.js` (`openFullChat()`) et
`admin.yaml.j2` (`browser_id: this`, `size: normal`, `content: {type:
iframe, url: ...}`) est écrit d'après la convention documentée de
browser_mod, mais les clés acceptées peuvent varier selon la version.
Si le popup ne s'ouvre pas après avoir installé browser_mod, vérifiez
le schéma exact du service sous Outils de développement > Actions >
`browser_mod.popup` sur l'instance en production et ajustez en
conséquence.

## Sélecteur de fournisseur — visuel inchangé

`input_select.vssp_chatbot_provider` (`gemini` / `claude` / `chatgpt` /
`custom`, `packages/vssp_generation.yaml`) se rend exactement comme
avant : un `type: tile` + fonctionnalité `select-options`, options en
texte brut, même `card_mod` de fond que les sélecteurs langue/format
juste à côté (`admin.yaml.j2`). Une version précédente de cette
fonctionnalité l'avait remplacé par une ligne de boutons-logos ; c'est
revenu en arrière à la demande de l'utilisateur — le visuel du
sélecteur a été volontairement laissé intact.

Ce qui est nouveau : un petit **bouton « Custom » apparaît sous la
ligne du sélecteur, uniquement quand « custom » est l'option
sélectionnée** (`type: conditional`, même motif que les boutons
CRÉER/RÉGÉNÉRER HOME de `system_dashboards.yaml`). Le taper ouvre le
même popup de configuration qu'avant, pour les champs du modèle
local/auto-hébergé.

Les trois SVG de logo provisoires
(`home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`)
qu'une version précédente de cette fonctionnalité avait ajoutés pour la
ligne de boutons-logos de l'ADMIN (depuis revenue en arrière) sont de
retour, mais pour un autre consommateur : le badge de tête de la barre
HOME (voir plus haut), pas le sélecteur de l'ADMIN, qui reste
inchangé.

## Secrets

Même convention que l'`input_text.vssp_ha_token` existant
(`packages/vssp_admin.yaml`) : chaque clé API est un helper
`input_text` en `mode: password`, écrit par un
`shell_command.vssp_write_<provider>_key` dans un fichier gitignoré
sous `/config/vssp/`, jamais passé en argument de ligne de commande ni
exposé à un navigateur. Lancez `script.vssp_save_<provider>_key` une
fois après avoir collé une clé (et à nouveau à chaque changement) :

| Fournisseur | Helper | Script d'enregistrement |
|---|---|---|
| Gemini | `input_text.vssp_gemini_api_key` | `script.vssp_save_gemini_key` |
| Claude | `input_text.vssp_claude_api_key` | `script.vssp_save_claude_key` |
| ChatGPT | `input_text.vssp_chatgpt_api_key` | `script.vssp_save_chatgpt_key` |
| Custom | `input_text.vssp_chatbot_custom_api_key` (optionnelle) | gérée automatiquement par l'Enregistrer du popup |

Le modèle utilisé par fournisseur est aussi un `input_text`
modifiable (`vssp_gemini_model`, `vssp_claude_model`,
`vssp_chatgpt_model`), donc changer de modèle ne demande aucune
modification de code — juste éditer le helper.

## Le contrat du fournisseur « custom »

Un point d'accès auto-hébergé doit parler un protocole compatible
OpenAI, `POST /chat/completions` (`{"model", "messages":[...]}` →
`{"choices":[{"message":{"content": "..."}}]}`) — le contrat le plus
courant exposé par Ollama, LM Studio et text-generation-webui en mode
« OpenAI API ». Un serveur parlant un protocole different n'est pas
pris en charge sans modifier
`build_custom_request()`/`parse_custom_response()` dans
`vssp/vssp_chatbot_send.py`.

## Limites connues de cette v1

- La barre HOME ne garde aucun historique de conversation (chaque
  message est isolé) et le popup de chat garde l'historique en mémoire
  uniquement — le fermer puis le rouvrir démarre une conversation
  neuve. Rien n'est persisté côté serveur au-delà du dernier échange
  (`chatbot_status.json`), par conception (ce projet n'a pas de
  stockage d'historique de chat).
- Le formulaire de configuration du modèle custom s'ouvre toujours
  vide ; il ne se pré-remplit pas depuis les valeurs déjà
  enregistrées. Consultez
  `input_text.vssp_chatbot_custom_*` dans Outils de développement >
  États si vous devez voir ce qui est actuellement enregistré.
- L'icône micro du popup de conversation complète
  (`vssp_chatbot.html`) reste décorative — seul le micro de la barre
  HOME est câblé à la Web Speech API pour l'instant.

## Fichiers

- `home-assistant/packages/vssp_admin.yaml` — helpers clé API/modèle,
  `shell_command` d'écriture des clés, scripts d'enregistrement.
- `home-assistant/packages/vssp_chatbot.yaml` — le webhook d'envoi et
  le webhook de configuration custom.
- `vssp/vssp_chatbot_send.py` — appelle la vraie API du fournisseur.
- `home-assistant/dashboards/templates_j2/home.yaml.j2` — la barre
  Chatbot de HOME (« Cadre 2 »).
- `home-assistant/www/vssp/js/vssp.js` — `VsspChatbotBar`
  (`window.vsspChatbot`) : envoi/interrogation/micro/openFullChat pour
  la barre HOME.
- `home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`
  — le badge par fournisseur de la barre HOME.
- `home-assistant/dashboards/templates_j2/admin.yaml.j2` — le bouton
  conditionnel « Custom » sous le sélecteur (inchangé).
- `home-assistant/www/vssp/wizard/vssp_chatbot.html` — le contenu du
  popup de conversation complète (interface de chat + formulaire).
