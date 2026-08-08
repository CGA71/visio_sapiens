/**
 * Visio Sapiens — <osv-datetime-card>
 * HUD header widget: live clock + full date (jour, mois, année).
 * Self-contained: does NOT depend on window.vssp engine, to avoid
 * breaking if that global object isn't loaded/available for any reason.
 *
 * Usage in a dashboard:
 *   - type: custom:osv-datetime-card
 *     icon: mdi:calendar-clock
 */
class OSVDateTimeCard extends HTMLElement {
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
    const tick = () => {
      const timeEl = this.querySelector("#osv-dt-time");
      const dateEl = this.querySelector("#osv-dt-date");
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

customElements.define("osv-datetime-card", OSVDateTimeCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "osv-datetime-card",
  name: "Visio Sapiens DateTime Widget",
  description: "Horloge + date en direct — cellule du bandeau HUD Visio Sapiens",
});
