########################################################################
# EN | POLICY FOR THE ADMINISTRATOR — the one that may see values.
# FR | POLICY DE L ADMINISTRATEUR — celle qui peut voir les valeurs.
#
# EN | Carried by the short-lived token the VAULT screen obtains when you
# EN | log in with userpass. It never reaches Home Assistant: the browser
# EN | asks Vault directly, so a revealed password travels from the safe
# EN | to the screen without passing through the state machine, the
# EN | recorder database or any log. The token lives in sessionStorage and
# EN | dies with the tab.
# EN | Scoped to secret/vssp/* — the safe can hold other things for other
# EN | tools without this policy reaching them.
# FR | Portee par le token de courte duree que l ecran COFFRE-FORT obtient
# FR | quand tu te connectes en userpass. Il n atteint jamais Home
# FR | Assistant : le navigateur interroge Vault directement, donc un mot
# FR | de passe revele va du coffre a l ecran sans passer par le state
# FR | machine, la base du recorder ni aucun journal. Le token vit en
# FR | sessionStorage et meurt avec l onglet.
# FR | Limite a secret/vssp/* — le coffre peut abriter autre chose pour
# FR | d autres outils sans que cette policy y touche.
########################################################################

# EN | Full CRUD on the values.
# FR | CRUD complet sur les valeurs.
path "secret/data/vssp/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# EN | Entry names, version history, and destroying an entry outright.
# FR | Noms d entrees, historique des versions, et destruction complete
# FR | d une entree.
path "secret/metadata/vssp/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/vssp" {
  capabilities = ["list", "read"]
}

# EN | Soft-delete, restore and permanent destruction of single versions.
# EN | `undelete` is the reason KV v2 was chosen over v1: overwriting a
# EN | password by mistake is recoverable instead of final.
# FR | Suppression douce, restauration et destruction definitive de
# FR | versions individuelles. `undelete` est la raison du choix de KV v2
# FR | plutot que v1 : ecraser un mot de passe par erreur se rattrape au
# FR | lieu d etre definitif.
path "secret/delete/vssp/*" {
  capabilities = ["update"]
}

path "secret/undelete/vssp/*" {
  capabilities = ["update"]
}

path "secret/destroy/vssp/*" {
  capabilities = ["update"]
}

path "sys/seal-status" {
  capabilities = ["read"]
}

# EN | Renew the session rather than forcing a fresh login every hour of
# EN | continuous work, and let the screen show its own expiry.
# FR | Renouveler la session plutot que d imposer une reconnexion toutes
# FR | les heures de travail continu, et permettre a l ecran d afficher sa
# FR | propre expiration.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/revoke-self" {
  capabilities = ["update"]
}
