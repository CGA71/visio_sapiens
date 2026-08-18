# Intégration TECHNICAL ROOM au repo `visio-sapiens`

> **Statut : l'intégration est faite.** Les fichiers sont en place, le fragment
> déclare les deux dashboards, le pipeline embarque la sonde LAN et le secret
> Livebox. Ce document devient une **fiche de référence** : ce qui est en place,
> comment ça marche, et les deux arbitrages qui restent ouverts.

---

## 1. Fichiers en place - projet VSSP

| Fichier | Chemin dans le repo | Chemin final dans `/config` | État |
|---|---|---|---|
| Vue desktop | `home-assistant/dashboards/views/technical_room.yaml` | `dashboards/views/technical_room.yaml` | ✅ |
| Vue mobile | `home-assistant/dashboards/views/technical_room_mobile.yaml` | `dashboards/views/technical_room_mobile.yaml` | ✅ |
| Package HA | `home-assistant/packages/vssp_technical_room.yaml` | `packages/vssp_technical_room.yaml` | ✅ |
| Sonde LAN | `vssp/vssp_lan_probe.py` | `/config/vssp/vssp_lan_probe.py` | ✅ déployée par la CI |
| Réglages box | `vssp/livebox.env` | `/config/vssp/livebox.env` | ✅ versionné |
| Secret box | *(généré au déploiement)* | `/config/vssp/.livebox.env` | ✅ variable CI/CD |

Reste à déposer : `home-assistant/www/vssp/backgrounds/technical.png` (fond des
deux vues). En attendant, `energy.png` ou `core.png` font l'affaire — il suffit
de changer l'URL dans le bloc `card_mod` final de chaque dashboard.

Le package est chargé tout seul : `config-fragment.yaml` pose
`homeassistant: packages: !include_dir_named packages`, et `deploy:*` copie
`packages/` de façon **additive** (les packages non-Visio Sapiens sont préservés).

---

## 2. Déclaration dans `config-fragment.yaml` ✅ appliquée

Présent dans le fragment, après `visio-sapiens-energy-m` :

```yaml
    visio-sapiens-technical:
      mode: yaml
      title: Technical Room
      icon: mdi:tools
      show_in_sidebar: false
      filename: dashboards/views/technical_room.yaml
    visio-sapiens-technical-m:
      mode: yaml
      title: Technical Room
      icon: mdi:cellphone-cog
      show_in_sidebar: false
      filename: dashboards/views/technical_room_mobile.yaml
```

Ces deux `url_path` ne sont pas choisis au hasard : la sidebar de `core.yaml`,
`energy.yaml` et `computer.yaml` pointe vers `/visio-sapiens-technical/technical`,
et le chip **TECH** de `energy_mobile.yaml` vers `/visio-sapiens-technical-m/technical`.
Aucune navigation existante n'a eu à être modifiée — les liens morts sont
devenus vivants.

Comme `OSV_PREFIX` vaut désormais `"visio-sapiens"`, ces deux entrées sont bien
écrites dans `configuration.yaml` par `vssp_apply_config.py`.

---

## 3. `.gitlab-ci.yml` ✅ patché

Les trois patchs sont dans le pipeline courant.

**`validate`** :

```yaml
    - test -f vssp/vssp_lan_probe.py || { echo "[ERR] vssp/vssp_lan_probe.py manquant"; exit 1; }
    - test -f vssp/livebox.env       || { echo "[ERR] vssp/livebox.env manquant"; exit 1; }
    - |
      if [ -f vssp/.livebox.env ]; then
        echo "[ERR] vssp/.livebox.env est versionne — il contient le mot de passe."
        echo "      git rm --cached vssp/.livebox.env  puis ajouter au .gitignore"
        exit 1
      fi
```

**`build`** :

```yaml
    - cp vssp/vssp_lan_probe.py dist/vssp/
    - cp vssp/livebox.env       dist/vssp/
```

**`deploy:staging`**, dans le `kubectl exec` :

```sh
        cp /config/.osv_stage/vssp/vssp_lan_probe.py /config/vssp/
        cp /config/.osv_stage/vssp/livebox.env      /config/vssp/
        chmod +x /config/vssp/vssp_lan_probe.py
```

**`deploy:production`**, dans le bloc `ssh ha` — la copie y est indispensable :
ce sont les capteurs `command_line` de HA qui exécutent la sonde, alors que les
patchers, eux, tournent dans le runner GitLab.

Le `hass --script check_config` valide le package ; le contrôle des `!include`
du job `build` reste satisfait, les deux dashboards n'incluant que
`../templates/button_card_templates.yaml` et
`../templates/decluttering_templates.yaml`, présents dans `dist/dashboards/templates/`.

---

## 4. Identifiants Livebox ✅ en place

Un seul élément est un secret : le mot de passe admin de la box. Tout le reste
(`LIVEBOX_HOST`, `LIVEBOX_USER`, `LIVEBOX_IP_MODE`, `NETGEAR_PORTS`) n'en est
pas un — le pipeline versionne déjà `HA_HOST: "192.168.1.26"` et
`STAGING_URL: "http://192.168.1.11:8123"`. Ces réglages vivent donc dans
`vssp/livebox.env` et se modifient par commit comme le reste.

Le mot de passe suit le mécanisme de `HA_SSH_KEY` et `HA_TOKEN_STAGING` : une
variable CI/CD masquée, écrite dans le conteneur au moment du déploiement.

