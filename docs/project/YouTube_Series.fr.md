# Visio Sapiens — Plan de la série YouTube

**Français** · [English](YouTube_Series.md)

Ce document fait correspondre la documentation du projet à une séquence de
vidéos. Chaque épisode a une doc source, une question centrale à laquelle il
répond, et une démo suggérée à l'écran.

La série est organisée en **quatre blocs thématiques** plus un pilote. Un bloc
se regarde dans l'ordre et se tient debout tout seul : quelqu'un venu pour les
sauvegardes n'a pas à regarder neuf épisodes d'interface d'abord. À l'intérieur
d'un bloc, l'ordre compte ; entre blocs, non.

| Bloc | Sujet | Épisodes |
|---|---|---|
| — | Pilote | 1 |
| **A** | Environnement & CI/CD | 5 |
| **B** | Sauvegarde | 4 |
| **C** | Coffre-fort | 4 |
| **D** | Interface domotique | 10 |

Les docs sources citées existent dans `docs/` dans les deux langues
(`X.md` / `X.fr.md`), sauf mention *à écrire*.

> **Révision du 14 septembre 2026.** Ce plan a été relu contre le dépôt deux
> jours après son découpage. Le pilote a été réécrit (sa narration et ses
> sous-titres régénérés), un épisode D10 s'ajoute, et plusieurs sections
> décrivaient un état qui n'est plus vrai. Le détail est dans
> [Ce qui a changé depuis le 12 septembre](#ce-qui-a-changé-depuis-le-12-septembre) ;
> les sections concernées sont corrigées en place.

---

## Bloc A — Environnement & CI/CD

Le socle : la machine, le cluster, le pipeline, et ce qui casse quand l'un des
trois ment. Ce bloc répond à « où tourne ce projet, et comment le code y
arrive-t-il ».

| # | Titre | Doc source | Question centrale |
|---|---|---|---|
| A1 | L'environnement : où tourne réellement tout ça | `Vision.md`, `mosquitto-k3s.md` | Pourquoi un cluster k3s pour une maison ? |
| A2 | Le pipeline CI/CD | `CI_CD.md` | Comment un seul commit atteint deux cibles très différentes ? |
| A3 | Sessions de débogage | `Troubleshooting.md` | À quoi ressemble la traque d'un bug qui « ne devrait pas être possible » ? |
| A4 | HTTPS, et le piège du proxy | `Https.md` | Comment chiffrer sans s'enfermer dehors ? |
| A5 | L'écran UPDATES | `Updates.md` | Comment un écran dit-il ce qu'il ne sait pas ? |

---

## Bloc B — Sauvegarde

Quatre épisodes courts là où il n'y avait qu'une demi-vidéo. Le sujet n'est pas
« comment copier un fichier » mais **ce qu'on doit à quelqu'un avant d'écraser
son travail** — et le bloc va jusqu'à la seule preuve qui compte, la
restauration.

| # | Titre | Doc source | Question centrale |
|---|---|---|---|
| B1 | Rien n'est jamais écrit à moitié | `Backup_Retention.md`, `Deployment.md` | Comment garantir l'atomicité sans transactions ? |
| B2 | Rotation et rétention | `Backup_Retention.md` | Que garde-t-on, combien de temps, et qui l'a décidé ? |
| B3 | Restaurer : l'épreuve que personne ne fait | `Backup_Retention.md` | Une sauvegarde jamais restaurée existe-t-elle ? |
| B4 | Ce que la sauvegarde ne couvre pas | `Security.md`, `Vision.md` | Où s'arrête « sauvegardé », où commence « reproductible » ? |

> **Réserve honnête sur ce bloc.** `Backup_Retention.md` fait 79 lignes
> aujourd'hui : c'est assez pour B2, pas pour B1, B3 et B4. Selon la règle du
> projet — *une doc s'écrit avant son épisode, jamais après* — ces trois-là
> demandent d'abord d'écrire leur source. B3 en particulier n'a encore **aucune
> procédure de restauration documentée**, et c'est le genre de manque qu'on
> découvre le mauvais jour.

---

## Bloc C — Coffre-fort

Le bloc entier est postérieur à la première version de ce plan : rien de tout
cela n'existait quand la série a été découpée. C'est le matériau le plus récent,
et le plus démontrable.

| # | Titre | Doc source | Question centrale |
|---|---|---|---|
| C1 | Pourquoi un coffre plutôt qu'un fichier | `Vault.md` | Qu'apporte un coffre qu'un `0600` n'apporte pas ? |
| C2 | L'écran COFFRE-FORT | `Vault.md` | À quoi ressemble une console de secrets défendable ? |
| C3 | Desceller d'un mot de passe, depuis un appareil enrôlé | `Unseal.md` | Comment supprimer le geste manuel sans supprimer sa sûreté ? |
| C4 | Une revue de sécurité honnête | `Security.md` | Que doit-on dire sur ce qui n'est pas protégé ? |

---

## Bloc D — Interface domotique

Le cœur historique du projet : l'interface elle-même, de la jauge au
générateur. Dix épisodes : les neuf premiers ont leur doc, D10 doit d'abord
écrire la sienne.

| # | Titre | Doc source | Question centrale |
|---|---|---|---|
| D1 | CORE — le dashboard système | `Core_Dashboard.md` | Comment une page statique transforme des métriques en jauges vivantes ? |
| D2 | Le générateur de dashboards | `Dashboard_Generator.md` | Pourquoi générer le YAML plutôt que l'éditer ? |
| D3 | Étude de cas : câbler une pièce entière | `Integration_Case_Study.md` | Que signifie « de bout en bout », concrètement ? |
| D4 | Étude de cas : le wizard d'assignation | `Deployment.md` | Comment transformer un scan brut en formulaire sûr ? |
| D5 | Automatiser une configuration OAuth | `Google_Calendar.md` | Jusqu'où automatiser — et où ça s'arrête ? |
| D6 | Un chatbot dans le dashboard | `Chatbot_Integration.md` | Quatre fournisseurs derrière une carte, sans backend ? |
| D7 | L'éditeur de charte graphique (TEMPLATE GRAPHIQUE) | `Design_System_Editor.md` | Comment rendre une charte modifiable sans laisser casser l'UI ? |
| D8 | Bilingue par construction | `Google_Calendar.md` + `locales/` + `_header.j2` | Que faut-il pour tenir **une** langue sur **un** écran ? |
| D9 | Le planificateur | `Scheduler.md`, `AI_Assistant.md` | Comment une interface ne ment-elle pas sur le futur ? |
| D10 | La tablette murale : concevoir pour 1194 × 834 | *à écrire* (`Tablet_Layout.md`) | Pourquoi un écran qui marche sur un bureau casse-t-il sur la tablette du salon ? |

---

## Correspondance avec l'ancienne numérotation

Les douze épisodes d'origine sont tous replacés ; aucun n'est perdu. L'ancien
épisode 12 est le seul à être **coupé en deux** — ses deux moitiés n'avaient en
commun que leur brièveté.

| Ancien | Devient | Remarque |
|---|---|---|
| 1 Vision & architecture | **Pilote** | script révisé le 14 septembre, narration et sous-titres régénérés |
| 2 CORE | **D1** | |
| 3 Générateur | **D2** | |
| 4 Câbler une pièce | **D3** | |
| 5 Wizard d'assignation | **D4** | |
| 6 Pipeline CI/CD | **A2** | |
| 7 Sessions de débogage | **A3** | |
| 8 OAuth | **D5** | |
| 9 Chatbot | **D6** | |
| 10 Design system | **D7** | |
| 11 Bilingue | **D8** | |
| 12 Sauvegardes + sécurité | **B2** *et* **C4** | coupé en deux |
| — | A1, A4, A5, B1, B3, B4, C1, C2, C3, D9, D10 | onze épisodes nouveaux |

---

## Pilote — Vision & architecture

Le seul épisode qui n'appartient à aucun bloc, parce qu'il les annonce tous.
Son script complet : `episode-01-vision-architecture.fr.md`, révisé le
14 septembre 2026. Sa narration (`episode-01-narration.fr.txt`) et ses
sous-titres (`episode-01.fr.srt`) sont **générés** depuis le script par
`scripts/build_episode_media.py` — les régénérer après toute retouche de voix
off plutôt que de les éditer à la main.

**Objectif :** donner aux spectateurs le modèle mental avant tout code. Ce
qu'est Visio Sapiens (une interface façon centre de contrôle posée sur Home
Assistant, pas un simple dashboard habillé), pourquoi le projet construit son
propre moteur de rendu au lieu d'assembler des cartes toutes faites, et comment
la série est organisée.

