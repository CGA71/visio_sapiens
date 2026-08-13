# Visio Sapiens — Générateur de dashboards (étape 5 du processus admin)

> **Statut : brique en cours d'intégration.** Le dépôt contient aujourd'hui
> `views/energy.yaml` en édition manuelle. Les répertoires `model/` et
> `templates_j2/` ainsi que `vssp/generate_dashboards.py` sont à ajouter — ce
> document décrit la cible et tout ce qu'elle implique, y compris côté CI.

## Principe

`views/energy.yaml` n'est plus édité à la main. Il est **généré** à partir de :

- **`home-assistant/dashboards/model/house.yaml`** — le modèle métier :
  pièces, appareils, circuits, capteurs solaires/EDF, navigation (desktop
  `path` et mobile `path_mobile`). C'est le fichier que le processus admin
  alimentera (wizard Phase 1 = pièces, Phase 2 = scan + assignation).
- **`home-assistant/dashboards/templates_j2/energy.yaml.j2`** — le template
  Jinja2, qui porte la charte graphique, le grid-layout, les polices et le
  modèle de cartes. Dérivé de l'`energy.yaml` original avec 100 % de fidélité
  (validé par comparaison structurelle des YAML parsés).

```
dashboards/model/house.yaml ──┐
                              ├── vssp/generate_dashboards.py
dashboards/templates_j2/*.j2 ─┘            │
                                           ▼
                          dashboards/views/energy.yaml
```

## Emplacement dans le repo

Le dossier `vssp/` existe déjà à la racine et contient les scripts métier ; les
deux nouveaux outils s'y ajoutent sans créer de répertoire supplémentaire.

```
vssp/
├── vssp_discovery.py           EXISTANT — scan par Area → report.json
├── vssp_upgrade.py             EXISTANT — diff non destructif
├── vssp_patch_dashboard.py     EXISTANT — overlays de plan
├── vssp_apply_config.py        EXISTANT — patcher configuration.yaml
├── vssp_ensure_packages.py     EXISTANT
├── vssp_sanitize_resources.py  EXISTANT
├── vssp_lan_probe.py           EXISTANT — sonde LAN/Livebox
├── vssp_admin_config.yaml      EXISTANT — helpers, shell_command, scripts
├── generate_dashboards.py      ← NOUVEAU
└── build_template.py           ← NOUVEAU (templatise un dashboard existant)

home-assistant/
├── templates/                  EXISTANT — button_card_templates.yaml,
│                                          decluttering_templates.yaml
├── packages/                   EXISTANT — vssp_technical_room.yaml, …
├── config-fragment.yaml        EXISTANT — état désiré de configuration.yaml
└── dashboards/
    ├── home.yaml               vue d'ensemble (desktop)
    ├── home_mobile.yaml        vue d'ensemble (mobile)
    ├── views/
    │   ├── core.yaml
    │   ├── computer.yaml
    │   ├── energy.yaml         ← DEVIENDRA GÉNÉRÉ, ne plus éditer
    │   ├── energy_mobile.yaml
    │   ├── technical_room.yaml
    │   └── technical_room_mobile.yaml
    ├── model/                  ← NOUVEAU
    │   └── house.yaml
    └── templates_j2/           ← NOUVEAU
        └── energy.yaml.j2
```

**Note sur les `!include`.** Le template `energy.yaml.j2` doit conserver tel
quel le chemin du dashboard fonctionnel :

```yaml
button_card_templates: !include ../templates/button_card_templates.yaml
decluttering_templates: !include ../templates/decluttering_templates.yaml
```

C'est le chemin correct : le job `build` recopie `home-assistant/templates/`
dans `dist/dashboards/templates/`, de sorte que, sur `/config`, un fichier de
`dashboards/views/` résout bien `../templates/`. Le contrôle des `!include` du
job `build` vérifie cette résolution à chaque pipeline — si le template Jinja
produit un chemin différent, la CI échoue avant le déploiement.

## Utilisation

