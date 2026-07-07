/**
 * OSVision V2 — <osv-footer-card>
 * HUD footer: live clock, date, connection status dot.
 * Self-contained: does NOT depend on window.osvision engine, to avoid
 * breaking if that global object isn't loaded/available for any reason.
 *
 * Usage in a dashboard:
 *   - type: custom:osv-footer-card
 *     label: OSVISION V2 // CORE SYSTEM
 */
class OSVFooterCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      label: "OSVISION V2 // CORE SYSTEM",
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
        <div class="osv-footer">
          <div class="osv-footer-label">${this._config.label}</div>
          <div class="osv-footer-clock" id="osv-clock">--:--</div>
          <div class="osv-footer-status">
            <span class="osv-dot" id="osv-status-dot"></span>
            <span id="osv-status-text">CONNECTED</span>
          </div>
        </div>
      </ha-card>
    `;
  }

  _startClock() {
    if (this._clockInterval) return;
    const tick = () => {
      const clockEl = this.querySelector("#osv-clock");
      if (clockEl) {
        const now = new Date();
        clockEl.textContent = `${this._formatTime(now)} — ${this._formatDate(now)}`;
      }
    };
    tick();
    this._clockInterval = setInterval(tick, 1000);
  }

  _updateStatus() {
    const dot = this.querySelector("#osv-status-dot");
    const text = this.querySelector("#osv-status-text");
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

customElements.define("osv-footer-card", OSVFooterCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "osv-footer-card",
  name: "OSVision Footer HUD",
  description: "Horloge, date et statut de connexion — pied de dashboard OSVision V2",
});
