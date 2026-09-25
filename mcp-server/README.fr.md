# Visio Sapiens — serveur MCP

Un serveur [Model Context Protocol](https://modelcontextprotocol.io) qui permet
à un client IA — Claude Desktop, Claude Code, ou tout autre client MCP — de
lire une instance Visio Sapiens vivante : ses pièces, ses entités, ses
dashboards, ses dépendances et ses mises à jour en attente.

## Pourquoi ce n'est pas le serveur MCP Home Assistant communautaire

Les serveurs communautaires exposent du CRUD Lovelace, et ils ne fonctionnent
que sur les dashboards en mode **storage** — ceux qu'une personne assemble en
cliquant dans l'interface.

Les dashboards Visio Sapiens sont en mode **YAML**. Ils sont rendus par
`vssp/generate_dashboards.py` depuis
`home-assistant/dashboards/templates_j2/`, contre le modèle de la maison tenu
par les registres de Home Assistant. Un serveur générique qui écrit des cartes
en mode storage ne peut pas les toucher, et une carte qu'il aurait écrite
serait effacée à la régénération suivante.

Ce serveur ne réimplémente donc pas le générateur. Il lit ce sur quoi le
générateur raisonne, et le remet à l'assistant dans le vocabulaire de ce
projet.

## Pourquoi il vit en dehors de `vssp/`

Tout ce qui est sous `vssp/` est copié dans `/config/vssp` sur chaque instance
par le pipeline de déploiement, et se limite donc à **stdlib + pyyaml** — une
machine Home Assistant OS n'est pas un endroit où l'on demande à un
utilisateur de lancer `pip install`.

Ce serveur tourne sur un poste de travail et dépend du SDK MCP. Le garder dans
un répertoire de premier niveau que le pipeline ne lit jamais est ce qui
préserve cette règle. Le répertoire s'appelle `mcp-server`, avec un trait
d'union, pour qu'il ne puisse pas masquer le paquet `mcp` dans `sys.path`
quand Python démarre depuis la racine du dépôt.

Il ne porte **pas** sa propre copie du client websocket : il importe
`vssp/vssp_ws.py`, pour la raison même qui a fait extraire ce fichier — deux
copies écrites à la main de la RFC 6455 divergent en silence.

## Installation

```bash
cd mcp-server
uv sync            # ou : pip install -e .
```

## Configuration

Deux variables d'environnement, toutes deux posées par le client MCP :

| Variable | Sens | Défaut |
|---|---|---|
| `VSSP_HA_URL` | l'instance à lire | `http://localhost:8123` |
| `HA_TOKEN` | un jeton longue durée pour elle | — |
| `VSSP_HA_TOKEN_FILE` | un fichier en contenant un, à la place de `HA_TOKEN` | `/config/vssp/.ha_token` |

Un jeton s'émet depuis votre page de profil Home Assistant, sous **Jetons
d'accès longue durée**. Rien d'autre ne peut en émettre — ni le Superviseur,
ni ce serveur. (Deux tentatives antérieures d'authentification via le proxy
`/core/websocket` du Superviseur ont échoué pour une raison structurelle : ce
proxy authentifie les **add-ons**, et le conteneur de Core n'en est pas un.
Voir le commentaire sur `auth_routes()` dans `vssp/vssp_dependencies.py`.)

La préproduction et la production sont deux machines avec deux jetons
différents. Pointez un serveur sur une instance ; déclarez deux entrées si vous
voulez les deux.

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "visio-sapiens": {
      "command": "uv",
      "args": ["--directory", "/chemin/absolu/vers/Visio-Sapiens/mcp-server",
               "run", "vssp-mcp"],
      "env": {
        "VSSP_HA_URL": "http://192.168.1.11:8123",
        "HA_TOKEN": "..."
      }
    }
  }
}
```

## L'essayer

```bash
uv run mcp dev vssp_mcp/server.py
```

Cela ouvre l'inspecteur MCP, où chaque outil peut être appelé à la main avant
qu'un client soit branché.

## Les outils

Tous en lecture seule.

| Outil | Répond |
|---|---|
| `vssp_instance` | version de Core, machine OS ou pod k3s, langue déployée |
| `vssp_rooms` | chaque pièce avec son nombre d'entités |
| `vssp_room(room)` | les entités d'une pièce, avec leurs états |
| `vssp_dashboards` | quels dashboards Visio Sapiens existent **en tant que fichiers** |
| `vssp_dependencies` | cartes, intégrations et ressources Lovelace manquantes |
| `vssp_updates` | mises à jour en attente, par famille |
| `find_entities(pattern)` | recherche par sous-chaîne sur les ids et les noms |

`vssp_instance` est celui à appeler en premier. Une machine Home Assistant OS
n'a pas de couche k3s sous elle, et la famille infrastructure y rapporte
correctement `n/a` — un assistant qui saute cette étape proposera à une
machine OS une mise à niveau k3s qui n'existe pas.

## Les pièces ne sont pas là où l'on croit

`vssp_rooms` rapporte le **registre des zones** de Home Assistant. Le
générateur de dashboards ne le lit pas. Son entrée est
`dashboards/model/house.yaml` **sur l'instance**, dont la clé `rooms:` est
écrite par le formulaire de pièces de la console ADMIN et complétée par
l'assistant de découverte — le seul à lire les zones, et il le fait par l'API
template (`{{ areas() }}`), pas par le registre. La copie de `house.yaml` dans
le dépôt est vide par conception.

À l'heure où ceci est écrit, les deux instances de ce projet rapportent **zéro
zone et zéro pièce active**. C'est une maison dont le formulaire de pièces n'a
pas été rempli, pas un appel cassé. `vssp_rooms` renvoie les compteurs du
modèle à côté de la liste du registre précisément pour qu'une réponse vide se
lise au lieu d'inquiéter.

## Ce qui a été vérifié

- Les sept outils s'enregistrent auprès du SDK avec les schémas ci-dessus.
- Le corps de chaque outil a été exécuté contre les registres et les états
  réels de l'instance de production. Deux défauts ont été trouvés ainsi :
  `vssp_updates` renvoyait les *commandes* de l'écran MISES À JOUR
  (`input_boolean`, `input_datetime`, trois `script.*`) mêlées à ses comptes,
  et `vssp_room` répondait « Known rooms: » suivi de rien sur une maison sans
  zone.
- Les deux transports échouent avec une phrase lisible quand le jeton est faux
  (HTTP 401 en REST, `Invalid access token` sur le websocket).
- **Chaque outil a tourné de bout en bout contre les deux instances vivantes**,
  authentifié, et les deux ont été correctement distinguées :

  | | préproduction (pod k3s) | production (HAOS) |
  |---|---|---|
  | `installation` | Core (container / k3s pod) | Home Assistant OS / Supervised |
  | `infrastructure_layers_apply` | `true` | `false` |
  | entités | 2732 | 702 |
  | dashboards présents | aucun | les trois |
  | dépendances manquantes | 5 | 0 |
  | mises à jour en attente | 55 | 10 |

  Cette dernière distinction est tout l'enjeu : une machine OS n'a pas de k3s
  sous elle, et un client qui appelle `vssp_instance` en premier ne peut pas
  lui proposer une version k3s.

## Lecture seule, volontairement

Aucun de ces outils ne change quoi que ce soit. La surface d'action existe déjà
et elle est voulue : les boutons de la console ADMIN, adossés à
`script.vssp_*`, chacun avec sa confirmation et son capteur d'état. Les
brancher est une seconde étape, prise une fois la moitié lecture éprouvée
contre une instance vivante.
