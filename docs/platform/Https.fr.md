# HTTPS — Home Assistant derrière Traefik

Ajoute le chiffrement sur le port **443** en réutilisant le Traefik que k3s
fait déjà tourner. **Le port 8123 continue de servir en clair, inchangé.**

---

## Pourquoi

Aujourd'hui, votre mot de passe Home Assistant et chacun de vos jetons longue
durée traversent le réseau **en clair** sur le port 8123. C'est tout
l'argument, et il suffit.

Ce n'est en revanche **pas nécessaire au descellement** : le service
[`vssp-unseal`](Unseal.fr.md) a son propre TLS sur 8443, en TLS mutuel, et la
phrase secrète ne passe jamais par Home Assistant. Les deux sujets sont
indépendants.

## Additif, pas une bascule

8123 reste ouvert, et c'est délibéré :

- le test de fumée de la CI vise `$STAGING_URL` ;
- les capteurs `command_line` et les scripts internes y pointent ;
- **c'est votre porte de secours** si la configuration du proxy est fausse.

Remplacer 8123 au lieu de s'y ajouter ferait qu'une erreur dans
`trusted_proxies` vous enfermerait dehors de la machine qui contient le
correctif.

---

## Le problème du proxy

**C'est le piège de cette installation, et il est silencieux.**

Sans proxy, Home Assistant voit l'adresse du navigateur. Derrière Traefik, il
ne la voit plus : **chaque requête lui arrive depuis l'adresse du pod
Traefik**, et l'adresse réelle du client ne survit que dans l'en-tête
`X-Forwarded-For`.

Trois comportements en découlent, et aucun n'est évident :

| Configuration | Ce qui se passe |
|---|---|
| Rien de posé | Tous les clients deviennent une seule adresse. Le bannissement d'IP bannit tout le monde ou personne, `trusted_networks` ne veut plus rien dire, et les journaux sont inutilisables. |
| `use_x_forwarded_for: true` **sans** `trusted_proxies` | Home Assistant **refuse la configuration** au démarrage. |
| En-tête reçu d'une adresse non approuvée | Home Assistant **refuse la requête en 400**. |

Le troisième cas est le méchant. Un ingress posé sans le bloc `http:`
correspondant produit **un site qui ne répond que des erreurs**, avec la cause
dans un journal que personne ne regarde encore. Depuis le navigateur, ça
ressemble à une panne du serveur.

### La solution

Dans `configuration.yaml`, puis redémarrer Home Assistant :

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 10.42.0.0/16      # le réseau des pods k3s — VÉRIFIEZ la vôtre, voir plus bas
```

Les requêtes qui arrivent **directement sur 8123** ne portent aucun
`X-Forwarded-For` : ces deux lignes ne les affectent pas. C'est ce qui rend la
manœuvre sûre.

### Trouver la bonne valeur

`10.42.0.0/16` est le réseau de pods par défaut de k3s, pas une garantie.
`k8s/apply-https.sh` la lit dans le cluster et vous l'affiche :

```bash
kubectl get nodes -o jsonpath='{.items[0].spec.podCIDR}'
kubectl get pods -A -l app.kubernetes.io/name=traefik -o jsonpath='{.items[*].status.podIP}'
```

**L'autorité en la matière n'est aucune des deux : c'est Home Assistant.** S'il
répond 400, son journal nomme l'adresse exacte :

```bash
kubectl logs -n homeassistant -l app=homeassistant --tail=50 | grep -i forwarded
```

> `Received X-Forwarded-For header from an untrusted proxy 10.42.0.14`

Mettez **cette** adresse, ou un CIDR qui la contient, dans `trusted_proxies`.
Un tutoriel qui supposait un autre CNI vous donnera une valeur plausible et
fausse.

### N'approuvez que le proxy

`trusted_proxies` est une liste de machines autorisées à **affirmer qui est le
client**. Y mettre `0.0.0.0/0` laisse n'importe qui se déclarer n'importe quelle
adresse : le bannissement d'IP et `trusted_networks` deviennent contournables
par un en-tête forgé. La liste doit contenir le proxy, et rien d'autre.

---

## Le second piège : contenu mixte

Une page servie en **HTTPS ne peut pas appeler une adresse en `http://`** — le
navigateur bloque la requête, en silence dans la console. Toute page servie par
Home Assistant qui joint un service en clair cesse donc de fonctionner le jour
où Home Assistant passe en HTTPS.

