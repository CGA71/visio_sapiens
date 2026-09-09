# Visio Sapiens — Planification (tableau INTERRUPTEURS)

**Français** · [English](Scheduler.md)

## Principe

Une icône d'horloge sur le titre du tableau **INTERRUPTEURS** d'une pièce
ouvre un popup où l'on dit :

- « éteins cette prise tous les soirs à 22h00 »
- « ouvre le volet samedi matin »
- « coupe la prise pendant quarante minutes »

Sans ouvrir l'éditeur d'automatisations, et sans quitter le dashboard de
la pièce.

## Les trois onglets

| Onglet | Ce qu'on saisit | Exemple |
|---|---|---|
| **Récurrent** | une heure + des jours | tous les lundis-vendredis à 22h00 |
| **Ponctuel** | une date + une heure | le 12 septembre à 18h30 |
| **Minuterie** | un nombre de minutes | dans 45 minutes |

## Les trois actions

| Action | Ce qui se passe |
|---|---|
| **Marche** | `homeassistant.turn_on` |
| **Arrêt** | `homeassistant.turn_off` |
| **Pause** | coupe, **puis rallume** après N minutes |

`homeassistant.turn_on` / `turn_off` servent tout le tableau sans branche
par domaine, parce que sur un volet ils signifient **ouvrir** et
**fermer**. Une lampe, une prise, un ventilateur et un volet passent donc
par le même appel.

**Pause** est un seul geste qui programme deux actions. Sa reprise n'est
pas un compte à rebours en cours d'exécution : c'est un second moment,
calculé et écrit au moment de l'enregistrement.

## Où vit chaque morceau

```
le popup            vssp_schedule.html
   │                (le formulaire, sans jeton)
   ▼ webhook vssp_schedule
packages/vssp_schedule.yaml
   │
   ▼ shell_command
vssp/vssp_schedule_apply.py     ← toute l'arithmétique de date vit ici
   │
   ▼
www/vssp/schedules.json          le magasin
   │
   ▼ capteur command_line
sensor.vssp_schedules
   │
   ▼ automatisation « battement », une fois par minute
homeassistant.turn_on / turn_off
```

### Pourquoi un webhook, et pas de vraies automatisations

Créer une véritable automatisation Home Assistant passe par l'API
authentifiée. Ce popup s'ouvre depuis le dashboard d'une **pièce**, sur
une tablette murale : demander de coller un jeton longue durée pour
programmer une lampe serait absurde. Le webhook n'exige aucun jeton et
`local_only: true` le maintient sur le réseau local — le même compromis
que font déjà `assign.html` et le chatbot.

Le prix à payer : ces règles n'apparaissent pas dans la liste des
automatisations de Home Assistant et n'ont pas de trace individuelle. La
seule automatisation visible est le battement.

### Pourquoi le battement est aussi bête

Le script Python réduit **chaque règle à des moments absolus** : une
heure murale plus des jours de semaine, ou un horodatage daté. Le côté
Home Assistant ne fait alors **aucun calcul de date**. Il se réveille une
fois par minute et compare des chaînes.

Ce que cela achète :

- **aucune minuterie à perdre au redémarrage.** Un redémarrage au milieu
  d'une pause est un non-événement : le moment de reprise a été écrit à
  l'enregistrement et il est toujours là.
- **aucun script en cours tenant un `delay`.** Un `delay` de trente
  minutes ne survit pas à un rechargement ; un horodatage dans un fichier,
  si.
- **une seule source de vérité.** Le fichier dit tout ; rien ne peut s'en
  désaccorder.

Le calcul le plus délicat est fait une fois, en Python, là où il se teste :
le **passage de minuit**. Une pause commencée à 23h50 pour 30 minutes
reprend à 00h20 le jour *suivant*, donc les jours de reprise sont les
jours de départ décalés d'un. S'y tromper, c'est un appareil qui reste
éteint jusqu'à ce que quelqu'un s'en aperçoive.

## Ce que le popup montre

**La liste des règles en place** pour ce tableau, avec sous chacune la
phrase reconstruite depuis les champs **stockés** — pas depuis ce qui a
été saisi. Ce que dit la liste est donc ce que lira le moteur.

Chaque règle porte deux boutons : **Suspendre** (la règle reste écrite
mais ne se déclenche plus) et **Supprimer**.

Une règle datée reste visible **24 heures** après son passage, grisée et
marquée *terminé* : rouvrir le popup pour vérifier que la règle d'hier
soir est bien passée est précisément ce qu'on fait. Ensuite l'élagage
quotidien la jette. Les règles récurrentes ne sont jamais élaguées.

## Détails qui comptent

**D'où viennent les noms.** Le générateur transmet au popup des
*identifiants* d'entités — c'est tout ce que contient le modèle de pièce.
Les noms lisibles sont cherchés dans `assign_data.json`, le fichier que
construit déjà l'assistant ASSIGN. Quand il manque, la page embellit
l'identifiant (`switch.prise_salon` → « Prise Salon ») plutôt que de ne
rien montrer.

**Quels appareils sont proposés.** Ceux du tableau dont le domaine figure
dans `ALLOWED_DOMAINS` — lumière, interrupteur, volet, ventilateur,
lecteur multimédia, booléen, climatisation, humidificateur, sirène. La
liste du template est tenue en phase avec celle du script : proposer un
appareil que le moteur refusera à l'enregistrement vaut moins que de ne
pas le proposer. Un tableau sans rien de planifiable reçoit un titre
simple, **pas d'horloge**.

**Collision dans la même minute.** Une pause qui reprend à 22h00 à côté
d'une règle qui allume le même appareil à 22h00 : `off` est appliqué en
premier, `on` en second. La collision se résout donc en faveur de
l'allumage. C'est une décision, pas un accident.

**Le moteur ne rattrape pas.** Une règle dont la minute est passée
pendant un redémarrage ne se déclenche pas en retard. Rattraper
imposerait de décider à partir de quand il est trop tard pour allumer les
lumières de quelqu'un, et personne ne veut voir une règle de 03h00 partir
à 07h00 parce que le pod a redémarré.

**Le magasin est lisible sur le LAN.** `schedules.json` vit sous
`/config/www` pour que le popup le relise sans jeton, et `/local` est
servi **sans authentification**. Il contient des identifiants d'entités
et des heures — aucun secret — mais le considérer comme lisible par tout
ce qui est sur le réseau local, exactement comme l'est déjà
`assign_data.json`. Voir [Security.fr.md](../platform/Security.fr.md).

**`browser_mod` est requis** (HACS), comme pour tout popup de ce projet.
Sans lui l'icône est inerte : elle s'affiche, elle prend le toucher, et
rien ne s'ouvre.

## Voir aussi

- [Dashboard_Generator.fr.md](Dashboard_Generator.fr.md) — le générateur,
  les tableaux et les langues
- [Updates.fr.md](Updates.fr.md) — l'autre écran qui planifie quelque
  chose, et pourquoi il s'y prend autrement
