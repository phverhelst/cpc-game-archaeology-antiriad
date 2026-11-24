"""Banc de vérification : le modèle `tal.py` contre le vrai code, exécuté dans l'émulateur cpcarch.emu.

Pour chaque tour où Tal est à pied, on prend une image de la mémoire à l'entrée de &5787 (logique de
Tal à pied), puis on relève la fiche de Tal à la sortie de l'animateur (&551A). Le modèle part de
l'image d'entrée et doit retrouver exactement la fiche de sortie.

Deux comparaisons :
  pas à pas : le modèle repart à chaque tour de l'état réel (localise une divergence) ;
  en continu : le modèle garde son propre état d'un bout à l'autre ; seul l'écran vient de l'émulateur.

Usage : python3 verif.py [scénario ...]   (sans argument : tous les scénarios)
"""
import sys, os
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from cpcarch.emu import CPC, KEY, FRAME
import tal as M

CHAMPS = ['x', 'y', 'dirs', 'vx', 'vy', 'etat', 'pas', 'attente', 'sprite', 'demi_largeur', 'hauteur', 'saut', 'mur']


def lire_tal(mem):
    o = 0xB400
    return M.Tal(x=mem[o + 3], y=mem[o + 4], dirs=mem[o + 7], vx=mem[o + 8], vy=mem[o + 9], etat=mem[o + 0xA],
                 pas=mem[o + 0xB], attente=mem[o + 0xC], sprite=mem[o + 0xD], demi_largeur=mem[o + 0xF],
                 hauteur=mem[o + 0x10], saut=mem[0xB498], mur=mem[0xB554])


def ecarts(a, b):
    return {k: (getattr(a, k), getattr(b, k)) for k in CHAMPS if getattr(a, k) != getattr(b, k)}


# Scénarios : liste de (touches, images). Tous partent de la première salle, Tal sur sa plateforme.
SCENARIOS = {
    'marche':      [(('joy_left',), 4), ((), 10), (('joy_left',), 40), ((), 10), (('joy_right',), 30), ((), 10)],
    'saut_droit':  [(('joy_left',), 4), ((), 10), (('joy_up',), 4), ((), 60), (('joy_right',), 4), ((), 6), (('joy_up',), 60)],
    'saut_course': [(('joy_left',), 16), (('joy_left', 'fire'), 4), (('joy_left',), 50), ((), 30)],
    'saut_arret':  [(('joy_left',), 4), ((), 20), (('joy_up', 'joy_left', 'fire'), 6), ((), 60),
                    (('joy_right',), 4), ((), 10), (('joy_up', 'joy_right', 'fire'), 6), ((), 60)],
    'chute':       [(('joy_right',), 50), ((), 40), (('joy_left',), 80), ((), 20)],
    'coups':       [(('joy_left',), 4), ((), 10), (('fire',), 30), ((), 20), (('joy_down',), 40), ((), 30),
                    (('joy_down', 'fire'), 20), (('joy_up',), 10), (('joy_right',), 4), ((), 10), (('fire',), 30),
                    (('joy_down',), 40), (('joy_right',), 10), ((), 20)],
    'mur':         [(('joy_right',), 120), (('joy_right', 'fire'), 6), (('joy_right',), 60), (('joy_up', 'joy_right', 'fire'), 80)],
    'mur_gauche':  [(('joy_left',), 200), (('joy_left', 'fire'), 6), (('joy_left',), 60), ((), 10), (('joy_up', 'joy_left', 'fire'), 6), ((), 60)],
    'accroupi_d':  [(('joy_right',), 4), ((), 10), (('joy_down',), 40), ((), 10), (('joy_down', 'joy_right'), 10), ((), 30)],
    'demi_tour':   [(('joy_left',), 3), (('joy_right',), 3), (('joy_left',), 3), (('joy_right',), 3), (('joy_up',), 2), (('joy_left',), 30)],
    'plafond':     [(('joy_left',), 4), ((), 6)] + [(('joy_up',), 30), (('joy_left',), 3)] * 6 + [((), 20)],
}

def demarrer():
    mem = open(os.path.join(ICI, '..', 'build', 'antiriad_5400.bin'), 'rb').read()
    c = CPC(mem, 0x5400, 0xBFF0)
    c.run(500_000); c.keys = {KEY['fire']}; c.run(500_000); c.keys = set(); c.run(1_000_000)
    return c


def jouer(nom, plan, verbeux=False):
    c = demarrer()
    R, mem = c.R, c.mem
    tours = []                                   # (image d'entrée, fiche de sortie, joystick)
    entree = None
    for touches, n in plan:
        c.keys = {KEY[k] for k in touches}
        for _ in range(n):
            t = R[25] + FRAME
            while R[25] < t:
                pc = R[24]
                if pc == 0x5787 and mem[0xB4F1] and not mem[0xB400]:
                    entree = bytes(mem)
                elif pc == 0x551A and entree is not None:
                    tours.append((entree, lire_tal(mem), mem[0x7A4C]))
                    entree = None
                c.run(1)
    pas_a_pas, continu, hors = [], [], []
    libre = lire_tal(tours[0][0]) if tours else None
    for i, (img, apres, joy_fin) in enumerate(tours):
        ecran = M.EcranMemoire(img)
        joy = img[0x7A4C]
        t = lire_tal(img)
        if i and ecarts(t, tours[i - 1][1]):     # changé entre deux tours (changement de salle…)
            hors.append((i, 'entre deux tours, %s' % ecarts(tours[i - 1][1], t)))
            libre = lire_tal(img)
        if apres.e in (0x14, 0x15):
            hors.append((i, 'mort'))
            libre = apres                        # hors du modèle : on repart de l'état réel
            continue
        M.tour(t, joy, ecran)
        d = ecarts(t, apres)
        if d:
            pas_a_pas.append((i, joy, joy_fin, d))
        M.tour(libre, joy, ecran)
        d = ecarts(libre, apres)
        if d and not continu:
            continu.append((i, joy, d))
        if verbeux:
            print('%3d joy=%02X X=%02X Y=%02X dirs=%X vy=%d etat=%02X sprite=%02X saut=%d' %
                  (i, joy, apres.x, apres.y, apres.dirs, apres.vy, apres.etat, apres.sprite, apres.saut))
    etats = sorted({a.e for _, a, _ in tours})
    print('%-12s %4d tours, états %s : pas à pas %d écart(s), en continu %s%s' % (
        nom, len(tours), ' '.join('%02X' % e for e in etats), len(pas_a_pas),
        'identique' if not continu else 'diverge au tour %d' % continu[0][0],
        ''.join(' [tour %d : %s, hors modèle]' % h for h in hors)))
    for i, joy, joy_fin, d in pas_a_pas[:5]:
        print('   tour %d joy=%02X (fin %02X) : %s' % (i, joy, joy_fin, d))
    if continu:
        print('   continu, tour %d joy=%02X : %s' % continu[0])
    return not pas_a_pas and not continu


if __name__ == '__main__':
    noms = [a for a in sys.argv[1:] if not a.startswith('-')] or list(SCENARIOS)
    ok = all([jouer(n, SCENARIOS[n], '-v' in sys.argv) for n in noms])
    print('TOUT CONCORDE' if ok else 'DES ÉCARTS RESTENT')