**À montrer à l'écran :**
- Les diagrammes de `Vision.md` : la vue d'ensemble (§2), la chaîne de
  génération (§4), la boucle en six temps de la console (§5). L'ancien
  diagramme « CORE / Room Engine / IA Layer / … » n'existe plus depuis la
  réécriture de `Vision.md` du 9 septembre.
- Une visite en direct de HOME **à 1194 × 834** (la tablette murale) : le rail
  de navigation, le bandeau (écran + heure, météo, agenda), la rangée d'état
  (système, énergie, alarme, thermostat, voyant de mises à jour), le radar, les
  appareils mesurés, la barre de l'assistant.
- `dashboards/model/design_system.yaml` à côté de l'écran TEMPLATE GRAPHIQUE :
  une taille de texte changée, tous les écrans qui suivent.
- La carte des quatre blocs, en motion design.

**Points à aborder :**
- La règle unique qui pilote toutes les autres décisions : « Home Assistant
  n'est plus qu'un moteur de données ; l'interface est entièrement pilotée
  par VSSP. »
- **Sur quoi le moteur repose, dit exactement :** trois fondations
  communautaires (`button-card`, `card-mod`, `layout-card`), quelques cartes
  spécialisées (graphiques, météo, agenda, historique), et les gabarits VSSP
  au-dessus. L'ancienne formule — « aucune dépendance communautaire, plus de
  rustine card-mod » — était fausse pour quiconque ouvre le dépôt.
- La migration de nommage (OSVision → VSSP) : le ménage du 12 septembre, les
  trois bugs qu'il a fait remonter, et les deux traces qui restent
  (`OSVisionEngine`, le chemin K3s de CORE — le correctif en direct de D1).
- Le montage « ce qui a été livré » se construit depuis l'historique Git :
  `Vision.md` n'a plus de section changelog.

**À ne pas filmer :** tout secret en direct (mot de passe Livebox, valeurs du
coffre-fort, phrase de descellement, clés du chatbot) — gardés pour le bloc C,
D3 et D6. Les jetons longue durée ne font plus partie de la mise en service
d'une tablette depuis le 14 septembre.

---

## A1 — L'environnement : où tourne réellement tout ça

**Objectif :** poser le décor matériel et logiciel avant tout pipeline. Un
spectateur qui ne sait pas où vit Home Assistant ne peut pas comprendre
pourquoi le déploiement a deux cibles.

**À montrer à l'écran :**
- L'hôte `k3s-master` : `kubectl get nodes`, `kubectl get pods -A`, et le pod
  Home Assistant parmi eux.
- Les deux mondes côte à côte : le **staging** dans k3s (un pod, un PVC) et la
  **production** sur HAOS (une box, SSH sur 22222). Ce ne sont pas deux
  environnements du même produit : ce sont deux produits différents qui
  reçoivent le même code.
- GitLab auto-hébergé sur le même hôte, et son runner dans le cluster — la
  boucle complète tient sur une machine.
- Le conteneur Vault à côté, pour annoncer le bloc C sans l'ouvrir.

**Points à aborder :**
- Pourquoi k3s plutôt que Docker Compose : ce n'est pas « Kubernetes parce que
  c'est moderne », c'est le runner, les PVC et le redémarrage automatique.
- Le coût honnête : un cluster qui ne finit pas son démarrage bloque tout, et
  ça arrive — l'épisode A3 en fait la démonstration.
