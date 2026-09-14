# ÉPISODE PILOTE — Vision & Architecture
## "Visio Sapiens : pourquoi j'ai jeté les cartes Lovelace natives"

**Doc source :** `Vision.md`
**Question centrale de l'épisode :** Pourquoi remplacer les cartes natives de Lovelace par un moteur maison ?
**Ancrage visuel :** diagramme d'architecture + visite en direct du dashboard HOME
**Durée :** 20 min — le format de toute la série
**Révision :** 14 septembre 2026 — voir [Révision du 14 septembre](#révision-du-14-septembre-2026) en fin de document pour ce qui a changé et pourquoi.
**Format de tournage :** aucun plan visage. La chaîne repose sur **voix off + captures d'écran + plans mains** (clavier, souris, éventuellement un stylet sur tablette pour annoter le diagramme).

**Objectif :** donner aux spectateurs le modèle mental avant tout code. Ce qu'est Visio Sapiens — une interface façon centre de contrôle posée sur Home Assistant, **pas** un simple dashboard habillé — pourquoi le projet construit son propre moteur de rendu au lieu d'assembler des cartes toutes faites, à quoi ressemblent la console et la « sécurité par défaut » une fois démontrées, et comment la suite de la série est organisée.

**⚠️ À ne pas filmer :** tout secret en direct — mot de passe Livebox, valeurs du coffre-fort, phrase de descellement, clés des fournisseurs du chatbot. Leur gestion a ses épisodes : bloc C (coffre-fort), D3 (Livebox), D6 (chatbot). Une nouvelle tablette ne demande plus de jeton d'accès longue durée : la connexion Home Assistant suffit, il n'y a donc rien à masquer à ce sujet.

---

## 0. COLD OPEN — LE DOUBLE PROBLÈME (0:00 - 1:00)

**Visuel :** le compteur de puissance animé publié par seanblanchfield sur le forum Home Assistant (« Dashboard real-time power meter with device-level detail », mai 2022) — construit, justement, avec Bar Card. Aucune caméra, uniquement des écrans. Crédit à l'écran.

**Voix off :**
> "Ces dashboards, je les trouve magnifiques. La communauté Home Assistant produit des cartes bluffantes visuellement."

**Visuel (cut) :** capture réelle du fil "Bar-Card Repo Removed in 2025.6.2" (forum Home Assistant, juin 2025) : l'avertissement "Repository removed from HACS" publié par l'auteur du fil, puis la réponse "The bar-card still works". Crédit à l'écran.

**Voix off :**
> "Bar Card, une des cartes les plus utilisées pour les barres d'énergie animées, a été retirée de HACS en juin 2025 : plus maintenue. Tous ceux qui l'utilisaient ont reçu le même avertissement : allez la supprimer. Elle marche encore — mais le jour où une mise à jour la casse, personne ne la réparera. 'Beau' et 'maintenu', ce sont deux choses différentes."

**Visuel (cut) :** icône de cadenas en motion design, puis schéma simple — une maison, une flèche "Internet", un point d'interrogation rouge sur la flèche.

**Voix off :**
> "Et il y a un deuxième problème, plus grave encore : ce tableau de bord, si vous voulez y accéder depuis votre téléphone en dehors de chez vous, il doit être exposé sur Internet. Et ce n'est pas juste des cartes qu'on expose — ce sont vos données personnelles. Vos habitudes de présence, vos caméras, parfois vos serrures. Un dashboard mal sécurisé sur une plateforme accessible depuis l'extérieur, c'est une porte ouverte sur votre maison."

**Titre animé :** VISIO SAPIENS — Pilote : Vision & Architecture

---

## 1. MON APPROCHE : SIMPLE, EFFICACE, SÉCURISÉ (1:00 - 2:30)

**Visuel :** plan mains sur clavier/souris, fenêtre de terminal ou éditeur de code en fond flouté à l'écran. Pas de visage à aucun moment.

**Voix off :**
> "Face à ces deux problèmes — la maintenance qui lâche, et la sécurité qu'on néglige — j'ai fait un choix de départ, et c'est celui qui définit tout le projet : construire un produit **simple et efficace**, qui embarque un maximum de sécurité **par défaut**, pas en option qu'on ajoute après coup si on y pense.
>
> Ça veut dire : le moins de dépendances externes possible sur lesquelles je n'ai aucun contrôle, une architecture pensée dès le départ pour être exposée sur Internet sans que ce soit un pari, et un environnement qui permet de revenir en arrière proprement si quelque chose casse — parce que ça arrivera, tôt ou tard, sur n'importe quel projet.
>
> Concrètement, ça se traduit par un environnement CI/CD qui permet à **une personne autodidacte** — pas une équipe DevOps, juste quelqu'un de motivé — de faire évoluer le produit progressivement, ou tout simplement de **restaurer une version précédente directement dans HAOS** si une mise à jour se passe mal. On détaillera ce pipeline dans le bloc A de la série, et la sauvegarde a son propre bloc, le bloc B. Mais je voulais que vous sachiez, dès ce premier épisode, que ce filet de sécurité existe et qu'il fait partie du socle du projet."

**Texte à l'écran (encadré) :**
> 🔧 Peu de dépendances externes non maîtrisées
> 🔒 Sécurité pensée dès le départ, pas ajoutée après
> ↩️ Restauration de version dans HAOS, accessible même en autodidacte

---

## 2. L'AUTRE PROBLÈME QU'ON NE VOIT PAS : LA COMPLEXITÉ DE HA (2:30 - 3:30)

**Visuel :** capture écran de l'interface Home Assistant standard — menus, panneaux de configuration, YAML — souris qui navigue pour illustrer la complexité, aucune caméra.

**Voix off :**
> "Il y a une troisième raison à tout ça, plus simple à formuler mais tout aussi centrale : l'interface native de Home Assistant est **très complexe**. Puissante, oui — mais complexe. Entre les menus de configuration, les entités, les zones, les dashboards imbriqués, on peut vite se perdre, surtout quand on débute.
>
> L'objectif de Visio Sapiens, c'est de **simplifier ce fonctionnement** — pas de cacher la puissance de Home Assistant, mais de la rendre accessible à travers une interface cohérente, pensée pour l'usage quotidien plutôt que pour la configuration technique."

**Texte à l'écran (encadré) :**
> 🎯 Objectif du projet : simplifier l'usage, sans sacrifier la puissance de HA

---

## 3. CE QU'EST VRAIMENT VISIO SAPIENS (3:30 - 5:00)

**Visuel :** dashboard HOME de Visio Sapiens en plein écran, souris qui se déplace lentement sur les zones évoquées. Aucun visage.

**Voix off :**
> "Alors concrètement, qu'est-ce que c'est ? Visio Sapiens n'est pas un dashboard. C'est une **interface façon centre de contrôle**, posée sur Home Assistant.
>
> La nuance est importante. Un dashboard, c'est une collection de cartes qu'on assemble. Un centre de contrôle, c'est un système cohérent, avec son propre moteur de rendu, sa propre logique visuelle, sa propre identité — et qui se contente d'aller chercher les données chez Home Assistant.
>
> Et cette nuance a une conséquence très concrète, que vous verrez à l'œuvre dans tous les épisodes : l'interface n'est pas assemblée à la main, elle est **générée**. Vous décrivez votre maison une fois, dans une console d'administration — la langue, le format, les pièces, l'apparence — et l'ensemble des écrans est produit à partir de cette description, puis tenu en cohérence quand la maison change. Ajouter une pièce, ce n'est pas dessiner un nouveau dashboard : c'est déclarer une pièce, et laisser le générateur faire le reste. Un dashboard qu'on assemble à la main vieillit. Un dashboard généré suit.
>
> Et ça mène à la règle unique qui pilote toutes les décisions techniques de ce projet, celle que vous allez retrouver dans chaque épisode :
>
> **Home Assistant n'est plus qu'un moteur de données. L'interface est entièrement pilotée par VSSP.**"

**Texte à l'écran (encadré) :**
> 🧠 HA = moteur de données
> 🎛️ VSSP = l'interface, entièrement

---

## 4. POURQUOI PAS LES CARTES LOVELACE NATIVES ? (5:00 - 7:30)

**Visuel :** écran partagé — à gauche l'éditeur Lovelace natif avec ses cartes standards, à droite le dashboard HOME de Visio Sapiens. Au passage sur les trois fondations, incruster leurs noms sur l'écran de droite. Au passage sur card-mod, montrer la carte météo du bandeau, puis la règle `::after` de `_header.j2` qui réécrit son texte. Toujours aucune caméra.

**Voix off :**
> "Alors la question qui vient tout de suite : pourquoi ne pas juste utiliser les cartes natives de Lovelace ? Elles existent, elles sont maintenues par le cœur de Home Assistant, elles marchent très bien.
>
> Justement — elles marchent très bien **pour ce qu'elles sont** : un système de cartes empilées. Mais dès qu'on veut une identité visuelle cohérente et un HUD qui se comporte comme une vraie interface système, pas comme une grille de widgets, on se heurte au plafond de verre de Lovelace.
>
> Alors le projet a fait un choix : ne pas assembler des cartes toutes faites, mais construire son propre moteur de rendu. Et je veux être précis, parce que la version courte serait fausse : ce moteur ne part pas de zéro. Il repose sur trois briques de la communauté — **button-card, card-mod et layout-card**. Des fondations, pas des widgets : l'une dessine, l'autre habille, la troisième place. Tout ce que vous voyez au-dessus — la navigation, le bandeau, les jauges, les pièces — ce sont des gabarits que j'écris, générés et versionnés dans le dépôt. Et quelques cartes spécialisées font ce qu'il serait absurde de réécrire : les graphiques, la météo, l'agenda, l'historique.
>
> La différence avec un dashboard communautaire classique, c'est la surface exposée. Trois fondations et une poignée de cartes, que l'écran des mises à jour surveille comme une famille à part — pas trente widgets avec trente mainteneurs. Le jour où une brique lâche, c'est une brique à remplacer, pas trente cartes à retrouver.
>
> Le prix de ce choix existe, soyons honnêtes : pour tout ce qui est au-dessus des fondations, **je deviens le mainteneur**. Mais ce coût-là, je le **contrôle** : un bug dans mes gabarits, je le corrige le soir même.
>
> Et card-mod mérite un mot. Sur mes propres gabarits, c'est un outil. Dans le shadow DOM d'une carte que je ne maîtrise pas, c'est une rustine — et il m'en reste une : pour forcer la langue d'une carte météo tierce, je masque son texte et j'en écris un autre par-dessus. Ça tient jusqu'à la mise à jour qui renomme une classe. C'est pour ça que ce genre de rustine reste une exception, et qu'elle est documentée."

**Texte à l'écran (encadré) :**
> 🧱 Fondations : `button-card` · `card-mod` · `layout-card`
> 📊 Cartes spécialisées : graphiques · météo · agenda · historique
> 🔧 Au-dessus : les gabarits VSSP, générés et versionnés

---

## 5. LE DIAGRAMME D'ARCHITECTURE (7:30 - 9:30)

**Visuel :** plein écran sur le diagramme « Vue d'ensemble » de `Vision.md` (§2), redessiné à la résolution d'enregistrement. Plan mains avec stylet/tablette graphique pour surligner chaque bloc au fur et à mesure — c'est le seul moment de "présence physique" de l'épisode, limité aux mains. Enchaîner sur la chaîne de génération (§4), puis sur la boucle en six temps de la console (§5).

**Voix off :**
> "Voilà à quoi ressemble l'architecture complète. Je vous la montre une fois, en entier, parce que c'est la carte dont vous aurez besoin pour suivre toute la série."

**Parcours du diagramme, bloc par bloc (surlignage successif au stylet) :**

> "Cinq endroits détiennent quelque chose, et ils ne sont pas interchangeables. Le **dépôt Git**, sur mon poste : le modèle, les gabarits, les traductions, l'outillage. Le **pipeline GitLab**, qui valide, construit et déploie. **Deux cibles**, qui reçoivent le même paquet : un cluster k3s pour le staging, Home Assistant OS pour la production. Et le **navigateur** — la tablette, le téléphone — où s'affichent les dashboards.
>
> Au milieu, une seule commande : **le générateur**. Il prend la description de la maison, les gabarits et la langue, et il produit tous les dashboards et le thème. Personne n'écrit un dashboard à la main.
>
> Et chaque écran de la console d'administration suit **la même boucle** : un formulaire envoie ce que vous avez décidé, un script sauvegarde d'abord, écrit le modèle, régénère, puis rend compte de ce qu'il a fait."

**Voix off (conclusion du parcours) :**
> "Retenez une chose de ce schéma : chaque morceau a une responsabilité précise, et aucun ne fait le travail d'un autre. C'est ce qui permet au projet de tenir dans la durée sans devenir un plat de spaghettis YAML — et c'est ce qui rend possible le reste de la série : on ne peut versionner, sauvegarder et restaurer proprement que ce qui est structuré."

---

## 6. VISITE EN DIRECT DU DASHBOARD HOME (9:30 - 11:30)

**Visuel :** capture en direct à **1194 × 834** — la tablette murale réelle (iPad 11 pouces, paysage), barre latérale de Home Assistant masquée. Souris qui pointe chaque élément au fur et à mesure du texte. Aucun visage.

**Voix off :**
> "Assez de théorie, on regarde le résultat. Voici HOME, l'écran d'accueil, tel qu'il s'affiche sur la tablette du salon."

**Pointage successif (curseur souris) :**
> "À gauche, le **rail de navigation** : une entrée par pièce déclarée, plus les écrans système. Il est généré lui aussi — ajoutez une pièce, son entrée apparaît sur tous les écrans à la fois.
>
> En haut, le **bandeau** : le nom de l'écran et l'heure, la météo, l'agenda. Le même bandeau sur chaque dashboard, parce qu'il vient d'un seul gabarit.
>
> Juste en dessous, la **rangée d'état** : le système, l'énergie, l'alarme avec ses modes et son bouton panique, le thermostat — et ce voyant de mises à jour, qui passe à l'orange quand quelque chose attend, et qui mène à l'écran qui dit exactement quoi.
>
> Au centre, le **radar des protocoles**, et à côté, les appareils mesurés avec ce qu'ils consomment. Puis la **barre de l'assistant**, et les derniers événements de la maison."

**Transition vers le repo :**
> "Et maintenant, la partie que je préfère montrer, parce qu'elle rend tout ça concret : d'où vient l'apparence de cet écran."

**Visuel :** split screen — à gauche `dashboards/model/design_system.yaml` dans un éditeur de code, à droite l'écran ADMIN → TEMPLATE GRAPHIQUE, puis HOME. Monter le curseur « Values » du groupe Text sizes, appliquer, revenir sur HOME.

**Voix off :**
> "À gauche, un fichier du dépôt, `design_system.yaml` : chaque couleur, la police, la taille de chaque catégorie de texte. À droite, l'écran de la console qui l'édite. Je monte la taille des valeurs — et tous les écrans suivent en même temps, parce qu'il n'y a qu'une seule source. Pas dix cartes à retoucher une par une en espérant n'en oublier aucune. Le code et l'interface parlent la même langue — et donc, ils se versionnent comme un vrai projet logiciel."

---

## 7. LA CONSOLE : DÉCRIRE LA MAISON UNE FOIS (11:30 - 14:00)

**Visuel :** capture à 1194 × 834. Le menu ADMIN et ses neuf lignes, puis PIÈCES & ÉTAGES : déclarer une pièce de démonstration (« Buanderie », rez-de-chaussée), APPLIQUER, le message de statut qui s'affiche. Retour sur HOME, gros plan sur le rail ; puis ÉNERGIE et CORE pour montrer la même entrée partout.

**Voix off :**
> "Je vous ai dit que l'interface est générée à partir d'une description de la maison. Voici où on l'écrit : la **console d'administration**.
>
> Neuf écrans, un par décision. Les pièces et les étages. Les appareils que le réseau vient de découvrir. L'affectation de chaque appareil à une pièce. L'agenda Google, la charte graphique, les dashboards eux-mêmes, les mises à jour, et le coffre-fort.
>
> On déclare une pièce, en direct. Une buanderie, au rez-de-chaussée. J'applique.
>
> Ce qui se passe pendant ces quelques secondes, c'est la boucle que je vous ai montrée sur le schéma. Le formulaire envoie ce que j'ai décidé. Un script **sauvegarde d'abord** l'état actuel — toujours, avant d'écrire quoi que ce soit. Il écrit le modèle, relance le générateur, et rend compte : ce message-là, en haut, c'est lui.
>
> Je reviens sur HOME. La buanderie est dans le rail. Et elle y est sur tous les écrans à la fois — l'énergie, le système, la console — parce que le rail n'est écrit nulle part à la main.
>
> Un détail honnête : l'écran de la pièce elle-même est déclaré dans la configuration de Home Assistant, et Home Assistant ne relit cette configuration qu'au démarrage. Son entrée apparaît tout de suite ; son écran, au prochain redémarrage. Je préfère vous le dire que de le couper au montage.
>
> Et c'est le même geste pour tout le reste. On ne dessine jamais un dashboard. On décide, et la console écrit."

---

## 8. LA SÉCURITÉ PAR DÉFAUT, CONCRÈTEMENT (14:00 - 16:30)

**Visuel :** quatre tuiles en motion design, chacune ouverte sur une preuve à l'écran : l'automation d'un webhook avec `local_only: true` ; les DevTools d'une iframe de la console, `localStorage` sans aucun jeton ; l'écran COFFRE-FORT avec des secrets **de démonstration** (noms visibles, valeurs masquées) ; un fichier `0600` et un journal de déploiement sans mot de passe. Puis `Https.md` à l'écran pour la partie « pas encore fait ».

**Voix off :**
> "Au début, je vous ai promis la sécurité par défaut. Une promesse, ça se vérifie — alors voici ce que ça veut dire concrètement, y compris ce qui n'est pas encore fait.
>
> **Un** : les formulaires de la console n'envoient rien avec un mot de passe. Ils passent par des points d'entrée que Home Assistant n'accepte que depuis le réseau local. Depuis Internet, ils n'existent pas.
>
> **Deux** : une tablette neuve ne garde aucun identifiant permanent. Les écrans de la console empruntent la session avec laquelle vous vous êtes connecté, un jeton court que Home Assistant renouvelle lui-même. Perdre la tablette, ce n'est pas perdre une clé.
>
> **Trois** : les secrets vivent dans un coffre-fort, pas dans des fichiers. Home Assistant peut y lire le nom de chaque secret, jamais sa valeur — parce que tout ce que Home Assistant lit finit en clair dans sa base d'historique. Le coffre se referme à chaque redémarrage, et on le rouvre d'une phrase secrète, depuis un appareil qu'on a enrôlé.
>
> **Quatre** : aucun mot de passe ne passe sur une ligne de commande ni dans un journal — ni celui de la box, ni les clés des assistants.
>
> Et maintenant, ce qui n'est pas fait. Aujourd'hui, sur le réseau local, le mot de passe de Home Assistant voyage encore en clair. Le passage en HTTPS est écrit et documenté ; il n'est pas encore posé. Il a son épisode, dans le bloc A.
>
> C'est ça, pour moi, la sécurité par défaut : pas une liste de promesses, mais une liste de choses qu'on peut vérifier — et, publiée juste à côté, la liste de celles qui manquent."

**Texte à l'écran (encadré) :**
> 🏠 Webhooks : réseau local uniquement
> 📱 Tablettes : la session, jamais un jeton permanent
> 🔐 Secrets : dans le coffre — HA lit les noms, jamais les valeurs
> 🚫 Aucun mot de passe en ligne de commande ni dans un journal
> ⏳ HTTPS : documenté, pas encore posé

---

## 9. UNE NOTE SUR LES NOMS (16:30 - 17:15)

**Visuel :** le commit du 12 septembre (`refactor: the old name is gone from the code…`) à l'écran, puis les deux traces restantes : `class OSVisionEngine` dans `www/vssp/js/vssp.js`, et le chemin `/local/osvision_v2/k3s_stats.json` dans `core.html`. Voix off seule.

**Voix off :**
> "Petite parenthèse avant de conclure, parce que vous allez tomber dessus : le projet s'appelait au départ **OSVision**, avant de devenir **VSSP**. En septembre, un grand ménage a retiré l'ancien nom des identifiants, des composants et des feuilles de style — et ce ménage a fait remonter trois vrais bugs, dont un lien mort que personne n'avait vu. Mais il reste des traces : le moteur JavaScript porte encore l'ancien nom, et le panneau K3s de l'écran CORE cherche toujours son fichier sous l'ancien chemin. Un bon projet ne cache pas ces traces, il les documente. Celle-là, on la corrigera en direct dans l'épisode D1."

---

## 10. MONTAGE RAPIDE — CE QUI A ÉTÉ LIVRÉ (17:15 - 18:00)

**Visuel :** montage rythmé calé sur la musique, un plan par jalon : le générateur qui régénère, l'écran PIÈCES & ÉTAGES, le bouton DESCELLER du coffre-fort, l'écran MISES À JOUR, le TEMPLATE GRAPHIQUE qui change la police. Source des jalons : l'historique Git (`git log --oneline`), `Vision.md` n'ayant plus de section changelog depuis sa réécriture du 9 septembre.

**Voix off (courte, punchy) :**
> "Tout ce que vous venez de voir n'existait pas il y a quelques mois. Un générateur qui produit chaque écran. Une console qui déclare les pièces. Un coffre-fort qui se descelle depuis un appareil enrôlé. Un écran de mises à jour qui sait ce qu'il ne sait pas. Une charte graphique qui change jusqu'à la police. Ce n'est pas un projet figé — c'est un système qui a une histoire, et qui continue d'en écrire une."

*(Note prod : ce bloc peut aussi servir d'ouverture alternative si le montage final préfère un cold open plus dynamique.)*

---

## 11. LA CARTE DE LA SÉRIE (18:00 - 19:00)

**Visuel :** motion design — quatre tuiles qui s'allument l'une après l'autre (A · B · C · D), chacune avec le titre de son bloc et le nombre de ses épisodes (6 · 2 · 3 · 10), puis les quatre ensemble, et « 20 min » sous chaque tuile.

**Voix off :**
> "La suite de la série est organisée en quatre blocs, et vous choisissez votre porte d'entrée. Chaque épisode dure une vingtaine de minutes : le temps de montrer, pas seulement de raconter.
>
> Le **bloc A**, c'est le socle : la machine, le cluster, le pipeline, et ce qui casse quand l'un des trois ment.
>
> Le **bloc B**, c'est la sauvegarde — jusqu'à la seule preuve qui compte : la restauration.
>
> Le **bloc C**, c'est le coffre-fort : où vivent les secrets, et comment on le descelle sans taper trois clés à la main.
>
> Et le **bloc D**, c'est l'interface elle-même, de la jauge jusqu'au générateur.
>
> À l'intérieur d'un bloc, l'ordre compte. Entre les blocs, non : si vous êtes venu pour les sauvegardes, vous n'avez pas à regarder dix épisodes d'interface d'abord."

**Texte à l'écran (encadré) :**
> A · Environnement & CI/CD — B · Sauvegarde — C · Coffre-fort — D · Interface

---

## 12. CONCLUSION (19:00 - 20:00)

**Visuel :** retour sur le dashboard HOME en plein écran, ou logo de la chaîne animé. Voix off seule. Les vingt dernières secondes portent l'écran de fin YouTube (abonnement + D1 + un épisode du bloc C).

**Voix off :**
> "Ce qu'il faut retenir : Visio Sapiens n'est pas un dashboard, c'est un centre de contrôle, simple, efficace et sécurisé par défaut. Home Assistant fournit la donnée, VSSP fournit l'interface — sur un petit nombre de fondations surveillées, avec un pipeline qui permet de revenir en arrière.
>
> Si vous ne savez pas par où commencer, prenez D1 : on suit une seule donnée, de la machine hôte jusqu'à une jauge dans votre navigateur.
>
> Abonnez-vous, et dites-moi en commentaire : votre Home Assistant, c'est encore un empilement de cartes, ou vous avez commencé à en sortir ? À très vite."

---

## NOTES DE PRODUCTION

- **Format sans visage :** aucun plan caméra face ne doit être filmé. La voix off porte tout le récit. Les seuls plans "présence humaine" autorisés sont des plans mains (clavier, souris, stylet sur tablette pour annoter le diagramme d'architecture, section 5). Le reste est 100% captures d'écran, motion design, et texte à l'écran.
- **Enregistrement voix :** une section = un fichier audio, posé au début de son créneau. La narration seule, découpée par section, vit dans `episode-01-narration.fr.txt` ; les sous-titres dans `episode-01.fr.srt`. Les deux sont **générés depuis ce script** — les régénérer après toute modification de voix off plutôt que de les retoucher à la main.
- **Ton général :** pédagogue, affirmatif sur le choix "moteur maison vs Lovelace natif" et sur la sécurité — c'est la thèse de l'épisode, elle doit être défendue clairement. Mais la section 4 dit exactement sur quoi le moteur repose : c'est ce qui rend la thèse défendable face à un spectateur qui ouvre le dépôt.
- **Fil rouge de l'intro :** double problème (maintenance communautaire qui lâche + exposition Internet non sécurisée) → réponse du projet (produit simple/efficace/sécurisé + CI/CD restaurable en HAOS) → complexité native de HA → simplification.
- **Captures :** toutes à **1194 × 834** (iPad 11 pouces, paysage — la tablette murale réelle), barre latérale de Home Assistant masquée. Toute capture de HOME faite avant le 14 septembre 2026 est périmée : le bandeau, la rangée d'état et la liste des appareils ont changé depuis.
- **Diagramme d'architecture :** les diagrammes de `Vision.md` (§2, §4, §5) sont en mermaid ; les redessiner à la résolution d'enregistrement avant tournage.
- **B-roll :** le compteur de puissance animé de seanblanchfield et le fil "Bar-Card Repo Removed in 2025.6.2" (forum Home Assistant — voir « Montage du chapitre 0 » ci-dessous), schéma exposition Internet, interface HA native (complexité), dashboard HOME en direct, `design_system.yaml` et l'écran TEMPLATE GRAPHIQUE, historique Git pour le montage.
- **Montage du chapitre 0 :** rendu le 14 septembre 2026 (60 s, 1920 × 1080, 30 i/s, sans son), calé sur les sous-titres FR ; une version avec les sous-titres FR incrustés sert d'aperçu. Les trois captures viennent du forum Home Assistant et sont des **citations** : garder les crédits à l'écran, lier les fils en description, et, pour le GIF de seanblanchfield, lui demander l'accord avant publication. Rangé dans `media/pilote/chapitre-00/`, que git ignore : les vidéos, `pilote_chap00_SOURCES.txt` (déroulé, sources, crédits) et, dans `sources/`, les captures et le script qui refait le rendu.
- **Ne pas filmer :** tout secret en direct → bloc C, D3, D6. En section 8, le coffre-fort ne montre que des secrets de démonstration.
- **La pièce de démonstration (section 7) :** la déclarer, appliquer, filmer le rail ; son propre écran n'existe qu'après intégration du fragment de configuration et redémarrage de Home Assistant — le faire hors caméra si on veut l'ouvrir. La supprimer après la prise (PIÈCES & ÉTAGES), sinon elle reste dans le rail de chaque écran.
- **Renvois croisés :** pipeline CI/CD → A2 ; HTTPS → A4 ; sauvegarde et restauration → bloc B ; coffre-fort → C1, C2 ; revue de sécurité → C3 ; CORE et le bug K3s de l'ancien chemin → D1 ; générateur → D2 ; assignation → D4 ; chatbot → D6 ; charte graphique → D7 ; la tablette murale → D10.

---

## MINUTAGE DE LA NARRATION

Mesuré contre les créneaux ci-dessus, à 140 mots par minute. La narration seule, découpée par section, vit dans `episode-01-narration.fr.txt`.

<!-- TIMING-TABLE -->
| # | Section | Créneau | Narration | Écart |
|---|---|---|---|---|
| 0 | Cold open | 60 s | 63 s | +3 s |
| 1 | Mon approche | 90 s | 87 s | −3 s |
| 2 | La complexité de HA | 60 s | 37 s | −23 s |
| 3 | Ce qu'est Visio Sapiens | 90 s | 86 s | −4 s |
| 4 | Pourquoi pas les cartes natives | 150 s | 151 s | +1 s |
| 5 | Diagramme d'architecture | 120 s | 95 s | −25 s |
| 6 | Visite de HOME | 120 s | 105 s | −15 s |
| 7 | La console | 150 s | 100 s | −50 s |
| 8 | La sécurité par défaut | 150 s | 114 s | −36 s |
| 9 | Une note sur les noms | 45 s | 44 s | −1 s |
| 10 | Montage — ce qui a été livré | 45 s | 32 s | −13 s |
| 11 | La carte de la série | 60 s | 54 s | −6 s |
| 12 | Conclusion | 60 s | 40 s | −20 s |
| | **Total** | **20:00** | **16:48** | **−192 s** |

Sections volontairement courtes, où l'image porte le temps : 2, 5, 6, 7, 8, 12. Partout ailleurs, la narration remplit son créneau.
<!-- /TIMING-TABLE -->

---

## Révision du 14 septembre 2026

Le script du 10 septembre avait été écrit contre un projet qui avait déjà bougé sous lui, et le projet a encore bougé depuis. Ce qui a changé, et pourquoi :

| Section | Avant | Maintenant | Pourquoi |
|---|---|---|---|
| 0 | « des milliers de dashboards avec une carte rouge, cassée, du jour au lendemain » | l'avertissement réel de HACS, et une carte qui marche encore sans mainteneur | le fil que cite le script montre l'avertissement « Repository removed from HACS » et une réponse « The bar-card still works » — aucune carte rouge. L'argument « beau ≠ maintenu » tient sans l'exagération |
| Tout le script | renvois « épisode 2, 3, 6, 9, 12 » | codes de bloc (A2, D1, D2, D6, C4…) | la série a été regroupée en quatre blocs le 12 septembre ; les anciens numéros n'existent plus |
| 4 | « aucune dépendance à un mainteneur communautaire », « plus de rustine card-mod », exceptions `weather-forecast` · `logbook` · `apexcharts-card` | trois fondations nommées (button-card, card-mod, layout-card), cartes spécialisées, une rustine card-mod assumée | les gabarits comptent 173 `custom:button-card`, 10 `grid-layout` et 95 blocs `card_mod` ; `weather-forecast` n'est utilisée nulle part (la météo passe par `dynamic-weather-card` et `simple-weather-card`). L'ancienne formulation était fausse pour quiconque ouvre le dépôt |
| 5 | diagramme « CORE / Room Engine / IA Layer / Animation / CSS / JS / Theme Engine » | la vue d'ensemble de `Vision.md` (§2), la chaîne de génération (§4), la boucle de la console (§5) | `Vision.md` a été réécrit le 9 septembre ; l'ancien diagramme n'y figure plus |
| 6 | « rangée HUD : météo, horloge, statut d'alarme, avatar », « rangée énergie », `vssp.css` comme source de l'apparence | bandeau (écran + heure, météo, agenda), rangée d'état (système, énergie, alarme, thermostat, voyant de mises à jour), radar, appareils mesurés, assistant ; `design_system.yaml` + écran TEMPLATE GRAPHIQUE | c'est ce qu'affiche HOME aujourd'hui ; depuis le 13 septembre la police et les tailles de texte sont des réglages de la charte |
| 9 | « vous allez croiser d'anciens noms de fichiers » | le ménage du 12 septembre, ses trois bugs, et les deux traces qui restent | l'ancien nom a été retiré du code le 12 septembre, sauf `OSVisionEngine` et le chemin K3s de CORE |
| 10 | placeholder « [liste de 3-4 jalons, à choisir dans Vision.md] » | cinq jalons écrits | `Vision.md` n'a plus de section changelog |
| 7 | — | **nouvelle section** : la console, et une pièce déclarée en direct | passage au format 20 minutes ; c'est la preuve de « l'interface est générée », la thèse de la section 3 |
| 8 | — | **nouvelle section** : la sécurité par défaut, quatre mesures vérifiables et ce qui manque | passage au format 20 minutes ; le cold open promet la sécurité, rien ne la montrait |
| 11 | — | **nouvelle section** : la carte des quatre blocs (6 · 2 · 3 · 10 épisodes de 20 min) | le plan de série dit que le pilote « les annonce tous » ; le script ne le faisait pas |
| 12 | « le prochain épisode suit une donnée depuis psutil » | D1 proposé comme point d'entrée, pas comme suite obligée | entre les blocs, l'ordre ne compte plus |
| Durée | 11-13 puis 13-15 min | **20 min** | format commun à toute la série, décidé le 14 septembre |
| Avertissement | « ne pas filmer : jetons longue durée » | secrets listés ; plus de jeton longue durée sur les tablettes | depuis le 14 septembre, les pages de la console empruntent la session Home Assistant de la tablette |
