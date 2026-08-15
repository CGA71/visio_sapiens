# Visio Sapiens — Neural Home Interface

[English](README.md) · **Français**

Interface Home Assistant futuriste inspirée d'OSVision, pensée pour
tablette et mobile. Chaque pièce devient un module système ; les
dashboards sont progressivement **générés** depuis un modèle métier
plutôt qu'écrits à la main.

## Concept

- CORE (Home) — HUD, radar central, IA Core, metrics
- LIVING / SLEEP MODULES — pièces de vie
- DATA CENTER / ENGINE ROOM — salle informatique, local technique
- POWER GRID — gestion de l'énergie (solaire, réseau, tableau électrique)
- Sidebar de navigation commune, charte graphique néon/glassmorphism

## Stack

Home Assistant (Lovelace YAML), button-card, card-mod, layout-card,
stack-in-card, apexcharts-card, mini-graph-card, config-template-card,
decluttering-card, browser_mod — thème `Visio Sapiens`, CSS/JS Engine
maison (`www/vssp/`). CI/CD GitLab → k3s.

## Langue

**L'anglais est la source de vérité.** Toute chaîne visible par
l'utilisateur vit dans `home-assistant/dashboards/locales/en.yaml` ; les
autres langues sont des surcouches fusionnées par-dessus, donc une clé
manquante retombe sur l'anglais au lieu d'afficher un libellé vide. Une
traduction partielle peut donc être livrée sans risque.

La langue se choisit une seule fois, à la génération — jamais à
l'exécution :

| Où | Ce que ça définit |
|---|---|
| Wizard admin, Phase 0 | écrit `locale:` dans `dashboards/model/house.yaml` |
| `generate_dashboards.py` | rend les templates Jinja2 avec ce catalogue |
| Variable CI `VSSP_LOCALE` | rend `config-fragment.yaml` au moment du build |

Trois consommateurs, un seul catalogue :

| Consommateur | Syntaxe |
|---|---|
| Templates Jinja2 | `{{ t('energy.tab.day') }}` |
| Fichiers simples (`config-fragment.yaml`, JS, CSS) | `__T:dashboard.energy.title__` |
| Wizard admin | lit le catalogue fusionné en JSON |

Deux règles empêchent ce mécanisme de casser un dashboard qui fonctionne :

1. **L'état stocké reste en anglais.** Les valeurs d'options des
   `input_select` restent `Day` / `Month` / `Year` dans toutes les
   langues — ce sont des identifiants comparés dans le JavaScript, et
   traduire l'état stocké casserait ces comparaisons. Seul le libellé
   d'onglet affiché est traduit.
2. **Les dates viennent d'`Intl`, pas de tableaux.** Les blocs JS des
   button-card utilisent `Intl.DateTimeFormat(LOCALE, …)` avec `LOCALE`
   injecté à la génération, ce qui produit `Mon` en anglais et `lun.` en
   français sans travail supplémentaire. Les tableaux `date.*` des
   catalogues n'existent que comme surcharge quand on veut un contrôle
   exact du libellé.

```bash
python3 vssp/vssp_i18n.py check                    # valide tous les catalogues
python3 vssp/vssp_i18n.py dump --locale fr         # inspecte le résultat fusionné
python3 vssp/vssp_i18n.py render --locale fr \
    --in home-assistant/config-fragment.yaml \
    --out /tmp/config-fragment.fr.yaml             # prévisualise un rendu
```

Ajouter une langue consiste à déposer une surcouche `<code>.yaml` dans
`home-assistant/dashboards/locales/` et à définir `VSSP_LOCALE` — aucune
modification de code nulle part.

## Conventions

| Élément | Règle |
|---|---|
| Commentaires de code (YAML, Python, JS, CSS) | un seul fichier, commentaires dans les deux langues, préfixés `# EN \|` et `# FR \|` |
| Chaînes visibles par l'utilisateur | jamais en dur — elles vivent dans les catalogues de langue |
| Documentation (`.md`) | un fichier par langue : `X.md` (anglais) + `X.fr.md`, avec une ligne de bascule en tête |
| Logs des jobs CI, messages de commit, noms de branches | anglais uniquement — destinés au développeur, hors produit localisé |
| Identifiants | anglais uniquement, jamais traduits : `entity_id`, `path` / `navigation_path`, noms de templates button-card, valeurs d'options `input_select`, noms de `grid-area`, noms de fichiers |

## Arborescence du repo

Les répertoires existants sont conservés tels quels ; seuls ceux marqués
**NOUVEAU** sont ajoutés par le générateur de dashboards et la couche
i18n.

