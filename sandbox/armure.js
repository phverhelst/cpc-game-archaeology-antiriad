// Mouvement de Tal dans l'armure — transcription JavaScript de movement/armure.py, fonction pour fonction.
// Vérifié contre armure.py par sandbox/verif_js.py. S'appuie sur tal.js (sol, plafond, animateur).
(function (racine) {
  'use strict';
  const TM = (typeof module !== 'undefined' && module.exports) ? require('./tal.js') : racine.TalModele;
  const {MONTE, DESCEND, VERS_GAUCHE, VERS_DROITE, HAUT} = TM;

  function ModeleArmure(T, GAZ, opts) {       // GAZ : 128 couples [directions, vitesse] lus en &8EF3
    const m = TM.Modele(T, opts);
    const e_ = t => t.etat & 0x7F;
    const poser = (t, e) => { t.etat = e; t.pas = 0; t.attente = 0; };
    const FLOTTEMENT = [[1, 1], [1, 0], [1, 0], [1, 0], [1, 1], [1, 0], [1, 0], [1, 0],
                        [2, 1], [2, 0], [2, 0], [2, 0], [2, 1], [2, 0], [2, 0], [2, 0]];   // &8ED3

    function reglerGaz(t) { const [h, l] = GAZ[t.gaz & 0x7F]; t.dirs = (t.dirs & 0x0C) | h; t.vy = l; }   // &64DC
    function ralentir(t) { if (t.glisse) t.glisse--; }                                     // &6480
    function pousser(t, sens) { t.dirs = (t.dirs & 3) | sens; if (t.glisse !== 6) t.glisse++; }   // &6498
    function changerEtat(t, joy) {                                                          // &6457
      t.dirs &= 3;
      const c = m.classe(joy);
      if (t.energie === 0 && (joy & HAUT)) return;
      const n = T.transitions[e_(t)][0][c];
      if (n) poser(t, n);
    }
    function commande(t, joy) {                                                             // &63A9
      const masque = T.transitions[e_(t)][1];
      if ((masque & 0x10) && !(t.etat & 0x80)) return;
      let c = joy; t.entree = c;
      if (t.energie === 0) c = t.entree = 0x02;
      const perdu = ((c & 1) && t.gaz === 6) || ((c & 2) && t.gaz === 8);  // son &752A : IX écrasé
      const regler = perdu ? () => {} : reglerGaz;
      if (c & 1) { if (t.gaz) { t.gaz--; regler(t); } }
      else if ((c & 2) || t.gaz < 7) { if (t.gaz !== 0x0E) { t.gaz++; regler(t); } }
      else if (t.gaz >= 8) { t.gaz--; regler(t); }
      if (t.glisse === 0) changerEtat(t, joy);                                              // &63F8
      const prec = t.sens_prec; t.sens_prec = t.entree & 0x0C;
      if ((t.entree & 0x0C) !== prec) { ralentir(t); return; }
      for (const [etat, sens] of [[0x1B, VERS_DROITE], [0x19, VERS_GAUCHE]])
        if (e_(t) === etat) { if (t.entree & sens) pousser(t, sens); else ralentir(t); }
    }
    const reflechir = t => { t.gaz = 0x0F - t.gaz; };                                     // &6390
    function solEtPlafond(t, ecran) {                                                       // &62C5
      t.en_vol = 0xFF;
      let auSol = false, b = t.vy + 1, ligne = t.y + t.hauteur + 1, c = 0;
      for (let k = 0; k < b; k++) {
        if (ligne < 0x32 || ligne >= 0xBA) break;
        if (m.sol(ecran, ligne, t.x)) {
          if (t.dirs & DESCEND) t.vy = c;
          if (c === 0) {
            auSol = true; t.en_vol = 0;
            if ((t.dirs & DESCEND) && (e_(t) === 0x16 || e_(t) === 0x17)) { t.dirs = 0; poser(t, 0x17); return; }
          }
          break;
        }
        ligne++; c++;
      }
      b = t.vy + 1; ligne = t.y + 3; c = 0;                                                 // &6324
      for (let k = 0; k < b; k++) {
        if (m.plafond(ecran, ligne, t.x)) {
          if (t.dirs & MONTE) t.vy = c;
          t.en_vol = 0;
          if (auSol) { t.dirs &= 0x0C; return; }
          if (t.dirs & MONTE) { t.dirs = (t.dirs & 0x0C) | DESCEND; reflechir(t); return; }
          break;
        }
        ligne--; c++;
      }
      if (auSol && (t.dirs & DESCEND)) { t.dirs = (t.dirs & 0x0C) | MONTE; reflechir(t); }
    }
    function flotter(t) {                                                                   // &627B
      if (t.gaz !== 7 || e_(t) === 0x17 || !t.en_vol) return;
      t.phase = (t.phase + 1) & 0x0F;
      const [h, l] = FLOTTEMENT[t.phase];
      t.dirs = (t.dirs & 0x0C) | h; t.vy = l;
    }
    function testMur(t, ecran) {                                                            // &67B6 (armure)
      if (!T.etats_mur.includes(e_(t))) { t.mur = 0xFF; return false; }
      const h = t.dirs & 0x0C;
      if (h === 0) { t.mur = 0xFF; return false; }
      const col = ((h & VERS_DROITE) ? t.x + 7 : t.x - 1) & 0xFF;
      if (t.y < 0x33) {
        for (let i = 0; i < 4; i++) if (ecran.octet(0x32 + i, col)) { t.mur = 0; return true; }
        t.mur = 0xFF; return false;
      }
      for (let k = 0; k < 0x26; k++) {
        const b = ecran.octet((t.y + 4 + k) & 0xFF, col);
        if ((b & 0xAA) === 0xA8 || (b & 0x55) === 0x54) { t.mur = 0; return true; }
      }
      t.mur = 0xFF; return false;
    }
    function rebondMur(t) { t.dirs ^= 0x0C; t.sens_prec ^= 0x03; }                         // &68A3
    function armureTour(t, joy, ecran) {                                                    // &5744
      if (t.deplaceur) return;
      commande(t, joy);
      solEtPlafond(t, ecran);
      flotter(t);
      if (testMur(t, ecran)) rebondMur(t);
      if (t.cellule === 0) { t.cellule = 0xFF; t.energie = 0x1F; }
    }
    function tour(t, joy, ecran) { armureTour(t, joy, ecran); m.animer(t); }
    return {tour, armureTour, pied: m};
  }

  const api = {ModeleArmure};
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else racine.TalArmure = api;
})(this);
