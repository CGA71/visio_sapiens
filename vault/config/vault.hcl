########################################################################
# EN | HashiCorp Vault — server configuration for the Visio Sapiens safe.
# FR | HashiCorp Vault — configuration serveur du coffre Visio Sapiens.
#
# EN | Runs as a Docker container on the 192.168.1.11 host, NOT inside
# EN | k3s. That is deliberate: the safe holds the SSH and k3s access
# EN | credentials, so putting it inside the cluster it protects would
# EN | lock the keys to the cluster inside the cluster. Docker on the host
# EN | survives a k3s failure; it does not survive a host failure, hence
# EN | the break-glass copy described in docs/Vault.md.
# FR | Tourne en conteneur Docker sur l hote 192.168.1.11, PAS dans k3s.
# FR | C est deliberé : le coffre detient les acces SSH et k3s, donc le
# FR | placer dans le cluster qu il protege enfermerait les cles du
# FR | cluster dans le cluster. Docker sur l hote survit a une panne k3s ;
# FR | il ne survit pas a une panne de l hote, d ou la copie de bris de
# FR | glace decrite dans docs/Vault.fr.md.
########################################################################

# EN | File storage, not the in-memory dev backend: the safe must survive
# EN | a container restart. The path is a Docker named volume, so
# EN | `docker compose down` does NOT erase it — only an explicit
# EN | `docker volume rm` does.
# FR | Stockage fichier, pas le backend dev en memoire : le coffre doit
# FR | survivre a un redemarrage du conteneur. Le chemin est un volume
# FR | Docker nomme, donc `docker compose down` ne l efface PAS — seul un
# FR | `docker volume rm` explicite le fait.
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address = "0.0.0.0:8200"

  # EN | TLS off on purpose, and this is the one real compromise of the
  # EN | setup. The safe is reachable only on the LAN, and Home Assistant
  # EN | itself is served over plain http on the same host, so terminating
  # EN | TLS here would protect a hop that is already the least exposed
  # EN | part of the path while adding a certificate to renew and a
  # EN | browser warning inside the ADMIN iframe. Turn it on the day the
  # EN | safe becomes reachable from outside the LAN — see docs/Vault.md,
  # EN | which spells out exactly what changes.
  # FR | TLS desactive volontairement, et c est le seul vrai compromis de
  # FR | l installation. Le coffre n est joignable que sur le reseau
  # FR | local, et Home Assistant lui-meme est servi en http simple sur le
  # FR | meme hote : terminer TLS ici protegerait le saut deja le moins
  # FR | expose du trajet, tout en ajoutant un certificat a renouveler et
  # FR | un avertissement navigateur dans l iframe ADMIN. A activer le
  # FR | jour ou le coffre devient joignable hors du reseau local — voir
  # FR | docs/Vault.fr.md, qui detaille exactement ce qui change.
  tls_disable = 1
}

# EN | The address Vault hands out to clients. Must be the address the
# EN | browser and Home Assistant actually use, not 127.0.0.1: a redirect
# EN | to localhost would send the ADMIN iframe to the visitor's own
# EN | machine.
# FR | L adresse que Vault communique aux clients. Doit etre celle
# FR | qu utilisent reellement le navigateur et Home Assistant, pas
# FR | 127.0.0.1 : une redirection vers localhost enverrait l iframe ADMIN
# FR | sur la machine du visiteur.
api_addr = "http://192.168.1.11:8200"

ui = true

# EN | Auto-unseal is NOT configured. Vault seals itself on every restart
# EN | and answers 503 until three of the five unseal keys are entered by
# EN | hand. That is an operational cost accepted on purpose: the
# EN | alternatives (a cloud KMS, or unseal keys sitting on the same disk)
# EN | either add an external dependency to a local-only setup or defeat
# EN | sealing altogether. The ADMIN screen shows the seal state in plain
# EN | sight so a sealed safe is never a mystery.
# FR | Le descellement automatique n est PAS configure. Vault se rescelle
# FR | a chaque redemarrage et repond 503 tant que trois des cinq cles de
# FR | descellement ne sont pas saisies a la main. C est un cout
# FR | d exploitation accepte volontairement : les alternatives (un KMS
# FR | cloud, ou des cles de descellement posees sur le meme disque)
# FR | ajoutent une dependance externe a une installation purement locale
# FR | ou annulent purement et simplement le scellement. L ecran ADMIN
# FR | affiche l etat de scellement en evidence, pour qu un coffre scelle
# FR | ne soit jamais une enigme.
