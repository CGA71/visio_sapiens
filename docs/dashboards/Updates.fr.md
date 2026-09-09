# Visio Sapiens — Mises à jour (ADMIN, écran MISES À JOUR)

**Français** · [English](Updates.md)

## Principe

Home Assistant connaît déjà chaque mise à jour en attente. Chacune est
une entité `update.*` qui porte `installed_version`, `latest_version`,
ses notes de version et un service d'installation. Réglages → Mises à
jour les liste — mais là seulement, et mélangées à tout le reste de ce
que fait cet écran.

L'écran MISES À JOUR n'ajoute **aucune source de données**. Il lit les
entités qui existent déjà et apporte la seule chose qu'un dashboard ne
peut pas deviner seul : la **répartition en trois familles**.

| Famille | Ce que c'est | Comment ça s'installe |
|---|---|---|
| **Système** | Home Assistant lui-même, le Supervisor, l'OS, les add-ons | une ligne à la fois |
| **Intégrations & cartes** | tout ce qui est installé via HACS | une ligne à la fois, **ou tout d'un coup** |
| **Micrologiciels** | `device_class: firmware` — un appareil physique | une ligne à la fois, jamais en masse |

Cette répartition est tout l'intérêt de l'écran. Réglages → Mises à jour
affiche le téléchargement d'une carte Lovelace et le flash d'une prise
murale comme la même sorte de ligne ; ce n'est pas la même sorte de
risque, et c'est la seule distinction qui décide si l'on clique sans
réfléchir ou si l'on lit d'abord les notes de version.

## Où vit chaque morceau

```
entités update.* (Home Assistant, déjà là)
        │
        ▼
packages/vssp_updates.yaml       4 capteurs — un décompte et une liste
        │                        d'entités par famille + un total
        ▼
templates_j2/admin.yaml.j2       l'écran MISES À JOUR affiche ces listes
```

La classification se fait **dans le package, pas dans le dashboard**.
Deviner que `update.browser_mod_update` appartient à HACS demande
`integration_entities()`, une fonction de template qui n'existe que du
côté Python — une carte Lovelace n'a pas d'équivalent. Les capteurs
publient donc chaque famille en attribut `entity_ids`, et les cartes
affichent la liste qu'on leur tend.

La famille système est définie par **soustraction** : tout ce qui n'est
ni HACS ni micrologiciel. C'est pourquoi le même fichier est juste sur
cette instance k3s (où il attrape le NAS) et sur une instance HAOS de
production (où il attrapera Core et les add-ons), sans retouche.

### Entités créées

| Entité | État | Attribut |
|---|---|---|
| `sensor.vssp_updates_pending` | total en attente | `entity_ids` |
| `sensor.vssp_updates_system` | en attente, système | `entity_ids` |
| `sensor.vssp_updates_hacs` | en attente, HACS | `entity_ids` |
| `sensor.vssp_updates_firmware` | en attente, micrologiciel | `entity_ids` |
| `script.vssp_updates_check` | — | ré-interroge chaque entité update |
| `script.vssp_updates_install_hacs` | — | installe toutes les mises à jour HACS |

Une mise à jour **ignorée** ne compte pas, et cela ne demande aucun
filtre : Home Assistant rapporte une telle entité à `off` tant que la
version ignorée reste la dernière. Ignorer depuis une ligne vide donc cet
écran exactement comme le fait l'installation.

## L'écran

**ÉTAT DES MISES À JOUR** — les quatre décomptes, d'un coup d'œil.

**À INSTALLER** — l'inventaire : chaque mise à jour en attente, groupée
par famille, avec les deux versions entre lesquelles elle se trouve
(`v3.2.2 → v3.2.3`). C'est ce qu'on lit avant de décider. Une famille
sans rien en attente affiche un tiret cadratin.

**Une carte par famille** — les lignes actionnables, et chaque carte est
absente quand sa famille est vide : une instance parfaitement à jour
n'affiche plus qu'un état et les commandes de maintenance.

Toucher une ligne ouvre **la boîte de dialogue de Home Assistant
lui-même** : notes de version, case de sauvegarde là où l'entité en
supporte une, Installer et Ignorer. Cette boîte vaut mieux que tout ce
que cette console pourrait reconstruire, donc la console ne la
reconstruit pas.