- Le piège des unités rivales : `k3s.service` et `k3s-agent.service` se
  disputent `127.0.0.1:6444`, et le symptôme est un hôte qui démarre sans
  jamais finir. Un cas d'école sur « le service est actif » ≠ « le service
  fonctionne ».

**Source :** `Vision.md`, `mosquitto-k3s.md`, `Updates.md` (section k3s).

---

## A2 — Le pipeline CI/CD

**Objectif :** un seul commit, deux cibles de déploiement très différentes —
le pipeline double-cible comme sujet à part entière, indépendant de toute
fonctionnalité particulière.

**À montrer à l'écran :**
- Le diagramme du pipeline : MR/master → build → `deploy:staging` (k3s,
  `kubectl cp`) vs. tag → `deploy:production` (HAOS, SSH) avec une porte
  manuelle.
- Un run de pipeline GitLab en direct, étape par étape.
- Un des trous de `CI_CD.md` encore ouverts, corrigé en direct. G1 (l'écart
  d'URL CSS/JS, le plus visuel) et G4 (l'ancien nom) sont **désormais
  fermés**. G2, G3 et G5 restent marqués ouverts — mais le pipeline déploie
  aujourd'hui l'ADMIN et régénère les dashboards sur le pod, donc G2 et G3
  sont à re-vérifier contre le pipeline actuel avant d'en faire la démo.

**Points à aborder :**
- La règle `workflow:` comme « premier réflexe de diagnostic » — un push sur
  une branche de fonctionnalité sans MR ouverte ne lance **rien**, le genre
  de chose qui fait perdre une heure si on ne sait pas le vérifier en
  premier.
- Pourquoi le fait que `configuration.yaml` nécessite un redémarrage complet
  de HA (pas un rechargement à chaud) était la cause racine de toute une
  classe de bugs « le staging semble inchangé » — lien direct avec
  l'épisode A3.
- Les secrets ne touchent jamais une ligne de commande ni un log : arguments
  shell positionnels en staging, stdin en production. Mérite une explication
  complète, c'est un savoir réutilisable bien au-delà de ce projet.

**Découpage optionnel :** si l'épisode A2 est trop long, le scinder en A2a
(mécanique du pipeline) et A2b (les trous G1–G5 comme épisode « problèmes
connus ») — la doc source se sépare déjà proprement sur cette ligne.

---

## A3 — Sessions de débogage

**Objectif :** l'épisode « enquête policière ». De vrais bugs, de vrais
symptômes, de vraies commandes lancées pour cerner la cause — le format qui
tend à le mieux performer parce que la résolution est gagnée à l'écran plutôt
que supposée.

**À montrer à l'écran — une réserve de huit mini-cas indépendants. En retenir
quatre par épisode, ou scinder en A3a / A3b :**
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
4. **Bonus, tiré de l'historique du projet :** le wizard ROOMS & FLOORS
   restant en français malgré un sélecteur de langue sur `en` — retracé
   jusqu'à un jeton de cache-busting `?v=` manquant sur une seule URL
   d'iframe, le seul actif de tout le pipeline non couvert par l'étape `sed`
   existante de cache-busting. Un bon cas de clôture car il montre que même
   un pipeline mature peut avoir exactement un coin non couvert, et que
   « c'est probablement mis en cache » vaut la peine d'être vérifié avant de
   supposer qu'un déploiement a échoué.
5. **Le cluster qui meurt à chaque démarrage** *(11 septembre)* —
   `k3s.service` et `k3s-agent.service` se disputaient `127.0.0.1:6444` ;
   l'hôte démarrait sans jamais finir. « Le service est actif » ≠ « le service
   fonctionne ». Se tourne en binôme avec A1.
6. **`set -e` : Illegal option** *(12 septembre)* — un script shell écrit
   depuis une copie Windows, donc en CRLF : `dash` lit `-e` suivi d'un retour
   chariot. Le correctif est une ligne de `.gitattributes`, pas le script.
7. **Coller le jeton faisait planter CORE** *(12 septembre)* — sans jeton,
   `init()` remplaçait toute la page par le formulaire ; `saveToken()`
   rappelait ensuite `init()` sur des éléments qui n'existaient plus. Le bug
   dormait tant que tout le monde avait déjà un jeton, et le renommage de la
   clé l'a réveillé. *(Depuis le 14 septembre, CORE ne demande plus de jeton
   du tout — le cas reste bon, le formulaire n'est plus qu'un repli.)*
8. **Des icônes absentes sur un seul appareil** *(14 septembre)* — sur l'iPad,
   seule l'icône d'APPAREILS ÉNERGIE s'affichait dans le menu ADMIN.
   Hypothèse fausse : le manque de place. Ce qui a tranché : Chromium à la
   même taille montrait les neuf icônes, et le serveur servait les neuf.
   L'icône visible était la seule déjà utilisée par le rail de navigation,
   donc déjà en cache ; les autres échouaient au chargement depuis un frontend
   périmé. Correctif : réinitialiser le cache du frontend. « Même taille
   d'écran » ≠ « même navigateur ».

**Points à aborder :**
- Chaque cas suit la même forme : symptôme → première hypothèse fausse → la
  commande qui cerne vraiment la cause → cause racine → correctif → le
  garde-fou ajouté ensuite pour empêcher toute récidive silencieuse. Nommer
  cette forme explicitement rend le format reproductible pour de futures
  vidéos sur de nouveaux bugs.
- Le motif « pipeline vert, résultat inchangé » mérite d'être nommé comme un
  concept à part entière — il revient dans les cas 1, 2 et 4 sous des formes
  différentes. Le cas 8 en est le cousin : **un seul client en tort**, alors
  que tout ce qui est vérifiable depuis le poste est juste.

---

## A4 — HTTPS, et le piège du proxy

**Objectif :** ajouter du chiffrement à une interface qui envoyait les mots de
passe en clair, sans casser la seule porte d'entrée qui reste quand on se
trompe.

