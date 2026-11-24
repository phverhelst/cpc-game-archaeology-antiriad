"""Vérifie que tal.js (bac à sable) reproduit exactement movement/tal.py, tour par tour.

Des suites d'entrées aléatoires (touches tenues pendant une durée aléatoire) sont jouées par les deux
modèles dans la salle d'essai ; l'état complet de Tal est comparé à chaque tour.
Usage : python3 verif_js.py [nombre_de_parties] [tours_par_partie]
"""
import json, os, random, subprocess, sys, dataclasses
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'movement'))
import tal as M
from tables import TABLES
import salle

CHAMPS = [f.name for f in dataclasses.fields(M.Tal)]
TOUCHES = [0, M.HAUT, M.HAUT | M.GAUCHE, M.HAUT | M.DROITE, M.BAS, M.GAUCHE, M.DROITE, M.FEU, M.GAUCHE | M.FEU, M.DROITE | M.FEU,
           M.HAUT | M.GAUCHE | M.FEU, M.HAUT | M.DROITE | M.FEU, M.BAS | M.FEU, M.HAUT | M.GAUCHE, M.BAS | M.DROITE]


def tables_js():
    return {'vitesses': TABLES.vitesses, 'classes': TABLES.classes,
            'transitions': {e: [s, m] for e, (s, m) in TABLES.transitions.items()},
            'animations': {e: {'delai': a.delai, 'code': a.code} for e, a in TABLES.animations.items()},
            'sprites': {s: list(v) for s, v in TABLES.sprites.items()},
            'etats_mur': TABLES.etats_mur, 'motif_sol': TABLES.motif_sol}


def depart():
    return M.Tal(x=0x20, y=0xB2 - 0x2A - 1, etat=0x02, sprite=0x08)


def main(parties=200, tours=400, diagonale=False):
    M.OPTIONS['saut_diagonal'] = diagonale
    rnd = random.Random(1986)
    sequences = []
    for _ in range(parties):
        seq = []
        while len(seq) < tours:
            seq += [rnd.choice(TOUCHES)] * rnd.choice([1, 1, 2, 3, 5, 8, 15, 30])
        sequences.append(seq[:tours])
    ecran = salle.EcranSalle()
    attendu = []
    for seq in sequences:
        t, etats = depart(), []
        for joy in seq:
            M.tour(t, joy, ecran)
            etats.append([getattr(t, k) for k in CHAMPS])
        attendu.append(etats)
    js = r'''
const {Modele, nouveauTal} = require(process.argv[process.argv.length - 1]);
const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const m = Modele(d.tables, {sautDiagonal: d.diagonale}), e = d.ecran, ecran = {octet: (l, c) => (l >= 0 && l < 256 && c >= 0 && c < 80) ? e[l][c] : 0};
const out = d.sequences.map(seq => { const t = nouveauTal(d.depart); return seq.map(j => { m.tour(t, j, ecran); return d.champs.map(k => t[k]); }); });
process.stdout.write(JSON.stringify(out));
'''
    d0 = depart()
    donnees = {'diagonale': diagonale, 'tables': tables_js(), 'ecran': ecran.e, 'sequences': sequences, 'champs': CHAMPS,
               'depart': {k: getattr(d0, k) for k in CHAMPS}}
    r = subprocess.run(['node', '-e', js, os.path.join(ICI, 'tal.js')], input=json.dumps(donnees),
                       capture_output=True, text=True, check=True)
    obtenu = json.loads(r.stdout)
    etats_vus = set()
    for p, (a, b) in enumerate(zip(attendu, obtenu)):
        for i, (x, y) in enumerate(zip(a, b)):
            etats_vus.add(x[CHAMPS.index('etat')] & 0x7F)
            if x != y:
                diff = {k: (u, v) for k, u, v in zip(CHAMPS, x, y) if u != v}
                print('ÉCART partie %d tour %d : %s' % (p, i, diff)); return False
    print('tal.js = tal.py%s sur %d parties de %d tours (%d tours), états atteints : %s' % (
        ' (option saut diagonal)' if diagonale else '', parties, tours, parties * tours, ' '.join('%02X' % e for e in sorted(etats_vus))))
    return True


if __name__ == '__main__':
    a = [int(x) for x in sys.argv[1:] if x.isdigit()]
    sys.exit(0 if main(*a, diagonale='--diagonale' in sys.argv) else 1)
