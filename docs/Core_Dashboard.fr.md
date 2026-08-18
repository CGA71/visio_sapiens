# core.html — Dashboard Système Visio Sapiens

**Français** · [English](Core_Dashboard.md)

Documentation du fonctionnement réel de la page : d'où viennent les métriques, comment elles
remontent jusqu'à la page, et à quelle fréquence.

**Emplacement réel dans le dépôt :** `home-assistant/www/vssp/core.html`
→ déployé en `/config/www/vssp/core.html` → servi sur `/local/vssp/core.html`.

---

## 1. Vue d'ensemble

`core.html` est une **page statique autonome** (HTML + CSS + JS inline, aucun build, aucun
framework). Elle ne collecte **aucune métrique elle-même** : c'est un pur client d'affichage
qui interroge l'API REST de Home Assistant.

Elle n'est pas ouverte directement par l'utilisateur : le dashboard Lovelace
`dashboards/views/core.yaml` (url_path `visio-sapiens-core`) l'embarque dans une **iframe**.
Ce fichier a d'ailleurs été corrigé pour ne plus superposer deux versions du même contenu —
les cartes natives HA (gauge, apexcharts, auto-entities) qui doublonnaient l'iframe ont été
retirées. La vue CORE ne contient plus que : sidebar (`nav`), première ligne du bandeau
(`header`), iframe, footer HUD.

La chaîne complète est la suivante :

```
┌──────────────┐   psutil / lm-sensors
│   Host Linux │   (lecture /proc, /sys)
└──────┬───────┘
       │
┌──────▼──────────────┐
│ Glances (Python)     │  daemon glances -w
│ API REST :61208      │  → JSON temps réel (CPU, RAM, swap, load, temps, disk, net)
└──────┬──────────────┘
       │ polling (scan_interval, 60 s par défaut)
┌──────▼──────────────────────────┐
│ Home Assistant                   │
│  • intégration "Glances"         │ → crée des entités sensor.*
│  • recorder (SQLite/MariaDB)     │ → historise les états
│  • API REST /api/states          │
│  • API /api/history/period       │
│  • serveur statique /local/       │
└──────┬──────────────────────────┘
       │ fetch() + Bearer token, toutes les 30 s
┌──────▼───────┐
│  core.html   │  jauges SVG + Chart.js
└──────────────┘

       ┌───────────────────────────────────────────┐
       │ Canal séparé pour K3s :                    │
       │ cron k3s_stats.sh → k3s_stats.json         │
       │ → /config/www/vssp/ → /local/vssp/...      │
       └───────────────────────────────────────────┘
```

**Point clé :** `HA_URL = window.location.origin`. La page **doit** être servie par Home
Assistant lui-même. Ouverte en `file://` ou depuis un autre domaine, tous les appels API
échouent (mauvaise origine + CORS). L'iframe de `core.yaml` respecte cette contrainte
puisqu'elle pointe sur une URL `/local/` de la même instance.

---

## 2. La couche de collecte : Glances

La dépendance de collecte est **Glances**, un outil de monitoring écrit en Python (basé sur
`psutil`). Le sous-titre du header le confirme : `Glances Monitoring`.

### Installation côté host

```bash
pip install "glances[web]"
# ou : apt install glances
glances -w                      # mode serveur web + API REST sur le port 61208
```

En service systemd :

```ini
[Unit]
Description=Glances
After=network.target

[Service]
ExecStart=/usr/local/bin/glances -w --disable-webui
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

- API REST : `http://<host>:61208/api/4/all` (v3 : `/api/3/all`)
- Les températures viennent du plugin `sensors`, qui nécessite **`lm-sensors`** installé et
  configuré sur le host (`sensors-detect`). Sans lui, la section « Température des
  composants » reste vide.

### Côté Home Assistant

Intégration **Glances** (Paramètres → Appareils et services → Ajouter → Glances), avec
host + port + version d'API. HA interroge Glances toutes les 60 s par défaut et crée des
entités du type :

| Métrique | Entité typique |
|---|---|
| CPU | `sensor.<host>_cpu_used_percent` / `..._utilisation_cpu` |
| RAM | `sensor.<host>_memory_use_percent` / `..._utilisation_memoire` |
| Swap | `sensor.<host>_swap_use_percent` |
| Load | `sensor.<host>_cpu_load_1m` / `..._charge_processeur_1` |
| Températures | `sensor.<host>_cpu_temp`, `..._package_id_0`, `..._nvme`, `..._edge` |
| Disque | `sensor.<host>_disk_use_percent` / `..._espace` |
| Réseau | `sensor.<host>_<iface>_rx` |

