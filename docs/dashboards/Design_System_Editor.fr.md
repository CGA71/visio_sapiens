# Visio Sapiens — Éditeur de charte graphique (ADMIN, écran THEME)

**Français** · [English](Design_System_Editor.md)

## Principe

La charte graphique (couleurs, en-tête, sidebar, forme des cartes/
dialogues) vivait dans un seul fichier édité à la main,
`themes/visio_sapiens.yaml`. Il est désormais **généré**, de la même
manière que `views/energy.yaml` est généré (voir
[Dashboard_Generator.fr.md](Dashboard_Generator.fr.md)), à partir de :

- **`home-assistant/dashboards/model/design_system.yaml`** — les
  tokens de design : palette, en-tête, séparateur, icônes, forme des
  cartes/dialogues, sidebar. C'est le fichier qu'une personne (ou
  l'éditeur graphique ci-dessous) édite.
- **`home-assistant/dashboards/templates_j2/theme.yaml.j2`** — le
  template Jinja2 qui rend ces tokens dans la forme exacte qu'attend
  Home Assistant pour un fichier de thème.

```
model/design_system.yaml ──┐
                           ├── generate_dashboards.py --only theme
templates_j2/theme.yaml.j2 ┘            │
                                        ▼
                          themes/visio_sapiens.yaml
```

`themes/visio_sapiens.yaml` n'est **plus édité à la main** — éditez
`design_system.yaml` à la place, puis lancez
`python3 vssp/generate_dashboards.py --only theme`, ou utilisez
l'écran THEME de la console ADMIN décrit plus bas, qui fait la même
chose plus un rechargement à chaud.

## Pourquoi aucune régénération de dashboard n'est nécessaire

Chaque dashboard produit par `generate_dashboards.py` lit ses couleurs
depuis le **thème Home Assistant actif** (`house.theme` dans
`house.yaml`), jamais depuis une copie qui lui serait propre. Changer
le thème est donc toute la mise à jour : aucun `views/*.yaml` n'a
besoin de changer, donc le pipeline THEME ne touche jamais
`dashboards/views/` et n'appelle jamais `lovelace.reload`. Le seul
service qui compte est `frontend.reload_themes`, qui recharge à chaud
chaque fichier `themes/*.yaml`. C'est plus léger que les pipelines
ENERGY/HOME/CORE, qui régénèrent bien des vues et prennent donc une
sauvegarde de dashboard et appellent `lovelace.reload`.

## L'écran THEME — un éditeur graphique, pas un formulaire texte

L'écran THEME de la console ADMIN (`/visio-sapiens-admin/theme`) suit
exactement le même patron déjà utilisé par ROOMS et ASSIGN : une page
HTML statique dans une iframe, qui parle à Home Assistant via un
**webhook local sans jeton** plutôt que par l'API REST — une iframe ne
peut pas atteindre l'objet `hass` de la page parente, et un jeton REST
longue durée n'a rien à faire dans un navigateur pour cela. Voir
`home-assistant/www/vssp/wizard/vssp_theme_editor.html`.

L'éditeur propose :
- un sélecteur de couleur par token hexadécimal simple (primary/accent,
  fonds, texte, en-tête, icônes, sidebar) ;
- un champ texte simple (avec une indication de format) pour les
  quelques tokens qui portent un canal alpha (`card_background`,
  `dialog_scrim`, `sidebar_selected_background`, `bubble_backdrop`),
  car un `<input type=color>` natif ne peut pas représenter un
  `rgba(...)` ;
- des curseurs pour `card_radius`, `card_border_width`,
  `dialog_radius` ;
- deux sélecteurs de police, `font_display` et `font_body` (voir
  *Typographie* plus bas), chacun avec une ligne d'échantillon dessinée
  dans la police choisie ;
- cinq curseurs de taille par usage — horloge, titres, valeurs, texte,
  libellés — affichant chacun son pourcentage et la taille résultante ;
- un **aperçu live** — une maquette autonome mise à jour à chaque
  saisie, entièrement côté client, sans aller-retour ;
- **Export** (télécharge les tokens courants en JSON) et **Import**
  (recharge un fichier exporté précédemment dans le formulaire) — ce
  que `adminmenu.section.theme_hint` dans les catalogues de locale
  (« Importer ou exporter la charte graphique CSS ») promettait déjà.

## Déploiement : `design_system.yaml` est un état côté pod

`.gitlab-ci.yml` remplace tout le dossier `dashboards/` à chaque
déploiement, puis recopie une courte liste blanche de fichiers depuis
l'ancienne copie parce qu'ils sont écrits sur l'instance, pas livrés
par le dépôt — `model/house_rooms.yaml` (le wizard des pièces),
`model/energy_devices.yaml` (le sync énergie), `views/home.yaml`
(édition Lovelace manuelle). `model/design_system.yaml` figure
désormais dans cette même liste blanche, puisque `vssp_theme_apply.py`
l'écrit exactement de la même manière. Sans cela, chaque déploiement
annulait en silence toute couleur appliquée depuis l'écran THEME pour
revenir à la valeur par défaut du dépôt — précisément la panne que
cette section existe pour empêcher. (La production n'a encore aucune
étape de régénération de dashboard côté pod, donc ses données
ENERGY/THEME ne sont fraîches que jusqu'à la dernière modification
faite en direct sur cette instance ; le staging régénère aussi
`themes/visio_sapiens.yaml` depuis le modèle préservé juste après
l'échange du déploiement, à l'image de la régénération ENERGY côté pod
déjà existante.)

## Revenir à la référence d'usine

`design_system.yaml` est désormais un état côté pod (voir ci-dessus),
donc une fois qu'une couleur est éditée depuis l'écran THEME, plus rien
dans le dépôt ne peut l'écraser en silence — c'est tout l'intérêt. Mais
cela veut aussi dire qu'il faut un chemin de retour explicite.

**`home-assistant/dashboards/model/design_system.default.yaml`** est
une seconde copie figée de la même structure `design:`, jamais écrite
par `vssp_theme_apply.py` et jamais listée dans la liste blanche « état
pod préservé » de `.gitlab-ci.yml` — elle part toujours avec ce que le
dépôt déclare actuellement comme référence, rafraîchie à chaque
déploiement comme n'importe quel template.

Le bouton **RESTAURER LA RÉFÉRENCE** de l'écran THEME (à côté de
l'iframe, avec une boîte de confirmation, même forme que REGENERER
HOME/ENERGY) appelle `vssp_theme_apply.py --restore-reference
design_system.default.yaml`, qui construit un payload
`{"tokens": {...}}` normal directement depuis ce fichier et le fait
passer par exactement le même code `validate()` / `apply()` /
sauvegarde qu'une vraie soumission de l'éditeur — pas de logique de
réinitialisation séparée à maintenir en phase. Il régénère ensuite le
thème et le recharge à chaud, exactement comme un APPLIQUER normal.

