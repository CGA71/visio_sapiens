# Descellement — un mot de passe, depuis un appareil enrôlé

Service **`vssp-unseal`** sur l'hôte du coffre. Remplace la saisie de trois
clés Shamir après chaque redémarrage par **un mot de passe**, à condition que
la demande vienne d'un appareil porteur d'un certificat délivré par vous.

---

## Le marché, en clair

Vault se rescelle à **chaque redémarrage**, par conception. Aujourd'hui les
cinq clés ne sont nulle part sur la machine : même `root` ne peut pas ouvrir
le coffre, il faut qu'un humain tape trois parts. C'est l'arrangement le plus
solide disponible ici.

Ce service en abandonne une partie, **délibérément**.

| | Avant | Après |
|---|---|---|
| Où sont les parts | nulle part sur la machine | sur la machine, chiffrées |
| Disque ou sauvegarde volés | rien à voler | du chiffré, inutilisable sans la phrase |
| Attaquant déjà `root`, machine allumée | ne peut rien faire | peut attendre la saisie et prendre les parts |
| Ce qu'il faut pour ouvrir | 3 clés sur 5 | 1 phrase secrète |

**Un partage 3-sur-5 dont les trois parts dorment dans le même fichier est un
secret 1-sur-1.** Ce service existe parce que ce marché a été fait en
connaissance de cause, pas parce qu'il serait gratuit. La phrase secrète doit
être longue et n'exister nulle part ailleurs.

Vos cinq clés d'origine restent valables et restent la voie de secours :
perdre la phrase ne rend pas le coffre inaccessible, seulement ce raccourci.

## Ce qui authentifie réellement

Deux facteurs, tous deux réels :

- **Ce que l'appareil possède** — un certificat client, vérifié en **TLS
  mutuel** contre une autorité privée créée par l'outil. Sans certificat, la
  poignée de main échoue : pas de page d'erreur, pas de 401, *rien* — la
  machine ne révèle même pas qu'un service écoute.
- **Ce que vous savez** — la phrase secrète, seule chose capable de dériver la
  clé qui déchiffre les parts.

### L'adresse MAC ne compte pas, et c'est volontaire

Elle avait été demandée comme second facteur. Elle n'en est pas un :

- elle se change en une commande — `ip link set dev wlan0 address …` ;
- elle est **invisible dès qu'un routeur sépare** le client de l'hôte : ce qui
  arrive est la MAC de la box.

Le service consigne la MAC qu'il peut voir dans sa ligne d'audit, et **ne lui
laisse décider de rien**. Un contrôle MAC n'aurait rien ajouté tout en donnant
l'impression d'un second facteur — le pire des deux mondes.

### Pourquoi pas dans Home Assistant

C'est la question naturelle, et la réponse est la même que celle qui a coupé
l'écran COFFRE-FORT en deux (voir [Vault.fr.md](Vault.fr.md)) : **tout état
d'entité est écrit en clair dans `home-assistant_v2.db`** par le recorder,
affiché dans Outils de développement → États, embarqué dans les sauvegardes et
servi à tout jeton par `/api/states`. Un mot de passe saisi dans un
`input_text` est un mot de passe écrit sur le disque. Le HTTPS protégerait le
trajet, pas le stockage — et l'instance est en HTTP simple de toute façon.

Le bouton peut vivre sur l'écran COFFRE-FORT ; la **saisie**, elle, part
directement vers ce service et n'entre jamais dans la machine à états.

## Ce que le service peut et ne peut pas faire

Il descelle. Il ne peut pas sceller, ni lire un secret, ni en écrire un. Il ne
joint que deux routes du Vault local : `sys/seal-status` et `sys/unseal`.
**Compromettre ce service, c'est compromettre l'étape de descellement, pas le
contenu du coffre.**

L'unité systemd est durcie en conséquence : `NoNewPrivileges`,
`ProtectSystem=strict`, `ProtectHome`, `CapabilityBoundingSet=` vide,
`MemoryDenyWriteExecute`, `SystemCallFilter=@system-service`, et aucune
famille d'adresses hors IP.

## Installation

Sur l'hôte, dans cet ordre. Rien n'est servi avant l'étape 4.

