# LIVING ROOM — gabarit de référence (DRAFT v5)

> **Brouillon de travail**, corrigé au fil des échanges. Il sera figé et
> traduit en paire EN/FR comme les autres documents de `docs/dashboards/`.
> Rien de ce qui suit n'est encore écrit dans le générateur.
>
> **v5** — cible arrêtée : **staging k3s (192.168.1.11)**. Inventaire refait
> sur la bonne instance (§3). Question d'activation ouverte en §10.
> **v4** — capteurs arrêtés (les trois, point de rosée compris).
> **v3** — 1 TV confirmée, Marantz confirmé `denonavr`, capteurs de
> température retenus. Et un problème nouveau, §3bis : **les appareils du
> salon et ses capteurs ne sont pas sur la même instance Home Assistant.**

---

## 1. Le problème que ce gabarit pose

Les cinq tableaux canoniques du générateur sont :

```
sensors · switches · appliances · security · infrastructure
```

Ils savent exprimer « une liste d'appareils qu'on allume et qu'on éteint ».
Un salon n'est pas cela. TV, ampli et console sont **tous des
`media_player`**, et le rendu générique — une liste défilante de lignes à
bascule — ne dit rien d'utile sur aucun des trois.

Il existe un précédent exact dans le projet : le tableau `security` a un
rendu **sur mesure** quand la pièce porte le jeu `entrance`. Le même
mécanisme répond ici.

**Deux décisions structurantes**, le reste n'est que mise en page :

1. un **sixième tableau canonique**, `media`, plus un tableau `audio` ;
2. la notion de **rôle**, et de **capacité** (§4).

---

## 2. Rangement, par tableau

| Élément | Tableau | Rôle |
|---|---|---|
| TV OLED LG | `media` | `tv` |
| Ampli Marantz NR1711 | `media` | `amplifier` |
| PS4 Pro | `media` | `console` |
| Streaming audio | `audio` | `streamer` |
| Température | `sensors` | — |
| Lumières | `switches` | — |
| Volets roulants (×2) | `switches` | — |

```yaml
slot_sets:
  living_room: [media, audio, sensors, switches]
```

`appliances`, `security` et `infrastructure` sont **hors du jeu** : hors du
jeu veut dire « jamais », pas « pas encore ».

**Nom retenu : `living_room`.** Vous confirmez que séjour, salle TV et salon
sont la même chose ; un seul jeu les couvre, et `room_icons.living_room`
(`mdi:sofa`) existe déjà.

---

## 3. Cible et inventaire réel

**Cible arrêtée : le premier staging, k3s, 192.168.1.11.** Le second staging
(HAOS, 192.168.1.200) sera déployé ensuite — le gabarit étant le même, il n'y
a rien à refaire pour lui le moment venu.

Inventaire mesuré sur cette instance :

| Rôle | Entité retenue | État |
|---|---|---|
| `tv` | `media_player.salon_2_salon_2` + `remote.salon_2_salon_2` | **vivante** (`off`, donc joignable). Attention : ici c'est le couple *(2)* qui vit — `media_player.salon`, `salon_2` et `tv_salon` sont tous `unavailable` |
| `amplifier` | `media_player.marantz_nr1711` | **vivante** (`idle`) |
| `streamer` | `media_player.marantz_nr1711_2` | `off` — à confirmer que c'est bien le HEOS |
| `sensors` | `gw3000a_temperature_3` · `humidity_3` · `dewpoint_3` | **vivants** : 22,1 °C · 62 % · 14,5 °C |
| `console` | aucune | **absent** |
| lumières salon | aucune | le Hue couvre bureau et jardin |
| volets ×2 | aucune `cover.` | **absent** |

### Ménage préalable

Cette instance porte un historique : **cinq** entités Marantz (`_1` à `_5`,
dont trois mortes), trois « Salon » morts, et d'anciens appareils — RX-V475,
XBOXONE, YAS_109, Samsung 7 Series, Décodeur TV UHD, CineHome-Denon ×3.

Ce n'est pas bloquant : le gabarit pointe des entités nommées, pas « tous les
media_player ». Mais le formulaire d'assignation, lui, proposera les vingt —
d'où l'intérêt de supprimer les entités mortes avant d'assigner.

## 4. Rôles et capacités

Un tableau reçoit aujourd'hui **une liste d'entités**, et le gabarit les
distingue par domaine (`light.`, `cover.`…). Impossible ici : TV, ampli et
console partagent `media_player`.

Le tableau `media` reçoit donc un **dictionnaire de rôles** :

