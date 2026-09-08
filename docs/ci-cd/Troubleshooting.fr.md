# Visio Sapiens — Dépannage et post-mortems

**Français** · [English](Troubleshooting.md)

Ce document réunit quatre post-mortems de terrain : pourquoi le déploiement
semblait ne jamais atteindre le staging, pourquoi les tableaux ENERGY
restaient vides après une synchronisation annoncée comme réussie, pourquoi
toutes les pièces ont disparu de la navigation après un seul clic dans la
console, et pourquoi une modification de slot_set revenait en silence — plus
une FAQ de dépannage pour le panneau ADMIN. Chaque cas garde sa forme narrative —
symptôme, cause, correctif ou commandes de diagnostic — pour servir de
matière à un futur épisode « sessions de debug ».

---

## 1. Le déploiement n'atteint pas le staging

> **Statut : les deux causes historiques ci-dessous sont corrigées dans le dépôt.**
> Cette section reste utile comme mémoire du symptôme (pipeline vert, staging
> inchangé) et surtout pour sa procédure de vérification, qui a été mise à jour
> et complétée avec les écarts encore ouverts.

### Cause 1 — `deploy:staging` ne redémarrait jamais Home Assistant ✅ corrigé

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

### Cause 2 — `OSV_PREFIX` empêchait l'écriture des dashboards ✅ corrigé

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

### Écarts encore ouverts (à traiter avant le prochain diagnostic)

Si le staging paraît toujours incomplet, ce ne sont plus les deux causes
ci-dessus. Les candidats actuels, détaillés dans `CI_CD.md` :

| # | Symptôme observable | Cause |
|---|---|---|
| G1 | Interface sans style, 404 sur `/local/vssp/css/osvision.css` ; `test:staging` rouge sur le JS | Les URL de `config-fragment.yaml` et celles du smoke test ne correspondent plus aux fichiers réels (`css/vssp.css`, `js/osvision.js`) |
| G2 | Boutons DISCOVERY / UPGRADE sans effet, `shell_command` en erreur | `vssp_discovery.py`, `vssp_upgrade.py`, `vssp_admin_config.yaml` ne sont pas copiés dans `dist/` |
| G4 | `cat /config/VSSP_VERSION` échoue alors que le déploiement a réussi | Le pipeline écrit encore `/config/OSVISION_VERSION` |
| — | Sondes Livebox en `unavailable` sur le staging uniquement | `LIVEBOX_PASSWORD` est marquée **Protected** : elle n'est pas exposée aux MR sur branches non protégées |

### Vérifier l'état réel de votre staging

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

#### Lecture des résultats

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

### Ordre d'application

1. ~~`OSV_PREFIX = "visio-sapiens"` dans `vssp/vssp_apply_config.py`~~ ✅ fait
2. ~~Redémarrage de HA dans `deploy:staging`~~ ✅ fait
3. Les correctifs G1 → G5 de `CI_CD.md`
4. Ouvrir une MR ou pousser sur `master` — sinon aucun pipeline ne part

---

## 2. La synchronisation ENERGY n'écrit rien

### Ce que montrent vos captures

Bonne nouvelle d'abord : le dashboard **est** maintenant généré depuis
le template. Les messages « Aucun appareil detecte » et « Aucun circuit
detecte » sont ceux que le template affiche quand le modèle est vide —
un fichier écrit à la main ne les contiendrait pas. Les deux premiers
maillons (template + générateur) fonctionnent.

Ce qui manque : `model/energy_devices.yaml` n'a pas été écrit par le
scan.

### Pourquoi la notification annonçait 10 appareils

Elle affichait `sensor.vssp_appareils_mesures`, qui compte les entités
`*_power` exposées par Home Assistant — **pas** ce que le scan a réussi
à écrire. Vos 10 appareils existent bien dans HA (le selftest l'a
confirmé), mais le scan n'a pas pu produire le fichier. La notification
était donc trompeuse : c'est corrigé, elle compare désormais les deux
et annonce un échec explicite quand le modèle est vide.

