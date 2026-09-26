# Prérequis — ce qu'une instance doit avoir avant qu'une version n'y atterrisse

[English](Prerequisites.md) · **Français**

La même livraison a produit une instance qui marche sur le pod de développement
et un écran blanc sur un Home Assistant OS fraîchement déployé. Le code était
identique — le générateur et les gabarits concordaient au bit près. Ce qui
différait, c'était tout ce que le déploiement n'avait jamais possédé.

Cette page est le contrat : ce qu'une instance doit avoir pour que le **centre
de contrôle** soit dessiné, comment le pipeline l'impose, et comment faire la
même chose à la main sur une instance qui n'a aucun pipeline.

---

## 1. La ligne : centre de contrôle, pas maison

Un prérequis est ce dont le **centre de contrôle** a besoin pour exister. Ce
n'est jamais un appareil connecté.

Une maison sans caméra, sans prise connectée et sans pièce déclarée doit quand
même recevoir un Visio Sapiens qui fonctionne — bandeau de navigation, en-tête,
console ADMIN, le tout. Les caméras et les thermostats viennent ensuite, depuis
la console ADMIN, et leur absence est signalée sans rien faire échouer.

Cette ligne traverse chacun des outils ci-dessous : `vssp_verify.py` échoue sur
un `sensor.vssp_*` manquant et pardonne une `camera.*` absente, et le manifeste
ne liste aucun appareil.

---

## 2. Le manifeste

[`vssp/requirements.yaml`](../../vssp/requirements.yaml) est la source unique de
vérité. Trois programmes le lisent, ils ne peuvent donc pas diverger :

| Programme | Quand | Ce qu'il fait |
|---|---|---|
| `vssp_preflight.py` | avant un déploiement | refuse une instance incapable d'héberger la livraison |
| `vssp_prepare.py` | quand le préflight refuse | installe ce qui peut l'être, nomme le reste |
| `vssp_dependencies.py` | depuis la console ADMIN | rapporte et installe, VÉRIFIER / INSTALLER |

Il contient quatre sections : la **version minimale de Home Assistant**,
**HACS**, les **cartes** (épinglées en `propriétaire/nom`, chacune marquée
bloquante ou non), les **intégrations** HACS, et les **intégrations natives**
livrées par Home Assistant.

**Bloquante** signifie que l'interface ne peut pas être dessinée du tout :
`button-card` porte chaque tuile, `card-mod` chaque style, `layout-card` chaque
mise en page, `browser_mod` les fenêtres de la console ADMIN. Tout le reste
alimente une carte, et son absence coûte cette carte, pas l'écran.

Les cartes sont épinglées en `propriétaire/nom` parce que deux dépôts peuvent
partager un nom de dossier : `kalkih/simple-weather-card` et
`I-Simen-I/simple-weather-card` finissent tous deux par `simple-weather-card`,
l'interface est écrite avec les options du fork, et une instance qui a reçu
l'autre ne dessinait rien là où la tuile météo devait être.

---

## 3. Dans le pipeline

```
validate → build → preflight → deploy → test
                       │                  └── verify:*   (après)
                       └── prepare:*      (manuel, quand le préflight refuse)
```

`preflight:staging`, `preflight:staging-haos` et `preflight:production`
interrogent la **cible**, pas le code. Chaque déploiement attend le sien : une
livraison n'atterrit jamais sur une instance incapable de l'héberger.
`prepare:*` est au même étage, manuel, parce qu'installer une douzaine de
dépôts tiers dans l'instance de quelqu'un est une décision, pas un effet de
bord d'un push.

Après le déploiement, `verify:*` contrôle ce qu'une personne regarderait :
chaque tableau de bord sert une configuration, chaque entité Visio Sapiens
existe, chaque ressource répond, le thème est sélectionné. Voir
[CI_CD.fr.md](../ci-cd/CI_CD.fr.md).

---

## 4. Sans pipeline, à la main

Une instance installée depuis HACS, ou toute maison sans runner, fait la même
chose avec les mêmes scripts. Ils ne parlent qu'au réseau, et le jeton est lu
dans l'environnement ou un fichier — jamais dans un argument, qui serait
visible dans la liste des processus de la machine.

**Sur l'instance** (add-on Terminal, ou le conteneur Home Assistant) :

```sh
export HA_TOKEN="<un jeton longue durée>"     # Profil > Sécurité
python3 /config/vssp/vssp_preflight.py --url http://localhost:8123
```

Il répond de deux façons. Soit `[OK] the instance can host the control centre`,
et vous déployez. Soit `[STOP]`, suivi de la liste exacte de ce qui manque et
de la raison pour laquelle chaque élément est nécessaire.

Puis :

```sh
python3 /config/vssp/vssp_prepare.py --url http://localhost:8123
```

Il installe les cartes et les ressources Visio Sapiens, crée les intégrations
natives dont l'installation ne demande aucune réponse de votre part —
Open-Meteo sur la zone du domicile, Date & heure, Moniteur système, un
calendrier local — et sélectionne le thème. Ajoutez `--city 13960` pour créer
aussi Météo-France, qui réclame une ville qu'aucun script ne peut deviner.

Relancez le préflight. Il doit maintenant répondre `[OK]`.

---

## 5. Ce qu'aucun script ne fera jamais

Quatre choses vous appartiennent, et les outils les nomment plutôt que de faire
semblant :

- **Installer HACS.** Son autorisation GitHub est un flux à code d'appareil lié
  à votre compte. Paramètres → Appareils et services → Ajouter une intégration
  → HACS. Sans HACS aucune carte ne pourra jamais être installée, et c'est
  pourquoi le préflight s'arrête là.
- **Créer un jeton longue durée.** Profil → Sécurité → Jetons d'accès longue
  durée. Les scripts côté instance en ont besoin ; écrivez-le dans
  `/config/vssp/.ha_token` en `0600`, ou collez-le dans la console ADMIN.
- **Appairer un appareil.** Le bouton du pont Hue, un mot de passe Synology, un
  code Apple TV. C'est la maison, pas le centre de contrôle.
- **Desceller le coffre.** Voir [Unseal.fr.md](Unseal.fr.md).

---

## 6. Après un premier déploiement

Deux choses qu'un déploiement ne peut pas décider à votre place :

- **Redémarrer une fois.** Le premier déploiement écrit le bloc
  `homeassistant.packages`, et un rechargement ne charge pas un bloc de
  packages qu'il vient de créer. Les entités apparaissent après un
  redémarrage.
- **Créer les tableaux de bord à la demande.** HOME, CORE et ENERGY partent
  absents, volontairement ; la console ADMIN a un bouton CRÉER pour chacun, ou
  une exécution du générateur avec `--only home,core,energy`.

Les deux sont signalés par `verify:*`, il n'y a donc rien à retenir.