```yaml
slots:
  media:
    tv:
      entity: media_player.salon_salon
      remote: remote.salon_salon        # optionnel, pour les touches
      label: "LG OLED"
      apps: [Netflix, Prime Video, Apple TV, Disney+]
      inputs: [HDMI1, HDMI2, HDMI3]
    amplifier:
      entity: media_player.marantz_nr1711
      label: "Marantz NR1711"
    console:
      label: "PS4 Pro"                  # aucune entité : rôle déclaré, non connecté
  audio:
    streamer:
      entity: media_player.marantz_nr1711_2
      outputs: [amplifier]              # une seule sortie aujourd'hui
  sensors:
    - sensor.gw3000a_temperature_3      # 22,1 °C
    - sensor.gw3000a_humidity_3         # 62 %
    - sensor.gw3000a_dewpoint_3         # 14,5 °C
```

Le tableau `sensors` reste une **liste**, pas des rôles : trois capteurs de
même nature se listent très bien, et le rendu générique existant leur
convient. Les rôles ne servent que là où la nature diffère (`media`).

Le rôle fixe **la place et les commandes** ; l'entité fixe seulement **d'où
viennent les données**.

### Deux niveaux d'absence, et c'est le cœur du gabarit

- **Rôle sans entité** (la PS4 aujourd'hui) → la carte garde sa place, sa
  taille et ses commandes, en grisé, mention « non connecté ».
- **Entité présente mais commande non supportée** (le format sonore du
  Marantz, §5) → la carte s'affiche, la commande manquante est grisée avec
  « non disponible ».

Le gabarit lit les `supported_features` et les listes (`source_list`,
`sound_mode_list`) **de l'entité réelle** et rend ce qui existe.

**Conséquence voulue : brancher la PS4 demain, ou obtenir enfin les modes
sonores du Marantz, ne change pas la mise en page.** Elle est arrêtée
aujourd'hui ; seules les données arrivent.

---

## 5. Le Marantz NR1711 — faut-il écrire une intégration ?

Votre question, et ma recommandation : **pas tout de suite, et probablement
pas une intégration complète.**

### Ce qui est établi

- Le NR1711 est couvert par l'intégration officielle **`denonavr`** (Denon et
  Marantz partagent le même protocole). Elle expose normalement `source_list`
  **et** `sound_mode_list` — exactement ce qui vous manque.
- Elle exige l'accès aux ports **23, 8080 et 60006 (TCP)** sur l'ampli. Un
  VLAN ou un pare-feu qui en bloque un donne précisément une entité pauvre.
- Le NR1711 a des tickets ouverts spécifiques (entité qui passe
  `unavailable`).
- Des intégrations communautaires vont déjà plus loin (Audyssey, volume par
  canal, modes sonores réels).

### Dans quel ordre regarder

1. ~~D'où vient l'entité ?~~ **Répondu : `denonavr`.** L'hypothèse la plus
   simple — une mauvaise intégration — est donc écartée.
2. **Reste les ports.** `denonavr` a besoin de **23, 8080 et 60006 (TCP)**
   vers l'ampli. S'il en manque un, l'entité se réduit exactement à ce que
   vous décrivez : marche/arrêt et volume, sans `source_list` ni
   `sound_mode_list`. C'est maintenant l'hypothèse n°1.
3. Vérification en une ligne, depuis un terminal du réseau :
   `for p in 23 8080 60006; do nc -z -w2 <ip-ampli> $p && echo "$p ouvert" || echo "$p FERMÉ"; done`
4. Vérifier aussi que l'ampli n'est pas en **veille réseau réduite** : au
   repos, certains NR1711 ne répondent plus que sur une partie du protocole.
5. Seulement si tout est ouvert et que les listes manquent encore, construire.

### Et si on doit construire

Je déconseille une **intégration Home Assistant complète** : c'est une
surface importante à posséder et à maintenir à chaque version de HA, pour un
seul appareil.

La forme juste dans ce projet est celle qu'il emploie déjà partout —
`vssp_icloud.py`, `vssp_energy_sync.py` : un **pont** `vssp_marantz.py` qui
parle à l'API HTTP de l'ampli (`/goform/…`) et publie ce qui manque sous
forme de `input_select` + `shell_command`. Une centaine de lignes, le même
patron que le reste, et le gabarit sait déjà afficher des `input_select`.

**Point important pour la conception : le gabarit ne dépend d'aucune des
trois issues.** Grâce aux capacités (§4), il rend les modes sonores s'ils
existent — d'où qu'ils viennent — et les grise sinon.

