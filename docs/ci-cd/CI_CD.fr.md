# Visio Sapiens — CI/CD, référence complète

**Français** · [English](CI_CD.md)

Document de référence du pipeline `.gitlab-ci.yml` **tel qu'il est réellement
dans le dépôt**, suivi des trous restants et de leurs correctifs.

Ce document intègre et remplace `CI_Integration.md`, qui ne décrivait qu'une
seule évolution antérieure (le patch de `configuration.yaml`) et utilisait
encore l'ancienne nomenclature `osvision/`. Un résumé de cette décision de
conception est conservé en fin de document, dans
[Historique de conception](#historique-de-conception--comment-on-en-est-arrivé-là).

---

## 1. Vue d'ensemble

Un paquet est construit **une seule fois** et déployé tel quel sur les deux
cibles ; seul le canal de transport change.

```
                          ┌──────────────┐
   MR / master  ─────────►│              │──► deploy:staging  (kubectl cp)  ──► k3s
                          │    build     │
   tag          ─────────►│  visio-      │──► deploy:production (ssh/scp)   ──► HAOS 18.1
                          │  sapiens.tgz │
                          └──────────────┘
```

| Stage | Jobs | Déclencheur |
|---|---|---|
| `validate` | `validate` | MR, `master`, tag |
| `build` | `build`, `package:hacs` | `build` : MR/master/tag · `package:hacs` : tag |
| `deploy` | `deploy:staging`, `deploy:production` | staging : MR/master · prod : tag + **gate manuelle** |
| `test` | `test:staging`, `test:production`, `rollback:production` | idem, rollback manuel |
| `release` | `release` | tag |

### Règle `workflow:` — le piège nº 1

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "master"
    - if: $CI_COMMIT_TAG
    - when: never
```

Un push sur `fix/*` ou `features/*` **sans MR ouverte ne lance aucun pipeline**.
C'est le premier réflexe de diagnostic quand « rien ne bouge en staging ».

### Variables versionnées (`variables:`)

`PACKAGE_NAME: visio-sapiens` · `K3S_NAMESPACE: homeassistant` ·
`K3S_CONTAINER: homeassistant` · `STAGING_URL: http://192.168.1.11:8123` ·
`HA_HOST: 192.168.1.26` · `HA_SSH_PORT: 22222` · `HA_SSH_USER: root` ·
`PROD_URL: http://192.168.1.26:8123` · `PROD_RESTART_CORE: "true"`

### Variables CI/CD à créer (Settings → CI/CD → Variables)

| Clé | Type | Options | Rôle |
|---|---|---|---|
| `HA_SSH_KEY` | File | Protected ✔ | clé privée vers HAOS |
| `HA_TOKEN_STAGING` | masquée | — | jeton longue durée k3s (restart + smoke test) |
| `HA_TOKEN_PROD` | masquée | — | jeton longue durée HAOS (smoke test) |
| `LIVEBOX_PASSWORD` | masquée | Masked ✔ | mot de passe admin Livebox |

> **Attention à l'option « Protected » sur `LIVEBOX_PASSWORD`.** Une variable
> protégée n'est exposée qu'aux branches et tags protégés. Or le staging se
> déploie depuis des MR sur `fix/*` / `features/*`, qui ne sont pas protégées :
> la variable sera systématiquement vide et le job affichera
> `[avert] LIVEBOX_PASSWORD absente`. En production (tags protégés) elle passe.
> Deux choix : décocher **Protected** (le secret devient lisible par tout
> committer autorisé à ouvrir une MR), ou accepter que les sondes Livebox
> restent en démonstration sur le staging. C'est un arbitrage, pas un bug.

---

## 2. Job `validate`

Image `alpine`, `python3 + py3-yaml`. Il vérifie, dans l'ordre :

1. **Structure** : `home-assistant/dashboards`, `home-assistant/templates`,
   `themes/visio_sapiens.yaml` (à la **racine**, imposé par HACS),
   `home-assistant/www/vssp`, `hacs.json`, `repository.yaml`.
2. **Patch config** : `home-assistant/config-fragment.yaml`,
   `vssp/vssp_apply_config.py`, `vssp/vssp_ensure_packages.py`,
   `vssp/vssp_sanitize_resources.py`.
3. **Sonde LAN** : `vssp/vssp_lan_probe.py`, `vssp/livebox.env`.
4. **Fuite de secret** : échoue si `vssp/.livebox.env` est versionné.
5. **Cohérence `OSV_PREFIX`** (non bloquant) : lit le préfixe dans
   `vssp_apply_config.py`, le compare aux clés `lovelace.dashboards` du
   fragment, et liste celles qui seraient ignorées.
6. **Thème unique** : échoue si `home-assistant/themes/` existe encore
   (source dupliquée avec `themes/` racine).
7. **Syntaxe YAML** de `home-assistant/**/*.yaml` + `themes/*.yaml`, avec un
   multi-constructeur qui accepte les tags HA (`!include`, `!secret`, …) sans
   les interpréter.

---

## 3. Job `build`

Produit `dist/`, image miroir de `/config` :

```
dist/
├── dashboards/            ← home-assistant/dashboards/. (dont views/, model/, templates_j2/)
│   └── templates/         ← home-assistant/templates/.   (cible des !include ../templates/)
├── themes/                ← themes/.  (racine)
├── www/                   ← home-assistant/www/.
├── packages/              ← home-assistant/packages/.
├── vssp/                  ← patchers + sonde LAN + livebox.env
├── config-fragment.yaml
└── OSVISION_VERSION
```

Points à connaître :

- **Cache-busting** : `find dist -name '*.yaml' ! -name 'config-fragment.yaml'`
  remplace `?v=…` dans les URL `/local/vssp/…`. Le fragment est **exclu** car il
  utilise le placeholder `__VTOKEN__`, substitué plus tard par `--vtoken`.
- **Contrôle des `!include`** : un script Python parcourt `dist/**/*.yaml` et
  vérifie que chaque cible d'`!include` / `!include_dir_*` existe **dans
  l'arborescence telle qu'elle sera sur `/config`**, pas dans le dépôt. C'est ce
  qui justifie la copie de `home-assistant/templates/` vers `dist/dashboards/templates/`.
- **Artefacts** : `visio-sapiens.tar.gz` + `.osv_version` (30 jours).

`package:hacs` (tags seulement) construit un paquet distinct, purement thème :
`themes/`, `hacs.json`, `repository.yaml`, `README.md`, `CHANGELOG.md`, `VERSION`.

### `vssp_mcp/` — déployé, mais pas exécuté par Home Assistant

`dist/vssp_mcp/` porte le paquet Python du [serveur MCP](../platform/MCP_Server.fr.md),
et les deux jobs de déploiement le copient dans `/config/vssp_mcp`. C'est la
seule chose du paquet que Home Assistant lui-même n'importe jamais : elle est
*stockée* sur l'instance et *lue* par le conteneur qui la sert — l'add-on
`vssp-mcp` sur Home Assistant OS, ou le pod k3s de `kubernetes/mcp/`.

C'est pourquoi il siège à côté de `vssp/` et non dedans. Tout ce qui est sous
`vssp/` est exécuté par Home Assistant, via des capteurs `command_line` et des
`shell_command`, et doit donc rester **stdlib + pyyaml** — une machine Home
Assistant OS n'est pas un endroit où l'on demande à un utilisateur de lancer
`pip install`. Le serveur MCP a besoin du SDK MCP, et l'obtient de son
conteneur. La règle n'a jamais été « aucune dépendance » mais « rien que
l'appareil doive installer pour toi », et cette séparation est ce qui la garde
absolue au lieu de la laisser devenir « stdlib, sauf quand ».

Livrer le code ainsi fait qu'une nouvelle version du serveur arrive par un
déploiement ordinaire — sans reconstruction d'add-on, sans image à pousser, et
sans rien qui exige un registre de conteneurs (ce GitLab n'en a aucun
d'activé).

Contrairement à `vssp/`, la copie est **en bloc, pas additive** :
`/config/vssp_mcp` est supprimé puis réécrit à chaque déploiement. Rien de
local n'y a sa place, donc un fichier supprimé du dépôt doit disparaître de
l'instance aussi.

---

## 4. Job `deploy:staging` (k3s)

Image `bitnami/kubectl`. Séquence réelle :

1. résolution du pod (`-l app=homeassistant`, repli sur le premier pod du namespace) ;
2. `kubectl cp` du paquet vers `/config/.osv.tar.gz` ;
3. `kubectl exec` : untar dans `/config/.osv_stage`, bascule
   `dashboards`/`themes` (avec `.old` de secours), remplacement de
   `/config/www/vssp`, copie des scripts `vssp/`, de `config-fragment.yaml`,
   `chmod +x` sur la sonde, copie **additive** de `packages/` ;
4. écriture du secret Livebox — le mot de passe est passé en **argument** du
   shell distant (`sh "$LIVEBOX_PASSWORD"` → `$1`), jamais dans la ligne de
   commande : invisible dans `ps` et dans les logs ;
5. vérification que `ruamel.yaml` s'importe sur le pod, installation
   (`pip install ruamel.yaml --break-system-packages`) sinon, et échec du
   job si l'import échoue toujours ensuite — nécessaire pour
   `vssp_apply_config.py` juste après, et pour `vssp_assign_apply.py` /
   `vssp_rooms_apply.py` plus tard à l'exécution ;
6. `vssp_apply_config.py` → `vssp_ensure_packages.py` → `vssp_sanitize_resources.py` ;
7. `hass --script check_config` ; en cas d'échec : restauration de
   `dashboards`/`themes` depuis `.old` **et** de `configuration.yaml` depuis le
   dernier `/config/backups/configuration_*.bak`, puis `exit 1` ;
8. nettoyage des `.old` / `.osv_stage` ;
9. **redémarrage de Home Assistant** : `POST /api/services/homeassistant/restart`
   avec `HA_TOKEN_STAGING`, repli sur `kubectl delete pod` si le token manque ou
   si le code HTTP n'est pas 200 ;
10. attente du retour de l'API (36 × 5 s) pour que `test:staging` ne parte pas sur
    une instance en cours de démarrage ;
11. **nouvelle résolution du nom du pod et nouvelle vérification de
    `ruamel.yaml`** : le repli `kubectl delete pod` de l'étape 9 recrée le
    pod depuis l'image, effaçant ce que l'étape 5 avait installé dans
    l'ancien. Revérifier contre le pod réellement en service maintenant
    (même logique installer-ou-échouer qu'à l'étape 5) permet de rattraper
    ce cas plutôt que de laisser `vssp_assign_apply.py` cassé sur un pod
    dont personne ne soupçonne qu'il vient de redémarrer ;
12. trace de la version réellement présente dans le conteneur.

L'étape 9 est indispensable : `lovelace.dashboards` et `homeassistant.packages`
ne sont **pas** rechargeables à chaud (voir [Troubleshooting.fr.md](Troubleshooting.fr.md)).

---

## 5. Job `deploy:production` (HAOS via SSH)

Tags uniquement, `when: manual`.

1. `HA_CFG` détecté (`/homeassistant` sinon `/config`) ;
2. `ha backups new --name pre-$CI_COMMIT_TAG` ;
3. paquet envoyé par `cat … | ssh ha "tar xzf -"` ;
4. même bascule de dossiers, plus la copie de `vssp_lan_probe.py` et
   `livebox.env` côté HAOS — obligatoire, puisque ce sont les capteurs
   `command_line` de HA qui l'exécutent (les patchers, eux, tournent dans le
   runner) ;
5. secret Livebox transmis par **stdin** (`printf … | ssh ha "cat > …"`) ;
6. patch de `configuration.yaml` **dans le runner** : `scp` du fichier,
   `vssp_apply_config.py` + `vssp_ensure_packages.py` +
   `vssp_sanitize_resources.py`, `scp` retour. Plus fiable que d'installer
   `ruamel.yaml` dans HAOS ;
7. `ha core check` ; en cas d'échec, rollback des dossiers + restauration du
   `configuration.yaml` pré-patch conservé côté runner ;
8. `ha core restart` (ou `ha core reload` si `PROD_RESTART_CORE != "true"`) ;
9. vérification que `ruamel.yaml` s'importe **à l'intérieur du conteneur
   Docker `homeassistant`** (`docker exec homeassistant python3 -c "import
   ruamel.yaml"`, atteignable directement depuis cette session SSH puisque
   le port 22222 de HAOS atterrit sur l'hôte avec accès Docker),
   installation sur place si besoin, et échec du job si l'import échoue
   encore — c'est un sujet différent de l'étape 6 (installation côté
   runner) : `vssp_assign_apply.py` et `vssp_rooms_apply.py` tournent à
   l'intérieur de HAOS à l'exécution, invoqués par le `shell_command` de HA
   lui-même, donc ce que possède le runner ne les atteint jamais ;
10. nettoyage.

`rollback:production` (manuel) retrouve le slug du backup `pre-$CI_COMMIT_TAG`
via `ha backups --raw-json` + `jq` et le restaure.

---

## 6. Tests de fumée

`.smoke_test` boucle jusqu'à 12 × 5 s sur `$TARGET_URL/api/` avec le jeton
correspondant, puis vérifie que le moteur JS et le moteur CSS sont servis, et
compte les entités `unavailable`.

---

# Ce qui manque encore — patchs à appliquer

Les cinq points suivants sont des trous réels du pipeline actuel. Les deux
premiers cassent quelque chose aujourd'hui.

---

## G1 — Les URL de ressources ne correspondent plus aux fichiers (corrigé : issue 124) 🟢

État constaté dans le dépôt :

| Déclaré dans `config-fragment.yaml` | Fichier réel |
|---|---|
| `/local/vssp/css/osvision.css` | `home-assistant/www/vssp/css/**vssp.css**` |
| `/local/vssp/js/osvision.js` | `home-assistant/www/vssp/js/**osvision.js**` |

Et dans `.smoke_test` :

```sh
curl -sfI "$TARGET_URL/local/vssp/js/vssp.js"    # ← ce fichier n'existe pas
curl -sfI "$TARGET_URL/local/vssp/css/vssp.css"  # ← celui-ci existe
```

La migration de nommage a renommé le CSS mais pas son URL, et l'URL du JS dans
le test mais pas le fichier. Conséquences : **le moteur CSS part en 404 à chaque
chargement de dashboard**, et le smoke test échoue sur le JS (`curl -sf … && echo`
retourne non-zéro, donc le job `test:staging` tombe en rouge).

**Correctif — deux lignes de renommage, puis un garde-fou.**

1. Choisir un nom et s'y tenir. Le plus cohérent avec le reste (`www/vssp/`,
   `/local/vssp/`, templates `vssp_*`) :

