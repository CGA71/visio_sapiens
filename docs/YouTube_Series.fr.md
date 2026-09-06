# Visio Sapiens — Plan de la série YouTube

**Français** · [English](YouTube_Series.md)

Ce document fait correspondre la documentation du projet à une séquence de
vidéos. Chaque épisode a une doc source (après la consolidation de `docs/`),
une question centrale à laquelle il répond, et une démo suggérée à l'écran.
Les épisodes sont ordonnés pour que chacun s'appuie sur ce que le précédent a
montré — mais les épisodes 2 à 12 peuvent être filmés dans le désordre si un
sujet est plus urgent ou plus prêt visuellement.

Les docs sources citées ci-dessous sont les noms **consolidés**, et chacune
existe dans `docs/` dans les deux langues (`X.md` / `X.fr.md`). Les épisodes
8 à 12 couvrent les documents écrits après la première version de ce plan :
c'est le matériau le plus récent et, pour cette raison, le plus démontrable.

---

## Vue d'ensemble

| # | Titre | Doc source | Question centrale | Ancrage visuel |
|---|---|---|---|---|
| 1 | Vision & architecture | `Vision.md` | Pourquoi remplacer les cartes natives de Lovelace par un moteur maison ? | Diagramme d'architecture + visite du dashboard HOME |
| 2 | CORE — le dashboard système | `Core_Dashboard.md` | Comment une page HTML statique transforme les métriques Glances en jauges vivantes ? | `core.html` en direct, onglet réseau des DevTools ouvert |
| 3 | Le générateur de dashboards | `Dashboard_Generator.md` | Pourquoi générer le YAML depuis un modèle plutôt que l'éditer à la main ? | `model/house.yaml` → régénération → diff dans le navigateur |
| 4 | Étude de cas : câbler une pièce entière | `Integration_Case_Study.md` | Que signifie concrètement « ajouter une fonctionnalité de bout en bout » ? | Dashboard Technical Room, avant/après |
| 5 | Étude de cas : le wizard d'assignation d'appareils | `Deployment.md` | Comment transformer un scan brut d'entités en formulaire sûr et vérifiable ? | L'iframe assign.html, scan → assignation → application en direct |
| 6 | Le pipeline CI/CD | `CI_CD.md` | Comment un seul commit atteint deux cibles très différentes (k3s staging, HAOS production) ? | Graphe du pipeline GitLab, un run en direct |
| 7 | Sessions de débogage | `Troubleshooting.md` | À quoi ressemble vraiment la traque d'un bug qui « ne devrait pas être possible » ? | Terminal + DevTools navigateur, vraies enquêtes |
| 8 | Automatiser une configuration OAuth | `Google_Calendar.md` | Jusqu'où peut-on automatiser la configuration OAuth d'un tiers — et où ça s'arrête ? | L'écran CALENDRIER : coller un ID client, atterrir sur la page de consentement Google |
| 9 | Un chatbot dans le dashboard | `Chatbot_Integration.md` | Comment brancher quatre fournisseurs de LLM derrière une seule carte, sans backend ? | La barre chatbot de HOME qui répond en ligne, fournisseur changé en direct dans l'ADMIN |
| 10 | L'éditeur de design system | `Design_System_Editor.md` | Comment rendre une charte graphique modifiable sans laisser casser l'interface ? | Écran THEME : changer une couleur, régénérer, voir toute l'UI suivre |
| 11 | Bilingue par construction | `Google_Calendar.md` (Langue de l'interface) + `locales/` | Que faut-il pour qu'une interface générée tienne **une** langue sur **un** écran ? | Le même écran en EN et en FR, côte à côte — et la version qui mélangeait les deux |
| 12 | Sauvegardes, rétention, et une revue de sécurité honnête | `Backup_Retention.md` + `Security.md` | Que doit-on à un utilisateur avant d'écraser son fichier — et que lui doit-on sur ce qui n'est pas sécurisé ? | Une sauvegarde écrite en direct, puis le vrai modèle de menace, dit franchement |

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
- Le pipeline de `Deployment.md` :
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

## Épisode 8 — Automatiser une configuration OAuth

**Objectif :** prendre une configuration que Home Assistant documente comme
un parcours manuel de neuf étapes dans *Paramètres > Appareils et services*
et la montrer se replier en un seul formulaire — puis s'arrêter honnêtement
sur la seule étape qui ne se replie pas.

**À montrer à l'écran :**
- Les deux parcours côte à côte : le natif (Identifiants d'application →
  Ajouter l'intégration → Google Calendar → consentement → choix du
  calendrier) face à l'écran CALENDRIER (coller deux valeurs → un bouton →
  consentement → choix du calendrier).
