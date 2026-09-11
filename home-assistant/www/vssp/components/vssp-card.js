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
 * Visio Sapiens — <vssp-footer-card>
 * HUD footer: live clock, date, connection status dot.
 * Self-contained: does NOT depend on window.osvision engine, to avoid
 * breaking if that global object isn't loaded/available for any reason.
 *
 * Usage in a dashboard:
 *   - type: custom:vssp-footer-card
 *     label: VISIO SAPIENS // CORE SYSTEM
 */
class VSSPFooterCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      label: "VISIO SAPIENS // CORE SYSTEM",
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
    this._updateStatus();
  }

  connectedCallback() {
    this._startClock();
  }

  disconnectedCallback() {
    if (this._clockInterval) clearInterval(this._clockInterval);
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
    });
  }

  _build() {
    this.innerHTML = `
      <ha-card style="box-shadow:none;border:none;background:transparent !important;">
        <div class="vssp-footer">
          <div class="vssp-footer-label">${this._config.label}</div>
          <div class="vssp-footer-clock" id="vssp-clock">--:--</div>
          <div class="vssp-footer-status">
            <span class="vssp-dot" id="vssp-status-dot"></span>
            <span id="vssp-status-text">CONNECTED</span>
          </div>
        </div>
      </ha-card>
    `;
  }

  _startClock() {
    if (this._clockInterval) return;
    const tick = () => {
      const clockEl = this.querySelector("#vssp-clock");
      if (clockEl) {
        const now = new Date();
        clockEl.textContent = `${this._formatTime(now)} — ${this._formatDate(now)}`;
      }
    };
    tick();
    this._clockInterval = setInterval(tick, 1000);
  }

  _updateStatus() {
    const dot = this.querySelector("#vssp-status-dot");
    const text = this.querySelector("#vssp-status-text");
    if (!dot || !text || !this._hass) return;
    const connected = this._hass.connected !== false;
    dot.classList.toggle("offline", !connected);
    text.textContent = connected ? "CONNECTED" : "OFFLINE";
  }

  getCardSize() {
    return 1;
  }

  static getStubConfig() {
    return { label: "OSVISION V2 // CORE SYSTEM" };
  }
}

customElements.define("vssp-footer-card", VSSPFooterCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vssp-footer-card",
  name: "OSVision Footer HUD",
  description: "Horloge, date et statut de connexion — pied de dashboard Visio Sapiens",
});
