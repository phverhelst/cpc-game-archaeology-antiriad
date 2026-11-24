"""Construit index.html, le bac à sable, à partir de gabarit.html, de tal.js et des données du jeu.

Les sprites de Tal sont décodés comme le fait la routine de dessin &6D3C : chaque octet de sprite
passe par les tables &0200 et &0300 (deux octets d'écran), auxquels s'ajoute par OU la teinte du
sprite (&9332) ; un octet nul est transparent. Les données d'origine regardent vers la gauche ; le
jeu les retourne en place quand le bit 7 du numéro de sprite est mis (&73F0). La palette est celle
de la zone de jeu, relevée dans l'émulateur.
Usage : python3 construire.py
"""
import json, os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'movement'))
sys.path.insert(0, ICI)
from tables import TABLES, BINAIRE
import salle
from verif_js import tables_js

# Palette de la zone de jeu (numéros de couleurs matérielles des stylos 0 à 15), relevée dans
# l'émulateur au premier écran ; correspondance RGB de cpcarch/cpcgfx.py.
STYLOS = [20, 22, 22, 18, 20, 28, 12, 28, 20, 7, 3, 24, 20, 14, 3, 28]
HW = {0x00: (128, 128, 128), 0x01: (128, 128, 128), 0x02: (0, 255, 128), 0x03: (255, 255, 128), 0x04: (0, 0, 128),
      0x05: (255, 0, 128), 0x06: (0, 128, 128), 0x07: (255, 128, 128), 0x08: (255, 0, 128), 0x09: (255, 255, 128),
      0x0A: (255, 255, 0), 0x0B: (255, 255, 255), 0x0C: (255, 0, 0), 0x0D: (255, 0, 255), 0x0E: (255, 128, 0),
      0x0F: (255, 128, 255), 0x10: (0, 0, 128), 0x11: (0, 255, 128), 0x12: (0, 255, 0), 0x13: (0, 255, 255),
      0x14: (0, 0, 0), 0x15: (0, 0, 255), 0x16: (0, 128, 0), 0x17: (0, 128, 255), 0x18: (128, 0, 128),
      0x19: (128, 255, 128), 0x1A: (128, 255, 0), 0x1B: (128, 255, 255), 0x1C: (128, 0, 0), 0x1D: (128, 0, 255),
      0x1E: (128, 128, 0), 0x1F: (128, 128, 255)}


def px0(b):
    return (((b >> 7) & 1) | (((b >> 3) & 1) << 1) | (((b >> 5) & 1) << 2) | (((b >> 1) & 1) << 3),
            ((b >> 6) & 1) | (((b >> 2) & 1) << 1) | (((b >> 4) & 1) << 2) | ((b & 1) << 3))


def sprites(mem):
    """Chaque sprite : liste de lignes de 12 caractères, stylo en hexadécimal ou '.' (transparent)."""
    w = lambda a: mem[a] | mem[a + 1] << 8
    res = {}
    for s, (dl, h) in TABLES.sprites.items():
        a, teinte, larg = w(0x9432 + 4 * s), mem[0x9332 + s], dl
        lignes = []
        for y in range(h):
            l = ''
            for xb in range(larg):
                c = mem[a + y * larg + xb]
                for o in (mem[0x200 + c], mem[0x300 + c]):
                    l += '..' if not o else ''.join('%x' % p for p in px0(o | teinte))
            lignes.append(l)
        res[s] = lignes
    return res


def main():
    mem = open(BINAIRE, 'rb').read()
    donnees = {
        'tables': tables_js(),
        'palette': ['#%02x%02x%02x' % HW[c] for c in STYLOS],
        'sprites': sprites(mem),
        'plan': salle.PLAN,
        'octets_case': salle.OCTETS,
    }
    g = open(os.path.join(ICI, 'gabarit.html'), encoding='utf-8').read()
    js = open(os.path.join(ICI, 'tal.js'), encoding='utf-8').read()
    page = g.replace('/*TAL_JS*/', js).replace('/*DONNEES*/', json.dumps(donnees, separators=(',', ':')))
    open(os.path.join(ICI, 'index.html'), 'w', encoding='utf-8').write(page)
    print('index.html écrit, %d octets' % len(page.encode()))


if __name__ == '__main__':
    main()
