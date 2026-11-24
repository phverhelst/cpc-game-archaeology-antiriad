"""Traces du vrai jeu pour vérifier le modèle des objets (monde.py), dans l'émulateur cpcarch.emu.

On démarre une partie, puis on fait entrer Tal dans la salle voulue par les routines du jeu : destruction
des huit objets (&6A1F), dessin de la salle et création de ses objets (&7051), réactivation de Tal (&6A2A).
On relève ensuite, à chaque tour de la boucle principale, une image de la mémoire en &5704 (juste après la
logique propre de Tal) et une autre au retour en &54FA (début du tour suivant). Le modèle doit passer de
la première à la seconde.
"""
import os, sys, time
ICI = os.path.dirname(os.path.abspath(__file__))
from cpcarch.emu import CPC, KEY, FRAME

BIN = os.path.join(ICI, '..', 'build', 'antiriad_5400.bin')
_DEPART = None


def depart():
    """Une partie lancée, arrêtée au début de la boucle principale (&54FA)."""
    global _DEPART
    if _DEPART is None:
        c = CPC(open(BIN, 'rb').read(), 0x5400, 0xBFF0)
        c.run(500_000); c.keys = {KEY['fire']}; c.run(500_000); c.keys = set(); c.run(1_000_000)
        while c.R[24] != 0x54FA:
            c.run(1)
        _DEPART = (list(c.mem), list(c.R), c.next_int)
    c = CPC(bytes(_DEPART[0]), 0x5400, 0xBFF0)
    c.mem[:] = _DEPART[0]; c.R[:] = _DEPART[1]; c.next_int = _DEPART[2]
    return c


def pousser(c, *adresses):
    for a in reversed(adresses):
        sp = (c.R[12] - 2) & 0xFFFF; c.mem[sp] = a & 0xFF; c.mem[sp + 1] = a >> 8; c.R[12] = sp


def entrer(c, salle, x, y, reglages=None):
    """Tal entre dans `salle` en (x, y) ; `reglages` : {adresse: valeur} posés avant l'entrée."""
    mem = c.mem
    for a, v in (reglages or {}).items():
        mem[a] = v
    mem[0xB4ED] = salle
    pousser(c, 0x6A18, 0x54FA)                 # &6A1F rend la main en &6A18 : CALL &7051, CALL &6A2A, RET
    c.R[24] = 0x6A1F
    c.run(1)
    while c.R[24] != 0x54FA:
        c.run(1)
    mem[0xB403], mem[0xB404] = x, y
    return c


def en_armure(c):
    """Tal entre dans l'armure là où il est (&60D3, comme movement/verif_armure.py)."""
    mem = c.mem
    mem[0xB4F4] = mem[0xB4ED]; mem[0xB4F5] = mem[0xB404] + 1; mem[0xB4F6] = mem[0xB403]
    pousser(c, 0x54FA)
    c.R[24] = 0x60D3
    c.run(1)
    while c.R[24] != 0x54FA:
        c.run(1)
    return c


def tracer(c, plan, arret=None):
    """plan : liste de (touches, nombre de tours). Renvoie [(image en &5704, image au &54FA suivant)]."""
    R, mem = c.R, c.mem
    paires, avant = [], None
    for touches, n in plan:
        c.keys = {KEY[k] for k in touches}
        for _ in range(n):
            while True:
                pc = R[24]
                if pc == 0x5704:
                    avant = bytes(mem)
                elif pc == 0x54FA and avant is not None:
                    paires.append((avant, bytes(mem))); avant = None
                    c.run(1)
                    break
                c.run(1)
            if arret and arret(mem):
                return paires
    return paires


if __name__ == '__main__':
    t = time.time(); c = depart(); print('départ %.1fs' % (time.time() - t))
    t = time.time(); entrer(c, 0x44, 0x24, 0x57); print('entrée %.1fs' % (time.time() - t))
    t = time.time(); p = tracer(c, [((), 50)]); print('%d tours %.1fs' % (len(p), time.time() - t))
    for a, b in p[:3]:
        print(' '.join('%02X' % v for v in b[0xB400:0xB400 + 19 * 3]))
    print('B512=%02X B4EE=%02X B4FB=%02X B4FA=%02X' % (b[0xB512], b[0xB4EE], b[0xB4FB], b[0xB4FA]))


def tracer_entre(c, plan, debut, fin):
    """Images de la mémoire en `debut` et en `fin` (adresses), à chaque passage, pendant le plan."""
    R, mem = c.R, c.mem
    paires, avant = [], None
    for touches, n in plan:
        c.keys = {KEY[k] for k in touches}
        for _ in range(n):
            t = R[25] + FRAME
            while R[25] < t:
                pc = R[24]
                if pc == debut:
                    avant = bytes(mem)
                elif pc == fin and avant is not None:
                    paires.append((avant, bytes(mem))); avant = None
                c.run(1)
    return paires