---

## 6. Mise en page

```
┌──────────────────────────────────────┬──────────────────────────┐
│ MEDIA                                │ SENSORS                  │
│ ┌──────────────────┐ ┌─────────────┐ │  Température      22.1°C │
│ │ LG OLED      ⏻   │ │ MARANTZ  ⏻  │ │  Humidité           62 % │
│ │ ┌────┐┌────┐┌───┐│ │ Source: TV  │ │  Point de rosée   14.5°C │
│ │ │NFLX││PRIME││AT││ │ DD+ ATMOS   │ ├──────────────────────────┤
│ │ └────┘└────┘└───┘│ │ non dispo.  │ │ SWITCHES         ⏱ SCHED │
│ │ ┌────┐           │ │ VOL ▬▬▬▬▬   │ │  Lumières                │
│ │ │DSN+│           │ └─────────────┘ │   non connecté           │
│ │ └────┘           │ ┌─────────────┐ │  Volets                  │
│ │ HDMI1 HDMI2 HDMI3│ │ PS4 PRO     │ │   non connecté           │
│ │ VOL ▬▬▬▬▬        │ │ non connecté│ │                          │
│ └──────────────────┘ └─────────────┘ │                          │
├──────────────────────────────────────┤                          │
│ AUDIO                                │                          │
│  ♪ Titre — Artiste                   │                          │
│  ◀◀  ▶  ▶▶          ▬▬▬▬▬▬▬▬▬▬      │                          │
│  Sortie : ▸ Marantz                  │                          │
└──────────────────────────────────────┴──────────────────────────┘
```

### TV — applications et entrées, pas des chaînes

Votre réponse change cette carte. Pas de ▲▼ : la LG expose les
**applications** (Netflix, Prime Video, Apple TV, Disney+) et les **entrées
HDMI**, toutes via `source_list` de l'intégration webOS. Donc :

- une **grille de lanceurs** pour les applications, en accès direct ;
- une **rangée d'entrées** HDMI1/2/3 ;
- marche/arrêt et volume.

C'est mieux qu'un défilement : quatre applications et trois entrées tiennent
en accès direct, sans menu.

*Question ouverte :* voulez-vous l'ordre des applications figé par vous, ou
repris tel quel de `source_list` ?

### Amplificateur

Source, volume, et format sonore — ce dernier grisé « non disponible » tant
que §5 n'a pas tranché.

### Console

État lisible : éteinte, **jeu** (titre), ou **disque** (Blu-ray/DVD) — la PS4
publie l'application en cours, ce qui suffit à distinguer les deux. Grisée
aujourd'hui.

### AUDIO

Pochette, titre, artiste, transport, progression, volume, et le choix de
sortie — **une seule pastille aujourd'hui, le Marantz**. Le sélecteur reste
affiché : il montre où ça sort, et accueillera les suivantes sans
redécoupage.

### SENSORS

Trois lignes, rendu générique existant, sans une ligne de code nouvelle :

| Ligne | Entité |
|---|---|
| Température | `sensor.gw3000a_temperature_3` |
| Humidité | `sensor.gw3000a_humidity_3` |
| Point de rosée | `sensor.gw3000a_dewpoint_3` |

**Les trois sont affichées**, point de rosée compris — décidé, plus de
question ouverte là-dessus. Il dit à partir de quelle température l'air
déposerait de la condensation, ce qui se lit bien juste sous l'humidité.

Le tableau n'a pas de limite de trois : le rendu générique est une liste
défilante, donc d'autres capteurs du salon s'y ajouteront plus tard sans
rien changer à la mise en page.

### SWITCHES

Tableau existant, rendu tel quel. `switches` groupe déjà lumières et
volets séparément et porte l'horloge SCHEDULE. Les **2 volets** y entreront
comme `cover.*` ; si leur intégration expose la position, la barre de
pourcentage apparaît d'elle-même, sinon ouvrir/fermer/stop.

---

## 7. Ce qu'il faut écrire

| Fichier | Nature |
|---|---|
| `generate_dashboards.py` | `media`/`audio` dans `SLOTS`, jeu `living_room`, normalisation par rôle + lecture des capacités |
| `model/house.yaml` | `slot_sets.living_room` |
| `templates_j2/room.yaml.j2` | branches `media` et `audio` |
| `templates_j2/_media_tile.j2` | nouveau partial — une carte de rôle |
| `locales/en.yaml` + `fr.yaml` | `slot.media`, `slot.audio`, libellés des rôles, « non connecté », « non disponible » |
| `vssp_assign_prepare.py` | un `media_player` propose le tableau `media` |
| `www/vssp/wizard/assign.html` | choisir le **rôle** quand on assigne à `media` |

