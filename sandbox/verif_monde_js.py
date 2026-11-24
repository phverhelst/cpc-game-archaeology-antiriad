"""Vérifie monde.js contre enemies/monde.py (lui-même vérifié contre le jeu par enemies/verif.py).

Les deux modèles partent des mêmes images de la mémoire du jeu (64 Ko), relevées dans l'émulateur au début des
scénarios de verif.py, à l'entrée de la salle &00 avec la mine, et après le déclenchement de la fin. Ils
appliquent ensuite la même suite d'opérations, tour après tour : joystick, tir de l'armure, mort de Tal, messages,
interruption des deux secondes, fin de tour, implosion et boucle finale. Après chaque tour, on compare
l'empreinte (MD5) de toute la mémoire. On compare aussi la création des objets des 69 salles, jeu lancé ou non,
avec et sans pièces.
Usage : python3 verif_monde_js.py   (nécessite node)
"""
import base64, hashlib, json, os, subprocess, sys, zlib
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'enemies'))
import trace as TR
import verif as V
import monde as W

TOURS = 320
JOY = [0, 0, 1, 0, 8, 8, 0x10, 0x18, 0, 4, 0x14, 2, 0, 9, 0x10, 0]


def jouer(m, sel):
    """La suite d'opérations, appliquée à m ; renvoie les empreintes après chaque tour."""
    empreintes, final = [], False
    for t in range(TOURS):
        m[0x7A4C] = JOY[(t * 7 + sel) % len(JOY)]
        if final:
            W.boucle_finale(m)
        else:
            if m[W.A_PIED] == 0 and m[0xB519] == 0:
                W.tir_pulsar(m)
            elif m[W.A_PIED]:
                W.mort_de_tal(m)
            if t % 37 == 5:
                W.message(m, 1 + (t * 13 + sel) % 0x15)
            if t % 34 == 0:
                W.toutes_les_deux_secondes(m)
            if W.fin_de_tour(m) == 'fin':
                W.implosion(m)
                final = True
        empreintes.append(hashlib.md5(bytes(m)).hexdigest())
    return empreintes


def departs():
    tous = dict(V.SCENARIOS, **{k: v + (True,) for k, v in V.EN_ARMURE.items()})
    for nom, (salle, x, y, reglages, plan, *armure) in tous.items():
        c = TR.depart(); TR.entrer(c, salle, x, y, reglages)
        if armure:
            TR.en_armure(c)
        img, _ = TR.tracer(c, [((), 1)])[0]
        yield nom, bytearray(img)
    rg = {0xB512: 0, 0xB519: 0, 0xB51A: 0, 0xB51B: 0, 0xB51C: 0}
    c = TR.depart(); TR.entrer(c, 0x00, 0x22, 0x50, rg); TR.en_armure(c)
    yield 'salle 00 avec la mine', bytearray(TR.tracer(c, [((), 1)])[0][0])
    p = TR.tracer(c, [(('joy_up',), 6), ((), 10), (('joy_down',), 80)], arret=lambda m: m[W.ACTIFS] == 0)
    yield 'mine posée', bytearray(p[-1][1])


def main():
    cas = []
    for sel, (nom, img) in enumerate(departs()):
        cas.append({'nom': nom, 'f': 'jeu', 'sel': sel, 'image': base64.b64encode(zlib.compress(bytes(img), 9)).decode(),
                    'attendu': jouer(bytearray(img), sel)})
    base = bytearray(TR.depart().mem)
    salles = []
    for r in range(0x45):
        for lance in (0xFF, 0):
            for pieces in (0xFF, 0):
                m = bytearray(base); m[W.SALLE] = r; m[0xB512] = lance; m[0xB519:0xB51D] = bytes([pieces] * 4)
                W.entrer_salle(m)
                salles.append([r, lance, pieces, hashlib.md5(bytes(m)).hexdigest()])
    f = '/tmp/monde_cas.json'
    json.dump({'tours': TOURS, 'joy': JOY, 'cas': cas, 'base': base64.b64encode(zlib.compress(bytes(base), 9)).decode(),
               'salles': salles}, open(f, 'w'))
    sortie = subprocess.run(['node', os.path.join(ICI, 'verif_monde_js.js'), f], capture_output=True, text=True)
    if sortie.returncode:
        print(sortie.stderr); sys.exit(1)
    r = json.loads(sortie.stdout)
    for nom, ok, ecart in r['cas']:
        print('%-22s %s' % (nom, 'identique sur %d tours' % TOURS if ok else 'diverge au tour %d' % ecart))
    print('création des objets : %d cas, %d différent(s)' % (len(salles), r['salles_ko']))
    tout = all(ok for _, ok, _ in r['cas']) and not r['salles_ko']
    print('JS CONCORDE' if tout else 'ÉCARTS')


if __name__ == '__main__':
    main()
