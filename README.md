# Visio Sapiens — Neural Home Interface

Interface Home Assistant futuriste inspirée d'OSVision, pensée pour
tablette et mobile. Chaque pièce devient un module système ; les
dashboards sont progressivement **générés** depuis un modèle métier
plutôt qu'écrits à la main.

## Concept

- CORE (Home) — HUD, radar central, IA Core, metrics
- LIVING / SLEEP MODULES — pièces de vie
- DATA CENTER / ENGINE ROOM — salle informatique, local technique
- POWER GRID — gestion de l'énergie (solaire, EDF, tableau électrique)
- Sidebar de navigation commune, chartre graphique néon/glassmorphism

## Stack

Home Assistant (Lovelace YAML), button-card, card-mod, layout-card,
stack-in-card, apexcharts-card, mini-graph-card, config-template-card,
decluttering-card, browser_mod — thème `Visio Sapiens`, CSS/JS Engine
maison (`www/vssp/`). CI/CD GitLab → k3s.

## Arborescence du repo

Les répertoires existants sont conservés tels quels ; seuls ceux
marqués **NOUVEAU** sont ajoutés par le générateur de dashboards.

```
.
├── .gitlab-ci.yml               validate / build / deploy:staging (k3s)
│                                + smoke tests (/local/vssp/*, cache-busting __VTOKEN__)
├── hacs.json
├── repository.yaml
├── README.md                    ← ce fichier
│
├── docs/
│   ├── project.md               architecture, changelog des itérations
│   ├── modules.md
│   ├── desygn-system.md         chartre graphique
│   ├── osvision.md
│   ├── CI_INTEGRATION.md        patch configuration.yaml dans le pipeline
│   └── Generator_templating.md  générateur de dashboards (étape 5)
│
├── scripts/                     package.sh / deploy.sh / reload.sh / validate.sh
│
├── themes/
│   └── visio_sapiens.yaml
│
├── vssp/                        scripts Python du processus admin + config HA
│   ├── vssp_discovery.py        scan des entités par Area → report.json
│   ├── vssp_upgrade.py          diff report.json ↔ dashboard (non destructif)
│   ├── vssp_apply_config.py     patch de configuration.yaml (ruamel)
│   ├── vssp_ensure_packages.py
│   ├── vssp_sanitize_resources.py
│   ├── vssp_lan_probe.py
│   ├── vssp_admin_config.yaml   helpers / shell_command / scripts ADMIN
│   ├── vssp_energy_sync.py      ← NOUVEAU — parc mesuré ENERGY (ajout/retrait)
│   ├── generate_dashboards.py   ← NOUVEAU — rend les templates Jinja2
│   └── build_template.py        ← NOUVEAU — templatise un dashboard existant
│
└── home-assistant/
    ├── config-fragment.yaml     état désiré des clés OSVision (lovelace, resources)
    ├── packages/                vssp_energy_totaux.yaml (totaux dynamiques), …
    ├── templates/               button_card_templates.yaml, decluttering_templates.yaml
    ├── dashboards/
    │   ├── home.yaml            dashboard principal /visio-sapiens (+ vue ADMIN)
    │   ├── home_mobile.yaml     variante mobile /visio-sapiens-m
    │   ├── admin/              ← NOUVEAU
    │   │   └── system_dashboards.yaml   carte ADMIN « dashboards système »
    │   │                                (ENERGY/CORE, hors cycle des pièces)
    │   ├── views/               vues et dashboards autonomes
    │   │   ├── core.yaml
    │   │   ├── computer.yaml
    │   │   ├── energy.yaml          ← GÉNÉRÉ — ne plus éditer à la main
    │   │   ├── energy_mobile.yaml
    │   │   ├── technical_room.yaml
    │   │   └── technical_room_mobile.yaml
    │   ├── model/               ← NOUVEAU
    │   │   └── house.yaml         modèle métier (pièces, appareils, circuits, nav)
    │   └── templates_j2/        ← NOUVEAU
    │       └── energy.yaml.j2     template Jinja2 (chartre graphique ENERGY)
    └── www/vssp/                CSS/JS Engine, composants, wizard, assets
        ├── css/  js/  components/  fonts/  icons/
        ├── wizard/              formulaire web (phases 1-4 du processus admin)
        ├── backgrounds/
        └── images/
```

## Processus admin — génération automatique des dashboards

| Étape | Statut | Où |
|---|---|---|
| 1. Tablette / mobile | ✅ dashboards `home.yaml` + `home_mobile.yaml` (+ variantes `-m` déclarées dans `config-fragment.yaml`) | `dashboards/` |
| 2. Formulaire pièces / étages | ✅ wizard Phase 1 | `www/vssp/wizard/` |
| 3. Scan des objets connectés | ✅ `vssp_discovery.py` (bouton DISCOVERY SCAN du panneau ADMIN, ou wizard Phase 2) → `report.json` | `vssp/` |
| 4. Assignation objets → pièces | ✅ wizard Phase 2 (sélecteur de pièce par entité) | `www/vssp/wizard/` |
| 5. Génération des dashboards | 🟡 **fait pour ENERGY** — `energy.yaml.j2` + `generate_dashboards.py` (fidélité 100 % validée par comparaison structurelle) ; à étendre aux autres vues | `dashboards/templates_j2/` + `vssp/` |

Le maillon restant entre 4 et 5 : écrire le résultat de l'assignation du
wizard dans `dashboards/model/house.yaml` (au lieu du seul `report.json`),
puis appeler `generate_dashboards.py`. `vssp_upgrade.py` reste l'outil de
diff non destructif pour vérifier les écarts avant régénération.

## Générer les dashboards

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py    # défauts alignés sur ce repo
```

Détails, garde-fous et intégration `shell_command` :
voir `docs/Generator_templating.md`.

## CI/CD

Pipeline GitLab (`.gitlab-ci.yml`) : `validate` (structure du repo,
YAML), `build` (paquet `dist/` + cache-busting `__VTOKEN__`),
`deploy:staging` (k3s : déballage dans le pod HA, patch de
`configuration.yaml` via `vssp_apply_config.py`, `check_config`,
rollback automatique), smoke tests HTTP sur `/local/vssp/*`.

## Statut

🚧 En développement actif — voir `docs/project.md` (changelog) pour le
détail des itérations.
