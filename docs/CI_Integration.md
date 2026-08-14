# Intégration du patch `configuration.yaml` dans `.gitlab-ci.yml`

> **Statut : appliqué.** Les trois modifications décrites ici sont dans le
> pipeline courant, et deux scripts complémentaires s'y sont ajoutés depuis.
> Ce document est conservé comme trace de la décision de conception ; la
> référence à jour du pipeline complet est **`CI_CD.md`**.
>
> ⚠️ La version précédente de ce fichier utilisait l'ancienne nomenclature
> `osvision/osvision_apply_config.py`. Les chemins réels sont
> `vssp/vssp_apply_config.py` — corrigés ci-dessous.

---

## 1. Arborescence du repo ✅

```
home-assistant/
└── config-fragment.yaml            ← état désiré des clés Visio Sapiens

vssp/                               ← à la RACINE, pas sous home-assistant/
├── vssp_apply_config.py            le patcher
├── vssp_ensure_packages.py         pose la clé homeassistant.packages
└── vssp_sanitize_resources.py      déduplique les resources Lovelace
```

Les deux scripts complémentaires ne figuraient pas dans le plan initial :

- **`vssp_ensure_packages.py`** — le patcher ne gère que
  `lovelace`, `input_text`, `shell_command` et `template`. Le domaine
  `homeassistant:` (donc `packages: !include_dir_named packages`) sort de son
  périmètre, par garde-fou. Ce script pose la clé de façon idempotente.
- **`vssp_sanitize_resources.py`** — le patcher déduplique les `resources` par
  URL **complète**. Le `?v=` changeant à chaque build, chaque déploiement
  ajoutait 6 entrées de plus. Ce script assainit la liste en dédupliquant par
  URL de base.

---

## 2. Job `build` — inclure le fragment + les scripts ✅

```yaml
    # --- Patch configuration.yaml : embarque fragment + patchers ---
    - cp home-assistant/config-fragment.yaml dist/config-fragment.yaml
    - mkdir -p dist/vssp
    - cp vssp/vssp_apply_config.py       dist/vssp/
    - cp vssp/vssp_ensure_packages.py    dist/vssp/
    - cp vssp/vssp_sanitize_resources.py dist/vssp/
```

Le cache-busting `?v=` du build s'applique aux `*.yaml` de `dist/` via le
`find … sed`. Le fragment, lui, utilise le placeholder `__VTOKEN__` (et non
`?v=X`), remplacé au moment du `apply` avec `--vtoken` : il est donc **exclu**
du sed.

```yaml
    - find dist -name '*.yaml' ! -name 'config-fragment.yaml' \
        -exec sed -i "s|\(/local/vssp/[^ \"']*\)?v=[0-9A-Za-z._-]*|\1?v=${VTOKEN}|g" {} +
```

> **Évolution recommandée (G2 de `CI_CD.md`) :** remplacer ces `cp` unitaires
> par `cp vssp/*.py dist/vssp/`. En l'état, `vssp_discovery.py`,
> `vssp_upgrade.py` et `vssp_admin_config.yaml` ne partent jamais dans le
> paquet, et le panneau ADMIN est inerte sur les deux cibles.

---

## 3. `deploy:staging` (k3s) ✅

Les scripts sont d'abord installés à leur emplacement définitif
(`/config/vssp/`), puis exécutés depuis là — et non depuis `/config/.osv_stage`,
qui est effacé en fin de job :

```yaml
    - |
      kubectl exec -n $K3S_NAMESPACE $HA_POD -c $K3S_CONTAINER -- sh -c '
        set -e
        pip install ruamel.yaml --quiet 2>/dev/null || pip install ruamel.yaml --quiet --break-system-packages 2>/dev/null
        python3 /config/vssp/vssp_apply_config.py \
          --config   /config/configuration.yaml \
          --fragment /config/config-fragment.yaml \
          --vtoken   "'"$OSV_VERSION"'"
        python3 /config/vssp/vssp_ensure_packages.py    --config /config/configuration.yaml
        python3 /config/vssp/vssp_sanitize_resources.py --config /config/configuration.yaml
      '
```

Le `hass --script check_config` qui suit valide le résultat, et le bloc de
rollback restaure `dashboards`/`themes` **et** `configuration.yaml` :

```yaml
        LAST_BAK=$(ls -t /config/backups/configuration_*.bak 2>/dev/null | head -1)
        [ -n "$LAST_BAK" ] && cp "$LAST_BAK" /config/configuration.yaml \
          && echo "[rollback] configuration.yaml restaure depuis $LAST_BAK"
```

