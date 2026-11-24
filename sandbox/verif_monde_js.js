// Côté JavaScript de verif_monde_js.py : même suite d'opérations que jouer() en Python, empreinte MD5 après chaque tour.
const fs = require('fs'), zlib = require('zlib'), crypto = require('crypto'), path = require('path');
const W = require(path.join(__dirname, 'monde.js'));
const d = JSON.parse(fs.readFileSync(process.argv[2]));
const md5 = m => crypto.createHash('md5').update(m).digest('hex');
const image = b64 => new Uint8Array(zlib.inflateSync(Buffer.from(b64, 'base64')));
const res = {cas: [], salles_ko: 0};
for (const c of d.cas) {
  const m = image(c.image);
  let final = false, ecart = -1;
  for (let t = 0; t < d.tours; t++) {
    m[0x7A4C] = d.joy[(t * 7 + c.sel) % d.joy.length];
    if (final) W.boucleFinale(m);
    else {
      if (m[W.A_PIED] === 0 && m[0xB519] === 0) W.tirPulsar(m);
      else if (m[W.A_PIED]) W.mortDeTal(m);
      if (t % 37 === 5) W.message(m, 1 + (t * 13 + c.sel) % 0x15);
      if (t % 34 === 0) W.toutesLesDeuxSecondes(m);
      if (W.finDeTour(m) === 'fin') { W.implosion(m); final = true; }
    }
    if (md5(m) !== c.attendu[t]) { ecart = t; break; }
  }
  res.cas.push([c.nom, ecart < 0, ecart]);
}
const base = image(d.base);
for (const [r, lance, pieces, h] of d.salles) {
  const m = new Uint8Array(base);
  m[W.SALLE] = r; m[0xB512] = lance; for (let i = 0; i < 4; i++) m[0xB519 + i] = pieces;
  W.entrerSalle(m);
  if (md5(m) !== h) res.salles_ko++;
}
console.log(JSON.stringify(res));