Depuis la racine du repo (les défauts du script pointent sur ces chemins) :

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py
```

Puis dans Home Assistant : Outils de développement → YAML →
**Recharger les dashboards Lovelace** (aucun redémarrage nécessaire, contrairement
à un changement de `configuration.yaml`).

En déploiement CI, le fichier généré part dans le paquet `dist/` comme n'importe
quel YAML de `dashboards/` — **mais le générateur lui-même n'est pas encore
copié dans le paquet.** Voir « Intégration CI » plus bas.

## Ajouter un nouvel objet connecté (en attendant le pont wizard → modèle)

1. Ouvrir `home-assistant/dashboards/model/house.yaml`
2. Ajouter le device sous la bonne pièce :

```yaml
rooms:
  - id: livingroom
    name: "Salon"
    devices:
      - name: "TV"
        icon: mdi:television
        model: "Shelly Plug S"
        power_entity: sensor.shelly_tv_power
        energy_entity: sensor.shelly_tv_energy_today
```

3. Relancer `vssp/generate_dashboards.py` → la ligne apparaît dans le panneau
   « Consommation par appareil » d'ENERGY.

Si la pièce n'existe pas encore, l'ajouter dans `rooms:` (et dans `nav:` si elle
doit apparaître dans les sidebars — chaque entrée `nav` porte `path` pour le
desktop et `path_mobile` pour les dashboards `-m`).

> **Convention d'entités à respecter dans le modèle.** Le package
> `packages/spvs_energy_totaux.yaml` somme tous les capteurs `*_energie` en
> partant du principe qu'ils sont **cumulatifs**. Les compteurs journaliers
> portent le suffixe `*_energie_jour`. Un `energy_entity:` du modèle destiné à
> la colonne « aujourd'hui » doit donc viser `*_energie_jour` — c'est le point
> 5.2 d'`INTEGRATION_technical_room.md`, qu'il est judicieux de trancher **dans
> le modèle** plutôt que dans les deux YAML de vue.

## Aperçu — itérer sans toucher au staging

Le wizard (phase 4) et le générateur savent produire un dashboard de **test
isolé**. Trois niveaux, du plus prudent au plus engageant :

| Mode | Commande | Écrit quoi |
|---|---|---|
| Validation seule | `--dry-run` | rien (juste le rapport JSON) |
| Aperçu | `--preview` | `views/energy_preview.yaml` (url `vssp-energy-preview`) |
| Publication | *(aucun flag)* | `views/energy.yaml` (staging) |

L'isolation repose sur trois choses simultanées : un **fichier de sortie
suffixé** (`_preview.yaml`), une **url_path distincte**
(`vssp-energy-preview`, donc une entrée Lovelace séparée déclarée une fois pour
toutes), et un **modèle séparé** (`model/house_rooms.preview.yaml`). Aucun
chemin de staging n'apparaît dans la chaîne d'aperçu — ce n'est pas une
convention de nommage, c'est structurel.

Boucle d'itération type :

```bash
# 1. tester
python3 vssp/generate_dashboards.py --preview
# 2. ouvrir /vssp-energy-preview/energy, corriger le modèle ou le template
# 3. relancer autant de fois que nécessaire… puis seulement :
python3 vssp/generate_dashboards.py
```

Le générateur écrit un rapport JSON (`--status-file`) que le wizard lit via
`/local/vssp/preview_status.json` : nombre de pièces, appareils, circuits,
appareils en TODO, et erreurs de validation le cas échéant.

Déclaration du dashboard d'aperçu : voir `config-fragment-preview.yaml` (à
fusionner une fois dans `home-assistant/config-fragment.yaml`).

⚠️ **La clé d'aperçu doit commencer par `visio-sapiens`**, sinon
`vssp_apply_config.py` l'ignorera (`OSV_PREFIX = "visio-sapiens"`). Nommer donc
l'entrée `visio-sapiens-energy-preview` et non `vssp-energy-preview`.

Ajouter au `.gitignore` :

```
home-assistant/dashboards/views/*_preview.yaml
home-assistant/dashboards/model/*.preview.yaml
home-assistant/www/vssp/preview_status.json
```

Le job `validate` peut refuser un aperçu versionné et le job `build` les purger
du paquet — voir G3 dans `CI_CD.md`.

## Garde-fous intégrés au générateur

- **Validation du modèle** avant rendu : champs obligatoires présents, pas
  d'entité assignée à deux pièces.
- **`StrictUndefined`** : une variable manquante dans le modèle fait échouer la
  génération au lieu de produire un trou silencieux.
- **Validation YAML du rendu avant écriture** : un template cassé ne remplace
  jamais un dashboard fonctionnel.

C'est complémentaire de `vssp_upgrade.py` : upgrade compare l'existant aux
découvertes (diagnostic), le générateur produit l'état cible (construction).

---

## Intégration CI — ce qu'il reste à faire

C'est le maillon manquant : sans ces trois patchs, le générateur fonctionne en
local mais n'existe ni sur le pod, ni en production, et rien ne garantit que le
`energy.yaml` versionné corresponde au modèle versionné.

### 1. Embarquer le générateur dans le paquet

Le job `build` copie aujourd'hui les scripts `vssp/` un par un et n'inclut ni
`generate_dashboards.py`, ni `build_template.py`, ni les outils admin. Le
correctif (détaillé en G2 de `CI_CD.md`) copie tout le dossier :

```yaml
    - mkdir -p dist/vssp
    - cp vssp/*.py   dist/vssp/
    - cp vssp/*.yaml dist/vssp/ 2>/dev/null || true
    - cp vssp/livebox.env dist/vssp/
    - rm -f dist/vssp/.livebox.env
```

`model/` et `templates_j2/` arrivent d'eux-mêmes : `build` fait déjà
`cp -r home-assistant/dashboards/. dist/dashboards/`.

### 2. Garde anti-dérive dans `validate`

Le pipeline doit refuser un `views/energy.yaml` qui ne correspond plus à
`model/house.yaml` — sinon un commit du modèle sans régénération déploie un
dashboard périmé, en silence :

```yaml
    - |
      if [ -f vssp/generate_dashboards.py ] && [ -f home-assistant/dashboards/model/house.yaml ]; then
        pip install jinja2 --quiet --break-system-packages 2>/dev/null || apk add --no-cache py3-jinja2 >/dev/null
        python3 vssp/generate_dashboards.py \
          --model     home-assistant/dashboards/model/house.yaml \
          --templates home-assistant/dashboards/templates_j2 \
          --out       /tmp/gen_views
        for f in /tmp/gen_views/*.yaml; do
          n=$(basename "$f")
          diff -q "$f" "home-assistant/dashboards/views/$n" >/dev/null 2>&1 || {
            echo "[ERR] views/$n differe de la generation depuis model/house.yaml"
            exit 1; }
        done
        echo "[OK] Dashboards generes conformes au modele"
      fi
```

### 3. Dépendance `jinja2` sur le pod

Le `shell_command` ci-dessous s'exécute **dans le conteneur Home Assistant**, qui
n'embarque pas forcément Jinja2 en tant que module Python autonome. À vérifier
avant de câbler le bouton GENERATE :

```sh
kubectl exec -n homeassistant <pod> -c homeassistant -- python3 -c "import jinja2, yaml; print('ok')"
```

Si l'import échoue, deux options : installer la dépendance dans le conteneur
(non persistant après update d'image), ou ne générer que dans la CI et laisser
le pod ne consommer que le YAML produit. **La seconde est la plus sûre** et
cohérente avec le choix déjà fait pour `ruamel.yaml` en production, où le
patcher tourne dans le runner GitLab et non sur HAOS.

---

## Intégration Home Assistant — à ajouter dans `vssp/vssp_admin_config.yaml`

Dans le même style que `vssp_discovery` / `vssp_upgrade` (le repo étant déployé
sous `/config` sur le pod) :

```yaml
shell_command:
  vssp_generate_dashboards: >-
    python3 /config/vssp/generate_dashboards.py
    --model /config/dashboards/model/house.yaml
    --templates /config/dashboards/templates_j2
    --out /config/dashboards/views

script:
  vssp_run_generate:
    alias: "Visio Sapiens — Régénérer les dashboards"
    sequence:
      - service: shell_command.vssp_backup_dashboard
      - service: shell_command.vssp_generate_dashboards
      - service: persistent_notification.create
        data:
          title: "Visio Sapiens — Dashboards régénérés"
          message: >
            energy.yaml a été régénéré depuis model/house.yaml.
            Rechargez Lovelace pour voir le résultat.
```

⚠️ **Attention aux chemins.** Le déploiement place les dashboards en
`/config/dashboards/`, **pas** en `/config/home-assistant/dashboards/`. Or
`vssp_admin_config.yaml` utilise aujourd'hui ce second chemin :

```yaml
  vssp_backup_dashboard: >-
    sh -c "mkdir -p /config/vssp/backups &&
    cp /config/home-assistant/dashboards/home.yaml         # ← n'existe pas sur le pod
    /config/vssp/backups/home_$(date +%Y%m%d_%H%M%S).yaml"
  vssp_delete_dashboard: >-
    rm -f /config/home-assistant/dashboards/home.yaml      # ← ne supprime rien
```

À corriger en `/config/dashboards/home.yaml` dans les deux commandes, sans quoi
la sauvegarde automatique du bouton DELETE est un no-op — c'est-à-dire une
protection qui n'en est pas une. Le même fichier référence par ailleurs
`input_text.vssp_ha_token`, qui n'est déclaré nulle part : à ajouter dans le
bloc `input_text:`.

Un bouton GENERATE peut ensuite rejoindre la rangée DISCOVERY / UPGRADE / DELETE
du panneau ADMIN (`template: vssp_admin_button`, `service: script.vssp_run_generate`).

## Pont wizard → modèle (le maillon manquant étapes 4 → 5)

Le wizard (Phase 2) connaît déjà `{entity_id, friendly_name, room}` ;
`vssp_discovery.py` produit `report.json` groupé par Area et device_class.
Prochaine brique : un petit `vssp/vssp_model_sync.py` qui

1. lit `report.json` + les assignations du wizard,
2. mappe les entités `power` / `energy` par appareil (icône déduite du
   device_class, modèle depuis le device registry),
3. fusionne dans `model/house.yaml` **sans écraser** les champs déjà
   personnalisés (nom, icône),
4. appelle `generate_dashboards.py`.

`vssp_upgrade.py` sert alors de contrôle final : zéro écart attendu entre les
entités découvertes assignées et le dashboard généré.

## Templatiser les autres dashboards

`vssp/build_template.py` montre la méthode : remplacements exacts des blocs
répétitifs par des boucles Jinja + substitution des entités. Candidats suivants,
par ordre de rentabilité :

1. **`views/energy_mobile.yaml`** — même modèle `house.yaml`, layout mobile
   (dashboard `visio-sapiens-energy-m` déjà déclaré dans `config-fragment.yaml`).
2. **`home_mobile.yaml`** — les tuiles de nav se génèrent depuis `nav:` avec
   `path_mobile`.
3. **`home.yaml`** — sidebar + KPIs + includes de vues pilotés par le modèle.
4. **`views/technical_room.yaml` / `_mobile`** — 10 interrupteurs et 8 appareils
   déjà structurés, donc un gain immédiat, et cela réglerait au passage
   l'arbitrage `*_energie` / `*_energie_jour` en un seul endroit.
5. **`room.yaml.j2`** — un template unique par pièce qui génère
   `views/livingroom.yaml`, `views/bedroom1.yaml`, etc. depuis `rooms:` (les
   vues encore commentées en fin de `home.yaml`).
