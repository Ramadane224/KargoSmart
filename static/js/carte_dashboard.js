/**
 * KargoSmart — Carte dashboard globale (Leaflet + OpenStreetMap)
 * Affiche les livreurs actifs et les livraisons en cours.
 */

const CONAKRY = [9.5370, -13.6773]; // Centre par défaut (Conakry, Guinée)

function initDashboardMap(elementId) {
  const map = L.map(elementId, { zoomControl: true }).setView(CONAKRY, 13);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  const livreurIcon = L.divIcon({
    className: '',
    html: '<div class="gps-marker-livreur">🛵</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  const livraisonsLayer = L.layerGroup().addTo(map);
  const livreursLayer = L.layerGroup().addTo(map);

  async function refresh() {
    // Positions livreurs
    try {
      const res = await fetch('/api/gps/livreurs/');
      const positions = await res.json();
      livreursLayer.clearLayers();
      positions.forEach(pos => {
        const marker = L.marker([pos.latitude, pos.longitude], { icon: livreurIcon });
        marker.bindPopup(`
          <strong>${pos.nom_livreur}</strong><br>
          ${pos.vehicule} · ${pos.progression}%<br>
          ${pos.livraison_code ? '📦 ' + pos.livraison_code : 'Libre'}
        `);
        livreursLayer.addLayer(marker);
      });
    } catch (e) { console.warn('Erreur positions livreurs', e); }

    // Livraisons en cours
    try {
      const res = await fetch('/api/livraisons/en_cours/');
      const livraisons = await res.json();
      livraisonsLayer.clearLayers();
      livraisons.forEach(liv => {
        if (liv.latitude_arrivee && liv.longitude_arrivee) {
          const marker = L.circleMarker(
            [liv.latitude_arrivee, liv.longitude_arrivee],
            { radius: 8, color: statutColor(liv.statut), fillOpacity: 0.8 }
          );
          marker.bindPopup(`
            <strong>${liv.code_livraison}</strong><br>
            ${liv.client_nom}<br>
            <span style="color:${statutColor(liv.statut)}">${liv.statut_display}</span><br>
            📍 ${liv.adresse_arrivee}
          `);
          livraisonsLayer.addLayer(marker);
        }
      });
    } catch (e) { console.warn('Erreur livraisons en cours', e); }
  }

  refresh();
  setInterval(refresh, 5000); // Rafraîchissement toutes les 5s
  return map;
}

function statutColor(statut) {
  const colors = {
    EN_ATTENTE: '#94a3b8',
    ASSIGNEE: '#3b82f6',
    EN_ROUTE: '#f59e0b',
    EN_COURS: '#f97316',
    PROCHE_DESTINATION: '#8b5cf6',
    LIVREE: '#22c55e',
    ANNULEE: '#ef4444',
    ECHOUEE: '#dc2626',
  };
  return colors[statut] || '#64748b';
}

window.initDashboardMap = initDashboardMap;
window.statutColor = statutColor;
