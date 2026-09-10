# ÉPISODE 1 — Vision & Architecture
## "Visio Sapiens : pourquoi j'ai jeté les cartes Lovelace natives"

**Doc source :** `Vision.md`
**Question centrale de l'épisode :** Pourquoi remplacer les cartes natives de Lovelace par un moteur maison ?
**Ancrage visuel :** diagramme d'architecture + visite en direct du dashboard HOME
**Durée estimée :** 11-13 min
**Format de tournage :** aucun plan visage. La chaîne repose sur **voix off + captures d'écran + plans mains** (clavier, souris, éventuellement un stylet sur tablette pour annoter le diagramme). Chaque indication "face caméra" des versions précédentes est remplacée ci-dessous.

**Objectif :** donner aux spectateurs le modèle mental avant tout code. Ce qu'est Visio Sapiens — une interface façon centre de contrôle posée sur Home Assistant, **pas** un simple dashboard habillé — et pourquoi le projet refuse les cartes Lovelace natives, sauf exceptions documentées (`weather-forecast`, `logbook`, `apexcharts-card`).

**⚠️ À ne pas filmer tout de suite :** tout ce qui dépend de secrets en direct (mot de passe Livebox, jetons longue durée) — garder la gestion des secrets pour l'épisode 4 ou 6.

---

## 0. COLD OPEN — LE DOUBLE PROBLÈME (0:00 - 1:00)

**Visuel :** montage de captures Reddit/HACS — dashboards communautaires magnifiques, animations, gauges custom. Aucune caméra, uniquement des écrans.

**Voix off :**
> "Ces dashboards, je les trouve magnifiques. La communauté Home Assistant produit des cartes bluffantes visuellement."

**Visuel (cut) :** capture réelle du forum communautaire — le fil "Bar-Card Repo Removed in 2025.6.2" — puis la même carte affichée en rouge dans un dashboard avec "Custom element doesn't exist".

**Voix off :**
> "Bar Card, une des cartes les plus utilisées pour les barres d'énergie animées, s'est retrouvée sans dépôt disponible dans HACS en 2025 — plus de mainteneur officiel. Résultat : des milliers de dashboards avec une carte rouge, cassée, du jour au lendemain, sans prévenir personne. 'Beau' et 'maintenu', ce sont deux choses différentes."

**Visuel (cut) :** icône de cadenas en motion design, puis schéma simple — une maison, une flèche "Internet", un point d'interrogation rouge sur la flèche.

**Voix off :**
> "Et il y a un deuxième problème, plus grave encore : ce tableau de bord, si vous voulez y accéder depuis votre téléphone en dehors de chez vous, il doit être exposé sur Internet. Et ce n'est pas juste des cartes qu'on expose — ce sont vos données personnelles. Vos habitudes de présence, vos caméras, parfois vos serrures. Un dashboard mal sécurisé sur une plateforme accessible depuis l'extérieur, c'est une porte ouverte sur votre maison."

**Titre animé :** VISIO SAPIENS — Épisode 1 : Vision & Architecture

---

## 1. MON APPROCHE : SIMPLE, EFFICACE, SÉCURISÉ (1:00 - 2:30)

**Visuel :** plan mains sur clavier/souris, fenêtre de terminal ou éditeur de code en fond flouté à l'écran. Pas de visage à aucun moment.

