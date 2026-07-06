# OSVision V2

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
* un moteur CSS et JavaScript propre à OSVision V2

L'objectif est que Home Assistant ne soit plus qu'un moteur de données. Toute l'interface est pilotée par OSVision.

Architecture
OSVision V2

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

Le dashboard HOME ne sera plus un assemblage de cartes

Il deviendra une interface unique.

Par exemple :

![Texte alternatif](/docs/osvion.png)

# Framework OsVision V2

1- OSVision Core UI (HUD, navigation, layout)
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

home-assistant/
├── docs
│      project.md
│      modules.md
│      desygn-system.md
│      osvision.md
│      osvision.png
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
│      osvision_v2.yaml
│
└── www/
    └── osvision_v2/
        ├── css/
        │      osvision.css
        │
        ├── js/
        │      osvision.js
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
* HUD OSVision V2
* Navigation HOME / LIVINGROOM / BEDROOM1 / BEDROOM2 / BATHROOM / COMPUTER ROOM / TECHNICAL ROOM / SECRET ROOM / GARDEN / ENERGY
* Radar central
* IA Core
* Metrics CPU / GPU / RAM / Storage / Network
* Quick Actions
* Alertes
* Footer
* compatible avec les templates button-card