Deuxième défaut corrigé : `continue_on_error: true` sur l'étape de scan
faisait que son échec passait inaperçu et que la génération s'exécutait
quand même — écrasant le dashboard avec un modèle vide. Retiré.

### Les trois commandes qui donnent la réponse

```sh
NS=homeassistant; POD=homeassistant-855dc8cb66-gbmvb; C=homeassistant

# 1. Le rapport du dernier scan (la cause y est écrite noir sur blanc)
sudo kubectl -n $NS exec $POD -c $C -- cat /config/www/vssp/energy_sync_status.json

# 2. Le modèle a-t-il été écrit ?
sudo kubectl -n $NS exec $POD -c $C -- ls -l /config/dashboards/model/

# 3. Le jeton est-il en place ?
sudo kubectl -n $NS exec $POD -c $C -- sh -c 'ls -l /config/vssp/.ha_token 2>&1; wc -c < /config/vssp/.ha_token 2>/dev/null'
```

### La cause la plus probable

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

### Nouveaux capteurs de contrôle

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

---

## 3. Toutes les pièces disparaissent de la navigation après une régénération

**Symptôme.** Les pièces étaient là. Un clic dans la console ADMIN —
RÉGÉNÉRER HOME, APPLIQUER AU BANDEAU, ou n'importe quel bouton
créer/régénérer d'une ligne du tableau — et le bandeau de navigation se
réduit à CORE, ENERGY et ADMIN. Aucune erreur, aucune notification.
*Paramètres > Tableaux de bord* de Home Assistant ne liste plus aucune
entrée `visio-sapiens-<pièce>`.

**Ce qui n'est PAS perdu.** Le **registre des zones** de Home Assistant —
la véritable source de vérité des pièces — est intact, étages compris.
Les affectations entité → zone aussi. Ce qui a disparu est généré : les
fichiers de vue des pièces et, surtout, `config-fragment-rooms.yaml`, le
fragment qui déclare ces dashboards à Home Assistant.

**Cause — celle qui comptait.** Un `card_mod` de l'écran CALENDRIER
lisait `design.palette.input_background`. Sous `StrictUndefined`, cela
lève dès que `design` est vide — et `design` **est** vide sur tout
lancement de dashboards : seule la commande `--only theme` passe
`--design-model`, et le défaut de cette option est un chemin relatif *au
dépôt*, qui se résout dans une copie de travail et jamais sur le pod. Le
crash était donc invisible à tout test local et certain sur l'instance :

```
admin.yaml.j2, line 870, in top-level template code
    --ha-color-form-background: {{ design.palette.input_background }};
jinja2.exceptions.UndefinedError: 'dict object' has no attribute 'palette'
```

Les dégâts sont sans commune mesure avec la cause. ADMIN est rendu en
**quatrième**, avant les dashboards de pièce et avant l'écriture du
fragment : l'exception interrompait donc chaque lancement au même point —
aucune vue de pièce générée, fragment jamais réécrit, aucun dashboard de
pièce déclaré. **Régénérer ne réparait rien : régénérer était ce qui
échouait**, et en silence du point de vue de la console, puisque la trace
n'existe que dans la stderr du shell_command.

C'est le signe distinctif de toute cette classe : *si régénérer ne change
strictement rien, c'est que le générateur ne va pas au bout.* Lire sa
stderr avant de croire à la moindre théorie sur le modèle.

**Cause — la latente trouvée en chemin.** Six `shell_command` de
`vssp_admin.yaml` (`vssp_create_home` / `vssp_regenerate_home` et les
mêmes paires pour core et energy) passaient `--rooms-fragment` **sans
`--rooms`**. Cela réécrit le fragment depuis le seul `rooms:` du modèle,
avec le même problème de défaut relatif au dépôt. Ce n'est pas la cause
de cet incident — `house.yaml` a gardé ses six pièces tout du long — mais
un clic sur RÉGÉNÉRER HOME face à une liste vide aurait produit les mêmes
dégâts à lui seul.

**Correctif.** Trois verrous :

