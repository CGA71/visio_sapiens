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
 * Visio Sapiens — <vssp-datetime-card>
 * HUD header widget: live clock + full date (jour, mois, année).
 * Self-contained: does NOT depend on window.vssp engine, to avoid
 * breaking if that global object isn't loaded/available for any reason.
 *
 * Usage in a dashboard:
 *   - type: custom:vssp-datetime-card
 *     icon: mdi:calendar-clock
 */
class VSSPDateTimeCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      icon: "mdi:calendar-clock",
      locale: "fr-FR",
      ...config,
    };
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) {
      this._build();
      this._built = true;
      this._startClock();
    }
  }

  connectedCallback() {
    this._startClock();
  }

  disconnectedCallback() {
    if (this._interval) clearInterval(this._interval);
  }

  _formatTime(date) {
    return date.toLocaleTimeString(this._config.locale, {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  _formatDate(date) {
    return date.toLocaleDateString(this._config.locale, {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  }

  _build() {
    this.innerHTML = `
      <ha-card style="height:100%;">
        <div class="vssp-datetime">
          <ha-icon icon="${this._config.icon}" class="vssp-datetime-icon"></ha-icon>
          <div class="vssp-datetime-text">
            <div class="vssp-datetime-time" id="vssp-dt-time">--:--</div>
            <div class="vssp-datetime-date" id="vssp-dt-date">--</div>
          </div>
        </div>
      </ha-card>
    `;
  }

  _startClock() {
    if (this._interval) return;
    const tick = () => {
      const timeEl = this.querySelector("#vssp-dt-time");
      const dateEl = this.querySelector("#vssp-dt-date");
      if (!timeEl || !dateEl) return;
      const now = new Date();
      timeEl.textContent = this._formatTime(now);
      dateEl.textContent = this._formatDate(now);
    };
    tick();
    this._interval = setInterval(tick, 1000);
  }

  getCardSize() {
    return 1;
  }

  static getStubConfig() {
    return { icon: "mdi:calendar-clock" };
  }
}

customElements.define("vssp-datetime-card", VSSPDateTimeCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vssp-datetime-card",
  name: "Visio Sapiens DateTime Widget",
  description: "Horloge + date en direct — cellule du bandeau HUD Visio Sapiens",
});
