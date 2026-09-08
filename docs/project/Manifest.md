# Manifeste des livrables — où va chaque fichier

Récapitulatif de tout ce qui a été produit dans cette session, avec la
destination dans le repo et le chemin correspondant sur le pod.

## Scripts Python → `vssp/`

| Fichier livré | Destination repo | Chemin pod |
|---|---|---|
| `vssp_energy_sync.py` | `vssp/vssp_energy_sync.py` | `/config/vssp/vssp_energy_sync.py` |
| `generate_dashboards.py` | `vssp/generate_dashboards.py` | `/config/vssp/generate_dashboards.py` |
| `build_template.py` | `vssp/build_template.py` | *(outil de dev, non déployé)* |

⚠ Ces deux premiers ne partent sur le pod **que si** le job `build` du
CI les copie — voir `PATCH_gitlab-ci.md`, deux lignes à ajouter :

```yaml
    - cp vssp/generate_dashboards.py     dist/vssp/
    - cp vssp/vssp_energy_sync.py        dist/vssp/
```

Sans elles, `shell_command.vssp_energy_sync` appelle un fichier absent
et le bouton SYNC échoue silencieusement.

## Packages Home Assistant → `home-assistant/packages/`

| Fichier livré | Destination repo | Chemin pod |
|---|---|---|
| `vssp_admin.yaml` | `home-assistant/packages/vssp_admin.yaml` | `/config/packages/vssp_admin.yaml` |
| `vssp_energy_totaux.yaml` | `home-assistant/packages/vssp_energy_totaux.yaml` | `/config/packages/vssp_energy_totaux.yaml` |

Déjà copiés par le CI (`cp -r home-assistant/packages/. dist/packages/`).
`vssp_energy_totaux.yaml` remplace `spvs_energy_totaux.yaml` — supprimer
l'ancien, sinon les deux définissent `sensor.home_energy_total` et le
chargement échoue.

L'ancien `vssp/vssp_admin_config.yaml` est à supprimer : il était dans un
dossier que Home Assistant ne lit pas.

## Dashboards → `home-assistant/dashboards/`

| Fichier livré | Destination repo | Chemin pod |
|---|---|---|
| `home.yaml` | `home-assistant/dashboards/home.yaml` | `/config/dashboards/home.yaml` |
| `system_dashboards.yaml` | `home-assistant/dashboards/admin/system_dashboards.yaml` | `/config/dashboards/admin/system_dashboards.yaml` |
| `energy.yaml.j2` | `home-assistant/dashboards/templates_j2/energy.yaml.j2` | `/config/dashboards/templates_j2/energy.yaml.j2` |
| `house.yaml` | `home-assistant/dashboards/model/house.yaml` | `/config/dashboards/model/house.yaml` |
| `energy_devices.example.yaml` | *(exemple — le vrai fichier est généré par le sync)* | `/config/dashboards/model/energy_devices.yaml` |
| `energy.generated.yaml` | *(exemple de sortie — ne pas commiter)* | — |

Déjà couverts par le CI (`cp -r home-assistant/dashboards/. dist/dashboards/`),
donc `admin/`, `model/` et `templates_j2/` suivent automatiquement.

## Interface → `home-assistant/www/vssp/wizard/`

| Fichier livré | Destination repo | Chemin pod |
|---|---|---|
| `vssp_wizard.html` | `home-assistant/www/vssp/wizard/vssp_wizard.html` | `/config/www/vssp/wizard/vssp_wizard.html` |

## Configuration → `home-assistant/`

| Fichier livré | Destination |
|---|---|
| `config-fragment-preview.yaml` | à **fusionner** dans `home-assistant/config-fragment.yaml` (bloc `lovelace: dashboards:`) |

## Documentation → `docs/`

| Fichier livré | Destination |
|---|---|
| `Generator_templating.md` | `docs/Generator_templating.md` |
| `DEPLOY_ADMIN.md` | `docs/DEPLOY_ADMIN.md` |
| `ADMIN_TROUBLESHOOTING.md` | `docs/ADMIN_TROUBLESHOOTING.md` |
| `PATCH_gitlab-ci.md` | `docs/PATCH_gitlab-ci.md` (puis appliquer, puis supprimer) |
| `README.md` | racine du repo |

## Ordre de mise en place

1. `vssp/vssp_energy_sync.py` + `vssp/generate_dashboards.py`
2. Les deux lignes de `PATCH_gitlab-ci.md` dans le job `build`
   (+ `jinja2` dans `deploy:staging`)
3. `home-assistant/packages/vssp_admin.yaml` — et supprimer
   `vssp/vssp_admin_config.yaml`
4. `home-assistant/packages/vssp_energy_totaux.yaml` — et supprimer
   `spvs_energy_totaux.yaml`
5. `home-assistant/dashboards/` : `home.yaml`, `admin/system_dashboards.yaml`,
   `templates_j2/energy.yaml.j2`, `model/house.yaml`
6. `home-assistant/www/vssp/wizard/vssp_wizard.html`
7. Fusionner `config-fragment-preview.yaml` dans `config-fragment.yaml`
8. Déployer, **redémarrer Home Assistant**, vérifier les entités
   (voir `DEPLOY_ADMIN.md`)

## Contrôle rapide après déploiement

```sh
NS=home-assistant; POD=home-assistant-0; C=home-assistant

kubectl -n $NS exec $POD -c $C -- ls -l \
  /config/vssp/vssp_energy_sync.py \
  /config/vssp/generate_dashboards.py \
  /config/packages/vssp_admin.yaml \
  /config/dashboards/templates_j2/energy.yaml.j2 \
  /config/dashboards/model/house.yaml

# Le sync tourne-t-il ? (--dry-run n'écrit rien)
kubectl -n $NS exec $POD -c $C -- python3 /config/vssp/vssp_energy_sync.py \
  --token "VOTRE_JETON" --dry-run \
  --devices /config/dashboards/model/energy_devices.yaml
```

La seconde commande affiche directement les appareils détectés et le
diff — c'est le moyen le plus rapide de savoir si la chaîne fonctionne,
indépendamment de l'interface.