C'est le `recorder` de HA qui stocke l'historique interrogé plus tard par les graphiques.

---

## 3. Authentification

```js
var HA_URL = window.location.origin,
    TOKEN  = localStorage.getItem('osv_ha_token') || '';
```

- Au premier chargement, si aucun token n'est en cache, `init()` remplace tout le contenu de
  `.page` par un mini-formulaire de connexion.
- `saveToken()` écrit le jeton dans `localStorage` sous la clé **`osv_ha_token`**, puis
  rappelle `init()`.
- Le jeton est un **Long-Lived Access Token** HA (profil utilisateur → bas de page →
  « Créer un jeton »).
- Il est ensuite envoyé sur chaque requête : `Authorization: Bearer <TOKEN>`.

⚠️ Le token est stocké en clair dans `localStorage` et reste valable très longtemps — à
traiter comme un secret d'accès complet à Home Assistant. La clé `osv_ha_token` est un
reliquat de nommage : la renommer casserait la session de tous les navigateurs déjà
appairés, donc à ne faire qu'avec une migration explicite (lire l'ancienne clé, réécrire
sous la nouvelle, supprimer l'ancienne).

---

## 4. Récupération des métriques temps réel

### 4.1 État instantané — `haGet('states')`

```js
async function haGet(p){
  var r = await fetch(HA_URL+'/api/'+p, {headers:{Authorization:'Bearer '+TOKEN}});
  if(!r.ok) throw new Error(p+': '+r.status);
  return r.json();
}
```

Un **seul appel** à `GET /api/states` récupère l'intégralité des entités de Home Assistant
(souvent plusieurs centaines d'objets JSON). Tout le dashboard est ensuite construit à partir
de ce tableau, sans requête supplémentaire par métrique.

### 4.2 Découverte automatique des entités

Le dashboard ne code en dur **aucun `entity_id`**. Il fait du *fuzzy matching* sur le couple
`entity_id + friendly_name` :

```js
function findEntity(s,k,x){          // k = mots-clés requis, x = mots-clés exclus
  return s.find(function(e){
    var c = (e.entity_id+' '+(e.attributes.friendly_name||'')).toLowerCase();
    return k.every(w => c.includes(w.toLowerCase()))
        && !x.some(w => c.includes(w.toLowerCase()));
  });
}
```

`findEntities()` est la variante qui retourne **toutes** les correspondances (utilisée pour
les capteurs de température).

La recherche est en **cascade avec fallbacks**, ce qui permet de supporter à la fois les
noms d'entités anglais et français :

```js
var cpu = findEntity(states,['cpu','use'],['core','temp','temperature'])
       || findEntity(states,['cpu_percent'])
       || findEntity(states,['utilisation','cpu'],['core','temp']);
```

Même logique pour la RAM (`ram+use` → `memory+use` → `utilisation+memoire`), le load
(`charge+processeur+1` → `load+1m`), la température (`cpu+temp` → `package+temp` →
`edge+temp`), le disque (`disk+use` → `espace`).

**Conséquence :** renommer une entité dans HA peut casser silencieusement une jauge
(elle affichera `0` ou `--` sans erreur).

**Effet de bord à connaître :** les exclusions de la table des températures listent
explicitement des pièces (`bedroom`, `kitchen`, `living`, `garden`, `spa`, `secret`,
`computer_room_temp`, `technical_room_temp`). Chaque nouvelle pièce du Room Engine devra
être ajoutée à cette liste, sinon son capteur d'ambiance apparaîtra dans le tableau des
composants matériels.

### 4.3 Historique — `haHistory(entity, days)`

```js
GET /api/history/period/<start_iso>
      ?filter_entity_id=<entity>
      &end_time=<now_iso>
      &minimal_response
      &no_attributes
```

- Fenêtre : **5 jours** (`d*864e5` ms), appelée avec `d = 5`.
- `minimal_response` + `no_attributes` allègent fortement la charge utile.
- En cas d'échec, retourne `[]` (le graphique reste vide, pas d'exception).

`processHistory()` nettoie ensuite la série :

