# EN | Pinned minor, not :latest. An add-on that silently changes Python
# EN | version under a home instance during a routine rebuild is not a
# EN | convenience.
# FR | Version mineure figee, pas :latest. Un add-on qui change de version
# FR | de Python en silence sous une instance domestique lors d une
# FR | reconstruction de routine n est pas un confort.
FROM python:3.12-alpine

# EN | jq reads /data/options.json, the file the Supervisor writes from the
# EN | add-on's configuration form. Same approach as vssp-vault beside it.
# FR | jq lit /data/options.json, le fichier que le Superviseur ecrit depuis
# FR | le formulaire de configuration de l add-on. Meme approche que
# FR | vssp-vault a cote.
RUN apk add --no-cache jq

# EN | The MCP SDK, and uvicorn to serve it. This is the dependency that
# EN | could never live under vssp/: everything there is copied into
# EN | /config on every instance and must stay stdlib + pyyaml, because a
# EN | Home Assistant OS box is not somewhere you ask a user to run
# EN | `pip install`. In a container, pip is exactly the right answer - the
# EN | rule was never "no dependencies", it was "nothing the appliance has
# EN | to install for you".
# FR | Le SDK MCP, et uvicorn pour le servir. C est la dependance qui n a
# FR | jamais pu vivre sous vssp/ : tout ce qui y est est copie dans
# FR | /config sur chaque instance et doit rester stdlib + pyyaml, parce
# FR | qu une machine Home Assistant OS n est pas un endroit ou l on demande
# FR | a un utilisateur de lancer `pip install`. Dans un conteneur, pip est
# FR | exactement la bonne reponse - la regle n a jamais ete « aucune
# FR | dependance », mais « rien que l appareil doive installer pour toi ».
RUN pip install --no-cache-dir "mcp>=2.2.0" "uvicorn>=0.30"

# EN | THE CODE IS NOT IN THIS IMAGE, ON PURPOSE. vssp_mcp/ is deployed to
# EN | /config/vssp_mcp by the pipeline, alongside vssp/, and read from
# EN | there at start. So the add-on never has to be rebuilt to pick up a
# EN | new version of the server: a deploy is enough, exactly as it is for
# EN | every other piece of this project. The image is the runtime, not the
# EN | product.
# FR | LE CODE N EST PAS DANS CETTE IMAGE, VOLONTAIREMENT. vssp_mcp/ est
# FR | deploye dans /config/vssp_mcp par le pipeline, a cote de vssp/, et lu
# FR | depuis la au demarrage. L add-on n a donc jamais a etre reconstruit
# FR | pour prendre une nouvelle version du serveur : un deploiement suffit,
# FR | exactement comme pour toute autre piece de ce projet. L image est
# FR | l execution, pas le produit.
COPY run.sh /run.sh
RUN chmod +x /run.sh

ENTRYPOINT []
CMD ["/run.sh"]