1. Le template utilise
   `design.get('palette', {}).get('<token>', '<hex>')` avec des replis
   littéraux. Une seule valeur inatteignable dans un `card_mod` ne doit
   jamais pouvoir emporter les pièces avec elle.
2. Les neuf commandes `generate_dashboards.py` passent `--design-model`,
   et les six ci-dessus passent aussi
   `--rooms /config/dashboards/model/house_rooms.yaml`.
3. `generate_dashboards.py` **refuse** de réécrire un fragment de pièces
   en fragment vide quand le fichier existant en déclare — voir
   *Garde-fous* dans
   [Dashboard_Generator.fr.md](../dashboards/Dashboard_Generator.fr.md).
   `--allow-empty-rooms` y renonce pour le cas légitime « les pièces ont
   vraiment toutes disparu ».

**Un chemin par défaut relatif au dépôt n'est pas un défaut**, c'est une
commodité locale : il rend une panne propre au pod invisible à tout test
lancé depuis une copie de travail. Toute nouvelle option pointant vers de
l'état d'instance devrait n'avoir aucun défaut, pour qu'un appelant qui
l'oublie échoue bruyamment au lieu de lire silencieusement du vide.

**Récupération**, dans l'ordre — rien ici n'a besoin des fichiers perdus :

1. ADMIN > **PIÈCES & ÉTAGES**, coller un jeton longue durée, *Se
   connecter*. Le formulaire lit le registre des zones, qui contient
   encore toutes les pièces.
2. **Appliquer à Home Assistant** — cela réécrit `rooms:` dans
   `house.yaml` (`vssp_rooms_apply.py`).
3. ADMIN > **DASHBOARDS** > **RÉGÉNÉRER TOUT**. Les vues de pièce sont
   reconstruites et le fragment réécrit avec elles.
4. Recharger Lovelace. Si une URL de pièce reste en 404, le fragment est
   bien arrivé dans `configuration.yaml` mais Home Assistant n'a pas
   redémarré — voir le cas 1.

**Réflexe de diagnostic.** Avant de régénérer quoi que ce soit, regarder
ce que le fragment déclare :

```sh
NS=home-assistant; POD=home-assistant-0; C=home-assistant
kubectl -n $NS exec $POD -c $C -- cat /config/config-fragment-rooms.yaml
kubectl -n $NS exec $POD -c $C -- \
  grep -c "^  - id:" /config/dashboards/model/house.yaml
```

Un fragment sans aucune clé `visio-sapiens-<pièce>`, ou un modèle dont
`rooms:` est vide, c'est exactement ce cas.

## 4. FAQ du panneau ADMIN

### « script.vssp_… introuvable » / « Entité non trouvée »

Même cause dans les deux cas : le fichier de configuration ADMIN n'est
pas chargé par Home Assistant. Les entités `script.vssp_*`,
`input_text.vssp_*` et `binary_sensor.vssp_dashboard_*` n'existent donc
pas, et les boutons appellent des services inconnus.

**La solution la plus simple chez vous** : le fichier est livré comme
package, `home-assistant/packages/vssp_admin.yaml`. Votre CI copie déjà
`home-assistant/packages/.` vers `dist/packages/` → `/config/packages/`,
et `config-fragment.yaml` pose `packages: !include_dir_named packages`.
Il est donc chargé sans rien ajouter à `configuration.yaml`.

**Vérifier dans l'ordre :**

1. Le fichier est-il sur le pod ?
   `kubectl -n home-assistant exec home-assistant-0 -c home-assistant -- ls /config/packages/`
2. La clé de chargement est-elle en place ?
   `grep -A2 "^homeassistant:" /config/configuration.yaml`
   (elle est posée automatiquement par `vssp_ensure_packages.py`)
3. **Redémarrer Home Assistant.** Les `input_text` et `command_line`
   déclarés en YAML ne se rechargent pas à chaud. Pour les scripts seuls,
   Outils de développement → YAML → Recharger les scripts suffit.
4. Outils de développement → États, chercher `vssp` : les entités
   `script.vssp_run_energy_sync`, `binary_sensor.vssp_dashboard_energy_present`
   et `input_text.vssp_ha_token` doivent apparaître.