1. filtre les points non numériques (`unavailable`, `unknown`…),
2. formate le label en `JJ/MM` (locale `fr-FR`),
3. **sous-échantillonne** à ~200 points max (`step = floor(len/200)`), sinon Chart.js
   s'effondrerait sur 5 jours de relevés minute par minute.

### 4.4 Statistiques K3s — canal séparé 🔴 chemin cassé

Le cluster Kubernetes **ne passe pas par l'API HA** :

```js
var k3r = await fetch(HA_URL+'/local/osvision_v2/k3s_stats.json?t='+Date.now());
```

**Ce chemin est périmé.** Le dossier `www/` du projet s'appelle désormais `vssp/`
(`home-assistant/www/vssp/` → `/local/vssp/`), et le pipeline ne déploie plus rien sous
`/local/osvision_v2/`. Le `fetch` part donc systématiquement en 404, le `catch` avale
l'erreur, et le panneau affiche en permanence *« K3s stats non disponibles. Installez le
cron k3s_stats.sh sur le host. »* — même quand le cron tourne parfaitement.

**Correctif, une ligne dans `core.html`:**

```js
var k3r = await fetch(HA_URL+'/local/vssp/k3s_stats.json?t='+Date.now());
```

Et vérifier que le cron écrit bien dans le nouveau dossier :

```sh
# k3s_stats.sh, côté host
OUT=/config/www/vssp/k3s_stats.json
```

Fonctionnement une fois corrigé :

- Un script `k3s_stats.sh` (exécuté en cron sur le host) appelle `kubectl` et écrit un JSON
  dans `/config/www/vssp/k3s_stats.json`.
- HA sert `/config/www/` sous l'URL `/local/` — pas de token nécessaire ici.
- Le paramètre `?t=<timestamp>` sert de **cache-buster**.
- Si le fichier est absent ou invalide, `renderK3s(null)` affiche le message d'aide.

Structure JSON attendue :

```json
{
  "version": "v1.29.4+k3s1",
  "node_count": 3,
  "pods_total": 87,
  "pods_running": 85,
  "deployments": 24,
  "services": 31,
  "namespaces": 12,
  "nodes": [{"name":"node1","status":"Ready","role":"control-plane",
             "cpu_capacity":"8","memory_capacity":"32Gi"}],
  "top_namespaces":  [{"ns":"default","count":14}],
  "top_deployments": [{"name":"nginx","ready":"3/3"}],
  "events": [{"time":"14:32","type":"Warning","object":"pod/x","message":"..."}]
}
```

> `k3s_stats.json` est produit sur le host, pas dans le dépôt : il ne doit **pas** être
> versionné, et le déploiement (`rm -rf /config/www/vssp` puis `mv`) l'écrase à chaque run.
> Si vous voulez qu'il survive aux déploiements, faites-le écrire ailleurs
> (ex. `/config/www/vssp_runtime/`) — ce dossier n'étant pas remplacé par la CI.

---

## 5. Boucle de rafraîchissement

```js
setTimeout(init, 30000);   // dernière ligne du bloc try de init()
```

Il n'y a **ni WebSocket, ni SSE, ni EventSource** : c'est du **polling récursif toutes les
30 secondes**, qui rejoue l'intégralité du cycle :

1. `GET /api/states` (toutes les entités),
2. re-découverte des entités par mots-clés,
3. re-rendu des 5 jauges,
4. **4 appels d'historique sur 5 jours** (CPU, RAM, réseau, disque),
5. destruction + recréation des 4 instances Chart.js,
6. fetch du JSON K3s,
7. reprogrammation du timer.

Le « temps réel » effectif est donc borné par la chaîne complète :

| Étage | Latence |
|---|---|
| Glances → lecture système | ~1 s (interne) |
| HA → polling Glances | 60 s par défaut (`scan_interval`) |
| core.html → polling HA | 30 s |
| **Fraîcheur réelle affichée** | **jusqu'à ~90 s** |

Rafraîchir la page plus vite que le `scan_interval` de l'intégration Glances n'apporte donc
rien. Pour un vrai temps réel, il faut abaisser le `scan_interval` côté HA (ou passer sur le
WebSocket HA avec `subscribe_events` / `state_changed`).

---

## 6. Rendu

### Jauges SVG — `renderGauge(id, valeur, max, unité, couleur, sous-titre)`

