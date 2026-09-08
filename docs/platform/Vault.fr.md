# Coffre-fort — HashiCorp Vault

Écran **ADMIN → COFFRE-FORT**. Range les secrets d'accès aux serveurs (SSH,
k3s, routeur), les comptes et les mots de passe applicatifs, avec création,
modification et suppression depuis Home Assistant.

---

## Le principe de conception, en une page

Tout ce que Home Assistant lit devient un état d'entité. Or **tout état
d'entité est écrit en clair dans `home-assistant_v2.db`** par le recorder,
affiché dans Outils de développement → États à n'importe quel administrateur,
et susceptible d'apparaître dans une trace d'automatisation. Un coffre dont le
contenu est recopié dans cette base à la seconde où il s'affiche ne protège
rien.

La fonctionnalité est donc coupée en deux, et **cette coupure est tout
l'argument de sécurité** :

| | Ce qu'il voit | Comment |
|---|---|---|
| **Home Assistant** | les **noms** d'entrées, les dates, les versions, l'état du coffre | capteurs RESTful natifs, token portant la policy `vssp-ha` |
| **L'iframe de l'écran** | les **valeurs** | parle à Vault directement, token de session propre |

Le token de Home Assistant reçoit `secret/metadata/*` et **absolument rien sur
`secret/data/*`**. En KV v2 ce sont deux chemins distincts : metadata porte les
noms, data porte les valeurs. Home Assistant peut lister, décrire et supprimer
une entrée — et se fait **refuser par Vault** s'il demande ce qu'elle contient.

Ce n'est pas une règle que les templates promettent de respecter : c'est une
règle qu'ils ne peuvent pas enfreindre. Même si `home-assistant_v2.db` fuit,
aucun secret ne fuit avec.

Répartition qui en découle :

- **Créer, modifier, révéler** → l'iframe. La valeur va du coffre à l'écran et
  nulle part ailleurs.
- **Lister, état, supprimer, restaurer** → les cartes natives. Aucune de ces
  opérations ne met en jeu une valeur.

---

## Ce que ça n'est pas

- **Pas de TLS.** Le coffre écoute en HTTP sur le réseau local, comme Home
  Assistant lui-même. Le jour où il devient joignable de l'extérieur, activer
  TLS dans `vault/config/vault.hcl` et refaire pointer `api_addr` et le CORS
  sur `https://`.
- **Pas de descellement automatique.** Vault se rescelle à chaque redémarrage
  et refuse tout tant que 3 des 5 clés ne sont pas saisies. C'est un coût
  d'exploitation accepté : les alternatives sont un KMS cloud (dépendance
  externe sur une installation purement locale) ou les clés posées sur le même
  disque (ce qui annule le scellement).
- **Pas un gestionnaire de mots de passe navigateur.** Pas d'extension, pas de
  remplissage automatique.

---

## Deux installations

| | Staging (hôte k3s) | Production (HAOS) |
|---|---|---|
| Forme | conteneur Docker | **add-on local** |
| Fichiers | `vault/` | `addons/vssp-vault/` |
| Démarrage | `docker compose up -d` | Paramètres → Modules complémentaires → Installer |
| `init` / descellement | `docker exec … vault operator init` | **interface web** sur `:8200/ui` |
| Bootstrap | `bootstrap.sh` ou `bootstrap-api.sh` | `bootstrap-api.sh` |

HAOS ne permet pas `docker compose` : le Superviseur possède le démon Docker,
et `docker exec` n'y est pas supporté. La voie supportée est un **add-on
local**, un conteneur que le Superviseur construit et gère lui-même. C'est
aussi pourquoi `bootstrap-api.sh` existe : il fait le même travail que
`bootstrap.sh` en passant par l'API HTTP, donc sans avoir à entrer dans le
conteneur. Il tourne depuis l'hôte k3s, depuis ton PC ou depuis l'add-on SSH,
contre l'un ou l'autre déploiement.

---

## Installation — staging (hôte k3s)

### 1. Accès Docker

L'hôte a Docker et Compose v2. Le compte `neo` n'est pas dans le groupe
`docker` :

```bash
sudo usermod -aG docker neo   # puis se reconnecter
```

À savoir : appartenir au groupe `docker` équivaut à un accès root sur cette
machine. Sinon, garder `sudo` devant chaque commande `docker` ci-dessous.

### 2. Démarrer le coffre

```bash
sudo mkdir -p /opt/vssp-vault && sudo chown neo /opt/vssp-vault
# copier vault/ du dépôt vers /opt/vssp-vault/
cd /opt/vssp-vault && docker compose up -d
```

### 3. Initialiser

```bash
docker exec -it vssp-vault vault operator init
```

**Cinq clés de descellement et un token root s'affichent. C'est la seule fois.**

Note-les **hors de cette machine** — sur papier, ou dans un gestionnaire de mots
de passe sur un autre appareil. C'est le bris de glace : sans elles, le coffre
est définitivement fermé, et avec elles seules quelqu'un l'ouvre entièrement.

### 4. Desceller

```bash
docker exec -it vssp-vault vault operator unseal   # trois fois, clé différente
```

### 5. Configurer

