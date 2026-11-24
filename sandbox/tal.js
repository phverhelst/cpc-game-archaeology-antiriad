// Mouvement de Tal à pied — transcription JavaScript de movement/tal.py, fonction pour fonction.
// La référence est tal.py (vérifié contre le code Z80 d'origine) ; ce fichier est vérifié contre
// tal.py par sandbox/verif_js.py. Les adresses renvoient aux routines du jeu.
(function (racine) {
  'use strict';
  const HAUT = 1, BAS = 2, GAUCHE = 4, DROITE = 8, FEU = 16;
  const MONTE = 1, DESCEND = 2, VERS_GAUCHE = 4, VERS_DROITE = 8;

  function nouveauTal(init) {
    return Object.assign({
      x: 0x24, y: 0x57, dirs: DESCEND, vx: 1, vy: 0, etat: 0x02, pas: 0, attente: 0,
      sprite: 0x08, demi_largeur: 3, hauteur: 0x2A, saut: 0, mur: 0xFF,
    }, init || {});
  }
  const e_ = t => t.etat & 0x7F;

  function Modele(T, opts) {
    opts = opts || {};   // sautDiagonal : option absente du jeu (voir movement/tal.py, OPTIONS)
    const bits = a => { let n = 0; while (a) { n += a & 1; a >>= 1; } return n; };
    const classe = joy => T.classes[(joy & FEU) ? 0x0F : (joy & 0x0F)];          // &656F
    const poser = (t, e) => { t.etat = e; t.pas = 0; t.attente = 0; };           // &6AE2

    function sol(ecran, ligne, col) {                                            // &68B4
      if ((ligne & 7) !== 2) return false;
      for (let i = 0; i < T.motif_sol.length; i++) {
        const b = ecran.octet(ligne, col + i), m = T.motif_sol[i];
        let a = b & 0x8A; if (a && a === (m & 0xAA)) return true;
        a = b & 0x45; if (a && a === (m & 0x55)) return true;
      }
      return false;
    }
    function plafond(ecran, ligne, col) {                                        // &6714
      if (ligne >= 0x3A && (ligne & 7) !== 1) return false;
      for (let i = 0; i < 4; i++) {
        const b = ecran.octet(ligne, col + 1 + i);
        let a = b & 0x8A; if (a && a === 0x80) return true;
        a = b & 0x45; if (a && a === 0x40) return true;
      }
      return false;
    }
    function testMur(t, ecran) {                                                 // &67B6
      if (!T.etats_mur.includes(e_(t))) { t.mur = 0xFF; return false; }
      const h = t.dirs & 0x0C; let col;
      if (h === 0) {
        if (e_(t) === 0x02) col = t.x - 1;
        else if (e_(t) === 0x0B) col = t.x + 7;
        else { t.mur = 0xFF; return false; }
      } else col = (h & VERS_DROITE) ? t.x + 7 : t.x - 1;
      col &= 0xFF;
      const ligne = t.y + 4;
      for (let k = 0; k < 0x23; k++) {
        const b = ecran.octet((ligne + k) & 0xFF, col);
        if ((b & 0xAA) === 0xA8 || (b & 0x55) === 0x54) { t.mur = 0; return true; }
      }
      t.mur = 0xFF; return false;
    }
    function transitions(t, joy) {                                               // &675C
      const [suivants, masque] = T.transitions[e_(t)];
      if ((masque & 0x10) && !(t.etat & 0x80)) return;
      const c = classe(joy);
      t.dirs = (t.dirs & 3) | (joy & masque & 0x0F);
      const n = suivants[c];
      if (n === 0) return;
      if (t.mur === 0 && (n === 0x0C || n === 0x03)) return;
      poser(t, n);
    }
    function lancerSaut(t, c) {                                                  // &66B1
      t.dirs = (c & 0x0C) | MONTE;
      poser(t, (t.sprite & 0x80) ? 0x10 : 0x07);
      t.saut = 0x0B;
    }
    function entree(t, joy) {                                                    // &6659
      const e = e_(t);
      if (opts.sautDiagonal && (joy & HAUT) && !(joy & FEU)) {           // option, absente du jeu
        const face = (e === 0x02 || e === 0x03) ? VERS_GAUCHE : (e === 0x0B || e === 0x0C) ? VERS_DROITE : 0;
        if (face && (joy & 0x0C) === face) { if (t.dirs & DESCEND) lancerSaut(t, face); return; }
      }
      if (!(joy & FEU)) {
        if ((joy & HAUT) && (e === 0x02 || e === 0x0B)) {
          if (t.dirs & DESCEND) lancerSaut(t, t.dirs);
          return;
        }
        return transitions(t, joy);
      }
      if (e === 0x03 || e === 0x0C) { if (t.dirs & DESCEND) lancerSaut(t, t.dirs); return; }
      const a = joy & 0x0D;
      if (a === 0 || bits(a) % 2) return transitions(t, joy);
      const c = (a & 0x0C) | 0x02;
      if (((c & VERS_GAUCHE) && e === 0x02) || ((c & VERS_DROITE) && e === 0x0B)) return lancerSaut(t, c);
      return transitions(t, joy);
    }
    function gravite(t, joy, ecran) {                                            // &65A2
      if (t.dirs & MONTE) {                                                      // &66CE
        const b = T.vitesses[t.saut];
        t.vy = b;
        let ligne = t.y + 7, c = 0;
        for (let k = 0; k < b; k++) {
          if (ligne < 0x3A && plafond(ecran, ligne, t.x)) {
            t.vy = c;
            if (c) return;
            t.saut = 0; t.dirs = (t.dirs & 0x0C) | DESCEND; return;
          }
          ligne--; c++;
        }
        t.saut--;
        if (t.saut === 0) t.dirs = (t.dirs & 0x0C) | DESCEND;
        return;
      }
      const b = T.vitesses[t.saut];
      let ligne = t.y + t.hauteur + 1, c = 0;
      for (let k = 0; k < b; k++) {
        if (ligne < 0x32 || ligne >= 0xBA) break;
        if (sol(ecran, ligne, t.x)) {                                            // &6610
          t.vy = c;
          if (e_(t) === 0x07 || e_(t) === 0x10 || t.saut) {
            t.saut = 0; t.dirs &= 3;
            poser(t, e_(t) < 0x0B ? 0x09 : 0x12);
            return;
          }
          return entree(t, joy);
        }
        ligne++; c++;
      }
      t.vy = T.vitesses[t.saut];                                                 // &65E2
      if (t.saut + 1 < 0x11) t.saut++;
      const e = e_(t);
      if (e < 0x0B) { if (e !== 0x02) poser(t, 0x08); }
      else if (e !== 0x0B) poser(t, 0x11);
    }
    function bloque(t) {                                                         // &6876
      if (e_(t) === 0x0C) poser(t, 0x0B);
      else if (e_(t) === 0x03) poser(t, 0x02);
      else if (t.saut === 0x0A) { t.dirs &= 3; return; }
      t.dirs = DESCEND;
    }
    function piedTour(t, joy, ecran) {                                           // &5787
      gravite(t, joy, ecran);
      if (testMur(t, ecran)) bloque(t);
    }
    function animer(t) {                                                         // &6B2F, &6C23
      if (e_(t)) {
        if (t.attente) t.attente--;
        else {
          const s = T.animations[e_(t)];
          for (;;) {
            const b = s.code[t.pas];
            if (b === 0xFC) { t.pas = 0; continue; }
            if (b === 0xFD) t.etat |= 0x80;
            else if (b === 0xFE) poser(t, s.code[t.pas + 1]);
            else if (b === 0xFF) throw new Error('FF : fin d\'objet');
            else {
              t.sprite = b;
              [t.demi_largeur, t.hauteur] = T.sprites[b & 0x7F];
              t.pas++; t.attente = s.delai;
            }
            break;
          }
        }
      }
      const d = t.dirs;
      if (d & MONTE) t.y = Math.max(t.y - t.vy, 0);
      if (d & DESCEND) t.y = Math.min(t.y + t.vy + t.hauteur, 0xFF) - t.hauteur;
      if (d & VERS_GAUCHE) t.x = Math.max(t.x - t.vx, 0);
      if (d & VERS_DROITE) { const l2 = (2 * t.demi_largeur) & 0xFF; t.x = Math.min(t.x + l2 + t.vx, 0x4F) - l2; }
    }
    function tour(t, joy, ecran) { piedTour(t, joy, ecran); animer(t); }
    return { tour, piedTour, animer, classe, sol, plafond, testMur, opts };
  }

  const api = { Modele, nouveauTal, HAUT, BAS, GAUCHE, DROITE, FEU, MONTE, DESCEND, VERS_GAUCHE, VERS_DROITE };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else racine.TalModele = api;
})(this);
