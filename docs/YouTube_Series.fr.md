# Visio Sapiens — Plan de la série YouTube

**Français** · [English](YouTube_Series.md)

Ce document fait correspondre la documentation du projet à une séquence de
vidéos. Chaque épisode a une doc source (après la consolidation de `docs/`),
une question centrale à laquelle il répond, et une démo suggérée à l'écran.
Les épisodes sont ordonnés pour que chacun s'appuie sur ce que le précédent a
montré — mais les épisodes 2 à 7 peuvent être filmés dans le désordre si un
sujet est plus urgent ou plus prêt visuellement.

Les docs sources citées ci-dessous sont les noms **consolidés** (voir
`Manifest.md` pour la correspondance ancien → nouveau pendant la transition).

---

## Vue d'ensemble

| # | Titre | Doc source | Question centrale | Ancrage visuel |
|---|---|---|---|---|
| 1 | Vision & architecture | `Vision.md` | Pourquoi remplacer les cartes natives de Lovelace par un moteur maison ? | Diagramme d'architecture + visite du dashboard HOME |
| 2 | CORE — le dashboard système | `Core_Dashboard.md` | Comment une page HTML statique transforme les métriques Glances en jauges vivantes ? | `core.html` en direct, onglet réseau des DevTools ouvert |
| 3 | Le générateur de dashboards | `Dashboard_Generator.md` | Pourquoi générer le YAML depuis un modèle plutôt que l'éditer à la main ? | `model/house.yaml` → régénération → diff dans le navigateur |
| 4 | Étude de cas : câbler une pièce entière | `Integration_Case_Study.md` | Que signifie concrètement « ajouter une fonctionnalité de bout en bout » ? | Dashboard Technical Room, avant/après |
| 5 | Étude de cas : le wizard d'assignation d'appareils | `Device_Assignment_Wizard.md` | Comment transformer un scan brut d'entités en formulaire sûr et vérifiable ? | L'iframe assign.html, scan → assignation → application en direct |
| 6 | Le pipeline CI/CD | `CI_CD.md` | Comment un seul commit atteint deux cibles très différentes (k3s staging, HAOS production) ? | Graphe du pipeline GitLab, un run en direct |
| 7 | Sessions de débogage | `Troubleshooting.md` | À quoi ressemble vraiment la traque d'un bug qui « ne devrait pas être possible » ? | Terminal + DevTools navigateur, vraies enquêtes |

---

## Épisode 1 — Vision & architecture

**Objectif :** donner aux spectateurs le modèle mental avant tout code. Ce
qu'est Visio Sapiens (une interface façon centre de contrôle posée sur Home
Assistant, pas un simple dashboard habillé), et pourquoi le projet refuse les
cartes Lovelace natives sauf exceptions documentées (`weather-forecast`,
`logbook`, `apexcharts-card`).

**À montrer à l'écran :**
- Le diagramme d'architecture de `Vision.md` (CORE / Room Engine / IA Layer /
  Animation Engine / CSS Engine / JS Engine / Theme Engine).
- Une visite en direct du dashboard HOME, en pointant des éléments concrets :
  la sidebar, la rangée HUD du header (météo, horloge, statut alarme,
  avatar), la rangée énergie.
- L'arborescence du dépôt, mise en correspondance en direct avec ce qui est
  affiché (`www/vssp/css/vssp.css` est littéralement ce qui peint cet écran).

**Points à aborder :**
- La règle unique qui pilote toutes les autres décisions : « Home Assistant
  n'est plus qu'un moteur de données ; l'interface est entièrement pilotée
  par VSSP. »
- La migration de nommage (OSVision → VSSP) comme étude de cas sur la façon
  dont l'histoire d'un projet laisse des traces — utile pour expliquer
  pourquoi certains noms de fichiers ne concorderont qu'à partir d'épisodes
  ultérieurs.
- La section changelog de `Vision.md` est un montage tout prêt de « tout ce
  qui a été livré » — bon pour une ouverture ou une conclusion en montage
  rapide.

