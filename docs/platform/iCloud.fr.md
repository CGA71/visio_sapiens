# Photos iCloud — déplacer une photothèque vers un stockage qui vous appartient

[English](iCloud.md) · **Français**

iCloud se remplit. La réponse habituelle est d'en payer davantage. Cet écran est
l'autre réponse : amener les photos et les vidéos qu'on veut garder vers un
stockage que cette maison possède — une partition de l'hôte Ubuntu, ou un
partage NAS — et ne libérer qu'ensuite la copie qui dort chez Apple.

L'ordre compte, et il est imposé par le code : **rien n'est jamais retiré
d'iCloud avant que le fichier ait été écrit ailleurs et que sa taille ait été
relue sur le disque.**

---

## 1. Ce que fait l'écran

Console ADMIN → **PHOTOS iCLOUD**.

| | |
|---|---|
| **Compteurs** | combien de photos, combien de vidéos, ce qu'elles pèsent, ce qu'il reste sur la destination |
| **Sélecteur** | une pellicule de miniatures — basculable en grille — avec des filtres (tout / non transférés / déjà stockés / photos / vidéos) |
| **Transfert** | les éléments cochés, ou tout ce qui manque encore, vers votre stockage |
| **Libération** | supprimer d'iCloud ce que le registre prouve stocké ici |
| **Stockage** | l'espace libre sur la destination, et l'agrandissement du volume qui la porte |

---

## 2. Le moteur : un seul `pip install`

Le bouton INSTALLER LE MOTEUR lance `pip install icloudpd`. Ce seul paquet livre
les deux moitiés dont cette fonction a besoin :

