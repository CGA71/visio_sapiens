# Visio Sapiens — Sécurité

**Français** · [English](Security.md)

## État actuel (bilan honnête)

Le contrôle d'accès est minimal aujourd'hui, et ce document existe
pour le dire clairement plutôt que de le laisser tacite :

- La console ADMIN et chaque dashboard reposent entièrement sur
  **l'authentification native de Home Assistant** (quiconque est
  connecté au frontend HA peut ouvrir `/visio-sapiens-admin`). Il
  n'existe aucun écran de connexion propre à Visio Sapiens.
- Le seul verrou dédié existant aujourd'hui est le bouton **DELETE
  DASHBOARD** : `input_text.vssp_admin_pin` (le code de référence,
  défini une fois via le script `vssp_set_admin_pin`) comparé à
  `input_text.vssp_pin_entry` (ce que l'utilisateur saisit) — voir
  `vssp_admin_config.yaml` et `docs/Troubleshooting.md`. Il protège une
  seule action destructrice, pas la console elle-même.
- Chaque webhook ajouté par ce projet (ASSIGN, ROOMS, THEME) est
  `local_only: true` — une restriction réseau, pas une vérification
  d'identité. Quiconque sur le réseau local connaît (ou devine)
  l'identifiant du webhook peut l'appeler.
- Le **serveur MCP** (`addons/vssp-mcp`, `kubernetes/mcp`) écoute sur le
  port 8099 et, contrairement à tout ce qui précède, ne se trouve **pas**
  derrière l'authentification de Home Assistant : c'est son propre
  service HTTP. Son option `api_token` est la seule barrière, elle est
  vide par défaut, et le serveur affiche un avertissement à chaque
  démarrage quand c'est le cas. Laissé vide, ce port est une lecture non
  authentifiée de l'état de chaque entité de la maison — les outils sont
  en lecture seule, mais c'est précisément la lecture qui fuit.
  Posez-le. Voir [MCP_Server](MCP_Server.fr.md).

Rien de tout cela n'est un système de connexion. C'est précisément
l'écart que la conception ci-dessous vise à combler.

## Prévu : reconnaissance faciale + code à 6 chiffres (pas encore implémenté)

**Contexte qui façonne la conception** : ce projet s'utilise
exclusivement depuis une tablette ou un téléphone — deux appareils qui
partagent un point commun pertinent, une caméra frontale. C'est ce qui
rend la reconnaissance faciale viable comme verrou ici, sans ajouter de
matériel.

**Le flux prévu**, tel que spécifié par le porteur du projet :

1. La **reconnaissance faciale** via la caméra frontale de l'appareil
   identifie la personne.
2. **Un code à 6 chiffres** est requis en plus de la reconnaissance
   faciale — deux facteurs, pas un seul, avant que Visio Sapiens
   n'octroie les droits d'utilisation (c'est-à-dire déverrouille
   l'interface pour un usage normal).
3. Séparément, **un code de sécurité unique** existe pour tout
   débloquer — un déverrouillage global, distinct du code à 6 chiffres
   ci-dessus.

## Questions de conception ouvertes

Consignées ici pour que le prochain passage d'implémentation parte
d'une liste de décisions, pas d'une page blanche :

- **Où la reconnaissance faciale s'exécute-t-elle réellement ?** Deux
  voies très différentes :
  - l'API biométrique native de l'appareil (ex. authentificateur de
    plateforme WebAuthn, Face ID / prompt biométrique Android exposé
    au navigateur) — aucune image ne quitte jamais l'appareil, mais
    cela lie le contrôle à « cet appareil/utilisateur précis déjà
    enrôlé », pas littéralement à un visage que Visio Sapiens compare
    lui-même ;
  - une photo capturée comparée à une référence par un modèle de
    reconnaissance — fonctionne sur n'importe quel appareil, mais
    impose de décider où tourne le modèle (localement sur le pod HA vs
    un service externe) et où la photo de référence est stockée.
- **Le code à 6 chiffres est-il par personne ou partagé ?** Le modèle
  actuel `vssp_admin_pin` est un secret unique partagé. Un code par
  personne suppose un petit registre d'utilisateurs qui n'existe pas
  encore.
- **Que débloque exactement le code maître ?** Candidats : contourner
  visage+code entièrement pour cette session, octroyer des droits
  admin ponctuels, ou désactiver le verrou jusqu'à réarmement. Ces
  options ont des rayons d'impact très différents et demandent
  probablement des flux de confirmation différents (comparer avec le
  motif de confirmation déjà en place pour DELETE DASHBOARD).
- **Où ce verrou s'applique-t-il ?** Seulement à l'entrée de la console
  ADMIN, ou sur chaque dashboard (HOME, dashboards de pièce, ENERGY
  aussi) ? Le patron iframe + webhook utilisé par ASSIGN/ROOMS/THEME
  (`local_only: true`, aucun jeton porteur dans le navigateur — voir
  `docs/Design_System_Editor.md`) est le précédent le plus proche pour
  « vérifier quelque chose côté serveur sans faire confiance au
  navigateur », et ce que deviendra ce verrou devrait le suivre plutôt
  que d'inventer un nouveau modèle de confiance.
- **Gestion des échecs** : que se passe-t-il quand la reconnaissance
  faciale échoue de manière répétée (éclairage, angle de caméra) — un
  repli sur le code seul après N tentatives, ou un blocage dur ? Un
  blocage sans surveillance sur le seul appareil qui pilote la maison
  est une panne en soi.

Cette section sera remplacée par un compte-rendu d'implémentation
(modèle, flux de données, noms de packages/scripts) une fois ces points
tranchés — la forme déjà utilisée pour THEME
(`docs/Design_System_Editor.md`) est le gabarit à suivre : un document
concret du pipeline, pas seulement une liste d'intentions.
