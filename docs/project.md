# Visio Sapiens

OS domotique avec une interface futuriste comparable à celle d'un centre de contrôle.

le socle doit se reposer sur :

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

L'objectif est que Home Assistant ne soit plus qu'un moteur de données. Toute l'interface est pilotée par VSSP.

Architecture
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
│      Computer
│      Technical
│      Secret
│      Garden
│      Energy
│
├── IA Layer
│      Widgets
│      Alerts
│      Notifications
│      Assistant
│
├── Animation Engine
│
├── CSS Engine
│
├── JS Engine
│
└── Theme Engine
```

Le dashboard HOME ne sera plus un assemblage de cartes

Il deviendra une interface unique.

mon project OS Vsion V2 :

![dashboard-VSSP](VSSP.png)

# Framework Visio Sapiens

1- VSSP Core UI (HUD, navigation, layout)
2- CSS Engine (~800 lignes dédiées à l'identité visuelle)
3- JavaScript Engine (animations, radar, IA, interactions)
4- Templates Button-Card (bibliothèque de composants réutilisables)
5- Dashboard HOME V2 basé sur ces composants, sans cartes natives visibles

Attention : ne plus utilisé les cartes lovelace classique

L'interface est composée de :
* HUD animé
* barre de navigation HOME / ROOMS / SYSTEM / ENERGY
* radar central
* IA Core
* cartes translucides
* jauges néon CPU / GPU / RAM / Storage / Network
* animations CSS
* composants réutilisables

# structure repository
```
home-assistant/
├── docs
│      project.md
│      modules.md
│      desygn-system.md
│      VSSP.md
│      VSSP.png
│
├── dashboards/
│      home.yaml(vue d'ensemble)
│      core.yaml (system central)
│      livingroom.yaml
│      bedroom1.yaml
│      bedroom2.yaml
│      bathroom.yaml
│      computerroom.yaml
│      technicalroom.yaml
│      secretroom.yaml
│      garden.yaml
│      energy.yaml
│
├── templates/
│      button_card_templates.yaml
│
├── themes/
│      VSSP_v2.yaml
│
└── www/
    └── VSSP_v2/
        ├── css/
        │      VSSP.css
        │
        ├── js/
        │      VSSP.js
		│
		├── components
		│      osv-card.js
		│      osv-core.js
        │
        ├── backgrounds/
		│      core.png
		│      home.png
		│
		├── images/
        ├── icons/
        └── fonts/
```

# Ressource lovelace ajouté
* button-card
* layout-card
* card-mod
* stack-in-card
* apexcharts-card
* mini-graph-card
* config-template-card
* decluttering-card

# home.yaml
* HUD Visio Sapiens
* Navigation HOME / LIVINGROOM / BEDROOM1 / BEDROOM2 / BATHROOM / COMPUTER ROOM / TECHNICAL ROOM / SECRET ROOM / GARDEN / ENERGY
* Radar central
* IA Core
* Metrics CPU / GPU / RAM / Storage / Network
* Quick Actions
* Alertes
* Footer
* compatible avec les templates button-card

---

# CHANGELOG — Évolutions depuis la V2 initiale

Cette section documente ce qui a été ajouté par rapport au squelette
d'origine ci-dessus, au fil des itérations.

## Navigation

* La barre de navigation HOME / ROOMS / SYSTEM / ENERGY horizontale du
  squelette d'origine a été remplacée par une **sidebar verticale**
  pleine hauteur (logo en tête, items icône + titre + sous-titre,
  highlight actif, hover sur toute la liste, logo/branding animé en
  pied de sidebar).
* Nouveaux templates : `VSSP_sidebar_logo`, `VSSP_nav_button`
  (refondu), `VSSP_sidebar_brand_footer`.

## Bandeau HUD (header)

* Le header générique ("Visio Sapiens — NEURAL CORE ACTIVE") a été
  remplacé par un **bandeau à 5 cases**, reproduisant la maquette
  cible :
  1. Chevron retour + titre de page + descriptif (`VSSP_page_header`)
  2. Météo extérieure — carte **native** `weather-forecast`
  3. Date/heure en direct — composant custom `osv-datetime-card`
  4. Statut alarme (squelette générique, réagit à `entity.state`
     quel que soit le domaine) — `VSSP_alarm_status`
  5. Avatar circulaire "OS" — `VSSP_os_avatar`

## Rangée Énergie (vue HOME uniquement)

* Nouvelle rangée sous les quick actions, avant le footer :
  1. Courbe production solaire / consommation — carte native
     `apexcharts-card` (2 séries)
  2. Synthèse kW production / consommation — `VSSP_metric`
  3. Événements des appareils connectés — carte **native** `logbook`
  4. Panneau Sécurité/Alarme (remplace l'emplacement météo détaillée
     de la maquette) — badge circulaire réactif + 4 lignes de statut
     (`VSSP_security_badge`, `VSSP_security_row`)

## Composants JS

* `osv-card.js` (footer) et `osv-datetime-card.js` ont été rendus
  **autonomes** : ils calculent l'heure/date nativement au lieu de
  dépendre de `window.VSSP.formatTime()/formatDate()`, suite à un
  bug où cette dépendance échouait silencieusement dans certains
  déploiements.
* `VSSP.js` (moteur) conservé pour son bus pub/sub et ses helpers
  de couleur/seuils, réutilisables par de futurs composants.

## Panneau ADMIN (nouveau, hors sidebar de navigation)

* Vue cachée `/VSSP-v2/admin` (non liée dans le menu), restreinte
  à un utilisateur HA précis via `visible:`.
* Trois actions :
  - **DISCOVERY** — lance `VSSP_discovery.py` (scan en lecture
    seule des entités par Area/pièce).
  - **UPGRADE** — lance `VSSP_upgrade.py` (compare le rapport de
    découverte au dashboard actuel, liste les écarts — non destructif,
    ne modifie jamais le YAML).
  - **DELETE DASHBOARD** — protégé par code PIN + confirmation native
    + sauvegarde automatique avant toute suppression. Retour visuel
    par popup `browser_mod.popup` (succès ou échec), plutôt qu'une
    simple notification discrète.
* Nouveau dossier `VSSP/` à la racine du repo : scripts Python
  (`VSSP_discovery.py`, `VSSP_upgrade.py`) + config HA associée
  (`VSSP_admin_config.yaml` : helpers, shell_command, scripts).

## Prochaines pistes identifiées (en cours de developpement)

* Basculer les popups **Discovery** et **Upgrade** sur `browser_mod.popup`
  également (actuellement encore en `persistent_notification`).
* Générateur automatique de dashboard piloté par formulaire
  (config_flow HA : nombre de pièces, mapping vers les Areas HA
  existantes, choix de thème) — actuellement seule la brique de
  découverte en lecture seule existe.
* Automation de détection de nouvelle entité non assignée à une Area,
  avec notification actionnable proposant de l'assigner.
