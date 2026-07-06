/**
 * OSVision V2 — <osv-radar-card>
 * The central "IA CORE" visual: animated radar + neural status line.
 *
 * Usage in a dashboard:
 *   - type: custom:osv-radar-card
 *     title: IA CORE
 *     ia_status_entity: binary_sensor.assist_ia_active   # optional
 *     alert_count_entity: sensor.osvision_active_alerts  # optional
 */
class OSVRadarCard extends HTMLElement {
  setConfig(config) {
    if (!config) {
      throw new Error("osv-radar-card: configuration invalide");
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
      <ha-card class="osv-fade-in" style="padding:22px 16px;">
        <div class="osv-metric-label" style="margin-bottom:10px;">${this._config.title}</div>
        <div class="osv-radar-wrap">
          <div class="osv-radar-sweep"></div>
          <div class="osv-radar-dot"></div>
        </div>
        <div class="osv-ia-status" id="ia-status">NEURAL CORE ONLINE</div>
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

customElements.define("osv-radar-card", OSVRadarCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "osv-radar-card",
  name: "OSVision Radar / IA Core",
  description: "Radar animé central + statut du noyau IA OSVision V2",
});