```
.
├── .gitlab-ci.yml               validate / build / deploy:staging (k3s)
│                                + smoke tests (/local/vssp/*, cache-busting __VTOKEN__)
├── hacs.json
├── repository.yaml
├── README.md                    version anglaise (rendue par défaut par GitLab)
├── README.fr.md                 ← ce fichier
│
├── docs/
│   ├── project.md               architecture, changelog des itérations
│   ├── modules.md
│   ├── desygn-system.md         charte graphique
│   ├── osvision.md
│   ├── CI_INTEGRATION.md        patch configuration.yaml dans le pipeline
│   └── Generator_templating.md  générateur de dashboards (étape 5)
│
├── kubernetes/                  manifestes k3s (cible staging)
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
│   ├── vssp_energy_sync.py      parc mesuré ENERGY (ajout/retrait)
│   ├── generate_dashboards.py   rend les templates Jinja2
│   ├── build_template.py        templatise un dashboard existant
│   └── vssp_i18n.py             ← NOUVEAU — moteur i18n (load, render, check)
│
└── home-assistant/
    ├── config-fragment.yaml     état désiré des clés Visio Sapiens
    │                            (lovelace, resources) — utilise __VTOKEN__ et __T:cle__
    ├── packages/                vssp_energy_totaux.yaml (totaux dynamiques), …
    ├── templates/               button_card_templates.yaml, decluttering_templates.yaml
    ├── dashboards/
    │   ├── home.yaml            dashboard principal /visio-sapiens (+ vue ADMIN)
    │   ├── home_mobile.yaml     variante mobile /visio-sapiens-m
    │   ├── admin/
    │   │   └── system_dashboards.yaml   carte ADMIN « dashboards système »
    │   │                                (ENERGY/CORE, hors cycle des pièces)
    │   ├── locales/            ← NOUVEAU
    │   │   ├── en.yaml            catalogue de référence — le contrat
    │   │   └── fr.yaml            surcouche française
    │   ├── views/               vues et dashboards autonomes
    │   │   ├── core.yaml
    │   │   ├── computer.yaml
    │   │   ├── energy.yaml          ← GÉNÉRÉ — ne plus éditer à la main
    │   │   ├── energy_mobile.yaml
    │   │   ├── technical_room.yaml
    │   │   └── technical_room_mobile.yaml
    │   ├── model/
    │   │   └── house.yaml         modèle métier (pièces, appareils, circuits, nav, locale)
    │   └── templates_j2/
    │       └── energy.yaml.j2     template Jinja2 (charte graphique ENERGY)
    └── www/vssp/                CSS/JS Engine, composants, wizard, assets
        ├── css/  js/  components/  fonts/  icons/
        ├── wizard/              formulaire web (phases 0-4 du processus admin)
        ├── backgrounds/
        └── images/
```

## Processus admin — génération automatique des dashboards

| Étape | Statut | Où |
|---|---|---|
| 0. Choix de la langue | 🟡 catalogues et moteur prêts, étape wizard à brancher | `dashboards/locales/` + `vssp/vssp_i18n.py` |
| 1. Tablette / mobile | ✅ dashboards `home.yaml` + `home_mobile.yaml` (variantes `-m` déclarées dans `config-fragment.yaml`) | `dashboards/` |
| 2. Formulaire pièces / étages | ✅ wizard Phase 1 | `www/vssp/wizard/` |
| 3. Scan des objets connectés | ✅ `vssp_discovery.py` (bouton DISCOVERY SCAN du panneau ADMIN, ou wizard Phase 2) → `report.json` | `vssp/` |
| 4. Assignation objets → pièces | ✅ wizard Phase 2 (sélecteur de pièce par entité) | `www/vssp/wizard/` |
| 5. Génération des dashboards | 🟡 **fait pour ENERGY** — `energy.yaml.j2` + `generate_dashboards.py` (fidélité 100 % validée par comparaison structurelle) ; à étendre aux autres vues | `dashboards/templates_j2/` + `vssp/` |

Le maillon restant entre 4 et 5 : écrire le résultat de l'assignation du
wizard dans `dashboards/model/house.yaml` (au lieu du seul
`report.json`), avec la langue choisie à l'étape 0, puis appeler
`generate_dashboards.py`. `vssp_upgrade.py` reste l'outil de diff non
destructif pour vérifier les écarts avant régénération.

## Générer les dashboards

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py    # défauts alignés sur ce repo
```

Le générateur lit `locale:` depuis `house.yaml` et injecte `t()`,
`locale` et `locale_tag` dans l'environnement Jinja2. Détails, garde-fous
et intégration `shell_command` : voir `docs/Generator_templating.md`.

## CI/CD

Pipeline GitLab (`.gitlab-ci.yml`), cinq stages :

| Stage | Ce qu'il fait |
|---|---|
| `validate` | structure du repo, syntaxe YAML, cohérence des catalogues de langue, résolution des substitutions `__T:`, couverture `OSV_PREFIX`, contrôle des secrets versionnés |
| `build` | paquet `dist/`, rendu de la langue dans `config-fragment.yaml`, cache-busting `__VTOKEN__`, résolution des `!include`, garde-fou liste blanche |
| `deploy` | staging sur k3s (branches/MR) ou production sur HAOS via SSH (tags, gate manuelle), avec `check_config` et rollback automatique |
| `test` | smoke tests HTTP sur `/local/vssp/*` et sur l'API HA |
| `release` | paquet HACS (incluant chaque `README.*.md`) et release GitLab |

Définir `VSSP_LOCALE` (Settings > CI/CD > Variables, ou au lancement d'un
pipeline) pour construire un livrable dans une autre langue. `en` est la
valeur par défaut et produit le libellé de référence inchangé. Une langue
sans catalogue fait échouer `validate` au lieu d'envoyer des
substitutions non remplacées dans la sidebar de Home Assistant.

## Statut

🚧 En développement actif — voir `docs/project.md` (changelog) pour le
détail des itérations.
