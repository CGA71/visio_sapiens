# Intégration TECHNICAL ROOM au repo `visio-sapiens`

Les livrables ont été réalignés sur la structure réelle du dépôt (packages HA,
dossier `vssp/`, `config-fragment.yaml`, pipeline GitLab). Quatre fichiers à
placer, deux fichiers existants à patcher.

---

## 1. Placement des fichiers

| Livrable | Destination dans le repo | Chemin final dans `/config` |
|---|---|---|
| `technical_room.yaml` | `home-assistant/dashboards/views/technical_room.yaml` | `dashboards/views/technical_room.yaml` |
| `technical_room_mobile.yaml` | `home-assistant/dashboards/views/technical_room_mobile.yaml` | `dashboards/views/technical_room_mobile.yaml` |
| `vssp_technical_room.yaml` | `home-assistant/packages/vssp_technical_room.yaml` | `packages/vssp_technical_room.yaml` |
| `vssp_lan_probe.py` | `vssp/vssp_lan_probe.py` | `/config/vssp/vssp_lan_probe.py` |

À déposer également : `home-assistant/www/vssp/backgrounds/technical.png`
(fond des deux vues). En attendant, `energy.png` ou `core.png` font l'affaire —
il suffit de changer l'URL dans le bloc `card_mod` final de chaque dashboard.

Le package est chargé tout seul : `config-fragment.yaml` pose déjà
`homeassistant: packages: !include_dir_named packages`. Aucun bloc à recopier
dans `configuration.yaml`, contrairement aux anciens `*_config_snippets.yaml`.

---

## 2. Patch `home-assistant/config-fragment.yaml`

Ajouter sous `lovelace: dashboards:`, après `visio-sapiens-energy-m` :

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
`energy.yaml` et `computer.yaml` pointe déjà vers `/visio-sapiens-technical/technical`,
et le chip **TECH** de `energy_mobile.yaml` vers `/visio-sapiens-technical-m/technical`.
Aucune navigation existante n'est à modifier — les liens morts deviennent vivants.

---

## 3. Patch `.gitlab-ci.yml`

**Job `validate`** — à côté des trois `test -f vssp/vssp_*.py` :

```yaml
    - test -f vssp/vssp_lan_probe.py || { echo "[ERR] vssp/vssp_lan_probe.py manquant"; exit 1; }
```

**Job `build`** — à côté des `cp vssp/vssp_*.py dist/vssp/` :

```yaml
    - cp vssp/vssp_lan_probe.py dist/vssp/
```

**Job `deploy:staging`** — dans le `kubectl exec`, à côté des autres `cp` vers
`/config/vssp/` :

```sh
        cp /config/.osv_stage/vssp/vssp_lan_probe.py /config/vssp/
        chmod +x /config/vssp/vssp_lan_probe.py
```

Le `hass --script check_config` existant validera le nouveau package, et le
contrôle des `!include` du job `build` reste satisfait : les deux dashboards
n'incluent que `../templates/button_card_templates.yaml` et
`../templates/decluttering_templates.yaml`, déjà présents dans `dist/`.

---

## 4. Identifiants Livebox

Créer `/config/vssp/.livebox.env` (chmod 600), non versionné :

```
LIVEBOX_HOST=192.168.1.1
LIVEBOX_USER=admin
LIVEBOX_PASSWORD=xxxxxxxx
LIVEBOX_IP_MODE=static
NETGEAR_PORTS=10
```

`LIVEBOX_IP_MODE=static` pilote le badge **IP FIXE** du dashboard. Ajouter la
ligne au `.gitignore` du repo.

Test manuel avant de brancher les capteurs :

```sh
kubectl exec -n <ns> <pod> -c <container> -- \
  python3 /config/vssp/vssp_lan_probe.py dhcp
```

---

## 5. Deux points relevés dans le repo

### 5.1 `OSV_PREFIX` empêche la fusion des dashboards

`vssp/vssp_apply_config.py` déclare :

```python
OSV_PREFIX = "vssp"
```

et fusionne les dashboards avec `_merge_named(dboards, src["dashboards"], only_prefix=OSV_PREFIX)`.
Or les clés de `config-fragment.yaml` sont `visio-sapiens`, `visio-sapiens-core`,
`visio-sapiens-energy`… — et `"visio-sapiens".startswith("vssp")` est faux.

**Conséquence : aucun dashboard du fragment n'est écrit dans `configuration.yaml`.**
Le commentaire du code dit d'ailleurs « merge par sous-clé, uniquement les vssp-* »,
ce qui correspond à l'ancienne convention `vssp-energy` visible dans
`vssp/energy_config_snippets.yaml` et dans les en-têtes de `core.yaml` / `energy.yaml`.
La migration de nommage a manifestement renommé les clés du fragment sans toucher
au préfixe du patcher.

Deux corrections possibles, l'une ou l'autre :

- `OSV_PREFIX = "visio-sapiens"` dans `vssp_apply_config.py` — la plus sûre, elle
  garde les URL actuelles et les `navigation_path` déjà déployés ;
- renommer les clés du fragment en `vssp-*` — mais il faudrait alors reprendre
  tous les `navigation_path` de `home.yaml`, `core.yaml`, `computer.yaml`,
  `energy.yaml`, `energy_mobile.yaml` et `home_mobile.yaml`.

`OSV_RESOURCE_MARK = "/local/vssp/"` est en revanche correct : les `resources`
du fragment sont bien fusionnées.

Mes deux entrées suivent la convention `visio-sapiens-*` du fragment : elles
seront donc posées dès que le préfixe sera corrigé, sans autre changement.

### 5.2 Le suffixe `_energie` a deux sens contradictoires

`packages/spvs_energy_totaux.yaml` somme tous les `*_energie` pour produire
`sensor.home_energy_total`, et sa note précise que ces capteurs doivent être des
compteurs **cumulatifs** — « n'y mets jamais un capteur déjà remis à zéro chaque
jour ». Mais `energy.yaml` et `energy_mobile.yaml` affichent ces mêmes
`sensor.technical_room_*_energie` sous l'en-tête **« Énergie (aujourd'hui) »**.

Les deux lectures ne peuvent pas être vraies en même temps. `vssp_technical_room.yaml`
tranche du côté de la règle du scan : les `*_energie` y sont des alias
`total_increasing` des compteurs Shelly, et les compteurs journaliers existent en
parallèle sous `*_energie_jour`. Pour afficher le jour dans les lignes d'appareils,
il suffit de remplacer dans les deux dashboards :

```yaml
energy_entity: sensor.technical_room_<appareil>_energie
# →
energy_entity: sensor.technical_room_<appareil>_energie_jour
```

Le même arbitrage vaut pour les 8 appareils du local technique déjà listés dans
`energy.yaml`, qui pointent aujourd'hui vers les `*_energie`.