```bash
sudo sh vault/unseal/install.sh          # compte, répertoires, unité systemd

# 1. le certificat de cet hôte — toutes les adresses que vos appareils utiliseront
sudo -u vssp-unseal vssp-unseal enroll-server 192.168.1.11

# 2. les clés. Coffre SCELLÉ de préférence : chaque clé est alors vérifiée
#    contre Vault avant que quoi que ce soit ne soit écrit.
sudo -u vssp-unseal vssp-unseal enroll-keys

# 3. un certificat par appareil
sudo -u vssp-unseal vssp-unseal enroll-device 'telephone'
sudo -u vssp-unseal vssp-unseal enroll-device 'pc-perso'

# 4. démarrer
sudo systemctl enable --now vssp-unseal
```

**Rien n'est jamais affiché à l'écran** : clés et phrase passent par `getpass`,
donc pas d'écho, pas d'historique de shell, et pas dans `argv` où n'importe
quel utilisateur de l'hôte les lirait dans `/proc`.

L'étape 2 **vérifie chaque clé** si le coffre est scellé : elle la soumet,
contrôle que le compteur de Vault avance, et remet le compteur à zéro à la
fin. Une faute de frappe est trouvée là, pas à deux heures du matin. Coffre
ouvert, la vérification est impossible et l'outil le dit au lieu de le
laisser croire.

### Sortir les deux fichiers de l'hôte

`/var/lib/vssp-unseal/devices` et `/etc/vssp-unseal` sont en **0700 et
appartiennent au compte de service** : `scp` sous votre propre compte échoue en
`Permission denied` avant d'avoir lu un seul octet. Copiez-les en changeant le
propriétaire dans le même geste :

```bash
sudo ls /var/lib/vssp-unseal/devices/        # le nom exact du fichier

sudo install -o neo -g neo -m 600 \
     /var/lib/vssp-unseal/devices/<nom>.p12 /home/neo/
sudo install -o neo -g neo -m 644 /etc/vssp-unseal/ca.crt /home/neo/
```

Depuis le poste de travail :

```bash
scp neo@192.168.1.11:/home/neo/<nom>.p12 .
scp neo@192.168.1.11:/home/neo/ca.crt .
```

Puis détruisez les copies intermédiaires — une identité lisible n'a rien à
faire dans un répertoire personnel :

```bash
shred -u /home/neo/<nom>.p12 && rm -f /home/neo/ca.crt
```

### Deux fichiers, deux magasins

C'est là que ça se passe mal le plus souvent. Le `.p12` et le `ca.crt` ne vont
**pas** au même endroit, et n'en installer qu'un ne fait pas la moitié du
travail :

| Fichier | Ce que c'est | Où il va |
|---|---|---|
| `<nom>.p12` | **votre identité** — certificat *et* clé privée | le magasin personnel / utilisateur |
| `ca.crt` | **l'autorité** qui a signé le serveur | le magasin des racines de confiance |

Sans le `.p12`, le service coupe la connexion pendant la poignée de main. Sans
le `ca.crt`, c'est votre propre client qui refuse le serveur. Les deux échecs
ne se ressemblent pas du tout ; le tableau de dépannage nomme les deux.

### Windows

Dans **PowerShell**, depuis le dossier qui contient les deux fichiers :

```powershell
certutil -user -addstore Root ca.crt
certutil -user -importpfx My <nom>.p12
Get-ChildItem Cert:\CurrentUser\My |
  Where-Object { $_.Subject -like "*<nom>*" } |
  Select-Object Thumbprint, Subject, NotAfter
```

`certutil -importpfx` demande le mot de passe d'export sans l'afficher.
L'empreinte imprimée par la troisième commande devient l'adresse du certificat
client :

```powershell
curl.exe --ssl-no-revoke --cert "CurrentUser\MY\<EMPREINTE>" `
         https://192.168.1.11:8443/status
