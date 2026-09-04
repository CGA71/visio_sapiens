# Visio Sapiens — Générateur de dashboards (étape 5 du processus admin)

**Français** · [English](Dashboard_Generator.md)

## Principe

`views/energy.yaml` n'est plus édité à la main. Il est **généré** à
partir de :

- **`home-assistant/dashboards/model/house.yaml`** — le modèle métier :
  pièces, appareils, circuits, capteurs solaires/EDF, navigation
  (desktop `path` et mobile `path_mobile`). C'est le fichier que le
  processus admin alimentera (wizard Phase 1 = pièces, Phase 2 =
  scan + assignation).
- **`home-assistant/dashboards/templates_j2/energy.yaml.j2`** — le
  template Jinja2, qui porte la chartre graphique, le grid-layout, les
  polices et le modèle de cartes. Dérivé de l'`energy.yaml` original
  avec 100 % de fidélité (validé par comparaison structurelle des YAML
  parsés).

```
dashboards/model/house.yaml ──┐
                              ├── vssp/generate_dashboards.py
dashboards/templates_j2/*.j2 ─┘            │
                                           ▼
                          dashboards/views/energy.yaml
```

## Emplacement dans le repo (répertoires existants inchangés)

```
vssp/
├── vssp_discovery.py          EXISTANT — scan par Area → report.json
├── vssp_upgrade.py            EXISTANT — diff non destructif
├── generate_dashboards.py     ← NOUVEAU
└── build_template.py          ← NOUVEAU (templatise un dashboard existant)

home-assistant/
├── templates/                 EXISTANT — button_card_templates.yaml, …
└── dashboards/
    ├── views/
    │   └── energy.yaml        ← GÉNÉRÉ, ne pas éditer
    ├── model/                 ← NOUVEAU
    │   └── house.yaml
    └── templates_j2/          ← NOUVEAU
        └── energy.yaml.j2
```

Note sur les `!include` : le template `energy.yaml.j2` conserve tel quel
le chemin de votre dashboard fonctionnel
(`!include ../templates/button_card_templates.yaml`). Si vos includes
résolvent vers `home-assistant/templates/` dans votre déploiement,
rien à changer ; sinon adaptez cette ligne dans le `.j2` une seule fois
— elle sera reprise dans chaque génération.

## Utilisation

Depuis la racine du repo (les défauts du script pointent sur ces
chemins) :

```bash
pip install jinja2 pyyaml
python3 vssp/generate_dashboards.py
```

Puis rafraîchir l'onglet du dashboard (Ctrl+Maj+R). Aucun service de
rechargement n'est nécessaire : un dashboard en mode YAML est relu par
Home Assistant dès que le fichier change (comparaison de date dans le
cache Lovelace). Il n'existe d'ailleurs pas de service
`lovelace.reload` — seul `lovelace.reload_resources` existe, et il ne
concerne que les ressources JS/CSS.
En déploiement CI, le fichier généré part dans le paquet `dist/` comme
n'importe quel YAML de `dashboards/` — rien à changer au pipeline.

## Ajouter un nouvel objet connecté (manuellement, en attendant le pont wizard → modèle)

1. Ouvrir `home-assistant/dashboards/model/house.yaml`
2. Ajouter le device sous la bonne pièce :

```yaml
rooms:
  - id: livingroom
    name: "Salon"
    devices:
      - name: "TV"
        icon: mdi:television
        model: "Shelly Plug S"
        power_entity: sensor.shelly_tv_power
        energy_entity: sensor.shelly_tv_energy_today
```

3. Relancer `vssp/generate_dashboards.py` → la ligne apparaît dans le
   panneau « Consommation par appareil » d'ENERGY.

Si la pièce n'existe pas encore, l'ajouter dans `rooms:` (et dans `nav:`
si elle doit apparaître dans les sidebars — chaque entrée `nav` porte
`path` pour le desktop et `path_mobile` pour les dashboards `-m`).

## Dashboards système (ENERGY, CORE) — hors du cycle des pièces