**À montrer à l'écran :**
- Le mot de passe qui traverse le réseau en clair sur 8123 — capturé, montré,
  puis corrigé. C'est l'argument, et il se voit.
- L'ingress Traefik appliqué, le certificat servi, le cadenas qui apparaît.
- **Le piège, en direct :** appliquer l'ingress *sans* le bloc `http:` et
  obtenir un site qui ne répond plus que des 400. Puis la ligne de log qui
  nomme l'adresse exacte, et le correctif.

**Points à aborder :**
- Additif, jamais un remplacement : 8123 reste ouvert, parce que c'est la voie
  de retour si `trusted_proxies` est faux. Remplacer au lieu d'ajouter, c'est
  s'enfermer dehors avec la clé à l'intérieur.
- `trusted_proxies` est une liste de machines autorisées à **affirmer qui est
  le client**. Y mettre `0.0.0.0/0` rend le bannissement d'IP contournable
  avec un en-tête forgé.
- Le contenu mixte : une page en HTTPS ne peut plus appeler une adresse en
  `http://`. Vérifié sur tout le dépôt, et à re-vérifier pour chaque page
  ajoutée ensuite.

**Source :** `Https.md`.

---

## A5 — L'écran UPDATES : l'infrastructure se met à jour depuis l'interface

**Objectif :** montrer un écran qui sait ce qu'il ne sait pas. Chaque ligne dit
ce que son bouton installerait, ou explique pourquoi elle ne peut pas le dire.

**À montrer à l'écran :**
- L'écran UPDATES avec ses huit lignes : hôte, GitLab, k3s, conteneurs,
  charges de travail, redémarrage requis…
- **Un coffre scellé, et l'écran qui ne se vide pas** : les lignes passent en
  gris avec « mesuré le … » au lieu de disparaître. C'est le cœur de
  l'épisode.
- Une ligne rouge « à jour, mais le service ne tourne pas » — la différence
  entre lire un numéro de version sur un binaire et vérifier qu'un service
  répond.

**Points à aborder :**
- `probed` / `stale` / `measured` / `health` : quatre champs pour quatre
  questions différentes, alors qu'un seul booléen semblait suffire.
- Pourquoi une ligne, et une seule, refuse d'être reportée : après un
  redémarrage, « redémarrage requis » est faux par construction — et c'est
  précisément l'instant où le coffre se rescelle, donc où la vérification est
  impossible. La bonne réponse est de ne rien afficher plutôt qu'afficher hier.
- Un installeur qui dit « lancé, pas terminé » plutôt que « terminé » quand il
  ne peut pas le savoir.

**Source :** `Updates.md`.

---

## B1 — Rien n'est jamais écrit à moitié

**Objectif :** ouvrir le bloc SAUVEGARDE par l'invariant qui le rend
nécessaire, avant toute question de rotation ou de rétention.

**À montrer à l'écran :**
- Une régénération de HOME lancée en direct : la sauvegarde horodatée est
  écrite **avant** que le premier octet du nouveau fichier n'existe.
- Les trois endroits indépendants où le même invariant apparaît :
  l'applicateur d'assignation, les dashboards protégés du générateur, l'étape
  de sauvegarde elle-même.
- Un échec provoqué en plein milieu — couper le générateur pendant qu'il écrit
  — et le fichier d'origine toujours intact.

**Points à aborder :**
- L'atomicité dans un système qui n'a pas de transactions : valider tout le
  payload avant de toucher au disque, écrire à côté puis renommer, ne jamais
  faire confiance à « ça ne devrait pas échouer ici ».
- Pourquoi « relancer un scan ne réinitialise pas le travail précédent » est
  une garantie qui paraît anodine quand elle tient et catastrophique quand
  elle lâche.

**Source :** `Backup_Retention.md`, `Deployment.md`, `Dashboard_Generator.md`.

---

## B2 — Rotation et rétention : ce qu'on garde, et combien de temps

**Objectif :** transformer « je fais des sauvegardes » en une politique qu'on
peut énoncer, vérifier et défendre.

**À montrer à l'écran :**
- Le répertoire de sauvegardes après plusieurs semaines de travail réel :
  combien de fichiers, quelle taille, quelle ancienneté.
- Le mode « montre ce que tu supprimerais » lancé avant le vrai élagage. Un
  outil destructif qui sait répéter avant de jouer.
- La règle de rotation appliquée en direct, et le fichier qui disparaît.

**Points à aborder :**
- Une politique de rétention est un arbitrage entre le disque et le regret, et
  il vaut mieux l'écrire que le laisser au hasard des `rm` manuels.
- Ce que la rotation **ne doit jamais** emporter, et comment on le garantit.

**Source :** `Backup_Retention.md`.

---

## B3 — Restaurer : l'épreuve que personne ne fait

**Objectif :** l'épisode qui donne sa valeur aux deux précédents. Une
sauvegarde jamais restaurée est une hypothèse, pas une sauvegarde.

**À montrer à l'écran :**
- Casser un dashboard pour de bon, à l'écran, sans filet préparé.
- La restauration complète, chronométrée : combien de temps s'écoule entre
  « c'est cassé » et « c'est revenu ».
- Le contrôle d'après-restauration : l'écran est-il vraiment celui d'avant, ou
  seulement quelque chose qui lui ressemble ?

**Points à aborder :**
- Pourquoi une restauration réussie ne prouve rien si elle n'a pas été faite
  depuis l'état réel de panne.
- Ce qu'il faut noter le jour où ça arrive pour de vrai : l'ordre des gestes,
  ce qui doit redémarrer, ce qui ne se recharge pas à chaud.

**Source :** `Backup_Retention.md`, `Troubleshooting.md`.

---

## B4 — Ce que la sauvegarde ne couvre pas

**Objectif :** le court épisode honnête. Nommer les angles morts vaut mieux que
les découvrir.

**À montrer à l'écran :**
- Le registre Home Assistant : les pièces et les appareils vivent **dans** HA,
  pas dans le dépôt — `house.yaml` est vide par conception.