Si le fichier est bien dans `/config/packages/` mais que les entités
n'apparaissent pas, regarder Paramètres → Journaux : une erreur de
fusion (clé dupliquée avec un autre package) y est explicite.

### « Entité non trouvée » (bandeau jaune) — détail

Une carte référence une entité que Home Assistant ne connaît pas.

Sur la capture, c'est la carte `entities` de la zone DELETE, qui affiche
`input_text.vssp_pin_entry`. Le helper n'existe pas encore : les
`input_text` de `vssp/vssp_admin_config.yaml` ne sont pas chargés.

**Vérifier** — Outils de développement → États, chercher
`input_text.vssp_`. S'il n'y a aucun résultat :

1. Déposer `vssp_admin.yaml` dans `home-assistant/packages/` (voir
   section précédente), déployer, redémarrer.
2. Définir le code admin une fois : lancer le script
   `vssp_set_admin_pin` après y avoir mis votre vraie valeur.
3. Renseigner `input_text.vssp_ha_token` avec un jeton longue durée
   (Profil → Jetons d'accès longue durée) — sans lui, `vssp_discovery`
   et `vssp_energy_sync` s'exécutent avec un jeton vide.

**Note** : le helper `input_text.vssp_ha_token` manquait dans la version
précédente du fichier alors que `vssp_discovery` et `vssp_energy_sync`
l'utilisent. Il est maintenant déclaré — sans lui, ces commandes
tournaient avec un jeton vide.

`vssp_admin_pin`/`vssp_pin_entry` est actuellement le seul verrou
d'accès dédié de tout le projet, et il protège un bouton, pas la
console. Voir `docs/Security.fr.md` pour l'état actuel du contrôle
d'accès et la conception prévue de la reconnaissance faciale + code à
6 chiffres.

### « ButtonCardJSTemplateError » (bandeau rouge)

Un template JS de button-card a levé une exception. La cause la plus
fréquente : accéder à `.state` sur une entité absente.

```js
// ✗ lève une exception si l'entité n'existe pas
states['sensor.x'].state

// ✓ garde systématique
var s = states['sensor.x'];
return s ? s.state : 'valeur par defaut';
```

C'était le cas du bouton CORE, qui lisait
`binary_sensor.vssp_dashboard_core_present` sans garde. Corrigé dans
`admin/system_dashboards.yaml` : les deux blocs JS sont désormais gardés
et testés avec zéro entité disponible.

### Le bouton CRÉER ENERGY n'apparaît pas

Symptôme visible sur la capture : la section « Dashboards système »
n'affiche que SYNC ENERGY et CORE.

Les deux cartes conditionnelles testaient `state: "off"` et
`state: "on"`. Quand `binary_sensor.vssp_dashboard_energy_present`
n'existe pas, l'état n'est ni l'un ni l'autre : **aucun** des deux
boutons ne s'affichait — exactement dans la situation où l'on a besoin
du bouton CRÉER.

Corrigé : la condition d'affichage de CRÉER est passée à
`state_not: "on"`, qui couvre aussi l'entité absente, `unknown` ou
`unavailable`. Le garde-fou contre l'écrasement reste côté générateur
(`--if-missing`), pas côté interface — l'affichage d'un bouton ne doit
jamais être la seule sécurité.

Un bandeau de diagnostic apparaît par ailleurs dans la carte quand les
capteurs d'état sont indisponibles, pour signaler que la configuration
ADMIN n'est pas chargée plutôt que de laisser des boutons inertes.

### Les boutons s'affichent mais « ne font rien »

Les `shell_command` s'exécutent dans le conteneur Home Assistant. À
vérifier dans l'ordre :

1. **Les scripts Python sont-ils sur le pod ?**
   `ls /config/vssp/generate_dashboards.py /config/vssp/vssp_energy_sync.py`
   S'ils manquent : le job `build` ne les a pas copiés dans `dist/vssp/`.
   Il copie le répertoire en bloc (`cp -r vssp/. dist/vssp/`), donc un
   manque signifie que le fichier est absent du dépôt ou exclu — voir
   [CI_CD.fr.md](CI_CD.fr.md).
2. **Les dépendances sont-elles présentes ?** `python3 -c "import jinja2, yaml"`
   — sinon `pip install jinja2 pyyaml` dans le conteneur, ou ajouter la
   dépendance à votre image.
3. **Les dossiers cibles existent-ils ?**
   `mkdir -p /config/www/vssp /config/vssp/backups /config/home-assistant/dashboards/model`
4. **Le rapport JSON** dit le reste :
   `cat /config/www/vssp/energy_generate_status.json`
   (clé `errors` en cas de modèle invalide).

Les journaux de `shell_command` apparaissent dans
Paramètres → Journaux avec le code retour de la commande.

### Le dashboard est généré mais absent de la barre latérale

Le fichier existe (`binary_sensor.vssp_dashboard_energy_present` à `on`)
mais aucune entrée n'apparaît : c'est la déclaration Lovelace qui
manque, pas la génération. Vérifier le bloc `lovelace: dashboards:` de
`config-fragment.yaml` — `vssp-energy` doit pointer sur
`home-assistant/dashboards/views/energy.yaml`. Un redémarrage est
nécessaire après ajout d'une entrée (le rechargement à chaud ne suffit
que pour le contenu, pas pour la déclaration).