**Ajout ultérieur, indispensable :** le job se termine désormais par un
redémarrage de Home Assistant (service REST, repli sur recréation du pod) puis
une attente du retour de l'API. Sans lui, `configuration.yaml` était bien patché
mais jamais relu — voir `DIAGNOSTIC_staging.md`.

---

## 4. `deploy:production` (HAOS/SSH) ✅ — option 1 retenue

Le conteneur HAOS n'a pas toujours `pip` accessible. C'est l'option
« patcher côté runner » qui a été retenue, et elle est en place :

```yaml
    - apk add --no-cache python3 py3-pip >/dev/null
    - pip install ruamel.yaml --quiet --break-system-packages 2>/dev/null || pip install ruamel.yaml --quiet
    - rm -rf /tmp/osv_pkg && mkdir -p /tmp/osv_pkg && tar xzf $PACKAGE_NAME.tar.gz -C /tmp/osv_pkg
    - scp ha:$HA_CFG/configuration.yaml /tmp/prod_configuration.yaml
    - cp /tmp/prod_configuration.yaml /tmp/prod_configuration.yaml.pre   # filet local
    - |
      python3 /tmp/osv_pkg/vssp/vssp_apply_config.py \
        --config   /tmp/prod_configuration.yaml \
        --fragment /tmp/osv_pkg/config-fragment.yaml \
        --vtoken   "$CI_COMMIT_TAG"
    - python3 /tmp/osv_pkg/vssp/vssp_ensure_packages.py    --config /tmp/prod_configuration.yaml
    - python3 /tmp/osv_pkg/vssp/vssp_sanitize_resources.py --config /tmp/prod_configuration.yaml
    - scp /tmp/prod_configuration.yaml ha:$HA_CFG/configuration.yaml
```

Le `ha core check` valide ; en cas d'échec, les dossiers sont restaurés et le
`configuration.yaml` pré-patch est renvoyé par `scp`. Le
`ha backups new --name pre-$CI_COMMIT_TAG` de début de job couvre le rollback
complet, et `rollback:production` (manuel) sait le restaurer par son slug.

L'option 2 (installer `ruamel.yaml` dans le conteneur HAOS) reste écartée : non
persistante après update de l'image.

---

## 5. Job `validate` ✅ — et au-delà

Le fragment et les patchers sont vérifiés :

```yaml
    - test -f home-assistant/config-fragment.yaml    || { echo "[ERR] config-fragment.yaml manquant"; exit 1; }
    - test -f vssp/vssp_apply_config.py              || { echo "[ERR] patcher manquant"; exit 1; }
    - test -f vssp/vssp_ensure_packages.py           || { echo "[ERR] ensure_packages manquant"; exit 1; }
    - test -f vssp/vssp_sanitize_resources.py        || { echo "[ERR] sanitize_resources manquant"; exit 1; }
```

Le bloc Python de validation YAML couvre `home-assistant/**/*.yaml`, donc le
fragment est syntaxiquement validé automatiquement.

S'y sont ajoutés depuis : le contrôle de cohérence `OSV_PREFIX` ↔ clés du
fragment, l'interdiction de versionner `vssp/.livebox.env`, et le refus d'un
`home-assistant/themes/` dupliqué.

---

## Résumé du comportement obtenu

| Situation | Résultat |
|---|---|
| 1er déploiement | Entrées `visio-sapiens-*` ajoutées à `configuration.yaml`, reste intact |
| Re-déploiement identique | `[OK] déjà conforme` — aucune écriture |
| Chemin/titre changé dans le fragment | Mis à jour en prod, backup `.bak` créé |
| Dashboard/resource perso de l'utilisateur | **Toujours préservé** |
| Échec `check_config` / `ha core check` | Rollback dossiers + restauration du `.bak` / backup HAOS |
| Ressource retirée du fragment | Conservée par défaut ; retirée si `--prune-resources` |
| Clé de dashboard hors préfixe `visio-sapiens` | **Ignorée silencieusement** — `validate` l'affiche en avertissement |

---

## Suite

Les trous restants du pipeline (ressources Lovelace pointant sur des fichiers
inexistants, outils admin non déployés, générateur non intégré, fichier de
version encore nommé `OSVISION_VERSION`, verrous de concurrence) sont traités
dans **`CI_CD.md`**, sections G1 à G5.