- Le détour websocket, en direct dans un terminal : `application_credentials`
  n'a **aucun** point d'accès REST, donc `vssp_google_setup.py` parle une
  centaine de lignes de RFC 6455 à la main plutôt que d'ajouter une
  dépendance au pod. Montrer les trames.
- Le clic de consentement lui-même, sur la page de Google — filmé plutôt que
  masqué, parce que c'est tout le propos.

**Points à développer :**
- « Automatiser tout ce qui entoure ce qu'on ne peut pas automatiser » est
  une règle de conception transposable, et OAuth en est l'exemple le plus
  net : l'écran de consentement existe *précisément* pour qu'aucun script ne
  signe à la place du propriétaire du compte. Le dire à voix haute vaut mieux
  que de faire croire à une automatisation totale.
- Le credential non modifiable (`UPDATE_FIELDS = {}`) : corriger une faute de
  frappe ne corrige pas un credential, ça en ajoute un second, et dès lors le
  config flow demande quelle implémentation utiliser. Excellent moment
  « la contrainte de l'API a changé ma conception » — le script répond avec
  l'id qu'il vient d'enregistrer, pas le premier de la liste.
- La gestion des secrets une fois de plus, cette fois comme un motif
  reconnaissable du projet plutôt qu'un cas isolé : le secret client est
  écrit dans un fichier 0600 et n'atteint jamais une ligne de commande,
  exactement comme `vssp_ha_token` et les clés du chatbot.

**Bon appariement :** l'épisode 11 reprend ce même écran comme exemple
travaillé — les filmer coup sur coup, tant que le matériau est frais.

---

## Épisode 9 — Un chatbot dans le dashboard

**Objectif :** quatre fournisseurs de LLM (Gemini, Claude, ChatGPT, plus un
point d'accès personnalisé) derrière une seule carte, sans service backend
propre au projet — et les contraintes qui façonnent une telle chose.

**À montrer à l'écran :**
- La barre chatbot de HOME qui répond en ligne, puis le sélecteur de
  fournisseur de l'ADMIN changé en direct et la même question reposée.
- Le chemin de stockage des clés : chaque clé de fournisseur dans son propre
  fichier protégé, même convention que partout ailleurs.
- Le formulaire du fournisseur personnalisé — le moment où la fonctionnalité
  cesse d'être « trois éditeurs codés en dur » pour devenir une interface.

**Points à développer :**
- Pourquoi la réponse revient *en ligne* plutôt que dans un popup, et ce que
  ça a changé dans la conception de la carte.
- Le piège du shadow DOM que rencontre tout travail sur les `custom_fields`
  d'une `button-card` : le HTML vit dans un shadow root, donc
  `document.getElementById` ne trouve rien et le handler doit recevoir `this`
  à la place. Court, concret, et ça épargnera une soirée à un spectateur.

---

## Épisode 10 — L'éditeur de design system

**Objectif :** une charte graphique qui tenait dans un fichier de thème
édité à la main, devenue un modèle plus un générateur plus un écran
d'édition — la même forme modèle→template→généré que l'épisode 3, appliquée
à l'apparence au lieu de la structure.

**À montrer à l'écran :**
- `model/design_system.yaml` à côté du thème généré, une couleur changée en
  direct, régénération, et toute l'interface qui suit.
- Le retour aux valeurs par défaut (`design_system.default.yaml`), qui est ce
  qui rend l'expérimentation assez sûre pour être filmée.
- Un piège CSS en direct, qui mérite son propre moment : `color-mix()` est
  bien analysé mais supprime silencieusement les bordures sur ce moteur de
  rendu, donc le projet calcule des `rgba()` à l'avance. « C'est du CSS
  valide et ça ne marche quand même pas » est une bonne leçon, honnête.

**Points à développer :**
- Où passe la ligne entre « thémable » et « cassable », et pourquoi un modèle
  par défaut dans le repo est le garde-fou qui permet à l'éditeur de rester
  permissif.
- Les design tokens comme contrat entre le générateur et le CSS — la raison
  pour laquelle une seule valeur peut déplacer toute l'interface.

---

## Épisode 11 — Bilingue par construction

**Objectif :** l'épisode sur un problème que la plupart des projets
découvrent bien trop tard — une interface en deux langues n'est pas une
tâche de traduction, c'est une contrainte d'architecture. Travaillé
entièrement sur l'écran CALENDRIER, le cas qui l'a rendu évident.

**À montrer à l'écran :**
- **Le bug d'abord**, parce qu'il se lit instantanément à l'écran : une seule
  page montrant des libellés traduits autour d'un formulaire figé dans
  l'autre langue, avec `not_configured` sous une légende traduite pour faire
  bonne mesure.
- Les trois sources de langue qui se rencontraient sur cet écran, chacune
  décidée dans son coin : les libellés générés (`t()` +
  `locales/<code>.yaml`), le formulaire intégré (ses propres chaînes figées),
  et les phrases d'état du script Python.
- Le correctif, en direct : `?lang=` transmis à l'iframe depuis la locale
  générée, une table `I18N` dans la page, `--locale` passé au script — puis
  le même écran rendu en EN et en FR côte à côte.
- Le fichier d'état comme artefact intéressant : il publie `state` (jeton
  machine non traduit), `state_label` (traduit), et `message_key` +
  `message_vars` **à côté** du `message` déjà rendu.