Pour changer la référence d'usine elle-même (un rebranding délibéré,
pas une édition quotidienne), modifiez `design_system.default.yaml` et
committez-le — `design_system.yaml` reste inchangé par ce changement
tant que personne ne clique sur RESTAURER LA RÉFÉRENCE.

## Pipeline déclenché par APPLIQUER

```
vssp_theme_editor.html (iframe)
        │  POST tokens en base64, aucun jeton, reseau local uniquement
        ▼
webhook `vssp_theme`  (home-assistant/packages/vssp_theme.yaml)
        ▼
vssp/vssp_theme_apply.py
        │  valide chaque token (vssp_design_fields.py : format
        │  couleur/rgba/longueur, bornes des rayons) — un payload
        │  invalide n'ecrit RIEN
        │  ecrit dans model/design_system.yaml (ruamel.yaml, commentaires conserves)
        │  sauvegarde l'ancien design_system.yaml d'abord
        ▼
generate_dashboards.py --only theme
        │  rend theme.yaml.j2, valide le YAML, sauvegarde l'ancien
        │  themes/visio_sapiens.yaml, ecrit le nouveau
        │  ecrit aussi design_system_status.json (valeurs plates, lu
        │  par l'editeur au prochain chargement)
        ▼
service frontend.reload_themes   ← la mise a jour dynamique
```

Chaque étape qui peut refuser une entrée invalide le fait — une
couleur invalide ou un rayon hors bornes est refusé par
`vssp_theme_apply.py` avant d'atteindre `design_system.yaml`, tout
comme `vssp_assign_apply.py` refuse une assignation impossible avant
qu'elle n'atteigne `house.yaml`.

## `vssp/vssp_design_fields.py` — la source unique de vérité des tokens

