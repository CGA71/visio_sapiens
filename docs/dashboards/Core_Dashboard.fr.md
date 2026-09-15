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
       │ Canal séparé, partitions + K3s :           │
       │ vssp_core_stats.py (ssh, toutes les 5 min) │
       │ → /local/vssp/core_stats.json   (§4.4)     │
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

La page emprunte **la session Home Assistant de la tablette elle-même** au dashboard CORE
qui entoure l'iframe (même origine, `sandbox allow-same-origin`) : `window.parent.document
.querySelector('home-assistant').hass.auth`. `hass.auth` rafraîchit lui-même son jeton court,
ce qui compte ici puisque la page interroge toutes les 30 s tant qu'elle reste ouverte. Une
nouvelle tablette n'a donc qu'à se connecter à Home Assistant.

Le jeton longue durée collé (clé `localStorage` `vssp_ha_token`) n'est que le repli pour
`core.html` ouvert seul, hors du dashboard ; sans session et sans lui, la page affiche un
petit formulaire de connexion.

Les fichiers `/local/` (`core_stats.json`, `core_scan_*.json`, `infra_updates.json`) ne
demandent aucun jeton, et le webhook du SCAN est sans authentification mais `local_only`.

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

### 4.4 Partitions et k3s — le collecteur hôte

Glances, via Home Assistant, remonte `/` une fois puis chaque volume kubelet monté depuis lui
(des dizaines de lignes identiques, jamais `/boot/efi`), et ne sait rien du cluster. Les deux
viennent de **`vssp/vssp_core_stats.py`**, lancé toutes les 5 minutes (et 2 minutes après un
démarrage de Home Assistant) par l'automatisation *CORE : collecte hôte et cluster*
(`packages/vssp_core.yaml`) :

```
vssp_core_stats.py ──ssh (identifiants du coffre, vssp-maint)──► hôte
   LC_ALL=C df -P -T -B1 / df -P -i      → partitions (montages kubelet écartés)
   nproc, /etc/os-release, uname -r      → cœurs, OS, noyau
   systemctl is-active k3s, k3s --version
   k3s kubectl get nodes,pods,deployments,statefulsets,daemonsets,pvc,services,namespaces -A -o json
   k3s kubectl get events -A --field-selector type=Warning -o json
   k3s kubectl top nodes                 → charge CPU / mémoire (metrics-server)
   openssl x509 -enddate (certificat du serveur API)
        │
        ▼
