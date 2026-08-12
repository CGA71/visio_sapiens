# Visio Sapiens — Générateur de dashboards (étape 5 du processus admin)

## Principe

`energy.yaml` n'est plus édité à la main. Il est **généré** à partir de :

- **`model/house.yaml`** — le modèle métier : pièces, appareils, circuits,
  capteurs solaires/EDF, navigation. C'est le fichier que remplira votre
  processus admin (formulaire → scan → assignation).
- **`energy.yaml.j2`** — le template Jinja2, qui porte la chartre graphique,
  le positionnement (grid-layout), les polices et les styles. Dérivé de
  votre `energy.yaml` original, avec 100 % de fidélité (validé par
  comparaison structurelle des YAML parsés).

```
house.yaml ──┐
             ├── generate_dashboards.py ──► dashboards/views/energy.yaml
energy.yaml.j2 ─┘
```

## Arborescence suggérée dans le repo

```
home-assistant/
├── dashboards/
│   ├── model/
│   │   └── house.yaml           ← source de vérité (modifiée par l'admin)
│   ├── templates_j2/
│   │   └── energy.yaml.j2       ← template (chartre graphique)
│   ├── templates/
│   │   └── button_card_templates.yaml   (inchangé)
│   └── views/
│       └── energy.yaml          ← GÉNÉRÉ, ne pas éditer
└── tools/
    ├── generate_dashboards.py
    └── build_template.py        ← outil pour templatiser vos autres
                                    dashboards (home, core, pièces…)
```

## Utilisation

```bash
pip install jinja2 pyyaml
python3 generate_dashboards.py \
    --model dashboards/model/house.yaml \
    --templates dashboards/templates_j2 \
    --out dashboards/views
```

Puis dans Home Assistant : Outils de développement → YAML →
**Recharger les dashboards Lovelace** (aucun redémarrage nécessaire).

## Ajouter un nouvel objet connecté (manuellement, en attendant le formulaire)

1. Ouvrir `model/house.yaml`
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
   « Consommation par appareil », avec le total de pièces/appareils affiché
   dans la sortie du script.

Si la pièce n'existe pas encore, ajoutez-la dans `rooms:` (et dans `nav:`
si elle doit apparaître dans la sidebar).

## Garde-fous intégrés au générateur

- **Validation du modèle** avant rendu : champs obligatoires présents,
  pas d'entité assignée à deux pièces.
- **`StrictUndefined`** : une variable manquante dans le modèle fait
  échouer la génération au lieu de produire un trou silencieux.
- **Validation YAML du rendu avant écriture** : un template cassé ne
  remplace jamais un dashboard fonctionnel.

## Brancher le générateur sur Home Assistant (préparation étapes 3–4)

Pour que le dashboard se régénère automatiquement quand l'admin valide
une assignation, ajoutez dans `configuration.yaml` :

```yaml
shell_command:
  vssp_generate_dashboards: >-
    python3 /config/tools/generate_dashboards.py
    --model /config/dashboards/model/house.yaml
    --templates /config/dashboards/templates_j2
    --out /config/dashboards/views
```

Puis un script/automatisation appelé par le bouton « Valider » du futur
formulaire admin :

```yaml
script:
  vssp_regenerer_dashboards:
    alias: "VSSP — Régénérer les dashboards"
    sequence:
      - service: shell_command.vssp_generate_dashboards
      - service: browser_mod.notification   # ou persistent_notification.create
        data:
          message: "Dashboards régénérés — rechargez Lovelace."
```

Le futur processus de **scan** (étape 3) pourra s'appuyer sur le registre
d'entités HA (`config/.storage/core.entity_registry` via WebSocket API)
pour détecter les nouveaux capteurs `*_power` / `*_energy` non présents
dans `house.yaml`, les proposer dans le formulaire d'assignation, écrire
le résultat dans `house.yaml`, puis appeler ce générateur.

## Templatiser vos autres dashboards

`build_template.py` montre la méthode utilisée pour transformer
`energy.yaml` : remplacements exacts des blocs répétitifs par des boucles
Jinja + substitution des entités. Adaptez-le pour `home.yaml`, `core.yaml`
et les vues par pièce — la sidebar `nav` est déjà factorisée dans le
modèle, donc commune à tous les futurs templates (`active_nav` pilote
le bouton actif).