**Voix off :**
> "Face à ces deux problèmes — la maintenance qui lâche, et la sécurité qu'on néglige — j'ai fait un choix de départ, et c'est celui qui définit tout le projet : construire un produit **simple et efficace**, qui embarque un maximum de sécurité **par défaut**, pas en option qu'on ajoute après coup si on y pense.
>
> Ça veut dire : le moins de dépendances externes possible sur lesquelles je n'ai aucun contrôle, une architecture pensée dès le départ pour être exposée sur Internet sans que ce soit un pari, et un environnement qui permet de revenir en arrière proprement si quelque chose casse — parce que ça arrivera, tôt ou tard, sur n'importe quel projet.
>
> Concrètement, ça se traduit par un environnement CI/CD qui permet à **une personne autodidacte** — pas une équipe DevOps, juste quelqu'un de motivé — de faire évoluer le produit progressivement, ou tout simplement de **restaurer une version précédente directement dans HAOS** si une mise à jour se passe mal. On détaillera ce pipeline en profondeur dans l'épisode 6, mais je voulais que vous sachiez, dès cet épisode 1, que ce filet de sécurité existe et qu'il fait partie du socle du projet, pas d'une fonctionnalité annexe."

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
> Et cette nuance a une conséquence très concrète, que vous verrez à l'œuvre dans tous les épisodes : l'interface n'est pas assemblée à la main, elle est **générée**. Vous décrivez votre maison une fois — la langue, le format, les pièces — et l'ensemble des écrans est produit à partir de cette description, puis tenu en cohérence quand la maison change. Ajouter une pièce, ce n'est pas dessiner un nouveau dashboard : c'est déclarer une pièce, et laisser le générateur faire le reste. Un dashboard qu'on assemble à la main vieillit. Un dashboard généré suit.
>
> Et ça mène à la règle unique qui pilote absolument toutes les décisions techniques de ce projet, celle que vous allez retrouver dans chaque épisode :
>
> **Home Assistant n'est plus qu'un moteur de données. L'interface est entièrement pilotée par VSSP.**"

**Texte à l'écran (encadré) :**
> 🧠 HA = moteur de données
> 🎛️ VSSP = l'interface, entièrement

---

## 4. POURQUOI PAS LES CARTES LOVELACE NATIVES ? (5:00 - 7:30)

**Visuel :** écran partagé — à gauche l'éditeur Lovelace natif avec ses cartes standards, à droite le dashboard HOME de Visio Sapiens. Toujours aucune caméra.

**Voix off :**
> "Alors la question qui vient tout de suite : pourquoi ne pas juste utiliser les cartes natives de Lovelace ? Elles existent, elles sont maintenues par le cœur de Home Assistant, elles marchent très bien.
>
> Justement — elles marchent **très bien pour ce qu'elles sont** : un système de cartes empilées. Mais dès qu'on veut une identité visuelle cohérente, des animations qui répondent en temps réel, un HUD qui se comporte comme une vraie interface système et pas comme une grille de widgets, on se heurte au plafond de verre de Lovelace.
>
> Alors le projet a fait un choix radical : **refuser les cartes Lovelace natives**, et construire son propre moteur de rendu par-dessus. Avec trois exceptions, assumées et documentées, parce que ce serait stupide de réinventer ce qui fonctionne déjà très bien : `weather-forecast`, `logbook`, et `apexcharts-card`.
>
> Tout le reste — la sidebar, le HUD, les jauges, les rangées énergie, les pièces — c'est du moteur maison, que **je** maintiens, avec le même pipeline CI/CD dont je vous parlais tout à l'heure. Pas de dépendance à un mainteneur communautaire qui peut disparaître du jour au lendemain.
>
> Alors soyons honnêtes sur le prix de ce choix, parce qu'il en a un : en refusant les cartes de la communauté, **je deviens le mainteneur**. Si une jauge casse, personne d'autre ne viendra la réparer. C'est un vrai coût, et je l'assume pour une raison précise : ce coût-là, je le **contrôle**. Une carte communautaire qui disparaît, je ne contrôle rien — ni le calendrier, ni la décision, ni la migration. Un bug dans mon propre moteur, je peux le corriger le soir même et le déployer dans la foulée.
>
> Et il y a un effet de bord que je n'avais pas anticipé en commençant. Quand on écrit son propre moteur, on arrête d'empiler des rustines. Le fameux `card-mod`, avec ses sélecteurs CSS qui vont piocher dans le shadow DOM d'une carte qu'on ne maîtrise pas — ça fonctionne, oui, jusqu'à la mise à jour qui renomme une classe. Là, il n'y a plus de rustine : il y a du CSS que j'écris, sur du HTML que je produis."

**Texte à l'écran (encadré) :**
> ✅ Exceptions documentées : `weather-forecast` · `logbook` · `apexcharts-card`
> 🔧 Tout le reste : moteur VSSP, maintenu en interne

---

## 5. LE DIAGRAMME D'ARCHITECTURE (7:30 - 9:30)