- Les secrets : rien de ce qui est chiffré n'est sauvegardé par ces scripts, et
  c'est le sujet du bloc C.
- L'historique long : la base d'états de Home Assistant, ce qu'elle contient en
  clair, et ce que ça implique.

**Points à aborder :**
- La différence entre « sauvegardé » et « reproductible » : le dépôt
  reconstruit l'interface, il ne reconstruit pas l'installation.
- Publier ses angles morts est une fonctionnalité, pas un aveu.

**Source :** `Backup_Retention.md`, `Security.md`, `Vision.md`.

---

## C1 — Pourquoi un coffre plutôt qu'un fichier

**Objectif :** ouvrir le bloc COFFRE-FORT par l'argument, pas par
l'installation. Qu'apporte un coffre qu'un fichier en `0600` n'apporte pas ?

**À montrer à l'écran :**
- Le fichier de secrets d'avant, ouvert à l'écran, et la question posée
  franchement : qui peut le lire, et qu'est-ce qui l'en empêche ?
- Vault en marche, ses chemins KV, une écriture puis une lecture.
- Les deux installations — staging et production — et pourquoi elles diffèrent.

**Points à aborder :**
- Ce qu'un coffre **n'est pas** : il ne protège pas d'un administrateur de la
  machine, et le dire tôt évite une fausse sécurité.
- Le scellement comme choix de conception : le coffre se rescelle à chaque
  redémarrage, exprès. C'est une contrainte, et le bloc entier tourne autour.

**Source :** `Vault.md`.

---

## C2 — L'écran COFFRE-FORT

**Objectif :** une console de secrets dans le dashboard, et les décisions qui
la rendent défendable.

**À montrer à l'écran :**
- L'écran ADMIN → COFFRE-FORT : connexion, les trois branches, révéler un
  secret, le masquer, l'éditer.
- Le jeton en `sessionStorage` et jamais en `localStorage` — et la
  démonstration de la différence : fermer l'onglet met fin à la session.
- L'écran quand le coffre est scellé : ce qu'il peut encore dire, et ce qu'il
  ne peut plus.

**Points à aborder :**
- Une page qui parle à Vault depuis le navigateur, c'est du CORS, et une
  adresse écrite deux fois est une adresse qui finira par se contredire — d'où
  une URL dérivée du nom d'hôte de la page.
- Ce qu'on n'affiche jamais, même à l'utilisateur légitime, et pourquoi.

**Source :** `Vault.md`.

---

## C3 — Desceller d'un mot de passe, depuis un appareil enrôlé

**Objectif :** l'épisode le plus dense du bloc. Supprimer le « `docker exec` et
trois clés à la main » sans supprimer ce qui le rendait sûr.

**À montrer à l'écran :**
- Le coffre scellé volontairement, l'écran COFFRE-FORT qui affiche le champ et
  le bouton **DESCELLER**, et le navigateur qui demande **quel certificat
  présenter**.
- Le même clic depuis un appareil non enrôlé : refusé pendant la poignée de
  main, avant même que la phrase secrète ne soit lue.
- Le journal du service : horodatage, nom du certificat, IP, MAC vue, résultat
  — et **jamais** la phrase ni une part.

**Points à aborder :**
- Ce qui authentifie réellement : le certificat client et la phrase secrète.
  L'adresse MAC, elle, ne compte pas — elle se change en une commande et ne
  survit pas à un routeur. Le dire est plus utile que de faire semblant.
- Pourquoi le service ne peut pas vivre dans Home Assistant : une phrase
  secrète ne doit pas devenir une entité.
- Le joker CORS et le certificat client ne peuvent pas coexister : un
  navigateur ne présente un certificat que si la page demande
  `credentials: "include"`, et refuse alors `Access-Control-Allow-Origin: *`.
  Une contrainte de spécification qui a dicté la conception du service.
- `scrypt` avec ses paramètres **stockés dans le fichier** plutôt que codés en
  dur, pour pouvoir les durcir plus tard sans orpheliner les données.
- Cinq échecs, quinze minutes de porte fermée, compteur persisté.

**Source :** `Unseal.md`.

---

## C4 — Une revue de sécurité honnête

**Objectif :** clore le bloc en lisant à l'écran ce qui n'est **pas** protégé.

**À montrer à l'écran :**
- `Security.md` ouvert et lu, y compris les passages inconfortables.
- Les questions de conception encore ouvertes, telles quelles.
- Ce qui a changé depuis la première rédaction du document — le coffre et le
  descellement sont précisément des réponses à deux de ces points.
- **Le jeton longue durée retiré des tablettes** *(14 septembre)* : les pages
  de la console (PIÈCES & ÉTAGES, APPAREILS DÉTECTÉS, CORE) empruntent la
  session Home Assistant du dashboard qui les contient, au lieu d'un jeton
  collé et gardé en clair dans `localStorage`. `Security.md` ne parle pas du
  tout de ce jeton — c'est un manque à combler avant le tournage.

**Points à aborder :**
- La différence entre un projet qui a un modèle de menace et un projet qui a
  une ambiance.
- Pourquoi c'est l'épisode qui vieillira le mieux, et pourquoi il faut
  re-vérifier le document le jour du tournage : c'est la doc qui se périme le
  plus silencieusement.

**Source :** `Security.md`.

---

## D1 — CORE, le dashboard système

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
  K3s reprendre vie. *Toujours présent dans `core.html` au 14 septembre.*
- **L'authentification a changé** *(14 septembre)* : `core.html` ne demande
  plus de jeton, il emprunte la session du dashboard CORE (`hass.auth`, jeton
  court rafraîchi à la demande), et son URL porte désormais `?v=` comme les
  autres iframes. Dans l'onglet Réseau, l'en-tête `Authorization` porte ce
  jeton court. `Core_Dashboard.md` décrit encore l'ancien jeton sous l'ancienne
  clé (`osv_ha_token`) : à réécrire avant le tournage.
- `esc()` et l'angle XSS — un aparté de 90 secondes sur pourquoi on échappe
  les données de son **propre** backend, pas seulement les entrées
  « non fiables ».