/config/www/vssp/core_stats.json  →  /local/vssp/core_stats.json
```

- Même porte que `vssp_infra_updates.py` (il réutilise son `Safe` et son `open_host`) : les
  identifiants de l'hôte vivent dans le coffre, le script les tient le temps d'une exécution,
  Home Assistant ne voit que le JSON. `kubectl` passe par `run_maybe_sudo` — `k3s.yaml` est en
  `0600 root` sur cet hôte. **Chaque commande est une lecture** ; rien n'est écrit sur l'hôte.
- **Coffre scellé** (l'état habituel après un redémarrage de l'hôte) : le fichier est réécrit
  avec la dernière mesure marquée `stale` et le `message_key` du coffre ; la page le dit,
  affiche les partitions de Glances, et pour le cluster se rabat sur le fichier de l'ancien
  minuteur hôte (point suivant).
- **L'ancien minuteur hôte.** Jusqu'ici le panneau était nourri par
  `/opt/osvision/k3s_stats.sh`, un minuteur systemd root (`k3s-stats.timer`, toutes les 60 s)
  posé à la main sur l'hôte, hors de ce dépôt, qui écrit dans le volume de HA sous
  `www/osvision_v2/k3s_stats.json`. Sa version est toujours vide (`kubectl version --short`
  n'existe plus) et ses messages d'événements sont coupés à leur dernier mot. `core.html` ne
  le lit que si `core_stats.json` n'a pas de données de cluster, et l'étiquette *données de
  base seulement*. Une fois le collecteur confirmé, le minuteur peut être retiré :
  `sudo systemctl disable --now k3s-stats.timer osvision-k3s-stats.timer`.

Structure : voir la version anglaise de ce document (mêmes champs).

`/config/www/vssp/` est remplacé à chaque déploiement : le fichier disparaît avec lui et
revient à l'exécution suivante (5 minutes au plus, ou 2 minutes après le redémarrage qui suit
le déploiement).

---

## 5. Boucle de rafraîchissement

`cycle()` lance `refresh()` toutes les 30 s et **se replanifie dans `finally`** : une erreur
réseau affiche un cadre rouge que le cycle suivant efface (elle arrêtait la boucle pour de
bon). À chaque cycle :

1. `GET /api/states` (toutes les entités) et découverte par mots-clés,
2. `core_stats.json`, `infra_updates.json` (et, en repli, l'ancien `k3s_stats.json`),
3. jauges, partitions, températures, panneau K3s, les deux encadrés de préconisations,
4. les **quatre historiques sur 5 jours seulement toutes les 5 minutes** — Glances ne se
   rafraîchit lui-même que toutes les 60 s, et quatre requêtes de cinq jours toutes les 30 s
   pesaient pour rien sur le recorder.

| Étape | Latence |
|---|---|
| Glances → lecture système | ~1 s (interne) |
| HA → interrogation de Glances | 60 s par défaut (`scan_interval`) |
| Collecteur hôte (partitions, k3s) | 5 min |
| core.html → HA / fichiers | 30 s |

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
- **Gestion d'erreur** : `refresh()` tourne dans le `try/catch/finally` de `cycle()` ; une
  erreur affiche un encart rouge en bas de page, et le cycle suivant — toujours replanifié —
  l'efface.
- **Cache-busting** : l'URL de l'iframe dans `core.yaml.j2` porte `?v={{ build_stamp }}` (et
  `&lang={{ locale }}`), un déploiement atteint donc chaque tablette ; « VIDER LE CACHE »
  conserve les deux paramètres en rechargeant.

---

## 8. Points d'attention / pistes d'amélioration

| Problème | Impact | État / correctif suggéré |
|---|---|---|
| ~~Chemin K3s `/local/osvision_v2/`~~ | Panneau K3s nourri par un minuteur hors dépôt | **Corrigé** : `vssp_core_stats.py` → `/local/vssp/core_stats.json` ; l'ancien fichier n'est plus qu'un repli |
| ~~`setTimeout` dans le `try`~~ | La boucle mourait à la première erreur réseau | **Corrigé** : replanifié dans `finally` |
| ~~4 historiques de 5 jours toutes les 30 s~~ | Charge inutile sur le recorder | **Corrigé** : toutes les 5 min |
| ~~Français seulement~~ | CORE en français sur une interface anglaise | **Corrigé** : `?lang=` fourni par `core.yaml.j2` |
| ~~Pas de `?v=` sur l'iframe~~ | Version périmée après déploiement | **Corrigé** : `?v={{ build_stamp }}&lang={{ locale }}` |
| ~~`pods_total / 330` en dur~~ | Ratio faux | **Corrigé** : somme des pods allouables des nœuds |
| Découverte par mots-clés | Casse silencieuse si une entité est renommée | Configuration explicite d'`entity_id` en surcharge |
| Exclusions de pièces codées en dur | Chaque nouvelle pièce pollue la table des températures | Filtrer sur la zone HA plutôt que sur le nom |
| Chart.js via CDN | Graphiques absents hors ligne | Héberger le fichier sous `/local/vssp/js/` |
| Entités Glances orphelines (une par volume kubelet) | Des centaines de capteurs `unavailable` | Masquer `/var/lib/kubelet/.*` dans `glances.conf` (la page le recommande à partir de 10) |
| Min/Max des températures | Retirés (toujours `--`) | Suivre les extrêmes via l'historique HA si besoin |

---

## 9. Préconisations et SCAN

### Encadrés de préconisations

Deux encadrés, **PRÉCONISATIONS SYSTÈME** (à côté des partitions) et **PRÉCONISATIONS K3S**
(sous les indicateurs du cluster), transforment ce qui est à l'écran en conseils. Ils sont
calculés dans la page (`systemRecs()`, `k3sRecs()`), dans la langue de `?lang=`, à chaque
cycle. Chaque constat a une sévérité, une phrase et la commande en lecture seule par laquelle
commencer ; la pire sévérité colore le cadre.

| Encadré | Règles |
|---|---|
| Système | CPU ≥ 75/90 %, RAM ≥ 80/90 %, swap ≥ 50 %, charge 15 min au-dessus du nombre de cœurs (×1,5 = critique), composant ≥ 75/85 °C, partition ≥ 80/90 % (conseil propre à `/` — ramasse-miettes des images du kubelet à 85 %, éviction à 90 % — et à `/boot`), inodes ≥ 85 %, ≥ 10 entités Glances orphelines, collecteur absent / bloqué par un coffre scellé / plus vieux que 15 min |
| K3s | service k3s pas `active`, API muette, nœud NotReady, pression disque/mémoire/PID, CPU/mémoire du nœud ≥ 85 %, pods en CrashLoopBackOff / échec de récupération d'image / OOMKilled / Pending > 5 min / Failed, ≥ 10 redémarrages, charges pas entièrement disponibles, PVC non attaché, alertes des dernières 24 h, pods ≥ 80 % de la capacité, certificat API < 90 / < 30 jours, mise à jour de k3s en attente dans l'écran MISES À JOUR |

### SCAN

Chaque encadré a un bouton **SCAN** qui demande à l'assistant de chat configuré dans la
console de chercher ses constats **sur Internet** et de rapporter quoi faire, avec ses
sources.

```
core.html ──POST /api/webhook/vssp_core_scan {payload_b64}──► automatisation (local_only, base64 vérifié)
   ──► shell_command.vssp_core_scan ──► vssp_core_scan.py --detach
         écrit core_scan_<portée>.json {state: "running"}, se détache, rend la main (HA tue un shell_command à 60 s)
         enfant : fournisseur + recherche web → core_scan_<portée>.json {state: "done", summary, items, citations}
