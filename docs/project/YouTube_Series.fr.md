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
| **D** | Interface domotique | 9 |

Les docs sources citées existent dans `docs/` dans les deux langues
(`X.md` / `X.fr.md`).

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
générateur. Neuf épisodes, tous déjà documentés.

| # | Titre | Doc source | Question centrale |
|---|---|---|---|
| D1 | CORE — le dashboard système | `Core_Dashboard.md` | Comment une page statique transforme des métriques en jauges vivantes ? |
| D2 | Le générateur de dashboards | `Dashboard_Generator.md` | Pourquoi générer le YAML plutôt que l'éditer ? |
| D3 | Étude de cas : câbler une pièce entière | `Integration_Case_Study.md` | Que signifie « de bout en bout », concrètement ? |
| D4 | Étude de cas : le wizard d'assignation | `Deployment.md` | Comment transformer un scan brut en formulaire sûr ? |
| D5 | Automatiser une configuration OAuth | `Google_Calendar.md` | Jusqu'où automatiser — et où ça s'arrête ? |
| D6 | Un chatbot dans le dashboard | `Chatbot_Integration.md` | Quatre fournisseurs derrière une carte, sans backend ? |
| D7 | L'éditeur de design system | `Design_System_Editor.md` | Comment rendre une charte modifiable sans laisser casser l'UI ? |
| D8 | Bilingue par construction | `Google_Calendar.md` + `locales/` | Que faut-il pour tenir **une** langue sur **un** écran ? |
| D9 | Le planificateur | `Scheduler.md`, `AI_Assistant.md` | Comment une interface ne ment-elle pas sur le futur ? |

---

## Correspondance avec l'ancienne numérotation

Les douze épisodes d'origine sont tous replacés ; aucun n'est perdu. L'ancien
épisode 12 est le seul à être **coupé en deux** — ses deux moitiés n'avaient en
commun que leur brièveté.

| Ancien | Devient | Remarque |
|---|---|---|
| 1 Vision & architecture | **Pilote** | inchangé, déjà tourné |
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
| — | A1, A4, A5, B1, B3, B4, C1, C2, C3, D9 | dix épisodes nouveaux |

---

## Pilote — Vision & architecture

C'est le premier épisode tourné, et le seul qui n'appartient à aucun bloc
parce qu'il les annonce tous. Son script complet existe déjà :
`episode-01-vision-architecture.fr.md`, avec sa narration et ses sous-titres.

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
pour l'épisode D3/A2.

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
  K3s reprendre vie.
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
- Le pont encore ouvert (`vssp_model_sync.py`, wizard → modèle) comme
  accroche « dans un prochain épisode ».

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
projet (c'est la même forme que le wizard ROOMS & FLOORS de cette session).

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
  exactement comme `vssp_ha_token` et les clés du chatbot.

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

## D7 — L'éditeur de design system

**Objectif :** une charte graphique qui tenait dans un fichier de thème
édité à la main, devenue un modèle plus un générateur plus un écran
d'édition — la même forme modèle→template→généré que l'épisode D2, appliquée
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

**Bon appariement :** le quatrième cas de l'épisode A3 (un wizard bloqué en
français parce qu'une URL d'iframe n'avait pas d'anti-cache) est la
mauvaise traduction antérieure du même écran, pour une cause complètement
différente. Montrés ensemble, ils établissent que « mauvaise langue à
l'écran » est un symptôme, pas un diagnostic.

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

## Plan d'action — quoi filmer ensuite

Le statut porte sur la **filmabilité**, pas sur le fait que la fonctionnalité
marche : une ligne n'est « prête » que si la documentation et une démo qui
survit à une prise existent toutes les deux aujourd'hui.

