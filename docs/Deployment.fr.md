# Déploiement de l'assignation des appareils

[English](DEPLOYMENT.md) · **Français**

Cette fonctionnalité ferme l'écart entre le scan de découverte et le
générateur de dashboards. Avant elle, le scan écrivait un rapport que
personne ne consommait et les `slots:` de `house.yaml` devaient être
remplis à la main.

```
DISCOVERY SCAN  ->  report.json          ce qui existe
prepare         ->  assign_data.json     ce qui existe + où c'est déjà
le formulaire   ->  webhook              où cela doit aller
apply           ->  house.yaml           la décision, enregistrée
le générateur   ->  dashboards/views/    la décision, rendue
```

## 1. Fichiers à déployer

| Fichier | État | MD5 |
|---|---|---|
| `vssp/vssp_assign_prepare.py` | nouveau | `ea6c388b9ddcb112cef95d763fc5b8ca` |
| `vssp/vssp_assign_apply.py` | nouveau | `72c5d285aaf67bdd2aecb5f06a27e57d` |
| `home-assistant/www/vssp/wizard/assign.html` | nouveau | `588a17009f7f62e0d3f5038d49d66c0a` |
| `home-assistant/packages/vssp_assign.yaml` | nouveau | `08e35fad6b341d12360e8a6354452830` |
| `home-assistant/dashboards/templates_j2/home.yaml.j2` | modifié | `58fc7fd57538f1545d61281d507cc6e1` |
| `home-assistant/dashboards/locales/en.yaml` | modifié | `ea2413cf43a88e8f7fa790690a4cfd9d` |
| `home-assistant/dashboards/locales/fr.yaml` | modifié | `4c0d2b1fd9f8b25b1d3bea48edd3cce5` |

Vérification avant commit :

```bash
md5sum vssp/vssp_assign_prepare.py vssp/vssp_assign_apply.py \
       home-assistant/www/vssp/wizard/assign.html \
       home-assistant/packages/vssp_assign.yaml \
       home-assistant/dashboards/templates_j2/home.yaml.j2 \
       home-assistant/dashboards/locales/en.yaml \
       home-assistant/dashboards/locales/fr.yaml
```

Les deux scripts Python vont dans `vssp/`, que le build copie en bloc —
rien à ajouter au pipeline. Le HTML doit être sous
`home-assistant/www/`, le seul répertoire que Home Assistant sert à un
navigateur, joignable sous `/local/`.

## 2. Prérequis déjà en place

| Quoi | Pourquoi | Contrôle |
|---|---|---|
| `packages/vssp_generation.yaml` | les sélecteurs langue et format que la vue ADMIN référence | `ls home-assistant/packages/vssp_generation.yaml` |
| `area_id` dans le modèle de pièce | permet à une entité découverte de proposer sa pièce | `grep -c area_id vssp/generate_dashboards.py` |
| `model/house.yaml` déclare des pièces | sinon il n'y a rien à quoi assigner les appareils | `grep -c "^  - id:" home-assistant/dashboards/model/house.yaml` |

Si `house.yaml` ne déclare aucune pièce, le formulaire le dit et refuse au
lieu d'afficher une liste déroulante vide.

## 3. Avant de déployer — deux contrôles

**Clés de packages en double.** Home Assistant refuse de démarrer quand
deux packages définissent la même clé :

```bash
grep -n "vssp_assign\|vssp_language\|vssp_format" home-assistant/packages/*.yaml
```

Chaque nom ne doit apparaître qu'une fois. Si `vssp_admin.yaml` en déclare
déjà un, n'en garder qu'une seule définition.

**ruamel.yaml sur le pod.** `vssp_assign_apply.py` réécrit `house.yaml` et
ne doit pas effacer les commentaires qui le documentent :

```bash
kubectl -n homeassistant exec <pod> -c homeassistant -- \
  python3 -c "import ruamel.yaml; print(ruamel.yaml.__version__)"
```

S'il manque :

```bash
kubectl -n homeassistant exec <pod> -c homeassistant -- \
  pip install ruamel.yaml --break-system-packages
```

Sans lui, le script s'arrête immédiatement avec un message clair — il ne
se rabat pas sur un écrivain qui perdrait les commentaires.

## 4. Déploiement

Committer et pousser sur `master`. Le pipeline valide, construit, déploie
sur le staging et redémarre Home Assistant. Un redémarrage est nécessaire
ici : la vue ADMIN gagne une carte, et `configuration.yaml` gagne le
package.

## 5. Vérification

```bash
# les scripts sont arrivés
ls -l /config/vssp/vssp_assign_*.py
# le formulaire est servi
curl -sI http://<ha>:8123/local/vssp/wizard/assign.html | head -1
# les entités existent (après redémarrage)
# Outils de développement > États : input_select.vssp_language, sensor.vssp_deployed_locale
```

Puis dans l'interface :

1. Console ADMIN > **DISCOVERY SCAN**. Il enchaîne maintenant le scan et la
   préparation du formulaire — un scan dont le formulaire ne peut pas lire
   le résultat ressemble à un scan qui n'a rien fait.
2. Le panneau **ASSIGNATION DES APPAREILS** liste les entités découvertes.
   Chacune arrive avec une pièce proposée depuis sa zone Home Assistant, et
   un tableau proposé depuis son `device_class`.
3. Ajuster, puis **Save and regenerate**.

Attends-toi à une longue liste : la découverte rapporte *toutes* les
entités de chaque zone, capteurs compris. Le champ de filtre et
l'assignation en masse — qui ne s'applique qu'aux lignes visibles —
existent pour cela.

## 6. Ce que chaque garde-fou refuse

| Situation | Comportement |
|---|---|
| Un tableau que la pièce n'a pas (un volet dans le jardin) | le formulaire ne le propose pas ; l'applicateur refuse le payload et n'écrit rien |
| Un appareil audio sans rôle `source` / `output` | refusé, rien d'écrit |
| Une pièce ou un tableau vide | l'entité est désassignée — c'est ainsi qu'on en retire une |
| Un payload malformé | refusé, une notification le signale |

Rien n'est jamais écrit à moitié : l'applicateur valide tout le payload
avant de toucher `house.yaml`, et le sauvegarde d'abord dans
`model/backups/`.

## 7. Relancer un scan

Un second scan ne réinitialise **pas** le travail précédent. Les entités
déjà assignées reviennent avec leur pièce et leur tableau
présélectionnés, marquées d'un liseré vert. C'était le risque principal de
cette conception, et il est testé.

## 8. Retour arrière

```bash
# le modèle
ls -t /config/dashboards/model/backups/ | head -3
cp /config/dashboards/model/backups/house_<horodatage>.yaml \
   /config/dashboards/model/house.yaml
# puis régénérer depuis la console ADMIN
```

Les dashboards eux-mêmes n'ont pas besoin de retour arrière : ils sont
générés, donc restaurer le modèle et régénérer suffit.
