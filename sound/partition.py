"""Lecture musicale des sons du jeu : le flot d'octets de chaque voix est décodé en notes et durées.

Une note est un index dans la table des périodes (&7974) : 0 = do 0 (16,35 Hz), un demi-ton par index. La
durée vient de la commande 83 (ou 86), en unités ; l'unité vaut 6000 / (8 × tempo) centièmes de seconde, soit
une triple croche quand le tempo (commande 85) est donné en noires par minute.
"""
import os
ICI = os.path.dirname(os.path.abspath(__file__))
NOMS = ['do', 'do♯', 'ré', 'ré♯', 'mi', 'fa', 'fa♯', 'sol', 'sol♯', 'la', 'la♯', 'si']
ANGLAIS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def memoire():
    return open(os.path.join(ICI, '..', 'build', 'antiriad_5400.bin'), 'rb').read()


def voix(m, son):
    """Liste d'événements (type, valeur, durée en unités) jusqu'à la reprise (82) ou la fin (8B)."""
    p = m[0x8AEF + 2 * son] | m[0x8AF0 + 2 * son] << 8
    duree, sortie, infos = 0, [], {}
    while True:
        a = m[p]
        if a < 0x80:
            sortie.append(('note', a, duree)); p += 1; continue
        c = a - 0x80
        if c in (0, 1, 7, 9, 0x0A):
            infos.setdefault({0: 'volume', 1: 'son/bruit', 7: 'instrument', 9: 'env. bruit', 0x0A: 'répétition'}[c], []).append(m[p + 1])
            sortie.append(({0: 'volume', 1: 'mixage', 7: 'instrument', 9: 'envbruit', 0x0A: 'repet'}[c], m[p + 1], 0))
            p += 2
        elif c == 3:
            duree = m[p + 1]; p += 2
        elif c == 5:
            sortie.append(('tempo', m[p + 1], 0)); p += 2
        elif c == 6:
            n = m[p + 1]; ds = list(m[p + 2:p + 2 + n])
            duree = sum(ds[:-1]); p += 2 + n
        elif c == 4:
            sortie.append(('silence', None, duree)); p += 1
        elif c == 8:
            sortie.append(('bruit', m[p + 1] & 0x1F, 0 if m[p + 1] & 0x80 else duree)); p += 2
        elif c == 2:
            return sortie, 'reprise'
        elif c == 0x0B:
            return sortie, 'fin'


def nom(n, francais=True):
    return (NOMS if francais else ANGLAIS)[n % 12] + str(n // 12)


if __name__ == '__main__':
    m = memoire()
    for s in (1, 2, 3):
        ev, fin = voix(m, s)
        notes = [e for e in ev if e[0] in ('note', 'silence')]
        total = sum(e[2] for e in notes)
        print('son %d : %d notes, %d unités = %.1f mesures de 3/4 (24 unités), %s' % (s, len(notes), total, total / 24, fin))
        t = 0; ligne = []
        for e in ev:
            if e[0] == 'note':
                ligne.append('%s:%d' % (nom(e[1]), e[2])); t += e[2]
            elif e[0] == 'silence':
                ligne.append('—:%d' % e[2]); t += e[2]
            elif e[0] in ('tempo', 'instrument', 'volume'):
                ligne.append('[%s %d]' % (e[0], e[1]))
        print('  ' + ' '.join(ligne[:60]))
