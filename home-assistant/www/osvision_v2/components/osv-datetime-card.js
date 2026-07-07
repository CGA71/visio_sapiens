/**
 * OSVision V2 — <osv-datetime-card>
 * HUD header widget: live clock + full date (jour, mois, année).
 * Distinct from <osv-footer-card> (which also shows connection status);
 * this one is a compact KPI-style cell for the header bar.
 *
 * Usage in a dashboard:
 *   - type: custom:osv-datetime-card
 *     icon: mdi:calendar-clock
 */
class OSVDateTimeCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      icon: "mdi:calendar-clock",
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

  _build() {
    this.innerHTML = `
      <ha-card style="height:100%;">
        <div class="osv-datetime">
          <ha-icon icon="${this._config.icon}" class="osv-datetime-icon"></ha-icon>
          <div class="osv-datetime-text">
            <div class="osv-datetime-time" id="osv-dt-time">--:--</div>
            <div class="osv-datetime-date" id="osv-dt-date">--</div>
          </div>
        </div>
      </ha-card>
    `;
  }

  _startClock() {
    if (this._interval) return;
    const engine = window.osvision;
    const tick = () => {
      const timeEl = this.querySelector("#osv-dt-time");
      const dateEl = this.querySelector("#osv-dt-date");
      if (timeEl && dateEl && engine) {
        timeEl.textContent = engine.formatTime();
        dateEl.textContent = engine.formatDate();
      }
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

customElements.define("osv-datetime-card", OSVDateTimeCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "osv-datetime-card",
  name: "OSVision DateTime Widget",
  description: "Horloge + date en direct — cellule du bandeau HUD OSVision V2",
});
