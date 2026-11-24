"""Banc de vérification : le modèle armure.py contre le vrai code, dans l'émulateur cpcarch.emu.

On fait entrer Tal dans l'armure par la routine du jeu (&60D3), appelée depuis la boucle principale
avec retour en &54FA, après avoir posé les drapeaux des pièces et l'énergie voulus. Ensuite, comme
pour verif.py : image de la mémoire à l'entrée de &5744, fiche relevée à la sortie de l'animateur
(&551A), comparaison pas à pas et en continu.
Usage : python3 verif_armure.py [scénario ...] [-v]
"""
import sys, os
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from cpcarch.emu import CPC, KEY, FRAME
import tal as M
import armure as A

CHAMPS = ['x', 'y', 'dirs', 'vx', 'vy', 'etat', 'pas', 'attente', 'sprite', 'demi_largeur', 'hauteur', 'mur',
          'gaz', 'glisse', 'entree', 'sens_prec', 'en_vol', 'phase', 'cellule']
BIN = os.path.join(ICI, '..', 'build', 'antiriad_5400.bin')


def lire(mem):
    o = 0xB400
    return A.TalArmure(x=mem[o + 3], y=mem[o + 4], dirs=mem[o + 7], vx=mem[o + 8], vy=mem[o + 9], etat=mem[o + 0xA],
                       pas=mem[o + 0xB], attente=mem[o + 0xC], sprite=mem[o + 0xD], demi_largeur=mem[o + 0xF],
                       hauteur=mem[o + 0x10], saut=mem[0xB498], mur=mem[0xB554], gaz=mem[0xB51D], glisse=mem[0xB51E],
                       entree=mem[0xB51F], sens_prec=mem[0xB520], en_vol=mem[0xB500], phase=mem[0xB4F3],
                       energie=mem[0xB4FD], cellule=mem[0xB518], deplaceur=mem[0xB519])


def ecarts(a, b):
    return {k: (getattr(a, k), getattr(b, k)) for k in CHAMPS if getattr(a, k) != getattr(b, k)}


def en_armure(pieces=(0, 0, 0xFF, 0xFF), energie=0x1F, cellule=0xFF):
    c = CPC(open(BIN, 'rb').read(), 0x5400, 0xBFF0)
    c.run(500_000); c.keys = {KEY['fire']}; c.run(500_000); c.keys = set(); c.run(1_000_000)
    mem, R = c.mem, c.R
    while R[24] != 0x54FA:
        c.run(1)
    mem[0xB4F4] = mem[0xB4ED]; mem[0xB4F5] = mem[0xB404] + 1; mem[0xB4F6] = mem[0xB403]
    for i, v in enumerate(pieces):
        mem[0xB519 + i] = v
    mem[0xB4FD] = energie; mem[0xB518] = cellule
    sp = (R[12] - 2) & 0xFFFF; mem[sp] = 0xFA; mem[sp + 1] = 0x54; R[12] = sp; R[24] = 0x60D3
    c.run(1)
    while R[24] != 0x54FA:
        c.run(1)
    return c


H, B, G, D, F = 'joy_up', 'joy_down', 'joy_left', 'joy_right', 'fire'
SCENARIOS = {
    'decollage':  ({}, [((), 10), ((H,), 30), ((), 60), ((B,), 30), ((), 40)]),
    'derive':     ({}, [((H,), 12), ((), 20), ((D,), 40), ((), 30), ((G,), 50), ((), 30)]),
    'murs':       ({}, [((H,), 10), ((), 10), ((D,), 160), ((G,), 200)]),
    'plafond':    ({}, [((H,), 80), ((), 30), ((H, D), 60), ((B,), 40)]),
    'atterrir':   ({}, [((H,), 8), ((), 30), ((B,), 50), ((), 30), ((D,), 6), ((), 20)]),
    'demi_tours': ({}, [((H,), 8)] + [((D,), 4), ((G,), 4)] * 8 + [((), 30)]),
    'sans_energie': ({'energie': 0}, [((), 10), ((H,), 40), ((D,), 30), ((), 20)]),
    'cellule':    ({'cellule': 0}, [((H,), 20), ((), 20)]),
    'inerte':     ({'pieces': (0xFF, 0xFF, 0xFF, 0xFF)}, [((H,), 20), ((D,), 20)]),
}


def jouer(nom, reglage, plan, verbeux=False):
    c = en_armure(**reglage)
    R, mem = c.R, c.mem
    tours, entree = [], None
    for touches, n in plan:
        c.keys = {KEY[k] for k in touches}
        for _ in range(n):
            t = R[25] + FRAME
            while R[25] < t:
                pc = R[24]
                if pc == 0x5744 and mem[0xB4F1] == 0:
                    entree = bytes(mem)
                elif pc == 0x551A and entree is not None:
                    tours.append((entree, lire(mem), mem[0xB4F1]))
                    entree = None
                c.run(1)
    pas_a_pas, continu, hors = [], [], []
    libre = lire(tours[0][0])
    for i, (img, apres, a_pied) in enumerate(tours):
        ecran = M.EcranMemoire(img)
        joy = img[0x7A4C]
        t = lire(img)
        if i and ecarts(t, tours[i - 1][1]):
            hors.append(i)
            libre = lire(img)
        libre.energie, libre.deplaceur = t.energie, t.deplaceur    # énergie : dégâts des ennemis, hors modèle
        if a_pied:                                       # Tal est sorti de l'armure (&6150) : hors modèle
            hors.append('sortie %d' % i)
            break
        A.tour(t, joy, ecran)
        d = ecarts(t, apres)
        if d:
            pas_a_pas.append((i, joy, d))
        A.tour(libre, joy, ecran)
        d = ecarts(libre, apres)
        if d and not continu:
            continu.append((i, joy, d))
        if verbeux:
            print('%3d joy=%02X X=%02X Y=%02X dirs=%X vy=%d état=%02X gaz=%d glisse=%d vol=%02X' %
                  (i, joy, apres.x, apres.y, apres.dirs, apres.vy, apres.etat, apres.gaz, apres.glisse, apres.en_vol))
    etats = sorted({a.e for _, a, p in tours if not p})
    print('%-13s %4d tours, états %s : pas à pas %d écart(s), en continu %s%s' % (
        nom, len(tours), ' '.join('%02X' % e for e in etats), len(pas_a_pas),
        'identique' if not continu else 'diverge au tour %d' % continu[0][0],
        ' [hors modèle : %s]' % ', '.join(map(str, hors)) if hors else ''))
    for i, joy, d in pas_a_pas[:4]:
        print('   tour %d joy=%02X : %s' % (i, joy, d))
    if continu:
        print('   continu, tour %d joy=%02X : %s' % continu[0])
    return not pas_a_pas and not continu


if __name__ == '__main__':
    noms = [a for a in sys.argv[1:] if not a.startswith('-')] or list(SCENARIOS)
    ok = all([jouer(n, *SCENARIOS[n], verbeux='-v' in sys.argv) for n in noms])
    print('TOUT CONCORDE' if ok else 'DES ÉCARTS RESTENT')
