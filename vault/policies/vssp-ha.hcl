########################################################################
# EN | POLICY FOR HOME ASSISTANT — names, never values.
# FR | POLICY DE HOME ASSISTANT — les noms, jamais les valeurs.
#
# EN | This is the load-bearing piece of the whole design, so it is worth
# EN | being explicit about what it does NOT grant.
# EN | Anything Home Assistant reads becomes an entity state or attribute,
# EN | and every entity state is written in clear text to
# EN | home-assistant_v2.db by the recorder, shown in Developer Tools >
# EN | States to any administrator, and liable to appear in automation
# EN | traces. A safe whose contents are copied into that database the
# EN | moment they are displayed is decorative.
# EN | So the token carrying this policy is given `secret/metadata/*` and
# EN | NOTHING on `secret/data/*`. In KV v2 those are two separate paths:
# EN | metadata holds the entry names, creation and update times and
# EN | version numbers; data holds the values. Home Assistant can list and
# EN | describe every entry in the safe and is refused, by Vault itself,
# EN | if it ever asks for one. This is not a rule the templates promise
# EN | to respect — it is a rule they cannot break.
# FR | C est la piece porteuse de tout le dispositif, donc il vaut la
# FR | peine d etre explicite sur ce qu elle n accorde PAS.
# FR | Tout ce que Home Assistant lit devient un etat ou un attribut
# FR | d entite, et tout etat d entite est ecrit en clair dans
# FR | home-assistant_v2.db par le recorder, affiche dans Outils de
# FR | developpement > Etats a tout administrateur, et susceptible
# FR | d apparaitre dans les traces d automatisation. Un coffre dont le
# FR | contenu est recopie dans cette base des qu il s affiche est
# FR | decoratif.
# FR | Le token portant cette policy recoit donc `secret/metadata/*` et
# FR | RIEN sur `secret/data/*`. En KV v2 ce sont deux chemins distincts :
# FR | metadata porte les noms d entrees, les dates de creation et de mise
# FR | a jour et les numeros de version ; data porte les valeurs. Home
# FR | Assistant peut lister et decrire chaque entree du coffre, et se
# FR | fait refuser par Vault lui-meme s il en demande une. Ce n est pas
# FR | une regle que les templates promettent de respecter — c est une
# FR | regle qu ils ne peuvent pas enfreindre.
########################################################################

# EN | List the entries of a branch and read their metadata.
# FR | Lister les entrees d une branche et lire leurs metadonnees.
path "secret/metadata/vssp/*" {
  capabilities = ["list", "read"]
}

# EN | The branch roots themselves, so a LIST at the top level works.
# FR | Les racines de branche elles-memes, pour qu un LIST au niveau
# FR | superieur fonctionne.
path "secret/metadata/vssp" {
  capabilities = ["list", "read"]
}

# EN | DELETE — the one write Home Assistant is allowed, and the reason it
# EN | is allowed is that it involves no value. `delete` on the data path
# EN | soft-deletes the latest version (recoverable with undelete);
# EN | `delete` on the metadata path destroys the entry and every version
# EN | of it, irreversibly. Both are exposed, because "remove an entry I
# EN | no longer use" is part of what the ADMIN screen is for — but the
# EN | screen asks for confirmation naming the entry before the second
# EN | one, the same way uninstalling an integration does.
# EN | Note there is no `read` here: Home Assistant can delete a secret it
# EN | is unable to look at.
# FR | SUPPRESSION — la seule ecriture autorisee a Home Assistant, et si
# FR | elle l est c est qu elle ne met en jeu aucune valeur. `delete` sur
# FR | le chemin data supprime en douceur la derniere version
# FR | (recuperable par undelete) ; `delete` sur le chemin metadata
# FR | detruit l entree et toutes ses versions, irreversiblement. Les deux
# FR | sont exposees, car « retirer une entree dont je ne me sers plus »
# FR | fait partie de la raison d etre de l ecran ADMIN — mais l ecran
# FR | demande confirmation en nommant l entree avant la seconde, comme le
# FR | fait la desinstallation d une integration.
# FR | A noter qu il n y a pas de `read` ici : Home Assistant peut
# FR | supprimer un secret qu il est incapable de regarder.
path "secret/data/vssp/*" {
  capabilities = ["delete"]
}

path "secret/delete/vssp/*" {
  capabilities = ["update"]
}

path "secret/undelete/vssp/*" {
  capabilities = ["update"]
}

# EN | Seal state and token self-inspection. sys/seal-status is
# EN | unauthenticated, so this grant is belt and braces; auth/token/
# EN | lookup-self is what lets the ADMIN screen show when this very token
# EN | expires instead of failing silently on the day it does.
# FR | Etat de scellement et introspection du token. sys/seal-status n est
# FR | pas authentifie, donc cette autorisation est une ceinture en plus
# FR | des bretelles ; auth/token/lookup-self est ce qui permet a l ecran
# FR | ADMIN d afficher quand ce token expire, plutot que d echouer en
# FR | silence le jour venu.
path "sys/seal-status" {
  capabilities = ["read"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
