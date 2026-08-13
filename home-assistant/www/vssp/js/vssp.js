/**
 * Visio Sapiens — JS ENGINE
 * Shared utilities used by OSVision custom cards (osv-radar-card, osv-footer-card, ...).
 * Loaded once as a global lovelace resource (type: module).
 *
 * This engine does NOT manipulate the dashboard DOM directly: each custom card
 * owns its own rendering. It only exposes small, dependency-free helpers so
 * every future OSVision component (rooms, widgets, alerts...) behaves consistently.
 *
 * NOTE: osv-card.js and osv-datetime-card.js no longer depend on this engine
 * for time/date formatting (they compute it natively) after the bug where
 * window.osvision.formatTime was found to be unavailable in some deployments.
 * This engine is kept for the pub/sub bus and color/threshold helpers, which
 * remain useful for future OSVision components (alerts, radar reactions...).
 */

class OSVisionEngine {
  constructor() {
    this.version = "2.0.1";
    this._listeners = {};
    console.info(`%cOSVision V2 Engine loaded (v${this.version})`, "color:#00E5FF;font-weight:bold;");
  }

  /* ---------------------------------------------------------------------
   * Time helpers (kept for backward compatibility / optional reuse)
   * ------------------------------------------------------------------- */
  now() {
    return new Date();
  }

  formatTime(date = new Date(), locale = "fr-FR") {
    return date.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
  }

  formatDate(date = new Date(), locale = "fr-FR") {
    return date.toLocaleDateString(locale, {
      weekday: "long",
      day: "2-digit",
      month: "long",
    });
  }

  /* ---------------------------------------------------------------------
   * Value / threshold helpers (used for neon gauge coloring)
   * ------------------------------------------------------------------- */
  clamp(value, min = 0, max = 100) {
    return Math.min(max, Math.max(min, Number(value) || 0));
  }

  /**
   * Returns a color for a numeric value given ascending thresholds.
   * colorForValue(72, [{max:50,color:'#00FFC3'},{max:80,color:'#FF9800'},{max:101,color:'#FF3D71'}])
   */
  colorForValue(value, thresholds = []) {
    const v = Number(value) || 0;
    for (const t of thresholds) {
      if (v <= t.max) return t.color;
    }
    return thresholds.length ? thresholds[thresholds.length - 1].color : "#00E5FF";
  }

  /* ---------------------------------------------------------------------
   * Tiny pub/sub — lets independent OSVision cards react to shared events
   * (e.g. an alert card raising "osv-alert" so the radar/footer can react)
   * ------------------------------------------------------------------- */
  on(event, callback) {
    (this._listeners[event] ||= []).push(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (!this._listeners[event]) return;
    this._listeners[event] = this._listeners[event].filter((cb) => cb !== callback);
  }

  emit(event, payload) {
    (this._listeners[event] || []).forEach((cb) => {
      try {
        cb(payload);
      } catch (e) {
        console.error("OSVision engine listener error:", e);
      }
    });
  }
}

window.osvision = window.osvision || new OSVisionEngine();
