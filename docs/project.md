# Visio Sapiens

OS domotique avec une interface futuriste comparable à celle d'un centre de contrôle.

Le socle repose sur :

* button-card (HUD, navigation, widgets)
* card-mod (CSS avancé)
* layout-card (mise en page libre)
* stack-in-card
* apexcharts-card
* mini-graph-card
* config-template-card
* browser_mod
* decluttering-card
* un moteur CSS et JavaScript propre à Visio Sapiens

L'objectif est que Home Assistant ne soit plus qu'un moteur de données. Toute
l'interface est pilotée par VSSP.

## Architecture

```
Visio Sapiens

├── CORE
│      HUD
│      IA
│      Radar
│      Navigation
│
├── Room Engine
│      Living
│      Bedroom1
│      Bedroom2
│      Bathroom
│      Computer      ← livré
│      Technical     ← livré (desktop + mobile)
│      Secret
│      Garden
│      Energy        ← livré (desktop + mobile)
│
├── IA Layer
│      Widgets
│      Alerts
│      Notifications
│      Assistant
│
├── Animation Engine
├── CSS Engine
├── JS Engine
└── Theme Engine
```

Le dashboard HOME n'est plus un assemblage de cartes : c'est une interface unique.

# Framework Visio Sapiens

1. VSSP Core UI (HUD, navigation, layout)
2. CSS Engine (~800 lignes dédiées à l'identité visuelle)
3. JavaScript Engine (animations, radar, IA, interactions)
4. Templates Button-Card (bibliothèque de composants réutilisables, préfixe `vssp_`)
5. Dashboards basés sur ces composants, sans cartes natives visibles

**Règle :** ne plus utiliser les cartes Lovelace classiques, sauf exceptions
assumées et documentées (`weather-forecast`, `logbook`, `apexcharts-card`).

L'interface est composée de :
* HUD animé
* sidebar verticale de navigation
* radar central
* IA Core
* cartes translucides
* jauges néon CPU / GPU / RAM / Storage / Network
* animations CSS
* composants réutilisables

---

# Structure réelle du dépôt

```
visio-sapiens/
├── .gitlab-ci.yml              pipeline dual-cible (k3s staging / HAOS prod)
├── hacs.json                   distribution HACS (domains: theme)
├── repository.yaml
├── README.md
│
├── themes/                     ← RACINE, imposé par HACS
│      visio_sapiens.yaml       (nom du thème dans les dashboards : "Visio Sapiens")
│
├── docs/
│      project.md               ce fichier
│      core.md                  fonctionnement de core.html
│      CI_CD.md                 référence complète du pipeline
│      DIAGNOSTIC_staging.md
│      INTEGRATION_technical_room.md
│      Generator_templating.md
│
├── vssp/                       scripts Python + config HA associée
│      vssp_apply_config.py     patcher idempotent de configuration.yaml
│      vssp_ensure_packages.py  pose la clé homeassistant.packages
│      vssp_sanitize_resources.py  déduplique les resources Lovelace
│      vssp_discovery.py        scan lecture seule par Area → report.json
│      vssp_upgrade.py          diff découvertes ↔ dashboard (non destructif)
│      vssp_patch_dashboard.py  overlays de plan
│      vssp_lan_probe.py        sonde LAN / Livebox / commutateur
│      vssp_admin_config.yaml   helpers, shell_command, scripts du panneau ADMIN
│      livebox.env              réglages NON secrets de la box (versionné)
│      .livebox.env             secret, généré au déploiement — JAMAIS versionné
│
└── home-assistant/
    ├── config-fragment.yaml    état désiré des clés Visio Sapiens de configuration.yaml
    │
    ├── packages/               packages HA multi-domaines
    │      vssp_technical_room.yaml
    │      spvs_energy_totaux.yaml
    │
    ├── templates/              cible des `!include ../templates/…` des vues
    │      button_card_templates.yaml
    │      decluttering_templates.yaml
    │
    ├── dashboards/
    │      home.yaml            vue d'ensemble desktop (+ vue cachée ADMIN)
    │      home_mobile.yaml     vue d'ensemble mobile
    │      views/
    │          core.yaml               iframe vers core.html
    │          computer.yaml
    │          energy.yaml
    │          energy_mobile.yaml
    │          technical_room.yaml
    │          technical_room_mobile.yaml
    │
    └── www/
        └── vssp/               servi par HA sous /local/vssp/
            ├── core.html       dashboard système autonome (Glances + K3s)
            ├── css/
            │      vssp.css     CSS Engine
            ├── js/
            │      osvision.js  JS Engine (bus pub/sub + helpers)  ⚠️ à renommer
            ├── components/
            │      osv-core.js
            │      osv-card.js
            │      osv-datetime-card.js
            │      osv-ad-banner-card.js
            ├── backgrounds/    core.png, home.png, energy.png (technical.png manquant)
            ├── images/
            ├── icons/
            └── fonts/
```

## Dashboards déclarés (`config-fragment.yaml`)

| url_path | Titre | Fichier | Sidebar |
|---|---|---|---|
| `visio-sapiens` | Visio-Sapiens | `dashboards/home.yaml` | ✔ |
| `visio-sapiens-m` | Visio-Sapiens | `dashboards/home_mobile.yaml` | ✔ |
| `visio-sapiens-core` | Core System | `dashboards/views/core.yaml` | — |
| `visio-sapiens-computer` | Computer Room | `dashboards/views/computer.yaml` | — |
| `visio-sapiens-energy` | Energy Management | `dashboards/views/energy.yaml` | — |
| `visio-sapiens-energy-m` | Energy Management | `dashboards/views/energy_mobile.yaml` | — |
| `visio-sapiens-technical` | Technical Room | `dashboards/views/technical_room.yaml` | — |
| `visio-sapiens-technical-m` | Technical Room | `dashboards/views/technical_room_mobile.yaml` | — |

Le préfixe `visio-sapiens` n'est pas cosmétique : `vssp_apply_config.py` ne
fusionne dans `configuration.yaml` que les clés qui commencent par
`OSV_PREFIX = "visio-sapiens"`. **Toute nouvelle entrée doit suivre cette
convention**, sinon elle sera silencieusement ignorée au déploiement.

# Ressources Lovelace déclarées

Cartes HACS : button-card, layout-card, card-mod, stack-in-card,
apexcharts-card, mini-graph-card, config-template-card, decluttering-card.

Moteurs maison, servis depuis `/local/vssp/` avec un cache-buster `?v=__VTOKEN__`
remplacé au déploiement par la version du build.

⚠️ **Écart connu** — le fragment déclare aujourd'hui `/local/vssp/css/osvision.css`
alors que le fichier s'appelle `css/vssp.css`, et le smoke test de la CI
interroge `/local/vssp/js/vssp.js` alors que le fichier s'appelle `js/osvision.js`.
Le CSS Engine part donc en 404 et le job `test:staging` échoue. Correctif détaillé
en **G1 de `CI_CD.md`**.

---

# CHANGELOG — Évolutions depuis la V2 initiale

## Navigation

* La barre horizontale HOME / ROOMS / SYSTEM / ENERGY du squelette d'origine a
  été remplacée par une **sidebar verticale** pleine hauteur (logo en tête,
  items icône + titre + sous-titre, highlight actif, hover sur toute la liste,
  branding animé en pied de sidebar).
* Nouveaux templates : `vssp_sidebar_logo`, `vssp_nav_button` (refondu),
  `vssp_sidebar_brand_footer`.
* Version mobile : barre de navigation **une ligne défilante** (champ custom de
  largeur fixe + `overflow-x` + `touch-action: pan-x`), transposition du pattern
  du tableau électrique d'`energy_mobile.yaml`.

## Bandeau HUD (header)

* Bandeau à 5 cases reproduisant la maquette cible :
  1. Chevron retour + titre de page + descriptif (`vssp_page_header`)
  2. Météo extérieure — carte **native** `weather-forecast`
  3. Date/heure en direct — composant custom `osv-datetime-card`
  4. Statut alarme (squelette générique, réagit à `entity.state` quel que soit
     le domaine) — `vssp_alarm_status`
  5. Avatar circulaire « OS » — `vssp_os_avatar`

## Rangée Énergie (vue HOME)

1. Courbe production solaire / consommation — `apexcharts-card` (2 séries)
2. Synthèse kW production / consommation — `vssp_metric`
3. Événements des appareils connectés — carte **native** `logbook`
4. Panneau Sécurité/Alarme — badge circulaire réactif + 4 lignes de statut
   (`vssp_security_badge`, `vssp_security_row`)

## Dashboard ENERGY

* Vue autonome desktop + vue mobile dédiée.
* Panneaux : production solaire, consommation par appareil (8 lignes),
  consommation totale, schéma de fonctionnement, excédent/revente EDF,
  tableau électrique (12 circuits `vssp_circuit_switch`).
* Package `spvs_energy_totaux.yaml` : somme des `*_energie` →
  `sensor.home_energy_total`.

## Dashboard TECHNICAL ROOM

* Vues desktop et mobile, package `vssp_technical_room.yaml`, sonde LAN
  `vssp_lan_probe.py` (Livebox + commutateur Netgear).
* Les liens de navigation existants (`/visio-sapiens-technical/technical`, chip
  TECH du mobile) étaient déjà en place : l'intégration les a rendus vivants
  sans toucher à la navigation.
* Secret de la box géré par variable CI/CD masquée, jamais versionné.

## Dashboard CORE

* La vue affichait en double les jauges/charts/températures/K3s : cartes
  natives HA **et** iframe vers `core.html`, qui recrée déjà tout en JS.
  Les cartes natives ont été retirées ; la vue ne contient plus que sidebar +
  première ligne du bandeau + iframe + footer.
* Voir `docs/core.md` pour la chaîne complète Glances → HA → page.

## Composants JS

* `osv-card.js` (footer) et `osv-datetime-card.js` ont été rendus **autonomes** :
  ils calculent l'heure/date nativement au lieu de dépendre du moteur, suite à
  un bug où cette dépendance échouait silencieusement dans certains déploiements.
* Le moteur JS est conservé pour son bus pub/sub et ses helpers de
  couleur/seuils (`clamp`, `colorForValue`), réutilisables par de futurs
  composants. Il s'expose encore en `window.osvision` — à renommer en même temps
  que le fichier.

## Panneau ADMIN

* Vue cachée `/visio-sapiens/admin` (desktop) et `/visio-sapiens-m/admin`
  (mobile), non liée dans le menu, restreinte à un utilisateur HA précis via
  `visible:`.
* Trois actions :
  - **DISCOVERY** — lance `vssp_discovery.py` (scan lecture seule des entités
    par Area).
  - **UPGRADE** — lance `vssp_upgrade.py` (compare le rapport de découverte au
    dashboard actuel, liste les écarts — ne modifie jamais le YAML).
  - **DELETE DASHBOARD** — protégé par code PIN + confirmation native +
    sauvegarde automatique. Retour visuel par `browser_mod.popup`.
* ⚠️ **Deux défauts ouverts dans `vssp_admin_config.yaml`** :
  les `shell_command` de sauvegarde et de suppression visent
  `/config/home-assistant/dashboards/home.yaml`, chemin qui n'existe pas sur le
  pod (le déploiement installe les dashboards en `/config/dashboards/`) — la
  sauvegarde du bouton DELETE est donc un no-op ; et `input_text.vssp_ha_token`
  est utilisé sans être déclaré. Détails dans `Generator_templating.md`.
* ⚠️ Les scripts `vssp_discovery.py` / `vssp_upgrade.py` **ne sont pas copiés
  dans le paquet de déploiement** : les boutons sont inertes en staging comme en
  production tant que le correctif G2 de `CI_CD.md` n'est pas appliqué.

## Industrialisation (déploiement)

* `config-fragment.yaml` : état désiré des clés Visio Sapiens de
  `configuration.yaml`, appliqué par un patcher idempotent qui **préserve tout
  le reste** du fichier (clés tierces, ordre, commentaires, tags `!include`) et
  crée une sauvegarde horodatée avant toute écriture.
* Pipeline GitLab dual-cible : MR/`master` → k3s (staging), tag → HAOS
  (production, gate manuelle). Contrôle des `!include`, cache-busting des
  ressources, smoke tests, rollback automatique sur échec de `check_config`.
* Voir `docs/CI_CD.md` pour le détail et les cinq trous encore ouverts.

## Migration de nommage OSVision → VSSP — état

| Élément | État |
|---|---|
| Nom du projet, README, `hacs.json`, `repository.yaml` | ✅ |
| Dossier `vssp/`, scripts `vssp_*.py` | ✅ |
| `home-assistant/www/vssp/`, URL `/local/vssp/` | ✅ |
| Templates button-card `vssp_*` | ✅ |
| Clés de dashboards `visio-sapiens-*` + `OSV_PREFIX` | ✅ |
| Thème `themes/visio_sapiens.yaml` | ✅ |
| `css/vssp.css` | ✅ fichier renommé, ❌ URL du fragment non mise à jour |
| `js/osvision.js`, global `window.osvision` | ❌ à renommer |
| Fichier de version `OSVISION_VERSION` produit par la CI | ❌ à renommer en `VSSP_VERSION` |
| Clé `localStorage` `osv_ha_token` de `core.html` | ⏸ à migrer avec précaution (casse les sessions) |
| Chemin K3s `/local/osvision_v2/k3s_stats.json` dans `core.html` | ❌ cassé, corriger en `/local/vssp/` |
| Commentaires internes `osvision_*` dans `vssp.css` | ⏸ cosmétique |
| Préfixes `OSV_PREFIX`, `OSV_VERSION`, `.osv_stage` (internes CI) | ⏸ sans impact fonctionnel |

## Prochaines pistes identifiées

* Appliquer les correctifs G1 → G5 de `CI_CD.md` (dans cet ordre : ressources,
  scripts admin, version, générateur, robustesse).
* Générateur de dashboards piloté par modèle (`model/house.yaml` +
  `templates_j2/*.j2`) — voir `Generator_templating.md`. Étape suivante :
  `vssp_model_sync.py`, pont entre le rapport de découverte et le modèle.
* Basculer les popups **Discovery** et **Upgrade** sur `browser_mod.popup`
  (actuellement encore en `persistent_notification`).
* Automation de détection de nouvelle entité non assignée à une Area, avec
  notification actionnable proposant de l'assigner.
* Vues de pièces restantes (Living, Bedroom1/2, Bathroom, Secret, Garden),
  idéalement générées depuis un `room.yaml.j2` unique plutôt qu'écrites à la main.
