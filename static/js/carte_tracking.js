/**
 * KargoSmart — Carte tracking livraison
 * Fonctionne avec ou sans coordonnées GPS (fallback Conakry).
 */

const CONAKRY_LAT = 9.5370;
const CONAKRY_LNG = -13.6773;

// Coordonnées simulées par défaut pour Conakry (départ Kaloum, arrivée Ratoma)
const DEFAUT_DEPART  = { lat: 9.5095, lng: -13.7122 };
const DEFAUT_ARRIVEE = { lat: 9.5731, lng: -13.6136 };

function initTrackingMap(elementId, cfg) {
  const latDep = cfg.latDepart  || DEFAUT_DEPART.lat;
  const lngDep = cfg.lngDepart  || DEFAUT_DEPART.lng;
  const latArr = cfg.latArrivee || DEFAUT_ARRIVEE.lat;
  const lngArr = cfg.lngArrivee || DEFAUT_ARRIVEE.lng;

  const map = L.map(elementId).setView([latDep, lngDep], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap', maxZoom: 19,
  }).addTo(map);

  // Marqueurs départ / arrivée
  L.marker([latDep, lngDep], {
    icon: L.divIcon({ className:'', html:'<div style="font-size:22px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.4))">🏪</div>', iconSize:[28,28], iconAnchor:[14,14] }),
  }).addTo(map).bindPopup('Départ');

  L.marker([latArr, lngArr], {
    icon: L.divIcon({ className:'', html:'<div style="font-size:22px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.4))">📍</div>', iconSize:[28,28], iconAnchor:[14,14] }),
  }).addTo(map).bindPopup('Destination');

  // Ligne de trajet
  const polyline = L.polyline([[latDep, lngDep],[latArr, lngArr]], {
    color:'#3b82f6', weight:3, dashArray:'8 4', opacity:0.7,
  }).addTo(map);
  map.fitBounds(polyline.getBounds(), { padding:[30,30] });

  // Marqueur livreur
  const livreurIcon = L.divIcon({
    className:'',
    html:'<div style="font-size:26px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.5))">🛵</div>',
    iconSize:[32,32], iconAnchor:[16,16],
  });
  const initLat = cfg.latLivreur || latDep;
  const initLng = cfg.lngLivreur || lngDep;
  let livreurMarker = L.marker([initLat, initLng], { icon: livreurIcon }).addTo(map);
  livreurMarker.bindPopup('Livreur en route');

  // Éléments UI
  const progressBar  = document.getElementById('progression-bar');
  const progressText = document.getElementById('progression-text');
  const statutBadge  = document.getElementById('statut-badge');

  function updateUI({ lat, lng, progression, statut }) {
    livreurMarker.setLatLng([lat, lng]);
    if (progressBar)  progressBar.style.width = progression + '%';
    if (progressText) progressText.textContent = progression + '%';
    if (statutBadge) {
      statutBadge.textContent = statut.replace(/_/g, ' ');
      const colors = { EN_ROUTE:'#f59e0b', EN_COURS:'#f97316', PROCHE_DESTINATION:'#8b5cf6', LIVREE:'#22c55e', ASSIGNEE:'#3b82f6' };
      statutBadge.style.background = colors[statut] || '#64748b';
    }
  }

  // Bouton simulation
  const btn = document.getElementById('btn-simuler');
  if (btn) {
    const sim = new GPSSimulator(
      cfg.livraisonId,
      { lat: latDep, lng: lngDep },
      { lat: latArr, lng: lngArr },
      updateUI,
    );
    btn.addEventListener('click', () => {
      btn.disabled = true;
      btn.textContent = '⏳ Simulation en cours...';
      btn.classList.replace('bg-blue-600', 'bg-slate-400');
      sim.start();
    });
  }

  // Polling position réelle toutes les 5s
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
    } catch {}
  }, 5000);

  return map;
}

window.initTrackingMap = initTrackingMap;
