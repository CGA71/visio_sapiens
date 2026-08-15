# Visio Sapiens — Neural Home Interface

[English](README.md) · **Français**

Visio Sapiens conçoit des **templates de dashboards Home Assistant
prédéfinis**. On décrit sa maison une seule fois dans une console
d'administration — langue, format, pièces — et toute l'interface est
générée à partir de cette description, puis maintenue à jour au fil des
évolutions. Chaque pièce devient un module système dans un HUD futuriste
inspiré Visio Sapiens.

## Concept

- CORE (Home) — HUD, radar central, IA Core, metrics
- MODULES DE PIÈCE — un dashboard généré par pièce déclarée
- POWER GRID — gestion de l'énergie (solaire, réseau, tableau électrique)
- Bandeau de navigation dynamique, charte graphique néon/glassmorphism

Les dashboards sont **générés**, pas écrits à la main, et **dynamiques** :
ils suivent le modèle de la maison en temps réel au lieu d'être un export
figé.

## Stack

Home Assistant (Lovelace YAML), button-card, card-mod, layout-card,
stack-in-card, apexcharts-card, mini-graph-card, config-template-card,
decluttering-card, browser_mod — thème `Visio Sapiens`, CSS/JS Engine
maison (`www/vssp/`), générateur Jinja2. CI/CD GitLab → k3s.

## Catalogue de dashboards

### Dashboards de pièce

La console admin propose un catalogue fermé de pièces. Chaque pièce
déclarée produit un dashboard issu du même template prédéfini.

| Pièce | Instances multiples |
|---|---|
| Cuisine | — |
| Salon | — |
| Salle à manger | — |
| Entrée | — |
| Buanderie | — |
| Local technique | — |
| Garage | — |
| Cave | — |
| Chambre | ✅ *(n)* |
| Salle de bain | ✅ *(n)* |
| Toilettes | ✅ *(n)* |
| Jardin | — |
| Piscine | — |
| Jacuzzi | — |
| Toit de la maison | — |

Les pièces marquées *(n)* peuvent être instanciées plusieurs fois ; le
générateur ajoute l'index (`Chambre 1`, `Chambre 2`, …). L'identifiant de
pièce (`bedroom`, `living_room`, …) reste en anglais dans toutes les
langues — il alimente les `entity_id`, les chemins de navigation et les
noms de fichiers.

### Dashboards système

Quatre dashboards sont toujours présents. Chacun a son **propre template
prédéfini**, chacun est généré à la création de la maison, et **aucun
n'est lié à un nom de pièce** :

| Dashboard | Rôle | Template |
|---|---|---|
| `HOME` | point d'entrée, HUD et radar central | `home.yaml.j2` |
| `CORE` | supervision du système central | `core.yaml.j2` |
| `ENERGY` | production, consommation, tableau électrique | `energy.yaml.j2` |
| `ADMIN` | la console de création elle-même | `admin.yaml.j2` |

Ils existent dès qu'une maison est créée, quelles que soient les pièces
déclarées — déclarer zéro pièce produit quand même ces quatre-là. Les
dashboards de pièce s'ajoutent ensuite par-dessus, depuis un unique
template de pièce partagé.

### Bandeau de navigation

Le bandeau de navigation à droite est un **template dynamique**. Il part
des quatre entrées système fixes et **se complète avec les pièces
déclarées**, donc sa longueur vaut toujours :

```
4 dashboards système (HOME, CORE, ENERGY, ADMIN)  +  pièces déclarées
```

Ajouter une salle de bain dans la console ajoute son entrée au bandeau sur
tous les dashboards d'un coup. Aucun bloc de navigation n'est maintenu à
la main dans le dépôt.

## Console d'administration

La console (dashboard `ADMIN`) est le point d'entrée unique pour créer et
maintenir la maison. Elle pilote la génération via trois entrées :

| Entrée | Valeurs | Effet |
|---|---|---|
| Sélecteur de langue | Français / Anglais | choisit le catalogue de langue utilisé pour chaque libellé généré |
| Sélecteur de format | Mobile / Tablette | choisit la variante de disposition du template |
| Formulaire de pièces | le catalogue ci-dessus, avec un nombre pour les pièces *(n)* | détermine combien de dashboards de pièce sont générés et la longueur du bandeau de navigation |

Ces trois réponses sont écrites dans `dashboards/model/house.yaml`, qui
est la source de vérité unique. Régénérer depuis ce modèle est
idempotent : les pièces ajoutées plus tard sont créées, le bandeau est
re-rendu, et les dashboards existants sont rafraîchis plutôt que
dupliqués.

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
| Console admin, sélecteur de langue | écrit `locale:` dans `dashboards/model/house.yaml` |
| `generate_dashboards.py` | rend les templates Jinja2 avec ce catalogue |
| Variable CI `VSSP_LOCALE` | rend `config-fragment.yaml` au moment du build |

Trois consommateurs, un seul catalogue :

| Consommateur | Syntaxe |
|---|---|
| Templates Jinja2 | `{{ t('room.bedroom') }}` |
| Fichiers simples (`config-fragment.yaml`, JS, CSS) | `__T:dashboard.energy.title__` |
| Console admin | lit le catalogue fusionné en JSON |

Deux règles empêchent ce mécanisme de casser un dashboard qui fonctionne :

1. **L'état stocké reste en anglais.** Les valeurs d'options des
   `input_select` restent `Day` / `Month` / `Year` dans toutes les
   langues — ce sont des identifiants comparés dans le JavaScript, et
   traduire l'état stocké casserait ces comparaisons. Seul le libellé
   affiché est traduit.
