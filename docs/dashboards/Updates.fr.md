# Visio Sapiens — Mises à jour (ADMIN, écran MISES À JOUR)

**Français** · [English](Updates.md)

## Principe

Home Assistant connaît déjà chaque mise à jour en attente. Chacune est
une entité `update.*` qui porte `installed_version`, `latest_version`,
ses notes de version et un service d'installation. Réglages → Mises à
jour les liste — mais là seulement, et mélangées à tout le reste de ce
que fait cet écran.

Pour ses trois premières familles, l'écran MISES À JOUR n'ajoute **aucune
source de données** : il lit les entités qui existent déjà et apporte la
seule chose qu'un dashboard ne peut pas deviner seul, la **répartition
par famille**. La quatrième est différente — l'infrastructure n'a pas
d'entités, elle a donc sa propre sonde. Cette moitié est décrite dans
[La quatrième famille](#la-quatrième-famille--infrastructure).

| Famille | Ce que c'est | Comment ça s'installe |
|---|---|---|
| **Système** | Home Assistant lui-même, le Supervisor, l'OS, les add-ons | une ligne à la fois |
| **Intégrations & cartes** | tout ce qui est installé via HACS | une ligne à la fois, **ou tout d'un coup** |
| **Micrologiciels** | `device_class: firmware` — un appareil physique | une ligne à la fois, jamais en masse |
| **Infrastructure** | l'hôte, k3s, GitLab, le runner, Vault | par palier — voir [la quatrième famille](#la-quatrième-famille--infrastructure) |

Cette répartition est tout l'intérêt de l'écran. Réglages → Mises à jour
affiche le téléchargement d'une carte Lovelace et le flash d'une prise
murale comme la même sorte de ligne ; ce n'est pas la même sorte de
risque, et c'est la seule distinction qui décide si l'on clique sans
réfléchir ou si l'on lit d'abord les notes de version.

## Où vit chaque morceau

```
entités update.* (Home Assistant, déjà là)
        │
        ▼
packages/vssp_updates.yaml       5 capteurs — un décompte et une liste
        │                        d'entités par famille, un total, et un
        │                        pour ce qui peut s'installer seul
        ▼
templates_j2/admin.yaml.j2       l'écran MISES À JOUR affiche ces listes
```

La classification se fait **dans le package, pas dans le dashboard**.
Deviner que `update.browser_mod_update` appartient à HACS demande
`integration_entities()`, une fonction de template qui n'existe que du
côté Python — une carte Lovelace n'a pas d'équivalent. Les capteurs
publient donc chaque famille en attribut `entity_ids`, et les cartes
affichent la liste qu'on leur tend.

La famille système est définie par **soustraction** : tout ce qui n'est
ni HACS ni micrologiciel. C'est pourquoi le même fichier est juste sur
cette instance k3s (où il attrape le NAS) et sur une instance HAOS de
production (où il attrapera Core et les add-ons), sans retouche.

### Entités créées

| Entité | État | Attribut |
|---|---|---|
| `sensor.vssp_updates_pending` | total en attente | `entity_ids` |
| `sensor.vssp_updates_system` | en attente, système | `entity_ids` |
| `sensor.vssp_updates_hacs` | en attente, HACS | `entity_ids` |
| `sensor.vssp_updates_firmware` | en attente, micrologiciel | `entity_ids` |
| `sensor.vssp_updates_auto` | en attente, installable seule | `entity_ids`, `protected` |
| `script.vssp_updates_check` | — | ré-interroge chaque entité update |
| `script.vssp_updates_install_hacs` | — | installe toutes les mises à jour HACS |
| `script.vssp_updates_install_auto` | — | la passe automatique, à la demande |
| `input_boolean.vssp_updates_auto` | l'option | éteinte tant qu'on ne l'allume pas |
| `input_datetime.vssp_updates_auto_time` | l'heure de passage | |
| `automation.vssp_updates_auto_nightly` | le déclencheur nocturne | |

Une mise à jour **ignorée** ne compte pas, et cela ne demande aucun
filtre : Home Assistant rapporte une telle entité à `off` tant que la
version ignorée reste la dernière. Ignorer depuis une ligne vide donc cet
écran exactement comme le fait l'installation.

## L'écran

**ÉTAT DES MISES À JOUR** — les décomptes, d'un coup d'œil, une ligne par
famille.

**À INSTALLER** — l'inventaire : chaque mise à jour en attente, groupée
par famille, avec les deux versions entre lesquelles elle se trouve
(`v3.2.2 → v3.2.3`). C'est ce qu'on lit avant de décider. Une famille
sans rien en attente affiche un tiret cadratin.

**Une carte par famille** — les lignes actionnables, et chaque carte est
absente quand sa famille est vide : une instance parfaitement à jour
n'affiche plus qu'un état et les commandes de maintenance.

Toucher une ligne ouvre **la boîte de dialogue de Home Assistant
lui-même** : notes de version, case de sauvegarde là où l'entité en
supporte une, Installer et Ignorer. Cette boîte vaut mieux que tout ce
que cette console pourrait reconstruire, donc la console ne la
reconstruit pas.

**MAINTENANCE** — deux boutons :

- **VÉRIFIER MAINTENANT** — les intégrations interrogent leur source à
  leur propre rythme (HACS environ toutes les heures), donc un écran vide
  signifie *rien trouvé la dernière fois qu'on a demandé*. Ce bouton
  transforme cela en *rien trouvé à l'instant*.
- **INSTALLER TOUTES LES INTÉGRATIONS & CARTES** — la seule installation
  groupée proposée.

### Pourquoi l'installation groupée s'arrête à HACS

Pas une limitation — une décision.

Une mise à jour HACS télécharge des fichiers et se défait en
réinstallant la version précédente depuis HACS. Une mise à jour de Core
ou d'un add-on, non, et elle veut la case de sauvegarde que sa propre
boîte propose — case qu'un appel groupé ne peut pas cocher,
`update.install` refusant `backup: true` sur toute entité qui n'annonce
pas le support BACKUP et faisant échouer l'appel entier pour une liste
mixte. Un flash de micrologiciel, lui, ne se défait par rien du tout.

Donc : HACS en masse, tout le reste depuis sa propre ligne.

Après une installation groupée HACS, une notification demande un
rechargement forcé (Ctrl+Maj+R). Une carte Lovelace remplacée sur le
disque reste l'ancien fichier dans le cache du navigateur, Home Assistant
ne le dit pas, et le symptôme — une carte qui continue de se comporter
comme la version qu'on vient de remplacer — se lit comme une mise à jour
ratée plutôt que comme un onglet périmé.

## Mises à jour automatiques — une option, et elle est éteinte

Rien ne s'installe tout seul tant que `input_boolean.vssp_updates_auto`
n'est pas activé depuis la carte MISES À JOUR AUTOMATIQUES. Interrupteur
fermé, l'automatisation reste chargée et ne fait rien : l'interrupteur
est une **condition**, pas un second déclencheur, donc le rallumer plus
tard ne rejoue pas les nuits qu'il a passées à l'arrêt.

Une fois allumé, chaque nuit à l'heure réglée juste à côté, la passe :

1. demande à chaque entité update de ré-interroger sa source, et attend
   les réponses ;
2. lit `sensor.vssp_updates_auto` — la liste de ce qui peut s'installer
   sans surveillance ;
3. les installe **une à la fois**, `continue_on_error`, à vingt secondes
   d'intervalle ;
4. publie une notification qui nomme ce qui a été installé **et ce qui a
   été retenu**.

Le décompte affiché sur la carte est lu depuis ce même capteur : le
nombre sur la ligne est donc le nombre de choses qui seront installées
cette nuit — pas un second calcul qui s'accorde avec le premier jusqu'au
jour où l'un des deux est modifié.

**LANCER LA PASSE MAINTENANT** appelle le même script que
l'automatisation. Tester le bouton teste la vraie passe nocturne, pas une
seconde copie qui divergera.

### Home Assistant Core n'est jamais installé automatiquement

C'est la seule mise à jour capable de laisser la maison sans dashboard :
un Core cassé emporte l'interface qui servirait à s'en apercevoir, la
console qui servirait à revenir en arrière, et toutes les automatisations
du fichier. Il veut la case de sauvegarde que sa propre boîte propose, et
quelqu'un devant l'écran.

L'exclusion vit dans **le capteur qui alimente l'automatisation**, pas
dans l'automatisation — l'écran l'énonce donc comme un fait qu'il relit
et non comme une promesse faite dans un commentaire, et l'entité retenue
est nommée dans la notification au lieu d'être silencieusement absente.

Core est reconnu de deux façons, parce que les deux ne coïncident pas
toujours : par `entity_id` (`update.home_assistant_core_update`,
l'identifiant que lui donne le Supervisor) et par l'attribut `title`
(`Home Assistant Core`), qui survit à une entité qu'on a renommée.

Aucun des deux n'existe sur l'instance k3s — Home Assistant y tourne en
conteneur, sans Supervisor pour le mettre à jour — donc `protected` y est
vide et la garde reste dormante jusqu'au passage du modèle sur HAOS,
c'est-à-dire précisément le moment où elle doit déjà être là.

**Ce qui n'est pas protégé :** le Supervisor, l'OS et les add-ons partent
avec le reste, comme demandé. C'est laisser l'interrupteur fermé qui les
retient.

### Pourquoi une à la fois

Un seul `update.install` sur toute la liste est un unique appel de
service. La première entité qui refuse — un appareil parti hors ligne
entre le rafraîchissement et l'installation — lève, et tout ce qui attend
derrière n'est jamais tenté, sans un mot. Boucler avec
`continue_on_error` coûte quelques minutes à quatre heures du matin et
achète une passe qui termine ce qu'elle peut.

Le délai entre chacune évite de surcroît que deux flashs de micrologiciel
se chevauchent, ce qui sur des appareils secteur signifie deux prises qui
redémarrent en même temps.

## Notes d'implémentation

**Ni iframe ni token.** Contrairement à PIÈCES & ÉTAGES, APPAREILS
DÉTECTÉS ou le COFFRE, cet écran est entièrement fait de cartes natives.
Une mise à jour est une entité `update.*`, les cartes natives atteignent
donc tout, et c'est la boîte de dialogue native qui agit.

**`custom:config-template-card` construit les lignes.** Une carte
`entities` ne sait pas filtrer : sa liste est figée dans du YAML écrit
des mois avant que la mise à jour n'existe. config-template-card évalue
une valeur qui commence par `${` et affecte ce qui revient — tableau
compris — donc la liste est lue depuis le capteur au moment du rendu.
Elle se re-rend quand une entité de son propre `entities:` change, d'où
le capteur de famille listé là, dont le décompte bouge dès qu'une
installation se termine.

Dans cette expression, la carte des états s'appelle **`states`** ; il n'y
a pas de `hass`. La garde `&& … || []` n'est pas de la superstition : le
capteur n'existe pas pendant les quelques secondes qui séparent un
redémarrage de la première passe de templates, et une carte entities à
qui l'on tend `undefined` lève au lieu de s'afficher vide.

**Les conditions énumèrent `unavailable` et `unknown` une par une.**
`state_not: "0"` seul est vrai pour les deux, donc sur une instance à
moitié démarrée la carte apparaîtrait, demanderait sa liste au capteur,
et n'obtiendrait rien.

**Le champ d'heure demande un token CSS, sur la carte.** Le sélecteur est
un contrôle Web Awesome quatre shadow roots plus bas (`ha-time-input` >
`ha-base-time-input` > `ha-input` > `wa-input`), et ce qui le peint est
`.text-field` dans le shadow root de `wa-input` lui-même — hors
d'atteinte de tout sélecteur écrit dans le template. Laissé tel quel, il
se rend en `#f3f3f3`, une dalle blanche sur une console sombre.
`--ha-color-form-background` posé sur le `ha-card` est la seule chose qui
le change.

Il doit aller sur la **carte**, pas sur le
`--wa-form-control-background-color` en aval : une propriété
personnalisée est substituée là où elle est *déclarée*, et Home Assistant
déclare cette chaîne à partir de ce token au-dessus de la carte — donc
quand elle atteint le champ, le nom en aval est déjà une valeur résolue.

Et pour le vérifier dans un navigateur, le champ porte une transition de
fond : lire le style calculé juste après avoir posé la propriété renvoie
l'**ancienne** couleur, et une correction qui marche ressemble à une
correction ratée.

**Deux moteurs de template sur la carte markdown.** Les trois libellés de
famille sont traduits par le *générateur* ; la boucle en dessous est
exécutée par *Home Assistant*. La frontière tombe entre les deux, la
balise `set` est donc émise en tant que texte — `{{ '{%' }}` est une
expression que le générateur évalue en deux caractères que Home Assistant
lira plus tard comme le début d'une balise. Une expression est de surcroît
insensible à `lstrip_blocks`, qui retire l'indentation devant une balise
de *bloc* — le piège dans lequel un bloc raw posé sur cette ligne serait
tombé tout droit, ramenant le template en colonne zéro et cassant le
YAML. Voir [Troubleshooting.fr.md](../ci-cd/Troubleshooting.fr.md) pour
la version de cette erreur qui est déjà partie en production une fois.

## La quatrième famille — INFRASTRUCTURE

Tout ce qui précède cette section lit des entités que Home Assistant
détient déjà. Celle-ci ne le peut pas, et c'est toute sa raison d'être.

Home Assistant sait qu'une mise à jour de Core l'attend. Il ignore que
l'hôte Ubuntu sur lequel il tourne a cinq paquets en attente et réclame
un redémarrage, que k3s a deux correctifs de retard, ou que le GitLab qui
le déploie a publié un correctif. Ces faits vivent de l'autre côté de la
frontière du conteneur et aucune entité `update.*` ne les porte — donc
l'écran qui prétendait réunir *toutes* les mises à jour en attente était,
jusqu'ici, aveugle à la machine sous lui.

### Trois couches, pas une liste plate

La première question devant une mise à jour d'infrastructure n'est pas
« quelle version » mais **« qu'est-ce que son redémarrage emporte avec
lui »**. Recréer le coffre-fort coûte un rescellement ; redémarrer k3s
emporte Home Assistant, donc l'écran depuis lequel on a appuyé. Ce sont
deux rayons d'explosion différents et ils tenaient dans la même liste de
sept lignes, qui ne nommait jamais la différence.

Chaque composant déclare donc sa **couche**, et l'écran regroupe dessus :

| Couche | Ce que c'est | Ce qu'un redémarrage emporte |
|---|---|---|
| `host` | l'installation Ubuntu elle-même — paquets apt, unités systemd | tout, pour le redémarrage de l'hôte ; rien, pour un paquet |
| `docker` | un conteneur du démon Docker de l'hôte, **à côté** du cluster | ce conteneur seul |
| `k3s` | ce qui tourne **dans** le cluster | le pod, et Home Assistant s'il en fait partie |

| Composant | Couche | Palier | D'où vient la version |
|---|---|---|---|
| Paquets de l'hôte | `host` | `auto` | `apt list --upgradable` sur l'hôte |
| Redémarrage de l'hôte | `host` | `manual` | `/var/run/reboot-required` |
| GitLab | `host` | `manual` | `apt-cache madison gitlab-ce`, ou l'API de l'instance |
| Runner GitLab | `host` | `auto` | `apt-cache madison gitlab-runner` |
| Cluster k3s | `host` | `manual` | `k3s --version` face aux releases k3s-io/k3s |
| Coffre-fort Vault | `docker` | `manual` | `vault version` **dans** le conteneur, face à Docker Hub |
| Autres conteneurs Docker | `docker` | `locked` | `docker ps`, remonté et non comparé |
| Charges du cluster | `k3s` | `locked` | `k3s kubectl get deploy,sts,ds -A`, remonté et non comparé |

Deux lignes sont nouvelles ou déplacées, et pour des raisons précises :

- **Charges du cluster.** Le cluster n'apparaissait que comme un numéro de
  version, et rien de son contenu n'apparaissait du tout — Home Assistant,
  qui sert cet écran, n'était pas sur l'écran. Cette ligne liste chaque
  deployment, statefulset et daemonset avec l'image qu'il tire, au niveau
  où cette image est déclarée : les pods vont et viennent, ce sont leurs
  contrôleurs qu'une mise à niveau modifie.
- **Le coffre-fort lit `vault version`, plus son tag d'image.** Le
  déploiement épingle `hashicorp/vault:1.20`, un alias flottant vers le
  correctif le plus récent de la série : le tag dit `1.20` quand le binaire
  est en `1.20.4`. Un plan construit sur le tag proposait donc `1.20.4` en
  première étape — une mise à niveau vers la version déjà en marche.

### Une étape par pression — le chemin, pas l'horizon

**Le problème.** Une ligne publiait un couple : installé, et la version la
plus haute en amont. Sur un paquet apt ce couple est aussi la consigne —
apt passe de l'un à l'autre en une étape. Sur le coffre-fort c'était un
mensonge. HashiCorp ne supporte qu'une série mineure à la fois, donc un
hôte en `1.20.4` atteint `2.1.0` ainsi :

```
1.20.4  ──▶  1.21.4  ──▶  2.0.4  ──▶  2.1.0
```

Trois mises à niveau, chacune avec sa migration de stockage et de
scellement. La ligne affichait `1.20.4 → 2.1.0` à côté d'un bouton
INSTALLER : elle proposait d'en sauter deux. Kubernetes interdit de la même
façon de sauter une mineure, et les migrations de base de GitLab tournent
par mineure.

**La correction.** La contrainte est propre à chaque composant, elle est
donc déclarée à côté de son palier, dans `vssp_infra_updates.py` :

| Politique | Ce qu'elle autorise | Qui la porte |
|---|---|---|
| `POLICY_DIRECT` | n'importe quelle version vers n'importe quelle autre, en un mouvement | paquets de l'hôte, runner GitLab |
| `POLICY_SERIES` | une série `majeure.mineure` à la fois, en atterrissant sur son plus haut correctif | Vault, k3s, GitLab |

La sonde publie alors tout le chemin au lieu de son extrémité :

| Champ | Ce que c'est |
|---|---|
| `next` | la **seule** version qu'installe une pression |
| `path` | chaque escale, de `next` jusqu'au sommet |
| `steps` | combien de mises à niveau cela représente |
| `latest` | le sommet. Reste sur la ligne — savoir de combien on est en retard a de la valeur — mais **n'est plus une cible** |

Ce que l'écran affiche désormais sur la ligne du coffre-fort :

```
Coffre-fort Vault      1.20.4 → 1.21.4          [INSTALLER]
                       puis 2.0.4 → 2.1.0 · 3 étapes
```

Le feu de HOME continue de rougir sur `latest` : avoir trois séries de
retard est un fait de version majeure quelle que soit la première étape,
et le feu parle du retard de la maison. Mais sa liste affiche `next` à côté
de la flèche, parce que c'est la version qu'une pression installe. Les deux
ne faisaient qu'un champ, d'où un feu et un bouton capables de décrire deux
mises à niveau différentes.

**Rien ne peut sauter une étape, même par accident.** `install_one` sonde le
composant *avant* d'installer et tend la ligne fraîche à l'installateur, qui
installe la version que cette ligne nomme. Ni un capteur périmé, ni une
carte rendue avant la dernière sonde, ni un second opérateur ne peut
transformer une pression sur `1.21.4` en un saut vers `2.1.0`. Côté apt
cela veut dire `apt-get install gitlab-ce=18.3.2-ce.0` et non
`--only-upgrade`, qui viserait le candidat, c'est-à-dire le sommet.

### Un coffre scellé ne vide pas l'écran

Vault se rescelle à **chaque redémarrage**, par conception : aucun
descellement automatique n'est configuré, et c'est un choix, pas un oubli.
L'accès SSH à l'hôte vit dans ce coffre. Un coffre scellé rend donc sept des
huit lignes immesurables — tout ce qui est sur le serveur, plus ce qui est
sous Docker et dans k3s.

Pendant longtemps le rapport écrit dans cet état disait, pour chacune de ces
lignes, `installed: ""`, `pending: false`, `count: 0`. L'écran l'affichait
fidèlement : **les mises à jour hôte, GitLab et k3s listées une heure plus tôt
disparaissaient purement et simplement**, et les compteurs tombaient à zéro.
Ce n'était pas un cas limite — c'était chaque redémarrage.

« Je n'ai pas pu mesurer ceci » et « il n'y a rien ici » sont deux faits
différents, et le rapport publiait le second à la place du premier.

`carry_forward()` hérite désormais, pour chaque ligne non mesurée, de la
dernière mesure réelle. Trois champs distincts portent la nuance :

| Champ | Question à laquelle il répond |
|---|---|
| `probed` | **cette** exécution a-t-elle mesuré la ligne ? |
| `stale` | les valeurs viennent-elles d'une exécution **antérieure** qui l'a fait ? |
| `measured` | de **quand** date cette mesure ? |

Seuls les champs de **mesure** voyagent (`CARRIED` dans
`vssp_infra_updates.py`) : le nom, le palier, l'icône, la couche, la
politique et l'avertissement continuent de venir de `COMPONENTS`, pour
qu'éditer la table change encore chaque ligne à l'exécution suivante.

À l'écran, une ligne souvenue garde ses chiffres, perd sa couleur, et porte
sa date en seconde ligne : *« mesuré le 11/09/2026 14:00 »*. Elle n'a pas de
bouton INSTALLER — une installation réclame le même accès à l'hôte qui
manquait à la sonde. La bannière ambrée au pied de la carte dit pourquoi et
imprime la commande qui y met fin.

**`measured` n'avance pas.** Une ligne déjà reportée garde l'horodatage de
l'exécution qui a vraiment vu la machine : une semaine de redémarrages
scellés continue de pointer sur elle, au lieu de faire glisser la date d'une
sonde à l'autre jusqu'à paraître fraîche.

**L'alternative était pire.** Ne rien écrire du tout — ce que ce fichier
faisait avant — laisse le rapport précédent intact sur disque, et l'écran
affiche ce qui est sur disque : de vieilles versions montrées comme
actuelles, sans que rien nulle part ne dise qu'elles sont vieilles. La
différence entre les deux n'est pas la donnée, c'est l'étiquette dessus.

**Et pour ne plus resceller ?** Il n'y a pas de voie gratuite, et c'est le
propos du scellement : toute automatisation revient à confier la clé à autre
chose. `seal "transit"` la confie à un second Vault, qui ne sert que s'il
tourne sur une machine ne redémarrant pas avec celle-ci. `seal "awskms"` /
`gcpckms` / `azurekeyvault` la confient à un KMS distant — la seule option
qui descelle vraiment seule sans second serveur, au prix d'une dépendance à
Internet au démarrage et d'un identifiant IAM posé sur l'hôte. Poser les clés
dans un fichier annule le coffre. PKCS#11/HSM est réservé à Vault
Enterprise. Tant qu'aucune n'est choisie, ce que cette section décrit est la
réponse : le scellement coûte trois saisies, pas un écran vide.

### À jour n'est pas en marche

La première mise à niveau k3s réelle a installé le bon binaire et laissé le
cluster à terre pendant un quart d'heure sans que rien ne le dise.

Le déroulé, parce qu'il se répétera ailleurs :

1. `get.k3s.io` installe `v1.36.4+k3s1` et redémarre l'unité. Journal propre.
2. Un processus **`k3s agent` de la version précédente survit à l'arrêt** —
   systemd le signale, « Found left-over process in control group while
   starting unit » — et garde `127.0.0.1:6444`, le port du superviseur.
3. Le nouveau serveur démarre, ne peut pas s'y lier, sort.
   `Failed with result 'protocol'`. systemd relance. **55 fois.**
4. Les charges continuent de tourner sous un `containerd` orphelin : Home
   Assistant répond 200, le navigateur ne montre rien d'anormal.
5. Et la ligne k3s affiche **« 1.36.4 · à jour »**, parce que la sonde lisait
   `k3s --version`, c'est-à-dire **le binaire sur le disque**.

Trois défauts, trois corrections :

| Défaut | Correction |
|---|---|
| L'installateur créait la condition | il **arrête** l'unité, **attend** que 6444 soit libéré, et tue ce qui le tient encore après 5 s |
| Il ne vérifiait pas | il attend `active` ; sinon il libère le port et redémarre **une** fois, puis écrit son verdict dans `.state` |
| La sonde lisait la version, pas l'état | elle demande aussi `systemctl is-active k3s` ; tout ce qui n'est pas `active` remplit `health` |

Le champ `health` prime sur tout le reste à l'écran : la ligne passe en rouge
et nomme l'état systemd, parce qu'`activating` et `failed` n'envoient pas au
même endroit. `activating` compte comme mauvais **volontairement** — c'est
l'état d'une unité `Type=notify` qui démarre sans jamais se déclarer prête,
donc l'apparence exacte d'une boucle de plantage vue de l'extérieur.

**La leçon vaut au-delà de k3s.** Une version est une réponse à « est-ce à
jour », jamais à « est-ce que ça marche », et cet écran a été construit pour
montrer la première. Tout composant dont le service peut mourir en gardant le
bon numéro mérite son `health`.

Dépannage manuel, si jamais le redémarrage automatique ne suffit pas :

```bash
sudo /usr/local/bin/k3s-killall.sh   # arrête les rescapés, ne désinstalle rien
sudo systemctl restart k3s
```

### Les trois paliers

Les autres familles se répartissent déjà par risque — HACS en lot, jamais
le micrologiciel. Celle-ci applique la même idée à des choses capables de
mettre la maison à l'arrêt :

- **`auto`** — la passe nocturne peut l'installer sans surveillance.
  Réversible, ou assez peu coûteux pour qu'un échec soit une gêne plutôt
  qu'une panne.
- **`manual`** — une ligne, un bouton, jamais la passe, quoi que dise
  l'interrupteur. GitLab redémarre tous ses services et réclame une
  sauvegarde préalable ; un redémarrage d'hôte est un redémarrage d'hôte.
- **`locked`** — remonté et jamais installé depuis la console, **et chaque
  ligne verrouillée dit pourquoi avec ses propres mots**. Une seule phrase
  les couvrait tous, donc la pastille VERROUILLÉ n'expliquait rien sur la
  ligne où elle se trouvait.

**k3s et Vault étaient `locked` et tous deux à tort**, pour des raisons
différentes.

- Le coffre-fort est un simple conteneur Docker **à côté** du cluster, pas
  dedans (voir [Vault.fr.md](../platform/Vault.fr.md) pour pourquoi) : le
  recréer ne touche ni Home Assistant ni k3s. Cela coûte un rescellement —
  3 des 5 clés à ressaisir — et c'est exactement ce dont sa demande de
  confirmation avertit avant la pression.
- k3s emporte réellement Home Assistant avec lui. Mais le redémarrage de
  l'hôte aussi, et il est un bouton depuis toujours : la réponse à « ceci
  tue la session qui l'a pressé » est de **détacher** la commande, pas de
  refuser l'opération. `install_k3s` écrit un script sur l'hôte et le lance
  sous `setsid`, comme `install_os_reboot` s'en remet à `shutdown -r +1` ;
  la mise à niveau se termine seule et la sonde suivante en rapporte le
  résultat.

Ce qui était réellement dangereux sur les deux, c'était de les viser sur la
release la plus récente — et c'est ce que corrige la section précédente.

**Chaque bouton lourd a désormais son propre avertissement**, déclaré à
côté de son palier. Une phrase unique faisait poser la même question au
coffre et au redémarrage de l'hôte pour deux conséquences entièrement
différentes : l'un rescelle un conteneur, l'autre met la maison à l'arrêt.

**Le palier est déclaré dans `vssp_infra_updates.py`, pas dans le
dashboard.** Une carte ne peut pas promouvoir un composant en l'affichant
autrement, et la passe nocturne filtre sur ce champ plutôt que sur quoi
que ce soit envoyé par l'interface.

### D'où viennent les privilèges

Lire `apt list` demande un compte sur l'hôte. Installer demande sudo.
Home Assistant ne doit détenir ni l'un ni l'autre : tout ce qu'il lit
devient un état d'entité, écrit en clair dans `home-assistant_v2.db` par
le recorder et visible dans les Outils de développement par n'importe
quel administrateur. C'est le raisonnement qui a donné sa forme au coffre
(voir [Vault.fr.md](../platform/Vault.fr.md)), appliqué à la maintenance.

Les identifiants vivent donc dans le coffre, sous `vssp/infra/`, et
**c'est le processus Python qui les lit — pas Home Assistant** :

```
Écran ADMIN  ──▶ shell_command ──▶ vssp_infra_updates.py
                                       │
                                       ├── lit secret/data/vssp/infra/*
                                       │   avec le jeton vssp-maint
                                       │   (/config/vssp/.vault_maint_token)
                                       ├── ssh vers l'hôte, apt / k3s / docker
                                       └── écrit www/vssp/infra_updates.json
                                               │
                    sensor.vssp_updates_infra ◀┘   (command_line, cat)
```

Les valeurs existent dans la mémoire d'une exécution brève, vont vers
`ssh` ou vers un appel HTTPS, et ne sont jamais rendues à l'appelant. Le
`shell_command` qui a lancé l'exécution récupère un décompte et un
message de statut. Rien n'atteint une entité, donc rien n'atteint la
base — la séparation survit, et elle survit comme le reste du coffre
l'impose : par ce que Vault refuse, pas par ce qu'un script promet.

`vssp-maint` accorde `read` sur `secret/data/vssp/infra/*` et rien
d'autre. Elle ne peut pas lister le coffre, ne voit ni `accounts/` ni
`apps/`, et n'écrit pas.

### Quoi mettre dans le coffre

Depuis l'écran COFFRE-FORT, catégorie `infra` :

| Entrée | Champs |
|---|---|
| `vssp/infra/host_ssh` | `host`, `user`, `port`, `private_key` |
| `vssp/infra/host_sudo` | `password` |
| `vssp/infra/gitlab` | `url`, `token` — seulement pour un GitLab qui n'est pas un paquet apt |

Lui donner **sa propre clé SSH**, créée pour cela et rien d'autre, pour
que révoquer l'accès de maintenance soit supprimer une ligne du
`authorized_keys` de l'hôte plutôt que faire tourner une clé dont
quelqu'un se sert aussi pour se connecter.

Puis créer le jeton et le poser dans la variable CI :

```bash
vault policy write vssp-maint vault/policies/vssp-maint.hcl
vault token create -policy=vssp-maint -period=768h -field=token
# → Settings > CI/CD > Variables, masquée + protégée, VAULT_MAINT_TOKEN
```

Sans cette variable rien ne casse : le déploiement avertit, et la famille
se déclare jamais sondée.

### auto, manuel, planifié

Les trois façons dont cette famille bouge, et ce sont les trois que le
reste de l'écran offrait déjà :

| | Ce qui tourne | Piloté par |
|---|---|---|
| **planifié** | la sonde, toutes les 6 h et 2 minutes après chaque redémarrage | rien — elle ne fait que lire |
| **auto** | le palier `auto`, à l'heure posée à côté de l'interrupteur | `input_boolean.vssp_updates_infra_auto` |
| **manuel** | un composant, depuis son propre bouton | vous |

**L'interrupteur infrastructure est un second interrupteur,
délibérément.** Celui du dessus installe des cartes Lovelace : une
mauvaise nuit coûte un Ctrl+Maj+R. Celui-ci lance `apt-get` sur le
serveur qui porte le cluster où vit Home Assistant. Les réunir en une
seule commande signifierait que quelqu'un ayant activé les mises à jour
HACS automatiques il y a des mois se met à mettre à jour son serveur ce
soir, sans avoir consenti à cela.

### Deux détails faciles à rater

**La ligne des paquets de l'hôte exclut GitLab et le runner.** Les deux
sont aussi des paquets apt et ont chacun leur ligne ; laissés dans le
décompte ils apparaîtraient deux fois, et le total de la famille
exagérerait le travail en attente. Ils sont retirés de la ligne *et* de
la commande de mise à jour — `install --only-upgrade <paquets nommés>`
plutôt qu'un `apt-get upgrade` nu, qui installerait sinon `gitlab-ce`,
composant de palier manuel, au milieu d'une passe sans surveillance. Le
palier aurait été respecté partout sauf dans la seule commande qui
installe.

**La version amont est le candidat apt, pas un flux de releases.** L'hôte
est déjà abonné au dépôt de l'éditeur, le candidat est donc par
définition la version que cette machine obtiendrait réellement — et il
reste juste sur un paquet épinglé ou gelé, ce qu'une API amont ne peut
pas savoir. `apt-cache policy` est aussi **traduit** : il affiche
`Installed:` sur un hôte anglais et `Installé :` sur un hôte français, la
sonde fige donc `LC_ALL=C` avant d'analyser. Sans cela elle marche sur la
machine où elle a été écrite et remonte partout ailleurs un paquet
inconnu.

### Entités ajoutées

| Entité | État |
|---|---|
| `sensor.vssp_updates_infra` | en attente sur l'infrastructure ; attributs `components`, `counts`, `generated` |
| `sensor.vssp_updates_all` | toutes les mises à jour en attente, les deux mondes réunis |
| `sensor.vssp_infra_auto` / `_manual` / `_locked` | le décompte par palier |
| `script.vssp_infra_check` | sonder maintenant |
| `script.vssp_infra_install_one` | installer un composant, par clé |
| `script.vssp_infra_install_auto` | la passe du palier `auto` |
| `input_boolean.vssp_updates_infra_auto` | l'option, éteinte tant qu'on ne l'allume pas |
| `automation.vssp_infra_probe_scheduled` | toutes les 6 heures |
| `automation.vssp_infra_auto_nightly` | la passe, 10 minutes après celle de Home Assistant |

`sensor.vssp_updates_infra` est un capteur `command_line` qui **lit un
fichier** — il ne lance pas la sonde. La sonde ouvre une session SSH et
appelle trois API amont ; la lancer à l'intervalle de scan d'un capteur
voudrait dire une connexion à l'hôte chaque minute pour un nombre qui
change deux fois par jour. Un `cat` sur un fichier absent sort en erreur
et le capteur devient indisponible, ce qui est correct et visiblement
différent de « rien n'attend ».

## Le feu sur HOME

Le cinquième panneau KPI du dashboard HOME — desktop comme mobile — est un
feu unique intitulé **UPGRADE**, et le toucher ouvre cet écran. Il a
remplacé le panneau sécurité/alarme, lequel a pris la troisième place, là
où se trouvait PIÈCES & APPAREILS.

| | Signifie | Affiché quand |
|---|---|---|
| 🟢 **À JOUR** | rien n'est exposé à une faille connue | aucun correctif de sécurité en attente, aucune version majeure disponible |
| 🟠 **CORRECTIFS DUS** | des correctifs de sécurité attendent | l'hôte a des paquets issus d'une poche `-security` |
| 🔴 **VERSION MAJEURE** | quelque chose réclame une vraie migration | le *premier* nombre de version d'un composant a bougé |

**Trois couleurs, jamais une quatrième.** Un parc qu'on n'a pas pu
inspecter — `sensor.vssp_updates_infra` indisponible parce que la sonde
n'a jamais tourné — porte lui aussi l'**orange**, avec sa propre icône et
le libellé NON SONDÉ. Il n'est pas vert : le vert est une affirmation,
*rien ici n'est exposé*, et la porter sans avoir regardé est la seule
défaillance qu'un feu de sécurité ne peut pas se permettre, car elle est
indiscernable du vrai précisément quand cela compte. L'orange dit ce qui
est vrai — attention requise — et le libellé dit pourquoi.

**Ce n'est pas un décompte de mises à jour en attente.** L'écran les liste
déjà. Un feu qui passe à l'orange parce qu'une carte Lovelace a une
nouvelle version vous apprend à l'ignorer avant la fin de la semaine ; la
question à laquelle il répond est donc délibérément étroite : *reste-t-il
quelque chose d'exposé, et quelque chose réclame-t-il bientôt une
migration ?* Une mise à jour mineure ordinaire le laisse vert.

**Le vert n'est jamais affiché par-dessus des données absentes.** Un feu
de sécurité qui annonce « tout va bien » sans avoir regardé est pire que
pas de feu du tout — d'où le quatrième état. Les mises à jour propres à
Home Assistant sont toujours connues, donc un hôte non sondé est la seule
chose qui puisse le passer au gris.

**Majeur veut dire que le premier nombre a bougé** — `1.20 → 2.1.0` est
majeur, `1.36.2 → 1.36.4` non. Les deux mondes sont lus : les composants
d'infrastructure depuis l'attribut de la sonde, et les entités `update.*`
que détient Home Assistant, dont `installed_version` et `latest_version`
reçoivent la même comparaison. Tout ce dont l'amont est inconnu est ignoré
plutôt que deviné — une version vide ne prouve pas un retard.

Le verdict est calculé une seule fois, dans `variables`, que button-card
évalue avant les champs qui les lisent ; icône, couleur, état et libellé
s'accordent donc au lieu de le recalculer chacun et de diverger sur une
frame lente.

## Voir aussi

- [Dashboard_Generator.fr.md](Dashboard_Generator.fr.md) — le générateur,
  les slots et les langues
- [Backup_Retention.fr.md](../platform/Backup_Retention.fr.md) — ce qu'une
  sauvegarde avant mise à jour de Core retient réellement
