# Visio Sapiens — Assistant IA (diagnostic vocal, alertes, réparation guidée)

**Français** · [English](AI_Assistant.md)

> **STATUT — SPÉCIFICATION, PAS ENCORE IMPLÉMENTÉE.**
> Rien de ce qui est décrit ici n'est livré dans la version actuelle. Aucun
> fichier de la section 8 n'existe encore. Ce document est la conception
> retenue et la procédure de déploiement à suivre une fois le code écrit ;
> tous les autres documents de `docs/` décrivent un comportement livré,
> celui-ci non.

## Principe

Trois besoins ont été exprimés : le diagnostic vocal d'un appareil
défaillant, l'annonce vocale d'un événement important (intrusion, panne
d'arrosage, n'importe quel objet connecté hors service), et
l'accompagnement au rétablissement. Cela ressemble à une seule
fonctionnalité. Ce n'en est pas une.

**Le découpage se fait par criticité, pas par emplacement.**

| Chemin | Exigence | Conséquence |
|---|---|---|
| **Alerte** | ne doit *jamais* échouer | local, déterministe, **aucun LLM sur le chemin critique** |
| **Diagnostic** | peut échouer sans gravité | LLM, à la demande |

Une intrusion peut commencer par couper la connexion internet. Tout ce qui
doit être prononcé ce jour-là est local et pré-écrit. Cette seule phrase
est la raison pour laquelle cette fonctionnalité est coupée en deux au lieu
d'être un agent conversationnel unique.

```
┌─ MACHINE D'INFÉRENCE (Ubuntu + Docker + GPU) ────────┐
│   Ollama :11434    Piper :10200    Whisper :10300    │
└───────────────▲──────────────────────▲───────────────┘
                │ LAN                  │ LAN
    ┌───────────┴────────┐   ┌─────────┴───────────────┐
    │ STAGING (pod k3s)  │   │ PRODUCTION (HAOS 18.1)  │
    │ pas de Supervisor  │   │ hassio.* disponible     │
    │ sortie = notif     │   │ sortie = enceinte réseau│
    └────────────────────┘   └─────────────────────────┘

  CHEMIN ALERTE     capteur anomalies ──► phrase figée (locales) ──► Piper
                    sans internet, sans LLM, sans cloud

  CHEMIN DIAGNOSTIC voix/texte ──► broker ──► Ollama ──► JSON contraint
                                      │
                                      └──► liste blanche script.vssp_fix_*
                                           (toujours validé par l'utilisateur)
```

## 1. Pourquoi le chemin d'alerte ne porte aucun LLM

Une annonce de sécurité doit être immédiate, identique à chaque fois, et
indépendante de tout service susceptible d'être indisponible. Un modèle —
local ou distant — échoue sur les trois : il ajoute de la latence, il peut
reformuler, et il peut être en panne. L'alerte lit donc une **chaîne figée
dans les fichiers de locale existants** (`home.alarm.intrusion` et ses
voisines existent déjà dans `dashboards/locales/`) et la transmet à Piper.

Le LLM peut enrichir une alerte *après* qu'elle a été prononcée. Il n'est
jamais sur le chemin entre la détection et la parole.

## 2. Livraison 1 — le moteur d'anomalies

Aucune IA, aucune voix. C'est la fondation : sans lui, l'assistant n'a rien
à analyser et les alertes n'ont rien à annoncer.

Un `sensor.vssp_anomalies` dont l'état est le nombre et dont les attributs
portent la liste, chaque entrée avec une `severity` `critical` ou
`warning`.

| Source | Détecte | Notes |
|---|---|---|
| Entités `unavailable` / `unknown` au-delà de N minutes | tout objet connecté qui ne répond plus | le cas général « appareil HS » |
| `last_triggered` d'une automation vs. son horaire attendu | **le cas arrosage** | détecte une *absence d'action*, pas une panne |
| Niveau de batterie sous un seuil | capteurs mourants, avant qu'ils ne se taisent | |
| Registre d'issues de Home Assistant (panneau Réparations) | les problèmes que HA remonte lui-même | signal gratuit, aucun code de détection à écrire |
| `sensor.vssp_core_health` | CPU / RAM | existe déjà, `packages/vssp_home_status.yaml` |
| `binary_sensor.vssp_energy_health` | production vs. consommation | existe déjà |
| `vssp/vssp_lan_probe.py` | MAC inconnue sur le LAN | le volet intrusion informatique ; voir la limite en section 5 |