**Bon pairing :** le correctif en direct de cet épisode est une version
courte de ce que fait l'épisode A3 en détail — envisager un renvoi croisé.

---

## D2 — Le générateur de dashboards

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
- Le pont wizard → modèle, que `Dashboard_Generator.md` annonce encore sous le
  nom `vssp_model_sync.py`, **existe désormais sous une autre forme** : les
  applicateurs de la console (`vssp_rooms_apply.py`, `vssp_assign_apply.py`)
  écrivent le modèle puis régénèrent. Accroche naturelle vers D4 — et section
  de la doc à mettre à jour avant le tournage.

---

## D3 — Étude de cas : câbler une pièce entière

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

## D4 — Étude de cas : le wizard d'assignation d'appareils

**Objectif :** une deuxième étude de cas, en contraste — un outil interactif
plutôt qu'un dashboard statique, et un bon moment pour montrer la forme
récurrente « découvrir → décider → appliquer » qu'on retrouve dans tout le
projet (c'est la même forme que l'écran PIÈCES & ÉTAGES).

**À montrer à l'écran :**
- Le pipeline de `Deployment.md` :
  `DISCOVERY SCAN → report.json → prepare → assign_data.json → le formulaire
  → webhook → apply → house.yaml → le générateur → dashboards/views/`.
- Un cycle scan → assignation → application en direct dans le navigateur.
- Le tableau des fichiers vérifiés par MD5 comme moment « comment on s'est
  assuré que les bons fichiers sont partis » — s'accorde bien avec le
  post-mortem du cache de l'épisode A3.

**Points à aborder :**
- « Rien n'est jamais écrit à moitié » : l'applicateur valide tout le
  payload avant de toucher `house.yaml`, et sauvegarde d'abord — bonne
  discussion sur l'atomicité dans un système sans vraies transactions.
- Relancer un scan ne réinitialise pas le travail précédent — une garantie
  subtile mais importante à souligner explicitement, car c'est exactement le
  genre de chose qui paraît anodine quand ça marche et catastrophique quand
  ça ne marche pas.

---

## D5 — Automatiser une configuration OAuth

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
  exactement comme le mot de passe Livebox et les clés du chatbot.

**Bon appariement :** l'épisode D8 reprend ce même écran comme exemple
travaillé — les filmer coup sur coup, tant que le matériau est frais.

---

## D6 — Un chatbot dans le dashboard

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

## D7 — L'éditeur de charte graphique (TEMPLATE GRAPHIQUE)

**Objectif :** une charte graphique qui tenait dans un fichier de thème
édité à la main, devenue un modèle plus un générateur plus un écran
d'édition — la même forme modèle→template→généré que l'épisode D2, appliquée
à l'apparence au lieu de la structure.

> **Statut remis à zéro le 13 septembre** (règle 2 du plan d'action) : l'écran
> a reçu la police, les tailles de texte par usage et le logo remplaçable.
> Rien de ce qui aurait été filmé avant n'est encore juste.

**À montrer à l'écran :**
- `model/design_system.yaml` à côté du thème généré, une couleur changée en
  direct, régénération, et toute l'interface qui suit.
- **Les tailles de texte par usage** — horloge, titres, valeurs, texte,
  libellés, chacune de 50 à 200 % : un curseur, et toutes les valeurs de tous
  les écrans suivent. C'est aussi la démo du pilote (section 6).
- **La police qui rejoint la charte**, et le piège de sa feuille : `/local` est
  mis en cache un mois par le navigateur, donc une police changée n'arrive pas
  tant que l'URL de la feuille ne porte pas de version.
- **Le logo carré remplaçable** du rail de navigation (par défaut, envoyé, ou
  aucun), dans un rail qui ne fait que la largeur de sa plus longue entrée.
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
- **Un modèle plus ancien que le code** : le modèle vivant du pod ne connaît
  pas les tokens ajoutés après sa création. Plutôt que de retomber sur rien,
  le générateur complète chaque token manquant depuis la référence d'usine
  (`design_system.default.yaml`). Une règle transposable : une donnée écrite
  par l'utilisateur vieillit plus lentement que le code qui la lit.

**Bon appariement :** D10 — la même semaine de travail, vue depuis la
tablette : le rail ajusté à ses entrées et le bandeau ramené à sa hauteur
sont nés là.

---

## D8 — Bilingue par construction

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

**Second cas — les cartes tierces qui parlent la langue du navigateur**
*(12 septembre)* : avec des dashboards générés en anglais, l'agenda et la
météo du bandeau restaient en français. Ces cartes lisent `hass.language` —
la langue du navigateur (fr-FR) — et non la langue générée. Correctif :
l'option `language:` quand la carte en a une (calendar-card-pro), sinon
card-mod qui masque le texte et le réécrit (simple-weather-card) — la rustine
assumée dans la section 4 du pilote. Un basculement fr→en qui « ne marche
pas » peut vouloir dire « une seule carte tierce est restée en français ».

**Bon appariement :** le quatrième cas de l'épisode A3 (un wizard bloqué en
français parce qu'une URL d'iframe n'avait pas d'anti-cache) est la
mauvaise traduction antérieure du même écran, pour une cause complètement
différente. Montrés ensemble — avec le second cas ci-dessus — ils établissent
que « mauvaise langue à l'écran » est un symptôme, pas un diagnostic.

---

## D9 — Le planificateur

**Objectif :** compléter le bloc interface par l'écran qui fait agir la maison
dans le temps plutôt que sur commande.

**À montrer à l'écran :**
- L'écran du planificateur, un créneau créé puis modifié, et l'effet réel sur
  un appareil.
- Le modèle derrière : ce qui est généré, ce qui est lu à l'exécution.

**Points à aborder :**
- Pourquoi la planification est un cas où l'interface ne peut pas mentir : une
  erreur ne se voit pas au moment du clic mais trois heures plus tard.
- L'assistant IA comme prolongement naturel du même écran.

**Source :** `Scheduler.md`, `AI_Assistant.md`.

---

