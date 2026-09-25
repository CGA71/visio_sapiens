# Le serveur MCP

Un serveur [Model Context Protocol](https://modelcontextprotocol.io) qui permet
à un client IA — Claude Desktop, Claude Code, n'importe quel client MCP — de
lire une instance Visio Sapiens vivante : ses pièces, ses entités, ses
dashboards, ses dépendances et ses mises à jour en attente.

**Il tourne sur l'instance, pas sur votre poste de travail.** Seul le *client*
est sur votre machine ; le serveur est un service sur la machine qu'il lit,
joint par HTTP. Il n'y a rien à installer sur un poste.

| Cible | Enveloppe | Identifiant |
|---|---|---|
| Home Assistant OS | `addons/vssp-mcp/` — un add-on local | aucun : le Superviseur |
| k3s (préproduction) | `kubernetes/mcp/` — un Deployment | un jeton longue durée dans un Secret |

Les deux exécutent le même paquet Python, `vssp_mcp/`, déployé dans
`/config/vssp_mcp` par le pipeline. Une seule copie du code, deux façons de le
servir.

## Pourquoi pas le serveur MCP de Home Assistant

Deux autres choses portent ce nom, et aucune ne fait ce travail.

**L'intégration `mcp_server` de Home Assistant** rend HA lui-même serveur MCP,
mais n'expose que ce qu'expose l'API LLM configurée — les intentions Assist,
sur les seules entités exposées à l'assistant vocal. Ni dashboards, ni
registres, ni état des mises à jour. (Elle n'est activée sur aucune des deux
instances de ce projet.)

**Les serveurs communautaires** exposent du CRUD Lovelace, et seulement pour
les dashboards en mode **storage** — ceux qu'une personne assemble en cliquant.
Les dashboards Visio Sapiens sont en mode **YAML**, rendus par
`vssp/generate_dashboards.py` depuis `dashboards/templates_j2/`. Une carte
écrite par l'API storage serait effacée à la régénération suivante.

Ce serveur ne réimplémente donc pas le générateur. Il lit ce sur quoi le
générateur raisonne, dans le vocabulaire de ce projet.

## Installer sur Home Assistant OS

Copier `addons/vssp-mcp/` vers `/addons/vssp-mcp` sur l'instance, puis
**Paramètres → Modules complémentaires → Boutique → ⋮ → Vérifier les mises à
jour**. Il apparaît sous *Modules complémentaires locaux*. Même procédure que
`vssp-vault` à côté.

Déployer Visio Sapiens d'abord : l'add-on lit son code dans
`/config/vssp_mcp`, et refuse de démarrer avec un message explicite si ce n'est
pas encore là.

### Aucun jeton, et pourquoi il a fallu trois tentatives

`homeassistant_api: true` dans la configuration de l'add-on est ce qui fait
accepter le conteneur par le Superviseur sur `http://supervisor/core` avec
`SUPERVISOR_TOKEN`. Aucun jeton longue durée à créer, coller ou révoquer.

Cette route a échoué deux fois auparavant, pour `vssp_dependencies.py`
(v1.0.8, v1.0.9), et la raison est structurelle : `/core/websocket` authentifie
les **add-ons**, et ce script tourne dans le conteneur de Core, qui n'en est pas
un. Un add-on en est un, la route devrait donc fonctionner ici.

*Devrait* est le mot qui s'est trompé deux fois, et cela ne peut pas se tester
depuis un poste de travail. Le serveur **sonde** donc chaque route au démarrage
et utilise la première qui répond, en journalisant laquelle. Si le proxy refuse,
mettre `ha_token` dans les options de l'add-on et c'est lui qui sera utilisé —
l'add-on fonctionne dans les deux cas. Voir `routes()` dans `vssp_mcp/ha.py`.

## Installer sur k3s

Il n'y a pas de Superviseur, un jeton longue durée est donc la seule voie
d'entrée. Depuis un clone, sur l'hôte k3s :

```sh
HA_TOKEN=<jeton longue durée> \
MCP_API_TOKEN=<une longue chaîne aléatoire> \
  sudo -E sh kubernetes/mcp/apply-mcp.sh
```

Les deux jetons sont lus dans l'environnement et n'apparaissent jamais dans une
ligne de commande, un manifeste ni le script. `--dry-run` montre ce qui
changerait.

Le script trouve le service de Home Assistant plutôt que de supposer son nom,
construit une ConfigMap depuis le dépôt (le paquet plus `vssp/vssp_ws.py`),
écrit le Secret, applique le Deployment et le Service, et redémarre le rollout —
parce que ni un changement de ConfigMap ni un changement de Secret n'atteint
tout seul un pod en cours d'exécution.

Aucune image privée n'est en jeu : ce GitLab n'a pas de registre de conteneurs,
donc l'exécution utilise l'image publique `python:3.12-alpine` et un conteneur
d'initialisation installe les deux dépendances dans un `emptyDir`.

## Brancher un client

Le point d'accès est `http://<instance>:8099/mcp` (NodePort `30099` sur k3s).

```json
{
  "mcpServers": {
    "visio-sapiens": {
      "type": "http",
      "url": "http://homeassistant.local:8099/mcp",
      "headers": { "Authorization": "Bearer <api_token>" }
    }
  }
}
```

### Posez le jeton

Un point d'accès MCP sur le réseau domestique sans jeton est une fenêtre non
authentifiée sur l'état de chaque entité de la maison. Les outils sont en
lecture seule, mais c'est précisément la lecture qui fuit.

`api_token` (add-on) / `MCP_API_TOKEN` (k3s) est comparé en temps constant à
chaque requête ; sans lui le serveur le dit dans son journal à chaque démarrage
plutôt que de prétendre qu'un port en lecture seule est inoffensif.
L'authentification propre au SDK a la forme d'OAuth et veut un serveur
d'autorisation, ce qui fait beaucoup de pièces mobiles pour un foyer — un secret
partagé est la réponse proportionnée.

## Les outils

Tous en lecture seule.

| Outil | Répond |
|---|---|
| `vssp_instance` | version de Core, machine OS ou pod k3s, identifiant utilisé |
| `vssp_rooms` | les zones de Home Assistant, **et** ce que tient le modèle |
| `vssp_room(room)` | les entités d'une zone, avec leurs états |
| `vssp_dashboards` | quels dashboards Visio Sapiens existent **en tant que fichiers** |
| `vssp_dependencies` | cartes, intégrations et ressources Lovelace manquantes |
| `vssp_updates` | mises à jour en attente, par famille |
| `find_entities(pattern)` | recherche par sous-chaîne sur les ids et les noms |

`vssp_instance` est celui à appeler en premier, et les instructions du serveur
le disent. Une machine Home Assistant OS n'a pas de couche k3s sous elle, et la
famille infrastructure y rapporte correctement `n/a` — un assistant qui saute
cette étape proposera à une machine OS une mise à niveau k3s qui n'existe pas.

### Les pièces ne sont pas là où l'on croit

`vssp_rooms` rapporte le **registre des zones**. Le générateur de dashboards ne
le lit pas. Son entrée est `dashboards/model/house.yaml` **sur l'instance**,
dont la clé `rooms:` est écrite par le formulaire de pièces de la console ADMIN
et complétée par l'assistant de découverte — le seul à lire les zones, et il le
fait par l'API template (`{{ areas() }}`). La copie du dépôt est vide par
conception.

À l'heure où ceci est écrit, les deux instances rapportent **zéro zone et zéro
pièce active**. C'est une maison dont le formulaire de pièces n'a pas été
rempli, pas un appel cassé : l'outil renvoie donc les compteurs du modèle à
côté de la liste du registre — une réponse vide qu'on ne peut pas lire est
indiscernable d'un échec.

## Lecture seule, volontairement

Aucun de ces outils ne change quoi que ce soit. La surface d'action existe déjà
et elle est voulue : les boutons de la console ADMIN, adossés à
`script.vssp_*`, chacun avec sa confirmation et son capteur d'état. Les brancher
est une étape distincte.

## Ce qui a été vérifié

- Les sept outils s'enregistrent auprès du SDK avec les schémas ci-dessus.
- Chaque outil a tourné de bout en bout contre **les deux instances vivantes**,
  authentifié, et les deux ont été correctement distinguées :

  | | préproduction (pod k3s) | production (HAOS) |
  |---|---|---|
  | `installation` | Core (container / k3s pod) | Home Assistant OS / Supervised |
  | `infrastructure_layers_apply` | `true` | `false` |
  | entités | 2734 | 702 |
  | dashboards présents | aucun | les trois |
  | dépendances manquantes | 5 | 0 |
  | mises à jour en attente | 55 | 10 |

- Par HTTP avec un secret partagé : `401` sans jeton, avec un mauvais jeton et
  avec un jeton de mauvaise longueur ; `200` et un vrai résultat d'outil avec le
  bon.
- Deux défauts ont été trouvés en exécutant les outils contre des données
  réelles plutôt qu'en relisant le code : `vssp_updates` renvoyait les
  *commandes* de l'écran MISES À JOUR mêlées à ses comptes, et `vssp_room`
  répondait « Known rooms: » suivi de rien sur une maison sans zone.

Pas vérifié, et invérifiable depuis un poste de travail : la **route
Superviseur** sur un vrai add-on Home Assistant OS. C'est pour cela que le
serveur sonde au lieu de supposer, et que `ha_token` existe en secours.
