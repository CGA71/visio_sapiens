########################################################################
# EN | POLICY FOR MAINTENANCE — the values, and only these values.
# FR | POLICY DE LA MAINTENANCE — les valeurs, et seulement celles-ci.
#
# EN | The third policy of the safe, and the only one that can read a
# EN | secret VALUE from a machine rather than from a browser. It exists
# EN | because the UPDATES screen was widened to the layer underneath Home
# EN | Assistant — the Ubuntu host, k3s, GitLab, the runner — and reaching
# EN | that layer needs an account on the host and a sudo password.
# FR | La troisieme policy du coffre, et la seule qui puisse lire une
# FR | VALEUR de secret depuis une machine plutot que depuis un
# FR | navigateur. Elle existe parce que l ecran MISES A JOUR a ete elargi
# FR | a la couche sous Home Assistant — l hote Ubuntu, k3s, GitLab, le
# FR | runner — et qu atteindre cette couche demande un compte sur l hote
# FR | et un mot de passe sudo.
#
# EN | WHO CARRIES IT — vssp/vssp_infra_updates.py, and nothing else. The
# EN | token lives in /config/vssp/.vault_maint_token, written 0600 by the
# EN | deploy job from a masked CI variable, exactly like the Livebox
# EN | password in .livebox.env. It is never versioned, never placed in
# EN | secrets.yaml, and never handed to a template.
# FR | QUI LA PORTE — vssp/vssp_infra_updates.py, et rien d autre. Le
# FR | jeton vit dans /config/vssp/.vault_maint_token, ecrit en 0600 par le
# FR | job de deploiement depuis une variable CI masquee, exactement comme
# FR | le mot de passe Livebox dans .livebox.env. Il n est jamais
# FR | versionne, jamais pose dans secrets.yaml, jamais remis a un
# FR | template.
#
# EN | WHY THIS IS NOT A HOLE IN THE DESIGN
# EN | vssp-ha.hcl refuses Home Assistant `secret/data/*` because anything
# EN | Home Assistant reads becomes an entity state, written in clear text
# EN | to home-assistant_v2.db by the recorder and visible in Developer
# EN | Tools to any administrator. That reasoning is about the RECORDER,
# EN | not about secrecy in the abstract.
# EN | A python process is not the recorder. The values this policy grants
# EN | are read into the memory of one short-lived run, handed to ssh or to
# EN | an HTTPS call, and never returned to the caller: the shell_command
# EN | that started the run gets back a count and a status message. Nothing
# EN | reaches an entity, so nothing reaches the database.
# EN | The separation is therefore preserved, and it is preserved the way
# EN | the rest of the safe preserves it — by what Vault refuses, not by
# EN | what a script promises. This token cannot LIST the safe, cannot see
# EN | vssp/accounts or vssp/apps, and cannot write anywhere.
# FR | POURQUOI CE N EST PAS UN TROU DANS LE DISPOSITIF
# FR | vssp-ha.hcl refuse `secret/data/*` a Home Assistant parce que tout
# FR | ce que Home Assistant lit devient un etat d entite, ecrit en clair
# FR | dans home-assistant_v2.db par le recorder et visible dans les Outils
# FR | de developpement par n importe quel administrateur. Ce raisonnement
# FR | porte sur le RECORDER, pas sur le secret dans l abstrait.
# FR | Un processus python n est pas le recorder. Les valeurs qu accorde
# FR | cette policy sont lues dans la memoire d une execution breve,
# FR | remises a ssh ou a un appel HTTPS, et jamais rendues a l appelant :
# FR | le shell_command qui a lance l execution recupere un decompte et un
# FR | message de statut. Rien n atteint une entite, donc rien n atteint la
# FR | base.
# FR | La separation est donc preservee, et elle l est comme le reste du
# FR | coffre la preserve — par ce que Vault refuse, pas par ce qu un
# FR | script promet. Ce jeton ne peut pas LISTER le coffre, ne voit ni
# FR | vssp/accounts ni vssp/apps, et n ecrit nulle part.
#
# EN | WHAT TO PUT IN THE SAFE — from the SAFE screen, category `infra`:
# FR | QUOI METTRE DANS LE COFFRE — depuis l ecran COFFRE-FORT, categorie
# FR | `infra` :
#
#   vssp/infra/host_ssh    host, user, port, private_key
#   vssp/infra/host_sudo   password
#   vssp/infra/gitlab      url, token   (EN | only for a GitLab that is not
#                                        EN | an apt package on the host
#                                        FR | seulement pour un GitLab qui
#                                        FR | n est pas un paquet apt)
#
# EN | INSTALLING THIS POLICY
# FR | INSTALLER CETTE POLICY
#
#   vault policy write vssp-maint vault/policies/vssp-maint.hcl
#   vault token create -policy=vssp-maint -period=768h -field=token
#
# EN | Then paste the token into the masked CI variable VAULT_MAINT_TOKEN
# EN | (Settings > CI/CD > Variables). The next deployment writes it to the
# EN | instance. See docs/platform/Vault.md.
# FR | Puis coller le jeton dans la variable CI masquee VAULT_MAINT_TOKEN
# FR | (Settings > CI/CD > Variables). Le deploiement suivant l ecrit sur
# FR | l instance. Voir docs/platform/Vault.md.
#
# EN | The SSH key this policy hands out should be its own key, created for
# EN | this and nothing else, so revoking maintenance access is deleting
# EN | one line from the host's authorized_keys rather than rotating the
# EN | key someone also uses to log in.
# FR | La cle SSH que distribue cette policy devrait etre sa propre cle,
# FR | creee pour cela et rien d autre, pour que revoquer l acces de
# FR | maintenance soit supprimer une ligne du authorized_keys de l hote
# FR | plutot que faire tourner la cle dont quelqu un se sert aussi pour se
# FR | connecter.
########################################################################

# EN | The values, under infra/ only. Note there is no `list` here and no
# EN | rule on secret/metadata/*: this token can read an entry whose name it
# EN | already knows, and cannot enumerate the safe to discover others.
# EN | The three names it knows are constants in vssp_infra_updates.py.
# FR | Les valeurs, sous infra/ seulement. Noter l absence de `list` et
# FR | l absence de regle sur secret/metadata/* : ce jeton peut lire une
# FR | entree dont il connait deja le nom, et ne peut pas enumerer le coffre
# FR | pour en decouvrir d autres. Les trois noms qu il connait sont des
# FR | constantes de vssp_infra_updates.py.
path "secret/data/vssp/infra/*" {
  capabilities = ["read"]
}

# EN | Enough to know whether the safe is sealed, so the probe can say "the
# EN | safe is sealed" instead of timing out on every entry in turn.
# FR | De quoi savoir si le coffre est scelle, pour que la sonde puisse dire
# FR | « le coffre est scelle » au lieu d expirer sur chaque entree l une
# FR | apres l autre.
path "sys/seal-status" {
  capabilities = ["read"]
}

# EN | A periodic token has to renew itself or it dies at the end of its
# EN | period, and a maintenance token that expires silently turns the
# EN | INFRASTRUCTURE family into "could not be probed" with no other
# EN | symptom. lookup-self is what lets the script report how long it has
# EN | left before that happens.
# FR | Un jeton periodique doit se renouveler ou il meurt a la fin de sa
# FR | periode, et un jeton de maintenance qui expire en silence transforme
# FR | la famille INFRASTRUCTURE en « non sondable » sans autre symptome.
# FR | lookup-self est ce qui permet au script de dire combien de temps il
# FR | lui reste avant cela.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
