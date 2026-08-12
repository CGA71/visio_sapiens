# Visio Sapiens — Générateur de dashboards (étape 5 du processus admin)

## Principe

Les dashboards générés ne sont plus édités à la main. Ils sont produits
à partir de :

- **`model/house.yaml`** — le modèle métier : pièces, appareils, circuits,
  capteurs solaires/EDF, navigation (desktop **et** mobile). C'est le
  fichier que remplira le processus admin (formulaire → scan → assignation),
  dont le panneau vit dans `home.yaml` (vue `/visio-sapiens/admin`).
- **`templates_j2/*.yaml.j2`** — les templates Jinja2, qui portent la
  chartre graphique, le positionnement (grid-layout), les polices et le
  modèle de cartes. `energy.yaml.j2` est dérivé de l'original avec 100 %
  de fidélité (validé par comparaison structurelle des YAML parsés).

```
model/house.yaml ──┐
                   ├── tools/generate_dashboards.py ──► views/energy.yaml
templates_j2/*.j2 ─┘
```

## Arborescence du repo

Les répertoires existants sont conservés tels quels ; seuls `model/`,
`templates_j2/` et `tools/` sont ajoutés (marqués **NOUVEAU**).

```
home-assistant/
├── dashboards/
│   ├── home.yaml                  ← dashboard principal "Visio Sapiens"
│   │                                (url /visio-sapiens : HOME, vues
│   │                                incluses depuis views/, panneau ADMIN)
│   ├── home_mobile.yaml           ← variante mobile/tablette
│   │                                (urls en -m : /visio-sapiens-m/…)
│   ├── templates/                 ← EXISTANT — inchangé
│   │   ├── button_card_templates.yaml
│   │   └── decluttering_templates.yaml
│   ├── views/                     ← EXISTANT — vues incluses par home.yaml
│   │   ├── core.yaml                (déjà en place)
│   │   ├── energy.yaml              ← GÉNÉRÉ, ne pas éditer
│   │   ├── livingroom.yaml          # à créer (futur template room.yaml.j2)
│   │   ├── bedroom1.yaml            # à créer
│   │   └── …                        # bedroom2, bathroom, computer,
│   │                                # technical, secret, garden
│   ├── model/                     ← NOUVEAU
│   │   └── house.yaml               (source de vérité, modifiée par l'admin)
│   └── templates_j2/              ← NOUVEAU
│       └── energy.yaml.j2           (template — chartre graphique)
├── tools/                         ← NOUVEAU
│   ├── generate_dashboards.py
│   └── build_template.py            (outil pour templatiser home.yaml,
│                                     core.yaml, home_mobile.yaml…)
└── www/vssp/                      ← EXISTANT — inchangé
    ├── backgrounds/                 (home.png, energy.png, …)
    └── images/                      (logo_VS-Sapiens.png, …)
```

Rappels de câblage (inchangés par rapport à votre installation) :
- `energy.yaml` reste un dashboard **autonome** déclaré dans
  `configuration.yaml` sous `lovelace: dashboards:` (url `vssp-energy`),
  ses `!include` pointent vers `../templates/`.
- `home.yaml` inclut ses vues via `!include views/<vue>.yaml` — quand
  une vue générée doit aussi apparaître dans le dashboard principal,
  il suffira de dé-commenter la ligne correspondante en fin de fichier.

## Utilisation

```bash
pip install jinja2 pyyaml
python3 tools/generate_dashboards.py \
    --model dashboards/model/house.yaml \
    --templates dashboards/templates_j2 \
    --out dashboards/views
```

Puis dans Home Assistant : Outils de développement → YAML →
**Recharger les dashboards Lovelace** (aucun redémarrage nécessaire).

## Ajouter un nouvel objet connecté (manuellement, en attendant le formulaire)

1. Ouvrir `dashboards/model/house.yaml`
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

3. Relancer `generate_dashboards.py` → la ligne apparaît dans le panneau
   « Consommation par appareil » d'ENERGY.

Si la pièce n'existe pas encore, ajoutez-la dans `rooms:` (et dans `nav:`
si elle doit apparaître dans les sidebars — chaque entrée `nav` porte
`path` pour le desktop et `path_mobile` pour la variante `-m`).

## Garde-fous intégrés au générateur

- **Validation du modèle** avant rendu : champs obligatoires présents,
  pas d'entité assignée à deux pièces.
- **`StrictUndefined`** : une variable manquante dans le modèle fait
  échouer la génération au lieu de produire un trou silencieux.
- **Validation YAML du rendu avant écriture** : un template cassé ne
  remplace jamais un dashboard fonctionnel.

## Brancher le générateur sur Home Assistant (préparation étapes 3–4)

Pour que les dashboards se régénèrent quand l'admin valide une
assignation, dans `configuration.yaml` :

```yaml
shell_command:
  vssp_generate_dashboards: >-
    python3 /config/tools/generate_dashboards.py
    --model /config/dashboards/model/house.yaml
    --templates /config/dashboards/templates_j2
    --out /config/dashboards/views
```

Puis un script appelé par le bouton « Valider » du panneau ADMIN
(vue `/visio-sapiens/admin` de `home.yaml`) :

```yaml
script:
  vssp_regenerer_dashboards:
    alias: "VSSP — Régénérer les dashboards"
    sequence:
      - service: shell_command.vssp_generate_dashboards
      - service: persistent_notification.create
        data:
          message: "Dashboards régénérés — rechargez Lovelace."
```

## Feuille de route du processus admin

| Étape | Statut | Où |
|---|---|---|
| 1. Tablette / mobile | dashboards `home.yaml` + `home_mobile.yaml` en place | racine dashboards |
| 2. Formulaire nombre de pièces | à construire dans la vue ADMIN | `home.yaml` |
| 3. Scan des nouveaux objets | à construire — registre d'entités HA (WebSocket API) pour détecter les capteurs `*_power` / `*_energy` absents de `house.yaml` | `tools/` |
| 4. Assignation objets → pièces | formulaire ADMIN qui écrit dans `model/house.yaml` | `home.yaml` + `tools/` |
| 5. Génération des dashboards | **fait pour ENERGY** — `energy.yaml.j2` + `generate_dashboards.py` | `templates_j2/` + `tools/` |

## Templatiser les autres dashboards

`tools/build_template.py` montre la méthode utilisée pour transformer
`energy.yaml` : remplacements exacts des blocs répétitifs par des boucles
Jinja + substitution des entités. Candidats suivants, dans l'ordre de
rentabilité :

1. **`home_mobile.yaml`** — la nav mobile (12 tuiles quasi identiques)
   se génère depuis `nav:` du modèle avec `path_mobile`.
2. **`home.yaml`** — sidebar + KPIs + includes de vues pilotés par le
   modèle (une pièce ajoutée dé-commente automatiquement son include).
3. **`room.yaml.j2`** — un template unique par pièce qui génère
   `views/livingroom.yaml`, `views/bedroom1.yaml`, etc. depuis `rooms:`.
