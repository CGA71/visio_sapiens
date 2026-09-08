# EN | Pinned, not :latest. A safe that silently changes major version
# EN | under a home instance during a routine add-on rebuild is not a
# EN | convenience; storage and seal formats are exactly the kind of thing
# EN | that must move deliberately.
# FR | Version figee, pas :latest. Un coffre qui change de version majeure
# FR | en silence sous une instance domestique lors d une reconstruction
# FR | de routine n est pas un confort ; les formats de stockage et de
# FR | scellement sont exactement ce qui doit bouger deliberement.
FROM hashicorp/vault:1.20

# EN | jq reads /data/options.json, the file the Supervisor writes from the
# EN | add-on's configuration form. The base image is Alpine, so this is
# EN | one small package rather than a second toolchain.
# FR | jq lit /data/options.json, le fichier que le Superviseur ecrit
# FR | depuis le formulaire de configuration de l add-on. L image de base
# FR | est Alpine, c est donc un seul petit paquet plutot qu une seconde
# FR | chaine d outils.
RUN apk add --no-cache jq

COPY run.sh /run.sh
RUN chmod +x /run.sh

# EN | The base image's entrypoint wraps `vault` with dev-mode niceties and
# EN | its own signal handling. Clearing it leaves run.sh as PID 1, which
# EN | is what `init: false` in config.yaml already told the Supervisor to
# EN | expect.
# FR | L entrypoint de l image de base enveloppe `vault` avec des facilites
# FR | de mode dev et sa propre gestion des signaux. Le vider laisse run.sh
# FR | en PID 1, ce que `init: false` dans config.yaml a deja annonce au
# FR | Superviseur.
ENTRYPOINT []
CMD ["/run.sh"]