core.html interroge /local/vssp/core_scan_<portée>.json toutes les 3 s jusqu'à y trouver son request_id
```

- **Fournisseur** : `input_select.vssp_chatbot_provider` et son fichier de clé
  (`/config/vssp/.<fournisseur>_key`), partagés avec la bulle de chat. Claude tourne sur
  `claude-opus-5` avec l'outil `web_search_20260209` (5 recherches au plus, repli côté
  serveur en cas de refus), quel que soit l'ancien modèle de la bulle de chat ; Gemini utilise
  l'ancrage `google_search` et ChatGPT l'outil `web_search` de l'API Responses, chacun avec le
  modèle choisi dans la console. Le fournisseur personnalisé n'a pas de recherche web : SCAN
  le dit. Seul le chemin Claude a été éprouvé de bout en bout.
- **Ce qui sort de la maison** : les textes des constats tels que la page les a écrits, les
  versions de l'OS, du noyau et de k3s, le nombre de cœurs et la taille de la mémoire. Jamais
  le nom d'hôte ; tout ce qui ressemble à une adresse IPv4 est de toute façon masqué par le
  script. Chaque scan est un appel d'API payant : il ne part que sur une pression du bouton.
- **Résultat** : un résumé, un élément par constat (conseil, commandes, sources), puis les
  pages citées. Le dernier résultat de chaque encadré reste affiché jusqu'au déploiement
  suivant. La page rappelle de vérifier les sources avant d'appliquer quoi que ce soit.
