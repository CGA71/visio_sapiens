# Diagnostic staging — pourquoi le fragment ne s'appliquait pas

> **Statut : les deux causes historiques sont corrigées dans le dépôt.**
> Ce document reste utile comme mémoire du symptôme (pipeline vert, staging
> inchangé) et surtout pour sa procédure de vérification, qui a été mise à jour
> et complétée avec les écarts encore ouverts.

---

## Cause 1 — `deploy:staging` ne redémarrait jamais Home Assistant ✅ corrigé

Séquence d'origine du job :

```
5.  kubectl cp du paquet
6.  untar + copie des dashboards / www / packages / vssp
7.  écriture du secret Livebox
8.  vssp_apply_config.py + ensure_packages + sanitize_resources
9.  hass --script check_config
10. nettoyage
11. echo "[OK] Staging a jour"          ← fin du job
```

`deploy:production` faisait `ha core restart` à l'étape équivalente ; le staging,
non. Or `configuration.yaml` n'est relu qu'au démarrage : `lovelace.dashboards`
et `homeassistant.packages` ne sont pas rechargeables à chaud. Le patcher
écrivait correctement, `check_config` validait, le job passait au vert — et
l'instance continuait de servir l'ancienne configuration. Comme les fichiers de
dashboard, eux, étaient bien remplacés sur disque, on obtenait l'effet trompeur
d'un déploiement « à moitié appliqué ».

**État actuel du `.gitlab-ci.yml`** — le job se termine désormais par :

1. `POST $STAGING_URL/api/services/homeassistant/restart` avec `HA_TOKEN_STAGING` ;
2. si le code HTTP n'est pas 200 (ou si le token est absent) : repli sur
   `kubectl delete pod` + `kubectl wait --for=condition=ready` ;
3. attente du retour de l'API (36 tentatives × 5 s, soit 3 min) pour que
   `test:staging` ne parte pas sur une instance en cours de démarrage ;
4. affichage de la version réellement présente dans le conteneur.

Le job se conclut par `[OK] HA redemarre et joignable`.

---

## Cause 2 — `OSV_PREFIX` empêchait l'écriture des dashboards ✅ corrigé

Le patcher filtrait les clés à fusionner :

```python
OSV_PREFIX = "vssp"                                   # ancien
_merge_named(dboards, src["dashboards"], only_prefix=OSV_PREFIX)
```

Les clés du fragment étant `visio-sapiens`, `visio-sapiens-core`,
`visio-sapiens-energy`…, et `"visio-sapiens".startswith("vssp")` valant `False`,
aucune entrée de `lovelace.dashboards` n'était jamais écrite. Les `resources`,
elles, sont fusionnées sans filtre de préfixe — d'où le fait que les mises à jour
visuelles passaient alors que les nouveaux dashboards n'apparaissaient pas.

**État actuel de `vssp/vssp_apply_config.py`** :

```python
OSV_PREFIX = "visio-sapiens"
OSV_RESOURCE_MARK = "/local/vssp/"
```

C'était l'option qui préserve les URL existantes et tous les `navigation_path`
déjà déployés. Le job `validate` embarque en plus un contrôle non bloquant qui
compare `OSV_PREFIX` aux clés du fragment et affiche
`[OK] N dashboard(s) du fragment couverts par OSV_PREFIX='visio-sapiens'`.

---

## Écarts encore ouverts (à traiter avant le prochain diagnostic)

Si le staging paraît toujours incomplet, ce ne sont plus les deux causes
ci-dessus. Les candidats actuels, détaillés dans `CI_CD.md` :

| # | Symptôme observable | Cause |
|---|---|---|
| G1 | Interface sans style, 404 sur `/local/vssp/css/osvision.css` ; `test:staging` rouge sur le JS | Les URL de `config-fragment.yaml` et celles du smoke test ne correspondent plus aux fichiers réels (`css/vssp.css`, `js/osvision.js`) |
| G2 | Boutons DISCOVERY / UPGRADE sans effet, `shell_command` en erreur | `vssp_discovery.py`, `vssp_upgrade.py`, `vssp_admin_config.yaml` ne sont pas copiés dans `dist/` |
| G4 | `cat /config/VSSP_VERSION` échoue alors que le déploiement a réussi | Le pipeline écrit encore `/config/OSVISION_VERSION` |
| — | Sondes Livebox en `unavailable` sur le staging uniquement | `LIVEBOX_PASSWORD` est marquée **Protected** : elle n'est pas exposée aux MR sur branches non protégées |

---

## Vérifier l'état réel de votre staging

```sh
POD=$(kubectl get pod -n homeassistant -l app=homeassistant \
      -o jsonpath='{.items[0].metadata.name}')

# 1. Quelle version le conteneur a-t-il reçue ?
#    (le pipeline écrit encore OSVISION_VERSION — voir G4 dans CI_CD.md)
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sh -c 'cat /config/VSSP_VERSION 2>/dev/null || cat /config/OSVISION_VERSION'

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

# 6. Les ressources déclarées existent-elles vraiment sur disque ? (cause G1)
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sh -c 'ls -l /config/www/vssp/css /config/www/vssp/js'
kubectl exec -n homeassistant $POD -c homeassistant -- \
  grep '/local/vssp/' /config/configuration.yaml

# 7. Les outils du panneau ADMIN sont-ils déployés ? (cause G2)
kubectl exec -n homeassistant $POD -c homeassistant -- ls -l /config/vssp/

# 8. Le secret Livebox est-il arrivé ?
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sh -c 'test -f /config/vssp/.livebox.env && echo present || echo absent'
```

### Lecture des résultats

- **1 affiche la bonne version, 2 ne montre pas les dashboards** → le patcher
  tourne et ignore les clés. Vérifier `OSV_PREFIX` (devrait être réglé).
- **2 montre bien les dashboards, mais l'interface ne les propose pas** → HA n'a
  pas redémarré. Confirmé par l'âge du pod en 4 (devrait être réglé).
- **1 affiche une version ancienne ou échoue** → soit le paquet n'est jamais
  arrivé, soit c'est le nom du fichier (G4). Côté pipeline : `workflow:` ne crée
  un pipeline que sur Merge Request, sur `master`, ou sur tag. Un push sur
  `fix/*` ou `features/*` sans MR ne lance **rien** — le cas est facile à manquer.
- **6 montre un fichier CSS/JS déclaré mais absent du disque** → G1. L'interface
  se charge sans identité visuelle, sans aucune erreur dans le log HA.
- **7 ne montre que les patchers et la sonde** → G2, le panneau ADMIN est inerte.
- **8 affiche `absent` sur le staging mais `present` en prod** → l'option
  **Protected** de `LIVEBOX_PASSWORD`, pas un bug de pipeline.

---

## Ordre d'application

1. ~~`OSV_PREFIX = "visio-sapiens"` dans `vssp/vssp_apply_config.py`~~ ✅ fait
2. ~~Redémarrage de HA dans `deploy:staging`~~ ✅ fait
3. Les correctifs G1 → G5 de `CI_CD.md`
4. Ouvrir une MR ou pousser sur `master` — sinon aucun pipeline ne part