```

Chrome et Edge lisent ce magasin. Firefox garde le sien : Paramètres → Vie
privée → Certificats → Afficher les certificats → Vos certificats → Importer.

#### Pourquoi pas `--cert <fichier>.p12` sous Windows

Parce que le `curl` de Windows est compilé contre **schannel**, et que schannel
**ne demande jamais le mot de passe d'un .p12**. Recevant le fichier seul, curl
tente un mot de passe vide et signale ce qui ressemble à un mot de passe faux :

```
curl: (58) schannel: Failed to import cert file EXPANSE-IT.p12, password is bad
```

La forme par fichier exige donc le mot de passe collé au chemin —
`--cert-type P12 --cert "C:\chemin\nom.p12:motdepasse"` — ce qui laisse un
secret dans l'historique du shell et casse net si le mot de passe contient
lui-même un `:`. Le passage par le magasin n'a ni l'un ni l'autre défaut. (Le
`C:` d'un chemin Windows n'est pas pris pour ce séparateur : curl reconnaît une
lettre de lecteur.) Et si schannel répond `--cacert is not supported`, retirez
l'option — l'autorité est déjà dans le magasin racine depuis la première
commande.


#### `CRYPT_E_NO_REVOCATION_CHECK`

```
curl: (35) schannel: next InitializeSecurityContext failed:
CRYPT_E_NO_REVOCATION_CHECK - La fonction de révocation n'a pas pu vérifier
la révocation du certificat.
```

Celle-ci arrive **après** l'acceptation du certificat client : c'est votre
propre machine qui refuse le serveur. Windows cherche à savoir si le
certificat du serveur a été révoqué, et une autorité privée ne publie ni CRL
ni répondeur OCSP — il n'y a donc personne à interroger, et schannel échoue
plutôt que de passer outre.

```powershell
curl.exe --ssl-no-revoke --cert "CurrentUser\MY\<EMPREINTE>" `
         https://192.168.1.11:8443/status
```

Cette option n'est pas un raccourci de sécurité ici. Il n'existe aucun service
de révocation à joindre pour cette autorité, et c'est délibéré : **l'autorité,
c'est vous**, et révoquer un appareil consiste à supprimer son certificat sur
l'hôte — `rm /var/lib/vssp-unseal/devices/<nom>.p12` puis réémission, sachant
qu'après cela l'ancien certificat reste valide et que la seule protection
réelle est la phrase secrète. Les navigateurs tolèrent d'eux-mêmes cette
vérification impossible ; le `curl` de Windows est le seul strict.

### Android

Paramètres → Sécurité → **Chiffrement et identifiants** → *Installer un
certificat*, **deux fois**, parce qu'Android trie lui-même les deux :

- *Certificat CA* pour `ca.crt`. Il vous avertira de ce qu'implique une
  autorité privée ; l'avertissement est exact, et la réponse est que l'autorité,
  c'est vous.
- *Certificat utilisateur VPN et application* pour le `.p12`, qui demande le
  mot de passe d'export.

### iOS / iPadOS

Ouvrez chaque fichier, puis Réglages → Général → **VPN et gestion de
l'appareil** → Installer. Puis l'étape que tout le monde rate : Réglages →
Général → Informations → **Réglages de confiance des certificats**, et activez
la confiance complète pour `VSSP Unseal CA`. Une autorité installée mais non
approuvée là ne fait absolument rien, silencieusement.

### Vérifier que ça marche

Sous Linux ou macOS, où curl est compilé contre OpenSSL et où la forme par
fichier convient :

```bash
curl --cert-type P12 --cert '<nom>.p12:<mot de passe d export>' \
     --cacert ca.crt https://192.168.1.11:8443/status
```

Attendu, pour un coffre actuellement ouvert :

```json
{"sealed": false, "t": 3, "n": 5, "progress": 0}
```

`Failed to connect to 192.168.1.11 port 8443` dit autre chose : le service ne
tourne pas. `systemctl is-active vssp-unseal` sur l'hôte, et
`ss -ltn | grep 8443` pour le voir écouter.

Une fois importé, supprimez le `.p12` du système de fichiers de l'appareil : le
magasin de certificats le détient désormais, et le fichier est un second
exemplaire d'une identité.

## Le bouton sur l'écran COFFRE-FORT

Quand le coffre est scellé, l'écran COFFRE-FORT affiche désormais un champ
pour la phrase secrète et un bouton **DESCELLER** sous l'avertissement, au
lieu de la seule ligne `docker exec` — qui reste imprimée en dessous, parce
qu'un navigateur n'est pas toujours disponible et que la voie manuelle ne doit
jamais disparaître de la documentation à l'écran.

