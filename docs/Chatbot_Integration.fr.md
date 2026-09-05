# Visio Sapiens — Intégration chatbot (carte HOME + sélecteur ADMIN)

**Français** · [English](Chatbot_Integration.md)

## Principe

La carte « Chatbot » du dashboard HOME et le sélecteur de fournisseur
du panneau GENERATION de l'ADMIN (`input_select.vssp_chatbot_provider`)
sont désormais branchés à de **vrais** backends IA — Gemini, Claude,
ChatGPT, ou un modèle auto-hébergé (« custom ») — au lieu d'être de
simples cadres d'accueil.

```
Carte Chatbot HOME / tuile "custom" de l'ADMIN
        │  tap_action : browser_mod.popup
        ▼
/local/vssp/wizard/vssp_chatbot.html   (iframe — vraie interface de chat ou formulaire)
        │  POST (webhook local_only)
        ▼
packages/vssp_chatbot.yaml  automatisations
        │  shell_command
        ▼
vssp/vssp_chatbot_send.py  ──HTTP──▶  Gemini / Claude / ChatGPT / votre serveur
        │  écrit
        ▼
/config/www/vssp/chatbot_status.json   (interrogé par l'iframe)
```

Même forme que l'écran THEME
(voir [Design_System_Editor.md](Design_System_Editor.fr.md)) : une page
HTML statique dans une iframe parle à Home Assistant via un **webhook
local uniquement**, jamais via l'API REST, car une iframe ne peut pas
atteindre l'objet `hass` de la page parente, et un jeton longue durée
n'a rien à faire dans un navigateur pour cela.

## Pourquoi un popup, pas un champ de saisie sur la carte

La carte Chatbot de HOME a une taille fixe (colonne de droite de la
grille HOME) qui ne doit pas changer. Les `custom_fields` de
`custom:button-card` ne peuvent pas héberger un vrai `<input>`
saisissable — donc la carte elle-même (`home.yaml.j2`, « Cadre 2»)
n'est qu'un **déclencheur visuel statique**, stylisé pour ressembler à
la barre de saisie d'une appli de chat (icône / texte grisé / micro /
envoi). Taper n'importe où dessus ouvre un popup
[browser_mod](https://github.com/thomasloven/hass-browser_mod) dont le
contenu est `vssp_chatbot.html` en iframe — cette page porte le vrai
champ de saisie, la liste des messages et le bouton d'envoi. Le même
mécanisme de popup est réutilisé par la tuile fournisseur « custom » de
l'ADMIN, en mode formulaire de configuration plutôt qu'en mode chat
(`?mode=custom`).

**`browser_mod` est une intégration HACS et n'est pas installée par ce
dépôt.** Elle doit être installée une fois sur le pod en production
(HACS → Intégrations → rechercher « browser_mod » → Installer →
redémarrer Home Assistant) avant qu'aucun des deux popups ne s'ouvre.
Rien d'autre dans cette fonctionnalité n'en dépend — le reste du
câblage (secrets, automatisations webhook, onglets fournisseur)
fonctionne malgré tout.

**À vérifier au déploiement** — ce dépôt n'a aucun exemple `browser_mod`
fonctionnel dont copier l'appel exact du popup (rien d'autre dans le
projet ne l'utilisait avant cette fonctionnalité). L'appel
`browser_mod.popup` dans `home.yaml.j2` et `admin.yaml.j2`
(`browser_id: this`, `size: normal`, `content: {type: iframe, url:
...}`) est écrit d'après la convention documentée de browser_mod, mais
les clés acceptées peuvent varier selon la version. Si le popup ne
s'ouvre pas après avoir installé browser_mod, vérifiez le schéma exact
du service sous Outils de développement > Actions > `browser_mod.popup`
sur l'instance en production et ajustez les deux blocs `tap_action` en
conséquence.

## Sélecteur de fournisseur — des logos plutôt que du texte

Les options d'`input_select.vssp_chatbot_provider` sont inchangées
(`gemini` / `claude` / `chatgpt` / `custom`,
`packages/vssp_generation.yaml`). Ce qui change, c'est la façon dont le
panneau GENERATION de l'ADMIN les affiche : pas un `type: tile` +
fonctionnalité `select-options` (cette fonctionnalité tile de HA ne
rend jamais que du texte brut, aucune icône/image par option), mais une
ligne de `custom:button-card`, un par option — le même motif de
radio-onglets déjà utilisé pour les onglets Jour/Mois/Année d'ENERGY
(`energy.yaml.j2` + template `vssp_energy_tab`). Le nouveau template,
`vssp_chatbot_provider_tab`
(`home-assistant/templates/button_card_templates.yaml`), affiche le
logo de chaque fournisseur via `image:` — sauf « custom », qui reste
icône + texte selon la demande d'origine, et qui ouvre en plus le popup
de configuration au tap.

Les fichiers de logo se trouvent dans
`home-assistant/www/vssp/images/providers/{gemini,claude,chatgpt}.svg`.
**Ce sont des marques placeholder originales et neutres, pas les vrais
logos déposés** (risque de droit d'auteur/marque à les reproduire sans
licence). Déposez les assets officiels à ces mêmes noms de fichier plus
tard si vous en détenez les droits — rien d'autre n'a besoin de
changer.

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

- Le popup de chat garde l'historique de conversation en mémoire
  uniquement — le fermer puis le rouvrir démarre une conversation
  neuve. Rien n'est persisté côté serveur au-delà du dernier échange
  (`chatbot_status.json`), par conception (ce projet n'a pas de
  stockage d'historique de chat).
- Le formulaire de configuration du modèle custom s'ouvre toujours
  vide ; il ne se pré-remplit pas depuis les valeurs déjà
  enregistrées. Consultez
  `input_text.vssp_chatbot_custom_*` dans Outils de développement >
  États si vous devez voir ce qui est actuellement enregistré.
- Pas encore de saisie vocale — l'icône micro, sur la carte comme dans
  le popup, est décorative.

## Fichiers

- `home-assistant/packages/vssp_admin.yaml` — helpers clé API/modèle,
  `shell_command` d'écriture des clés, scripts d'enregistrement.
- `home-assistant/packages/vssp_chatbot.yaml` — le webhook d'envoi et
  le webhook de configuration custom.
- `vssp/vssp_chatbot_send.py` — appelle la vraie API du fournisseur.
- `home-assistant/dashboards/templates_j2/home.yaml.j2` — la carte
  Chatbot de HOME (« Cadre 2 »).
- `home-assistant/dashboards/templates_j2/admin.yaml.j2` — la ligne
  d'onglets fournisseur.
- `home-assistant/templates/button_card_templates.yaml` —
  `vssp_chatbot_provider_tab`.
- `home-assistant/www/vssp/wizard/vssp_chatbot.html` — le contenu du
  popup (interface de chat + formulaire).
- `home-assistant/www/vssp/images/providers/*.svg` — logos des
  fournisseurs.