**Points à développer :**
- La règle qui en découle : **traduire au dernier moment possible, et ne
  jamais traduire ce qu'une machine lit.** Un jeton d'état sur lequel on
  s'aiguille et une phrase que lit un humain sont deux valeurs différentes
  qui se ressemblent — tout le bug consiste à les traiter comme une seule.
- Pourquoi `unit_of_measurement: "calendriers"` ne pouvait être sauvé par
  aucune précaution : ce n'est pas templatable, donc le seul geste correct
  était de la supprimer et de laisser le libellé traduit porter le sens.
  Savoir quels réglages *ne peuvent pas* être localisés, c'est la moitié du
  travail.
- La conséquence que l'utilisateur ressent : changer de langue impose une
  régénération, parce que la langue est figée à la génération. C'est un
  arbitrage délibéré — et il vaut mieux le défendre à l'écran que le passer
  sous silence.

**Bon appariement :** le quatrième cas de l'épisode 7 (un wizard bloqué en
français parce qu'une URL d'iframe n'avait pas d'anti-cache) est la
mauvaise traduction antérieure du même écran, pour une cause complètement
différente. Montrés ensemble, ils établissent que « mauvaise langue à
l'écran » est un symptôme, pas un diagnostic.

---

## Épisode 12 — Sauvegardes, rétention, et une revue de sécurité honnête

**Objectif :** deux sujets courts qui vont ensemble parce que tous deux
portent sur ce qu'on doit à la personne de l'autre côté du logiciel.

**À montrer à l'écran :**
- Une action destructive lancée en direct — régénérer HOME — avec la
  sauvegarde horodatée écrite d'abord, puis restaurée.
- Les règles de rétention : ce qui est gardé, combien de temps, et pourquoi
  la réponse est une politique et non un accident.
- `Security.md` ouvert et lu à l'écran, y compris les passages qui disent ce
  qui n'est *pas* protégé aujourd'hui.