```sh
git mv home-assistant/www/vssp/js/osvision.js home-assistant/www/vssp/js/vssp.js
```

et dans `config-fragment.yaml` :

```yaml
    - url: /local/vssp/css/vssp.css?v=__VTOKEN__
      type: css
    - url: /local/vssp/js/vssp.js?v=__VTOKEN__
      type: module
```

> Le `sanitize_resources` déduplique par URL de base : les anciennes entrées
> `osvision.css` / `osvision.js` déjà présentes dans le `configuration.yaml` de
> prod ne seront **pas** retirées automatiquement. Passer une fois
> `--prune-resources`, ou les supprimer à la main.

2. Ajouter dans `validate` un contrôle qui rend ce genre d'écart impossible :

```yaml
    # Chaque resource /local/vssp/... du fragment doit exister dans www/vssp/
    - |
      python3 - <<'PY'
      import sys, os, yaml
      yaml.SafeLoader.add_multi_constructor('!', lambda l, s, n: None)
      with open('home-assistant/config-fragment.yaml', encoding='utf-8') as fh:
          frag = yaml.safe_load(fh) or {}
      res = ((frag.get('lovelace') or {}).get('resources') or [])
      err = 0
      for item in res:
          url = str((item or {}).get('url', ''))
          if not url.startswith('/local/vssp/'):
              continue
          rel = url[len('/local/vssp/'):].split('?')[0]
          path = os.path.join('home-assistant/www/vssp', rel)
          if not os.path.isfile(path):
              print(f"[ERR] resource {url}"); print(f"      -> {path} introuvable"); err = 1
      print("[OK] Toutes les resources /local/vssp/ existent" if not err
            else "[ERR] Resources Lovelace cassees")
      sys.exit(err)
      PY
```