**MAINTENANCE** — deux boutons :

- **VÉRIFIER MAINTENANT** — les intégrations interrogent leur source à
  leur propre rythme (HACS environ toutes les heures), donc un écran vide
  signifie *rien trouvé la dernière fois qu'on a demandé*. Ce bouton
  transforme cela en *rien trouvé à l'instant*.
- **INSTALLER TOUTES LES INTÉGRATIONS & CARTES** — la seule installation
  groupée proposée.

### Pourquoi l'installation groupée s'arrête à HACS

Pas une limitation — une décision.

Une mise à jour HACS télécharge des fichiers et se défait en
réinstallant la version précédente depuis HACS. Une mise à jour de Core
ou d'un add-on, non, et elle veut la case de sauvegarde que sa propre
boîte propose — case qu'un appel groupé ne peut pas cocher,
`update.install` refusant `backup: true` sur toute entité qui n'annonce
pas le support BACKUP et faisant échouer l'appel entier pour une liste
mixte. Un flash de micrologiciel, lui, ne se défait par rien du tout.

Donc : HACS en masse, tout le reste depuis sa propre ligne.

Après une installation groupée HACS, une notification demande un
rechargement forcé (Ctrl+Maj+R). Une carte Lovelace remplacée sur le
disque reste l'ancien fichier dans le cache du navigateur, Home Assistant
ne le dit pas, et le symptôme — une carte qui continue de se comporter
comme la version qu'on vient de remplacer — se lit comme une mise à jour
ratée plutôt que comme un onglet périmé.

## Notes d'implémentation

**Ni iframe ni token.** Contrairement à PIÈCES & ÉTAGES, APPAREILS
DÉTECTÉS ou le COFFRE, cet écran est entièrement fait de cartes natives.
Une mise à jour est une entité `update.*`, les cartes natives atteignent
donc tout, et c'est la boîte de dialogue native qui agit.

**`custom:config-template-card` construit les lignes.** Une carte
`entities` ne sait pas filtrer : sa liste est figée dans du YAML écrit
des mois avant que la mise à jour n'existe. config-template-card évalue
une valeur qui commence par `${` et affecte ce qui revient — tableau
compris — donc la liste est lue depuis le capteur au moment du rendu.
Elle se re-rend quand une entité de son propre `entities:` change, d'où
le capteur de famille listé là, dont le décompte bouge dès qu'une
installation se termine.

Dans cette expression, la carte des états s'appelle **`states`** ; il n'y
a pas de `hass`. La garde `&& … || []` n'est pas de la superstition : le
capteur n'existe pas pendant les quelques secondes qui séparent un
redémarrage de la première passe de templates, et une carte entities à
qui l'on tend `undefined` lève au lieu de s'afficher vide.

**Les conditions énumèrent `unavailable` et `unknown` une par une.**
`state_not: "0"` seul est vrai pour les deux, donc sur une instance à
moitié démarrée la carte apparaîtrait, demanderait sa liste au capteur,
et n'obtiendrait rien.

**Deux moteurs de template sur la carte markdown.** Les trois libellés de
famille sont traduits par le *générateur* ; la boucle en dessous est
exécutée par *Home Assistant*. La frontière tombe entre les deux, la
balise `set` est donc émise en tant que texte — `{{ '{%' }}` est une
expression que le générateur évalue en deux caractères que Home Assistant
lira plus tard comme le début d'une balise. Une expression est de surcroît
insensible à `lstrip_blocks`, qui retire l'indentation devant une balise
de *bloc* — le piège dans lequel un bloc raw posé sur cette ligne serait
tombé tout droit, ramenant le template en colonne zéro et cassant le
YAML. Voir [Troubleshooting.fr.md](../ci-cd/Troubleshooting.fr.md) pour
la version de cette erreur qui est déjà partie en production une fois.

## Voir aussi

- [Dashboard_Generator.fr.md](Dashboard_Generator.fr.md) — le générateur,
  les slots et les langues
- [Backup_Retention.fr.md](../platform/Backup_Retention.fr.md) — ce qu'une
  sauvegarde avant mise à jour de Core retient réellement
