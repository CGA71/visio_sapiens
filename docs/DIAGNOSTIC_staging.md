# Pourquoi config-fragment.yaml ne s'applique pas en staging

Deux causes cumulées. La première suffit à produire exactement le symptôme
observé — pipeline vert, staging inchangé.

---

## Cause 1 — `deploy:staging` ne redémarre jamais Home Assistant

Séquence actuelle du job, dans l'ordre :

```
5.  kubectl cp du paquet
6.  untar + copie des dashboards / www / packages / vssp
7.  écriture du secret Livebox
8.  vssp_apply_config.py + ensure_packages + sanitize_resources
9.  hass --script check_config
10. nettoyage
11. echo "[OK] Staging a jour"          ← fin du job
```

`deploy:production` fait `ha core restart` à l'étape équivalente. **Le staging,
non.** Or `configuration.yaml` n'est relu qu'au démarrage : `lovelace.dashboards`
et `homeassistant.packages` ne sont pas rechargeables à chaud.

Conséquence : le patcher écrit correctement dans `/config/configuration.yaml`,
`check_config` valide le résultat, le job passe au vert — et l'instance continue
de servir l'ancienne configuration jusqu'au prochain redémarrage fortuit du pod.
Comme les fichiers de dashboard, eux, sont bien remplacés sur disque, on obtient
l'effet trompeur d'un déploiement « à moitié appliqué ».

**Corrigé** dans le `.gitlab-ci.yml` fourni : appel du service
`homeassistant.restart` via l'API REST, repli sur la recréation du pod si le
token est absent, puis attente du retour de l'API (jusqu'à 3 min) pour que
`test:staging` ne se lance pas sur une instance en cours de démarrage.

---

## Cause 2 — `OSV_PREFIX` empêche l'écriture des dashboards

Dans `vssp/vssp_apply_config.py` :

```python
OSV_PREFIX = "vssp"
```

```python
_merge_named(dboards, src["dashboards"], only_prefix=OSV_PREFIX)
```

Les clés du fragment sont `visio-sapiens`, `visio-sapiens-core`,
`visio-sapiens-energy`… et `"visio-sapiens".startswith("vssp")` vaut `False`.
**Aucune entrée de `lovelace.dashboards` n'est donc jamais écrite.**

Les `resources` (CSS/JS), elles, sont fusionnées sans filtre de préfixe — d'où
le fait que les mises à jour visuelles passent alors que les nouveaux dashboards
n'apparaissent pas.

**Correction, une ligne :**

```python
OSV_PREFIX = "visio-sapiens"
```

C'est l'option qui préserve les URL existantes et tous les `navigation_path`
déjà déployés. Renommer les clés du fragment en `vssp-*` obligerait à reprendre
la navigation de `home.yaml`, `core.yaml`, `computer.yaml`, `energy.yaml`,
`energy_mobile.yaml` et `home_mobile.yaml`.

---

## Vérifier l'état réel de votre staging

```sh
POD=$(kubectl get pod -n homeassistant -l app=homeassistant \
      -o jsonpath='{.items[0].metadata.name}')

# 1. Quelle version le conteneur a-t-il reçue ?
kubectl exec -n homeassistant $POD -c homeassistant -- cat /config/OSVISION_VERSION

# 2. Le patcher a-t-il écrit les dashboards ?
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sed -n '/^lovelace:/,/^[a-z]/p' /config/configuration.yaml

# 3. Le fragment déployé contient-il bien les nouvelles entrées ?
kubectl exec -n homeassistant $POD -c homeassistant -- \
  grep -A2 technical /config/config-fragment.yaml

# 4. Depuis quand le pod tourne-t-il ? (antérieur au déploiement = jamais redémarré)
kubectl get pod -n homeassistant $POD -o wide

# 5. Sauvegardes créées par le patcher, dans l'ordre chronologique
kubectl exec -n homeassistant $POD -c homeassistant -- \
  ls -lt /config/backups/ | head
```

Lecture des résultats :

- **1 affiche la bonne version, mais 2 ne montre pas les dashboards** → cause 2,
  le patcher tourne et ignore les clés.
- **2 montre bien les dashboards, mais l'interface ne les propose pas** → cause 1,
  HA n'a pas redémarré. Confirmé par l'âge du pod en 4.
- **1 affiche une version ancienne ou échoue** → le paquet n'est jamais arrivé :
  le pipeline ne s'est pas déclenché. Le `workflow:` ne crée un pipeline que sur
  Merge Request, sur `master`, ou sur tag. Un push sur `fix/*` ou `features/*`
  sans MR ne lance **rien** — le cas est facile à manquer.

---

## Ordre d'application

1. `OSV_PREFIX = "visio-sapiens"` dans `vssp/vssp_apply_config.py`
2. Le `.gitlab-ci.yml` fourni
3. Ouvrir une MR ou pousser sur `master` — sinon aucun pipeline ne part

Au run suivant, `validate` affichera `[OK] N dashboard(s) du fragment couverts
par OSV_PREFIX='visio-sapiens'` au lieu de la liste d'avertissements, et
`deploy:staging` se terminera par `[OK] HA redemarre et joignable`.
