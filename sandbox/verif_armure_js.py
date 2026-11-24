"""Vérifie que armure.js reproduit movement/armure.py, et tal.js movement/tal.py, dans les vraies salles.

Parties aléatoires dans les salles du carré du bac à sable 2 (&40, &3F, &32, &31), lues dans
rooms/salles.bin. Les deux modèles jouent les mêmes entrées ; l'état complet est comparé à chaque tour.
Usage : python3 verif_armure_js.py [parties] [tours]
"""
import json, os, random, subprocess, sys, dataclasses
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'movement'))
import tal as M, armure as A
from verif_js import tables_js

SALLES = [0x40, 0x3F, 0x32, 0x31]
BIN = open(os.path.join(ICI, '..', 'rooms', 'salles.bin'), 'rb').read()
TOUCHES = [0, M.HAUT, M.BAS, M.GAUCHE, M.DROITE, M.FEU, M.HAUT | M.DROITE, M.HAUT | M.GAUCHE, M.BAS | M.DROITE,
           M.BAS | M.GAUCHE, M.GAUCHE | M.FEU, M.DROITE | M.FEU, M.HAUT | M.GAUCHE | M.FEU]


def ecran_salle(r):
    base = r * 136 * 80
    lignes = [list(BIN[base + i * 80:base + (i + 1) * 80]) for i in range(136)]

    class E:
        def octet(self, l, c):
            return lignes[l - 0x32][c] if 0x32 <= l < 0xBA and 0 <= c < 80 else 0
    return E(), lignes


def main(parties=160, tours=300):
    rnd = random.Random(1986)
    cas = []
    for p in range(parties):
        armure = p % 4 != 3
        salle = SALLES[p % 4]
        seq = []
        while len(seq) < tours:
            seq += [rnd.choice(TOUCHES)] * rnd.choice([1, 2, 3, 5, 8, 13, 21, 40])
        x, y = rnd.randrange(4, 0x44), rnd.randrange(0x34, 0x80)
        reg = {'energie': rnd.choice([0x1F, 0x1F, 0x1F, 5, 0]), 'cellule': rnd.choice([0xFF, 0xFF, 0]),
               'deplaceur': rnd.choice([0, 0, 0, 0xFF])} if armure else {}
        cas.append({'armure': armure, 'salle': salle, 'seq': seq[:tours], 'x': x, 'y': y, 'reg': reg})
    attendu, champs = [], None
    for k in cas:
        e, _ = ecran_salle(k['salle'])
        if k['armure']:
            t = A.TalArmure(x=k['x'], y=k['y'], etat=0x17, sprite=0x17, dirs=0, **k['reg'])
            f = A.tour
        else:
            t = M.Tal(x=k['x'], y=k['y'], etat=0x02, sprite=0x08)
            f = M.tour
        k['depart'] = dataclasses.asdict(t)
        champs = [f.name for f in dataclasses.fields(A.TalArmure)]
        etats = []
        for joy in k['seq']:
            f(t, joy, e)
            etats.append([getattr(t, c, None) for c in champs])
        attendu.append(etats)
    js = r'''
const {Modele, nouveauTal} = require(process.argv[process.argv.length - 2]);
const {ModeleArmure} = require(process.argv[process.argv.length - 1]);
const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const mp = Modele(d.tables), ma = ModeleArmure(d.tables, d.gaz);
const out = d.cas.map(k => {
  const L = d.salles[k.salle];
  const ecran = {octet: (l, c) => (l >= 0x32 && l < 0xBA && c >= 0 && c < 80) ? L[l - 0x32][c] : 0};
  const t = Object.assign({}, k.depart);
  const f = k.armure ? ma.tour : mp.tour;
  return k.seq.map(j => { f(t, j, ecran); return d.champs.map(c => (c in t) ? t[c] : null); });
});
process.stdout.write(JSON.stringify(out));
'''
    donnees = {'tables': tables_js(), 'gaz': [list(g) for g in A.GAZ], 'cas': cas, 'champs': champs,
               'salles': {r: ecran_salle(r)[1] for r in SALLES}}
    for k in cas:
        if not k['armure']:   # Tal à pied : pas de champs d'armure
            k['depart'] = {c: v for c, v in k['depart'].items()}
    r = subprocess.run(['node', '-e', js, os.path.join(ICI, 'tal.js'), os.path.join(ICI, 'armure.js')],
                       input=json.dumps(donnees), capture_output=True, text=True)
    if r.returncode:
        print(r.stderr); return False
    obtenu = json.loads(r.stdout)
    vus = set()
    for p, (a, b) in enumerate(zip(attendu, obtenu)):
        for i, (x, y) in enumerate(zip(a, b)):
            vus.add((cas[p]['armure'], x[champs.index('etat')] & 0x7F))
            if x != y:
                diff = {c: (u, v) for c, u, v in zip(champs, x, y) if u != v}
                print('ÉCART partie %d (%s, salle %02X) tour %d : %s' % (p, 'armure' if cas[p]['armure'] else 'à pied', cas[p]['salle'], i, diff))
                return False
    print('armure.js = armure.py et tal.js = tal.py : %d parties de %d tours dans les salles %s ; états armure %s ; à pied %s' % (
        parties, tours, ' '.join('%02X' % s for s in SALLES),
        ' '.join('%02X' % e for a, e in sorted(vus) if a), ' '.join('%02X' % e for a, e in sorted(vus) if not a)))
    return True


if __name__ == '__main__':
    a = [int(x) for x in sys.argv[1:3]]
    sys.exit(0 if main(*a) else 1)