3. Et faire lire les URL au smoke test au lieu de les coder en dur :

```yaml
    - |
      for u in $(grep -o '/local/vssp/[^ ?"'"'"']*' home-assistant/config-fragment.yaml | sort -u); do
        if curl -sfI "$TARGET_URL$u" >/dev/null; then
          echo "[OK] $u servi"
        else
          echo "[ERR] $u absent (404)"; exit 1
        fi
      done
```

---

## G2 — Le panneau ADMIN n'est jamais déployé (upgrade fix) 🟠

`build` ne copie que `vssp_apply_config.py`, `vssp_ensure_packages.py`,
`vssp_sanitize_resources.py`, `vssp_lan_probe.py` et `livebox.env`.

Ne partent donc **jamais** dans le paquet : `vssp_discovery.py`,
`vssp_upgrade.py`, `vssp_patch_dashboard.py`, `vssp_admin_config.yaml`. Les
boutons DISCOVERY / UPGRADE / GENERATE du panneau ADMIN appellent des
`shell_command` qui pointent sur `/config/vssp/vssp_*.py` — fichiers absents en
staging comme en production. Ils ne fonctionnent que si on les a déposés
manuellement.

**Patch `build`** — remplacer les `cp` unitaires par une copie de tout le dossier :

```yaml
    # Scripts vssp/ : patchers, sonde LAN, outils admin, generateur
    - mkdir -p dist/vssp
    - cp vssp/*.py   dist/vssp/
    - cp vssp/*.yaml dist/vssp/ 2>/dev/null || true
    - cp vssp/livebox.env dist/vssp/
    # Le secret ne doit jamais entrer dans le paquet
    - rm -f dist/vssp/.livebox.env
```

