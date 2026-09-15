# Visio Sapiens — Intégration chatbot (carte HOME + sélecteur ADMIN)

**Français** · [English](Chatbot_Integration.md)

## Principe

La carte « Chatbot » du dashboard HOME et le sélecteur de fournisseur
du panneau GENERATION de l'ADMIN (`input_select.vssp_chatbot_provider`)
sont désormais branchés à de **vrais** backends IA — Gemini, Claude,
ChatGPT, ou un modèle auto-hébergé (« custom ») — au lieu d'être de
simples cadres d'accueil.

```
Barre Chatbot HOME / popup de chat complet (vssp_chatbot.html)
        │  POST /api/webhook/vssp_chatbot_send (local_only, base64 vérifié)
        ▼
packages/vssp_chatbot.yaml
        ├─ 1er choix : l'intégration Home Assistant du fournisseur
        │     conversation.process (agent d'Anthropic / Google Gemini / OpenAI / Ollama)
        │     └─ shell_command.vssp_chatbot_reply ─▶ vssp_chatbot_send.py --agent (classe la réponse)
        └─ repli : shell_command.vssp_chatbot_send ─▶ vssp_chatbot_send.py ──HTTP──▶ API du fournisseur
                                                        (fichier de clé, ou point d'accès du formulaire custom)
        ▼  écrit
/config/www/vssp/chatbot_status.json   (interrogé par la barre HOME et le popup)

ADMIN > DASHBOARDS : choisir un fournisseur ──▶ popup de configuration de l'IA (wizard/vssp_ai_setup.html)
                     ou taper CONFIGURER L'IA     installation guidée de l'intégration, état en direct
```

Même forme que l'écran THEME
(voir [Design_System_Editor.md](Design_System_Editor.fr.md)) : une page
HTML statique dans une iframe parle à Home Assistant via un **webhook
local uniquement**, jamais avec un jeton longue durée dans le
navigateur.

## Configurer un fournisseur — le popup de configuration de l'IA

Choisir un fournisseur dans le menu de ADMIN > DASHBOARDS ouvre aussitôt
sa configuration guidée, dans un popup `browser_mod`
(`home-assistant/www/vssp/wizard/vssp_ai_setup.html`). Le bouton
**CONFIGURER L'IA** sous le menu ouvre le même popup pour le choix
courant, pour y revenir plus tard.

Chaque fournisseur se configure par **l'intégration propre de Home
Assistant**, pas par une clé saisie dans Visio Sapiens :