La page envoie la phrase secrète à `https://<hôte>:8443/unseal` et nulle part
ailleurs. Elle ne passe ni par Vault ni par Home Assistant : Home Assistant
sert la page, la page parle directement au service de descellement sur sa
propre connexion mutuellement authentifiée.

À la première utilisation, le navigateur demande **quel certificat
présenter**. Cette invite est le TLS mutuel qui fonctionne. Chrome et Edge
retiennent la réponse pour la session ; Firefox redemande sauf indication
contraire.

### Pourquoi le service renvoie l'origine au lieu de répondre `*`

Un navigateur ne présente pas de certificat client sur une requête
cross-origine si la page ne demande pas `credentials: "include"` — et une
requête faite ainsi **refuse net une origine joker dans
`Access-Control-Allow-Origin`**. Le joker et le certificat ne peuvent pas
coexister : un service qui répond `*` ne pourrait jamais être appelé depuis
une page.

Il renvoie donc l'origine de l'appelant, et seulement pour les origines qu'il
accepte. Le défaut accepte les pages servies par **le même hôte**, comparées à
l'en-tête `Host` de la requête, ce qui ne demande aucune configuration et
reste juste si la machine est renommée ou jointe par une seconde adresse.
`VSSP_UNSEAL_ORIGINS` prend une liste d'origines exactes, séparées par des
virgules, pour un déploiement séparé.

Cette liste n'authentifie rien — le certificat et la phrase secrète s'en
chargent, et aucun en-tête CORS ne peut accorder l'un ou l'autre. Ce qu'elle
empêche, c'est qu'un site quelconque visité par l'opérateur tire des requêtes
sur le service avec un certificat que le navigateur détient déjà : cinq
d'entre elles bloqueraient le vrai utilisateur quinze minutes.

## Au quotidien

`GET /status` et `POST /unseal` sur `https://<hôte>:8443`, certificat client
obligatoire.

```bash
# Linux / macOS — le curl OpenSSL prend le .p12 directement depuis le fichier
curl --cert-type P12 --cert 'telephone.p12:<mot de passe d export>' \
     --cacert ca.crt https://192.168.1.11:8443/status
curl --cert-type P12 --cert 'telephone.p12:<mot de passe d export>' \
     --cacert ca.crt -X POST -d '{"passphrase":"..."}' \
     https://192.168.1.11:8443/unseal
```

```powershell
# Windows — depuis le magasin de certificats, voir « Pourquoi pas --cert
# <fichier>.p12 » ci-dessus
curl.exe --ssl-no-revoke --cert "CurrentUser\MY\<EMPREINTE>" `
         https://192.168.1.11:8443/status
