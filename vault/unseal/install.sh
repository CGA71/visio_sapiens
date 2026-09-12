#!/bin/sh
# EN | Installs the VSSP unseal service. Run with sudo, ONCE, on the host that
# EN | runs the safe. It creates the account, the directories and the systemd
# EN | unit, and it stops there: nothing is started, because there is nothing
# EN | to serve until the keys have been enrolled, and the keys are enrolled by
# EN | the operator typing them — never by this script, never by anyone else.
# FR | Installe le service de descellement VSSP. A lancer avec sudo, UNE fois,
# FR | sur l hote qui fait tourner le coffre. Il cree le compte, les
# FR | repertoires et l unite systemd, et s arrete la : rien n est demarre,
# FR | parce qu il n y a rien a servir tant que les cles n ont pas ete
# FR | enrolees, et les cles sont enrolees par l operateur qui les tape —
# FR | jamais par ce script, jamais par quiconque d autre.
set -e

USER_NAME=vssp-unseal
LIB=/usr/local/lib/vssp-unseal
ETC=/etc/vssp-unseal
VAR=/var/lib/vssp-unseal
BIN=/usr/local/bin/vssp-unseal
UNIT=/etc/systemd/system/vssp-unseal.service
SRC=$(cd "$(dirname "$0")" && pwd)

[ "$(id -u)" = 0 ] || { echo "[ERR] run this with sudo"; exit 1; }
[ -f "$SRC/vssp_unseal.py" ] || { echo "[ERR] vssp_unseal.py not beside this script"; exit 1; }

python3 -c 'import cryptography' 2>/dev/null || {
  echo "[ERR] python3-cryptography is missing:  apt-get install python3-cryptography"
  exit 1
}

# EN | A system account with no shell and no home to log into. It needs to read
# EN | the encrypted shares, read the certificates and write the lockout
# EN | counter, and nothing else on this machine.
# FR | Un compte systeme sans shell et sans repertoire personnel ou se
# FR | connecter. Il doit lire les parts chiffrees, lire les certificats et
# FR | ecrire le compteur de blocage, et rien d autre sur cette machine.
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd --system --no-create-home --home-dir "$VAR" \
          --shell /usr/sbin/nologin "$USER_NAME"
  echo "[OK] created the $USER_NAME account"
fi

install -d -m 0755 "$LIB"
install -m 0755 "$SRC/vssp_unseal.py" "$LIB/vssp_unseal.py"
ln -sf "$LIB/vssp_unseal.py" "$BIN"

# EN | 0700, owned by the service account. The encrypted shares live here, and
# EN | the passphrase is the only thing between that file and the safe: no
# EN | other account on this host has any business listing this directory.
# FR | 0700, possede par le compte de service. Les parts chiffrees vivent ici,
# FR | et la phrase secrete est la seule chose entre ce fichier et le coffre :
# FR | aucun autre compte de cet hote n a a lister ce repertoire.
install -d -m 0700 -o "$USER_NAME" -g "$USER_NAME" "$ETC"
install -d -m 0700 -o "$USER_NAME" -g "$USER_NAME" "$VAR"
install -d -m 0700 -o "$USER_NAME" -g "$USER_NAME" "$VAR/devices"

# EN | Where is the safe, really? The container publishes its port on one
# EN | address, and on this host that address is the LAN one, not the loopback
# EN | — a client aiming at 127.0.0.1 is refused and misreads it as an outage.
# EN | Ask docker rather than assume; 0.0.0.0 means "every address", and the
# EN | loopback is the right one to pick out of it.
# FR | Ou est le coffre, vraiment ? Le conteneur publie son port sur une
# FR | adresse, et sur cet hote c est l adresse LAN, pas la boucle locale — un
# FR | client qui vise 127.0.0.1 est refuse et le prend pour une panne.
# FR | Demander a docker plutot que supposer ; 0.0.0.0 veut dire "toutes les
# FR | adresses", et la boucle locale est celle a retenir dedans.
VAULT_ADDR=${VSSP_VAULT_ADDR:-}
if [ -z "$VAULT_ADDR" ] && command -v docker >/dev/null 2>&1; then
  published=$(docker port vssp-vault 8200/tcp 2>/dev/null | head -n 1 | tr -d '
')
  case "$published" in
    0.0.0.0:*)  VAULT_ADDR="http://127.0.0.1:${published##*:}" ;;
    "[::]":*)   VAULT_ADDR="http://127.0.0.1:${published##*:}" ;;
    ?*:*)       VAULT_ADDR="http://$published" ;;
  esac
fi
[ -n "$VAULT_ADDR" ] || VAULT_ADDR=http://192.168.1.11:8200
echo "[OK] vault at $VAULT_ADDR"

# EN | The hardening below is not decoration. This process holds, for the
# EN | length of one request, the three shares that open the safe. Everything
# EN | here narrows what a flaw in it could reach: no privilege escalation, no
# EN | writable filesystem beyond its own state, no home directories, no device
# EN | nodes, no address families but IP, and no memory that is both writable
# EN | and executable.
# FR | Le durcissement ci-dessous n est pas decoratif. Ce processus detient, le
# FR | temps d une requete, les trois parts qui ouvrent le coffre. Tout ici
# FR | reduit ce qu un defaut en lui pourrait atteindre : pas d elevation de
# FR | privileges, pas de systeme de fichiers inscriptible au-dela de son
# FR | propre etat, pas de repertoires personnels, pas de peripheriques, pas de
# FR | familles d adresses autres qu IP, et pas de memoire a la fois
# FR | inscriptible et executable.
cat > "$UNIT" <<UNITEOF
[Unit]
Description=Visio Sapiens - unseal Vault from an enrolled device
Documentation=file://$LIB/vssp_unseal.py
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
Environment=VSSP_VAULT_ADDR=$VAULT_ADDR
ExecStart=/usr/bin/python3 $LIB/vssp_unseal.py serve
Restart=on-failure
RestartSec=5

NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
RestrictNamespaces=yes
RestrictAddressFamilies=AF_INET AF_INET6
LockPersonality=yes
MemoryDenyWriteExecute=yes
SystemCallArchitectures=native
SystemCallFilter=@system-service
CapabilityBoundingSet=
ReadWritePaths=$ETC $VAR

[Install]
WantedBy=multi-user.target
UNITEOF

systemctl daemon-reload
echo "[OK] installed $UNIT (not started)"
echo
echo "Next, on this host, in this order:"
echo
echo "  1. This host's certificate - list every address a device will use:"
echo "       sudo -u $USER_NAME $BIN enroll-server 192.168.1.11"
echo
echo "  2. The keys. It asks for three unseal keys and a passphrase, none of"
echo "     them echoed. Do this while the safe is SEALED so each key is"
echo "     verified against Vault before anything is written:"
echo "       sudo -u $USER_NAME $BIN enroll-keys"
echo
echo "  3. One certificate per device:"
echo "       sudo -u $USER_NAME $BIN enroll-device 'telephone'"
echo "       sudo -u $USER_NAME $BIN enroll-device 'pc-perso'"
echo "     then copy $VAR/devices/*.p12 and $ETC/ca.crt to the devices."
echo
echo "  4. Start it:"
echo "       sudo systemctl enable --now vssp-unseal"
echo
echo "Nothing is served until step 4, and nothing at all without a client"
echo "certificate issued in step 3."