### Note sur les chemins du pod

Le CI déploie `home-assistant/dashboards/` vers **`/config/dashboards/`**
(et non `/config/home-assistant/dashboards/`), `home-assistant/packages/`
vers `/config/packages/`, `vssp/` vers `/config/vssp/` et
`home-assistant/www/` vers `/config/www/`.

Les chemins des `shell_command` sont alignés là-dessus :

| Dans le repo | Sur le pod |
|---|---|
| `home-assistant/dashboards/views/energy.yaml` | `/config/dashboards/views/energy.yaml` |
| `home-assistant/dashboards/model/house.yaml` | `/config/dashboards/model/house.yaml` |
| `home-assistant/dashboards/templates_j2/` | `/config/dashboards/templates_j2/` |
| `home-assistant/packages/vssp_admin.yaml` | `/config/packages/vssp_admin.yaml` |
| `vssp/generate_dashboards.py` | `/config/vssp/generate_dashboards.py` |

Les valeurs par défaut de `generate_dashboards.py` utilisent les chemins
du **repo** (pour un lancement depuis la racine du dépôt) ; les
`shell_command` passent les chemins du **pod** explicitement.

### « L'action script.vssp_… utilise l'action lovelace.reload qui n'a pas été trouvée »

`lovelace.reload` **n'existe pas** dans Home Assistant. Le domaine
`lovelace` n'expose qu'un seul service, `lovelace.reload_resources`, qui
recharge les ressources JS/CSS déclarées dans `lovelace.resources` — pas
les dashboards.

Home Assistant refuse d'exécuter un script dont une étape référence un
service inconnu : le script s'arrête à cette ligne, même si les étapes
précédentes ont réussi. C'est pour ça que le message apparaît alors que
la synchronisation, elle, s'est peut-être bien déroulée.

**Corrigé** : les appels ont été retirés de `vssp_admin.yaml` et de
`vssp_energy_totaux.yaml`.

**Pourquoi rien ne les remplace** : un dashboard en mode YAML est relu
automatiquement. Home Assistant met la configuration en cache avec la
date de modification du fichier et la recharge dès que celle-ci change.
Le seul cache restant est celui du navigateur pour l'onglet déjà ouvert
— d'où l'invitation à faire Ctrl+Maj+R dans les notifications.

Ce qui nécessite en revanche un vrai redémarrage, c'est l'ajout d'une
**entrée** de dashboard dans `lovelace: dashboards:` — pas la
modification de son contenu.

#### Vérifier qu'un service existe avant de l'appeler

Outils de développement → Actions : le sélecteur ne propose que les
services réellement enregistrés. Taper `lovelace.` n'y fait apparaître
que `reload_resources`, ce qui confirme le diagnostic en deux secondes.

