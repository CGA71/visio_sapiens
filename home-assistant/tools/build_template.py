#!/usr/bin/env python3
"""Transforme energy.yaml (original) en energy.yaml.j2 (template Jinja2).

Les blocs répétitifs (nav, appareils, circuits) deviennent des boucles ;
toutes les entités deviennent des variables du modèle house.yaml.
Le reste du fichier (styles, chartre graphique, layout) est conservé
strictement à l'identique.
"""
import re
import sys

SRC = "/mnt/user-data/uploads/energy.yaml"
DST = "/home/claude/vssp/energy.yaml.j2"

text = open(SRC, encoding="utf-8").read().replace("\r\n", "\n")

def replace_once(txt, old, new, label):
    if txt.count(old) != 1:
        sys.exit(f"ERREUR [{label}] : {txt.count(old)} occurrence(s) au lieu de 1")
    return txt.replace(old, new)

# ── 1. En-tête : note "fichier généré" ────────────────────────────────
text = replace_once(
    text,
    "########################################################################\n"
    "# Visio Sapiens — ENERGY Dashboard\n",
    "########################################################################\n"
    "# Visio Sapiens — ENERGY Dashboard\n"
    "#\n"
    "# *** FICHIER GÉNÉRÉ — NE PAS ÉDITER À LA MAIN ***\n"
    "# Source : energy.yaml.j2 + model/house.yaml\n"
    "# Régénérer avec : python3 generate_dashboards.py\n",
    "en-tête",
)

# ── 2. Titre / thème / chemins du dashboard ───────────────────────────
text = replace_once(text, "title: ENERGY\ntheme: Visio Sapiens\n",
    "title: {{ energy.title }}\ntheme: {{ house.theme }}\n", "titre racine")
text = replace_once(text, "  - title: ENERGY\n    path: energy\n",
    "  - title: {{ energy.title }}\n    path: {{ energy.view_path }}\n", "titre vue")
text = replace_once(text,
    '            icon: mdi:chevron-left\n            name: ENERGY\n            label: "Energy Management"',
    '            icon: mdi:chevron-left\n            name: {{ energy.title }}\n            label: "{{ energy.subtitle }}"',
    "page header")
text = replace_once(text, "navigation_path: /vssp-energy/energy",
    "navigation_path: /{{ energy.url_path }}/{{ energy.view_path }}", "nav path header")
text = replace_once(text,
    'url("/local/vssp/backgrounds/energy.png")',
    'url("{{ energy.background }}")', "background")

# ── 3. Entités simples → variables (partout, y compris dans le JS) ────
entity_map = {
    "weather.maison": "{{ house.weather_entity }}",
    "sensor.time": "{{ house.time_entity }}",
    "input_select.vssp_energy_period": "{{ energy.period_helper }}",
    "input_number.vssp_solar_capacity": "{{ energy.solar.capacity_helper }}",
    "input_number.vssp_tarif_revente": "{{ energy.solar.tarif_helper }}",
    "binary_sensor.solar_inverter_running": "{{ energy.solar.inverter_running }}",
    "sensor.solar_power_production": "{{ energy.solar.power }}",
    "sensor.solar_energy_today": "{{ energy.solar.today }}",
    "sensor.solar_energy_this_month": "{{ energy.solar.month }}",
    "sensor.solar_energy_this_year": "{{ energy.solar.year }}",
    "sensor.home_power_consumption": "{{ energy.totals.power }}",
    "sensor.home_energy_today": "{{ energy.totals.today }}",
    "sensor.home_energy_this_month": "{{ energy.totals.month }}",
    "sensor.home_energy_this_year": "{{ energy.totals.year }}",
    "sensor.grid_import_power": "{{ energy.grid.import_power }}",
    "sensor.grid_export_power": "{{ energy.grid.export_power }}",
    "sensor.grid_export_energy_today": "{{ energy.grid.export_today }}",
    "sensor.grid_export_energy_this_month": "{{ energy.grid.export_month }}",
    "sensor.vssp_revente_mois": "{{ energy.grid.revenue_month }}",
    "sensor.vssp_revente_annee": "{{ energy.grid.revenue_year }}",
}
for old, new in entity_map.items():
    text = re.sub(rf"(?<![\w.]){re.escape(old)}(?![\w.])", new, text)

# Les commentaires "# TODO" n'ont plus de sens sur des lignes templatisées
text = re.sub(r"[ \t]*# TODO[^\n]*(?=\n)",
              lambda m: "" if "{{" in text[max(0, m.start()-120):m.start()].splitlines()[-1] else m.group(0),
              text)

# ── 4. Sidebar nav → boucle sur `nav` ─────────────────────────────────
nav_start = text.index("          - type: custom:button-card\n"
                       "            template: vssp_nav_button\n"
                       "            icon: mdi:view-dashboard")
nav_end = text.index("          - type: custom:button-card\n"
                     "            show_icon: false\n"
                     "            show_name: false\n"
                     "            show_label: false")
nav_loop = """\
{% for item in nav %}
          - type: custom:button-card
            template: vssp_nav_button
            icon: {{ item.icon }}
            name: {{ item.name }}
            label: "{{ item.label }}"
{% if item.id == active_nav %}
            variables:
              active: true
{% endif %}
            tap_action:
              action: navigate
              navigation_path: {{ item.path }}

{% endfor %}
"""
text = text[:nav_start] + nav_loop + text[nav_end:]

# ── 5. Liste des appareils → double boucle rooms/devices ──────────────
dev_start = text.index("                    # ── Lignes appareils (8)")
dev_end = text.index("          # ── Total ──")
dev_loop = """\
                    # ── Lignes appareils (générées depuis house.yaml) ──
{% for room in rooms %}
{% for d in room.devices %}
                    - type: custom:button-card
                      template: vssp_energy_device_row
                      entity: {{ d.power_entity }}
                      name: "{{ d.name }}"
                      icon: {{ d.icon }}
                      variables:
                        room: "{{ room.name }}"
                        model: "{{ d.model }}"
                        energy_entity: {{ d.energy_entity }}
                      tap_action:
                        action: more-info

{% endfor %}
{% endfor %}
"""
text = text[:dev_start] + dev_loop + text[dev_end:]

# ── 6. Tableau électrique → boucle `circuits` par rangées ─────────────
cir_start = text.index("          # ── Rangée 1 (6 circuits)")
cir_end = text.index("          # ── Légende ──")
cir_loop = """\
          # ── Circuits (générés depuis house.yaml, par rangées) ──────
{% for row in circuits | batch(circuits_per_row | default(6)) %}
          - type: horizontal-stack
            cards:
{% for c in row %}
              - type: custom:button-card
                template: vssp_circuit_switch
                entity: {{ c.entity }}
                name: "{{ c.name }}"
                icon: {{ c.icon }}
                variables:
                  model: "{{ c.model }}"
                  amp: "{{ c.amp }}"
{% endfor %}

{% endfor %}
"""
text = text[:cir_start] + cir_loop + text[cir_end:]

open(DST, "w", encoding="utf-8").write(text)
print(f"OK → {DST} ({len(text.splitlines())} lignes)")
