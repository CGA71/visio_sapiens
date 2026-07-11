/**
 * OSVision V2 — Discovery Wizard
 * Page web séparée (React) lancée depuis le bouton DISCOVERY du panneau Admin.
 * 
 * Étape 1 : Définir la structure de la maison (étages, pièces, extérieurs)
 * Étape 2 : Récupérer les appareils HA et les assigner aux pièces
 * Étape 3 : Générer un plan SVG interactif
 * Étape 4 : Sauvegarder le résultat (config JSON + SVG)
 * 
 * Usage : à déposer dans /config/www/osvision_v2/wizard/index.html
 * Accessible via http://192.168.1.11:8123/local/osvision_v2/wizard/
 */

import { useState, useCallback, useMemo } from "react";

// ─── Design tokens (OSVision V2) ────────────────────────────────────────────
const T = {
  bg:       "#02050B",
  panel:    "rgba(8,18,28,0.85)",
  cyan:     "#00E5FF",
  cyanDim:  "rgba(0,229,255,0.15)",
  cyanBorder: "rgba(0,229,255,0.35)",
  green:    "#00FFC3",
  red:      "#FF3D71",
  orange:   "#FF9800",
  text:     "#FFFFFF",
  textDim:  "#8FB6C9",
  textMute: "#56707E",
  font:     "'Rajdhani', system-ui, sans-serif",
  fontMono: "'Orbitron', system-ui, sans-serif",
};

// ─── Helpers ────────────────────────────────────────────────────────────────
const HA_URL  = window.location.origin;
const HA_TOKEN = localStorage.getItem("osv_ha_token") || "";

async function haGet(path) {
  const r = await fetch(`${HA_URL}/api/${path}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem("osv_ha_token")}` },
  });
  if (!r.ok) throw new Error(`HA API ${path}: ${r.status}`);
  return r.json();
}

const EXTERIOR_TYPES = ["Jardin", "Piscine", "Jacuzzi", "Garage", "Terrasse", "Véranda"];

const DOMAIN_ICON = {
  light:   "💡", switch: "🔌", sensor: "📡", binary_sensor: "🚨",
  climate: "🌡", media_player: "🎵", cover: "🪟", camera: "📷",
  alarm_control_panel: "🔒", vacuum: "🤖", fan: "💨", lock: "🔑",
};

// ─── Styles communs ──────────────────────────────────────────────────────────
const S = {
  page: {
    minHeight: "100vh", background: T.bg, color: T.text,
    fontFamily: T.font, padding: "24px", boxSizing: "border-box",
  },
  card: {
    background: T.panel, border: `1px solid ${T.cyanBorder}`,
    borderRadius: 16, padding: "24px", marginBottom: 16,
    backdropFilter: "blur(12px)",
  },
  title: {
    fontFamily: T.fontMono, color: T.cyan, fontSize: 22,
    letterSpacing: 3, marginBottom: 4, margin: 0,
  },
  sub: { color: T.textDim, fontSize: 13, marginBottom: 20, marginTop: 6 },
  label: { color: T.textDim, fontSize: 12, letterSpacing: 1, marginBottom: 4, display: "block" },
  input: {
    background: "rgba(0,229,255,0.06)", border: `1px solid ${T.cyanBorder}`,
    borderRadius: 8, padding: "8px 12px", color: T.text, fontSize: 14,
    fontFamily: T.font, outline: "none", width: "100%", boxSizing: "border-box",
  },
  select: {
    background: "rgba(0,229,255,0.06)", border: `1px solid ${T.cyanBorder}`,
    borderRadius: 8, padding: "8px 12px", color: T.text, fontSize: 14,
    fontFamily: T.font, outline: "none", width: "100%", boxSizing: "border-box",
  },
  btn: (variant = "primary") => ({
    background: variant === "primary" ? T.cyanDim : "transparent",
    border: `1px solid ${variant === "danger" ? T.red : T.cyan}`,
    borderRadius: 10, padding: "10px 20px", color: variant === "danger" ? T.red : T.cyan,
    fontFamily: T.fontMono, fontSize: 13, letterSpacing: 1, cursor: "pointer",
    transition: "all .2s ease",
  }),
  chip: (active) => ({
    display: "inline-block", padding: "4px 12px", borderRadius: 20,
    fontSize: 12, letterSpacing: 1, cursor: "pointer", marginRight: 6, marginBottom: 6,
    background: active ? T.cyanDim : "transparent",
    border: `1px solid ${active ? T.cyan : T.cyanBorder}`,
    color: active ? T.cyan : T.textDim,
    transition: "all .2s",
  }),
  row: { display: "flex", gap: 12, alignItems: "center", marginBottom: 10 },
  stepBar: { display: "flex", gap: 0, marginBottom: 32 },
  stepDot: (active, done) => ({
    flex: 1, height: 4, borderRadius: 2,
    background: done ? T.green : active ? T.cyan : T.cyanBorder,
    transition: "background .3s",
  }),
  badge: (col) => ({
    display: "inline-block", background: `${col}22`,
    border: `1px solid ${col}66`, borderRadius: 6,
    padding: "2px 8px", fontSize: 11, color: col, marginRight: 4,
  }),
};