**À ne pas filmer tout de suite :** tout ce qui dépend de secrets en direct
(mot de passe Livebox, jetons longue durée) — garder la gestion des secrets
pour l'épisode 4/6.

---

## Épisode 2 — CORE, le dashboard système

**Objectif :** une seule page, de bout en bout — de `psutil` sur l'hôte à une
jauge SVG dans le navigateur — comme un unique chemin de données que l'on
peut suivre pas à pas.

**À montrer à l'écran :**
- Le diagramme de chaîne de `Core_Dashboard.md` (Glances → intégration HA →
  `core.html`), redessiné ou repris tel quel.
- L'onglet Réseau des DevTools ouvert pendant que `core.html` interroge :
  les spectateurs voient le vrai appel `GET /api/states` et l'intervalle de
  30 secondes en temps réel.
- La fonction de correspondance floue `findEntity()` — un bon moment « voici
  une décision de conception subtile » : pourquoi aucun `entity_id` codé en
  dur, et le coût que ça a (une entité renommée casse silencieusement une
  jauge).

**Points à aborder :**
- Les deux boucles de polling indépendantes (Glances→HA à 60s, page→HA à
  30s) et pourquoi ça plafonne le « temps réel » à ~90 secondes — bon
  endroit pour inviter les questions des spectateurs sur les compromis.
- Le bug encore ouvert du chemin K3s (404 sur `/local/osvision_v2/...`)
  corrigé en direct : le trouver, expliquer pourquoi le `catch` avale
  l'erreur silencieusement, patcher la ligne, redéployer, montrer le panneau
  K3s reprendre vie.
- `esc()` et l'angle XSS — un aparté de 90 secondes sur pourquoi on échappe
  les données de son **propre** backend, pas seulement les entrées
  « non fiables ».

**Bon pairing :** le correctif en direct de cet épisode est une version
courte de ce que fait l'épisode 7 en détail — envisager un renvoi croisé.

---

## Épisode 3 — Le générateur de dashboards

**Objectif :** expliquer le pipeline modèle → template → YAML généré qui a
remplacé les dashboards édités à la main — et le relier au travail du wizard
ROOMS & FLOORS, la matière la plus fraîche et la plus démontrable de tout le
projet.