## D10 — La tablette murale : concevoir pour 1194 × 834

**Objectif :** l'appareil qui compte n'est pas l'écran de bureau sur lequel on
développe, c'est l'iPad 11 pouces en paysage accroché au mur. Un épisode sur
tout ce qu'un écran de bureau ne montre pas — et sur la règle qui en est
sortie : **chaque test se fait à 1194 × 834**.

**À montrer à l'écran, quatre cas du 14 septembre :**
1. **Des noms d'appareils à 0 px de large.** Dans CONSOMMATION PAR APPAREIL,
   une ligne dispose de 272 px, et ses colonnes fixes (icône, pièce,
   puissance, énergie, flèche, espaces) en réclamaient 358. La colonne du nom
   tombait à zéro — pendant que la colonne pièce n'affichait qu'un tiret.
   Retirer la colonne ne suffisait pas (18 px) ; il a fallu ajuster chaque
   colonne à son contenu réel.
2. **Un bandeau de 246 px au lieu de 76.** Le rail de navigation couvre les
   deux lignes de la grille ; avec des lignes `auto auto` et un contenu court,
   la grille répartit la hauteur du rail sur les deux — l'en-tête gonfle. Neuf
   écrans sur dix passaient par chance, parce que leur contenu était plus haut
   que le rail. `auto 1fr` partout.
3. **Une tablette neuve = une connexion.** Les pages de la console (des
   iframes) demandaient un jeton longue durée à coller. Elles empruntent
   désormais la session de la tablette elle-même : rien à coller, rien de
   permanent stocké dans le navigateur.
4. **Ce que le poste de test ne voit pas.** Des icônes absentes sur l'iPad
   seulement : Chromium à la même taille les affichait toutes. La taille de
   l'écran se simule ; le moteur du navigateur, non (voir A3, cas 8).

**Points à aborder :**
- Mesurer plutôt que regarder : chaque cas a été tranché par une largeur ou
  une hauteur lue dans le DOM, pas par une capture.
- Un rail aussi large que sa plus longue entrée, un en-tête à la hauteur de
  son contenu : laisser le contenu dimensionner la mise en page plutôt que
  l'inverse.
- Pourquoi les tests se font dans un navigateur qui n'est pas celui de la
  tablette, et comment le dire honnêtement dans chaque compte rendu.

**Source :** *à écrire* — `docs/dashboards/Tablet_Layout.md`. Les quatre cas
sont documentés dans leurs commits du 14 septembre ; les écrire tant qu'ils
sont frais.

---

## Ce qui a changé depuis le 12 septembre

Le plan a été découpé le 12 septembre ; ce qui suit a bougé depuis, ou était
déjà faux ce jour-là.

| Date | Ce qui a changé | Épisodes touchés |
|---|---|---|
| 9 sept. | `Vision.md` réécrit : l'ancien diagramme « Room Engine / IA Layer » et la section changelog disparaissent | Pilote |
| 12 sept. | L'ancien nom retiré du code — sauf `OSVisionEngine` et le chemin K3s de CORE | Pilote, D1, A3 |
| 12 sept. | Agenda et météo du bandeau suivent la langue générée, plus celle du navigateur | D8 |
| 13 sept. | La police, les tailles de texte par usage et le logo remplaçable rejoignent le TEMPLATE GRAPHIQUE ; les tokens manquants sont complétés depuis la référence d'usine | D7 (statut remis à zéro), Pilote |
| 13-14 sept. | Le rail de navigation et le bandeau s'ajustent à leur contenu ; les panneaux ÉNERGIE s'alignent en hauteur ; la colonne pièce disparaît de CONSOMMATION PAR APPAREIL | D10, Pilote |
| 14 sept. | Les pages de la console empruntent la session de la tablette : plus de jeton longue durée | C4, D1, D10, Pilote |
| 14 sept. | L'en-tête d'APPAREILS ÉNERGIE ramené au standard (76 px) | D10 |
| — | Déjà faux le 12 : G1 et G4 fermés dans `CI_CD.md` ; le pont `vssp_model_sync.py` construit sous une autre forme ; `weather-forecast` utilisée nulle part ; « tout le reste est du moteur maison » contredit par 173 `button-card` et 95 blocs `card_mod` | A2, D2, Pilote |

Trois docs sources décrivent encore l'état d'avant et doivent être mises à
jour **avant** leur épisode (règle 1) : `Core_Dashboard.md` (l'ancien jeton,
D1), `Dashboard_Generator.md` (le pont, D2), `CI_CD.md` (le statut de G2/G3,
A2).

---

## Plan d'action — quoi filmer ensuite

Le statut porte sur la **filmabilité**, pas sur le fait que la fonctionnalité
marche : une ligne n'est « prête » que si la documentation et une démo qui
survit à une prise existent toutes les deux aujourd'hui.

