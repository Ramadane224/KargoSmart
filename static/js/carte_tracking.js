/**
 * KargoSmart — Carte tracking livraison
 * Fonctionne avec ou sans coordonnées GPS (fallback Conakry).
 */

const CONAKRY_LAT = 9.5370;
const CONAKRY_LNG = -13.6773;
const DEFAUT_DEPART = { lat: 9.5095, lng: -13.7122 };
const DEFAUT_ARRIVEE = { lat: 9.5731, lng: -13.6136 };

console.debug('[tracking] carte_tracking.js chargé');

function initTrackingMap(elementId, cfg) {
  console.debug('[tracking] initTrackingMap start', elementId, cfg);
  const container = document.getElementById(elementId);
  if (!container) {
    console.error('[tracking] container introuvable:', elementId);
    return null;
  }

  const placeholder = document.getElementById('map-tracking-placeholder');
  if (placeholder) {
    placeholder.style.display = 'flex';
    placeholder.textContent = 'Initialisation de la carte...';
  }

  if (typeof L === 'undefined') {
    console.error('[tracking] Leaflet introuvable. Vérifiez que la librairie est chargée.');
    container.innerHTML = '<div class="flex h-full items-center justify-center text-sm text-red-500">Erreur : Leaflet non chargé.</div>';
    return null;
  }

  const parseCoord = (value) => {
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  };

  const latDep = parseCoord(cfg.latDepart);
  const lngDep = parseCoord(cfg.lngDepart);
  const latArr = parseCoord(cfg.latArrivee);
  const lngArr = parseCoord(cfg.lngArrivee);
  const latLivreur = parseCoord(cfg.latLivreur);
  const lngLivreur = parseCoord(cfg.lngLivreur);

  const hasDepart = latDep !== null && lngDep !== null;
  const hasArrivee = latArr !== null && lngArr !== null;
  const hasLivreur = latLivreur !== null && lngLivreur !== null;

  const initialCenter = hasDepart
    ? [latDep, lngDep]
    : hasLivreur
    ? [latLivreur, lngLivreur]
    : hasArrivee
    ? [latArr, lngArr]
    : [CONAKRY_LAT, CONAKRY_LNG];

  let map;
  try {
    map = L.map(elementId).setView(initialCenter, 12);
  } catch (error) {
    console.error('[tracking] impossible de créer la carte', error);
    if (container) {
      container.innerHTML = '<div class="flex h-full items-center justify-center text-sm text-red-500">Erreur d’initialisation de la carte.</div>';
    }
    return null;
  }

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    subdomains: 'abc',
    maxZoom: 19,
  }).addTo(map);

  map.whenReady(() => {
    map.invalidateSize();
    if (placeholder) {
      placeholder.style.display = 'none';
    }
    console.debug('[tracking] carte prête');
  });

  const departIcon = L.divIcon({
    className: '',
    html: '<div style="font-size:22px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.4))">🏪</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

  const arriveeIcon = L.divIcon({
    className: '',
    html: '<div style="font-size:22px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.4))">📍</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

  const markers = [];
  if (hasDepart) {
    markers.push(L.marker([latDep, lngDep], { icon: departIcon }).addTo(map).bindPopup('Départ'));
  }
  if (hasArrivee) {
    markers.push(L.marker([latArr, lngArr], { icon: arriveeIcon }).addTo(map).bindPopup('Destination'));
  }

  let routeLine = null;
  const createRoute = (points) => {
    if (routeLine) {
      routeLine.remove();
    }
    routeLine = L.polyline(points, {
      color: '#3b82f6',
      weight: 3,
      dashArray: '8 4',
      opacity: 0.7,
    }).addTo(map);
    const bounds = routeLine.getBounds();
    if (markers.length > 0) {
      markers.forEach((m) => bounds.extend(m.getLatLng()));
    }
    if (hasLivreur) {
      bounds.extend([latLivreur, lngLivreur]);
    }
    map.fitBounds(bounds, { padding: [30, 30] });
  };

  if (hasDepart && hasArrivee) {
    createRoute([[latDep, lngDep], [latArr, lngArr]]);
  }

  const livreurIcon = L.divIcon({
    className: '',
    html: '<div style="font-size:26px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5))">🛵</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  const initLat = hasLivreur ? latLivreur : hasDepart ? latDep : hasArrivee ? latArr : CONAKRY_LAT;
  const initLng = hasLivreur ? lngLivreur : hasDepart ? lngDep : hasArrivee ? lngArr : CONAKRY_LNG;
  const livreurMarker = L.marker([initLat, initLng], { icon: livreurIcon }).addTo(map).bindPopup('Livreur en route');

  function drawRoute(currentLat, currentLng) {
    const points = [];
    if (hasDepart) {
      points.push([latDep, lngDep]);
    }
    if (Number.isFinite(currentLat) && Number.isFinite(currentLng)) {
      points.push([currentLat, currentLng]);
    }
    if (hasArrivee) {
      points.push([latArr, lngArr]);
    }
    if (points.length > 1) {
      createRoute(points);
    }
  }

  const progressBar = document.getElementById('progression-bar');
  const progressText = document.getElementById('progression-text');
  const statutBadge = document.getElementById('statut-badge');

  function updateUI({ lat, lng, progression, statut }) {
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return;
    }
    livreurMarker.setLatLng([lat, lng]);
    drawRoute(lat, lng);
    if (progressBar) progressBar.style.width = progression + '%';
    if (progressText) progressText.textContent = progression + '%';
    if (statutBadge) {
      statutBadge.textContent = statut.replace(/_/g, ' ');
      const colors = {
        EN_ROUTE: '#f59e0b',
        EN_COURS: '#f97316',
        PROCHE_DESTINATION: '#8b5cf6',
        LIVREE: '#22c55e',
        ASSIGNEE: '#3b82f6',
      };
      statutBadge.style.background = colors[statut] || '#64748b';
    }
  }

  const btn = document.getElementById('btn-simuler');
  if (btn) {
    if (typeof GPSSimulator === 'function') {
      const sim = new GPSSimulator(
        cfg.livraisonId,
        { lat: latDep, lng: lngDep },
        { lat: latArr, lng: lngArr },
        updateUI,
        () => {
          btn.disabled = false;
          btn.textContent = '▶ Simuler déplacement';
          btn.classList.replace('bg-slate-400', 'bg-blue-600');
        },
      );

      btn.addEventListener('click', () => {
        if (sim.running) return;
        btn.disabled = true;
        btn.textContent = '⏳ Simulation en cours...';
        btn.classList.replace('bg-blue-600', 'bg-slate-400');
        sim.start();
      });
    } else {
      console.warn('[tracking] GPSSimulator indisponible. Le bouton simuler est désactivé.');
      btn.disabled = true;
      btn.textContent = 'Simulateur indisponible';
    }
  }

  updateUI({
    lat: initLat,
    lng: initLng,
    progression: cfg.progression != null ? cfg.progression : 0,
    statut: cfg.statut || 'ASSIGNEE',
  });

  setTimeout(() => {
    if (placeholder) {
      placeholder.style.display = 'none';
    }
  }, 1200);

  setInterval(async () => {
    try {
      const r = await fetch(`/api/gps/tracking/${cfg.livraisonId}/`);
      const d = await r.json();
      if (d.position_livreur) {
        updateUI({
          lat: parseFloat(d.position_livreur.latitude),
          lng: parseFloat(d.position_livreur.longitude),
          progression: d.position_livreur.progression,
          statut: d.statut,
        });
      }
    } catch (e) {
      console.warn('[tracking] polling failed', e);
    }
  }, 5000);

  return map;
}

window.initTrackingMap = initTrackingMap;

function startTrackingMapFromDOM() {
  const mapEl = document.getElementById('map-tracking');
  if (!mapEl) {
    return;
  }

  const statusEl = document.getElementById('map-tracking-status');
  const debugEl = document.getElementById('map-tracking-debug');
  const placeholder = document.getElementById('map-tracking-placeholder');

  function setStatus(text, isError) {
    if (statusEl) {
      statusEl.textContent = 'Statut du suivi : ' + text;
      statusEl.className = 'mt-3 text-xs font-medium ' + (isError ? 'text-red-600' : 'text-slate-500');
    }
  }

  function setDebug(text) {
    if (debugEl) {
      debugEl.textContent = 'Debug : ' + text;
    }
  }

  setStatus('initialisation en cours...');
  setDebug('chargement du module de tracking');

  const cfg = {
    livraisonId: mapEl.dataset.livraisonId,
    latDepart: parseFloat(mapEl.dataset.latDepart),
    lngDepart: parseFloat(mapEl.dataset.lngDepart),
    latArrivee: parseFloat(mapEl.dataset.latArrivee),
    lngArrivee: parseFloat(mapEl.dataset.lngArrivee),
    latLivreur: parseFloat(mapEl.dataset.latLivreur),
    lngLivreur: parseFloat(mapEl.dataset.lngLivreur),
    progression: parseFloat(mapEl.dataset.progression) || 0,
    statut: mapEl.dataset.statut || 'ASSIGNEE',
  };

  if (typeof initTrackingMap !== 'function') {
    setStatus('initTrackingMap introuvable', true);
    setDebug('initTrackingMap non défini dans carte_tracking.js');
    console.error('[tracking] initTrackingMap manquant');
    return;
  }

  const map = initTrackingMap('map-tracking', cfg);
  if (!map) {
    setStatus('impossible de créer la carte', true);
    setDebug('initTrackingMap a retourné null');
    return;
  }

  setStatus('carte prête', false);
  setDebug('initialisation terminée');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startTrackingMapFromDOM);
} else {
  startTrackingMapFromDOM();
}