**Patch `deploy:staging`**, dans le `kubectl exec`, en remplacement des `cp`
unitaires vers `/config/vssp/` :

```sh
        mkdir -p /config/vssp
        cp /config/.osv_stage/vssp/*.py   /config/vssp/
        cp /config/.osv_stage/vssp/*.yaml /config/vssp/ 2>/dev/null || true
        cp /config/.osv_stage/vssp/livebox.env /config/vssp/
        chmod +x /config/vssp/*.py
```

**Patch `deploy:production`**, dans le bloc `ssh ha "set -e …"` :

```sh
        mkdir -p $HA_CFG/vssp
        cp $HA_CFG/.osv_stage/vssp/*.py   $HA_CFG/vssp/
        cp $HA_CFG/.osv_stage/vssp/*.yaml $HA_CFG/vssp/ 2>/dev/null || true
        cp $HA_CFG/.osv_stage/vssp/livebox.env $HA_CFG/vssp/
        chmod +x $HA_CFG/vssp/*.py
```

**Patch `validate`** — pour que le paquet ne reparte jamais sans eux :

```yaml
    - test -f vssp/vssp_discovery.py || { echo "[ERR] vssp/vssp_discovery.py manquant"; exit 1; }
    - test -f vssp/vssp_upgrade.py   || { echo "[ERR] vssp/vssp_upgrade.py manquant"; exit 1; }
```

