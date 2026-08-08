/**
 * Visio Sapiens — Ad Banner Card (v2, autonome)
 * Bandeau publicitaire défilant (gauche → droite), chaque logo est un lien
 * cliquable vers une URL externe.
 *
 * v2 : le style est désormais injecté DIRECTEMENT dans le composant
 * (balise <style> interne) plutôt que de dépendre d'vssp.css.
 * Raison : ha-card utilise son propre Shadow DOM, ce qui empêchait le
 * CSS externe d'atteindre nos classes de façon fiable.
 *
 * Usage dans home.yaml (inchangé) :
 *   - type: custom:osv-ad-banner-card
 *     view_layout:
 *       grid-area: band2
 *     speed: 25
 *     ads:
 *       - name: HIKVISION
 *         url: https://www.hikvision.com
 *         image: /local/vssp/images/ads/hikvision.png   # optionnel
 *       ...
 */

class OsvAdBannerCard extends HTMLElement {
  setConfig(config) {
    if (!config.ads || !Array.isArray(config.ads) || config.ads.length === 0) {
      throw new Error("osv-ad-banner-card: 'ads' (liste) est requis");
    }
    this._config = config;
    this._render();
  }

  set hass(hass) { /* no-op — carte statique */ }

  getCardSize() {
    return 1;
  }

  _render() {
    const ads = this._config.ads;
    const speed = this._config.speed || 25;
    const doubled = [...ads, ...ads]; // défilement infini sans coupure

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

    // Style 100% autonome — inline, aucune dépendance à vssp.css
    this.innerHTML = `
      <style>
        osv-ad-banner-card{
          display:block;
          height:100%;
        }
        osv-ad-banner-card .osv-ad-banner{
          overflow:hidden;
          height:100%;
          display:flex;
          align-items:center;
          background:rgba(8,18,28,0.72);
          border:1px solid rgba(0,229,255,0.22);
          border-radius:18px;
          box-shadow:0 0 18px rgba(0,229,255,0.18);
          position:relative;
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
        }
        osv-ad-banner-card .osv-ad-banner::before,
        osv-ad-banner-card .osv-ad-banner::after{
          content:"";
          position:absolute;
          top:0; bottom:0;
          width:40px;
          z-index:2;
          pointer-events:none;
        }
        osv-ad-banner-card .osv-ad-banner::before{
          left:0;
          background:linear-gradient(90deg, #02050B 0%, transparent 100%);
        }
        osv-ad-banner-card .osv-ad-banner::after{
          right:0;
          background:linear-gradient(270deg, #02050B 0%, transparent 100%);
        }
        osv-ad-banner-card .osv-ad-track{
          display:flex;
          align-items:center;
          gap:48px;
          white-space:nowrap;
          padding:0 24px;
          animation-name: osv-ad-scroll-anim;
          animation-duration: ${speed}s;
          animation-timing-function: linear;
          animation-iteration-count: infinite;
          will-change: transform;
        }
        osv-ad-banner-card .osv-ad-banner:hover .osv-ad-track{
          animation-play-state: paused;
        }
        @keyframes osv-ad-scroll-anim{
          from{ transform: translateX(0); }
          to{ transform: translateX(-50%); }
        }
        osv-ad-banner-card .osv-ad-item{
          display:flex;
          align-items:center;
          justify-content:center;
          flex-shrink:0;
          height:44px;
          min-width:90px;
          text-decoration:none;
          cursor:pointer;
          transition: transform .2s ease, filter .2s ease;
        }
        osv-ad-banner-card .osv-ad-item:hover{
          transform: scale(1.08);
        }
        osv-ad-banner-card .osv-ad-item img{
          height:100%;
          width:auto;
          max-width:140px;
          object-fit:contain;
          filter: grayscale(0.25) brightness(1.15) drop-shadow(0 0 6px rgba(0,229,255,.15));
          transition: filter .2s ease;
        }
        osv-ad-banner-card .osv-ad-item:hover img{
          filter: grayscale(0) brightness(1.3) drop-shadow(0 0 10px rgba(0,229,255,.35));
        }
        osv-ad-banner-card .osv-ad-fallback{
          align-items:center;
          justify-content:center;
          height:100%;
          padding:0 16px;
          border:1px solid rgba(0,229,255,0.35);
          border-radius:12px;
          background:rgba(0,229,255,0.08);
          color:#00E5FF;
          font-family:'Orbitron','Courier New',monospace;
          font-size:11px;
          letter-spacing:1.5px;
          font-weight:700;
          white-space:nowrap;
          text-decoration:none;
        }
      </style>
      <div class="osv-ad-banner">
        <div class="osv-ad-track">
          ${itemsHtml}
        </div>
      </div>
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
