# Panneau ADMIN — dépannage

## « script.vssp_… introuvable » / « Entité non trouvée »

Même cause dans les deux cas : le fichier de configuration ADMIN n'est
pas chargé par Home Assistant. Les entités `script.vssp_*`,
`input_text.vssp_*` et `binary_sensor.vssp_dashboard_*` n'existent donc
pas, et les boutons appellent des services inconnus.

**La solution la plus simple chez vous** : le fichier est livré comme
package, `home-assistant/packages/vssp_admin.yaml`. Votre CI copie déjà
`home-assistant/packages/.` vers `dist/packages/` → `/config/packages/`,
et `config-fragment.yaml` pose `packages: !include_dir_named packages`.
Il est donc chargé sans rien ajouter à `configuration.yaml`.

**Vérifier dans l'ordre :**

1. Le fichier est-il sur le pod ?
   `kubectl -n home-assistant exec home-assistant-0 -c home-assistant -- ls /config/packages/`
2. La clé de chargement est-elle en place ?
   `grep -A2 "^homeassistant:" /config/configuration.yaml`
   (elle est posée automatiquement par `vssp_ensure_packages.py`)
3. **Redémarrer Home Assistant.** Les `input_text` et `command_line`
   déclarés en YAML ne se rechargent pas à chaud. Pour les scripts seuls,
   Outils de développement → YAML → Recharger les scripts suffit.
4. Outils de développement → États, chercher `vssp` : les entités
   `script.vssp_run_energy_sync`, `binary_sensor.vssp_dashboard_energy_present`
   et `input_text.vssp_ha_token` doivent apparaître.

Si le fichier est bien dans `/config/packages/` mais que les entités
n'apparaissent pas, regarder Paramètres → Journaux : une erreur de
fusion (clé dupliquée avec un autre package) y est explicite.

## « Entité non trouvée » (bandeau jaune) — détail

Une carte référence une entité que Home Assistant ne connaît pas.

Sur la capture, c'est la carte `entities` de la zone DELETE, qui affiche
`input_text.vssp_pin_entry`. Le helper n'existe pas encore : les
`input_text` de `vssp/vssp_admin_config.yaml` ne sont pas chargés.

**Vérifier** — Outils de développement → États, chercher
`input_text.vssp_`. S'il n'y a aucun résultat :

1. Déposer `vssp_admin.yaml` dans `home-assistant/packages/` (voir
   section précédente), déployer, redémarrer.
2. Définir le code admin une fois : lancer le script
   `vssp_set_admin_pin` après y avoir mis votre vraie valeur.
3. Renseigner `input_text.vssp_ha_token` avec un jeton longue durée
   (Profil → Jetons d'accès longue durée) — sans lui, `vssp_discovery`
   et `vssp_energy_sync` s'exécutent avec un jeton vide.

**Note** : le helper `input_text.vssp_ha_token` manquait dans la version
précédente du fichier alors que `vssp_discovery` et `vssp_energy_sync`
l'utilisent. Il est maintenant déclaré — sans lui, ces commandes
tournaient avec un jeton vide.

## « ButtonCardJSTemplateError » (bandeau rouge)

Un template JS de button-card a levé une exception. La cause la plus
fréquente : accéder à `.state` sur une entité absente.

```js
// ✗ lève une exception si l'entité n'existe pas
states['sensor.x'].state

// ✓ garde systématique
var s = states['sensor.x'];
return s ? s.state : 'valeur par defaut';
```

C'était le cas du bouton CORE, qui lisait
`binary_sensor.vssp_dashboard_core_present` sans garde. Corrigé dans
`admin/system_dashboards.yaml` : les deux blocs JS sont désormais gardés
et testés avec zéro entité disponible.

## Le bouton CRÉER ENERGY n'apparaît pas

Symptôme visible sur la capture : la section « Dashboards système »
n'affiche que SYNC ENERGY et CORE.

Les deux cartes conditionnelles testaient `state: "off"` et
`state: "on"`. Quand `binary_sensor.vssp_dashboard_energy_present`
n'existe pas, l'état n'est ni l'un ni l'autre : **aucun** des deux
boutons ne s'affichait — exactement dans la situation où l'on a besoin
du bouton CRÉER.

Corrigé : la condition d'affichage de CRÉER est passée à
`state_not: "on"`, qui couvre aussi l'entité absente, `unknown` ou
`unavailable`. Le garde-fou contre l'écrasement reste côté générateur
(`--if-missing`), pas côté interface — l'affichage d'un bouton ne doit
jamais être la seule sécurité.

Un bandeau de diagnostic apparaît par ailleurs dans la carte quand les
capteurs d'état sont indisponibles, pour signaler que la configuration
ADMIN n'est pas chargée plutôt que de laisser des boutons inertes.

## Les boutons s'affichent mais « ne font rien »

Les `shell_command` s'exécutent dans le conteneur Home Assistant. À
vérifier dans l'ordre :

1. **Les scripts Python sont-ils sur le pod ?**
   `ls /config/vssp/generate_dashboards.py /config/vssp/vssp_energy_sync.py`
   S'ils manquent : le job `build` du CI ne les copie pas encore dans
   `dist/vssp/` — voir `PATCH_gitlab-ci.md` (deux lignes à ajouter).
2. **Les dépendances sont-elles présentes ?** `python3 -c "import jinja2, yaml"`
   — sinon `pip install jinja2 pyyaml` dans le conteneur, ou ajouter la
   dépendance à votre image.
3. **Les dossiers cibles existent-ils ?**
   `mkdir -p /config/www/vssp /config/vssp/backups /config/home-assistant/dashboards/model`
4. **Le rapport JSON** dit le reste :
   `cat /config/www/vssp/energy_generate_status.json`
   (clé `errors` en cas de modèle invalide).

Les journaux de `shell_command` apparaissent dans
Paramètres → Journaux avec le code retour de la commande.

## Le dashboard est généré mais absent de la barre latérale

Le fichier existe (`binary_sensor.vssp_dashboard_energy_present` à `on`)
mais aucune entrée n'apparaît : c'est la déclaration Lovelace qui
manque, pas la génération. Vérifier le bloc `lovelace: dashboards:` de
`config-fragment.yaml` — `vssp-energy` doit pointer sur
`home-assistant/dashboards/views/energy.yaml`. Un redémarrage est
nécessaire après ajout d'une entrée (le rechargement à chaud ne suffit
que pour le contenu, pas pour la déclaration).