Arc de **270°** dessiné à la main en SVG (départ à −225°, rayon 50, centre 60/60), généré
par trigonométrie sans librairie. Code couleur automatique :

| Remplissage | Couleur |
|---|---|
| > 80 % | `#FF3D71` (rouge) |
| > 60 % | `#FF9800` (orange) |
| sinon | couleur passée en paramètre |

Le Load Average n'utilise pas de jauge : c'est un bloc texte 1m / 5m / 15m.

### Graphiques — `createChart()`

**Chart.js 4.4.1** chargé depuis `cdnjs.cloudflare.com` (⚠️ dépendance Internet). Courbes de
type `line`, `fill: true`, `tension: .3`, `pointRadius: 0`. L'instance précédente est
`destroy()` avant recréation, ce qui évite les fuites mémoire à chaque cycle.

### Table des températures — `renderTemps()`

Deux niveaux de filtrage :

1. `findEntities(states, ['temp'], [...])` exclut météo, prévisions, pièces de la maison,
2. ne garde que les capteurs matériels dont l'`entity_id` contient `cpu`, `core`, `nvme`,
   `ssd`, `package`, `edge`, `board`, `k10`, `it87`.

Barre de progression sur une échelle **0–85 °C**, seuil d'alerte **> 70 °C** (`WARN`).
Les colonnes Min/Max sont actuellement des placeholders `--` non alimentés.

### Sécurité d'affichage

`esc()` échappe `&`, `<`, `>` sur toutes les valeurs injectées via `innerHTML` — protection
XSS pour les données provenant de HA et surtout des messages d'événements K3s.

---

## 7. Divers

- **`clearCache()`** (bouton « ↻ VIDER CACHE ») : purge la Cache API du navigateur puis
  recharge la page avec `?nocache=<timestamp>`. Utile quand le service worker HA sert une
  ancienne version du fichier.
- **Gestion d'erreur** : tout `init()` est enveloppé dans un `try/catch` ; une erreur affiche
  un encart rouge en bas de page. À noter — en cas d'erreur, **le `setTimeout` n'est pas
  atteint**, donc la boucle s'arrête définitivement jusqu'au rechargement manuel.
- **Cache-busting CI** : le `find … sed` du job `build` ne réécrit que les `?v=` des `*.yaml`
  de `dist/`. `core.html` n'est **pas** couvert, et n'est de toute façon pas déclaré en
  ressource Lovelace : c'est l'URL de l'iframe dans `core.yaml` qui devrait porter un `?v=`
  si l'on veut forcer le rechargement après déploiement. Sans ça, seul le bouton
  « VIDER CACHE » débloque un navigateur qui a mis la page en cache.

---

## 8. Points d'attention / pistes d'amélioration

| Problème | Impact | Piste |
|---|---|---|
| **Chemin K3s `/local/osvision_v2/`** | Panneau K3s toujours vide, sans erreur visible | Passer à `/local/vssp/` (§4.4) |
| `setTimeout` dans le `try` | La boucle meurt à la première erreur réseau | Déplacer dans un `finally` |
| `saveToken()` rappelle `init()` | Risque de plusieurs boucles concurrentes | Garder l'id du timer et `clearTimeout` |
| 4 requêtes d'historique 5 j toutes les 30 s | Charge inutile sur le recorder HA | Rafraîchir l'historique toutes les 5–10 min seulement |
| Découverte par mots-clés | Casse silencieuse au renommage d'entité | Config d'`entity_id` explicites en surcharge |
| Exclusions de pièces codées en dur | Chaque nouvelle pièce pollue la table des températures | Filtrer sur l'Area HA plutôt que sur le nom |
| Chart.js via CDN | Dashboard KO hors ligne | Héberger le fichier dans `/local/vssp/js/` |
| Token en `localStorage` | Accès HA complet exposé au XSS | Token dédié / durée limitée |
| `pods_total / 330` en dur | Faux ratio si le nb de nœuds change | Calculer `node_count × 110` |
| Colonnes Min/Max températures | Toujours `--` | Suivre les extrêmes via l'historique HA |
| Polling 30 s vs scan 60 s | Moitié des cycles sans nouvelle donnée | WebSocket HA `state_changed` |
| Pas de `?v=` sur l'iframe | Ancienne version servie après déploiement | Ajouter le token de version dans `core.yaml` |
