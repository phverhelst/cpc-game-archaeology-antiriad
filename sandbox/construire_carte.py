"""Construit carte.html, le bac à sable 3 : la carte complète (69 salles), Tal à pied et dans l'armure,
la cellule de recharge et les quatre pièces de l'armure à leurs positions d'origine.

Les salles viennent de rooms/salles.bin (capturées par rooms/capturer.py), compressées (zlib) dans la
page et décompressées par le navigateur (DecompressionStream). La disposition de la carte est
celle de la carte C64, corrigée par les liens Amstrad (&9632).
Usage : python3 construire_carte.py
"""
import base64, json, os, sys, zlib
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'movement'))
sys.path.insert(0, ICI)
from tables import TABLES, BINAIRE
import armure as A
from verif_js import tables_js
from construire import HW
from construire_armure import sprites, messages

NB = 0x45


# Disposition de la carte : celle de la carte C64 du C64-Wiki (colonnes A-O, rangées 1-14, mêmes numéros de
# salles). Les salles &27 et &28, absentes de sa grille numérotée mais dessinées sur sa carte illustrée (N12, O12),
# sont au-dessus de &36 et &37. Un seul point est corrigé d'après les liens Amstrad : la salle &06 est à gauche
# de &07 et au-dessus de &0A (liens &07 gauche, &06 droite, &06 bas, &0A haut), et non à droite de &09.
# Les 8 liens restants qui ne collent pas sont des retours d'un bout à l'autre d'une rangée (&06/&09, &0D/&12,
# &1A/&23, &29/&37) ; le lien bas de &32 mène à la salle inexistante &45.
RANGEES = {
    0: {7: 0x00}, 1: {7: 0x01}, 2: {7: 0x02, 8: 0x03}, 3: {7: 0x04, 8: 0x05},
    4: {6: 0x06, 7: 0x07, 8: 0x08, 9: 0x09}, 5: {6: 0x0A, 7: 0x0B, 9: 0x0C},
    6: dict(zip(range(5, 11), range(0x0D, 0x13))), 7: {6: 0x13, 7: 0x14, 8: 0x15}, 8: {6: 0x16, 7: 0x17, 8: 0x18},
    9: {7: 0x19}, 10: dict(zip(range(3, 13), range(0x1A, 0x24))), 11: {5: 0x24, 7: 0x25, 8: 0x26, 13: 0x27, 14: 0x28},
    12: dict(zip(range(0, 15), range(0x29, 0x38))), 13: dict(zip(range(1, 14), range(0x38, 0x45))),
}


def disposition(liens):
    pos = {r: (x, y) for y, m in RANGEES.items() for x, r in m.items()}
    assert sorted(pos) == list(range(NB))
    dep = {'gauche': (-1, 0), 'droite': (1, 0), 'haut': (0, -1), 'bas': (0, 1)}
    ok = hors = 0
    for r, l in liens.items():
        for c, (dx, dy) in dep.items():
            if l[c] == 255: continue
            if pos[l[c]] == (pos[r][0] + dx, pos[r][1] + dy): ok += 1
            else: hors += 1
    print('liens conformes à la grille : %d, hors grille : %d' % (ok, hors))
    return pos


DEPART = os.path.join(ICI, '..', 'build', 'antiriad_54FA.bin')


def depart_mem():
    """La mémoire du jeu au début de la boucle principale (&54FA), partie lancée : écrite une fois par
    l'émulateur (enemies/trace.py), puis relue."""
    if not os.path.exists(DEPART):
        sys.path.insert(0, os.path.join(ICI, '..', 'enemies'))
        import trace as TR
        open(DEPART, 'wb').write(bytes(TR.depart().mem))
    return open(DEPART, 'rb').read()


def main():
    mem = open(BINAIRE, 'rb').read()
    info = json.load(open(os.path.join(ICI, '..', 'rooms', 'salles.json')))['salles']
    brut = open(os.path.join(ICI, '..', 'rooms', 'salles.bin'), 'rb').read()
    liens = {}
    for k, v in info.items():
        # Le lien « haut » de la salle &32 vaut &45 : salle inexistante (la table n'a que 69 entrées).
        liens[int(k, 16)] = {c: (x if x < NB else 255) for c, x in v['liens'].items()}
    pos = disposition(liens)
    cellules = [{'salle': mem[0xA066 + 3 * i] & 0x7F, 'x': mem[0xA067 + 3 * i], 'y': mem[0xA068 + 3 * i]} for i in range(15)]
    pieces = [{'salle': mem[0x8F14 + 3 * i], 'x': mem[0x8F15 + 3 * i], 'y': mem[0x8F16 + 3 * i], 'etat': 0x1D + i,
               'sprite': mem[(mem[0x9021 + 2 * (0x1D + i)] | mem[0x9022 + 2 * (0x1D + i)] << 8) + 1] & 0x7F} for i in range(4)]
    ids = set(TABLES.sprites) | {0x65, 0x1C} | {p['sprite'] for p in pieces}
    for e in range(1, 0x40):                                         # toutes les images de toutes les animations
        p = mem[0x9021 + 2 * e] | mem[0x9022 + 2 * e] << 8
        for c in mem[p + 1:p + 40]:
            if c >= 0xFC:
                break
            ids.add(c & 0x7F)
    ids = sorted(ids)
    textes = mem[0xA100:0xA480].decode('latin1').split('$')
    msgs = {n: textes[n - 2] for n in range(3, 0x16)}
    msgs[1], msgs[2] = 'ALREADY CARRYING RECHARGE CELL', 'YOU HAVE THREE REJUVENATIONS REMAINING'
    donnees = {
        'tables': tables_js(), 'gaz': [list(g) for g in A.GAZ], 'sprites': sprites(mem, ids),
        'salles_z': base64.b64encode(zlib.compress(brut, 9)).decode(),
        'palettes': {int(k, 16): ['#%02x%02x%02x' % HW[c & 31] for c in v['palette']] for k, v in info.items()},
        'liens': liens, 'pos': pos,
        'armure': {'salle': mem[0x8F11], 'y': mem[0x8F12], 'x': mem[0x8F13]},
        'depart': {'salle': 0x44, 'x': 0x24, 'y': 0x57},
        'cellules': cellules, 'pieces': pieces, 'messages': msgs,
        'memoire_z': base64.b64encode(zlib.compress(depart_mem(), 9)).decode(), 'hw': ['#%02x%02x%02x' % HW.get(k, (0, 0, 0)) for k in range(32)],
    }
    g = open(os.path.join(ICI, 'gabarit_carte.html'), encoding='utf-8').read()
    page = (g.replace('/*TAL_JS*/', open(os.path.join(ICI, 'tal.js'), encoding='utf-8').read())
             .replace('/*ARMURE_JS*/', open(os.path.join(ICI, 'armure.js'), encoding='utf-8').read())
             .replace('/*MONDE_JS*/', open(os.path.join(ICI, 'monde.js'), encoding='utf-8').read())
             .replace('/*DONNEES*/', json.dumps(donnees, separators=(',', ':'))))
    open(os.path.join(ICI, 'carte.html'), 'w', encoding='utf-8').write(page)
    w = max(p[0] for p in pos.values()) + 1; h = max(p[1] for p in pos.values()) + 1
    print('carte.html écrit, %d octets ; grille %d × %d ; pièces %s' % (
        len(page.encode()), w, h, ' '.join('%02X:%02X' % (p['etat'], p['salle']) for p in pieces)))


if __name__ == '__main__':
    main()
