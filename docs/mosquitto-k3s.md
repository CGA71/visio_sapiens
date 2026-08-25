# Installation de Mosquitto (broker MQTT) sur k3s pour Home Assistant

Déploiement du broker MQTT Mosquitto dans un cluster k3s, dans le même namespace que Home Assistant, avec authentification par mot de passe et exposition via LoadBalancer (ServiceLB intégré à k3s).

## Contexte

- Cluster : k3s (nœud `k3s-master`)
- Namespace : `homeassistant`
- Image : `docker.io/eclipse-mosquitto:2`
- Home Assistant tourne déjà dans ce namespace (déploiement Kubernetes, pas d'add-on Supervisor)

## Architecture du déploiement

Le déploiement se compose de cinq ressources :

| Ressource | Rôle |
|-----------|------|
| ConfigMap `mosquitto-config` | Fichier `mosquitto.conf` |
| Secret `mosquitto-passwd` | Fichier de mots de passe hashés |
| PersistentVolumeClaim `mosquitto-data` | Persistance des messages retained/sessions |
| Deployment `mosquitto` | Le broker + un initContainer pour les permissions |
| Service `mosquitto` (LoadBalancer) | Exposition sur le LAN |

## Point clé : permissions du passwordfile

Mosquitto tourne en uid 1883 et refuse d'ouvrir un fichier de mots de passe monté directement depuis un Secret Kubernetes (problème de permissions sur le montage et ses symlinks `..data/`).

La solution retenue est un **initContainer** qui copie le fichier du Secret vers un `emptyDir`, avec un `chmod 0600`. Mosquitto lit alors un fichier local banal qu'il possède, et le problème de permissions disparaît définitivement.

## Générer le hash du mot de passe

Le Secret ne contient jamais le mot de passe en clair. Générer la ligne hashée avec un pod jetable :

```bash
kubectl run mosqpw --rm -i --restart=Never \
  --image=docker.io/eclipse-mosquitto:2 -- \
  sh -c 'mosquitto_passwd -c -b /tmp/pw hass TON_MOT_DE_PASSE >/dev/null && cat /tmp/pw'
```

Copier la ligne renvoyée (`hass:$7$...`) dans le champ `passwordfile` du Secret ci-dessous.

Pour ajouter d'autres utilisateurs plus tard (un par appareil, plus propre), régénérer les lignes avec `mosquitto_passwd` **sans** le `-c` (qui écrase le fichier), les empiler dans le Secret, puis `kubectl rollout restart deployment/mosquitto -n homeassistant`.

## Manifeste complet (`mosquitto.yaml`)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mosquitto-config
  namespace: homeassistant
data:
  mosquitto.conf: |
    listener 1883
    allow_anonymous false
    password_file /mosquitto/secret/passwordfile
    persistence true
    persistence_location /mosquitto/data/
    log_dest stdout
---
apiVersion: v1
kind: Secret
metadata:
  name: mosquitto-passwd
  namespace: homeassistant
stringData:
  passwordfile: |
    hass:$7$...COLLE_TON_HASH_ICI...
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mosquitto-data
  namespace: homeassistant
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mosquitto
  namespace: homeassistant
spec:
  replicas: 1
  selector:
    matchLabels: {app: mosquitto}
  template:
    metadata:
      labels: {app: mosquitto}
    spec:
      securityContext:
        runAsUser: 1883
        runAsGroup: 1883
        fsGroup: 1883
      initContainers:
        - name: prepare-passwd
          image: docker.io/eclipse-mosquitto:2
          command:
            - sh
            - -c
            - |
              cp /secret-src/passwordfile /passwd/passwordfile
              chmod 0600 /passwd/passwordfile
          volumeMounts:
            - {name: secret, mountPath: /secret-src}
            - {name: passwd, mountPath: /passwd}
      containers:
        - name: mosquitto
          image: docker.io/eclipse-mosquitto:2
          ports:
            - containerPort: 1883
          volumeMounts:
            - {name: config, mountPath: /mosquitto/config}
            - {name: passwd, mountPath: /mosquitto/secret}
            - {name: data,   mountPath: /mosquitto/data}
      volumes:
        - name: config
          configMap: {name: mosquitto-config}
        - name: secret
          secret:
            secretName: mosquitto-passwd
        - name: passwd
          emptyDir: {}
        - name: data
          persistentVolumeClaim: {claimName: mosquitto-data}
---
apiVersion: v1
kind: Service
metadata:
  name: mosquitto
  namespace: homeassistant
spec:
  type: LoadBalancer
  selector: {app: mosquitto}
  ports:
    - port: 1883
      targetPort: 1883
```

## Déploiement

```bash
kubectl apply -f mosquitto.yaml
kubectl -n homeassistant rollout restart deployment/mosquitto
```

## Vérification

```bash
# Le pod doit être 1/1 Running
kubectl -n homeassistant get pod -l app=mosquitto

# ENDPOINTS doit afficher une IP 10.42.x.x:1883 (pas <none>)
kubectl -n homeassistant get endpoints mosquitto

# Le log doit montrer : Opening ipv4 listen socket on port 1883
kubectl -n homeassistant logs -l app=mosquitto -c mosquitto --tail=15

# EXTERNAL-IP donne l'adresse du broker (ex. 192.168.1.11)
kubectl -n homeassistant get svc mosquitto
```

Test de bout en bout depuis le nœud (`apt install -y mosquitto-clients`) :

```bash
mosquitto_sub -h 192.168.1.11 -p 1883 -u hass -P 'TON_MOT_DE_PASSE' -t '#' -v
```

Une connexion qui tient sans erreur d'authentification valide broker + port + mot de passe.

## Connexion depuis Home Assistant

**Paramètres → Appareils et services → Ajouter une intégration → MQTT**

| Champ | Valeur |
|-------|--------|
| Broker | `192.168.1.11` (EXTERNAL-IP du Service) |
| Port | `1883` |
| Utilisateur | `hass` |
| Mot de passe | celui défini à la génération du hash |

> Le nom DNS interne `mosquitto.homeassistant.svc.cluster.local` fonctionne aussi, mais l'IP LoadBalancer est plus fiable et sert également aux appareils externes (ESPHome, Zigbee2MQTT, Tasmota...).

## Dépannage

| Symptôme | Cause | Correctif |
|----------|-------|-----------|
| `Unable to open pwfile` | Permissions du Secret monté | L'initContainer (déjà dans le manifeste) règle ça |
| Pod en `Error` / `CrashLoopBackOff` | Secret vide ou tronqué | Vérifier : `kubectl -n homeassistant get secret mosquitto-passwd -o jsonpath='{.data.passwordfile}' \| base64 -d` — doit être une seule ligne complète |
| `ENDPOINTS` = `<none>` | Aucun pod sain derrière le Service | Le broker crashe encore : lire les logs |
| Hostname inconnu depuis HA | DNS cluster non résolu | Utiliser directement l'EXTERNAL-IP `192.168.1.11` |
| `Init:Error` | L'initContainer échoue | `kubectl -n homeassistant logs -l app=mosquitto -c prepare-passwd` |

## Notes

- `type: LoadBalancer` exploite le ServiceLB intégré de k3s : l'IP du service est exposée sur le LAN via l'IP du nœud. Pour un broker interne uniquement (accès HA seul), `type: ClusterIP` suffit.
- Le `fsGroup: 1883` et l'initContainer sont complémentaires : le premier aligne le groupe des volumes, le second garantit un passwordfile lisible quoi qu'il arrive.
- La persistance (`persistence true` + PVC) conserve les messages retained et les sessions entre redémarrages du pod.