ENERGY et CORE ne sont rattachés à aucune pièce Home Assistant. Ils ne
passent donc pas par le formulaire création / modification / suppression
du wizard, qui raisonne par pièce : ils ont leur propre cycle de vie,
piloté depuis le panneau ADMIN.

La carte vit dans son propre fichier,
`home-assistant/dashboards/admin/system_dashboards.yaml`, chargée par
`home.yaml` via `- !include admin/system_dashboards.yaml` — même
mécanique que vos vues.

Le panneau affiche **un seul emplacement à deux états**, pour qu'aucune
mauvaise manipulation ne puisse écraser un dashboard en place :

| État du fichier `views/energy.yaml` | Bouton affiché | Action |
|---|---|---|
| absent | **CRÉER ENERGY** | sync du parc + génération (`--only energy --if-missing`) |
| présent | **RÉGÉNÉRER ENERGY** | sauvegarde + sync + génération complète |
| (toujours) | **SYNC ENERGY** | met à jour les tableaux sans tout régénérer |

La bascule repose sur `binary_sensor.vssp_dashboard_energy_present`, un
capteur `command_line` qui teste l'existence du fichier toutes les 60 s.
Le bouton RÉGÉNÉRER affiche en libellé la date de dernière génération et
le nombre d'appareils mesurés détectés.

Double sécurité côté générateur : `--if-missing` fait que la création
**ne peut pas** écraser un fichier existant, même si le bouton est
cliqué par erreur ou si le capteur est en retard d'un cycle.

CORE apparaît dans le panneau pour la cohérence, mais son bouton est
inactif tant que `core.yaml.j2` n'existe pas. Quand le template sera
écrit, il suffira de décommenter l'entrée `core` dans `DASHBOARDS`
(`generate_dashboards.py`) et de dupliquer le couple conditionnel
d'ENERGY.

## ENERGY — un dashboard dynamique, à deux vitesses

ENERGY n'est pas un dashboard de pièce : il liste tous les appareils
mesurés de la maison. Sa mise à jour se fait à deux niveaux, et il est
important de savoir lequel s'applique à quoi.

| Panneau | Mécanisme | Régénération nécessaire ? |
|---|---|---|
| Consommation Totale (jour / mois / année) | **scan à l'exécution** — `packages/vssp_energy_totaux.yaml` somme tous les `*_puissance` et `*_energie` | **Non** — automatique |
| Puissance instantanée maison | scan à l'exécution (idem) | **Non** |
| Consommation par appareil (lignes) | boucle Jinja sur `model/energy_devices.yaml` | Oui |
| Tableau électrique (cases) | boucle Jinja sur `circuits` | Oui |

La raison de cette asymétrie : Lovelace ne sait pas boucler sur une
liste d'entités. Une somme, si — d'où des totaux réellement vivants,
et des tableaux qui demandent une passe de génération.

### La boucle automatique

```
appairage / suppression d'un Shelly
        │
        ├─► totaux : mis à jour immédiatement (scan)
        │
        └─► event entity_registry_updated
                │  (automation vssp_energy_autosync, temporisée 5 min)
                ├─► vssp_energy_sync.py    → met à jour energy_devices.yaml
                ├─► generate_dashboards.py → régénère views/energy.yaml
                └─► lovelace.reload
```

Une passe quotidienne à 04h30 sert de filet, au cas où un événement
aurait été manqué (redémarrage pendant un appairage).

### vssp_energy_sync.py — fusion non destructive

Le script apparie les capteurs d'un même appareil par radical d'entité
(`sensor.shelly_bureau_power` + `sensor.shelly_bureau_energy_today`),
détecte les `switch.*` pour le tableau électrique, puis fusionne avec
l'existant :

