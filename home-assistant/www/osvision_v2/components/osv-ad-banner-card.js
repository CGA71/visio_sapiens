/**
 * OSVision V2 — Ad Banner Card
 * Bandeau publicitaire défilant (gauche → droite), chaque logo est un lien
 * cliquable vers une URL externe. Autonome (pas de dépendance Lit/hass).
 *
 * Usage dans home.yaml :
 *   - type: custom:osv-ad-banner-card
 *     view_layout:
 *       grid-area: band2
 *     speed: 25          # secondes pour un tour complet (optionnel, défaut 25)
 *     ads:
 *       - name: HIKVISION
 *         url: https://www.hikvision.com
 *         image: /local/osvision_v2/images/ads/hikvision.png   # optionnel
 *       - name: ECOWITT
 *         url: https://www.ecowitt.com
 *         image: /local/osvision_v2/images/ads/ecowitt.png
 *       - name: PHILIPS HUE
 *         url: https://www.philips-hue.com
 *         image: /local/osvision_v2/images/ads/philips.png
 *       - name: UBER EATS
 *         url: https://www.ubereats.com
 *         image: /local/osvision_v2/images/ads/ubereats.png
 *
 * Si `image` est absent ou introuvable (404), un badge texte stylé
 * s'affiche automatiquement à la place — aucun fichier requis pour tester.
 */

class OsvAdBannerCard extends HTMLElement {
  setConfig(config) {
    if (!config.ads || !Array.isArray(config.ads) || config.ads.length === 0) {
      throw new Error("osv-ad-banner-card: 'ads' (liste) est requis");
    }
    this._config = config;
    this._render();
  }

  // Carte statique — pas besoin de hass, mais HA l'appelle quand même
  set hass(hass) { /* no-op */ }

  getCardSize() {
    return 1;
  }

  _render() {
    const ads = this._config.ads;
    const speed = this._config.speed || 25;
    // Doubler la liste pour un défilement infini sans coupure visible
    const doubled = [...ads, ...ads];

    const itemsHtml = doubled.map((ad) => {
      const safeUrl = this._escapeAttr(ad.url || "#");
      const safeName = this._escapeHtml(ad.name || "");
      if (ad.image) {
        const safeImg = this._escapeAttr(ad.image);
        return `
          <a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="osv-ad-item" title="${safeName}">
            <img src="${safeImg}" alt="${safeName}"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
            <span class="osv-ad-fallback" style="display:none">${safeName}</span>
          </a>`;
      }
      return `
        <a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="osv-ad-item" title="${safeName}">
          <span class="osv-ad-fallback" style="display:flex">${safeName}</span>
        </a>`;
    }).join("");

    this.innerHTML = `
      <ha-card class="osv-ad-banner">
        <div class="osv-ad-track" style="animation-duration:${speed}s">
          ${itemsHtml}
        </div>
      </ha-card>
    `;
  }

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  _escapeAttr(str) {
    return String(str).replace(/"/g, "&quot;");
  }
}

customElements.define("osv-ad-banner-card", OsvAdBannerCard);
