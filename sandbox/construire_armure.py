"""Construit armure.html, le bac à sable 2 : Tal, l'armure et la cellule de recharge dans 2 × 2 vraies salles.

Salles &31 | &32 (haut) et &3F | &40 (bas), lues dans rooms/salles.bin (capturées par rooms/capturer.py).
Positions d'origine : armure en &3F (table &8F11), cellules de recharge des salles &32 et &40 (table &A066).
Usage : python3 construire_armure.py
"""
import base64, json, os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'movement'))
sys.path.insert(0, ICI)
from tables import TABLES, BINAIRE
import armure as A
from verif_js import tables_js
from construire import HW, px0

CARRE = [[0x31, 0x32], [0x3F, 0x40]]   # &31 au-dessus de &3F, &32 au-dessus de &40


def sprites(mem, ids):
    w = lambda a: mem[a] | mem[a + 1] << 8
    res = {}
    for s in ids:
        a, teinte, larg, h = w(0x9432 + 4 * s), mem[0x9332 + s], mem[0x9432 + 4 * s + 2], mem[0x9432 + 4 * s + 3]
        lignes = []
        for y in range(h):
            l = ''
            for xb in range(larg):
                c = mem[a + y * larg + xb]
                for o in (mem[0x200 + c], mem[0x300 + c]):
                    l += '..' if not o else ''.join('%x' % p for p in px0(o | teinte))
            lignes.append(l)
        res[s] = {'l': lignes, 'dl': larg}
    return res


def messages(mem):
    """Textes du jeu (table en &A100…, séparés par $) ; le numéro de message n correspond au texte n − 2."""
    t = mem[0xA100:0xA480].decode('latin1').split('$')
    return {n: t[n - 2] for n in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10)}


def main():
    mem = open(BINAIRE, 'rb').read()
    salles = json.load(open(os.path.join(ICI, '..', 'rooms', 'salles.json')))['salles']
    brut = open(os.path.join(ICI, '..', 'rooms', 'salles.bin'), 'rb').read()
    d = {}
    for rang in CARRE:
        for r in rang:
            info = salles['%02X' % r]
            d[r] = {'octets': base64.b64encode(brut[r * 10880:(r + 1) * 10880]).decode(),
                    'palette': ['#%02x%02x%02x' % HW[c & 31] for c in info['palette']],
                    'liens': info['liens']}
    cellules = []
    for i in range(15):
        r, x, y = mem[0xA066 + 3 * i] & 0x7F, mem[0xA067 + 3 * i], mem[0xA068 + 3 * i]
        if r in d:
            cellules.append({'salle': r, 'x': x, 'y': y})
    ids = sorted(set(TABLES.sprites) | {0x65, 0x1C})
    donnees = {
        'tables': tables_js(), 'gaz': [list(g) for g in A.GAZ],
        'sprites': sprites(mem, ids), 'carre': CARRE, 'salles': d,
        'armure': {'salle': mem[0x8F11], 'y': mem[0x8F12], 'x': mem[0x8F13]},
        'cellules': cellules, 'messages': messages(mem),
    }
    g = open(os.path.join(ICI, 'gabarit_armure.html'), encoding='utf-8').read()
    page = (g.replace('/*TAL_JS*/', open(os.path.join(ICI, 'tal.js'), encoding='utf-8').read())
             .replace('/*ARMURE_JS*/', open(os.path.join(ICI, 'armure.js'), encoding='utf-8').read())
             .replace('/*DONNEES*/', json.dumps(donnees, separators=(',', ':'))))
    open(os.path.join(ICI, 'armure.html'), 'w', encoding='utf-8').write(page)
    print('armure.html écrit, %d octets ; armure en salle %02X X=%02X Y=%02X ; %d cellules' % (
        len(page.encode()), donnees['armure']['salle'], donnees['armure']['x'], donnees['armure']['y'], len(cellules)))


if __name__ == '__main__':
    main()