| # | Épisode | Prêt à filmer ? | Prochaine étape concrète |
|---|---|---|---|
| C3 | Desceller depuis un appareil enrôlé | **Prêt, et le plus frais** | Sceller le coffre exprès pour la prise ; prévoir un second appareil non enrôlé pour filmer le refus |
| A5 | L'écran UPDATES | **Prêt** | Capturer l'écran gris « mesuré le … » pendant que le coffre est scellé — ça n'arrive que là |
| C2 | L'écran COFFRE-FORT | **Prêt** | Préparer des secrets de démonstration ; rien de réel à l'écran |
| D5 | Automatiser une configuration OAuth | **Prêt** | Un projet Google Cloud vierge, pour que le consentement soit filmable sans coupure |
| D8 | Bilingue par construction | **Prêt** | Capturer EN/FR côte à côte et le commit d'avant correctif avant qu'il ne vieillisse |
| D2 | Le générateur de dashboards | Prêt | Choisir l'unique modification de modèle à démontrer |
| D7 | L'éditeur de design system | Prêt | Décider si le piège `color-mix()` est un moment ou un short à part |
| D6 | Un chatbot dans le dashboard | Prêt, avec une réserve | Confirmer quelles clés peuvent être à l'écran ; flouter ou clé jetable |
| A4 | HTTPS et le piège du proxy | Prêt, non appliqué | L'ingress n'est pas encore posé : le faire une première fois **hors caméra**, puis rejouer |
| A2 | Le pipeline CI/CD | Prêt | Choisir lequel de G1–G5 est corrigé à l'écran (G1 est le plus visuel) |
| C1 | Pourquoi un coffre | Prêt | Retrouver le fichier de secrets d'avant dans l'historique git |
| D1 | CORE | Bloqué sur un correctif | Le 404 `/local/osvision_v2/…` est le correctif en direct — vérifier qu'il se reproduit |
| D4 | Le wizard d'assignation | Prêt | Relire la doc source de bout en bout avant d'écrire le script |
| D3 | Câbler une pièce entière | Partiellement bloqué | Deux arbitrages ouverts — trancher, ou les filmer comme questions ouvertes |
| B2 | Rotation et rétention | Prêt | Laisser le répertoire vieillir : un dossier de trois fichiers ne montre rien |
| C4 | Revue de sécurité honnête | Prêt | Re-vérifier `Security.md` le jour du tournage — c'est la doc qui se périme le plus silencieusement |
| A3 | Sessions de débogage | Prêt, à filmer en dernier | Ajouter le crash-loop k3s et le CRLF comme nouveaux cas |
| A1 | L'environnement | **Doc à écrire** | Aucune doc ne décrit l'hôte lui-même ; l'écrire d'abord |
| D9 | Le planificateur | **Doc à relire** | `Scheduler.md` est antérieur aux derniers écrans |
| B1 | Rien n'est jamais écrit à moitié | **Doc à écrire** | L'invariant est appliqué en trois endroits mais documenté nulle part |
| B3 | Restaurer | **Doc à écrire — priorité** | Aucune procédure de restauration n'existe. C'est un manque, pas seulement un épisode manquant |
| B4 | Ce que la sauvegarde ne couvre pas | **Doc à écrire** | Dépend de B3 |

Trois règles permanentes pour ce plan :

1. **Une doc s'écrit avant son épisode, jamais après.** C'est ce qui rend
   l'étape d'écriture du script courte — et c'est la règle qui classe quatre
   épisodes du bloc B en « doc à écrire » plutôt qu'en « prêt ».
2. **Quand un écran change, le statut de son épisode repart à zéro.** L'écran
   COFFRE-FORT a reçu son bouton DESCELLER après la rédaction de ce plan : tout
   ce qui aurait été filmé avant serait déjà faux.
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
- La console ADMIN a maintenant assez d'écrans (ROOMS & FLOORS, ASSIGN, ENERGY,
  CALENDRIER, THEME, GÉNÉRATION, COFFRE-FORT, UPDATES) pour qu'un court « tour
  de la console » serve de bande-annonce, monté à partir de rushes que les
  autres épisodes produisent déjà.