**Points à développer :**
- « Rien n'est jamais écrit à moitié » comme invariant du projet, et les
  trois endroits indépendants où il apparaît (l'applicateur d'assignation,
  les dashboards protégés du générateur, l'étape de sauvegarde).
- Pourquoi publier une section « limites » honnête est une fonctionnalité :
  c'est la différence entre un projet qui a un modèle de menace et un projet
  qui a une ambiance. C'est l'épisode qui vieillira le mieux.
- Une conclusion naturelle pour la série entière, si vous en voulez une.

---

## Plan d'action — quoi filmer ensuite

Le statut porte sur la **filmabilité**, pas sur le fait que la
fonctionnalité marche : une ligne n'est « prête » que si la documentation et
une démo qui survit à une prise existent toutes les deux aujourd'hui.

| # | Épisode | Doc source | Prêt à filmer ? | Prochaine étape concrète |
|---|---|---|---|---|
| 8 | Automatiser une configuration OAuth | `Google_Calendar.md` ✔ | **Prêt** — écran livré, doc complète dans les deux langues | Préparer un projet Google Cloud vierge pour que la page de consentement soit filmable sans coupure |
| 11 | Bilingue par construction | `Google_Calendar.md` + `locales/` ✔ | **Prêt** — et l'avant/après existe dans l'historique git | Capturer les deux captures d'écran (EN/FR) et le commit d'avant correctif avant que le matériau ne vieillisse |
| 1 | Vision & architecture | `Vision.md` ✔ | Prêt | Refaire le diagramme d'architecture à la résolution d'enregistrement |
| 3 | Le générateur de dashboards | `Dashboard_Generator.md` ✔ | Prêt | Choisir l'unique modification de modèle à démontrer (ajouter un appareil se lit le mieux) |
| 10 | L'éditeur de design system | `Design_System_Editor.md` ✔ | Prêt | Décider si le piège `color-mix()` est un moment de cet épisode ou un short à part |
| 9 | Un chatbot dans le dashboard | `Chatbot_Integration.md` ✔ | Prêt, avec une réserve | Confirmer quelles clés de fournisseur peuvent être à l'écran ; flouter ou utiliser une clé jetable |
| 2 | CORE — le dashboard système | `Core_Dashboard.md` ✔ | Bloqué sur un correctif | Le 404 K3s `/local/osvision_v2/…` est le correctif en direct — vérifier qu'il se reproduit encore avant de filmer |
| 5 | Le wizard d'assignation d'appareils | `Deployment.md` ✔ | Prêt | La doc source a été renommée ; la relire de bout en bout avant d'écrire le script |
| 4 | Câbler une pièce entière | `Integration_Case_Study.md` ✔ | Partiellement bloqué | Deux arbitrages encore ouverts (`_energie` vs `_energie_jour`, `technical.png` manquant) — trancher, ou les filmer comme questions ouvertes |
| 6 | Le pipeline CI/CD | `CI_CD.md` ✔ | Prêt | Choisir lequel de G1–G5 est corrigé à l'écran (G1 est le plus visuel) |
| 12 | Sauvegardes + sécurité | `Backup_Retention.md` + `Security.md` ✔ | Prêt | Vérifier que `Security.md` correspond encore à la réalité le jour du tournage — c'est la doc qui se périme le plus silencieusement |
| 7 | Sessions de débogage | `Troubleshooting.md` ✔ | Prêt, à filmer en dernier | Ajouter le mélange FR/EN comme cinquième cas une fois l'épisode 11 sorti |

Deux règles permanentes pour ce plan :

1. **Une doc s'écrit avant son épisode, jamais après.** Chaque épisode
   ci-dessus a sa doc source dans `docs/`, dans les deux langues — c'est ce
   qui rend l'étape d'écriture du script courte.
2. **Quand un écran change, le statut de son épisode repart à zéro.**
   L'écran CALENDRIER a été livré puis retravaillé pour la langue en quelques
   jours ; tout ce qui aurait été filmé entre les deux serait déjà faux.

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
  d'abord. L'épisode 10 couvre désormais une partie de ce terrain, vu depuis
  l'éditeur.
- **8 → 11** est le meilleur nouveau binôme : le même écran, d'abord comme
  fonctionnalité puis comme problème de langue. Les filmer dans cet ordre et
  dans la même session — l'avant/après de l'épisode 11 n'existe que tant que
  la version d'avant correctif est encore récente dans l'historique.
- **9, 10, 12** sont autonomes comme 2, 4, 6 et 7, et peuvent se glisser
  n'importe où quand une semaine a besoin d'un épisode.
- La console ADMIN a maintenant assez d'écrans (ROOMS & FLOORS, ASSIGN,
  ENERGY, CALENDRIER, THEME, GÉNÉRATION) pour qu'un court « tour de la
  console » serve de bande-annonce ou d'intro de chaîne, monté à partir de
  rushes que les autres épisodes produisent déjà.