| # | Épisode | Prêt à filmer ? | Prochaine étape concrète |
|---|---|---|---|
| — | Pilote | **Script révisé — voix et captures à refaire** | Recapturer HOME à 1194 × 834 ; ré-enregistrer la voix section par section ; relancer `scripts/build_episode_media.py` après toute retouche du script |
| C3 | Desceller depuis un appareil enrôlé | **Prêt, et le plus frais** | Sceller le coffre exprès pour la prise ; prévoir un second appareil non enrôlé pour filmer le refus |
| A5 | L'écran UPDATES | **Prêt** | Capturer l'écran gris « mesuré le … » pendant que le coffre est scellé — ça n'arrive que là |
| C2 | L'écran COFFRE-FORT | **Prêt** | Préparer des secrets de démonstration ; rien de réel à l'écran |
| D5 | Automatiser une configuration OAuth | **Prêt** | Un projet Google Cloud vierge, pour que le consentement soit filmable sans coupure |
| D8 | Bilingue par construction | **Prêt** | Capturer EN/FR côte à côte ; le second cas (cartes tierces du bandeau) n'existe plus que dans l'historique — rejouer le commit d'avant le 12 septembre |
| D2 | Le générateur de dashboards | Prêt, doc à retoucher | Choisir l'unique modification de modèle à démontrer ; mettre à jour la section « pont » de `Dashboard_Generator.md` |
| D7 | L'éditeur de charte graphique | **Écran changé — statut remis à zéro** | Refilmer avec la police, les tailles de texte et le logo ; décider si le piège `color-mix()` est un moment ou un short à part |
| D6 | Un chatbot dans le dashboard | Prêt, avec une réserve | Confirmer quelles clés peuvent être à l'écran ; flouter ou clé jetable |
| A4 | HTTPS et le piège du proxy | Prêt, non appliqué | L'ingress n'est pas encore posé : le faire une première fois **hors caméra**, puis rejouer |
| A2 | Le pipeline CI/CD | Prêt, démo à rechoisir | G1 est fermé : re-vérifier G2/G3/G5 contre le pipeline actuel, puis choisir celui qu'on corrige à l'écran |
| C1 | Pourquoi un coffre | Prêt | Retrouver le fichier de secrets d'avant dans l'historique git |
| D1 | CORE | Bloqué sur un correctif, doc à réécrire | Le 404 `/local/osvision_v2/…` se reproduit toujours (vérifié dans le code le 14 septembre) ; réécrire la partie authentification de `Core_Dashboard.md` |
| D4 | Le wizard d'assignation | Prêt | Relire la doc source de bout en bout avant d'écrire le script |
| D3 | Câbler une pièce entière | Partiellement bloqué | Deux arbitrages ouverts — trancher, ou les filmer comme questions ouvertes |
| B2 | Rotation et rétention | Prêt | Laisser le répertoire vieillir : un dossier de trois fichiers ne montre rien |
| C4 | Revue de sécurité honnête | Prêt, doc à compléter | Ajouter à `Security.md` le retrait du jeton longue durée des tablettes ; re-vérifier le document le jour du tournage |
| A3 | Sessions de débogage | Prêt, à filmer en dernier | Huit cas en réserve : en choisir quatre, ou scinder en A3a / A3b |
| D10 | La tablette murale | **Doc à écrire** | `Tablet_Layout.md` : quatre cas frais du 14 septembre, à écrire tant qu'ils le sont |
| A1 | L'environnement | **Doc à écrire** | Aucune doc ne décrit l'hôte lui-même ; l'écrire d'abord |
| D9 | Le planificateur | **Doc à relire** | `Scheduler.md` est antérieur aux derniers écrans |
| B1 | Rien n'est jamais écrit à moitié | **Doc à écrire** | L'invariant est appliqué en trois endroits mais documenté nulle part |
| B3 | Restaurer | **Doc à écrire — priorité** | Aucune procédure de restauration n'existe. C'est un manque, pas seulement un épisode manquant |
| B4 | Ce que la sauvegarde ne couvre pas | **Doc à écrire** | Dépend de B3 |

Trois règles permanentes pour ce plan :

1. **Une doc s'écrit avant son épisode, jamais après.** C'est ce qui rend
   l'étape d'écriture du script courte — et c'est la règle qui classe trois
   épisodes du bloc B, A1 et D10 en « doc à écrire » plutôt qu'en « prêt ».
2. **Quand un écran change, le statut de son épisode repart à zéro.** L'écran
   COFFRE-FORT a reçu son bouton DESCELLER après la rédaction de ce plan : tout
   ce qui aurait été filmé avant serait déjà faux. Même chose le 13 septembre
   pour le TEMPLATE GRAPHIQUE (D7), et le 14 pour HOME (le pilote).
3. **Un bloc se publie dans l'ordre, les blocs se publient dans n'importe
   lequel.** C'est ce qui permet de sortir C3 tant qu'il est frais sans
   attendre que le bloc B soit écrit.

---

## Notes de séquencement

- **Le bloc C est le plus prêt**, et c'est contre-intuitif : c'est le plus
  récent. C3 en particulier devrait être tourné vite — un épisode sur un
  mécanisme qu'on vient de construire se raconte mieux que six mois plus tard.
- **Le bloc B est le moins prêt**, et le savoir est utile : trois de ses quatre
  épisodes demandent d'abord une doc. B3 est le plus important des trois, parce
  qu'écrire sa doc revient à se doter d'une procédure de restauration qui
  n'existe pas encore.
- **A1 → A2 → A3** est le fil naturel « voici la machine, voici comment le code
  y arrive, voici ce qui casse ». Filmable comme un mini-arc.
- **D5 → D8** reste le meilleur binôme : le même écran, d'abord comme
  fonctionnalité puis comme problème de langue. Dans cette session et dans cet
  ordre — l'avant/après de D8 n'existe que tant que la version d'avant correctif
  est récente dans l'historique.
- **A3 gagne à être filmé en dernier** pour chaque bug — une fois le correctif
  déployé et confirmé — mais peut être **publié** plus tôt si un cas est déjà
  entièrement résolu.
- **C1 → C2 → C3 → C4** est le seul bloc qui se regarde vraiment comme une
  histoire : un problème, un outil, une automatisation, un bilan honnête.
- **Le pilote se publie en premier**, et c'est lui qui doit être juste avant
  tout le reste : il cite des épisodes de chaque bloc. Le refaire après D7 ou
  D10 obligerait à le refaire une troisième fois.
- **D7 → D10** : la même semaine de travail — la charte, puis la tablette qui
  l'affiche. À tourner dans cet ordre, pendant que les écrans sont stables.
- La console ADMIN a maintenant neuf écrans (PIÈCES & ÉTAGES, APPAREILS
  DÉTECTÉS, ASSIGNATION DES APPAREILS, APPAREILS ÉNERGIE, CALENDRIER GOOGLE,
  TEMPLATE GRAPHIQUE, DASHBOARDS, MISES À JOUR, COFFRE-FORT) — assez pour qu'un
  court « tour de la console » serve de bande-annonce, monté à partir de rushes
  que les autres épisodes produisent déjà. APPAREILS ÉNERGIE affiche encore
  « pas encore construit » : le montrer tel quel, ou le couper.