La règle « horaire attendu vs. `last_triggered` » est celle qui mérite le
plus de soin. Une automation d'arrosage qui ne s'est jamais déclenchée ne
remonte d'erreur nulle part : toutes les entités sont saines, rien n'est
`unavailable`, et aucune intégration ne se plaint. C'est la classe de
défaillance la plus souvent oubliée dans une installation domotique, et
c'est celle qui a été nommée.

## 3. Livraison 2 — voix et alertes

**Piper et Whisper tournent en simples conteneurs Docker sur la machine
d'inférence, pas en add-ons HAOS.** Les deux sont des serveurs du protocole
Wyoming, et Home Assistant les joint via l'intégration native `wyoming` en
TCP. Une seule installation, la même intégration et la même forme de
configuration sur les deux environnements — seule l'adresse change. Des
add-ons auraient été plus simples en production et impossibles en staging.

### Les deux niveaux

| Niveau | Exemples | Chemin | LLM |
|---|---|---|---|
| **Critique** | intrusion, fumée, fuite d'eau | phrase figée → Piper → moins d'une seconde, fonctionne WAN coupé | jamais |
| **Important** | arrosage muet, module HS, disque plein | groupé, formulé en langage naturel | peut enrichir |

### Aiguillage de la sortie

Un helper `input_select.vssp_voice_output_mode` avec `speaker`,
`notification`, `both`. La production annonce sur l'enceinte réseau ; le
staging écrit une `persistent_notification` et une ligne de log. Même code
des deux côtés, et toute la chaîne reste testable en staging sans jamais
émettre un son — ce qui est de toute façon ce que l'on veut là-bas : on y
teste l'enchaînement, pas l'acoustique. Voir la section 6 pour la raison
pour laquelle le staging ne peut de toute façon pas joindre une enceinte
Cast.

## 4. Livraison 3 — l'écran ADMIN « ASSISTANT IA »

Un septième écran dans la console d'administration. La liste des écrans est
une simple liste de tuples dans `dashboards/templates_j2/admin.yaml.j2`,
plus deux clés de locale par langue.

### Le broker — le modèle ne détient jamais de jeton

On ne donne jamais de compte Home Assistant au modèle. Le sens est inversé :

```
Home Assistant construit un contexte ciblé et expurgé
        ▼
Ollama — répond dans une forme JSON contrainte :
        { diagnostic, action_id, confiance, sources }
        ▼
Home Assistant valide action_id contre une LISTE BLANCHE
        ▼
L'utilisateur confirme — toujours, pour chaque action
        ▼
script.vssp_fix_<action_id> s'exécute
```

La liste blanche contient des **noms de scripts du projet**
(`script.vssp_fix_reload_integration`), jamais des noms de services bruts.
Le modèle renvoie un identifiant ; Home Assistant le traduit. **Le modèle
ne compose jamais un appel de service.** C'est ce qui rend une injection de
prompt survivable : son meilleur résultat est une mauvaise suggestion tirée
d'une liste connue, pas une action arbitraire.

Cela compte parce que les vecteurs d'injection sont déjà présents. Les
titres d'événements de calendrier proviennent de quiconque peut envoyer une
invitation (`packages/vssp_google.yaml`), et les noms conviviaux d'entités,
les corps de notification et les noms d'appareils découverts sont autant de
textes que le foyer ne contrôle pas entièrement. Un modèle détenant un
jeton admin pourrait se voir ordonner, par une invitation de calendrier, de
désarmer l'alarme — et un jeton admin peut appeler *n'importe quel*
service, y compris les `shell_command.*` du projet, ce qui équivaut à une
exécution de code arbitraire dans le conteneur Home Assistant.

### L'échelle d'actions