**À montrer à l'écran :**
- `model/house.yaml` ouvert à côté de `templates_j2/energy.yaml.j2`, avec une
  valeur modifiée en direct (ajout d'un appareil) puis le générateur relancé.
- Le mode aperçu (`--preview`) qui génère un `energy_preview.yaml` isolé sur
  son propre `url_path` — une bonne démonstration d'un outillage « sans
  danger à casser ».
- L'écran admin ROOMS & FLOORS (ligne langue/format + iframe en direct) comme
  l'expression la plus récente et la plus aboutie de cette même idée — un
  pont naturel entre « voici le moteur » et « voici à quoi ça ressemble une
  fois fini ».

**Points à aborder :**
- Pourquoi Lovelace ne sait pas boucler sur une liste d'entités, et comment
  ça force la conception à deux vitesses du dashboard ENERGY (totaux scannés
  en direct vs. lignes par appareil générées).
- Les règles de fusion non destructive de `vssp_energy_sync.py` (nouvel
  appareil ajouté en fin de liste, appareil connu préservé, appareil disparu
  signalé mais pas retiré, `keep: true` comme échappatoire) — bonne matière
  pour « comment éviter qu'un script n'efface la personnalisation manuelle de
  quelqu'un ».
- Le pont encore ouvert (`vssp_model_sync.py`, wizard → modèle) comme
  accroche « dans un prochain épisode ».

---

## Épisode 4 — Étude de cas : câbler une pièce entière

**Objectif :** montrer que « ajouter une fonctionnalité de bout en bout » est
une checklist reproductible, pas une improvisation ponctuelle — en utilisant
l'intégration de Technical Room comme exemple travaillé.

**À montrer à l'écran :**
- Le tableau des fichiers de `Integration_Case_Study.md` : vues de
  dashboard, package HA, script de sonde LAN, gestion du secret — chacun
  ouvert brièvement.
- Le motif de gestion du secret pour `LIVEBOX_PASSWORD` : variable CI/CD
  masquée, transmise en argument positionnel du shell (jamais sur une ligne
  de commande visible), écrite avec `umask 077`. C'est un contenu vraiment
  instructif, pas une anecdote propre au projet — à cadrer ainsi.
- Les deux arbitrages encore ouverts (l'ambiguïté `_energie` vs.
  `_energie_jour`, l'image `technical.png` manquante) comme un moment
  honnête « voici ce qu'on n'a pas encore tranché » — bon pour
  l'authenticité.

**Points à aborder :**
- Pourquoi l'option `Protected` d'une variable CI/CD est un piège pour les
  déploiements staging depuis des branches non protégées — une leçon GitLab
  concrète et transférable.
- L'astuce de navigation : les liens vers Technical Room existaient déjà
  comme des liens morts ailleurs dans l'interface, donc l'intégrer a rendu
  des liens existants vivants plutôt que d'en ajouter de nouveaux.

---

## Épisode 5 — Étude de cas : le wizard d'assignation d'appareils

**Objectif :** une deuxième étude de cas, en contraste — un outil interactif
plutôt qu'un dashboard statique, et un bon moment pour montrer la forme
récurrente « découvrir → décider → appliquer » qu'on retrouve dans tout le
projet (c'est la même forme que le wizard ROOMS & FLOORS de cette session).

**À montrer à l'écran :**
- Le pipeline de `Device_Assignment_Wizard.md` :
  `DISCOVERY SCAN → report.json → prepare → assign_data.json → le formulaire
  → webhook → apply → house.yaml → le générateur → dashboards/views/`.
- Un cycle scan → assignation → application en direct dans le navigateur.
- Le tableau des fichiers vérifiés par MD5 comme moment « comment on s'est
  assuré que les bons fichiers sont partis » — s'accorde bien avec le
  post-mortem du cache de l'épisode 7.

**Points à aborder :**
- « Rien n'est jamais écrit à moitié » : l'applicateur valide tout le
  payload avant de toucher `house.yaml`, et sauvegarde d'abord — bonne
  discussion sur l'atomicité dans un système sans vraies transactions.
- Relancer un scan ne réinitialise pas le travail précédent — une garantie
  subtile mais importante à souligner explicitement, car c'est exactement le
  genre de chose qui paraît anodine quand ça marche et catastrophique quand
  ça ne marche pas.

---

## Épisode 6 — Le pipeline CI/CD

**Objectif :** un seul commit, deux cibles de déploiement très différentes —
le pipeline double-cible comme sujet à part entière, indépendant de toute
fonctionnalité particulière.

**À montrer à l'écran :**
- Le diagramme du pipeline : MR/master → build → `deploy:staging` (k3s,
  `kubectl cp`) vs. tag → `deploy:production` (HAOS, SSH) avec une porte
  manuelle.
- Un run de pipeline GitLab en direct, étape par étape.
- Un des trous G1–G5 encore ouverts, corrigé en direct (G1, l'écart d'URL
  CSS/JS, est le plus visuel : une feuille de style en 404 qui devient une
  page stylisée à l'écran).

**Points à aborder :**
- La règle `workflow:` comme « premier réflexe de diagnostic » — un push sur
  une branche de fonctionnalité sans MR ouverte ne lance **rien**, le genre
  de chose qui fait perdre une heure si on ne sait pas le vérifier en
  premier.
- Pourquoi le fait que `configuration.yaml` nécessite un redémarrage complet
  de HA (pas un rechargement à chaud) était la cause racine de toute une
  classe de bugs « le staging semble inchangé » — lien direct avec
  l'épisode 7.
- Les secrets ne touchent jamais une ligne de commande ni un log : arguments
  shell positionnels en staging, stdin en production. Mérite une explication
  complète, c'est un savoir réutilisable bien au-delà de ce projet.

**Découpage optionnel :** si l'épisode 6 est trop long, le scinder en 6a
(mécanique du pipeline) et 6b (les trous G1–G5 comme épisode « problèmes
connus ») — la doc source se sépare déjà proprement sur cette ligne.

---

## Épisode 7 — Sessions de débogage

**Objectif :** l'épisode « enquête policière ». De vrais bugs, de vrais
symptômes, de vraies commandes lancées pour cerner la cause — le format qui
tend à le mieux performer parce que la résolution est gagnée à l'écran plutôt
que supposée.

**À montrer à l'écran, comme trois (ou quatre) mini-cas indépendants tirés de
`Troubleshooting.md` :**
1. **Le staging semble inchangé après un pipeline vert** — le job
   `deploy:staging` ne redémarrait jamais Home Assistant, donc
   `lovelace.dashboards` et `homeassistant.packages` continuaient de servir
   une config périmée alors même que les fichiers sur disque étaient
   corrects. Corrigé en ajoutant le redémarrage + l'attente de disponibilité.
2. **`OSV_PREFIX` qui fait disparaître tous les dashboards en silence** —
   `"visio-sapiens".startswith("vssp")` vaut `False`, donc le patcher
   n'écrivait rien, alors que les `resources` (non filtrées) se mettaient à
   jour normalement — un bug classique « la moitié du déploiement a marché »,
   ce qui l'a rendu plus difficile à remarquer.
3. **Tableaux énergie vides après un sync qui annonçait un succès** — un
   jeton longue durée vide produisait un 401 silencieux, et
   `continue_on_error: true` laissait le générateur tourner quand même sur
   un modèle vide, écrasant un dashboard fonctionnel par un vide.
4. **Bonus, tiré des logs de cette session même :** le wizard ROOMS & FLOORS
   restant en français malgré un sélecteur de langue sur `en` — retracé
   jusqu'à un jeton de cache-busting `?v=` manquant sur une seule URL
   d'iframe, le seul actif de tout le pipeline non couvert par l'étape `sed`
   existante de cache-busting. Un bon cas de clôture car il montre que même
   un pipeline mature peut avoir exactement un coin non couvert, et que
   « c'est probablement mis en cache » vaut la peine d'être vérifié avant de
   supposer qu'un déploiement a échoué.

**Points à aborder :**
- Chaque cas suit la même forme : symptôme → première hypothèse fausse → la
  commande qui cerne vraiment la cause → cause racine → correctif → le
  garde-fou ajouté ensuite pour empêcher toute récidive silencieuse. Nommer
  cette forme explicitement rend le format reproductible pour de futures
  vidéos sur de nouveaux bugs.
- Le motif « pipeline vert, résultat inchangé » mérite d'être nommé comme un
  concept à part entière — il revient dans les cas 1, 2 et 4 sous des formes
  différentes.

---

## Notes de séquencement

- **1 → 3 → 5** est le fil naturel « voici le parcours du wizard, du début à
  la fin » — filmable comme un mini-arc même si les autres épisodes sortent
  plus tard.
- **2, 4, 6, 7** sont chacun autonomes et peuvent être réordonnés selon ce
  qui est visuellement prêt ou ce qu'un rapport de bug rend d'actualité une
  semaine donnée.
- L'épisode 7 gagne à être filmé **en dernier** chronologiquement pour chaque
  bug (c'est-à-dire une fois le correctif déployé et confirmé), mais peut
  être **publié** plus tôt si un cas est déjà entièrement résolu et
  documenté, comme c'est le cas pour trois des quatre actuellement.
- Les trois fichiers stubs sources de `Vision.md` (`vision.md`,
  `design-system.md`, `modules.md`) étaient vides avant cette consolidation —
  si un futur épisode veut une plongée dédiée sur le design system CSS
  spécifiquement, ce contenu n'existe pas encore et devra être écrit
  d'abord.