**Visuel :** plein écran sur le diagramme d'architecture de `Vision.md`. Plan mains avec stylet/tablette graphique pour surligner chaque bloc au fur et à mesure — c'est le seul moment de "présence physique" de l'épisode, limité aux mains.

**Voix off :**
> "Voilà à quoi ressemble l'architecture complète. Je vous la montre une fois, en entier, parce que c'est la carte mentale dont vous aurez besoin pour comprendre tous les épisodes qui suivent."

**Parcours du diagramme, bloc par bloc (surlignage successif au stylet) :**

> "**CORE** : le socle système — c'est lui qui expose les métriques, l'état de la machine, ce sur quoi tout le reste s'appuie. On y reviendra en détail dans l'épisode 2.
>
> **Room Engine** : la logique qui transforme une définition de pièce en interface — c'est le cœur du générateur de dashboards, épisode 3.
>
> **IA Layer** : la couche qui branche de l'intelligence dans l'interface — le chatbot, les automatisations. Épisode 9.
>
> **Animation Engine, CSS Engine, JS Engine, Theme Engine** : les quatre couches qui donnent à Visio Sapiens son identité visuelle et son comportement — c'est ce qui fait qu'une pièce ne ressemble pas à une carte Lovelace avec un joli thème, mais à une vraie interface vivante."

**Voix off (conclusion du parcours) :**
> "Retenez juste une chose de ce schéma : chaque couche a une responsabilité précise, et aucune ne fait le travail d'une autre. C'est ce qui permet au projet de tenir dans la durée sans devenir un plat de spaghettis YAML — et c'est aussi ce qui rend le pipeline CI/CD possible : on ne peut versionner et restaurer proprement que ce qui est structuré."

---

## 6. VISITE EN DIRECT DU DASHBOARD HOME (9:30 - 11:30)

**Visuel :** écran en direct, souris qui pointe chaque élément au fur et à mesure du texte. Aucun visage.

**Voix off :**
> "Assez de théorie, on regarde le résultat. Voici HOME, l'écran d'accueil de Visio Sapiens."

**Pointage successif (curseur souris) :**
> "La **sidebar** — navigation entre les écrans du centre de contrôle.
>
> La **rangée HUD** dans le header : météo, horloge, statut d'alarme, avatar — tout ce qu'on veut voir d'un coup d'œil en entrant dans la maison.
>
> La **rangée énergie** — production, consommation, ce que la maison fait en ce moment, pas un historique qu'on doit aller chercher.
>
> Les **modules de pièces** — un écran par pièce déclarée, tous produits par le même générateur, à partir du même gabarit. Ce ne sont pas dix dashboards écrits dix fois : c'est un gabarit, et dix pièces.
>
> Et le **rail de navigation**, ici, qui se reconstruit tout seul quand une pièce apparaît ou disparaît — parce qu'il est généré lui aussi, pas entretenu à la main dans un coin de YAML qu'on finit toujours par oublier."

**Transition vers le repo :**
> "Et maintenant, la partie que je préfère montrer, parce qu'elle rend tout ça concret : l'arborescence du dépôt, en direct, à côté de ce qui s'affiche à l'écran."

**Visuel :** split screen — arborescence du repo à gauche (dans un éditeur de code type VS Code), dashboard HOME à droite.

**Voix off :**
> "Ce fichier — `www/vssp/css/vssp.css` — c'est **littéralement** ce qui peint cet écran. Pas une métaphore : chaque couleur, chaque espacement que vous voyez à droite vient de ce fichier à gauche. C'est ça, avoir un moteur maison plutôt qu'un thème posé sur des cartes génériques : le code et l'interface parlent la même langue — et donc, sont versionnables comme un vrai projet logiciel.
>
> Et si je change une couleur ici, à gauche, elle change à droite au prochain déploiement. Sur tous les écrans à la fois, parce qu'il n'y a qu'une seule source. Pas dix cartes à retoucher une par une en espérant n'en oublier aucune."

---

## 7. UNE NOTE SUR LES NOMS (11:30 - 12:00)

**Visuel :** capture de l'historique Git / anciens noms de fichiers à l'écran (`osvision_v2/...`), voix off seule, pas de plan mains nécessaire ici.

