/**
 * KargoSmart GPS Simulator
 * Interpolation linéaire départ→arrivée, mise à jour toutes les 3s.
 * Change le statut Django une seule fois par valeur (pas de doublons).
 */

class GPSSimulator {
  constructor(livraisonId, depart, arrivee, onUpdate) {
    this.livraisonId = livraisonId;
    this.depart = depart;
    this.arrivee = arrivee;
    this.onUpdate = onUpdate;
    this.step = 0;
    this.totalSteps = 30;
    this.timer = null;
    this.running = false;
    this.lastStatut = null;
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.step = 0;
    this.lastStatut = null;
    this._tick();
    this.timer = setInterval(() => this._tick(), 3000);
  }

  stop() {
    this.running = false;
    clearInterval(this.timer);
  }

  _pos(ratio) {
    const j = () => (Math.random() - 0.5) * 0.001;
    return {
      lat: this.depart.lat + (this.arrivee.lat - this.depart.lat) * ratio + j(),
      lng: this.depart.lng + (this.arrivee.lng - this.depart.lng) * ratio + j(),
    };
  }

  _statut(p) {
    if (p < 5)   return 'EN_ROUTE';
    if (p < 75)  return 'EN_COURS';
    if (p < 100) return 'PROCHE_DESTINATION';
    return 'LIVREE';
  }

  async _tick() {
    if (this.step > this.totalSteps) { this.stop(); return; }

    const ratio = this.step / this.totalSteps;
    const progression = Math.round(ratio * 100);
    const pos = this._pos(ratio);
    const statut = this._statut(progression);
    this.step++;

    // Mise à jour carte
    this.onUpdate({ ...pos, progression, statut });

    // Position GPS → API
    fetch('/api/gps/position/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify({ lat: pos.lat, lng: pos.lng, livraison_id: this.livraisonId, progression }),
    }).catch(() => {});

    // Statut Django — une seule fois par valeur
    if (statut !== this.lastStatut) {
      this.lastStatut = statut;
      const fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf());
      fd.append('nouveau_statut', statut);
      fd.append('commentaire', 'Simulation GPS automatique');
      fetch(`/livraisons/${this.livraisonId}/statut/`, { method: 'POST', body: fd })
        .then(r => r.json())
        .then(d => { if (!d.success) console.warn('Statut refusé:', statut); })
        .catch(() => {});
    }

    if (progression >= 100) this.stop();
  }
}

function csrf() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

window.GPSSimulator = GPSSimulator;