| Clé | Valeur | Options |
|---|---|---|
| `LIVEBOX_PASSWORD` | mot de passe admin de la Livebox | Masked ✔ · Protected ✔ |

**⚠️ L'option Protected a un effet de bord sur le staging.** Une variable
protégée n'est exposée qu'aux branches et tags **protégés**. Le staging se
déploie depuis des MR sur `fix/*` / `features/*` : la variable y sera toujours
vide, le job affichera `[avert] LIVEBOX_PASSWORD absente` et les sondes
resteront en démonstration. C'est cohérent en production (tags protégés). Si
vous voulez des sondes vivantes en staging, décochez **Protected** — en sachant
que le secret devient alors lisible par tout committer capable d'ouvrir une MR.

### Comment le secret est transmis

Le pipeline ne met **jamais** le mot de passe sur une ligne de commande.

En staging, il est passé en argument du shell distant, donc récupéré via `$1` —
invisible dans `ps` et dans les logs :

```yaml
    - |
      if [ -z "$LIVEBOX_PASSWORD" ]; then
        echo "[avert] LIVEBOX_PASSWORD absente — sondes Livebox inactives."
      else
        kubectl exec -n $K3S_NAMESPACE $HA_POD -c $K3S_CONTAINER -- sh -c \
          'umask 077; printf "LIVEBOX_PASSWORD=%s\n" "$1" > /config/vssp/.livebox.env' \
          sh "$LIVEBOX_PASSWORD"
        echo "[OK] Secret Livebox deploye"
      fi
```

En production, il transite par **stdin** :

```yaml
    - |
      if [ -z "$LIVEBOX_PASSWORD" ]; then
        echo "[avert] LIVEBOX_PASSWORD absente — sondes Livebox inactives."
      else
        printf 'LIVEBOX_PASSWORD=%s\n' "$LIVEBOX_PASSWORD" \
          | ssh ha "umask 077; cat > $HA_CFG/vssp/.livebox.env"
        echo "[OK] Secret Livebox deploye"
      fi
```

Le garde-fou `if [ -z … ]` évite de casser le pipeline tant que la variable
n'existe pas : le déploiement passe, seules les sondes Livebox restent en
`unavailable`.

`.gitignore` doit contenir :

```
vssp/.livebox.env
```

Diagnostic ponctuel, sans rien modifier :

```sh
kubectl exec -n homeassistant <pod> -c homeassistant -- \
  python3 /config/vssp/vssp_lan_probe.py dhcp
```

---

## 5. Points relevés dans le repo

### 5.1 `OSV_PREFIX` ✅ corrigé

`vssp/vssp_apply_config.py` déclare maintenant `OSV_PREFIX = "visio-sapiens"`,
et `OSV_RESOURCE_MARK = "/local/vssp/"`. Les dashboards du fragment sont donc
bien fusionnés dans `configuration.yaml`. Le job `validate` affiche à chaque run
la liste des clés éventuellement ignorées, ce qui rend une régression visible
immédiatement.

L'alternative — renommer les clés du fragment en `vssp-*` — reste écartée : elle
obligerait à reprendre tous les `navigation_path` de `home.yaml`, `core.yaml`,
`computer.yaml`, `energy.yaml`, `energy_mobile.yaml` et `home_mobile.yaml`.

### 5.2 Le suffixe `_energie` a deux sens contradictoires ⚠️ toujours ouvert

`packages/spvs_energy_totaux.yaml` somme tous les `*_energie` pour produire
`sensor.home_energy_total`, et sa note précise que ces capteurs doivent être des
compteurs **cumulatifs** — n'y mettre jamais un capteur remis à zéro chaque jour.
Mais `energy.yaml` et `energy_mobile.yaml` affichent ces mêmes
`sensor.technical_room_*_energie` sous l'en-tête **« Énergie (aujourd'hui) »**.

Les deux lectures ne peuvent pas être vraies en même temps.
`vssp_technical_room.yaml` tranche du côté de la règle du scan : les `*_energie`
y sont des alias `total_increasing` des compteurs Shelly, et les compteurs
journaliers existent en parallèle sous `*_energie_jour`.

Pour afficher le jour dans les lignes d'appareils, remplacer dans les deux
dashboards :

```yaml
energy_entity: sensor.technical_room_<appareil>_energie
# →
energy_entity: sensor.technical_room_<appareil>_energie_jour
```

Le même arbitrage vaut pour les 8 appareils du local technique déjà listés dans
`energy.yaml`, qui pointent aujourd'hui vers les `*_energie`.

> Quand `energy.yaml` sera généré depuis `model/house.yaml` (voir
> `Generator_templating.md`), cette correction se fera **dans le modèle**, une
> seule fois, et se propagera aux deux vues à la génération suivante. Il peut
> être rentable d'attendre ce moment plutôt que de patcher les deux YAML à la
> main maintenant.

### 5.3 Fond `technical.png` manquant ⚠️ ouvert

Les deux vues référencent `/local/vssp/backgrounds/technical.png`, absent du
dépôt. Le rendu retombe sur un fond vide. Le contrôle de resources proposé en G1
de `CI_CD.md` ne couvre que les entrées `lovelace.resources` : les images
appelées en `card_mod` ne sont vérifiées par rien.