> Voir aussi le point 5 de [Dashboard_Generator.fr.md](../dashboards/Dashboard_Generator.fr.md) : `vssp_admin_config.yaml`
> pointe sur `/config/home-assistant/dashboards/home.yaml`, chemin qui n'existe
> pas sur le pod (le déploiement met les dashboards en `/config/dashboards/`).
> La sauvegarde et la suppression sont donc actuellement des no-ops.

---

## G3 — Le générateur de dashboards n'est pas intégré au pipeline 🟠

`cp -r home-assistant/dashboards/.` embarque bien `model/` et `templates_j2/`
s'ils existent — donc le modèle et les templates arrivent sur `/config`. Mais :

- `vssp/generate_dashboards.py` n'est pas copié (couvert par G2 si le patch
  `cp vssp/*.py` est appliqué) ;
- **rien ne garantit que `views/energy.yaml` versionné correspond au modèle
  versionné.** Si quelqu'un édite `model/house.yaml` sans relancer le
  générateur, le dépôt part avec un dashboard périmé et le pipeline ne dit rien ;
- les fichiers d'aperçu (`*_preview.yaml`, `*.preview.yaml`,
  `preview_status.json`) partiraient en `dist/` s'ils étaient commités par
  mégarde.

**Patch `validate` — garde anti-dérive** (à placer après le contrôle de syntaxe) :

