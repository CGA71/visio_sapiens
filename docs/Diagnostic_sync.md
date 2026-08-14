# Pourquoi les tableaux sont vides après le sync

## Ce que montrent vos captures

Bonne nouvelle d'abord : le dashboard **est** maintenant généré depuis
le template. Les messages « Aucun appareil detecte » et « Aucun circuit
detecte » sont ceux que le template affiche quand le modèle est vide —
un fichier écrit à la main ne les contiendrait pas. Les deux premiers
maillons (template + générateur) fonctionnent.

Ce qui manque : `model/energy_devices.yaml` n'a pas été écrit par le
scan.

## Pourquoi la notification annonçait 10 appareils

Elle affichait `sensor.vssp_appareils_mesures`, qui compte les entités
`*_power` exposées par Home Assistant — **pas** ce que le scan a réussi
à écrire. Vos 10 appareils existent bien dans HA (le selftest l'a
confirmé), mais le scan n'a pas pu produire le fichier. La notification
était donc trompeuse : c'est corrigé, elle compare désormais les deux
et annonce un échec explicite quand le modèle est vide.

Deuxième défaut corrigé : `continue_on_error: true` sur l'étape de scan
faisait que son échec passait inaperçu et que la génération s'exécutait
quand même — écrasant le dashboard avec un modèle vide. Retiré.

## Les trois commandes qui donnent la réponse

```sh
NS=homeassistant; POD=homeassistant-855dc8cb66-gbmvb; C=homeassistant

# 1. Le rapport du dernier scan (la cause y est écrite noir sur blanc)
sudo kubectl -n $NS exec $POD -c $C -- cat /config/www/vssp/energy_sync_status.json

# 2. Le modèle a-t-il été écrit ?
sudo kubectl -n $NS exec $POD -c $C -- ls -l /config/dashboards/model/

# 3. Le jeton est-il en place ?
sudo kubectl -n $NS exec $POD -c $C -- sh -c 'ls -l /config/vssp/.ha_token 2>&1; wc -c < /config/vssp/.ha_token 2>/dev/null'
```

## La cause la plus probable

Le message « Login attempt failed » que vous avez vu juste avant est le
symptôme : le `shell_command` transmet le jeton lu dans
`input_text.vssp_ha_token`, qui est vide. Le scan reçoit un jeton vide,
Home Assistant renvoie 401, le scan s'arrête sans rien écrire.

**Correctif immédiat** — créer le fichier jeton sur le pod :

```sh
sudo kubectl -n $NS exec $POD -c $C -- sh -c \
  'printf "%s" "VOTRE_NOUVEAU_JETON" > /config/vssp/.ha_token && chmod 600 /config/vssp/.ha_token'
```

Puis vérifier que le scan voit vos appareils, sans rien écrire :

```sh
sudo kubectl -n $NS exec $POD -c $C -- python3 /config/vssp/vssp_energy_sync.py \
  --dry-run --devices /config/dashboards/model/energy_devices.yaml
```

La sortie doit lister vos 10 appareils. Ensuite seulement, le bouton
SYNC ENERGY du panneau ADMIN écrira le modèle et régénérera les
tableaux.

**Attention** : le fichier `.ha_token` vit dans `/config/vssp/`, qui est
écrasé à chaque déploiement CI. Pour qu'il survive, utilisez plutôt le
script `vssp_save_token` (il recopie le helper vers le fichier après
chaque déploiement), ou déclarez le jeton dans `secrets.yaml`.

## Nouveaux capteurs de contrôle

Le package ajoute trois capteurs qui rendent ce diagnostic visible sans
ligne de commande :

| Capteur | Sens |
|---|---|
| `sensor.vssp_appareils_mesures` | appareils `*_power` exposés par HA |
| `sensor.vssp_modele_appareils` | appareils réellement écrits dans le modèle |
| `sensor.vssp_modele_circuits` | circuits écrits dans le modèle |
| `sensor.vssp_sync_resultat` | `ok`, `echec` ou `jamais_lance` |

Un écart entre les deux premiers signifie exactement ce que vous vivez :
Home Assistant connaît les appareils, mais le scan n'a pas pu les
écrire.