Le dernier point est le seul vrai travail d'interface : aujourd'hui
l'assignation range une entité dans un tableau ; pour `media` il faut dire
**laquelle est la TV**.

---

## 8. Ce qu'il reste à trancher

1. **Sur quelle instance vit le salon ?** C'est la question bloquante (§3bis).
   Les appareils AV sont propres sur la **maison** ; les capteurs de
   température n'existent que sur **staging**. Trois issues :
   - *le salon vise la maison* → il faut y ajouter la passerelle Ecowitt
     GW3000A ; le gabarit affichera « non connecté » en attendant ;
   - *le salon vise staging* → les capteurs sont là, mais il faut d'abord
     faire le ménage dans les cinq entités Marantz et les anciens appareils ;
   - *les deux* → le gabarit est le même, chaque instance remplit ce qu'elle a.
2. **Nettoyer le doublon « Salon (2) »** sur la maison — une seule TV.
3. **Les trois ports du Marantz** — le test d'une ligne du §5.
4. **Ordre des applications** TV — le vôtre, ou celui de `source_list` ?
5. **Le streaming audio** — est-ce bien le HEOS du NR1711 (`…_nr1711_2`) ?
6. **Volets** — quelle intégration est prévue ? Elle décide seule de la
   présence des positions intermédiaires.

## 9. « Comme ENERGY, qu'on active ou pas » — la question à trancher

Votre dernière phrase propose quelque chose de précis, et il y a deux
lectures qui mènent à deux travaux différents. Je préfère les poser que
choisir à votre place.

### Lecture A — un dashboard système, activable depuis la console

LIVING ROOM deviendrait un dashboard **comme ENERGY, CORE et GALERIE** : une
ligne dans l'écran DASHBOARDS avec CRÉER / RÉGÉNÉRER / DÉSACTIVER, une URL à
lui, une entrée de bandeau conditionnelle.

- **Pour :** testable tout de suite, sans déclarer de pièce ni assigner un
  seul appareil. Un bouton, et l'écran existe.
- **Contre :** il sort du système des pièces. Et il cesse alors d'être « la
  référence pour la génération automatique pour ce type de pièce » — ce qui
  était votre objectif de départ. Un second salon, ou le salon du HAOS,
  n'en hériterait pas : il faudrait un second dashboard système.

### Lecture B — un préréglage de pièce, proposé à la déclaration

`living_room` reste un **jeu de tableaux**, mais livré **prédéfini** : au
moment de déclarer une pièce dans ROOMS & FLOORS, on choisit le gabarit
« Salon (audio/vidéo) », et la pièce arrive avec ses quatre tableaux, ses
quatre rôles et sa mise en page — sans rien assigner à la main.

- **Pour :** c'est exactement « qu'on active ou pas », mais à la bonne
  granularité. Chaque salon déclaré en hérite, sur n'importe quelle
  instance, y compris le HAOS plus tard. L'objectif de référence est tenu.
- **Contre :** il faut déclarer une pièce avant de voir quoi que ce soit.
  Une étape de plus pour le premier essai.

### Ce que je recommande

**La lecture B**, parce qu'elle seule tient l'objectif que vous avez énoncé
en ouvrant le sujet : servir de référence à la génération automatique de
*toute* pièce de ce type. La lecture A donnerait un bel écran unique qui ne
se reproduit pas.

Et le « contre » de B se répare facilement : le préréglage peut pré-remplir
les quatre rôles avec les entités trouvées (`salon_2_salon_2`,
`marantz_nr1711`, les trois GW3000A), de sorte que déclarer la pièce suffise
à voir l'écran rempli. On garde l'immédiateté de A sans perdre la
réutilisation.

**Si vous préférez A**, c'est faisable et je sais déjà le faire — GALERIE
vient d'être construite exactement comme ça cette nuit. Dites-le et je pars
là-dessus.

---

## 10. Hors périmètre de ce draft

- Variante **mobile** (`room_mobile.yaml.j2`) : ordre des tableaux à décider.
- **Multiroom** entre pièces.
- **Télécommande complète** (pavé directionnel, menu, retour) : c'est un
  second écran, pas une carte de salon. En popup si vous le souhaitez —
  `remote.salon_salon` est déjà là pour ça.
