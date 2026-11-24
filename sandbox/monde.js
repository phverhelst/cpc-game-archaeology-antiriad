// Les objets du jeu (ennemis, obstacles, pierre, Tal en tant qu'objet) : transcription en JavaScript de
// enemies/monde.py, elle-même transcrite du code Z80 d'origine. Le modèle travaille sur une image de la
// mémoire du jeu (Uint8Array de 64 Ko) : il lit les tables du binaire (&8B00-&A0FF suffisent) et lit et
// écrit les variables du jeu en &B400-&B5FF, aux mêmes adresses. Vérifié contre monde.py par verif_monde_js.py.
(function (racine) {
  const OBJ = 0xB400, TAILLE = 19, ACTIFS = 0xB4EE, VIE_TAL = 0xB4FB, ENERGIE_ARMURE = 0xB4FD, A_PIED = 0xB4F1,
    SALLE = 0xB4ED, SCORE_AFFICHE = 0xB534, SCORE = 0xB536, COUPS = 0xB543, CHRONO_GENERATEUR = 0xB54F,
    REPIT = 0xB552, PROCHAIN = 0xB553, JEU_LANCE = 0xB512, NEGATEUR = 0xB51C, CONTACTS = 0xB502;
  const o = n => OBJ + TAILLE * n;
  const mot = (m, a) => m[a] | m[a + 1] << 8;
  const ecrireMot = (m, a, v) => { m[a] = v & 0xFF; m[a + 1] = (v >> 8) & 0xFF; };
  const animPtr = (m, e) => mot(m, 0x9021 + 2 * e);
  const prop = (m, e) => 0x922A + 4 * ((e - 1) & 0xFF);          // adresse des 4 octets de l'état
  const actif = (m, n) => (m[ACTIFS] >> n) & 1;

  function creer(m, n, x, y, script, etat) {                       // &6A50
    m[ACTIFS] |= 1 << n;
    const b = o(n);
    for (const k of [0x11, 1, 2, 7, 0xB]) m[b + k] = 0;
    m[b + 3] = m[b + 5] = x; m[b + 4] = m[b + 6] = y;
    m[b] = script; m[b + 0xA] = etat;
    const p = animPtr(m, etat);
    m[b + 0xC] = m[p]; m[b + 0xD] = m[b + 0xE] = m[p + 1];
    m[b + 0x12] = m[prop(m, etat)] & 0x40 ? 1 : 0;
  }
  function poserEtat(m, n, e) { const b = o(n); m[b + 0xA] = e; m[b + 0xB] = 0; m[b + 0xC] = 0; }   // &6AE2
  function detruire(m, n) { m[ACTIFS] &= ~(1 << n) & 0xFF; }       // &6955
  function tuer(m, n) {                                            // &5D9E
    const b = o(n);
    if (m[b + 0x12] === 0) { m[b + 0x12] = 0xFF; m[b + 0x11] = 0x0C; m[b] = 0; m[b + 7] = 0; }
  }
  function fondus(m) {                                             // &5704
    for (let n = 0; n < 8; n++) {
      const b = o(n), f = m[b + 0x12];
      if (!f) continue;
      if (f < 0x80) { m[b + 0x11] = (m[b + 0x11] + 1) & 0xFF; if (m[b + 0x11] === 0x0C) m[b + 0x12] = 0; }
      else { m[b + 0x11] = (m[b + 0x11] - 1) & 0xFF; if (m[b + 0x11] >= 0x80) { m[b + 0x12] = 0; detruire(m, n); } }
    }
  }

  function guidage(m, b) {                                         // &6CDE
    let c = 0;
    const a = (m[0xB403] - 3) & 0xFF;
    if (a !== m[b + 3]) c |= a < m[b + 3] ? 4 : 8;
    const cible = (m[0xB404] + 0x0C) & 0xFF;
    let d = (cible - m[b + 4]) & 0xFF;
    if (d >= 0x80) d = (-d) & 0xFF;
    if (d >= 4 && cible !== m[b + 4]) c |= cible < m[b + 4] ? 1 : 2;
    return c;
  }
  function deplacer(m, b, c) {                                     // &6C23-&6C93
    if (c & 1) m[b + 4] = Math.max(m[b + 4] - m[b + 9], 0);
    if (c & 2) { const a = (m[b + 4] + m[b + 9]) & 0xFF, s = a + m[b + 0x10]; m[b + 4] = ((s > 0xFF ? 0xFF : s) - m[b + 0x10]) & 0xFF; }
    if (c & 4) m[b + 3] = Math.max(m[b + 3] - m[b + 8], 0);
    if (c & 8) { const l2 = (m[b + 0xF] << 1) & 0xFF, a = (l2 + m[b + 3] + m[b + 8]) & 0xFF; m[b + 3] = (Math.min(a, 0x4F) - l2) & 0xFF; }
  }
  function animer(m, n) {                                          // &6B2F
    const b = o(n), e = m[b + 0xA] & 0x7F;
    if (e) {
      if (m[b + 0xC]) m[b + 0xC]--;
      else for (;;) {
        const p = animPtr(m, e), code = m[p + 1 + m[b + 0xB]];
        if (code === 0xFC) { m[b + 0xB] = 0; continue; }
        if (code === 0xFD) m[b + 0xA] |= 0x80;
        else if (code === 0xFE) poserEtat(m, n, m[p + 2 + m[b + 0xB]]);
        else if (code === 0xFF) { detruire(m, n); return; }
        else {
          m[b + 0xD] = code;
          const s = 0x9432 + 4 * (code & 0x7F);
          m[b + 0xF] = m[s + 2]; m[b + 0x10] = m[s + 3];
          m[b + 0xB] = (m[b + 0xB] + 1) & 0xFF; m[b + 0xC] = m[p];
        }
        break;
      }
    }
    if (m[b] && !m[b + 0x12]) {                                    // &6BB0 : script de mouvement
      if (m[b + 2]) m[b + 2]--;
      else for (;;) {
        const q = mot(m, 0x97F8 + 2 * m[b]) + 4 * m[b + 1], d = m[q];
        if (d === 0xFC) { m[b + 1] = 0; continue; }
        if (d === 0xFE) { m[b] = m[b + 1] = m[b + 2] = 0; m[0xB409] = 0; m[0xB408] = 1; m[0xB407] = 2; }
        else if (d < 0xFC) { m[b + 7] = d; m[b + 2] = m[q + 1]; m[b + 8] = m[q + 2]; m[b + 9] = m[q + 3]; m[b + 1] = (m[b + 1] + 1) & 0xFF; }
        break;
      }
    }
    const c = m[b + 7];
    deplacer(m, b, c === 0x0F ? guidage(m, b) : c);
    if (n && !m[b + 0x12]) {                                       // &6C94
      const e2 = m[b + 0xD] ^ m[b + 0xE];
      if (!(e2 | m[b + 7]) || !(e2 | m[b + 8] | m[b + 9])) return;
    }
    m[b + 5] = m[b + 3]; m[b + 6] = m[b + 4]; m[b + 0xE] = m[b + 0xD];
  }
  function animateur(m) { for (let n = 7; n >= 0; n--) if (actif(m, n)) animer(m, n); }   // &6B0E

  function lancerPierre(m) {                                       // &68EF
    const t = o(0);
    if (m[t + 0xB] !== 5) return;
    let script, x;
    if (m[t + 0xA] === 0x0A) { script = 2; x = m[t + 3] - 2; }
    else if (m[t + 0xA] === 0x13) { script = 1; x = m[t + 3] + 6; }
    else return;
    if (actif(m, 1)) return;
    creer(m, 1, x & 0xFF, (m[t + 4] + 6) & 0xFF, script, 0x2C);
  }
  function arreterPierre(m) {                                      // &5D6F
    const p = o(1);
    m[p + 4] = (m[p + 4] - 4) & 0xFF; m[p] = 0; m[p + 7] = 0; poserEtat(m, 1, 0x2D);
  }
  function pierreSortie(m) {                                       // &6932
    if (!actif(m, 1) || (m[o(1) + 0xA] & 0x7F) === 0x2D) return;
    const x = m[o(1) + 3];
    if (x === 0 || x >= 0x49) detruire(m, 1);
  }

  function collisions(m) {                                         // &5933
    let hl = CONTACTS;
    for (const n of [0, 1]) {
      if (!actif(m, n)) continue;                                  // les résultats précédents restent
      const ix = o(n);
      for (let k = 7; k >= 2; k--) {
        const iy = o(k);
        let r = 0xFF;
        if (actif(m, k) && !((m[iy + 0xA] & 0x7F) === 0x2F && m[0xB403] < m[iy + 3])) {
          const dx = m[ix + 3] - m[iy + 3], d = dx < 0 ? m[ix + 0xF] : m[iy + 0xF];
          if (Math.abs(dx) < ((d << 1) & 0xFF)) {
            const dy = m[ix + 4] - m[iy + 4];
            if (Math.abs(dy) < (dy < 0 ? m[ix + 0x10] : m[iy + 0x10])) r = k;
          }
        }
        m[hl + 7 - k] = r;
      }
      hl += 6;
    }
  }
  function coupsDePierre(m) {                                      // &5CD7
    if (!actif(m, 1)) return;
    let k = 0xFF;
    for (let i = 0; i < 6; i++) if (m[CONTACTS + 6 + i] !== 0xFF) { k = m[CONTACTS + 6 + i]; break; }
    if (k === 0xFF || (m[o(1) + 0xA] & 0x7F) === 0x2D) return;
    const b = o(k);
    if (m[b + 0x12]) return;
    const pr = prop(m, m[b + 0xA] & 0x7F);
    if (m[pr] & 0x80) { arreterPierre(m); return; }
    const pierre = (m[o(1) + 0xA] & 0x7F) === 0x2C;
    const reste = m[COUPS + k - 2] - (pierre ? 1 : 2);
    m[COUPS + k - 2] = reste & 0xFF;
    if (reste > 0) { arreterPierre(m); return; }
    tuer(m, k);
    ecrireMot(m, SCORE, mot(m, SCORE) + (pierre ? m[pr + 2] : m[pr + 2] >> 1));
    arreterPierre(m);
  }
  function degats(m, k) {                                          // &5B19, poignée 5
    const b = o(k);
    if (m[b + 0x12] || !actif(m, 0) || m[0xB412]) return;
    const s = m[b + 0xA] & 0x7F, accroupi = [0x05, 0x0E, 0x04, 0x0D];
    let a = s;
    if (s === 0x2F) { a = m[0xB40A] & 0x7F; if (accroupi.includes(a)) return; }
    if (a === 0x33 && m[0xB404] >= 0x78) { a = m[0xB40A] & 0x7F; if (accroupi.includes(a)) return; }
    if (m[REPIT] && s !== 0x3B) return;
    if ([0x3B, 0x3C, 0x31, 0x30].includes(s)) m[REPIT] = 8;
    const pr = prop(m, s);
    let d = m[pr + 1] & 0x1F, cible;
    if (m[A_PIED]) cible = VIE_TAL;
    else { cible = ENERGIE_ARMURE; d = (d >> 1) || 1; if (m[NEGATEUR] === 0) d = (d >> 1) || 1; }
    const v = (m[cible] - d) & 0xFF;
    m[cible] = v >= 0x80 ? 0 : v;
    if (m[pr] & 0x80) return;
    ecrireMot(m, SCORE, mot(m, SCORE) + (m[A_PIED] ? m[pr + 2] : m[pr + 2] >> 1));
    tuer(m, k);
    m[COUPS + k - 2] = 0;
  }
  function barriere(m) { if (m[A_PIED] === 0) { m[0xB407] ^= 0x0C; m[0xB520] ^= 0x03; } }   // &5BFF, &68A3
  function contactsTal(m, hors) {                                  // &59B5
    for (let i = 5; i >= 0; i--) {
      const k = m[CONTACTS + i];
      if (k === 0xFF) continue;
      const f = m[prop(m, m[o(k) + 0xA] & 0x7F)];
      if (!(f & 0x20)) continue;
      const p = f & 0x1F;
      if (p === 5) degats(m, k);
      else if (p === 8) barriere(m);
      else if (p === 9) minePosee(m);
      else if (hors) hors.push([p, k]);
    }
  }


  // ---- le panneau de l'armure (mode 1, lignes d'écran 136 à 199), écrit dans la mémoire d'écran comme le jeu
  function ligneSuivante(a) { a += 0x800; if ((a & 0x3800) === 0) a = a - 0x4000 + 0x50; return a & 0xFFFF; }
  function texte(m, rangee, col, adr) {                            // &6FBE, &701E
    for (;;) {
      const c = m[adr];
      if (c === 0x24) return;
      if (c === 0x0D) { rangee++; adr++; continue; }
      if (c >= 0x80) { m[0xB499] = m[0x8BEF + (c & 0x7F)]; adr++; continue; }
      let g;
      if (c >= 0x30 && c < 0x3A) g = c - 0x0E;
      else if (c >= 0x41 && c < 0x5B) g = c - 0x40;
      else { g = c; for (let i = 0; i < 19; i++) if (m[0x8B3D + i] === c) { g = m[0x8B50 + i]; break; } }
      let src = 0x0400 + 16 * g, e = (mot(m, 0x8BBD + 2 * rangee) + ((2 * col) & 0xFF)) & 0xFFFF;
      for (let k = 0; k < 8; k++) {
        m[e] = m[src] & m[0xB499]; m[(e + 1) & 0xFFFF] = m[src + 1] & m[0xB499];
        src += 2; e = (e + 0x800) & 0xFFFF;
      }
      adr++; col++;
    }
  }
  function scoreTexte(m) {                                         // &56A8
    let v = mot(m, SCORE_AFFICHE);
    [10000, 1000, 100, 10].forEach((d, i) => { m[0x8B82 + i] = (0x30 + Math.floor(v / d)) & 0xFF; v %= d; });
    m[0x8B86] = 0x30 + v;
    texte(m, 0x14, 0x0A, 0x8B81);
  }
  function jauge(m, adr, v) {                                      // &5DFC
    let c = m[v], b;
    const cible = m[v + 1];
    if (cible === c) return;
    if (cible < c) { c--; b = 0xFF; } else { c++; b = 1; }
    m[v] = c;
    adr += (c & 0x1C) >> 2;
    const motif = m[0x8EBE + (c & 3)];
    let d = 0xF0;
    if ((c & 0x1C) === 0x1C) b = 1;
    if ((c & 0x1C) >= 0x10) d = 0xFF;
    const val = motif & d;
    for (let k = 0; k < 4; k++) { m[adr] = val; if (b === 0xFF) m[adr + 1] = 0; adr = (adr + 0x800) & 0xFFFF; }
  }
  function bruit(m) {                                              // &5E56
    if (m[0xB531]) return;
    let hl = mot(m, 0xB4F7);
    for (const [n, de0] of [[3, 0xEE14], [8, 0xC664], [8, 0xC6B4], [4, 0xC704]]) {
      let de = de0;
      for (let r = 0; r < n; r++) {
        for (let k = 0; k < 10; k++) m[de + k] = m[(hl + k) & 0xFFFF];
        hl = (hl + 10) & 0xFFFF; de = (de + 0x800) & 0xFFFF;
      }
    }
    ecrireMot(m, 0xB4F7, hl);
  }
  function imagePiece(m, n) {                                      // &5F83, &5F99, &5FC8
    if (n < 8 || n >= 0x0C) return;
    let a = 0xEE14;
    for (let r = 0; r < 0x17; r++) { for (let k = 0; k < 10; k++) m[a + k] = 0; a = ligneSuivante(a); }
    let src = 0x21D8 + (n - 8) * 0x60, de = 0xC666;
    for (let r = 0; r < 16; r++) { for (let k = 0; k < 6; k++) m[de + k] = m[src + k]; src += 6; de = ligneSuivante(de); }
    m[0xB531] = 0xFF;
  }
  function lettre(m, hl) {                                         // &5F6B
    const c = m[hl], a = c === 0x20 ? 0 : (c - 0x40) & 0xFF;
    ecrireMot(m, 0xB52B, hl); ecrireMot(m, 0xB52D, 0x0400 + 16 * a);
  }
  function message(m, n) {                                         // &5EA0
    if ((m[A_PIED] & 1) && n >= 8 && n < 0x0C) {
      for (let i = 0; i < 4; i++) if (m[0xB53D + i] === 0xFF) { m[0xB53D + i] = n; break; }
      return;
    }
    let autre = false;
    for (let i = 0; i < 8; i++) { const v = m[0xB521 + i]; if (v === n) return; if (v !== 0xFF) autre = true; }
    const b = m[0xB52A];
    m[0xB521 + b] = n; m[0xB52A] = (b + 1) & 7;
    if (autre) return;
    m[0xB530] = 0; m[0xB529] = b;
    imagePiece(m, n);
    lettre(m, mot(m, 0xA093 + 2 * n));
  }
  function sonCoupe(m) {
    const p = mot(m, 0x8AEF);
    m[0x7A5B] = m[0x7A5D] = p & 0xFF; m[0x7A5C] = m[0x7A5E] = p >> 8;
    for (let k = 0; k < 0x2A; k++) m[0x7A5F + k] = 0;
  }
  function messageSuivant(m) {                                     // &5FFC
    m[0xB531] = 0;
    const i = 0xB521 + m[0xB529];
    if (m[i]) { m[i] = 0; return mot(m, 0xA093); }
    m[i] = 0xFF;
    m[0xB529] = (m[0xB529] + 1) & 7;
    const n = m[0xB521 + m[0xB529]];
    if (n === 0xFF) { m[0xB530] = 0xFF; sonCoupe(m); return 0x7A5B; }
    imagePiece(m, n);
    const hl = mot(m, 0xA093 + 2 * n);
    ecrireMot(m, 0xB52B, hl); m[0xB530] = 0;
    return hl;
  }
  function defilement(m) {                                         // &5F12, &5F55
    if (m[JEU_LANCE] || m[0xB530]) return false;
    let ix = mot(m, 0xB52D) + (m[0xB52F] ? 1 : 0), hl = 0xC74F;
    for (let r = 0; r < 8; r++) {
      for (let k = 0; k < 0x15; k++) m[hl - 1 + k] = m[hl + k];
      m[hl + 0x14] = m[ix & 0xFFFF];
      hl = (hl + 0x800) & 0xFFFF; ix += 2;
    }
    m[0xB52F] ^= 1;
    if (m[0xB52F]) return false;
    let p = (mot(m, 0xB52B) + 1) & 0xFFFF;
    if (m[p] === 0x79) return true;
    if (m[p] === 0x24) p = messageSuivant(m);
    lettre(m, p);
    return false;
  }
  function rayonnement(m, force) {                                 // &72C5, &72CA
    if (m[JEU_LANCE] && !force) return;
    const r = m[SALLE];
    let b = 6;
    for (let i = 0; i < 6; i++) { if (r < m[0x8B37 + i]) break; b--; }
    m[0xB538] = b;
    texte(m, 0x17, 0x1B, b >= 5 ? 0x8B68 : 0x8B97);
    let q = 0x8B9A;
    for (let k = 0; k <= b; k++) { texte(m, m[q], m[q + 1], q + 2); q += 5; }
    texte(m, 0x15, 0x1C, 0x8B94);
  }
  function paletteArmure(m, dedans) { const s = dedans ? 0x8E06 : 0x8E03; for (let k = 0; k < 3; k++) m[0x8E00 + k] = m[s + k]; }
  function toutesLesDeuxSecondes(m) {                              // &6F18
    if (m[A_PIED] === 0) {
      if (m[VIE_TAL] !== 0x1F) m[VIE_TAL]++;
      if (m[SALLE] < 2) { const e = m[ENERGIE_ARMURE]; if (e < 2) m[ENERGIE_ARMURE] = 0; else if (e > 2) m[ENERGIE_ARMURE] = e - 2; }
    } else {
      const r = m[0xB538];
      if (r >= 2 && r < 5) { const v = (m[VIE_TAL] - (r >> 1)) & 0xFF; m[VIE_TAL] = v >= 0x80 ? 0 : v; }
    }
  }
  function panneauTour(m) {                                        // &5DDA
    if (m[JEU_LANCE]) return false;
    jauge(m, 0xD69A, 0xB4FA); jauge(m, 0xD5FA, 0xB4FC); bruit(m);
    return defilement(m);
  }
  function tirPulsar(m) {                                          // &64EF
    const feu = m[0x7A4C] & 0x10, e = m[0xB40A] & 0x7F;
    if (m[0xB51A]) return feu && (e === 0x19 || e === 0x1B) ? 0x0E : null;
    if (!feu) return null;
    let script, etat, x;
    if (e === 0x19) { script = 4; etat = 0x34; x = m[0xB403] - 6; }
    else if (e === 0x1B) { script = 3; etat = 0x32; x = m[0xB403] + 6; }
    else return null;
    if (actif(m, 1)) return null;
    creer(m, 1, x & 0xFF, (m[0xB404] + 0x0E) & 0xFF, script, etat);
    m[0x98AA] = m[0x98BB] = m[0xB407]; m[0x98AC] = m[0x98BD] = m[0xB408]; m[0x98AD] = m[0x98BE] = m[0xB409];
    return null;
  }
  function minePosee(m) {                                          // &5C0E, poignée 9
    if (m[0xB51B] || (m[0xB40A] & 0x7F) !== 0x16 || !(m[0xB407] & 2)) return false;
    poserEtat(m, 0, 0x17); message(m, 0x13); m[ACTIFS] = 0;
    return true;
  }
  function hasard(m) {                                             // &6584
    let hl = mot(m, 0xB4EF);
    hl = (hl * 3) & 0xFFFF;
    const bc0 = hl;
    hl = (hl * 2) & 0xFFFF;
    const a = hl & 0xFF;
    hl = (hl * 4 + bc0) & 0xFFFF;
    hl = (((a << 8) | 0x29) - hl) & 0xFFFF;
    ecrireMot(m, 0xB4EF, hl);
    return hl;
  }
  function implosion(m) {                                          // &5C31
    m[ACTIFS] = 0;
    const effaces = [];
    for (let k = 0; k < 0x4000; k++) { let a = hasard(m); if (((a >> 8) & 7) < 5) { a |= 0xC000; m[a] = 0; effaces.push(a); } }
    creer(m, 4, 0x26, 0x68, 0x2D, 0x3F);
    m[0xB529] = m[0xB52A] = m[0xB52F] = 0; m[0xB530] = 0xFF;
    for (let a = 0xB521; a < 0xB529; a++) m[a] = 0xFF;
    return effaces;
  }
  function boucleFinale(m) { fondus(m); animateur(m); panneauTour(m); message(m, 0x14); }   // &5CA6

  function creerListe(m, entree, n, nb) {                          // &7192
    const p = mot(m, 0xB549);
    for (let i = 0; i < nb; i++) {
      const q = p + 4 * (entree + i), etat = m[q + 3];
      creer(m, n, m[q], m[q + 1], m[q + 2], etat);
      m[COUPS + n - 2] = m[prop(m, etat) + 1] >> 5;
      if (etat === 0x29) { m[CHRONO_GENERATEUR] = 0x28; return null; }
      n++;
    }
    m[PROCHAIN] = n;
    return n;
  }
  function entrerSalle(m) {                                        // &723A, &7160, &71CD, &7202, &7113
    m[ACTIFS] = 0;
    const r = m[SALLE];
    if (m[A_PIED] && r === m[0xB4F4]) creer(m, 7, m[0xB4F6], m[0xB4F5], 0, 0x36);
    m[CHRONO_GENERATEUR] = 0xFF;
    const p = mot(m, 0x9BC7 + 2 * r);
    ecrireMot(m, 0xB549, p + 1);
    creerListe(m, 0, 2, m[p]);
    for (let i = 0; i < 4; i++) {
      const q = 0x8F14 + 3 * i;
      if (m[0xB519 + i] && m[q] === r) { creer(m, 6, m[q + 1], m[q + 2], 0, 0x1D + i); break; }
    }
    for (let i = 0; i < 15; i++) {
      const q = 0xA066 + 3 * i;
      if (m[q] === r) { creer(m, m[ACTIFS] & 0x40 ? 7 : 6, m[q + 1], m[q + 2], 0, 0x1C); ecrireMot(m, 0xB539, q); break; }
    }
    for (const rg of [0x13, 0x14, 0x15]) texte(m, rg, 0x1B, 0x8B8F);   // &7319
    rayonnement(m);
    if (r < 2 && m[NEGATEUR]) { m[VIE_TAL] = 0; message(m, 0x12); }
    m[ACTIFS] |= 1;
  }
  function minuteries(m) {                                         // &6217
    if (m[REPIT]) m[REPIT]--;
    m[0xB4F9] = (m[0xB4F9] + 1) & 0xFF;
    if (m[0xB517]) m[0xB517]--;
    if (m[COUPS] === 0 || m[COUPS] >= 0x80) return;
    const c = m[CHRONO_GENERATEUR];
    if (c === 0xFF) return;
    if (c) { m[CHRONO_GENERATEUR] = c - 1; return; }
    if ((m[o(2) + 0xA] & 0x7F) !== 0x29) return;
    if (actif(m, 2)) { tuer(m, 2); return; }
    creerListe(m, 1, 2, m[mot(m, 0xB549) - 1] - 1);
    m[CHRONO_GENERATEUR] = 0xFF;
  }
  function activation(m) {                                         // &604F
    if (m[0xB513]) return null;
    let hl = mot(m, 0xB515), a = (m[0xB514] - 1) & 0xFF;
    if (a === 0) { a = 7; hl++; }
    ecrireMot(m, 0xB515, hl); m[0xB514] = a;
    const v = m[hl];
    if (v === 0) { m[0xB513] = 0xFF; m[JEU_LANCE] = 0; message(m, 0x11); return null; }
    const bit = ((v << a) >> 8) & 1, s = bit ? 0x8E0C : 0x8E0F;   // &61E9, &61F8
    for (let k = 0; k < 3; k++) m[0x8E09 + k] = m[s + k];
    return bit;
  }
  function canon(m) {                                              // &5642
    const p = o(5);
    if ((m[p + 0xA] & 0x7F) === 0x33 && m[p + 3] >= 0x46) { detruire(m, 5); poserEtat(m, 2, 0x2B); }
    if ((m[o(2) + 0xA] & 0x7F) !== 0x2B || actif(m, 5) || m[o(2) + 0xC]) return;
    creer(m, 5, 0x1B, 0x7F, 0x29, 0x32); poserEtat(m, 2, 0x2B);
  }
  function goutte(m) {                                             // &55F5
    const g = o(2);
    if (!actif(m, 2)) {
      if ((m[g + 0xA] & 0x7F) !== 0x3A) return;
      const p = mot(m, 0xB549);
      creer(m, 2, m[p], m[p + 1], m[p + 2], m[p + 3]);
      return;
    }
    if ((m[g + 0xA] & 0x7F) !== 0x39 || m[g + 4] < 0x92) return;
    m[g + 4] = 0x95; poserEtat(m, 2, 0x3A); m[g] = 0; m[g + 7] = 0;
  }
  function volatile(m) {                                           // &5598
    const n = m[PROCHAIN], b = o(n);
    if ((m[b + 0xA] & 0x7F) === 0x2E && m[b + 4] >= 0xA0) detruire(m, n);
    if (!actif(m, 2) || (m[o(2) + 0xA] & 0x7F) !== 0x27) return;
    if (((m[ACTIFS] >> n) & 1) || m[o(2) + 0x12]) return;
    creer(m, n, (m[o(2) + 3] + 5) & 0xFF, (m[o(2) + 4] + 0x15) & 0xFF, 0x23, 0x2E);
  }
  function finDeTour(m, hors) {                                    // de &5704 au retour en &54FA
    fondus(m);
    if ((m[0xB40A] & 0x7F) === 0x17) m[0xB407] = 0;
    animateur(m);
    lancerPierre(m);
    if (panneauTour(m)) return 'fin';                              // &5DDA
    collisions(m); coupsDePierre(m); contactsTal(m, hors); pierreSortie(m); minuteries(m);
    const bit = activation(m);
    if (!m[JEU_LANCE] && mot(m, SCORE_AFFICHE) < mot(m, SCORE)) { ecrireMot(m, SCORE_AFFICHE, mot(m, SCORE_AFFICHE) + 1); scoreTexte(m); }
    canon(m); goutte(m); volatile(m);
    return bit;
  }
  function mortDeTal(m) {                                          // &579C, &57D7
    const t = o(0);
    let r = null;
    if (m[VIE_TAL] === 0 && ![0x10, 0x07, 0x08, 0x11].includes(m[t + 0xA] & 0x7F) && m[t] === 0) {
      m[t + 4] = (m[t + 4] + 6) & 0xFF; poserEtat(m, 0, 0x14);
      m[t] = 0x2A; m[t + 1] = 0; m[t + 2] = 0; m[0xB551] >>= 1; r = 'mort';
    }
    if (m[t + 0xA] === 0x94) {
      if (m[0xB551] & 1) return 'fin';
      m[0xB550] = (m[0xB550] + 1) & 0xFF; m[VIE_TAL] = 0x1F;
      m[t + 4] = (m[t + 4] - 0x0B) & 0xFF; poserEtat(m, 0, 0x15);
      m[t] = 0x2B; m[t + 1] = 0; m[t + 2] = 0; r = 'renaissance';
    }
    return r;
  }

  const api = {o, TAILLE, OBJ, ACTIFS, VIE_TAL, ENERGIE_ARMURE, A_PIED, SALLE, SCORE, SCORE_AFFICHE, COUPS, REPIT, JEU_LANCE,
    NEGATEUR, CONTACTS, prop, actif, creer, poserEtat, detruire, tuer, animer, entrerSalle, finDeTour, mortDeTal, mot, ecrireMot,
    texte, message, rayonnement, paletteArmure, toutesLesDeuxSecondes, panneauTour, tirPulsar, implosion, boucleFinale, scoreTexte};
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else racine.Monde = api;
})(this);