**Vérifié sur ce dépôt :** aucune page de `www/vssp/` n'est concernée. Les
`fetch` des assistants sont relatifs à Home Assistant, donc same-origin, et ils
suivent le protocole de la page. Le seul `http://` trouvé —
`http://192.168.1.50:11434` dans `vssp_chatbot.html` — est un **placeholder**
dans un champ de saisie : l'appel à Ollama part du serveur, pas du navigateur.

À garder en tête pour toute page ajoutée ensuite.

---

## Installation

```bash
# 1. le certificat de Home Assistant, signé par l'autorité déjà installée
#    sur vos appareils pour le descellement
sudo -u vssp-unseal vssp-unseal issue-cert homeassistant --host 192.168.1.11

# 2. le secret TLS et l'ingress (inspection d'abord)
sudo sh k8s/apply-https.sh --dry-run
sudo sh k8s/apply-https.sh

# 3. le bloc http: ci-dessus dans configuration.yaml, puis redémarrer HA
```

Le script découvre le service Home Assistant au lieu de le supposer : un
manifeste au backend codé en dur qui n'existe pas produit un ingress qui
accepte l'`apply` puis sert du 503 — un échec plus lent et plus déroutant que
refuser tout de suite.

### Une seule autorité

Le certificat de Home Assistant est signé par **la même autorité** que les
certificats d'appareil du descellement. Vous n'installez qu'un `ca.crt` sur le
téléphone, et vous obtenez les deux. Une seconde autorité privée voudrait dire
une chose de plus à installer et à approuver partout ; lui faire confiance est
une décision unique, prise une fois.

### Pourquoi pas de `host:` dans l'ingress

Un `host:` d'Ingress doit être un **nom DNS**. Ce cluster se joint par IP :
`host: 192.168.1.11` est rejeté comme invalide, et un nom que personne ne
résout ne correspond à rien. L'omettre crée un routeur attrape-tout — ce dont a
besoin un service de réseau local adressé par IP — et Traefik sert alors le
certificat nommé dans `tls.secretName`. C'est le certificat, lui, qui porte
l'IP en `subjectAltName`, et c'est cela que le navigateur vérifie.

---

## Dépannage

| Symptôme | Cause |
|---|---|
| `400 Bad Request` sur tout | `trusted_proxies` absent ou faux — lisez le journal, il nomme l'adresse |
| Home Assistant ne démarre plus | `use_x_forwarded_for: true` sans `trusted_proxies` |
| Avertissement de certificat | le `ca.crt` n'est pas approuvé sur l'appareil |
| `503` depuis Traefik | le backend de l'ingress ne pointe pas sur le bon service |
| `404` sur 443 | aucune règle d'ingress ne correspond — l'`apply` n'a pas eu lieu |
| Une page ne charge plus une ressource | contenu mixte : elle appelle du `http://` |
| Tout est cassé | 8123 est toujours là, en clair, inchangé |

## Fichiers

| Chemin | Contenu |
|---|---|
| `k8s/apply-https.sh` | secret TLS, ingress, et détection de `trusted_proxies` |
| `/var/lib/vssp-unseal/certs/homeassistant.{crt,key}` | le certificat servi par Traefik |
| `/etc/vssp-unseal/ca.crt` | l'autorité à approuver sur les appareils |

## Voir aussi

- [Unseal.fr.md](Unseal.fr.md) — le descellement, son TLS mutuel, et pourquoi
  un mot de passe ne doit pas devenir une entité Home Assistant
- [Vault.fr.md](Vault.fr.md) — le coffre-fort
