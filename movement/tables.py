"""Tables du mouvement de Tal, lues dans la mémoire du jeu au démarrage (build/antiriad_5400.bin).

Lancé seul, le module écrit `tal_tables.json`, la même chose sous une forme lisible par n'importe
quel langage. Les adresses sont celles du jeu en mémoire.
"""
import json, os
from dataclasses import dataclass

ICI = os.path.dirname(os.path.abspath(__file__))
BINAIRE = os.path.join(ICI, '..', 'build', 'antiriad_5400.bin')

ADRESSES = {
    'vitesses':    (0x8EC2, "vitesse verticale (lignes/tour) selon l'index &B498, montée et chute"),
    'classes':     (0x8F3B, "classe d'entrée selon les 4 bits du joystick (0x0F = feu)"),
    'transitions': (0x8F4B, "par état (1 à 0x1B), 8 octets : état suivant pour les classes 0-5, masque des directions"),
    'animations':  (0x9021, "par état, pointeur vers : délai, puis images ; FC boucle, FD fin, FE n autre état"),
    'sprites':     (0x9432, "par sprite, 4 octets : adresse, demi-largeur (octets), hauteur (lignes)"),
    'etats_mur':   (0x8B2D, "états pour lesquels on teste le mur devant Tal"),
    'motif_sol':   (0x8E1C, "motif de pixels reconnu comme sol (6 octets)"),
}


@dataclass
class Animation:
    delai: int
    code: list


class Tables:
    def __init__(self, mem):
        w = lambda a: mem[a] | mem[a + 1] << 8
        self.vitesses = list(mem[0x8EC2:0x8EC2 + 17])
        self.classes = list(mem[0x8F3B:0x8F3B + 16])
        self.transitions = {}
        for e in range(1, 0x1C):
            a = 0x8F4B + (e - 1) * 8
            self.transitions[e] = (list(mem[a:a + 6]), mem[a + 6])
        self.animations = {}
        for e in range(1, 0x1C):
            p = w(0x9021 + 2 * e)
            code, i = [], p + 1
            while True:
                b = mem[i]; code.append(b); i += 1
                if b in (0xFC, 0xFD, 0xFF):
                    break
                if b == 0xFE:
                    code.append(mem[i]); break
            self.animations[e] = Animation(mem[p], code)
        ids = {b & 0x7F for a in self.animations.values() for b in a.code if b < 0xFC}
        self.sprites = {s: (mem[0x9432 + 4 * s + 2], mem[0x9432 + 4 * s + 3]) for s in sorted(ids)}
        self.etats_mur = list(mem[0x8B2D:0x8B2D + 10])
        self.motif_sol = list(mem[0x8E1C:0x8E1C + 6])

    def json(self):
        return {
            'source': 'The Sacred Armour of Antiriad (Amstrad CPC, Palace Software 1986), mémoire au démarrage',
            'adresses': {k: {'adresse': '&%04X' % a, 'role': r} for k, (a, r) in ADRESSES.items()},
            'vitesses': self.vitesses,
            'classes': self.classes,
            'transitions': {'%02X' % e: {'suivants': s, 'masque': m} for e, (s, m) in self.transitions.items()},
            'animations': {'%02X' % e: {'delai': a.delai, 'code': ['%02X' % b for b in a.code]}
                           for e, a in self.animations.items()},
            'sprites': {'%02X' % s: {'demi_largeur': l, 'hauteur': h} for s, (l, h) in self.sprites.items()},
            'etats_mur': self.etats_mur,
            'motif_sol': self.motif_sol,
        }


TABLES = Tables(open(BINAIRE, 'rb').read())

if __name__ == '__main__':
    with open(os.path.join(ICI, 'tal_tables.json'), 'w') as f:
        json.dump(TABLES.json(), f, indent=1, ensure_ascii=False)
    print('tal_tables.json écrit')