```bash
docker exec -e VAULT_TOKEN=hvs.xxxxx -it vssp-vault sh /vault/bootstrap.sh
```

Le script monte KV v2, écrit les deux policies, active `userpass`, demande
interactivement ton mot de passe d'écran, autorise l'origine de Home Assistant
dans le CORS, crée les trois branches, puis **affiche le token de Home
Assistant**.

### 6. Brancher Home Assistant

Coller le token affiché dans `/config/secrets.yaml` :

```yaml
vault_ha_token: hvs.xxxxxxxx
```

La clé y est déjà, vide : le déploiement l'ajoute avec
`vssp_ensure_secret.py`. C'est délibéré — un `!secret` manquant ne casse pas un
capteur, il **empêche Home Assistant de démarrer**.

Puis redémarrer Home Assistant.

---

## Installation — production (HAOS)

### 1. Déposer l'add-on

Le déploiement production le copie vers `/addons/vssp-vault` si `/addons` est
joignable en SSH (add-on Terminal & SSH). Sinon, à la main via le partage Samba
`addons`.

Copier les fichiers **n'installe pas** l'add-on : Paramètres → Modules
complémentaires → Boutique → (trois points) **Vérifier les mises à jour**. Il
apparaît sous « Modules complémentaires locaux ».

### 2. Configurer avant de démarrer

Dans l'onglet Configuration de l'add-on, régler **`api_addr`** sur l'adresse par
laquelle ton navigateur joint réellement l'instance, par exemple
`http://192.168.1.20:8200`. Pas `127.0.0.1` : Vault renverrait l'écran
COFFRE-FORT vers la machine du visiteur.

Puis **Démarrer**.

### 3. Initialiser et desceller — dans le navigateur

`http://<instance>:8200/ui` propose l'initialisation et le descellement.
**Les 5 clés et le token root ne s'affichent qu'une fois** : les noter hors de
la machine.

### 4. Bootstrap

Depuis n'importe quelle machine qui joint le coffre :

```bash
VAULT_ADDR=http://<instance>:8200 HA_URL=http://<instance>:8123 VAULT_TOKEN=hvs.xxxxx sh vault/bootstrap-api.sh
```

Puis coller le token affiché dans `secrets.yaml`, comme en staging.

> **Non testé.** Je n'ai pas d'accès à une instance HAOS : l'add-on est écrit
> d'après les contraintes du Superviseur, pas vérifié contre lui. Le stockage
> pointe sur `/data`, seul volume qui survit à une mise à jour de l'add-on —
> c'est le point à vérifier en premier si quelque chose se passe mal.

---

## Au quotidien

Après **chaque redémarrage de l'hôte**, le coffre est scellé. L'écran l'annonce
en bandeau orange avec le nombre de clés déjà fournies. Desceller :

```bash
docker exec -it vssp-vault vault operator unseal   # trois fois
```

**Révéler** un mot de passe l'affiche masqué ; un clic l'affiche en clair, et il
se remasque seul au bout de 45 secondes.

**Copier** utilise le repli `execCommand` : l'API presse-papiers moderne
n'existe pas hors contexte sécurisé, et cette console est servie en HTTP.

**Supprimer** depuis l'iframe ou depuis la carte MAINTENANCE est une suppression
*douce* — la version est masquée et reste restaurable. **DÉTRUIRE** emporte
l'entrée et tout son historique, sans retour.

---

## Dépannage

| Symptôme | Cause |
|---|---|
| « COFFRE INJOIGNABLE » | conteneur arrêté, **ou** origine absente du CORS de Vault. Rejouer l'étape 4 de `bootstrap.sh`. |
| Les 3 capteurs de branche indisponibles, le capteur de scellement OK | coffre scellé (les capteurs de branche sont authentifiés) ou `vault_ha_token` vide/expiré. |
| Le capteur de scellement indisponible aussi | Vault ne tourne pas du tout. |
| « Refusé par Vault » à la révélation | tu es connecté avec un compte dont la policy n'est pas `vssp-admin`. |
| Le coffre cesse de répondre à HA après des semaines | le token périodique n'a pas été renouvelé. L'automatisation `vssp_vault_renew` s'en charge à 04:17 ; vérifier qu'elle n'est pas désactivée. |

---

## Fichiers

| Chemin | Rôle |
|---|---|
| `vault/docker-compose.yml` | le conteneur |
| `vault/config/vault.hcl` | configuration serveur |
| `vault/policies/vssp-ha.hcl` | policy Home Assistant — noms, jamais valeurs |
| `vault/policies/vssp-admin.hcl` | policy administrateur — les valeurs |
| `vault/bootstrap.sh` | mise en place unique, depuis le conteneur |
| `vault/bootstrap-api.sh` | la meme, via l'API — seule voie sur HAOS |
| `addons/vssp-vault/` | l'add-on HAOS (config, Dockerfile, run.sh) |
| `home-assistant/packages/vssp_vault.yaml` | capteurs, commandes, scripts |
| `home-assistant/www/vssp/wizard/vssp_vault.html` | l'écran |
| `vssp/vssp_ensure_secret.py` | amorce `vault_ha_token` dans `secrets.yaml` |
