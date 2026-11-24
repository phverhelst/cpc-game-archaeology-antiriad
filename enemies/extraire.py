"""Scripts de mouvement des objets (&97F8) et ennemis de chaque salle (&9BC7), lus dans le binaire.

Écrit ennemis.json et imprime le classement des scripts et leur emploi dans les 69 salles.
Un pas de script fait 4 octets : directions (+7), durée (+2, le pas dure durée+1 tours),
vitesse horizontale (+8), vitesse verticale (+9). Directions &0F : guidage vers Tal (&6CDE).
Commandes : FC reprend au début, FD fige (garde les dernières directions), FE rend la main à Tal.
"""
import json, os
from collections import Counter
ICI = os.path.dirname(os.path.abspath(__file__))
m = open(os.path.join(ICI, '..', 'build', 'antiriad_5400.bin'), 'rb').read()
w = lambda a: m[a] | m[a + 1] << 8
NB_SCRIPTS, NB_SALLES = 0x2E, 0x45


def script(s):
    p, pas = w(0x97F8 + 2 * s), []
    for i in range(64):
        d, t, vx, vy = m[p + 4 * i:p + 4 * i + 4]
        if d >= 0xFC:
            return pas, {0xFC: 'boucle', 0xFD: 'fige', 0xFE: 'fin', 0xFF: 'FF'}[d]
        pas.append((d, t + 1, vx, vy))
    raise ValueError(s)


def bilan(pas):
    """Déplacement net (octets, lignes) d'un passage complet, si aucun pas n'est guidé."""
    dx = dy = 0
    for d, t, vx, vy in pas:
        if d == 0x0F:
            return None
        dx += t * vx * ((d >> 3 & 1) - (d >> 2 & 1))
        dy += t * vy * ((d >> 1 & 1) - (d & 1))
    return dx, dy


def categorie(s, pas, fin):
    if any(d == 0x0F for d, *_ in pas):
        return 'guidé vers Tal'
    if fin == 'boucle':
        return 'patrouille fermée' if bilan(pas) == (0, 0) else 'boucle ouverte'
    return 'trajet unique (%s)' % fin


salles = {}
for r in range(NB_SALLES):
    p = w(0x9BC7 + 2 * r)
    salles[r] = [dict(zip(('x', 'y', 'script', 'etat'), m[p + 1 + 4 * i:p + 5 + 4 * i])) for i in range(m[p])]
emploi = Counter(o['script'] for L in salles.values() for o in L)
scripts = {}
for s in range(1, NB_SCRIPTS):
    pas, fin = script(s)
    scripts[s] = {'pas': pas, 'fin': fin, 'categorie': categorie(s, pas, fin), 'bilan': bilan(pas),
                  'duree': sum(t for _, t, _, _ in pas), 'emplois': emploi.get(s, 0)}

if __name__ == '__main__':
    json.dump({'scripts': {'%02X' % s: v for s, v in scripts.items()},
               'salles': {'%02X' % r: L for r, L in salles.items()},
               'liens_salles': {'%02X' % r: list(m[0x9632 + 4 * r:0x9636 + 4 * r]) for r in range(NB_SALLES)}},
              open(os.path.join(ICI, 'ennemis.json'), 'w'), indent=1, ensure_ascii=False)
    tot = Counter()
    for s, v in scripts.items():
        tot[v['categorie']] += v['emplois']
        print('%02X %-24s %2d objets, cycle %3d tours, bilan %s' % (s, v['categorie'], v['emplois'], v['duree'], v['bilan']))
    print('sans script (immobiles) :', emploi.get(0, 0))
    print('objets par catégorie :', dict(tot), '; total', sum(len(L) for L in salles.values()))