- **nouvel appareil** → ajouté en fin de liste ;
- **appareil déjà connu** → conservé tel quel, avec vos personnalisations
  (nom, icône, modèle, ampérage, ordre d'affichage) ;
- **appareil disparu de HA** → *signalé mais pas retiré*. Un Shelly hors
  ligne ne doit pas faire disparaître sa ligne. Le retrait effectif
  demande `--prune` (bouton PRUNE de l'ADMIN) ;
- **`keep: true`** sur un appareil → jamais retiré, même avec `--prune`
  (utile pour un équipement saisonnier).

Un appareil n'entre dans le tableau que s'il a **les deux** capteurs
(puissance ET énergie) : une ligne sans sa colonne énergie n'aurait pas
de sens. Les agrégats (`sensor.home_*`, `sensor.solar_*`,
`sensor.grid_*`, `*_room_power`) sont exclus pour éviter les doubles
comptes.

### Convention de nommage (la clé de tout)

| Suffixe | Sens | Entre dans les scans |
|---|---|---|
| `*_puissance` / `*_power` | puissance instantanée | oui (total puissance) |
| `*_energie` / `*_energy` | compteur cumulatif (lifetime) | oui (total énergie) |
| `*_energie_jour` / `*_energy_today` | compteur journalier | non — sinon on mélangerait kWh de vie et kWh du jour |

Le capteur `sensor.vssp_appareils_mesures` compte les appareils
détectés : si sa valeur dépasse le nombre de lignes du tableau, une
resynchronisation est en attente.

## Aperçu — itérer sans toucher au staging

Le wizard (phase 4) et le générateur savent produire un dashboard de
**test isolé**. Trois niveaux, du plus prudent au plus engageant :

| Mode | Commande | Écrit quoi |
|---|---|---|
| Validation seule | `--dry-run` | rien (juste le rapport JSON) |
| Aperçu | `--preview` | `views/energy_preview.yaml` (url `vssp-energy-preview`) |
| Publication | *(aucun flag)* | `views/energy.yaml` (staging) |

L'isolation repose sur trois choses simultanées : un **fichier de
sortie suffixé** (`_preview.yaml`), une **url_path distincte**
(`vssp-energy-preview`, donc une entrée Lovelace séparée déclarée une
fois pour toutes), et un **modèle séparé**
(`model/house_rooms.preview.yaml`). Aucun chemin de staging n'apparaît
dans la chaîne d'aperçu — ce n'est pas une convention de nommage, c'est
structurel.

Boucle d'itération type :

```bash
# 1. tester
python3 vssp/generate_dashboards.py --preview
# 2. ouvrir /vssp-energy-preview/energy, corriger le modèle ou le template
# 3. relancer autant de fois que nécessaire… puis seulement :
python3 vssp/generate_dashboards.py
```

Le générateur écrit un rapport JSON (`--status-file`) que le wizard lit
via `/local/vssp/preview_status.json` : nombre de pièces, appareils,
circuits, appareils en TODO, et erreurs de validation le cas échéant.

Déclaration du dashboard d'aperçu : voir
`config-fragment-preview.yaml` (à fusionner une fois dans
`home-assistant/config-fragment.yaml`). Pensez à ajouter les fichiers
`*_preview.yaml`, `*.preview.yaml` et `preview_status.json` au
`.gitignore` pour qu'ils ne partent jamais en CI.

## Garde-fous intégrés au générateur

- **Validation du modèle** avant rendu : champs obligatoires présents,
  pas d'entité assignée à deux pièces.
- **`StrictUndefined`** : une variable manquante dans le modèle fait
  échouer la génération au lieu de produire un trou silencieux.
- **Validation YAML du rendu avant écriture** : un template cassé ne
  remplace jamais un dashboard fonctionnel.

C'est complémentaire de `vssp_upgrade.py` : upgrade compare l'existant
aux découvertes (diagnostic), le générateur produit l'état cible
(construction).

## Intégration Home Assistant — à ajouter dans `vssp/vssp_admin_config.yaml`

Dans le même style que `vssp_discovery` / `vssp_upgrade` (le repo étant
déployé sous `/config` sur le pod) :

```yaml
shell_command:
  vssp_generate_dashboards: >-
    python3 /config/vssp/generate_dashboards.py
    --locale {{ states('input_select.vssp_language') }}
    --model /config/dashboards/model/house.yaml
    --templates /config/dashboards/templates_j2
    --out /config/dashboards/views

script:
  vssp_run_generate:
    alias: "Visio Sapiens — Régénérer les dashboards"
    sequence:
      - service: shell_command.vssp_backup_dashboard
      - service: shell_command.vssp_generate_dashboards
      - service: persistent_notification.create
        data:
          title: "Visio Sapiens — Dashboards régénérés"
          message: >
            energy.yaml a été régénéré depuis model/house.yaml.
            Rechargez Lovelace pour voir le résultat.
```

**`--locale` n'est pas optionnel ici, meme si le script accepte `None`
et retombe sur autre chose** : sa propre priorite est `--locale`
(selecteur de la console) > `house.locale` > `'en'`. Chaque
`shell_command` qui appelle `generate_dashboards.py` — celui-ci,
CREER/REGENERER pour HOME/ENERGY/CORE, les commandes d'apercu — a
besoin du flag explicitement, en lisant
`input_select.vssp_language`. L'omettre sur l'une d'elles fait que
cette commande regenere en silence dans ce que dit `house.locale` au
lieu de ce qu'affiche le selecteur de langue de l'ecran ADMIN, sans
aucune erreur : le dashboard revient juste dans la mauvaise langue.
Ceci a reellement touche `home-assistant/packages/vssp_admin.yaml` —
chaque `shell_command` la-bas manquait le flag jusqu'au 2026-09-04 ;
voir l'historique git pour le correctif sur les neuf points d'appel.

Un bouton GENERATE peut rejoindre la rangée DISCOVERY / UPGRADE /
DELETE du panneau ADMIN (`template: vssp_admin_button`,
`service: script.vssp_run_generate`).

## Pont wizard → modèle (le maillon manquant étapes 4 → 5)

Le wizard (Phase 2) connaît déjà `{entity_id, friendly_name, room}` ;
`vssp_discovery.py` produit `report.json` groupé par Area et
device_class. Prochaine brique : un petit
`vssp/vssp_model_sync.py` qui

1. lit `report.json` + les assignations du wizard,
2. mappe les entités `power`/`energy` par appareil (icône déduite du
   device_class, modèle depuis le device registry),
3. fusionne dans `model/house.yaml` **sans écraser** les champs déjà
   personnalisés (nom, icône),
4. appelle `generate_dashboards.py`.

`vssp_upgrade.py` sert alors de contrôle final : zéro écart attendu
entre les entités découvertes assignées et le dashboard généré.

## Templatiser les autres dashboards

`vssp/build_template.py` montre la méthode : remplacements exacts des
blocs répétitifs par des boucles Jinja + substitution des entités.
Candidats suivants, par ordre de rentabilité :

1. **`views/energy_mobile.yaml`** — même modèle `house.yaml`, layout
   mobile (dashboard `visio-sapiens-energy-m` déjà déclaré dans
   `config-fragment.yaml`).
2. **`home_mobile.yaml`** — les 12 tuiles de nav se génèrent depuis
   `nav:` avec `path_mobile`.
3. **`home.yaml`** — sidebar + KPIs + includes de vues pilotés par le
   modèle.
4. **`room.yaml.j2`** — un template unique par pièce qui génère
   `views/livingroom.yaml`, `views/bedroom1.yaml`, etc. depuis `rooms:`
   (les vues encore commentées en fin de `home.yaml`).

La charte graphique elle-même suit le même principe de génération
depuis un modèle : `themes/visio_sapiens.yaml` est désormais rendu
depuis `model/design_system.yaml` par `templates_j2/theme.yaml.j2`,
éditable graphiquement depuis l'écran THEME de la console ADMIN. Voir
[Design_System_Editor.fr.md](Design_System_Editor.fr.md).

## Partial d'en-tête partagé (`_header.j2`)

`templates_j2/_header.j2` est le bandeau horizontal par lequel s'ouvre
chaque dashboard (titre, météo, horloge/agenda) — inclus (`!include`)
depuis `home.yaml.j2`, `room.yaml.j2`, `energy.yaml.j2`,
`admin.yaml.j2` et `core.yaml.j2` pour qu'il existe une seule fois au
lieu de six copies. Depuis le 2026-09-04, il rend **le modèle
d'en-tête de HOME de façon inconditionnelle** pour chacun d'eux :

- **Case 1** — titre fusionné avec l'horloge (icône + titre +
  sous-titre à gauche, heure + date courte à droite) dans une seule
  carte, au lieu d'une case titre seule.
- **Case 3** — un `custom:calendar-card-pro` seul, l'agenda jour par
  jour (`days_to_show: 7`, `overflow-y: auto` puisqu'une semaine
  d'événements peut dépasser la ligne).

`calendar_entity` vaut par défaut `calendar.calebar` (la seule entité
`calendar.*` de cette installation) directement dans le partial via
`{% set calendar_entity = calendar_entity | default('calendar.calebar') %}`
— aucun appelant n'a rien à définir pour que le modèle s'applique ;
passer un autre id depuis un fichier `.yaml.j2` particulier pour
pointer ce seul dashboard vers un autre calendrier. La hauteur de la
ligne d'en-tête est passée de `105px` à `130px` chez chaque appelant
(`admin.yaml.j2` sur ses deux écrans, `core.yaml.j2`,
`energy.yaml.j2`, et le budget de ligne dynamique par pièce calculé
dans `compute_room_grid()` de `generate_dashboards.py`) pour laisser
la place à la case fusionnée plus haute et au calendrier. Les
dashboards mobiles ne sont pas concernés — ils utilisent le
`_header_mobile.j2` séparé, une seule carte compacte sans place pour
un agenda.

Deux pièges d'implémentation à connaître si vous retouchez ce partial :

- **`custom:stack-in-card` n'est pas installée sur cette instance** —
  seule `custom:vertical-stack-in-card` l'est (vérifié en direct dans
  Paramètres > Tableaux de bord > Ressources). Une première version de
  la Case 3 utilisait la première et se rendait en « Erreur de
  configuration », effaçant l'horloge que l'en-tête affichait
  auparavant.
- **`custom:button-card` centre verticalement une carte ne portant
  qu'un `label:` par défaut.** La ligne flex de la Case 1 se retrouvait
  ~20px plus bas que les Cases 2/3 tant que `styles.grid` ne forçait
  pas explicitement `grid-template-rows: min-content` +
  `align-content: start` — le même contournement dont la case heure
  seule (la branche `{% else %}`, toujours utilisée par tout appelant
  hors HOME) avait déjà besoin pour la même raison.

## Grille des dashboards de pièce — disposition dynamique des tableaux (**proposé, pas encore implémenté**)

**Statut : conception validée le 31/08/2026, en attente de simulations
avant tout code.** Tout ce qui suit décrit un comportement *cible*, pas
ce que fait actuellement `room.yaml.j2`. Le mécanisme livré aujourd'hui
— une grille dessinée à la main par `slot_set` dans `DEFAULT_LAYOUTS`
(`generate_dashboards.py`), l'un de `default` / `toilet` / `garden` /
`utility` / `entrance` / `minimal` / `computer` — reste la référence
tant que ceci n'est pas réellement construit et validé.

### Pourquoi changer

`DEFAULT_LAYOUTS` est une grille figée par préréglage nommé : chaque
pièce utilisant `default` obtient exactement les mêmes proportions,
que son tableau `appliances` porte neuf appareils ou un seul. Faire
grandir le vocabulaire de tableaux (cinq aujourd'hui, le tableau
`infrastructure` de `computer` ajouté par-dessus) veut dire dessiner à
la main une nouvelle grille pour chaque nouvelle combinaison qui
compte. La proposition remplace la *forme* de la grille par un calcul
basé sur ce que la pièce contient réellement, tandis que `slot_set`
continue de décider *quels* tableaux sont candidats (cette partie ne
change pas — voir « Jeux de tableaux » plus haut dans ce document et
`KNOWN_SLOT_SETS` dans `vssp_assign_prepare.py`/`vssp_rooms_apply.py`).

### L'algorithme

Vocabulaire :
- **tableau par défaut** — l'un des cinq tableaux candidats de la
  pièce, choisi pièce par pièce (un nouveau champ, pas encore ajouté
  au schéma des pièces de `house.yaml`). Toujours rendu, pleine
  largeur, en haut de la grille, même vide.
- **tableaux secondaires** — les autres candidats. Un tableau
  secondaire à zéro appareil assigné **n'est pas rendu du tout** (pas
  de placeholder `slot.empty` ici — c'est le seul changement de
  comportement délibéré par rapport aux grilles statiques actuelles,
  où un tableau vide-mais-dans-le-jeu affiche quand même « aucun
  appareil pour l'instant »).
- **poids** — le nombre d'appareils d'un tableau secondaire
  (`len(slot.entities)`, déjà calculé par `normalise_slots()`).

Étapes :
1. Réserver le tableau par défaut → bandeau pleine largeur, hauteur
   fixe, en haut.
2. Écarter tout tableau secondaire de poids 0.
3. Trier les secondaires restants par poids décroissant.
4. Les répartir en au plus deux étages :
   - **Étage A** — les 2 plus lourds, partageant un bloc à hauteur
     fixe (3 lignes de grille) sous le tableau par défaut. 1 tableau
     présent → il remplit le bloc seul ; 2 présents → cote à cote,
     largeur proportionnelle au poids.
   - **Étage B** — les 2 suivants par poids (n'existe que si 3 ou 4
     secondaires sont présents), partageant une ligne en bas, même
     règle de largeur proportionnelle. 1 tableau en étage B → remplit
     la ligne seul.

| Secondaires présents | Étage A | Étage B |
|---|---|---|
| 1 | ce tableau, bloc entier | — |
| 2 | les deux, repartis par poids | — |
| 3 | les 2 plus lourds, repartis par poids | le 3e, ligne entière |
| 4 | les 2 plus lourds, repartis par poids | 3e + 4e, repartis par poids |

Formule du nombre de colonnes pour un membre d'étage, sur une grille
de contenu à 12 colonnes :

```
col_span = round(12 × son_poids / poids_total_de_l_etage)
```

plafonné pour qu'aucun membre ne descende sous un minimum lisible
(valeur exacte du plafond : question ouverte, voir plus bas).

### Exemple chiffré

Une pièce avec `switches` comme tableau par défaut, et quatre
secondaires présents : `appliances` (9 appareils), `sensors` (3),
`security` (2), `infrastructure` (2).

```
switches — par défaut, pleine largeur, ligne 1
┌──────────────────────────────┬───────────────┐
│ appliances (9)                │ sensors (3)   │   étage A, 3 lignes
│ 9/12 col                      │ 3/12 col      │
├───────────────────┬───────────┴───────────────┤
│ security (2)       │ infrastructure (2)        │   étage B, 1 ligne
│ 6/12 col            │ 6/12 col                  │
└───────────────────┴────────────────────────────┘
```

### Questions ouvertes à trancher pendant les simulations de demain

- **Valeur du plafond** pour `col_span` — jusqu'où un membre d'étage
  peut-il s'amincir avant de devenir inutilisable (un nombre de
  colonnes minimum, ou un pourcentage minimum) ?
- **Hauteurs de ligne** — les 3 lignes de l'étage A et la 1 ligne de
  l'étage B sont-elles des valeurs pixel/`fr` fixes, ou varient-elles
  aussi selon quelque chose ?
- **Format mobile** — `room_mobile.yaml.j2` est mono-colonne ; l'ordre
  basé sur le poids (défaut d'abord, puis secondaires du plus lourd au
  plus léger) s'y applique-t-il aussi, même sans l'étagement 2D ?
- **Règle actuelle « switches toujours pleine largeur »** — le nouveau
  mécanisme de tableau par défaut la remplace-t-il purement et
  simplement, ou `switches` peut-il encore être forcé pleine largeur
  même quand ce n'est pas le tableau par défaut choisi ?
- **Égalité de poids** — quand deux secondaires ont le même nombre
  d'appareils, qu'est-ce qui départage (ordre des tableaux dans
  `SLOTS`, alphabétique, autre chose) ?
- **Pièce entièrement à zéro** — une pièce où chaque secondaire est
  vide (seul le tableau par défaut a du contenu, ou rien du tout) :
  la grille se réduit-elle juste au bandeau par défaut, ou autre chose
  remplit-il l'espace restant ?