**Voix off :**
> "Petite parenthèse avant de conclure, parce que vous allez tomber dessus dans les épisodes suivants : le projet s'appelait au départ **OSVision**, et a été renommé en **VSSP**. Vous allez croiser d'anciens noms de fichiers, d'anciens chemins, qui datent de cette époque.
>
> Je le mentionne maintenant pour une raison simple : l'histoire d'un projet laisse des traces. Un bon projet ne cache pas ces traces, il les documente. Vous verrez cette cicatrice de renommage plus tard, notamment dans le bug K3s de l'épisode 2 — et maintenant vous saurez pourquoi elle existe."

---

## 8. MONTAGE RAPIDE — CHANGELOG (12:00 - 12:30)

**Visuel :** montage rythmé, défilement du changelog de `Vision.md`, captures d'écran qui s'enchaînent en rythme avec la musique. Aucune caméra, uniquement écran + musique.

**Voix off (courte, punchy) :**
> "Tout ce que vous venez de voir n'existait pas il y a quelques mois. [liste rapide de 3-4 jalons du changelog, à choisir dans `Vision.md`]. Ce n'est pas un projet figé — c'est un système qui a une histoire, et qui continue d'en écrire une."

*(Note prod : ce bloc peut aussi servir d'ouverture alternative si le montage final préfère un cold open plus dynamique.)*

---

## 9. TRANSITION VERS L'ÉPISODE 2 (12:30 - 13:15)

**Visuel :** retour sur le dashboard HOME en plein écran, ou logo de la chaîne animé. Voix off seule.

**Voix off :**
> "Ce qu'il faut retenir de cet épisode : Visio Sapiens n'est pas un dashboard, c'est un centre de contrôle, pensé pour être simple, efficace et sécurisé par défaut. Home Assistant fournit la donnée, VSSP fournit tout le reste — sans dépendre de cartes communautaires qui peuvent lâcher sans prévenir, et avec un pipeline qui permet de revenir en arrière si besoin, même en autodidacte.
>
> Dans le prochain épisode, on descend d'un niveau : on suit une seule donnée, depuis `psutil` sur la machine hôte jusqu'à une jauge SVG dans votre navigateur, avec les DevTools ouverts pour tout voir passer en direct.
>
> Abonnez-vous, activez la cloche, et dites-moi en commentaire : votre install Home Assistant, elle ressemble encore à un empilement de cartes Lovelace, ou vous avez déjà commencé à en sortir ?
>
> À très vite."

---

## NOTES DE PRODUCTION

- **Format sans visage :** aucun plan caméra face ne doit être filmé. La voix off porte tout le récit. Les seuls plans "présence humaine" autorisés sont des plans mains (clavier, souris, stylet sur tablette pour annoter le diagramme d'architecture, section 5). Le reste est 100% captures d'écran, motion design, et texte à l'écran.
- **Enregistrement voix :** prévoir une prise de voix off propre, séparée du tournage écran, pour pouvoir resynchroniser facilement en montage.
- **Ton général :** pédagogue, affirmatif sur le choix "moteur maison vs Lovelace natif" et sur la sécurité — c'est la thèse de l'épisode, elle doit être défendue clairement, pas juste énoncée.
- **Fil rouge de l'intro :** double problème (maintenance communautaire qui lâche + exposition Internet non sécurisée) → réponse du projet (produit simple/efficace/sécurisé + CI/CD restaurable en HAOS) → complexité native de HA → simplification.
- **Diagramme d'architecture :** à refaire à la résolution d'enregistrement avant tournage.
- **B-roll :** dashboards communautaires (avant/après cassure — capture du fil forum "Bar-Card Repo Removed in 2025.6.2"), schéma exposition Internet, interface HA native (complexité), dashboard HOME en direct, arborescence du repo, changelog `Vision.md`.
- **Ne pas filmer :** tout secret en direct (mot de passe Livebox, jetons longue durée) → épisodes 4/6.
- **Renvois croisés :** pipeline CI/CD détaillé en épisode 6 ; bug K3s et cicatrice OSVision → VSSP en épisode 2 ; sécurité approfondie en épisode 12.
