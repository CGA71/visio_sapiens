# Documentation — Visio Sapiens

[English](README.md) · **Français**

Chaque document existe dans les deux langues : `X.md` en anglais, `X.fr.md` en
français, côte à côte dans le même répertoire, avec un sélecteur de langue en
tête de chacun.

Les quatre domaines ci-dessous répondent à quatre questions différentes.
Choisis selon ce que tu es en train de faire, pas selon le nom d'un fichier.

---

## `dashboards/` — l'interface, et sa génération

Ce que voit l'utilisateur, et la mécanique qui le produit.

| | |
|---|---|
| [Dashboard_Generator](dashboards/Dashboard_Generator.fr.md) | le générateur Jinja2 : modèle, slots, grilles de pièce, langue |
| [Design_System_Editor](dashboards/Design_System_Editor.fr.md) | l'écran THEME de l'ADMIN et la charte qu'il édite |
| [Core_Dashboard](dashboards/Core_Dashboard.fr.md) | `core.html`, le dashboard système |
| [Chatbot_Integration](dashboards/Chatbot_Integration.fr.md) | la carte de discussion HOME et le sélecteur de fournisseur |
| [Google_Calendar](dashboards/Google_Calendar.fr.md) | l'écran Google Calendar et le bandeau d'en-tête |
| [Updates](dashboards/Updates.fr.md) | l'écran MISES À JOUR de l'ADMIN : système, HACS, micrologiciels et le serveur en dessous, séparés |
| [Scheduler](dashboards/Scheduler.fr.md) | l'horloge du tableau INTERRUPTEURS d'une pièce : règles récurrentes, ponctuelles et minuteries |
| [AI_Assistant](dashboards/AI_Assistant.fr.md) | **spécification, pas encore construit** — diagnostic vocal, réparation guidée |

## `platform/` — le socle

Installer et faire tourner ce sur quoi reposent les dashboards. À lire au
moment de monter l'instance, ou quand quelque chose cloche sous l'interface.

| | |
|---|---|
| [Deployment](platform/Deployment.fr.md) | déployer l'assignation des appareils, de bout en bout |
| [Vault](platform/Vault.fr.md) | le coffre HashiCorp Vault : Docker sur k3s, add-on sur HAOS |
| [Security](platform/Security.fr.md) | la posture honnête : ce qui est protégé, ce qui ne l'est pas |
| [Backup_Retention](platform/Backup_Retention.fr.md) | qui écrit des sauvegardes, et qui les élague |
| [mosquitto-k3s](platform/mosquitto-k3s.md) | installer le broker MQTT sur k3s *(français uniquement)* |

## `ci-cd/` — le pipeline

| | |
|---|---|
| [CI_CD](ci-cd/CI_CD.fr.md) | référence complète : stages, garde-fous, variables |
| [Troubleshooting](ci-cd/Troubleshooting.fr.md) | postmortems de terrain et FAQ du panneau ADMIN |

## `project/` — le projet lui-même

| | |
|---|---|
| [Vision](project/Vision.fr.md) | à quoi tout cela sert, et l'architecture complète du système |
| [Integration_Case_Study](project/Integration_Case_Study.fr.md) | intégrer TECHNICAL ROOM dans le dépôt |
| [YouTube_Series](project/YouTube_Series.fr.md) | le plan de la série |
| [episode-01](project/episode-01-vision-architecture.fr.md) | script de tournage de l'épisode 1 — plus `episode-01-narration.fr.txt` (narration seule, pour la synthèse vocale) et `episode-01.fr.srt` (sous-titres) |

---

## Conventions

- **Paires bilingues.** `X.md` et `X.fr.md` voyagent toujours ensemble et vivent
  toujours dans le même répertoire, pour que le sélecteur en tête de chacun
  reste un simple lien frère.
- **Le livré, pas le prévu.** Chaque document ici décrit ce que le code fait
  réellement. La seule exception le dit elle-même, en gras, dès son premier
  paragraphe : `AI_Assistant`.
- **Les liens depuis le code.** Les commentaires de `.gitlab-ci.yml`, des
  packages et de l'outillage Python désignent les documents par chemin complet
  (`docs/platform/Security.md`). Déplacer un document impose de les mettre à
  jour aussi — c'est de la prose, mais un renvoi qui ne résout plus vaut moins
  que pas de renvoi.