Un petit module sans dépendance liste chaque token éditable, son
chemin sous `design:`, et sa règle de validation (dict `FIELDS`). Il
est importé par :
- `vssp_theme_apply.py` (valide un payload soumis face à cette table —
  a besoin de `ruamel.yaml`, dont ce module ne dépend
  volontairement **pas**) ;
- `generate_dashboards.py` (écrit `design_system_status.json` à partir
  de cette table — les seules dépendances de ce script restent
  `jinja2` + `pyyaml`, voir
  [Dashboard_Generator.fr.md](Dashboard_Generator.fr.md)).

Extraire le vocabulaire de cette manière garantit que le formulaire de
l'éditeur, la validation du webhook et le fichier de statut qu'il lit
en retour ne peuvent jamais diverger — il n'existe qu'une seule liste
de noms de tokens.

## `selector_background` — un seul aspect pour tous les sélecteurs

La console ADMIN contient cinq contrôles `input_select` : langue et
format apparaissent deux fois (PIÈCES & ÉTAGES et GÉNÉRATION), plus le
fournisseur de chatbot. Les cinq se rendent de la même manière, et
`selector_background` est le token qui les colore.

La règle derrière cela : **un `input_select` dans cette console est
toujours une carte `tile` avec une fonctionnalité `select-options` en
ligne, jamais une ligne dans une carte `entities`.** Le picker Material
natif sur lequel retombe une ligne d'entities se rend en remplissage
blanc large tant que chaque variable de thème MDC n'est pas définie, et
reste un picker pleine largeur plutôt que la rangée de pastilles
compacte utilisée partout ailleurs dans la console.

Dans `admin.yaml.j2`, cet aspect est émis par une macro Jinja
`selector_card_mod()` plutôt que par une ancre YAML. Tous les écrans
atterrissent dans **un seul** document généré, dans l'ordre de `screens`
: une ancre définie sur un écran et aliasée depuis un autre dépend donc
silencieusement de celui des deux qui est émis en premier — réordonner
`screens` la casserait. Une macro n'a pas ce couplage.

Pointer le fond vers `selector_background` plutôt que vers
`card-background-color` est délibéré : cela garde les sélecteurs
ajustables depuis l'écran THEME, indépendamment de toutes les autres
cartes de la console.

## Champs texte — `input_background` / `input_ink` / `input_label`

