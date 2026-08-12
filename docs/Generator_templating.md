# Visio Sapiens — Générateur de dashboards (étape 5 du processus admin)

## Principe

`views/energy.yaml` n'est plus édité à la main. Il est **généré** à
partir de :

- **`home-assistant/dashboards/model/house.yaml`** — le modèle métier :
  pièces, appareils, circuits, capteurs solaires/EDF, navigation
  (desktop `path` et mobile `path_mobile`). C'est le fichier que le
  processus admin alimentera (wizard Phase 1 = pièces, Phase 2 =
  scan + assignation).
- **`home-assistant/dashboards/templates_j2/energy.yaml.j2`** — le
  template Jinja2, qui porte la chartre graphique, le grid-layout, les
  polices et le modèle de cartes. Dérivé de l'`energy.yaml` original
  avec 100 % de fidélité (validé par comparaison structurelle des YAML
  parsés).

```
dashboards/model/house.yaml ──┐
                              ├── vssp/generate_dashboards.py
dashboards/templates_j2/*.j2 ─┘            │
                                           ▼
                          dashboards/views/energy.yaml
```

## Emplacement dans le repo (répertoires existants inchangés)

```
vssp/
├── vssp_discovery.py          EXISTANT — scan par Area → report.json
├── vssp_upgrade.py            EXISTANT — diff non destructif
├── generate_dashboards.py     ← NOUVEAU
└── build_template.py          ← NOUVEAU (templatise un dashboard existant)

home-assistant/
├── templates/                 EXISTANT — button_card_templates.yaml, …
└── dashboards/
    ├── views/
    │   └── energy.yaml        ← GÉNÉRÉ, ne pas éditer
    ├── model/                 ← NOUVEAU
    │   └── house.yaml
    └── templates_j2/          ← NOUVEAU
        └── energy.yaml.j2
```

Note sur les `!include` : le template `energy.yaml.j2` conserve tel quel
le chemin de votre dashboard fonctionnel
(`!include ../templates/button_card_templates.yaml`). Si vos includes
résolvent vers `home-assistant/templates/` dans votre déploiement,
rien à changer ; sinon adaptez cette ligne dans le `.j2` une seule fois
— elle sera reprise dans chaque génération.

## Utilisation

Depuis la racine du repo (les défauts du script pointent sur ces
chemins) :

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py
```

Puis dans Home Assistant : Outils de développement → YAML →
**Recharger les dashboards Lovelace** (aucun redémarrage nécessaire).
En déploiement CI, le fichier généré part dans le paquet `dist/` comme
n'importe quel YAML de `dashboards/` — rien à changer au pipeline.

## Ajouter un nouvel objet connecté (manuellement, en attendant le pont wizard → modèle)

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

3. Relancer `vssp/generate_dashboards.py` → la ligne apparaît dans le
   panneau « Consommation par appareil » d'ENERGY.

Si la pièce n'existe pas encore, l'ajouter dans `rooms:` (et dans `nav:`
si elle doit apparaître dans les sidebars — chaque entrée `nav` porte
`path` pour le desktop et `path_mobile` pour les dashboards `-m`).

## Garde-fous intégrés au générateur

- **Validation du modèle** avant rendu : champs obligatoires présents,
  pas d'entité assignée à deux pièces.
- **`StrictUndefined`** : une variable manquante dans le modèle fait
  échouer la génération au lieu de produire un trou silencieux.
- **Validation YAML du rendu avant écriture** : un template cassé ne
  remplace jamais un dashboard fonctionnel.

C'est complémentaire de `vssp_upgrade.py` : upgrade compare l'existant
aux découvertes (diagnostic), le générateur produit l'état cible
(construction).

## Intégration Home Assistant — à ajouter dans `vssp/vssp_admin_config.yaml`

Dans le même style que `vssp_discovery` / `vssp_upgrade` (le repo étant
déployé sous `/config` sur le pod) :

```yaml
shell_command:
  vssp_generate_dashboards: >-
    python3 /config/vssp/generate_dashboards.py
    --model /config/home-assistant/dashboards/model/house.yaml
    --templates /config/home-assistant/dashboards/templates_j2
    --out /config/home-assistant/dashboards/views

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

Un bouton GENERATE peut rejoindre la rangée DISCOVERY / UPGRADE /
DELETE du panneau ADMIN (`template: vssp_admin_button`,
`service: script.vssp_run_generate`).

## Pont wizard → modèle (le maillon manquant étapes 4 → 5)

Le wizard (Phase 2) connaît déjà `{entity_id, friendly_name, room}` ;
`vssp_discovery.py` produit `report.json` groupé par Area et
device_class. Prochaine brique : un petit
`vssp/vssp_model_sync.py` qui

1. lit `report.json` + les assignations du wizard,
2. mappe les entités `power`/`energy` par appareil (icône déduite du
   device_class, modèle depuis le device registry),
3. fusionne dans `model/house.yaml` **sans écraser** les champs déjà
   personnalisés (nom, icône),
4. appelle `generate_dashboards.py`.

`vssp_upgrade.py` sert alors de contrôle final : zéro écart attendu
entre les entités découvertes assignées et le dashboard généré.

## Templatiser les autres dashboards

`vssp/build_template.py` montre la méthode : remplacements exacts des
blocs répétitifs par des boucles Jinja + substitution des entités.
Candidats suivants, par ordre de rentabilité :

1. **`views/energy_mobile.yaml`** — même modèle `house.yaml`, layout
   mobile (dashboard `visio-sapiens-energy-m` déjà déclaré dans
   `config-fragment.yaml`).
2. **`home_mobile.yaml`** — les 12 tuiles de nav se génèrent depuis
   `nav:` avec `path_mobile`.
3. **`home.yaml`** — sidebar + KPIs + includes de vues pilotés par le
   modèle.
4. **`room.yaml.j2`** — un template unique par pièce qui génère
   `views/livingroom.yaml`, `views/bedroom1.yaml`, etc. depuis `rooms:`
   (les vues encore commentées en fin de `home.yaml`).