// ═══════════════════════════════════════════════════════════════════════════
// STEP 1 — Structure de la maison
// ═══════════════════════════════════════════════════════════════════════════
function Step1Structure({ house, setHouse, onNext }) {
  const addFloor = () => setHouse(h => ({
    ...h,
    floors: [...h.floors, { name: h.floors.length === 0 ? "Rez-de-chaussée" : `Étage ${h.floors.length}`, rooms: [] }],
  }));

  const updateFloorName = (fi, name) => setHouse(h => ({
    ...h, floors: h.floors.map((f, i) => i === fi ? { ...f, name } : f),
  }));

  const addRoom = (fi) => setHouse(h => ({
    ...h, floors: h.floors.map((f, i) => i === fi
      ? { ...f, rooms: [...f.rooms, { name: "", color: "#0A2030" }] } : f),
  }));

  const updateRoom = (fi, ri, key, val) => setHouse(h => ({
    ...h, floors: h.floors.map((f, i) => i !== fi ? f : {
      ...f, rooms: f.rooms.map((r, j) => j !== ri ? r : { ...r, [key]: val }),
    }),
  }));

  const removeRoom = (fi, ri) => setHouse(h => ({
    ...h, floors: h.floors.map((f, i) => i !== fi ? f : {
      ...f, rooms: f.rooms.filter((_, j) => j !== ri),
    }),
  }));

  const toggleExt = (name) => setHouse(h => ({
    ...h, exteriors: h.exteriors.includes(name)
      ? h.exteriors.filter(e => e !== name) : [...h.exteriors, name],
  }));

  const canNext = house.floors.some(f => f.rooms.length > 0);

  return (
    <div>
      <p style={S.sub}>Définissez la structure de votre maison — étages, pièces et espaces extérieurs.</p>

      {house.floors.map((floor, fi) => (
        <div key={fi} style={S.card}>
          <div style={S.row}>
            <span style={{ color: T.cyan, fontFamily: T.fontMono, fontSize: 12 }}>ÉTAGE {fi + 1}</span>
            <input
              style={{ ...S.input, flex: 1 }}
              value={floor.name}
              onChange={e => updateFloorName(fi, e.target.value)}
              placeholder="Nom de l'étage"
            />
          </div>
          {floor.rooms.map((room, ri) => (
            <div key={ri} style={{ ...S.row, marginLeft: 20 }}>
              <input
                style={{ ...S.input, flex: 1 }}
                value={room.name}
                onChange={e => updateRoom(fi, ri, "name", e.target.value)}
                placeholder="Nom de la pièce"
              />
              <input
                type="color"
                value={room.color}
                onChange={e => updateRoom(fi, ri, "color", e.target.value)}
                title="Couleur de la pièce"
                style={{ width: 36, height: 36, border: "none", background: "none", cursor: "pointer", borderRadius: 6 }}
              />
              <button style={S.btn("danger")} onClick={() => removeRoom(fi, ri)}>✕</button>
            </div>
          ))}
          <button style={{ ...S.btn(), marginTop: 8, marginLeft: 20, fontSize: 12 }} onClick={() => addRoom(fi)}>
            + Ajouter une pièce
          </button>
        </div>
      ))}

      <button style={{ ...S.btn(), marginBottom: 24 }} onClick={addFloor}>
        + Ajouter un étage
      </button>

      <div style={S.card}>
        <p style={{ ...S.label, fontSize: 13, marginBottom: 12 }}>ESPACES EXTÉRIEURS</p>
        {EXTERIOR_TYPES.map(ext => (
          <span key={ext} style={S.chip(house.exteriors.includes(ext))} onClick={() => toggleExt(ext)}>
            {ext}
          </span>
        ))}
        <div style={{ marginTop: 12, ...S.row }}>
          <input
            id="ext-custom"
            style={{ ...S.input, flex: 1 }}
            placeholder="Autre espace extérieur…"
            onKeyDown={e => {
              if (e.key === "Enter" && e.target.value.trim()) {
                toggleExt(e.target.value.trim());
                e.target.value = "";
              }
            }}
          />
        </div>
      </div>

      <div style={{ textAlign: "right" }}>
        <button style={S.btn()} disabled={!canNext} onClick={onNext}>
          Suivant → Découverte des appareils
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// STEP 2 — Découverte & assignation des appareils
// ═══════════════════════════════════════════════════════════════════════════
function Step2Devices({ house, devices, setDevices, loading, error, onNext, onBack }) {
  const allRooms = useMemo(() => {
    const rooms = [];
    house.floors.forEach(f => f.rooms.forEach(r => r.name && rooms.push(r.name)));
    house.exteriors.forEach(e => rooms.push(e));
    return rooms;
  }, [house]);

  const assign = (entityId, room) => setDevices(d =>
    d.map(dev => dev.entity_id === entityId ? { ...dev, room } : dev)
  );

  const assigned = devices.filter(d => d.room).length;

  const byDomain = useMemo(() => {
    const map = {};
    devices.forEach(d => {
      const dom = d.entity_id.split(".")[0];
      if (!map[dom]) map[dom] = [];
      map[dom].push(d);
    });
    return map;
  }, [devices]);

  return (
    <div>
      <p style={S.sub}>
        {loading ? "Récupération des appareils en cours…" : error ? `Erreur : ${error}` :
          `${devices.length} appareils trouvés — ${assigned} assignés`}
      </p>

      {loading && (
        <div style={{ textAlign: "center", padding: 40, color: T.cyan }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⟳</div>
          Connexion à Home Assistant…
        </div>
      )}

      {!loading && !error && Object.entries(byDomain).map(([domain, devs]) => (
        <div key={domain} style={S.card}>
          <p style={{ ...S.label, fontSize: 13, marginBottom: 12 }}>
            {DOMAIN_ICON[domain] || "📦"} {domain.toUpperCase().replace("_", " ")}
            <span style={S.badge(T.cyan)}>{devs.length}</span>
          </p>
          {devs.map(dev => (
            <div key={dev.entity_id} style={{ ...S.row, flexWrap: "wrap", marginBottom: 8 }}>
              <div style={{ flex: 2, minWidth: 200 }}>
                <div style={{ fontSize: 13, color: T.text }}>{dev.friendly_name || dev.entity_id}</div>
                <div style={{ fontSize: 11, color: T.textMute }}>{dev.entity_id}</div>
              </div>
              <select
                style={{ ...S.select, flex: 1, minWidth: 160 }}
                value={dev.room || ""}
                onChange={e => assign(dev.entity_id, e.target.value)}
              >
                <option value="">— Non assigné —</option>
                {allRooms.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          ))}
        </div>
      ))}

      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button style={S.btn("secondary")} onClick={onBack}>← Retour</button>
        <button style={S.btn()} onClick={onNext} disabled={assigned === 0}>
          Suivant → Générer le plan
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// STEP 3 — Génération du plan SVG
// ═══════════════════════════════════════════════════════════════════════════
function generateSVG(house, devices) {
  const W = 1200, MARGIN = 40, GAP = 20;
  const floorCount = house.floors.length + (house.exteriors.length > 0 ? 1 : 0);
  const FLOOR_H = 280;
  const H = MARGIN * 2 + floorCount * (FLOOR_H + GAP);

  const devicesByRoom = {};
  devices.forEach(d => {
    if (d.room) {
      if (!devicesByRoom[d.room]) devicesByRoom[d.room] = [];
      devicesByRoom[d.room].push(d);
    }
  });

  let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
  <defs>
    <style>
      text { font-family: 'Rajdhani', system-ui, sans-serif; }
      .floor-label { font-family: 'Orbitron', system-ui, sans-serif; fill: #00E5FF; font-size: 13px; letter-spacing: 2px; }
      .room-name { fill: #00E5FF; font-size: 12px; font-weight: bold; letter-spacing: 1px; }
      .room-devices { fill: #8FB6C9; font-size: 10px; }
      .device-icon { font-size: 14px; }
      .exterior-label { fill: #00FFC3; font-size: 12px; font-weight: bold; }
    </style>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Fond -->
  <rect width="${W}" height="${H}" fill="#02050B"/>
`;

  // Titre
  svgContent += `
  <text x="${W / 2}" y="${MARGIN - 8}" text-anchor="middle" class="floor-label" style="font-size:18px">
    OSVision V2 — Plan de la maison
  </text>`;

  // Étages
  house.floors.forEach((floor, fi) => {
    const y = MARGIN + fi * (FLOOR_H + GAP);
    const roomCount = floor.rooms.length || 1;
    const roomW = (W - MARGIN * 2 - GAP * (roomCount - 1)) / roomCount;

    // Label étage
    svgContent += `
  <text x="${MARGIN}" y="${y + 18}" class="floor-label">${floor.name.toUpperCase()}</text>
  <line x1="${MARGIN}" y1="${y + 24}" x2="${W - MARGIN}" y2="${y + 24}" stroke="#00E5FF" stroke-opacity="0.3" stroke-width="1"/>`;

    // Pièces
    floor.rooms.forEach((room, ri) => {
      if (!room.name) return;
      const rx = MARGIN + ri * (roomW + GAP);
      const ry = y + 32;
      const rh = FLOOR_H - 40;
      const devs = devicesByRoom[room.name] || [];

      // Rectangle pièce
      svgContent += `
  <rect x="${rx}" y="${ry}" width="${roomW}" height="${rh}" rx="12"
    fill="${room.color || "#0A2030"}" fill-opacity="0.7"
    stroke="#00E5FF" stroke-opacity="0.4" stroke-width="1"/>`;

      // Nom de la pièce
      svgContent += `
  <text x="${rx + roomW / 2}" y="${ry + 22}" text-anchor="middle" class="room-name">
    ${room.name.toUpperCase()}
  </text>`;

      // Compteur appareils
      svgContent += `
  <text x="${rx + roomW / 2}" y="${ry + 38}" text-anchor="middle" class="room-devices">
    ${devs.length} appareil${devs.length > 1 ? "s" : ""}
  </text>`;

      // Icônes appareils (max 12 par pièce)
      const iconsPerRow = Math.min(6, Math.ceil(roomW / 30));
      devs.slice(0, 12).forEach((dev, di) => {
        const col = di % iconsPerRow;
        const row = Math.floor(di / iconsPerRow);
        const ix = rx + 12 + col * (roomW - 24) / Math.max(iconsPerRow - 1, 1);
        const iy = ry + 55 + row * 28;
        const icon = DOMAIN_ICON[dev.entity_id.split(".")[0]] || "📦";
        svgContent += `
  <text x="${ix}" y="${iy}" text-anchor="middle" class="device-icon" filter="url(#glow)">${icon}</text>`;
      });
    });
  });

  // Extérieurs
  if (house.exteriors.length > 0) {
    const fi = house.floors.length;
    const y = MARGIN + fi * (FLOOR_H + GAP);
    const extW = (W - MARGIN * 2 - GAP * (house.exteriors.length - 1)) / house.exteriors.length;

    svgContent += `
  <text x="${MARGIN}" y="${y + 18}" class="floor-label" style="fill:#00FFC3">EXTÉRIEURS</text>
  <line x1="${MARGIN}" y1="${y + 24}" x2="${W - MARGIN}" y2="${y + 24}" stroke="#00FFC3" stroke-opacity="0.3" stroke-width="1"/>`;

    house.exteriors.forEach((ext, ei) => {
      const ex = MARGIN + ei * (extW + GAP);
      const ey = y + 32;
      const eh = FLOOR_H - 40;
      const devs = devicesByRoom[ext] || [];

      svgContent += `
  <rect x="${ex}" y="${ey}" width="${extW}" height="${eh}" rx="12"
    fill="rgba(0,120,40,0.25)" stroke="#00FFC3" stroke-opacity="0.4" stroke-width="1"/>
  <text x="${ex + extW / 2}" y="${ey + 22}" text-anchor="middle" class="exterior-label">
    ${ext.toUpperCase()}
  </text>
  <text x="${ex + extW / 2}" y="${ey + 38}" text-anchor="middle" class="room-devices">
    ${devs.length} appareil${devs.length > 1 ? "s" : ""}
  </text>`;

      devs.slice(0, 8).forEach((dev, di) => {
        const icon = DOMAIN_ICON[dev.entity_id.split(".")[0]] || "📦";
        svgContent += `
  <text x="${ex + 20 + (di % 4) * 30}" y="${ey + 60 + Math.floor(di / 4) * 28}"
    class="device-icon">${icon}</text>`;
      });
    });
  }

  svgContent += "\n</svg>";
  return svgContent;
}

function Step3Generate({ house, devices, onBack }) {
  const [svg, setSvg] = useState(null);
  const [saved, setSaved] = useState(false);
  const [jsonSaved, setJsonSaved] = useState(false);

  const generate = useCallback(() => {
    const s = generateSVG(house, devices);
    setSvg(s);
    setSaved(false);
  }, [house, devices]);

  const downloadSvg = () => {
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "floorplan.svg"; a.click();
    setSaved(true);
  };

  const downloadConfig = () => {
    const config = {
      generated: new Date().toISOString(),
      house,
      devices: devices.filter(d => d.room),
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = "osvision_floorplan_config.json"; a.click();
    setJsonSaved(true);
  };

  const assigned = devices.filter(d => d.room).length;
  const totalRooms = house.floors.reduce((s, f) => s + f.rooms.filter(r => r.name).length, 0) + house.exteriors.length;

  return (
    <div>
      <p style={S.sub}>
        Récapitulatif : {totalRooms} pièces/zones · {assigned} appareils assignés
      </p>

      <div style={S.card}>
        <p style={{ ...S.label, fontSize: 13 }}>RÉSUMÉ DE LA STRUCTURE</p>
        {house.floors.map((f, fi) => (
          <div key={fi} style={{ marginBottom: 12 }}>
            <div style={{ color: T.cyan, fontSize: 13, fontFamily: T.fontMono, marginBottom: 4 }}>
              {f.name}
            </div>
            <div style={{ paddingLeft: 16 }}>
              {f.rooms.filter(r => r.name).map((r, ri) => {
                const devs = devices.filter(d => d.room === r.name);
                return (
                  <div key={ri} style={{ ...S.row, marginBottom: 4 }}>
                    <span style={{ color: T.text, fontSize: 13, flex: 1 }}>{r.name}</span>
                    <span style={S.badge(T.cyan)}>{devs.length} appareils</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
        {house.exteriors.length > 0 && (
          <div>
            <div style={{ color: T.green, fontSize: 13, fontFamily: T.fontMono, marginBottom: 4 }}>Extérieurs</div>
            <div style={{ paddingLeft: 16 }}>
              {house.exteriors.map(e => {
                const devs = devices.filter(d => d.room === e);
                return (
                  <div key={e} style={{ ...S.row, marginBottom: 4 }}>
                    <span style={{ color: T.text, fontSize: 13, flex: 1 }}>{e}</span>
                    <span style={S.badge(T.green)}>{devs.length} appareils</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <button style={S.btn()} onClick={generate}>⚡ Générer le plan SVG</button>
        {svg && (
          <>
            <button style={S.btn()} onClick={downloadSvg}>
              ⬇ Télécharger floorplan.svg {saved && "✓"}
            </button>
            <button style={{ ...S.btn(), borderColor: T.green, color: T.green }} onClick={downloadConfig}>
              ⬇ Télécharger config.json {jsonSaved && "✓"}
            </button>
          </>
        )}
      </div>

      {svg && (
        <div style={{ ...S.card, padding: 0, overflow: "hidden" }}>
          <div dangerouslySetInnerHTML={{ __html: svg }}
            style={{ width: "100%", overflowX: "auto" }} />
        </div>
      )}

      {saved && jsonSaved && (
        <div style={{ ...S.card, borderColor: T.green, background: "rgba(0,255,195,0.06)", marginTop: 16 }}>
          <p style={{ color: T.green, margin: 0, fontSize: 14 }}>
            ✓ Fichiers téléchargés — dépose <strong>floorplan.svg</strong> dans{" "}
            <code style={{ color: T.cyan }}>/config/www/osvision_v2/images/</code>{" "}
            et recharge le dashboard OSVision.
          </p>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <button style={S.btn("secondary")} onClick={onBack}>← Retour</button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TOKEN SCREEN
// ═══════════════════════════════════════════════════════════════════════════
function TokenScreen({ onConfirm }) {
  const [token, setToken] = useState(HA_TOKEN);
  return (
    <div style={{ maxWidth: 480, margin: "80px auto" }}>
      <div style={S.card}>
        <h2 style={{ ...S.title, marginBottom: 16 }}>CONNEXION HA</h2>
        <p style={S.sub}>
          Crée un jeton longue durée dans{" "}
          <em>Profil → Jetons d'accès longue durée</em> et colle-le ci-dessous.
        </p>
        <label style={S.label}>JETON D'ACCÈS</label>
        <input
          type="password"
          style={{ ...S.input, marginBottom: 16 }}
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder="eyJhbGciOi..."
        />
        <button style={S.btn()} onClick={() => { localStorage.setItem("osv_ha_token", token); onConfirm(token); }}>
          Connexion →
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════════════════
export default function App() {
  const [token, setToken] = useState(HA_TOKEN);
  const [step, setStep] = useState(1);
  const [house, setHouse] = useState({ floors: [], exteriors: [] });
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const STEPS = ["Structure", "Appareils", "Plan SVG"];

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const states = await haGet("states");
      const relevant = states
        .filter(s => {
          const dom = s.entity_id.split(".")[0];
          return ["light","switch","sensor","binary_sensor","climate",
                  "media_player","cover","camera","alarm_control_panel",
                  "vacuum","fan","lock"].includes(dom);
        })
        .map(s => ({
          entity_id: s.entity_id,
          friendly_name: s.attributes?.friendly_name || s.entity_id,
          state: s.state,
          room: null,
        }));
      setDevices(relevant);
      setStep(2);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  if (!token) return <TokenScreen onConfirm={t => setToken(t)} />;

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
        <div style={{ width: 36, height: 36, borderRadius: "50%",
          border: `2px solid ${T.cyan}`, display: "flex", alignItems: "center",
          justifyContent: "center", color: T.cyan, fontSize: 18 }}>⬡</div>
        <div>
          <h1 style={{ ...S.title, fontSize: 18, margin: 0 }}>OSVISION V2</h1>
          <p style={{ margin: 0, color: T.textMute, fontSize: 11, letterSpacing: 1 }}>
            DISCOVERY WIZARD
          </p>
        </div>
        <div style={{ marginLeft: "auto", color: T.textMute, fontSize: 11 }}>
          {HA_URL}
        </div>
      </div>

      {/* Step bar */}
      <div style={S.stepBar}>
        {STEPS.map((s, i) => (
          <div key={i} style={{ flex: 1, marginRight: i < STEPS.length - 1 ? 4 : 0 }}>
            <div style={S.stepDot(step === i + 1, step > i + 1)} />
            <div style={{ fontSize: 10, color: step >= i + 1 ? T.cyan : T.textMute,
              letterSpacing: 1, marginTop: 4, fontFamily: T.fontMono }}>
              {i + 1}. {s.toUpperCase()}
            </div>
          </div>
        ))}
      </div>

      {/* Steps */}
      {step === 1 && (
        <Step1Structure house={house} setHouse={setHouse} onNext={fetchDevices} />
      )}
      {step === 2 && (
        <Step2Devices
          house={house} devices={devices} setDevices={setDevices}
          loading={loading} error={error}
          onNext={() => setStep(3)} onBack={() => setStep(1)}
        />
      )}
      {step === 3 && (
        <Step3Generate house={house} devices={devices} onBack={() => setStep(2)} />
      )}
    </div>
  );
}
