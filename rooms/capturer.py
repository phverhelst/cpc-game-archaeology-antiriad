"""Capture des 69 salles telles que le jeu les dessine.

Pour chaque salle, on part de l'état du jeu au démarrage, on règle &B4ED (salle courante) et on fait
exécuter la routine de dessin du jeu (&7051) jusqu'en &7101, juste avant la création des objets
(armure, ennemis, cellules, pièces). La zone de jeu (lignes &32 à &B9, 80 octets) est alors relevée
par la table d'adresses de lignes (&8BF3).

Pendant le dessin, le jeu met la palette au noir ; la palette de chaque salle se reconstitue sans
exécution : stylos communs relevés au démarrage (&8DF3), stylos 1 à 7 pris dans le schéma de couleurs
de la salle (&51D7 + 10 × schéma, schéma = &518F[salle]).

Écrit salles.bin (69 × 136 × 80 octets, salle après salle, ligne après ligne) et salles.json
(palettes en numéros de couleurs matérielles, liens de sortie droite/gauche/bas/haut dans l'ordre
lu par &69A7, schéma). Le lien « bas » de la salle &32 vaut &45 : salle inexistante.
Nécessite cpcarch et SkoolKit (voir README.md).
"""
import json, os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
from cpcarch.emu import CPC, KEY

NB, LIGNES, OCTETS = 0x45, 0xBA - 0x32, 80


def main():
    m = open(os.path.join(ICI, '..', 'build', 'antiriad_5400.bin'), 'rb').read()
    c = CPC(m, 0x5400, 0xBFF0)
    c.run(500_000); c.keys = {KEY['fire']}; c.run(500_000); c.keys = set(); c.run(1_000_000)
    mem, R = c.mem, c.R
    w = lambda a: mem[a] | mem[a + 1] << 8
    etat, regs = list(mem), list(R)
    base = list(mem[0x8DF3:0x8DF3 + 16])
    sortie, info = bytearray(), {}
    for r in range(NB):
        mem[:] = etat; R[:] = regs
        mem[0xB4ED] = r
        sp = (R[12] - 2) & 0xFFFF; mem[sp] = 0; mem[sp + 1] = 0; R[12] = sp; R[24] = 0x7051
        n = 0
        while R[24] != 0x7101:
            c.run(1); n += 1
            assert n < 3_000_000, r
        for l in range(0x32, 0xBA):
            a = w(0x8BF3 + 2 * l)
            sortie += bytes(mem[(a + x) & 0xFFFF] for x in range(OCTETS))
        schema = m[0x518F + r]
        pal = list(base); pal[1:8] = m[0x51D7 + 10 * schema:0x51D7 + 10 * schema + 7]
        info['%02X' % r] = {'palette': pal, 'schema': schema,
                            # ordre lu par &69A7 : octet 0 sortie à droite, 1 à gauche, 2 en bas, 3 en haut
                            'liens': dict(zip(('droite', 'gauche', 'bas', 'haut'), m[0x9632 + 4 * r:0x9636 + 4 * r]))}
    open(os.path.join(ICI, 'salles.bin'), 'wb').write(sortie)
    json.dump({'source': 'dessin par la routine du jeu &7051, arrêt en &7101', 'lignes': [0x32, 0xB9], 'octets': OCTETS,
               'salles': info}, open(os.path.join(ICI, 'salles.json'), 'w'), indent=1)
    print('salles.bin : %d octets ; salles.json' % len(sortie))


if __name__ == '__main__':
    main()