| Niveau | Exemple | Qui décide |
|---|---|---|
| **L0 — lecture** | états, historique, logs, changelog | le modèle, librement |
| **L1 — réversible** | recharger une intégration, relancer une automation, redémarrer un add-on | **le modèle propose, l'utilisateur valide** |
| **L2 — perturbant** | `homeassistant.restart`, `hassio.host_reboot` | confirmation explicite |
| **L3 — destructif** | `hassio.restore_full` | confirmation à l'écran, jamais vocale seule |

Le niveau L1 demande toujours. C'est un choix délibéré : c'est le seul
réglage qui reste sain si un texte injecté atteint un jour le contexte.

Les services `hassio.*` n'existent qu'en production — voir la section 6.

Un assistant qui redémarre le système où il vit ne peut pas en rapporter le
résultat. L'intention est écrite dans un fichier avant le redémarrage,
relue au démarrage, et le résultat annoncé à ce moment-là.

### La recherche de correctifs

Deux sources, dans cet ordre :

1. **Les notes de version de Home Assistant.** Comparer la version
   installée à la dernière et lire les *breaking changes* de l'écart. La
   plupart des pannes « ça marchait hier » sont l'effet de bord d'une mise
   à jour. Source structurée et fiable, joignable avec `urllib` seul — même
   discipline « stdlib uniquement » que `vssp_chatbot_send.py`.
2. **La recherche web ouverte — plus tard, optionnelle.** Un modèle local
   n'a aucun accès web par lui-même. Si le besoin se confirme, un conteneur
   SearxNG auto-hébergé sur la machine d'inférence permet au broker de
   chercher et d'injecter les résultats, sans qu'aucune donnée du foyer ne
   parte chez un tiers. Les trouvailles sont toujours sourcées et **jamais
   appliquées automatiquement**.

## 5. Ce que cette fonctionnalité ne peut pas faire

**Si Home Assistant est mort, l'assistant est mort.** Toute la chaîne —
webhook, `shell_command`, Python, iframe — tourne à l'intérieur de Home
Assistant.

| État | Assistant |
|---|---|
| Dégradé (un appareil HS, une automation muette) | fonctionne, et sert à quelque chose |
| Mort (ne démarre plus, configuration invalide) | indisponible — précisément quand on voudrait « restaure le système » |

La sortie de secours vit donc **hors** de Home Assistant, et existe déjà :
`rollback:production` dans `.gitlab-ci.yml` lance
`ha backups restore <slug>` en SSH sur le port 22222, indépendamment de
l'état de Home Assistant. L'assistant couvre les états *dégradés* ; le
rollback CI couvre les états *morts*.

**Un LLM ne détecte pas les virus informatiques ni les intrusions
réseau.** C'est le métier d'un IDS, pas d'un assistant conversationnel.
`vssp_lan_probe.py` peut lever « une MAC inconnue est apparue sur le LAN »,
et l'assistant peut *expliquer* cette alerte — il ne peut pas la
*produire*. Tout ce qui va au-delà demande un vrai IDS et sort du périmètre
de cette fonctionnalité.

## 6. Staging et production ne sont pas le même Home Assistant

Trois divergences, toutes à traiter dans le code plutôt qu'à découvrir à
l'exécution.

| | Staging (pod k3s) | Production (HAOS 18.1) |
|---|---|---|
| Supervisor | **absent** — un Home Assistant conteneurisé n'en a pas | présent |
| Services `hassio.*` | **n'existent pas** — ni `restore_full`, ni `host_reboot`, ni `backup_full` | disponibles |
| Add-ons | n'existent pas | disponibles (inutilisés ici — Wyoming tourne sur la machine d'inférence) |
| Découverte Cast / Sonos | **impossible** — le multicast mDNS ne traverse pas un overlay CNI sans `hostNetwork: true` | fonctionne |
| Mode de sortie vocale | `notification` | `speaker` |

