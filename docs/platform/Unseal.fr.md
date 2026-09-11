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

### Sur les appareils

Copiez `/var/lib/vssp-unseal/devices/<nom>.p12` et `/etc/vssp-unseal/ca.crt`
sur l'appareil, puis importez-les :

- **iOS** — ouvrir le fichier, Réglages → Profil téléchargé, puis Réglages →
  Général → Informations → Certificats de confiance pour approuver le `ca.crt`.
- **Android** — Paramètres → Sécurité → Chiffrement → Installer un certificat.
- **Firefox** — Paramètres → Vie privée → Certificats → Afficher les
  certificats → Vos certificats → Importer.
- **Chrome / Edge / Safari** — importer dans le magasin du système.

Le `.p12` est protégé par un mot de passe d'export qui lui est propre, demandé
à l'étape 3 : le fichier doit voyager jusqu'à l'appareil, et il ne doit pas
être une identité utilisable pendant le trajet. Supprimez-le une fois importé.

## Au quotidien

`GET /status` et `POST /unseal` sur `https://<hôte>:8443`, certificat client
obligatoire.

```bash
curl --cert telephone.pem --cacert ca.crt https://192.168.1.11:8443/status
curl --cert telephone.pem --cacert ca.crt -X POST \
     -d '{"passphrase":"..."}' https://192.168.1.11:8443/unseal
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
