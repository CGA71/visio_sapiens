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

/**
 * Visio Sapiens — HOME chatbot bar controller.
 *
 * The HOME dashboard's chatbot pill (home.yaml.j2, "Cadre 2") is rendered as
 * raw HTML through a button-card custom_fields template — that HTML cannot
 * carry a <script> tag (browsers never execute one inserted via innerHTML),
 * so its input/mic/send elements call these window-level functions through
 * plain inline `onclick`/`onkeydown` attributes instead. Loaded once as a
 * global lovelace resource (type: module, same mechanism as the OSVisionEngine
 * above), so the functions exist before any dashboard view renders.
 *
 * This runs in the top-level Home Assistant frontend (not a sandboxed
 * iframe), which is what lets openFullChat() reach `hass.callService`
 * directly — vssp_chatbot.html, by contrast, is an iframe and has to go
 * through a webhook for everything, including the actual send below.
 */
class VsspChatbotBar {
  constructor() {
    this._bubble = null;
  }

  // EN | Same trick as vssp_chatbot.html: btoa() only handles Latin1, so
  // EN | unicode text (accents, emoji...) needs this wrapping first.
  // FR | Meme astuce que vssp_chatbot.html : btoa() ne gere que le Latin1,
  // FR | donc un texte unicode (accents, emoji...) a besoin de cet enrobage.
  _b64EncodeUnicode(str) {
    return btoa(unescape(encodeURIComponent(str)));
  }

  // EN | The reply/error bubble is appended to <body>, not to the
  // EN | button-card's own DOM: that card can re-render (e.g. when the
  // EN | active provider changes) and wipe anything nested inside it, and
  // EN | its `overflow: visible` still clips a fixed-position descendant on
  // EN | some browsers. position:fixed + a viewport-relative rect anchors it
  // EN | correctly regardless of where the pill sits in the page.
  // FR | La bulle reponse/erreur est ajoutee a <body>, pas au DOM propre de
  // FR | la button-card : cette carte peut se re-rendre (ex. quand le
  // FR | fournisseur actif change) et effacer tout ce qui est imbrique
  // FR | dedans, et son `overflow: visible` peut quand meme decouper un
  // FR | descendant en position fixe sur certains navigateurs.
  // FR | position:fixed + un rectangle relatif au viewport l'ancre
  // FR | correctement quel que soit l'endroit ou la pilule se trouve sur la
  // FR | page.
  _ensureBubble(anchorRect) {
    if (this._bubble) this._bubble.remove();
    const b = document.createElement('div');
    b.style.cssText = `
      position:fixed;
      left:${Math.max(8, anchorRect.left)}px;
      top:${anchorRect.bottom + 8}px;
      width:${Math.max(anchorRect.width, 260)}px;
      max-width:90vw;
      background:rgba(8,18,28,0.95);
      border:1px solid rgba(0,229,255,0.35);
      border-radius:14px;
      padding:10px 14px;
      color:#DCEEF6;
      font-size:13px;
      line-height:1.4;
      z-index:999999;
      box-shadow:0 4px 24px rgba(0,0,0,0.5);
      backdrop-filter:blur(8px);
      white-space:pre-wrap;
      word-break:break-word;
    `;
    document.body.appendChild(b);
    this._bubble = b;
    const dismiss = (ev) => {
      if (ev && b.contains(ev.target)) return;
      b.remove();
      if (this._bubble === b) this._bubble = null;
      document.removeEventListener('click', dismiss, true);
    };
    // EN | Deferred: without this, the same click that opened the bubble
    // EN | (still bubbling up to document) would close it immediately.
    // FR | Differe : sans cela, le meme clic qui a ouvert la bulle (encore
    // FR | en train de remonter jusqu'a document) la refermerait aussitot.
    setTimeout(() => document.addEventListener('click', dismiss, true), 0);
    setTimeout(() => dismiss(), 15000);
    return b;
  }