## 5. slot_set / default_slot (ou une sauvegarde ASSIGN / THEME) revient en silence

### Ce que ça donne

Vous choisissez un `slot_set` et un `default_slot` pour une pièce dans
PIÈCES & ÉTAGES (ou une assignation dans ASSIGNATION DES APPAREILS, ou
une couleur dans THEME), vous cliquez sur Appliquer/Enregistrer, vous
voyez le message de succès habituel — et quand vous revenez sur la
page plus tard, le champ est revenu à `default` / `(automatique)`
comme si rien n'avait jamais été enregistré. Aucune erreur nulle part.

### Reproduit en direct, pas deviné

Ceci a été retrouvé en pilotant réellement l'iframe PIÈCES & ÉTAGES
(une session Playwright avec un vrai jeton longue durée), en
interceptant l'appel `fetch()` vers `/api/webhook/vssp_rooms_sync`, et
en décodant le payload base64 envoyé : il était **correct** —
`{"area_id":"entrance_hall","slot_set":"entrance","default_slot":"security", ...}`.
`house.yaml` montrait quand même toujours `slot_set: default` ensuite.
Le client n'était donc jamais le problème — tout ce qui se passe après
le webhook devait être vérifié.

### La commande qui donne la réponse

```sh
sudo kubectl -n homeassistant exec $POD -- true   # (verification d'acces)
```

Puis, depuis la console du navigateur (ou toute session authentifiée),
lister les exécutions récentes de l'automatisation et regarder
`script_execution` :

```js
await hass.callWS({ type: 'trace/list', domain: 'automation',
                     item_id: 'vssp_receive_rooms_sync' });
```

Une exécution avec `"script_execution": "failed_single"` est la preuve
irréfutable : l'automatisation n'a même jamais démarré pour ce
déclenchement.

### La cause

`vssp_receive_rooms_sync` (et le même motif identique dans
`vssp_receive_assignment` et `vssp_receive_theme`, les trois dans
`home-assistant/packages/`) utilisait `mode: single`. Chacune de ces
automatisations declenchées par webhook fait un vrai travail —
`vssp_rooms_apply.py` + `vssp_generate_dashboards` +
`vssp_assign_prepare` pour les pièces, environ 4-5 secondes de bout en
bout.

La page PIÈCES & ÉTAGES déclenche le même webhook depuis **trois**
endroits : `connect()` (au chargement de la page), `reload()`, et la
propre synchronisation post-Appliquer de `applyDiff()`. Ouvrez la page
et cliquez sur Appliquer peu après (ou gardez-la ouverte dans deux
onglets) et deux POST arrivent rapprochés. Avec `mode: single`, quelle
que soit la requête encore en cours quand la seconde arrive l'emporte ;
la seconde est purement et simplement rejetée — et **le point d'entrée
webhook lui-même répond quand même HTTP 200** dans les deux cas, donc
le navigateur affiche son avis « appliqué » habituel que
l'automatisation ait réellement tourné ou non. En pratique, le perdant
est souvent la vraie modification de l'utilisateur : la synchronisation
au moment du connect() de la page (envoyée avec ce qui était affiché
*avant* la modification) peut très bien tourner encore quand le POST du
vrai Appliquer arrive quelques secondes plus tard.

### Corrigé

Les trois automatisations passées en `mode: queued` (`max: 10`) —
chaque déclenchement est traité dans l'ordre, aucun n'est rejeté en
silence. Diagnostiqué et corrigé le 2026-09-05 ; voir le commit pour
l'explication complète.

**Si vous rencontrez ceci sur une version antérieure au correctif** :
ce que vous avez appliqué en dernier n'est peut-être pas réellement sur
le disque. Vérifiez la valeur actuelle du champ après un chargement de
page frais (pas juste après Appliquer — ça a toujours l'air correct
juste après, voir la note dans `vssp_rooms_floors.html` sur
`applyPendingLocalSlotSets()`) avant de supposer que tout va bien.
