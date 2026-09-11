/*
 * Visio Sapiens - Neural Home Interface for Home Assistant
 * Copyright (C) 2026 Expanse IT <expanse-it@outlook.fr>
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 * MA 02110-1301 USA.
 */

/**
 * Visio Sapiens — <vssp-radar-card>
 * The central "IA CORE" visual: animated radar + neural status line.
 *
 * Usage in a dashboard:
 *   - type: custom:vssp-radar-card
 *     title: IA CORE
 *     ia_status_entity: binary_sensor.assist_ia_active   # optional
 *     alert_count_entity: sensor.osvision_active_alerts  # optional
 */
class VSSPRadarCard extends HTMLElement {
  setConfig(config) {
    if (!config) {
      throw new Error("vssp-radar-card: configuration invalide");
    }
    this._config = {
      title: "IA CORE",
      ia_status_entity: null,
      alert_count_entity: null,
      ...config,
    };
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) {
      this._build();
      this._built = true;
    }
    this._update();
  }

  _build() {
    this.innerHTML = `
      <ha-card class="vssp-fade-in" style="padding:22px 16px;">
        <div class="vssp-metric-label" style="margin-bottom:10px;">${this._config.title}</div>
        <div class="vssp-radar-wrap">
          <div class="vssp-radar-sweep"></div>
          <div class="vssp-radar-dot"></div>
        </div>
        <div class="vssp-ia-status" id="ia-status">NEURAL CORE ONLINE</div>
      </ha-card>
    `;
  }

  _update() {
    if (!this._hass) return;
    const statusEl = this.querySelector("#ia-status");
    if (!statusEl) return;

    let alertCount = 0;
    if (this._config.alert_count_entity) {
      const st = this._hass.states[this._config.alert_count_entity];
      alertCount = st ? Number(st.state) || 0 : 0;
    }

    let iaOnline = true;
    if (this._config.ia_status_entity) {
      const st = this._hass.states[this._config.ia_status_entity];
      iaOnline = st ? ["on", "home", "active", "true"].includes(st.state) : true;
    }

    if (alertCount > 0) {
      statusEl.textContent = `${alertCount} ALERTE${alertCount > 1 ? "S" : ""} ACTIVE${alertCount > 1 ? "S" : ""}`;
      statusEl.classList.add("alert");
    } else {
      statusEl.textContent = iaOnline ? "NEURAL CORE ONLINE" : "NEURAL CORE STANDBY";
      statusEl.classList.remove("alert");
    }
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return { title: "IA CORE" };
  }
}

customElements.define("vssp-radar-card", VSSPRadarCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vssp-radar-card",
  name: "Visio Sapiens Radar / IA Core",
  description: "Radar animé central + statut du noyau IA Visio Sapiens",
});