```

Cinq phrases fausses et la porte reste fermée **quinze minutes**, y compris à
la bonne phrase. Le compteur est persisté : redémarrer le service ne le remet
pas à zéro, et seul `root` peut le redémarrer.

## Cryptographie

| | |
|---|---|
| Dérivation | `scrypt` (bibliothèque standard), N=2¹⁷, r=8, p=1 → ~128 Mo et ~0,3 s par tentative |
| Chiffrement | AES-256-GCM, sel et nonce tirés à chaque écriture |
| Authentifié en plus | la version et **les paramètres du KDF**, pour que personne ne puisse faire relire le blob avec des réglages plus faibles |
| Certificats | ECDSA P-256, autorité privée, `CERT_REQUIRED` côté serveur |

Le tag GCM fait échouer une phrase fausse comme une **erreur de
déchiffrement** plutôt que comme un charabia vraisemblable qui serait ensuite
envoyé à Vault comme s'il s'agissait d'une clé.

Le service ne distingue pas, dans sa réponse, « phrase fausse » de « fichier
altéré » : le dire renseignerait gratuitement un attaquant sur l'intégrité du
fichier.

> **Piège rencontré à l'écriture.** `hashlib.scrypt(..., maxmem=0)` se lit
> « pas de limite » et signifie « la limite propre d'OpenSSL », soit 32 Mo —
> alors que N=2¹⁷ en demande 128. Les paramètres honnêtes échouent donc
> franchement sur `memory limit exceeded` tant que le plafond ne les suit pas.
> Il est calculé à partir de `n`, `r` et `p`, pour qu'augmenter le coût plus
> tard ne puisse pas ramener la panne.

## Fichiers

| Chemin | Contenu |
|---|---|
| `/etc/vssp-unseal/shares.enc` | les trois parts chiffrées (0600) |
| `/etc/vssp-unseal/ca.{crt,key}` | l'autorité privée |
| `/etc/vssp-unseal/server.{crt,key}` | le certificat de l'hôte |
| `/etc/vssp-unseal/state.json` | compteurs d'échec et blocages |
| `/var/lib/vssp-unseal/devices/` | les `.p12` délivrés |
| `vault/unseal/vssp_unseal.py` | l'outil — enrôlement et service |
| `vault/unseal/install.sh` | compte, répertoires, unité systemd |

## Dépannage

| Symptôme | Cause |
|---|---|
| Le navigateur ne propose aucun certificat | le `.p12` n'est pas importé, ou le `ca.crt` n'est pas approuvé |
| `403 denied` | phrase fausse — ou fichier altéré, le service ne dit pas lequel |
| `429 locked` | cinq échecs ; attendez, ou `sudo rm /etc/vssp-unseal/state.json` |
| `503 not enrolled` | l'étape 2 n'a pas été faite |
| `502 vault unreachable`, ou `Connection refused` à l'enrôlement | le coffre n'est pas là où l'outil le cherche — voir ci-dessous. Un conteneur arrêté donne la même chose ; vérifiez les deux |
| `schannel: ... password is bad` | le curl de Windows a reçu le `.p12` comme fichier ; schannel ne demande jamais son mot de passe — passez par le magasin de certificats |
| `scp: Permission denied` sur le `.p12` | il est en 0600 dans un répertoire 0700 du compte de service ; sortez-le d'abord avec `sudo install -o <vous>` |
| TLS `certificate required`, ou la poignée de main se ferme | le `.p12` n'est pas dans le magasin personnel, ou le client n'a pas reçu l'ordre de le présenter |
| `CRYPT_E_NO_REVOCATION_CHECK` | Windows ne peut pas vérifier la révocation auprès d'une autorité privée, qui n'en publie aucune — ajoutez `--ssl-no-revoke` |
| `unknown CA`, `self-signed certificate in chain` | le `ca.crt` n'est pas dans le magasin des racines — c'est l'autre moitié du travail |
| Un certificat installé sur iOS ne change rien | les Réglages de confiance des certificats n'ont jamais été activés pour l'autorité |

### `Connection refused` alors que le conteneur tourne

Docker publie un port **sur une adresse**, et sur cet hôte il a choisi
l'adresse LAN :

```
vssp-vault | Up 2 hours (healthy) | 192.168.1.11:8200->8200/tcp
```

Une liaison écrite ainsi répond là **et nulle part ailleurs** : un
client qui vise `127.0.0.1` est refusé, ce qui ressemble à une panne
alors que le coffre se porte bien. Demandez à docker plutôt que de
supposer :

```bash
docker port vssp-vault 8200/tcp
curl -s http://192.168.1.11:8200/v1/sys/seal-status
```

`install.sh` lit cette liaison et l'écrit dans l'unité sous
`Environment=VSSP_VAULT_ADDR=` ; `systemctl cat vssp-unseal` montre
l'adresse employée. Pour une commande ponctuelle, préfixez-la :
`sudo -u vssp-unseal env VSSP_VAULT_ADDR=http://192.168.1.11:8200 vssp-unseal enroll-keys`.

Les journaux sont dans `journalctl -u vssp-unseal`. Ils portent l'horodatage,
le nom du certificat, l'IP, la MAC vue et le résultat — **jamais** la phrase ni
une part.

## Voir aussi

- [Vault.fr.md](Vault.fr.md) — le coffre lui-même, et pourquoi les secrets ne
  traversent pas la machine à états de Home Assistant
- [../dashboards/Updates.fr.md](../dashboards/Updates.fr.md) — pourquoi un
  coffre scellé ne vide plus l'écran MISES À JOUR