2. **Les dates viennent d'`Intl`, pas de tableaux.** Les blocs JS des
   button-card utilisent `Intl.DateTimeFormat(LOCALE, …)` avec `LOCALE`
   injecté à la génération, ce qui produit `Mon` en anglais et `lun.` en
   français sans travail supplémentaire.

```bash
python3 vssp/vssp_i18n.py check                    # valide tous les catalogues
python3 vssp/vssp_i18n.py dump --locale fr         # inspecte le résultat fusionné
python3 vssp/vssp_i18n.py render --locale fr \
    --in home-assistant/config-fragment.yaml \
    --out /tmp/config-fragment.fr.yaml             # prévisualise un rendu
```

Ajouter une langue consiste à déposer une surcouche `<code>.yaml` dans
`home-assistant/dashboards/locales/` et à la proposer dans la console —
aucune modification de code nulle part.

## Conventions

| Élément | Règle |
|---|---|
| Commentaires de code (YAML, Python, JS, CSS) | un seul fichier, commentaires dans les deux langues, préfixés `# EN \|` et `# FR \|` |
| Chaînes visibles par l'utilisateur | jamais en dur — elles vivent dans les catalogues de langue |
| Documentation (`.md`) | un fichier par langue : `X.md` (anglais) + `X.fr.md`, avec une ligne de bascule en tête |
| Logs des jobs CI, messages de commit, noms de branches | anglais uniquement — destinés au développeur, hors produit localisé |
| Identifiants | anglais uniquement, jamais traduits : clés de pièces, `entity_id`, `path` / `navigation_path`, noms de templates button-card, valeurs d'options `input_select`, noms de `grid-area`, noms de fichiers |

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
    │   │                                (CORE/ENERGY, hors cycle des pièces)
    │   ├── locales/            ← NOUVEAU
    │   │   ├── en.yaml            catalogue de référence — le contrat
    │   │   └── fr.yaml            surcouche française
    │   ├── views/               dashboards de pièce générés + vues système
    │   │   ├── core.yaml
    │   │   ├── computer.yaml
    │   │   ├── energy.yaml          ← GÉNÉRÉ — ne plus éditer à la main
    │   │   ├── energy_mobile.yaml
    │   │   ├── technical_room.yaml
    │   │   └── technical_room_mobile.yaml
    │   ├── model/
    │   │   └── house.yaml         source de vérité : locale, format, pièces, appareils, nav
    │   └── templates_j2/        templates Jinja2, variantes mobile et tablette
    │       ├── home.yaml.j2       ┐
    │       ├── core.yaml.j2       │ les quatre dashboards système,
    │       ├── energy.yaml.j2     │ générés à la création
    │       ├── admin.yaml.j2      ┘
    │       ├── room.yaml.j2       template partagé, un rendu par pièce
    │       └── nav.yaml.j2        bandeau de navigation dynamique
    └── www/vssp/                CSS/JS Engine, composants, console admin, assets
        ├── css/  js/  components/  fonts/  icons/
        ├── wizard/              formulaire web derrière la console admin
        ├── backgrounds/
        └── images/
```

## Chaîne de génération

| Étape | Statut | Où |
|---|---|---|
| 0. Sélecteurs langue et format | 🟡 catalogues et moteur prêts, étape console à brancher | `dashboards/locales/` + `vssp/vssp_i18n.py` |
| 1. Formulaire de pièces | 🟡 pièces déclarées, nombre pour les pièces *(n)* à brancher | `www/vssp/wizard/` |
| 2. Scan des objets connectés | ✅ `vssp_discovery.py` (bouton DISCOVERY SCAN) → `report.json` | `vssp/` |
| 3. Assignation objets → pièces | ✅ sélecteur de pièce par entité | `www/vssp/wizard/` |
| 4. Écriture du modèle de maison | 🔴 à construire — la console doit écrire `house.yaml`, pas seulement `report.json` | `dashboards/model/` |
| 5. Génération des dashboards | 🟡 **fait pour ENERGY** — `energy.yaml.j2` + `generate_dashboards.py` (fidélité 100 % validée par comparaison structurelle) ; à étendre à chaque template de pièce | `dashboards/templates_j2/` + `vssp/` |
| 6. Bandeau de navigation dynamique | 🔴 à construire — rendre le bandeau depuis la liste des pièces au lieu de le maintenir à la main | `dashboards/templates_j2/` |

L'étape 4 est le maillon manquant : écrire les réponses de la console
(langue, format, pièces, assignation des appareils) dans
`dashboards/model/house.yaml`, puis appeler `generate_dashboards.py`.
`vssp_upgrade.py` reste l'outil de diff non destructif pour vérifier les
écarts avant régénération.

## Générer les dashboards

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py    # défauts alignés sur ce repo
```

Le générateur lit `locale:`, `format:` et la liste des pièces depuis
`house.yaml`, et injecte `t()`, `locale` et `locale_tag` dans
l'environnement Jinja2. Détails, garde-fous et intégration
`shell_command` : voir `docs/Generator_templating.md`.

## CI/CD

Pipeline GitLab (`.gitlab-ci.yml`), cinq stages :

| Stage | Ce qu'il fait |
|---|---|
| `validate` | structure du repo, syntaxe YAML, cohérence des catalogues de langue, résolution des substitutions `__T:`, couverture `OSV_PREFIX`, contrôle des secrets versionnés |
| `build` | paquet `dist/`, rendu de la langue dans `config-fragment.yaml`, garde-fou des substitutions non rendues, cache-busting `__VTOKEN__`, résolution des `!include`, garde-fou liste blanche |
| `deploy` | staging sur k3s (branches/MR) ou production sur HAOS via SSH (tags, gate manuelle), garde-fou avant patch, `check_config` et rollback automatique |
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
