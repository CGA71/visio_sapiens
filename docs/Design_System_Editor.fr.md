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

## Périmètre de cette phase (MVP)

Seuls les **tokens de thème natifs Home Assistant** sont couverts :
ceux déjà déclarés dans `themes/visio_sapiens.yaml` avant ce
changement (palette, en-tête, séparateur, icônes, forme des
cartes/dialogues, sidebar). Ils pilotent button-card, mushroom et
card_mod partout où ils utilisent un `var(--...)` du thème actif.

**Pas encore couvert** — l'aspect vitre néon (bordures, flou, ombre)
codé en dur en valeurs littérales dans les blocs `card_mod` à travers
`templates_j2/*.j2` (67 occurrences sur 8 templates au moment de la
rédaction), et dupliqué à nouveau dans les propres blocs `<style>` des
pages wizard (`assign.html`, `vssp_rooms_floors.html`, etc.). Éditer
une couleur dans l'écran THEME aujourd'hui change tous les
consommateurs de tokens natifs, mais pas ces blocs codés en dur.

### Phase 2 (à venir, non implémentée ici)

Refactoriser chaque occurrence codée en dur de
`rgba(0,229,255,...)` / `border-radius: 18px` /
`backdrop-filter: blur(12px)` / `Orbitron` dans `templates_j2/*.j2` et
dans les pages HTML des wizards pour qu'elles consomment des
propriétés personnalisées `var(--vssp-*)` à la place — des propriétés
que le `theme.yaml.j2` de cette phase peut déjà émettre une fois la
décision prise. À ce moment-là, une modification dans l'écran THEME
changera littéralement tout l'aspect visuel du produit, pas seulement
les tokens que les composants Home Assistant comprennent déjà. C'est
un chantier plus large et plus risqué (retester visuellement 8
templates), volontairement hors périmètre du MVP décrit dans ce
document.

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