- **la commande `icloudpd`** — une boucle de téléchargement durcie contre Apple
  depuis des années : reprenable, consciente des limites de débit, et porteuse
  de `--keep-icloud-recent-days`, la seule option qui exprime toute cette
  fonction en une passe (télécharger, puis supprimer dans iCloud ce qui vient
  d'être stocké, sauf les N derniers jours) ;
- **le module `pyicloud_ipd`**, vendoré dans cette même distribution — la
  bibliothèque à laquelle la commande parle elle-même. L'importer donne l'accès
  élément par élément (un id, une taille, une miniature), que la ligne de
  commande ne sait pas exprimer : aucun drapeau icloudpd ne veut dire « ces 37
  éléments que j'ai cochés ».

Les deux chemins ne sont donc pas deux façons de faire la même chose — ce sont
les deux seules choses que chaque outil sait faire :

```
CHOISIR   une grille de miniatures, au cas par cas  ->  la bibliothèque
EN MASSE  tout ce qui manque encore en local        ->  la commande
```

Les deux écrivent dans la même arborescence (`<dest>/AAAA/MM/`) et le même
registre, et les deux reposent sur **une** session de confiance, dans **un**
répertoire de cookies. C'est cette session partagée qui impose `pyicloud_ipd`
plutôt que `pyicloud` tout court : les fichiers de session que lit icloudpd sont
ceux qu'écrit sa propre bibliothèque.

`pyicloud` est accepté comme repli pour le sélecteur. Sur une instance qui n'a
que lui, la grille marche et le bouton de masse explique pourquoi il est
indisponible.

> **Sur Home Assistant OS, une mise à jour du cœur remplace le conteneur et
> efface tout ce qui y a été installé par pip.** L'écran affichera alors
> *Moteur absent* — pressez à nouveau INSTALLER LE MOTEUR. Cette dépendance
> n'est volontairement **pas** dans `vssp/requirements.yaml` et **pas**
> installée par le déploiement : le manifeste couvre ce dont le centre de
> contrôle a besoin pour être dessiné, et une maison qui n'ouvre jamais cet
> écran n'a pas à porter quinze paquets transitifs.

---

## 3. Se connecter

**Utilisez le vrai mot de passe de l'identifiant Apple.** Les mots de passe
d'application d'Apple n'ouvrent que les services publiés CalDAV/IMAP ; la
photothèque n'en fait pas partie.

**Le mot de passe ne devient jamais une entité Home Assistant**, et c'est un
écart délibéré avec la façon dont le secret client Google d'à côté est traité.
Un `input_text` en `mode: password` ne fait que masquer la boîte dans
l'interface : la valeur, elle, vit dans la machine d'états, est écrite dans la
base du recorder, est diffusée par websocket à tout frontend connecté, et est
lisible par n'importe quel utilisateur Home Assistant et n'importe quelle
intégration. Un identifiant client OAuth Google le tolère — il est la moitié
d'une paire publique. Un mot de passe d'identifiant Apple ouvre les photos, les
sauvegardes, Localiser et le compte lui-même.

Il va donc du formulaire au webhook puis à un fichier 0600,
`/config/vssp/.icloud_password`, confié à l'écrivain en variable d'appel de
service, sans jamais entrer dans la machine d'états. Il est enveloppé en base64
au passage — non pour le secret mais pour le quoting : la valeur est interpolée
dans une commande shell entre apostrophes, et un mot de passe contenant une
apostrophe, un backtick ou `$(…)` serait sinon livré au shell comme du code.

### La seule étape non automatisable

Apple envoie un code à six chiffres vers vos appareils de confiance. Aucun
formulaire ne peut l'y lire, exactement comme OAuth est conçu pour que le
propriétaire du compte clique le consentement dans l'interface de Google.
Saisissez-le à l'étape 2 du formulaire intégré.

Une fois validée, la session est de confiance pour **deux mois environ** et rien
ne redemande — y compris chaque exécution d'`icloudpd`, qui la réutilise au lieu
de recevoir un mot de passe.

Exactement deux choses demandent un code à Apple : **CONNECTER**, parce que se
connecter est le moment où un code est censé arriver, et **ENVOYER UN NOUVEAU
CODE**, qui n'existe que pour ça. Valider un code n'en demande jamais — le faire
pendant l'appel même qui valide donne une invite sans fin : on tape un code, un
nouveau est demandé, celui qu'on a tapé est périmé, et ainsi de suite.

**ENVOYER UN NOUVEAU CODE** *annule celui qui est déjà sur votre téléphone* :
ne le pressez que si le premier est perdu ou expiré.

### « Aucun code n'arrive » n'est en général pas une panne

Apple envoie un code quand une connexion en a réellement besoin. Une fois la
session de confiance, CONNECTER répond `linked` immédiatement et rien n'est
envoyé — c'est la fonction qui marche, pas qui échoue. L'étape de vérification
dit dans laquelle des deux situations vous êtes, au lieu de laisser un champ
vide qui invite à attendre.

Un code manque vraiment seulement quand l'étape annonce qu'on en attend un et
que rien n'arrive. Alors :

### Aucun code n'arrive alors qu'on en attend un


Une session mémorisée n'est pas tout ou rien. Elle peut annoncer un compte lié
tout en étant périmée dessous — après un changement de mot de passe Apple, par
exemple — et comme la bibliothèque ne se réauthentifie alors jamais, Apple n'est
sollicité de rien et aucun code ne part. Presser CONNECTER n'y change rien.

**OUBLIER LA SESSION** est la sortie. Cela efface
`/config/vssp/.icloud_session` et rien d'autre — le mot de passe reste — pour
que le CONNECTER suivant soit une vraie connexion, suivie d'un code. Le bouton
est dans le formulaire et, délibérément, aussi sur la console elle-même, où il
continue de fonctionner si le formulaire intégré ne charge pas.

Pour la même raison, l'étape de vérification est toujours à l'écran au lieu
d'apparaître seulement quand l'état annonce qu'un code est requis : une étape
joignable seulement parfois est une impasse dès que cet état est périmé ou
faux.

Le code est pris par la bibliothèque plutôt que par `icloudpd --auth-only` pour
une raison pratique : icloudpd lit le code depuis une invite console ou une
interface web et n'a aucun drapeau pour s'en voir confier un, alors que la
bibliothèque a `validate_2fa_code()`. La session qui en sort est la même
session, dans le même répertoire.

---

## 4. Où vont les fichiers

| Champ | Signification |
|---|---|
| **Destination** | le chemin tel que *Home Assistant* le voit, p. ex. `/media/icloud` |
| **Chemin côté hôte** | le même endroit vu par l'*hôte Ubuntu*, p. ex. `/srv/photos` |

Une partition ou un partage NAS ajouté dans **Paramètres → Système → Stockage**
apparaît sous `/media` et n'exige aucune autre plomberie. Pour un NAS, c'est
tout — laissez le chemin côté hôte vide.

Le chemin côté hôte n'existe que pour le redimensionnement, et seul ce champ
peut le fournir : un bind mount masque sa propre origine, donc le conteneur ne
peut pas déduire quel chemin de l'hôte — et donc quel volume logique — se
trouve dessous.

Les fichiers atterrissent en `<dest>/AAAA/MM/<nom>`, exactement la forme
qu'écrit icloudpd avec `--folder-structure {:%Y/%m}` : les deux chemins
remplissent donc un seul arbre et non deux. Quand un nom est déjà pris, l'id de
l'élément est ajouté : Apple réutilise `IMG_0001.HEIC` d'une année et d'un
appareil à l'autre, et faire tomber deux photos différentes sur un même chemin
en perdrait une en silence.

---

## 5. Agrandir le volume

AGRANDIR LE VOLUME lance `lvextend -r -L +<taille>` sur l'hôte Ubuntu, par le
transport SSH de `vssp_infra_updates.py`, avec les identifiants déjà présents
dans le coffre sous `host_ssh`. Un **Vault scellé** répond donc « le coffre est
fermé » ici aussi — descellez-le d'abord (voir [Descellement](Unseal.fr.md)).

**Agrandissement seulement.** Rétrécir et repartitionner sont refusés
nommément, avec la raison :

- `lvextend -r` sur un volume monté est en ligne, journalisé et rattrapable en
  agrandissant encore — LVM et ext4/xfs le supportent tous deux pendant que les
  données servent ;
- rétrécir n'est rien de tout cela : xfs ne sait pas rétrécir, ext4 exige un
  démontage, et une erreur emporte la photothèque ;
- repartitionner est encore plus loin de ce qu'un bouton de dashboard devrait
  atteindre.

Une destination réseau n'est pas non plus agrandissable d'ici — un NAS
s'agrandit sur le NAS. L'écran dit dans quel cas il se trouve.

---

## 6. Libérer iCloud

Deux routes, qui toutes deux refusent de supprimer ce dont la présence ici n'est
pas prouvée.

**Au cas par cas** — cochez dans le sélecteur, puis RETIRER LA SÉLECTION
D'iCLOUD. La preuve est volontairement étroite : le registre nomme un chemin, ce
chemin existe, et sa taille sur disque égale la taille enregistrée au transfert.
Un élément qui échoue à l'un des trois est ignoré et compté, jamais supprimé.

**En masse** — activez **LIBÉRER iCLOUD APRÈS UN TRANSFERT DE MASSE** et réglez
**JOURS CONSERVÉS DANS iCLOUD** (30 par défaut), puis TOUT TRANSFÉRER. icloudpd
stocke chaque fichier puis le retire d'iCloud, en gardant ce qui tient dans la
fenêtre. La boîte de confirmation le dit, plutôt que de supposer l'interrupteur
remarqué.

Les éléments supprimés passent par *Supprimés récemment* chez Apple pendant 30
jours : il reste donc un filet en dessous — mais ne comptez pas dessus.

---

## 7. Une remarque sur les miniatures

Home Assistant sert `/config/www` en `/local/` **sans authentification** : tout
navigateur capable de joindre l'instance peut y lire un fichier s'il sait le
nommer. Le sélecteur a besoin de miniatures dans un navigateur, et une iframe
n'a aucun jeton Bearer à présenter : aucun chemin authentifié ne lui est
accessible.

Plutôt que de faire semblant que le répertoire est privé, les noms sont rendus
indevinables et le séjour court :

- chaque miniature se nomme `HMAC-SHA256(sel, id)[:32].jpg`, le sel vivant dans
  un fichier 0600 créé une fois par instance ;
- la miniature d'un élément transféré est effacée dès que le fichier atterrit ;
- seule la page regardée est matérialisée ;
- EFFACER LES MINIATURES vide le reste.

---

## 8. Fichiers

| Fichier | Rôle |
|---|---|
| `vssp/vssp_icloud.py` | le pont — liaison, scan, page, transfert, masse, libération, stockage, agrandissement |
| `home-assistant/packages/vssp_icloud.yaml` | helpers, commandes, capteurs, scripts, le webhook |
| `home-assistant/www/vssp/wizard/vssp_icloud.html` | le formulaire intégré et le sélecteur |
| `/config/vssp/icloud_index.json` | l'index de la photothèque (id, nom, type, taille, date) |
| `/config/vssp/icloud_ledger.json` | ce qui est stocké où — l'enregistrement qui autorise une suppression |
| `/config/www/vssp/icloud_status.json` | interrogé par les capteurs de la console et par le formulaire |
| `/config/www/vssp/icloud_page.json` | un écran de miniatures, réécrit à chaque défilement |
| `/config/vssp/icloud.log` | sortie des exécutions détachées |

Les actions longues (scan, transfert, masse, libération) se relancent détachées,
parce qu'un `shell_command` est tué à 60 secondes et qu'aucune d'elles n'est un
travail de 60 secondes. Un verrou par pid empêche deux d'entre elles de tourner
ensemble, et un verrou mort — le processus a disparu après un redémarrage de
conteneur — est repris plutôt que laissé à bloquer l'écran.

---

## 9. Dépannage

| Symptôme | Cause |
|---|---|
| *Moteur absent* | `icloudpd` n'est pas installé, ou une mise à jour du cœur l'a effacé. Pressez INSTALLER LE MOTEUR. |
| *Code requis* revient à chaque fois | Trois causes distinctes, et le message dit désormais laquelle : le code a été **refusé** (il est à usage unique — pressez ENVOYER UN NOUVEAU CODE et tapez celui qui arrive) ; le code a été **accepté mais la session n'est pas devenue de confiance** (vérifiez que `/config/vssp/.icloud_session` survit aux redémarrages, et que l'identifiant Apple n'a pas la Protection avancée des données) ; ou le **répertoire de session n'est pas inscriptible**, auquel cas chaque exécution démarre une nouvelle session et chaque code est périmé en arrivant. |
| Le bouton de masse est grisé | la **commande** `icloudpd` manque bien que le module soit là — seul le sélecteur marche. Pressez INSTALLER LE MOTEUR. |
| *icloudpd s'est arrêté avec le code … : session expirée* | la session de confiance a vieilli. Reconnectez-vous à l'étape 1 ; aucun mot de passe n'atteint la ligne de commande d'icloudpd. |
| Rien n'a été retiré d'iCloud | aucun des éléments cochés n'est au registre avec une taille concordante sur disque. Transférez-les d'abord. |
| *pas un volume logique LVM* | la destination n'est pas sur LVM, ou le chemin côté hôte est faux. Vérifiez `findmnt --target <chemin hôte>` sur l'hôte. |
| Le redimensionnement dit que le coffre est fermé | Vault se rescelle à chaque redémarrage par conception — voir [Descellement](Unseal.fr.md). |
| *n'est pas un stockage monté* | la destination aboutit au système de fichiers du conteneur. Il est inscriptible et vaste, et un redémarrage de pod ou une mise à jour du cœur le jette — les deux chemins de transfert le refusent donc. Ajoutez la partition ou le partage NAS dans Paramètres > Système > Stockage. |
| TOUT TRANSFÉRER est grisé alors qu'icloudpd est installé | la commande est là mais `pyicloud_ipd` n'est pas importable : le sélecteur tourne donc sur `pyicloud` tout court, et icloudpd ne sait pas lire la session avec laquelle cet écran s'est connecté. Le sélecteur fonctionne quand même. Réinstallez avec `pip install icloudpd` dans l'interpréteur qu'utilise Home Assistant, et vérifiez `python3 -c "import pyicloud_ipd"`. |
| La grille est vide | aucun index. Pressez ANALYSER LA PHOTOTHÈQUE ; la première passe sur une grande photothèque prend du temps et rend compte au fur et à mesure. |