La boîte éditable que rend une ligne `input_text` (« Calendrier affiché
dans le bandeau » de l'écran CALENDRIER) est le seul champ texte de toute
la console, et elle est arrivée en boîte blanche contenant un libellé
cyan pâle et une valeur blanche — illisibles tous les deux sur un écran
sombre.

La cause mérite d'être notée, car deux réponses plausibles sont fausses.
Home Assistant a livré trois générations de composants de formulaire, et
un thème peut poser les noms des trois sans aucun effet :

| Génération | Variable de remplissage | Lue par ce widget ? |
|---|---|---|
| Material (MDC) | `--mdc-text-field-fill-color` | non |
| Couche propre à HA | `--input-fill-color` | non |
| **Web Awesome** (`ha-input` > `wa-input`) | **`--ha-color-form-background`** | **oui** |

Le thème posait déjà les deux premières. Mesuré sur la console en
production : le champ était en `rgb(243,243,243)` avec du texte en
`rgb(255,255,255)` alors que `--mdc-text-field-fill-color` était bien
sombre — le widget ne la lit tout simplement pas. La déclaration gagnante
est `.input::part(base)`, dans le shadow root de `ha-input`.

Le champ est désormais volontairement gris clair avec une encre sombre :
un endroit où l'on saisit se lit mieux en surface claire qu'en énième
panneau sombre. Cela demande trois tokens et non un — le remplissage plus
les deux textes qui reposent dessus, la valeur et un libellé plus doux.

**Ces trois valeurs sont appliquées par `admin.yaml.j2` en `card_mod`
limité à la carte, pas via le thème.** Le libellé flottant lit
`--secondary-text-color`, un token *global*, correct partout ailleurs
dans l'interface. Le basculer vers une encre sombre pour tout le thème
afin d'arranger un seul champ casserait le texte secondaire dans toute
l'UI : il n'est donc basculé que là où un champ clair se trouve
réellement.

Si un second champ texte apparaît un jour sur un autre écran, il faudra
les trois mêmes lignes — c'est le coût de cette limitation de portée, et
c'est le côté le moins cher de l'arbitrage.

## Typographie — `font_display` / `font_body`

Deux polices, stockées sous `design.typography` comme un **nom** de
famille choisi dans une liste fermée (`FONTS` dans
`vssp_design_fields.py`) : Orbitron, Rajdhani, Exo 2, Oxanium, Chakra
Petch, Share Tech Mono, Roboto, System. Le thème reçoit la pile CSS
complète de chacune, jamais le nom seul.

| Token | Variables de thème | Atteint |
|---|---|---|
| `font_display` (défaut Orbitron) | `--vssp-font-display` | tout ce que les templates codaient en dur en `Orbitron` : pastilles de nav et nav mobile, titre et horloge du header, titres de page/section, en-têtes de pièce, valeurs énergie, ampérages des circuits |
| `font_body` (défaut Roboto) | `--vssp-font-body`, `--ha-font-family-body`, `--primary-font-family`, `--paper-font-common-base_-_font-family`, `--mdc-typography-font-family` | tout le reste du texte — entrées de la nav desktop, contenu des cartes, lignes natives, dialogues |

Chaque template écrit `var(--vssp-font-display, Orbitron, sans-serif)`,
donc un dashboard affiché sans le thème Visio Sapiens garde son ancien
aspect. La police de texte ne demande aucun changement de template :
elle passe par les variables de police de Home Assistant lui-même, que
le thème du dashboard pose sur `<html>` (mesuré en 2026.8 : surcharger
`--ha-font-family-body` à cet endroit change aussitôt la police des
entrées de nav).

**Pourquoi une liste fermée et pas du texte libre.** Un nom de famille
n'est que la moitié d'une police — il faut aussi servir le fichier.
Avant ce changement, aucune page ne chargeait Orbitron : `document.fonts`
sur le dashboard en ligne ne contenait que Roboto, donc chaque
`font-family: Orbitron` retombait sur sans-serif, sauf sur les machines
où la police se trouvait installée. Les polices sont désormais
auto-hébergées sous `www/vssp/fonts/` (sous-ensemble latin, woff2, SIL
OFL 1.1 — textes de licence à côté) et déclarées dans
`www/vssp/css/vssp_fonts.css`, que `vssp.css` `@import` et que l'éditeur
THEME lie directement. Aucune requête ne part vers Google Fonts : une
tablette murale rend la même chose sans internet. Ajouter une police,
c'est déposer son woff2 à cet endroit, la déclarer dans
`vssp_fonts.css`, et l'ajouter à `FONTS` et au miroir `FONT_STACKS` de
l'éditeur.

### Tailles de texte par usage — `size_clock` / `size_title` / `size_value` / `size_text` / `size_label`

Cinq **échelles**, pas cinq tailles, stockées en `"NNN%"` (50–200 %)
sous `design.typography.size`. Un rôle couvre volontairement plusieurs
tailles — un titre fait 20px dans le header, 15px sur une section, 11px
sur une sous-section — donc une valeur en pixels par rôle écraserait la
hiérarchie. Chaque `font-size` littéral de
`button_card_templates.yaml` et `templates_j2/*.j2` (201, plus les deux
tailles que button-card calcule en JS) vaut désormais
`calc(<px> * var(--vssp-scale-<rôle>, 1))`, classé selon ce qu'*est* le
texte :

| Rôle | Quoi | Exemples |
|---|---|---|
| `clock` | les chiffres de l'horloge du header | 24px desktop, 20px mobile |
| `title` | titre du header, logo de la sidebar, titres de page/section/carte | « HOME », « VISIO SAPIENS », « TOP 10 CONSUMPTION » |
| `value` | une mesure ou un état d'appareil | W, kWh, °C, ampères des circuits, thermostat, état de l'alarme |
| `text` | les noms et le texte propre à Home Assistant | entrées de nav, noms d'appareils, lignes |
| `label` | légendes, unités, aides, en-têtes de colonne, badges | « Smart Home OS », « kW », « CPU 6% » |

Le thème écrit chaque échelle comme un multiplicateur sans unité
(`120%` → `vssp-scale-value: "1.2"`) ; l'échelle `text` pilote aussi
`ha-font-size-scale`, le multiplicateur propre à Home Assistant, pour
que cartes et lignes natives suivent. L'éditeur affiche chaque curseur
en pourcentage et en taille résultante d'un texte de référence du rôle.

Les cartes tierces demandent le même branchement à la main :
`calendar-card-pro` dans le header avait des tailles fixes de
14/26/14px et ressortait comme la seule case surdimensionnée à une
échelle de 80 %. Ses options `*_font_size` sont recopiées telles quelles
dans des variables CSS, donc `_header.j2` leur passe
`calc(<px par défaut> * var(--vssp-scale-<rôle>, 1))` — chiffres de la
date sur `clock`, événements sur `text`, le reste sur `label`.

### Logo de nav — `nav_logo`

L'image sous le bandeau de navigation : `"default"` (house.logo),
`"none"`, ou une image envoyée depuis l'éditeur. Elle est peinte depuis
le thème (`--vssp-nav-logo`, `--vssp-nav-logo-display`), donc un nouveau
logo est actif dès l'APPLIQUER comme une couleur — sans régénération de
dashboard, HOME compris. C'est toujours un **carré** (`aspect-ratio:
1/1`) de la largeur du bandeau ; l'éditeur place l'image choisie entière
sur un canvas transparent de 256×256 (jamais rognée ni étirée) et la
ré-encode (WebP, sinon PNG) jusqu'à passer sous 48 Ko. Cette limite
garde le payload sous la limite Linux de 128 Kio pour une entrée argv —
le webhook le passe à `shell_command` en un seul argument.
`vssp_theme_apply.py` vérifie la signature du fichier (PNG/JPEG/WebP),
l'écrit dans `www/vssp_user/nav_logo.<ext>` — hors de `www/vssp/`, que
chaque déploiement remplace — et enregistre
`custom:nav_logo.<ext>?v=<horodatage>`, le `?v=` servant de clé de
cache. Une valeur `custom:` qui nomme un fichier absent est refusée.

### Largeur du bandeau de nav

Le bandeau fait la largeur de sa plus large entrée : chaque layout
desktop lui donne une colonne `max-content` (c'était `minmax(200px,
auto)`, plus un `min-width: 200px` dans `_nav.j2`), et le titre de
marque et le carré du logo portent `contain: inline-size`, ils
s'adaptent donc à la largeur choisie par les entrées au lieu d'imposer
la leur. Le bandeau est en `box-sizing: border-box` — avec
`width: 100%` en content-box, son padding et sa bordure s'ajoutaient
par-dessus et il débordait de 22px de sa propre colonne — et son
espacement est serré (bandeau 6px, entrée 8px, colonne d'icône 22px).
Mesuré en staging : 205px avant, 157px après, 16px entre le texte le
plus long et le bord du bandeau.

### Hauteur du bandeau d'en-tête

La ligne du header est `auto` dans chaque layout desktop (c'était 130px
fixes), chaque case la remplit, et la carte agenda est en
`contain: size` pour qu'une semaine d'événements ne la fixe jamais —
elle remplit la hauteur choisie par les autres cases et défile dedans.
HOME : bandeau de 118px pour 76px de contenu avant, 76px maintenant ;
des échelles horloge/titre/libellé plus grandes l'agrandissent d'elles-
mêmes (106px à 200/160/140 %). Réserve : la nav couvre la ligne du
header, donc sur une page dont le contenu serait plus court que la nav,
le surplus irait au header ; toutes les pages actuelles sont plus
hautes que la nav (585px).

**Le `design_system.yaml` du pod est antérieur à la section.** Le pod
garde sa propre copie d'un déploiement à l'autre, il n'a donc pas de
`typography:` avant le premier APPLIQUER. `generate_dashboards.py`
pose donc le fichier du pod sur `design_system.default.yaml` avant le
rendu : chaque token que le fichier du pod possède l'emporte, chaque
token qui lui manque vient de la référence, et le lancement affiche
lesquels. Avant cela, un seul token absent
(`palette.selector_background` en staging) faisait échouer tout le
rendu du thème côté pod à chaque déploiement — le thème restait celui
du dépôt et `design_system_status.json` n'était jamais écrit, l'éditeur
s'ouvrait donc sur les valeurs d'usine. `font_stack()` /
`size_scale()` se replient toujours d'eux-mêmes, et
`vssp_theme_apply.py` crée une section absente à l'écriture au lieu
d'échouer dessus.

**`/local` est mis en cache 31 jours.** Home Assistant sert `/local`
avec `max-age=2678400`, et sur cette instance les ressources Lovelace
sont en mode **storage** : le jeton `?v=` que le déploiement écrit dans
`configuration.yaml` n'atteint donc jamais le navigateur — la ressource
`vssp.css` était restée à `?v=4` et les navigateurs gardaient une copie
vieille de plusieurs mois. La ressource a été bumpée à la main
(`lovelace/resources/update`) pour livrer les polices ; tant que le
déploiement ne bumpe pas lui-même les ressources en mode storage, tout
changement de `vssp.css` demandera la même chose. `vssp_fonts.css` est
importé en `?v=1` — l'incrémenter à chaque changement de la feuille ou
d'un fichier de police.

## Périmètre de cette phase (MVP)

Seuls les **tokens de thème natifs Home Assistant** sont couverts :
ceux déjà déclarés dans `themes/visio_sapiens.yaml` avant ce
changement (palette, en-tête, séparateur, icônes, forme des
cartes/dialogues, sidebar). Ils pilotent button-card, mushroom et
card_mod partout où ils utilisent un `var(--...)` du thème actif.

**Désormais couverte** — la couleur des bordures/lueurs néon. Chaque
bordure, box-shadow et scrollbar-color `card_mod` à travers
`templates_j2/*.j2` (120 occurrences, 11 templates) codait en dur
`rgba(0,229,255,ALPHA)`, exactement le hex du token Primary par défaut,
sans jamais le lire. Elles utilisent désormais
`color-mix(in srgb, var(--primary-color, #00E5FF) N%, transparent)` —
même alpha par occurrence, donc rien ne change tant que Primary n'est
pas réellement édité, mais un APPLIQUER de l'écran THEME change
désormais visiblement chaque bordure et lueur néon du produit.

**Toujours pas couvert** — `border-radius` et `backdrop-filter: blur`
codés en dur en valeurs littérales dans ces mêmes blocs `card_mod`,
plus tout (bordures, flou, ombre, rayon) dupliqué à nouveau dans les
propres blocs `<style>` des pages wizard (`assign.html`,
`vssp_rooms_floors.html`, etc.). `border-radius` a été volontairement
laissé de côté plutôt que mappé mécaniquement : les littéraux `18px` et
`20px` sont utilisés de façon incohérente comme rayon de carte ET de
dialogue selon les templates (par exemple plusieurs cartes de
`energy.yaml.j2` utilisent `20px` comme leur propre rayon de carte, pas
un dialogue), donc les relier à `--ha-card-border-radius` vs
`--ha-dialog-border-radius` demande une lecture au cas par cas, pas un
chercher/remplacer — un risque de correction silencieusement erronée
qu'une passe mécanique pourrait introduire.

### Phase 2 (travail restant)

Refactoriser les occurrences `border-radius` / `backdrop-filter:
blur(12px)` restantes dans `templates_j2/*.j2` (au cas par cas, carte vs
dialogue) et chaque doublon dans les pages HTML des wizards, pour
qu'elles consomment `var(--ha-card-border-radius)` /
`var(--ha-dialog-border-radius)` — déjà émis tous les deux par
`theme.yaml.j2` — au lieu de littéraux. Le rayon de flou n'a pas encore
de champ correspondant dans `design_system.yaml`, donc le relier suppose
de décider d'abord s'il devient un token éditable. (La police est faite
— voir *Typographie* ; les blocs `<style>` propres aux pages wizard
nomment encore Orbitron directement, comme leurs couleurs.)

## Vérification

- `python3 vssp/generate_dashboards.py --only theme` rend
  `themes/visio_sapiens.yaml` depuis le `design_system.yaml` livré —
  le tout premier lancement produit un fichier identique à celui qu'il
  remplace, puisque le modèle a été construit comme une correspondance
  1:1 des valeurs précédemment écrites à la main.
- Changer une valeur dans `design_system.yaml` et relancer `--only
  theme` ne change que cette valeur dans le fichier rendu.
- `python3 vssp/vssp_theme_apply.py --dry-run --json-file <exemple>`
  rapporte quels tokens seraient écrits/rejetés sans toucher
  `design_system.yaml`.
- L'aller-retour webhook → `frontend.reload_themes` ne peut être
  exercé que sur un pod Home Assistant déployé, comme ROOMS/ASSIGN
  avant lui.