| Choix | Intégration | Clé API |
|---|---|---|
| Claude | Anthropic (`anthropic`) | console.anthropic.com › API Keys (crédits API nécessaires — Claude Pro ne donne pas l'API) |
| Gemini | Google Gemini (`google_generative_ai_conversation`) | aistudio.google.com › Get API key |
| ChatGPT | OpenAI (`openai_conversation`) | platform.openai.com › API keys (crédits API nécessaires — ChatGPT Plus ne donne pas l'API) |
| Personnalisé | Ollama (`ollama`), un modèle qui tourne dans la maison | pas de clé : l'URL du serveur Ollama |

Le popup déroule quatre étapes : obtenir la clé, ajouter l'intégration,
choisir le modèle (roue dentée de l'**Agent de conversation**, décocher
**Paramètres recommandés pour le modèle** ; cocher **Assist** sous
**Contrôler Home Assistant** pour qu'il pilote les appareils) et, en
option, en faire l'agent par défaut dans **Paramètres › Assistants
vocaux**. Chaque étape a un bouton qui ouvre le bon écran de Home
Assistant (directement la boîte d'ajout d'intégration, via
`/config/integrations/dashboard/add?domain=…`), et une vérification en
direct lue avec la session de la tablette — installée ou non, entité
de l'agent, modèle, agent Assist par défaut. La page ne fait que lire
(`config_entries/get`, les registres d'entités et d'appareils,
`assist_pipeline/pipeline/list`).

« Personnalisé » mène aussi à l'ancien formulaire pour tout autre
serveur compatible OpenAI (LM Studio, text-generation-webui, vLLM…),
pour lequel Home Assistant n'a pas d'intégration.

**Pourquoi le menu l'ouvre tout seul :** la fonctionnalité
`select-options` de la tuile ne peut pas exécuter de code. `VsspAiSetup`
dans `js/vssp.js` surveille `input_select.vssp_chatbot_provider` et ouvre
le popup quand il change, **par l'utilisateur connecté**
(`context.user_id`), **pendant que cet écran affiche ADMIN >
DASHBOARDS**. Un changement fait par une automatisation (l'enregistrement
du formulaire custom) ou sur une autre tablette n'ouvre rien.

## Quel chemin répond à un message

1. **L'intégration du fournisseur, quand elle est installée** —
   l'automatisation du webhook trouve son entité `conversation.*`
   (`integration_entities`) et appelle `conversation.process`. La clé
   reste dans Home Assistant ; l'agent garde la conversation sous un
   `conversation_id` que le fichier de statut rend au popup de chat
   complet, qui le renvoie avec le message suivant. Pour « custom », le
   point d'accès du formulaire, s'il est rempli, passe avant Ollama.
2. **Sinon, le repli** — `vssp_chatbot_send.py` appelle l'API du
   fournisseur avec la clé enregistrée dans Visio Sapiens (voir
   [Secrets](#secrets)), ou le point d'accès du formulaire custom.

Le SCAN de CORE suit la même préférence : la tâche IA (`ai_task.*`) de
l'intégration du fournisseur choisi d'abord, puis n'importe quelle
autre.

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
garde pas.

**`browser_mod` est une intégration HACS et n'est pas installée par ce
dépôt.** Elle doit être installée une fois sur le pod en production
(HACS → Intégrations → rechercher « browser_mod » → Installer →
redémarrer Home Assistant) avant que les popups (conversation complète,
configuration de l'IA) ne s'ouvrent — la saisie/réponse en ligne de la
barre HOME n'en a besoin en rien.

**Comment les popups s'ouvrent** — jamais par un appel de service
backend : `browser_id: this` n'a de sens que pour le frontend, donc un
`hass.callService('browser_mod', 'popup', {browser_id: 'this'})` atteint
un serveur qui ne sait pas quel navigateur est « celui-ci », signale un
succès et n'ouvre rien. En JavaScript, `js/vssp.js` appelle le service
frontend de browser_mod (`window.browser_mod.service('popup', …)`, sans
`browser_id` : cet écran) ; depuis un dashboard, `tap_action:
fire-dom-event` avec un bloc `browser_mod:`. Vérifié sur browser_mod
3.2.3.

## Sélecteur de fournisseur — visuel inchangé

`input_select.vssp_chatbot_provider` (`gemini` / `claude` / `chatgpt` /
`custom`, `packages/vssp_generation.yaml`) se rend exactement comme
avant : un `type: tile` + fonctionnalité `select-options`, options en
texte brut, même `card_mod` de fond que les sélecteurs langue/format
juste à côté (`admin.yaml.j2`). Une version précédente de cette
fonctionnalité l'avait remplacé par une ligne de boutons-logos ; c'est
revenu en arrière à la demande de l'utilisateur — le visuel du
sélecteur a été volontairement laissé intact.

Ce qui est nouveau : choisir une option ouvre son popup de
configuration de l'IA, et un bouton **CONFIGURER L'IA** sous la ligne du
sélecteur le rouvre (voir
[Configurer un fournisseur](#configurer-un-fournisseur--le-popup-de-configuration-de-lia)).
Il remplace l'ancien bouton « Custom », affiché seulement pour
`custom` : le formulaire custom s'atteint maintenant depuis le popup
Personnalisé.

Les trois SVG de logo provisoires
(`home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`)
qu'une version précédente de cette fonctionnalité avait ajoutés pour la
ligne de boutons-logos de l'ADMIN (depuis revenue en arrière) sont de
retour, mais pour un autre consommateur : le badge de tête de la barre
HOME (voir plus haut), pas le sélecteur de l'ADMIN, qui reste
inchangé.

## Secrets

Par le chemin intégration, la clé vit dans l'entrée de configuration de
Home Assistant, saisie dans son formulaire natif — Visio Sapiens ne la
voit jamais. Les helpers ci-dessous ne servent qu'au repli.

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
  message est isolé). Le popup de chat garde sa conversation jusqu'à sa
  fermeture : par le `conversation_id` de l'agent sur le chemin
  intégration, en mémoire sur le repli. Visio Sapiens ne persiste rien
  au-delà du dernier échange (`chatbot_status.json`).
- Un seul fichier de statut pour toute la maison : deux tablettes qui
  envoient à la même seconde peuvent lire la réponse l'une de l'autre.
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
- `home-assistant/packages/vssp_chatbot.yaml` — le webhook d'envoi
  (agent de l'intégration d'abord, puis le repli) et le webhook de
  configuration custom.
- `vssp/vssp_chatbot_send.py` — classe la réponse de l'agent de
  l'intégration (`--agent`), ou appelle lui-même l'API du fournisseur
  (repli).
- `home-assistant/www/vssp/wizard/vssp_ai_setup.html` — le popup de
  configuration de l'IA, une configuration guidée par fournisseur.
- `home-assistant/dashboards/templates_j2/home.yaml.j2` — la barre
  Chatbot de HOME (« Cadre 2 »).
- `home-assistant/www/vssp/js/vssp.js` — `VsspChatbotBar`
  (`window.vsspChatbot`) : envoi/interrogation/micro/openFullChat pour
  la barre HOME ; `VsspAiSetup` (`window.vsspAiSetup`) : ouvre le popup
  de configuration de l'IA quand le fournisseur change.
- `home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`
  — le badge par fournisseur de la barre HOME.
- `home-assistant/dashboards/templates_j2/admin.yaml.j2` — le bouton
  CONFIGURER L'IA sous le sélecteur (inchangé).
- `home-assistant/www/vssp/wizard/vssp_chatbot.html` — le contenu du
  popup de conversation complète (interface de chat + formulaire).
