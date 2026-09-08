# Visio Sapiens — Rétention des sauvegardes

**Français** · [English](Backup_Retention.md)

## Pourquoi ce mécanisme existe

Plusieurs actions du projet écrivent une sauvegarde horodatée avant
d'écraser quelque chose, sur le principe qu'aucune action destructrice
ne doit être sans retour :

| Ce qui crée la sauvegarde | Où elle est écrite | Format |
|---|---|---|
| `shell_command.vssp_backup_dashboard` (HOME) | `/config/vssp/backups/` | `home_<AAAAMMJJ>_<HHMMSS>.yaml` |
| `shell_command.vssp_backup_energy` | `/config/vssp/backups/` | `energy_<AAAAMMJJ>_<HHMMSS>.yaml` |
| REGENERER CORE (`vssp_admin_config.yaml`) | `/config/vssp/backups/` | `core_<AAAAMMJJ>_<HHMMSS>.yaml` |
| `shell_command.vssp_backup_theme` (`packages/vssp_theme.yaml`) | `/config/vssp/backups/` | `theme_<AAAAMMJJ>_<HHMMSS>.yaml` |
| `vssp_assign_apply.py`, avant d'écrire `house.yaml` | `dashboards/model/backups/` | `house_<AAAAMMJJ>_<HHMMSS>.yaml` |
| `vssp_rooms_apply.py`, avant d'écrire `house.yaml` | `dashboards/model/backups/` | `house_<AAAAMMJJ>_<HHMMSS>.yaml` |
| `vssp_theme_apply.py`, avant d'écrire `design_system.yaml` | `dashboards/model/backups/` | `design_system_<AAAAMMJJ>_<HHMMSS>.yaml` |

Aucun d'eux ne supprimait jamais une ancienne sauvegarde. Constaté sur
la première instance réelle vérifiée : **62 fichiers** dans
`/config/vssp/backups/` remontant à trois semaines, plus de la moitié
écrits à quelques minutes d'intervalle pendant une seule session de
test. Laissé tel quel, ça grossit sans limite.

## Comment fonctionne la rotation

**`vssp/vssp_prune_backups.py`** regroupe les fichiers d'un répertoire
par préfixe (la partie avant `_<AAAAMMJJ>_<HHMMSS>.yaml` — `home`,
`energy`, `core`, `theme`, `house`, `design_system`, ...) et ne garde
que les `--keep` plus récents par préfixe (5 par défaut), triés par
date de modification. Un fichier qui ne correspond pas à cette
convention de nommage est signalé et laissé intact — jamais deviné ni
balayé par accident.

**`home-assistant/packages/vssp_maintenance.yaml`** le lance une fois
par jour (`04:45`, quinze minutes après le filet de sécurité quotidien
d'ENERGY déjà existant dans `vssp_energy_totaux.yaml`, pour éviter
d'empiler la charge des shell_command sur la même minute) sur les deux
répertoires de sauvegarde :

```
shell_command.vssp_prune_backups
  --dir /config/vssp/backups
  --dir /config/dashboards/model/backups
  --keep 5
```

Pas de `persistent_notification` — même retenue que le sync quotidien
ENERGY : un entretien de routine qui réussit chaque jour ne vaut pas
une alerte pour toujours. Le résultat du dernier passage reste
consultable à `/local/vssp/prune_status.json` (détail par répertoire et
par préfixe de ce qui a été gardé et supprimé).

## Le lancer à la main

```bash
# voir ce qui serait supprimé, sans rien supprimer
python3 vssp/vssp_prune_backups.py --dir /config/vssp/backups --keep 5 --dry-run

# purger reellement
python3 vssp/vssp_prune_backups.py \
  --dir /config/vssp/backups \
  --dir /config/dashboards/model/backups \
  --keep 5
```

Pour changer le nombre de sauvegardes conservées, modifier la valeur
`--keep` dans le shell_command `vssp_prune_backups` de
`vssp_maintenance.yaml` — il n'y a pas de contrôle dans la console
ADMIN pour ça (ça ne semblait pas justifier un bouton d'interface pour
un nombre qu'on fixe une fois et qu'on revisite rarement).

## Ce que ça ne touche PAS

- **`/config/backups`** — le système natif de sauvegardes complètes de
  Home Assistant (`ha backups new`, utilisé par `deploy:production`
  avant chaque publication). Un mécanisme totalement différent ; ce
  package n'a aucun avis sur sa rétention.
- **`home-assistant_v2.db`** — la base de données recorder en direct.
