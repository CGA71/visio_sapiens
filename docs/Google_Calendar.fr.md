# Visio Sapiens — Calendrier Google (écran ADMIN + bandeau)

**Français** · [English](Google_Calendar.md)

## Principe

L'écran **CALENDRIER GOOGLE** de la console ADMIN remplace le parcours
manuel de Home Assistant (*Paramètres > Appareils et services >
Identifiants d'application*, puis *Ajouter l'intégration > Google
Calendar*), et choisit ensuite quel calendrier s'affiche dans le bandeau
de tous les dashboards.

```
Écran CALENDRIER GOOGLE (console ADMIN)
        │  iframe : /local/vssp/wizard/vssp_google.html
        │  POST (webhook local_only) → vssp_google_config
        ▼
packages/vssp_google.yaml  automatisation + scripts
        │  shell_command
        ▼
vssp/vssp_google_setup.py
        ├── websocket  ──▶ application_credentials/list + /create   (enregistre le client OAuth)
        ├── REST       ──▶ /api/config/config_entries/flow          (démarre le flux, renvoie l'URL de consentement)
        └── REST       ──▶ /api/states                              (liste les entités calendar.*)
        │  écrit
        ▼
/config/www/vssp/google_status.json   (lu par l'iframe et par 3 capteurs command_line)
```

## Ce qui est automatisé, et ce qui ne peut pas l'être

| Étape | Où | Automatisé ? |
|---|---|---|
| Projet Google Cloud, activation de l'API Calendar, écran de consentement, création de l'ID client OAuth | Google Cloud Console | **Non** — hors de portée de Home Assistant |
| Enregistrement du client OAuth dans Home Assistant | `application_credentials/create` | **Oui** |
| Démarrage du config flow `google` | API REST config flow | **Oui** |
| **Clic de consentement Google** | navigateur | **Non — impossible par conception** |
| Détection des entités `calendar.*` créées | `/api/states` | **Oui** |
| Injection du calendrier dans le bandeau | `--calendar-entity` à la génération | **Oui** |

Le consentement OAuth ne peut pas être supprimé : OAuth existe
précisément pour que le propriétaire du compte approuve l'accès dans
l'interface de Google. Le formulaire se termine donc en affichant un
bouton **Autoriser chez Google** ; tout ce qui l'entoure est automatisé.

## Prérequis côté Google (une seule fois)

1. [Console Google Cloud](https://console.cloud.google.com/) → créer un
   projet, puis activer **Google Calendar API**.
2. Écran de consentement OAuth : type `External`, puis **publier**
   l'application — sinon les identifiants expirent au bout de 7 jours.
3. *Identifiants* → créer un **ID client OAuth**, type
   **Application Web**.
4. Y coller cette URI de redirection autorisée, **exactement** :

   ```
   https://my.home-assistant.io/redirect/oauth
   ```

Documentation officielle :
<https://www.home-assistant.io/integrations/google/>

## Utilisation

1. Console ADMIN → **CALENDRIER GOOGLE**.
2. Coller l'**ID client** et le **secret client**, puis
   *Enregistrer & connecter*.
3. Cliquer **Autoriser chez Google**, approuver avec le compte
   propriétaire du calendrier.
4. Cliquer **ACTUALISER** : les entités `calendar.*` apparaissent.
5. Choisir le calendrier voulu, puis **Utiliser pour le header**.
6. **APPLIQUER AU BANDEAU** (régénère HOME) pour que le bandeau
   l'affiche.

## Où vivent les valeurs

| Donnée | Emplacement | Remarque |
|---|---|---|
| ID client OAuth | `input_text.vssp_google_client_id` | public par conception (il voyage dans l'URL de consentement) |
| Secret client | `input_text.vssp_google_client_secret` → `/config/vssp/.google_client_secret` (0600) | **jamais** passé en ligne de commande, même convention que `vssp_ha_token` et les clés du chatbot |
| Calendrier du bandeau | `input_text.vssp_google_calendar_entity` | passé au générateur via `--calendar-entity` |
| Défaut du modèle | `house.calendar_entity` (`model/house.yaml`) | utilisé quand le flag est absent |
| État de la configuration | `/config/www/vssp/google_status.json` | lu par `sensor.vssp_google_state` / `_message` / `_calendars` |

Priorité pour le bandeau :
`--calendar-entity` > `house.calendar_entity` > `calendar.calebar`
(l'ancien défaut codé en dur, conservé pour un modèle antérieur à cette
clé). Une valeur vide ou `unknown` — un `input_text` jamais rempli vaut
`unknown` — ne l'emporte jamais sur le modèle.

## Détails d'implémentation utiles

- **Pourquoi un client websocket écrit à la main**
  (`MiniWS` dans `vssp_google_setup.py`) : `application_credentials`
  n'expose **aucun** point d'accès REST ; ses commandes CRUD sont
  générées par le helper de collection de Home Assistant
  (`DictStorageCollectionWebsocket`, préfixe `application_credentials`),
  donc uniquement en websocket. Plutôt qu'ajouter une dépendance au pod,
  le script parle les quelques trames de la RFC 6455 nécessaires.
- **Jeton administrateur requis** : la collection est enregistrée avec
  `admin_only=True`. `input_text.vssp_ha_token` doit donc porter un jeton
  d'un compte administrateur.
- **Un credential ne peut pas être modifié** : Home Assistant déclare
  `UPDATE_FIELDS = {}`. Corriger un ID client mal saisi laisse l'ancien
  credential en place et en ajoute un second ; le config flow demande
  alors quelle implémentation utiliser. Le script répond avec **le
  nôtre** (il retient l'`id` renvoyé par `/list` ou `/create`) au lieu du
  premier de la liste, qui serait justement le périmé.
- **Le bandeau n'est pas dynamique** : l'entité calendrier est figée dans
  le YAML du dashboard au moment de la génération. Changer de calendrier
  impose donc une régénération — c'est ce que fait le bouton
  **APPLIQUER AU BANDEAU** (script `vssp_regenerate_home_dashboard`,
  HOME étant le dashboard protégé).

## Dépannage

| Symptôme | Cause probable |
|---|---|
| `État : error`, « token missing » | `input_text.vssp_ha_token` vide, ou *SAVE TOKEN* jamais lancé |
| `auth refusée` | jeton non administrateur, ou expiré |
| Config flow interrompu : `missing_credentials` | l'enregistrement du client OAuth a échoué avant le flux |
| `already_configured` | Google Calendar est déjà lié — rien à faire |
| Le lien de consentement ne mène nulle part | URI de redirection absente ou différente côté Google |
| Aucun calendrier après le consentement | cliquer **ACTUALISER** (les capteurs ne rescannent que toutes les 30 s) |
| Le bandeau montre encore l'ancien calendrier | régénérer : **APPLIQUER AU BANDEAU** |

## Fichiers

| Fichier | Rôle |
|---|---|
| `vssp/vssp_google_setup.py` | client websocket + REST, écrit `google_status.json` |
| `home-assistant/packages/vssp_google.yaml` | helpers, shell_commands, capteurs, scripts, webhook |
| `home-assistant/www/vssp/wizard/vssp_google.html` | le formulaire (iframe) |
| `home-assistant/dashboards/templates_j2/admin.yaml.j2` | écran CALENDRIER GOOGLE |
| `home-assistant/dashboards/templates_j2/_header.j2` | case agenda du bandeau |
| `vssp/generate_dashboards.py` | option `--calendar-entity` |
