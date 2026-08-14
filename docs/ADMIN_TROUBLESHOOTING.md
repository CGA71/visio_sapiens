# Panneau ADMIN — dépannage

## « Entité non trouvée » (bandeau jaune)

Une carte référence une entité que Home Assistant ne connaît pas.

Sur la capture, c'est la carte `entities` de la zone DELETE, qui affiche
`input_text.vssp_pin_entry`. Le helper n'existe pas encore : les
`input_text` de `vssp/vssp_admin_config.yaml` ne sont pas chargés.

**Vérifier** — Outils de développement → États, chercher
`input_text.vssp_`. S'il n'y a aucun résultat :

1. Les helpers de `vssp_admin_config.yaml` doivent être fusionnés dans
   votre configuration. Trois façons, au choix :

   * **En package** (le plus simple ici, la clé existe déjà chez vous) :
     copier le fichier dans `home-assistant/packages/` — les clés
     `input_text`, `shell_command`, `script`, `command_line` y sont
     toutes acceptées.
   * **Par include** dans `configuration.yaml` :
     `input_text: !include vssp/vssp_admin_config_input_text.yaml`
     (il faut alors éclater le fichier par domaine).
   * **Par fusion manuelle** des blocs dans `configuration.yaml`.

2. Redémarrer Home Assistant (les `input_text` ne se rechargent pas à
   chaud lorsqu'ils sont déclarés en YAML).

3. Définir le code admin une fois : lancer le script
   `vssp_set_admin_pin` après y avoir mis votre vraie valeur.

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