```yaml
    # Le dashboard genere doit correspondre au modele versionne
    - |
      if [ -f vssp/generate_dashboards.py ] && [ -f home-assistant/dashboards/model/house.yaml ]; then
        pip install jinja2 --quiet --break-system-packages 2>/dev/null || apk add --no-cache py3-jinja2 >/dev/null
        python3 vssp/generate_dashboards.py \
          --model     home-assistant/dashboards/model/house.yaml \
          --templates home-assistant/dashboards/templates_j2 \
          --out       /tmp/gen_views
        for f in /tmp/gen_views/*.yaml; do
          n=$(basename "$f")
          if ! diff -q "$f" "home-assistant/dashboards/views/$n" >/dev/null 2>&1; then
            echo "[ERR] views/$n differe de la generation depuis model/house.yaml"
            echo "      Relance : python3 vssp/generate_dashboards.py  puis commit"
            diff -u "home-assistant/dashboards/views/$n" "$f" | head -40
            exit 1
          fi
        done
        echo "[OK] Dashboards generes conformes au modele"
      else
        echo "[i] Generateur absent — controle de derive ignore"
      fi
```

**Patch `build` — ne jamais empaqueter un aperçu :**

```yaml
    - find dist -name '*_preview.yaml' -o -name '*.preview.yaml' -o -name 'preview_status.json' | xargs -r rm -f
```

**Patch `validate` — refuser un aperçu versionné :**

```yaml
    - |
      if git ls-files | grep -Eq '(_preview\.yaml|\.preview\.yaml|preview_status\.json)$'; then
        echo "[ERR] Des fichiers d'apercu sont versionnes. Ajoute-les au .gitignore."
        git ls-files | grep -E '(_preview\.yaml|\.preview\.yaml|preview_status\.json)$'
        exit 1
      fi
```

---

## G4 — Reliquats de nommage `OSVISION` (fix uprgade : issue 125)🟢

Le pipeline écrit toujours `dist/OSVISION_VERSION`, copié en
`/config/OSVISION_VERSION`. Les commandes de diagnostic qui lisent
`/config/VSSP_VERSION` échouent donc — ce n'est pas le paquet qui manque, c'est
le nom du fichier.

**Patch `build` :**

```yaml
    - |
      cat > dist/VSSP_VERSION <<EOF
      version=$OSV_VERSION
      commit=$CI_COMMIT_SHA
      ref=$CI_COMMIT_REF_NAME
      pipeline=$CI_PIPELINE_ID
      built=$(date -u +%Y-%m-%dT%H:%M:%SZ)
      EOF
    - cp dist/VSSP_VERSION dist/OSVISION_VERSION   # transition, a retirer plus tard
```

Puis dans les deux jobs de déploiement, copier `VSSP_VERSION` à côté de
l'existant, et basculer les `cat /config/OSVISION_VERSION` des traces et de la
doc. Retirer la ligne de transition une fois les deux cibles redéployées.

