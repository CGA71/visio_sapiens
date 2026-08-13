# Intégration du patch `configuration.yaml` dans `.gitlab-ci.yml`

Trois modifications ciblées. Rien d'autre du pipeline ne change.

---

## 1. Arborescence du repo

Ajoute ces deux fichiers au dépôt :

```
home-assistant/
├── config-fragment.yaml          ← état désiré des clés vssp
└── vssp/
    └── vssp_apply_config.py  ← le patcher (à côté de tes autres scripts vssp/)
```

---

## 2. Job `build` — inclure le fragment + le script dans le paquet

Dans le job **`build`**, après la copie des dossiers (`cp -r ...`), ajoute :

```yaml
    # --- Patch configuration.yaml : embarque fragment + patcher ---
    - cp home-assistant/config-fragment.yaml       dist/config-fragment.yaml
    - mkdir -p dist/vssp
    - cp home-assistant/vssp/vssp_apply_config.py dist/vssp/
```

Le cache-busting `?v=` du build s'applique déjà aux `*.yaml` de `dist/` via le `find ... sed`
existant. Mais le fragment utilise le placeholder `__VTOKEN__` (pas `?v=X`), qu'on
remplacera au moment du `apply` avec `--vtoken`. **Ne le fais donc PAS passer dans le
sed de cache-busting** — laisse `__VTOKEN__` intact dans `dist/config-fragment.yaml`.

Si ton `find` risque de le toucher, exclus-le :
```yaml
    - find dist -name '*.yaml' ! -name 'config-fragment.yaml' -exec sed -i "s|...|...|g" {} +
```

---

## 3. `deploy:staging` (k3s) — appliquer le patch dans le conteneur

Dans **`deploy:staging`**, le bloc `kubectl exec ... tar xzf` déballe déjà le paquet dans
`/config/.osv_stage`. Juste APRÈS le déballage et AVANT le `hass --script check_config`,
insère l'application du patch :

```yaml
    - |
      kubectl exec -n $K3S_NAMESPACE $HA_POD -c $K3S_CONTAINER -- sh -c '
        set -e
        pip install ruamel.yaml --quiet 2>/dev/null || pip install ruamel.yaml --quiet --break-system-packages
        python3 /config/.osv_stage/vssp/vssp_apply_config.py \
          --config   /config/configuration.yaml \
          --fragment /config/.osv_stage/config-fragment.yaml \
          --vtoken   "'"$OSV_VERSION"'"
      '
```

Le `hass --script check_config` qui suit valide DÉJÀ le résultat, et le bloc de rollback
existant restaure `dashboards/themes`. Pour restaurer AUSSI `configuration.yaml` en cas
d'échec, ajoute au bloc de rollback existant :

```yaml
        # dans le "if ! ... check_config" de rollback, avant "exit 1" :
        LAST_BAK=$(ls -t /config/backups/configuration_*.bak 2>/dev/null | head -1)
        [ -n "$LAST_BAK" ] && cp "$LAST_BAK" /config/configuration.yaml && echo "[rollback] configuration.yaml restauré depuis $LAST_BAK"
```

---

## 4. `deploy:production` (HAOS/SSH) — idem via ssh

Dans **`deploy:production`**, après le bloc `ssh ha "set -e ... mv ..."` qui installe les
dossiers, et AVANT le `ha core check`, insère :

```yaml
    - |
      ssh ha "set -e
        pip install ruamel.yaml --quiet 2>/dev/null || pip install ruamel.yaml --quiet --break-system-packages 2>/dev/null || true
        python3 $HA_CFG/.osv_stage/vssp/vssp_apply_config.py \
          --config   $HA_CFG/configuration.yaml \
          --fragment $HA_CFG/.osv_stage/config-fragment.yaml \
          --vtoken   '$CI_COMMIT_TAG'"
```

> Note HAOS : le conteneur HA n'a pas toujours `pip` accessible. Deux options fiables :
> 1. **Recommandé** — n'utilise pas ruamel sur HAOS : fais tourner le patcher dans le
>    runner GitLab (image alpine avec python3+ruamel), en récupérant le fichier par SSH :
>    ```yaml
>    - apk add --no-cache py3-pip >/dev/null && pip install ruamel.yaml --quiet --break-system-packages
>    - scp ha:$HA_CFG/configuration.yaml /tmp/prod_config.yaml
>    - python3 dist/vssp/vssp_apply_config.py \
>        --config /tmp/prod_config.yaml \
>        --fragment dist/config-fragment.yaml \
>        --vtoken "$CI_COMMIT_TAG"
>    - scp /tmp/prod_config.yaml ha:$HA_CFG/configuration.yaml
>    ```
>    (La sauvegarde .bak est alors créée côté runner ; le `ha backups new --name pre-$CI_COMMIT_TAG`
>    déjà présent en début de job couvre le rollback complet côté HAOS.)
> 2. Installer ruamel dans le conteneur HAOS (moins propre, non persistant après update).

Le `ha core check` existant valide le résultat. Le bloc de rollback existant restaure
`dashboards/themes` ; le `rollback:production` manuel (restore backup HAOS `pre-$CI_COMMIT_TAG`)
couvre déjà `configuration.yaml` puisque le backup natif HAOS est complet.

---

## 5. Job `validate` — valider le fragment aussi (optionnel mais recommandé)

Dans **`validate`**, ajoute le fragment à la liste des fichiers vérifiés :

```yaml
    - test -f home-assistant/config-fragment.yaml || { echo "[ERR] config-fragment.yaml manquant"; exit 1; }
    - test -f home-assistant/vssp/vssp_apply_config.py || { echo "[ERR] patcher manquant"; exit 1; }
```

Le bloc Python de validation YAML existant couvre déjà `home-assistant/**/*.yaml`, donc
le fragment est syntaxiquement validé automatiquement.

---

## Résumé du comportement obtenu

| Situation | Résultat |
|---|---|
| 1er déploiement | Entrées vssp ajoutées à `configuration.yaml`, reste intact |
| Re-déploiement identique | `[OK] déjà conforme` — aucune écriture |
| Chemin/titre vssp changé dans le fragment | Mis à jour en prod, backup .bak créé |
| Dashboard/resource perso de l'utilisateur | **Toujours préservé** |
| Échec `ha core check` | Rollback dossiers + restauration du .bak / backup HAOS |
| Ressource vssp retirée du fragment | Conservée par défaut ; retirée si `--prune-resources` |
