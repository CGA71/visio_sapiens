# LIVING ROOM — gabarit de référence (DRAFT v7)

> **Brouillon de travail**, corrigé au fil des échanges. Il sera figé et
> traduit en paire EN/FR comme les autres documents de `docs/dashboards/`.
> Rien de ce qui suit n'est encore écrit dans le générateur.
>
> **v8** — le Wake-on-LAN existe, en entite bouton separee : le bouton
> d alimentation de la TV appelle donc deux choses selon son etat.
> **v7** — la LG EST sur staging, je l'avais manquee : `media_player.`
> `lg_webos_tv_oled55b9pla`, allumee, 21 sources. Section 3 corrigee.
> **v6** — attributs réels lus par l'API (2867 entités). Trois corrections,
> dont une bonne nouvelle : **les modes sonores du Marantz existent** (§5).
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

**Cible : le premier staging, k3s, 192.168.1.11.** Les attributs ci-dessous
sont lus par l'API Home Assistant, pas supposés.

| Rôle | Entité | Ce qu'elle sait faire |
|---|---|---|
| `amplifier` | **`media_player.marantz_nr1711_2`** | `device_class: receiver` · TURN_ON/OFF · SELECT_SOURCE (13) · **SELECT_SOUND_MODE (23)** · VOLUME_STEP · VOLUME_MUTE |
| `streamer` | **`media_player.marantz_nr1711`** | HEOS intégré · `idle` · BROWSE_MEDIA · PLAY_MEDIA · SELECT_SOURCE (11) · pas de modes sonores |
| `sensors` | `gw3000a_temperature_3` · `humidity_3` · `dewpoint_3` | 22,1 °C · 62 % · 14,5 °C — vivants |
| `tv` | **aucune** | voir ci-dessous |
| `console` | aucune | — |
| lumières, volets | aucune | — |

### La TV, trouvee a la deuxieme recherche

`media_player.lg_webos_tv_oled55b9pla` — **allumee**, `device_class: tv`,
`SELECT_SOURCE` avec **21 sources** ou applications et entrees cohabitent,
exactement comme vous l'aviez decrit :

```
Netflix · Prime Video · Disney+ · Apple TV · YouTube · Twitch · Live TV
LG Content Store · Navigateur Web · Musique · Photo & Video · Pathe Home
Smarters VPN Player · LG Streaming Week · GALERIE · Amazon Alexa
Tableau de bord Maison · DVD Player · HDMI 1 · HDMI 3 · HDMI 4
```

Deux details qui changent le gabarit :

- **les entrees s'ecrivent `HDMI 1` avec une espace, et il n'y a pas de
  HDMI 2** — un libelle approximatif aurait donne une pastille morte ;
- **la TV n'annonce pas `TURN_ON`**, seulement `TURN_OFF` — et pourtant le
  Wake-on-LAN *est* configure. Il vit en entite separee,
  `button.wake_on_lan_64_95_6c_3d_03_94`, dont le media_player webostv ignore
  tout. Le bouton d alimentation de la carte appelle donc **deux choses
  differentes selon l etat** : `media_player.turn_off` quand la TV est
  allumee, `button.press` sur le bouton WoL quand elle dort. Le role porte
  un champ `wake:` pour les lier, parce que rien d autre ne le peut.

Elle expose aussi `sound_output` (`tv_external_speaker` en ce moment, donc le
Marantz) et le domaine `webostv` offre trois services : `select_sound_output`,
`button` (pave directionnel) et `command`.

**C'est la vraie reponse a « choisir la sortie enceinte/Marantz ».** Ce n'est
pas une commande de l'ampli : c'est le televiseur qui decide s'il joue par
lui-meme ou par le Marantz, et rien du cote de l'ampli ne peut le rapporter.
La carte TV porte donc une rangee SORTIE : TV · Marantz · Optique.

### Doublons à nettoyer

Trois entités `receiver` identiques (`_2`, `_4`, `_5`), toutes avec 23 modes
sonores ; `_4` a une source de plus (`SOURCE`). Ce sont trois entrées de
configuration `denonavr` pour le même appareil. J'ai retenu `_2`.

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

## 5. Le Marantz NR1711 — n'écrivez pas d'intégration

**Les modes sonores existent déjà.** L'entité `media_player.marantz_nr1711_2`
publie `SELECT_SOUND_MODE` et **23 modes** :

```
MUSIC · MOVIE · GAME · AUTO · STANDARD · VIRTUAL · MATRIX · ROCK ARENA
JAZZ CLUB · VIDEO GAME · MONO MOVIE · SUPER STADIUM · CLASSIC CONCERT
WIDE SCREEN · DIRECT · PURE DIRECT · DOLBY DIGITAL · DTS SURROUND
AURO3D · AURO2DSURR · MCH STEREO · STEREO · ALL ZONE STEREO
```

et **13 sources** : 8K, AUX, Blu-ray, Bluetooth, CD, Decodeur UHD, Game,
HEOS Music, MBox Meson Ref, PS4, Phono, TV Audio, Tuner.

### Pourquoi vous ne les voyiez pas

Le NR1711 crée **deux entités de natures différentes**, et celle sans suffixe
est la plus pauvre :

| Entité | Nature | Ce qu'elle offre |
|---|---|---|
| `marantz_nr1711` | **HEOS**, le lecteur réseau intégré | lecture, navigation, volume — *pas de marche/arrêt, pas de modes* |
| `marantz_nr1711_2` | **denonavr**, l'ampli lui-même | marche/arrêt, sources, **modes sonores** |

Vous regardiez la première. Ce n'était pas une intégration pauvre, c'était la
mauvaise entité — et cela ferme la question : **aucun pont `vssp_marantz.py`
n'est nécessaire**, aucun port à ouvrir, aucune intégration à écrire.

Les deux servent, et le gabarit les emploie toutes les deux : la HEOS devient
le rôle `streamer` du tableau `audio` (son état `idle` est bien celui d'un
lecteur), la denonavr devient le rôle `amplifier`.

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