  // EN | Fire-and-forget send, then poll the same status file
  // EN | vssp_chatbot.html polls — see packages/vssp_chatbot.yaml for what
  // EN | writes it. No conversation history is sent: this bar has no
  // EN | message list to hold one, unlike the full popup.
  // FR | Envoi puis interrogation du meme fichier de statut que
  // FR | vssp_chatbot.html — voir packages/vssp_chatbot.yaml pour ce qui
  // FR | l'ecrit. Aucun historique de conversation envoye : cette barre n'a
  // FR | pas de liste de messages pour en garder un, contrairement au popup
  // FR | complet.
  async send(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    const bubble = this._ensureBubble(input.getBoundingClientRect());
    bubble.textContent = '…';
    const sentAt = Date.now();
    try {
      const res = await fetch('/api/webhook/vssp_chatbot_send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_b64: this._b64EncodeUnicode(text),
          history_b64: '',
        }),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      await this._pollReply(sentAt, bubble, input);
    } catch (e) {
      bubble.textContent = (input.dataset.errorPrefix || 'Error: ') + e.message;
    }
  }

  async _pollReply(sentAt, bubble, input) {
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 1200));
      if (this._bubble !== bubble) return; // dismissed by the user already
      let data;
      try {
        const res = await fetch('/local/vssp/chatbot_status.json?t=' + Date.now(), { cache: 'no-store' });
        if (!res.ok) continue;
        data = await res.json();
      } catch (e) {
        continue;
      }
      // EN | Only accept a status written AFTER we sent — see the same
      // EN | guard in vssp_chatbot.html.
      // FR | N'accepte qu'un statut ecrit APRES notre envoi — voir la meme
      // FR | garde dans vssp_chatbot.html.
      if (!data.timestamp || new Date(data.timestamp).getTime() < sentAt) continue;
      bubble.textContent = data.ok
        ? (data.reply || input.dataset.emptyReply || '')
        : (data.error || (input.dataset.errorPrefix || 'Error: ') + 'unknown');
      return;
    }
    if (this._bubble === bubble) {
      bubble.textContent = input.dataset.noReply || 'No reply after 30s.';
    }
  }

  // EN | Web Speech API — fills the input with the transcript, does not
  // EN | auto-send: same "type then tap send" flow as typing by hand, just
  // EN | dictated. Chromium-only (webkitSpeechRecognition); silently shows
  // EN | the "unsupported" bubble on browsers without it instead of
  // EN | throwing.
  // FR | Web Speech API — remplit le champ avec la transcription, n'envoie
  // FR | pas automatiquement : meme flux "taper puis appuyer sur envoyer"
  // FR | que la saisie manuelle, juste dicte. Chromium uniquement
  // FR | (webkitSpeechRecognition) ; affiche la bulle "non disponible" sur
  // FR | les navigateurs qui ne l'ont pas plutot que d'echouer bruyamment.
  mic(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      const bubble = this._ensureBubble(input.getBoundingClientRect());
      bubble.textContent = input.dataset.micUnsupported || 'Voice input not available in this browser.';
      return;
    }
    let lang = 'fr-FR';
    try {
      const ha = document.querySelector('home-assistant');
      if (ha && ha.hass && ha.hass.language) lang = ha.hass.language;
    } catch (e) {
      /* keep the fr-FR default */
    }
    const rec = new SR();
    rec.lang = lang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (ev) => {
      const transcript = ev.results && ev.results[0] && ev.results[0][0] ? ev.results[0][0].transcript : '';
      if (transcript) input.value = transcript;
      input.focus();
    };
    rec.start();
  }

  // EN | Opens the same browser_mod popup the pill used to open on any tap,
  // EN | now reserved for the leading provider icon: the input/mic/send
  // EN | elements handle their own actions, so tapping the icon is what's
  // EN | left to reach the full conversation view (with message history)
  // EN | instead of this bar's single-turn inline replies.
  // FR | Ouvre le meme popup browser_mod que la pilule ouvrait sur n'importe
  // FR | quel tap auparavant, desormais reserve a l'icone de fournisseur en
  // FR | tete : les elements input/mic/envoi gerent leurs propres actions,
  // FR | taper l'icone est donc ce qui reste pour atteindre la vue de
  // FR | conversation complete (avec historique) plutot que les reponses en
  // FR | ligne, un tour a la fois, de cette barre.
  openFullChat(el) {
    try {
      const ha = document.querySelector('home-assistant');
      if (!ha || !ha.hass) return;
      ha.hass.callService('browser_mod', 'popup', {
        browser_id: 'this',
        title: (el && el.dataset && el.dataset.title) || 'Chatbot',
        size: 'normal',
        content: {
          type: 'iframe',
          url: '/local/vssp/wizard/vssp_chatbot.html?mode=chat',
        },
      });
    } catch (e) {
      /* browser_mod not installed yet — see docs/Security.md */
    }
  }
}

window.vsspChatbot = window.vsspChatbot || new VsspChatbotBar();