**Garde-fou pour `hassio.*` :** Home Assistant ne valide pas l'existence
d'un service au chargement d'un script, seulement à l'appel — la
configuration se charge des deux côtés, et en staging l'appel échoue en
silence. Un `binary_sensor.vssp_supervisor_available` (piloté par la
présence d'une entité fournie par le Supervisor — l'identifiant exact est à
figer contre l'instance réelle) conditionne les scripts L2/L3, qui
annoncent alors « action indisponible sur cet environnement » au lieu
d'échouer sans bruit.

## 7. Procédure de déploiement

### 7.1 Machine d'inférence — une seule fois, hors CI

La machine est un simple Ubuntu Server avec les pilotes NVIDIA et Docker.
Home Assistant n'y est **pas** installé : HAOS ne porte aucun pilote NVIDIA
ni CUDA, donc installer HAOS sur la machine GPU gaspillerait la carte. Les
garder séparés est précisément ce qui rend le GPU exploitable.

Trois conteneurs, joignables depuis le LAN :

| Service | Port | Rôle |
|---|---|---|
| Ollama | 11434 | le modèle de diagnostic |
| Piper | 10200 | synthèse vocale (Wyoming) |
| Whisper | 10300 | reconnaissance vocale (Wyoming) |

À vérifier depuis **les deux** environnements avant d'aller plus loin — si
ces trois-là ne répondent pas, rien d'autre dans cette fonctionnalité ne
peut fonctionner :

```bash
curl -s http://<machine-inference>:11434/api/tags   # Ollama : la liste des modèles
nc -z <machine-inference> 10200 && echo "piper ok"
nc -z <machine-inference> 10300 && echo "whisper ok"
```

### 7.2 Ce que le CI emporte tout seul

Le job `build` fonctionne sur un principe de **liste noire** : `cp -r vssp/.`
embarque tout le dossier, donc **chaque nouveau script Python atteint le
staging et la production sans toucher à `.gitlab-ci.yml`**. Il en va de
même pour `home-assistant/packages/`, `home-assistant/dashboards/` et
`home-assistant/www/`, copiés en bloc.

`vssp_ensure_packages.py` garantit
`homeassistant: packages: !include_dir_named packages` dans
`configuration.yaml`, donc un nouveau fichier de package est chargé sans
modification du CI non plus.

**La seule chose qui exigerait une modification du CI** serait un nouveau
dossier *de premier niveau*. `deploy:production` échoue bruyamment sur tout
fichier empaqueté qu'il n'a pas déployé :

```
[ERR] Files packaged but never deployed:
      Add their deployment to deploy:staging AND deploy:production.
```

Cette fonctionnalité n'ajoute aucun dossier de premier niveau : aucune
modification du CI n'est attendue.

### 7.3 Staging (automatique, sur `master`)

Commit et push. `deploy:staging` construit, copie l'archive dans le pod,
permute les dossiers et redémarre Home Assistant. Un redémarrage est
nécessaire ici : la vue ADMIN gagne un écran et de nouvelles entités
apparaissent.

```bash
NS=<namespace>; POD=<pod>; C=homeassistant

# les nouveaux scripts sont arrivés
kubectl -n $NS exec $POD -c $C -- ls -l /config/vssp/vssp_anomalies.py \
                                       /config/vssp/vssp_ai_broker.py
# le package est en place
kubectl -n $NS exec $POD -c $C -- ls -l /config/packages/vssp_ai.yaml
# la passe d'anomalies tourne (n'écrit rien)
kubectl -n $NS exec $POD -c $C -- python3 /config/vssp/vssp_anomalies.py --dry-run
```

Rappel : un redémarrage de pod recrée le conteneur depuis l'image et efface
tout ce qui avait été installé par pip dans le précédent. Cette
fonctionnalité n'ajoute aucune dépendance Python — stdlib uniquement, même
règle que `vssp_chatbot_send.py` — précisément pour que cela ne devienne
jamais un sujet.

### 7.4 Production (manuel, sur tag)

`deploy:production` est en `when: manual` et sur tag uniquement. Il prend
une sauvegarde HAOS `pre-<tag>` avant de toucher à quoi que ce soit,
permute les dossiers en SSH sur le port 22222, patche `configuration.yaml`
depuis le runner, lance `ha core check`, puis redémarre. En cas d'échec du
check, il remet les dossiers en place tout seul.

```bash
# après le déploiement, via le même accès SSH
ssh ha "ls -l /config/vssp/vssp_anomalies.py /config/packages/vssp_ai.yaml"
ssh ha "ha core check"
```

### 7.5 Étapes manuelles que le CI ne peut pas faire

Les intégrations à entrée de configuration s'ajoutent par l'interface et
sont stockées dans `.storage`, qui est gitignoré et jamais déployé. Ce sont
des opérations uniques par environnement, et ce sont les étapes les plus
susceptibles d'être oubliées :

1. **Paramètres > Appareils et services > Ajouter une intégration >
   Wyoming** — `<machine-inference>:10200` (Piper), puis à nouveau pour
   `<machine-inference>:10300` (Whisper).
2. **Le modèle de diagnostic.** Pointer le fournisseur `custom` du chatbot
   existant sur `http://<machine-inference>:11434/v1/chat/completions`. Ce
   fournisseur parle déjà le contrat OpenAI (`vssp_chatbot_send.py`), qu'Ollama
   sert — aucun nouveau code de transport n'est donc nécessaire. À régler
   depuis le popup fournisseur de l'ADMIN, pas en éditant des fichiers.
3. **Production uniquement — l'enceinte réseau.** Confirmer que l'entité
   `media_player` Cast/Sonos existe et noter son identifiant. Elle
   n'apparaîtra pas en staging ; c'est attendu, voir la section 6.
4. **Les deux — régler `vssp_voice_output_mode`** : `notification` en
   staging, `speaker` en production.

### 7.6 Vérification de bout en bout

Dans cet ordre — chaque étape est sans objet si la précédente a échoué :

1. `sensor.vssp_anomalies` existe et affiche un nombre plausible.
2. Provoquer une anomalie (débrancher un appareil de test, attendre
   au-delà du seuil) et confirmer qu'elle apparaît dans les attributs.
3. Déclencher une annonce de niveau critique : prononcée en production,
   notifiée en staging.
4. Poser une question de diagnostic à l'assistant et confirmer qu'il répond
   par un JSON valide portant un `action_id` de la liste blanche.
5. Confirmer qu'une action L1 **demande avant d'agir**, et que la refuser ne
   fait rien.
6. Confirmer qu'une action L2/L3 est refusée en staging avec le message
   « indisponible sur cet environnement » plutôt qu'un échec silencieux.

L'étape 6 est celle que l'on saute et celle qui se rappellera au bon
souvenir : c'est la seule qui prouve que le garde-fou Supervisor
fonctionne.

### 7.7 Retour arrière

Production : `rollback:production`, manuel, restaure la sauvegarde
`pre-<tag>` prise au déploiement. Staging : redéployer le commit précédent.

## 8. Fichiers

Aucun n'existe encore. Les chemins sont les destinations retenues.

| Fichier | Rôle |
|---|---|
| `home-assistant/packages/vssp_ai.yaml` | capteur d'anomalies, automations d'alerte, `script.vssp_fix_*` en liste blanche, garde-fou Supervisor |
| `vssp/vssp_anomalies.py` | la passe de détection d'anomalies |
| `vssp/vssp_ai_broker.py` | construction du contexte, appel Ollama, validation du JSON contre la liste blanche |
| `home-assistant/www/vssp/wizard/vssp_ai.html` | l'iframe de l'assistant |
| `home-assistant/dashboards/templates_j2/admin.yaml.j2` | un tuple ajouté à `screens` |
| `home-assistant/dashboards/locales/{fr,en}.yaml` | clés de menu, phrases d'alerte figées |

## Voir aussi

- [Chatbot_Integration.fr.md](Chatbot_Integration.fr.md) — le pont fournisseur réutilisé ici
- [Security.fr.md](Security.fr.md) — conventions de gestion des secrets
- [CI_CD.fr.md](CI_CD.fr.md) — les deux jobs de déploiement cités tout au long de la section 7
- [Troubleshooting.fr.md](Troubleshooting.fr.md)