## Note sur les chemins du pod

Le CI déploie `home-assistant/dashboards/` vers **`/config/dashboards/`**
(et non `/config/home-assistant/dashboards/`), `home-assistant/packages/`
vers `/config/packages/`, `vssp/` vers `/config/vssp/` et
`home-assistant/www/` vers `/config/www/`.

Les chemins des `shell_command` sont alignés là-dessus :

| Dans le repo | Sur le pod |
|---|---|
| `home-assistant/dashboards/views/energy.yaml` | `/config/dashboards/views/energy.yaml` |
| `home-assistant/dashboards/model/house.yaml` | `/config/dashboards/model/house.yaml` |
| `home-assistant/dashboards/templates_j2/` | `/config/dashboards/templates_j2/` |
| `home-assistant/packages/vssp_admin.yaml` | `/config/packages/vssp_admin.yaml` |
| `vssp/generate_dashboards.py` | `/config/vssp/generate_dashboards.py` |

Les valeurs par défaut de `generate_dashboards.py` utilisent les chemins
du **repo** (pour un lancement depuis la racine du dépôt) ; les
`shell_command` passent les chemins du **pod** explicitement.

## « L'action script.vssp_… utilise l'action lovelace.reload qui n'a pas été trouvée »

`lovelace.reload` **n'existe pas** dans Home Assistant. Le domaine
`lovelace` n'expose qu'un seul service, `lovelace.reload_resources`, qui
recharge les ressources JS/CSS déclarées dans `lovelace.resources` — pas
les dashboards.

Home Assistant refuse d'exécuter un script dont une étape référence un
service inconnu : le script s'arrête à cette ligne, même si les étapes
précédentes ont réussi. C'est pour ça que le message apparaît alors que
la synchronisation, elle, s'est peut-être bien déroulée.

**Corrigé** : les appels ont été retirés de `vssp_admin.yaml` et de
`vssp_energy_totaux.yaml`.

**Pourquoi rien ne les remplace** : un dashboard en mode YAML est relu
automatiquement. Home Assistant met la configuration en cache avec la
date de modification du fichier et la recharge dès que celle-ci change.
Le seul cache restant est celui du navigateur pour l'onglet déjà ouvert
— d'où l'invitation à faire Ctrl+Maj+R dans les notifications.

Ce qui nécessite en revanche un vrai redémarrage, c'est l'ajout d'une
**entrée** de dashboard dans `lovelace: dashboards:` — pas la
modification de son contenu.

### Vérifier qu'un service existe avant de l'appeler

Outils de développement → Actions : le sélecteur ne propose que les
services réellement enregistrés. Taper `lovelace.` n'y fait apparaître
que `reload_resources`, ce qui confirme le diagnostic en deux secondes.
