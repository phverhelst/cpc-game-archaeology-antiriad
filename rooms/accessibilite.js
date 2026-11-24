// Exploration exhaustive des positions que Tal à pied peut atteindre, avec le modèle vérifié (sandbox/tal.js).
// Usage : node accessibilite.js <tables.json> <carre|monde> [diagonale]
const fs = require('fs'), path = require('path');
const {Modele, nouveauTal} = require(path.join(__dirname, '..', 'sandbox', 'tal.js'));
const T = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const MODE = process.argv[3] || 'carre', DIAG = process.argv[4] === 'diagonale';
const m = Modele(T, {sautDiagonal: DIAG});
const BIN = fs.readFileSync(path.join(__dirname, 'salles.bin'));
const INFO = JSON.parse(fs.readFileSync(path.join(__dirname, 'salles.json'), 'utf8')).salles;
const CARRE = new Set([0x40, 0x3F, 0x32, 0x31]);
const ecrans = {};
const ecran = r => ecrans[r] || (ecrans[r] = {octet: (l, c) => (l >= 0x32 && l < 0xBA && c >= 0 && c < 80) ? BIN[r * 10880 + (l - 0x32) * 80 + c] : 0});
const H = 1, B = 2, G = 4, D = 8, F = 16;
const ENTREES = [0, G, D, H, B, F, G | F, D | F, H | G | F, H | D | F, H | G, H | D];
const CH = ['x', 'y', 'dirs', 'vx', 'vy', 'etat', 'pas', 'attente', 'sprite', 'demi_largeur', 'hauteur', 'saut', 'mur'];
const cle = (r, t) => r + ',' + CH.map(k => t[k]).join(',');
const ARM = {r: 0x3F, x: 0x18, y: 0x40, dl: 3, h: 41};
function touche(r, t) {
  if (r !== ARM.r || (t.etat & 0x7F) !== 1) return false;        // de face (état 01) : condition d'entrée &6094
  const lx = 2 * (t.x >= ARM.x ? ARM.dl : t.demi_largeur), ly = t.y >= ARM.y ? ARM.h : t.hauteur;
  return Math.abs(t.x - ARM.x) < lx && Math.abs(t.y - ARM.y) < ly;
}
function salleSuivante(r, t, avant) {                           // &69A7
  const L = INFO[r.toString(16).toUpperCase().padStart(2, '0')].liens;
  let cote = null, pos;
  if (t.x < 5) { cote = 'gauche'; pos = () => { t.x = 0x44; }; }
  else if (t.x >= 0x45) { cote = 'droite'; pos = () => { t.x = 6; }; }
  else if (t.y < 0x19) { cote = 'haut'; pos = () => { t.y = 0x99; }; }
  else if (t.y >= 0x9B) { cote = 'bas'; pos = () => { t.y = 0x1B; }; }
  if (!cote) return r;
  const c = L[cote];
  if (MODE === 'carre') {
    if (c !== 255 && CARRE.has(c)) { pos(); return c; }
    t.x = avant.x; t.y = avant.y; return r;                      // bord fermé du bac à sable
  }
  pos(); return c === 255 ? r : c;                               // jeu : &FF renvoie dans la même salle
}
// départs : Tal debout au sol, au milieu de chaque salle concernée
const departs = [];
const DEP = process.argv.find(a => a.startsWith('depart='));
// option « complet » : explore tout, sans s'arrêter à l'armure, et liste les salles atteintes
const salles = DEP ? [parseInt(DEP.slice(7), 16)] : MODE === 'carre' ? [...CARRE] : Object.keys(INFO).map(s => parseInt(s, 16));
for (const r of salles) for (const x of (DEP ? [0x24] : [0x0C, 0x24, 0x3C])) departs.push([r, nouveauTal({x, y: 0x40, etat: 0x08, sprite: 0x08})]);
const vus = new Map(), file = [];
for (const [r, t] of departs) { const k = cle(r, t); vus.set(k, null); file.push([r, t, k]); }
let trouve = null, i = 0, armureAtteinte = null;
const COMPLET = process.argv.includes('complet');
const sallesVues = new Set();
while (i < file.length && !trouve) {
  const [r, t, k] = file[i++];
  for (const j of ENTREES) {
    const u = {...t}, avant = {x: t.x, y: t.y};
    m.tour(u, j, ecran(r));
    const r2 = salleSuivante(r, u, avant);
    const k2 = cle(r2, u);
    if (vus.has(k2)) continue;
    vus.set(k2, [k, j]); file.push([r2, u, k2]); sallesVues.add(r2);
    if (touche(r2, u) && !COMPLET) { trouve = k2; break; }
    if (touche(r2, u)) armureAtteinte = armureAtteinte || u;
  }
  if (vus.size > 8e6) { console.log('arrêt : plafond de 8 millions d\'états'); break; }
}
console.log(`mode ${MODE}${DIAG ? ' + saut diagonal' : ''}${DEP ? ' depuis le sol de ' + DEP.slice(7) : ''} : ${vus.size} états explorés, salles visitées ${[...sallesVues].map(r => r.toString(16)).sort().join(' ')}`);
if (COMPLET) { const tous = new Set(Object.keys(INFO).map(s => parseInt(s, 16))); const non = [...tous].filter(r => !sallesVues.has(r)).map(r => r.toString(16).toUpperCase().padStart(2, '0'));
  console.log(`armure ${armureAtteinte ? 'atteignable' : 'non atteignable'} ; salles jamais atteintes à pied (${non.length}) : ${non.join(' ')}`); process.exit(0); }
if (!trouve) { console.log('armure NON atteinte'); process.exit(0); }
const chemin = []; let k = trouve;
while (vus.get(k)) { const [p, j] = vus.get(k); chemin.push([k, j]); k = p; }
chemin.reverse();
const nom = j => j === 0 ? '·' : [[H, '↑'], [B, '↓'], [G, '←'], [D, '→'], [F, 'F']].filter(([b]) => j & b).map(([, s]) => s).join('');
console.log(`armure atteinte en ${chemin.length} tours, depuis la salle ${k.split(',')[0] | 0 ? (+k.split(',')[0]).toString(16) : '?'}`);
let prec = null, n = 0, txt = [];
for (const [kk, j] of chemin) { const s = nom(j); if (s === prec) n++; else { if (prec !== null) txt.push(prec + '×' + n); prec = s; n = 1; } }
txt.push(prec + '×' + n); console.log(txt.join(' '));
const etapes = chemin.filter((_, q) => q % 8 === 0 || q === chemin.length - 1).map(([kk]) => { const v = kk.split(','); return `${(+v[0]).toString(16)}:${(+v[1]).toString(16)},${(+v[2]).toString(16)}`; });
console.log('salle:x,y tous les 8 tours :', etapes.join(' '));