---

## G5 — Robustesse des jobs de déploiement 🟡

Trois ajouts qui ne changent rien au comportement nominal :

```yaml
deploy:staging:
  resource_group: staging      # jamais deux deploiements concurrents sur le meme pod
  interruptible: true          # une nouvelle MR annule le run precedent

deploy:production:
  resource_group: production
  interruptible: false
```

Et sur `.smoke_test`, remplacer les `curl … && echo` par une forme explicite
(voir G1) : aujourd'hui un 404 fait tomber le job sans message lisible.

---

## Ordre d'application recommandé

1. **G1** — renommage JS/CSS + contrôle `validate` (débloque le smoke test et le
   moteur CSS).
2. **G2** — copie de `vssp/*` (débloque le panneau ADMIN).
3. **G4** — `VSSP_VERSION` (rend les diagnostics exacts).
4. **G3** — garde anti-dérive du générateur, quand `model/` et `templates_j2/`
   seront versionnés.
5. **G5** — confort.

Chacun est indépendant et peut partir dans sa propre MR.

---

## Résumé du comportement obtenu (patch `configuration.yaml`)

| Situation | Résultat |
|---|---|
| 1er déploiement | Entrées `visio-sapiens-*` ajoutées, reste de `configuration.yaml` intact |
| Re-déploiement identique | `[OK] déjà conforme` — aucune écriture |
| Chemin/titre changé dans le fragment | Mis à jour, backup `.bak` créé |
| Dashboard/resource perso de l'utilisateur | **Toujours préservé** |
| Échec `check_config` / `ha core check` | Rollback dossiers + restauration du `.bak` / backup HAOS |
| Resource retirée du fragment | Conservée par défaut ; retirée avec `--prune-resources` |
| Ressource renommée (G1) | **Ancienne entrée conservée** tant qu'on ne prune pas |

---

## Historique de conception — comment on en est arrivé là

Avant que ce pipeline ne patche automatiquement `configuration.yaml`, les
entrées `lovelace.dashboards`, `lovelace.resources`, `input_text`,
`shell_command` et `template` requises par Visio Sapiens devaient être
fusionnées à la main dans le `configuration.yaml` de chaque cible — une étape
manuelle et sujette à erreur à chaque release. La conception d'origine a
introduit `home-assistant/config-fragment.yaml` (l'état désiré, dans
l'arborescence à la racine des scripts `vssp/`, pas sous `home-assistant/`)
et un patcher unique, `vssp_apply_config.py`, invoqué depuis `deploy:staging`
et `deploy:production` pour fusionner ce fragment dans le `configuration.yaml`
en place, de façon idempotente, avec un backup `.bak` à chaque écriture.

Deux scripts supplémentaires se sont ajoutés une fois ce patcher en
production, pour couvrir ce qu'il laisse volontairement de côté :

- **`vssp_ensure_packages.py`** — le patcher ne touche que `lovelace`,
  `input_text`, `shell_command` et `template` ; le domaine `homeassistant:`
  (et donc `packages: !include_dir_named packages`) est hors périmètre par
  conception, comme garde-fou. Ce script pose cette clé de façon idempotente.
- **`vssp_sanitize_resources.py`** — le patcher déduplique les `resources`
  par URL **complète**. Comme le jeton de cache-busting `?v=` change à chaque
  build, chaque déploiement ajoutait six entrées en double de plus. Ce script
  assainit la liste en dédupliquant par URL de base à la place.

Cette trace de décision — arborescence d'origine, diffs précis de `build`,
`deploy:staging`, `deploy:production` et `validate`, et justification du
choix de patcher `configuration.yaml` depuis le runner plutôt que d'installer
`ruamel.yaml` sur HAOS — vivait auparavant dans un document séparé,
`CI_Integration.md`. Ce document est désormais **remplacé** : tout ce qui y
restait d'actuel est intégré dans les sections 2 à 5 ci-dessus, et les trous
G1 à G5 qu'il signalait comme suite à donner sont suivis ici en totalité.
