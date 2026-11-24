"""Vérifie pilote.py contre le vrai jeu : la musique de l'écran titre, puis des bruitages en cours de partie.

À chaque appel du pilote (&755E), on prend l'image de la mémoire à l'entrée, on applique le modèle, et l'on
compare à la mémoire du jeu juste avant l'envoi au AY (&7706) : les 11 registres, les trois fiches de voie et
l'enveloppe de bruit. On fait aussi tourner le modèle en continu, sans recaler, sur toute la durée.
Usage : python3 verif.py [nombre d'appels]
"""
import os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
from cpcarch.emu import CPC
import pilote as P

ZONE = list(range(0x7A4F, 0x7A5B)) + list(range(P.VOIES, P.VOIES + 3 * P.TAILLE)) + list(range(0x7AE5, 0x7AF2))


def appels(c, n, debut=0x755E, fin=0x7706):
    R, mem = c.R, c.mem
    avant = None
    while n:
        pc = R[24]
        if pc == debut:
            avant = bytearray(mem)
        elif pc == fin and avant is not None:
            yield avant, bytes(mem); avant = None; n -= 1
        c.run(1)


def comparer(paires, nom):
    libre, ecarts, diverge = None, 0, None
    for i, (img, apres) in enumerate(paires):
        m = bytearray(img); P.tour(m)
        d = [a for a in ZONE if m[a] != apres[a]]
        ecarts += bool(d)
        if libre is None:
            libre = bytearray(img)
        else:                                                        # en continu : seules les commandes du jeu (&752A) viennent du jeu
            for a in ZONE:
                if img[a] != prec[a]:
                    libre[a] = img[a]
        P.tour(libre)
        if diverge is None and any(libre[a] != apres[a] for a in ZONE):
            diverge = i
        prec = apres
        if d and ecarts <= 3:
            print('   appel %d : %s' % (i, ' '.join('%04X:%02X/%02X' % (a, m[a], apres[a]) for a in d[:8])))
    print('%-28s %5d appels : %d écart(s), en continu %s' % (nom, i + 1, ecarts, 'identique' if diverge is None else 'diverge à %d' % diverge))
    return not ecarts and diverge is None


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
    c = CPC(open(os.path.join(ICI, '..', 'build', 'antiriad_5400.bin'), 'rb').read(), 0x5400, 0xBFF0)
    ok = comparer(appels(c, n), "musique de l'écran titre")
    sys.path.insert(0, os.path.join(ICI, '..', 'enemies'))
    import trace as TR
    from cpcarch.emu import KEY
    for nom, salle, x, y, reglages, touches in (
            ('bruitages, salle 44', 0x44, 0x30, 0x7F, {}, ['joy_left', '', 'fire', '', 'fire', 'joy_right', 'fire', '']),
            ('bruitages, salle 0F', 0x0F, 0x24, 0x57, {}, ['', 'fire', 'joy_up', '', 'fire', 'joy_left', 'fire', ''])):
        c = TR.depart(); TR.entrer(c, salle, x, y, reglages)
        def plan():
            for i, t in enumerate(touches * 6):
                c.keys = {KEY[t]} if t else set()
                yield from appels(c, 60)
        ok = comparer(plan(), nom) and ok
    print('TOUT CONCORDE' if ok else 'ÉCARTS')
