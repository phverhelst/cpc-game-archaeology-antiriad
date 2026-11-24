"""Banc de vérification de monde.py contre le vrai jeu (émulateur du cpcarch).

Pour chaque scénario : Tal entre dans une salle (routines du jeu), on joue un plan de touches, et pour
chaque tour on applique le modèle à l'image mémoire relevée en &5704 ; le résultat doit égaler l'image
relevée au retour en &54FA, sur les fiches des huit objets et les variables du jeu concernées. On vérifie
aussi la création des objets de la salle (entrer_salle) contre &7051, et on fait tourner le modèle en
continu, sans recaler, tant que le jeu ne sort pas du périmètre du modèle.
Usage : python3 verif.py [scénario ...] [-v]
"""
import sys
import trace as TR
from cpcarch.emu import FRAME
import monde as W

CHAMPS = [(W.o(n) + k, 'obj%d+%X' % (n, k)) for n in range(8) for k in range(19)]
GLOBALES = {0xB4EE: 'actifs', 0xB4FA: 'vie affichée', 0xB4FB: 'vie', 0xB4FC: 'énergie affichée', 0xB4FD: 'énergie',
            0xB4F9: 'compteur', 0xB517: 'délai armure', 0xB534: 'score affiché', 0xB535: 'score affiché h',
            0xB536: 'score', 0xB537: 'score h', 0xB54F: 'générateur', 0xB552: 'répit', 0xB553: 'prochain',
            0xB407: 'Tal dirs', 0xB520: 'sens armure', 0xB512: 'jeu lancé', 0xB513: 'activation', 0xB514: 'bit motif'}
GLOBALES.update({W.COUPS + i: 'coups obj%d' % (i + 2) for i in range(6)})
GLOBALES.update({W.CONTACTS + i: 'contacts %d' % i for i in range(12)})
GLOBALES.update({a: 'var %04X' % a for a in list(range(0xB521, 0xB532)) + [0xB4F7, 0xB4F8, 0xB538, 0xB499, 0x8E09, 0x8E0A, 0x8E0B]
                 + list(range(0x8B82, 0x8B87)) + list(range(0x98AA, 0x98C0))})
# L'écran central (lignes 157 à 183, colonnes 36 à 45) montre la mémoire du jeu telle qu'elle est au moment du dessin :
# des octets volatils (pile, fiches, son) y diffèrent selon l'instant exact. On vérifie le pointeur (&B4F7), pas l'image.
CENTRE = {(l, x) for l in range(157, 184) for x in range(36, 46)}
PANNEAU = [(0xC000 + (l % 8) * 0x800 + (l // 8) * 80 + x, 'panneau l%d c%d' % (l, x)) for l in range(136, 200) for x in range(80)
           if (l, x) not in CENTRE]
GLOBALES.update(dict(PANNEAU))


def avec_interruption(img, apres, f):
    """Applique f (une partie de la boucle) à une copie de img. Si l'interruption des deux secondes (&6F18) est
    tombée pendant ce tour, on ne sait pas à quel moment : on l'essaie avant puis après, et on garde le meilleur."""
    m = bytearray(img)
    if apres[0xB541] >= img[0xB541]:
        r = f(m); return m, r
    essais = []
    for avant in (True, False):
        m = bytearray(img)
        if avant: W.toutes_les_deux_secondes(m)
        r = f(m)
        if not avant: W.toutes_les_deux_secondes(m)
        essais.append((len(ecarts(m, apres)), m, r))
    _, m, r = min(essais, key=lambda e: e[0])
    return m, r


def ecarts(a, b, actifs_seuls=True):
    d = []
    for adr, nom in CHAMPS:
        n = (adr - W.OBJ) // W.TAILLE
        if actifs_seuls and not ((a[W.ACTIFS] | b[W.ACTIFS]) >> n & 1) and (adr - W.OBJ) % W.TAILLE not in (0xA,):
            continue
        if a[adr] != b[adr]:
            d.append('%s %02X/%02X' % (nom, a[adr], b[adr]))
    for adr, nom in GLOBALES.items():
        if a[adr] != b[adr]:
            d.append('%s %02X/%02X' % (nom, a[adr], b[adr]))
    return d


G, D, H, B, F = 'joy_left', 'joy_right', 'joy_up', 'joy_down', 'fire'
# salle, x, y de Tal, réglages mémoire, plan
SCENARIOS = {
    'depart_44':    (0x44, 0x24, 0x57, {}, [((), 120), ((G,), 20), ((), 40)]),
    'pierres_44':   (0x44, 0x24, 0x7F, {}, [((), 10)] + [((F,), 12), ((), 8)] * 8 + [((D,), 20), ((F,), 30)]),
    'guides_43':    (0x43, 0x30, 0x7F, {}, [((), 200)]),
    'volatile_0F':  (0x0F, 0x24, 0x57, {}, [((), 250)]),
    'gouttes_08':   (0x08, 0x10, 0x57, {}, [((), 260)]),
    'generateur_20': (0x20, 0x24, 0x7F, {}, [((), 150)]),
    'canon_1E':     (0x1E, 0x40, 0x7F, {}, [((), 200)]),
    'obstacles_03': (0x03, 0x24, 0x57, {}, [((), 80), ((D,), 60), ((G,), 60)]),
    'plantes_2A':   (0x2A, 0x24, 0x7F, {}, [((), 40), ((D,), 60), ((G,), 80)]),
    'armure_31':    (0x31, 0x24, 0x57, {}, [((), 100)]),
    'barrieres_2E': (0x2E, 0x24, 0x7F, {}, [((), 60), ((G,), 60)]),
    'tir_44':       (0x44, 0x30, 0x7F, {}, [((G,), 3), ((), 5)] + [((F,), 10), ((), 4)] * 25),
    'tir_43':       (0x43, 0x40, 0x7F, {}, [((G,), 3), ((), 5)] + [((F,), 10), ((), 4)] * 25),
    'cible_43':     (0x43, 0x40, 0x7F, {}, [((G,), 3), ((), 5)] + [((F,), 10), ((), 6)] * 12),
    'panneau_44':   (0x44, 0x24, 0x7F, {0xB512: 0}, [((), 300), ((G,), 3), ((), 5)] + [((F,), 10), ((), 4)] * 15),
    'radiation_10': (0x10, 0x24, 0x7F, {0xB512: 0}, [((), 150)]),
    'radiation_14': (0x14, 0x24, 0x7F, {0xB512: 0}, [((), 150)]),
    'contact_44':   (0x44, 0x40, 0x7F, {}, [((), 300)]),
    'mort_0F':      (0x0F, 0x24, 0x57, {0xB4FB: 3}, [((), 300)]),
}
PIECES = {0xB519: 0, 0xB51A: 0xFF, 0xB51B: 0xFF, 0xB51C: 0xFF}
EN_ARMURE = {
    'armure_44':    (0x44, 0x24, 0x57, PIECES, [((), 30), ((H,), 20), ((), 60), ((G,), 40), ((), 100)]),
    'negateur_0F':  (0x0F, 0x24, 0x57, {**PIECES, 0xB51C: 0}, [((H,), 15), ((), 150), ((D,), 40)]),
    'messages_3E':  (0x3E, 0x24, 0x57, {0xB512: 0, 0xB519: 0xFF, 0xB51A: 0xFF, 0xB51B: 0xFF, 0xB51C: 0xFF},
                     [((H,), 5), ((), 200), ((H,), 3), ((), 150)]),
    'pulsar_3E':    (0x3E, 0x24, 0x57, {0xB512: 0, 0xB519: 0, 0xB51A: 0, 0xB51B: 0xFF, 0xB51C: 0xFF},
                     [((H,), 8), ((), 10), ((D,), 4), ((F,), 30), ((G,), 6), ((F, G), 40), ((), 40)]),
    'barriere_2E':  (0x2E, 0x28, 0x7F, PIECES, [((), 70), ((H,), 6), ((), 10), ((D,), 60), ((G,), 30), ((D,), 60)]),
}


# poses après l'entrée (adresse: valeur), pour amener des cibles devant Tal
POSES = {
    'cible_43': {W.o(2) + 0: 0, W.o(2) + 7: 0, W.o(2) + 3: 0x28, W.o(2) + 4: 0x60,
                 W.o(4) + 0: 0, W.o(4) + 7: 0, W.o(4) + 3: 0x14, W.o(4) + 4: 0x62},
}


def jouer(nom, salle, x, y, reglages, plan, armure=False, verbeux=False):
    c = TR.depart()
    avant = bytes(c.mem)
    TR.entrer(c, salle, x, y, reglages)
    modele = bytearray(avant)
    for a, v in reglages.items():
        modele[a] = v
    modele[W.SALLE] = salle
    W.entrer_salle(modele)
    modele[0xB403], modele[0xB404] = x, y
    e_entree = ecarts(modele, c.mem, actifs_seuls=True)
    if armure:
        TR.en_armure(c)
    for a, v in POSES.get(nom, {}).items():
        c.mem[a] = v
    paires = TR.tracer(c, plan, arret=lambda m: m[W.SALLE] != salle)
    pas, libre, hors, diverge = [], None, set(), None
    for i, (img, apres) in enumerate(paires):
        if apres[W.SALLE] != salle:
            break
        poignees = []
        deux_s = apres[0xB541] < img[0xB541]
        m, _ = avec_interruption(img, apres, lambda x: W.fin_de_tour(x, poignees))
        hors.update(p for p, _ in poignees)
        d = ecarts(m, apres)
        if d:
            pas.append((i, d))
        # en continu : Tal (objet 0, avant l'animateur) et les entrées viennent du jeu, le reste du modèle
        if libre is None:
            libre = bytearray(img)
        else:
            libre[W.OBJ:W.OBJ + W.TAILLE] = img[W.OBJ:W.OBJ + W.TAILLE]
            libre[0x7A4C] = img[0x7A4C]
            for a in list(range(0xB521, 0xB532)) + list(range(0xB53D, 0xB541)) + list(range(0x98AA, 0x98C0)):
                if img[a] != paires[i - 1][1][a]:                    # messages et rayon venus de la logique de Tal
                    libre[a] = img[a]
            for a in (0xB4F1, 0xB513, 0xB514, 0xB515, 0xB516, 0xB4FB, 0xB4FD, 0xB407, 0xB408, 0xB409, 0xB51D, 0xB51E, 0xB520, 0xB517, 0xB498):
                libre[a] = img[a]
            libre[W.ACTIFS] = (libre[W.ACTIFS] & 0xFE) | (img[W.ACTIFS] & 1)
        if i and img[W.A_PIED] == 0 and img[0xB519] == 0:            # tir de l'armure, dans sa logique (&5744)
            W.tir_pulsar(libre)
        if deux_s:
            W.toutes_les_deux_secondes(libre)
        W.fin_de_tour(libre)
        if diverge is None:
            d = ecarts(libre, apres)
            if d:
                diverge = (i, d)
        if verbeux:
            print('%3d actifs=%02X %s' % (i, apres[W.ACTIFS], ' '.join(
                '%d:%02X,%02X,%02X' % (n, apres[W.o(n) + 3], apres[W.o(n) + 4], apres[W.o(n) + 0xA])
                for n in range(8) if apres[W.ACTIFS] >> n & 1)))
    etats = sorted({img[W.o(n) + 0xA] & 0x7F for img, _ in paires for n in range(2, 8) if img[W.ACTIFS] >> n & 1})
    print('%-14s salle %02X, %3d tours, états %s : entrée %s, pas à pas %d écart(s), en continu %s%s' % (
        nom, salle, len(paires), ' '.join('%02X' % e for e in etats), 'identique' if not e_entree else e_entree[:4],
        len(pas), 'identique' if diverge is None else 'diverge au tour %d' % diverge[0],
        ' [poignées hors modèle : %s]' % ' '.join(map(str, sorted(hors))) if hors else ''))
    ev = couverture(paires, salle)
    print('   ' + ', '.join('%s %d' % kv for kv in ev.items() if kv[1]))
    for i, d in pas[:3]:
        print('   tour %d : %s' % (i, ', '.join(d[:8])))
    if diverge and not pas:
        print('   continu, tour %d : %s' % (diverge[0], ', '.join(diverge[1][:8])))
    return not e_entree and not pas and diverge is None


def couverture(paires, salle):
    from collections import Counter
    ev = Counter()
    for img, apres in paires:
        if apres[W.SALLE] != salle:
            break
        if apres[W.VIE_TAL] < img[W.VIE_TAL]: ev['vie perdue'] += 1
        if apres[W.ENERGIE_ARMURE] < img[W.ENERGIE_ARMURE]: ev['énergie perdue'] += 1
        if W.mot(apres, W.SCORE) > W.mot(img, W.SCORE): ev['points'] += 1
        for n in range(1, 8):
            b = W.o(n)
            if apres[b + 0x12] == 0xFF and img[b + 0x12] != 0xFF: ev['tués'] += 1
            if apres[W.ACTIFS] >> n & 1 and not img[W.ACTIFS] >> n & 1: ev['créés'] += 1
        if apres[W.o(1) + 0xA] & 0x7F == 0x2D and img[W.o(1) + 0xA] & 0x7F != 0x2D: ev['pierres arrêtées'] += 1
        if apres[W.REPIT] == 8: ev['répit'] += 1
        for k in apres[W.CONTACTS:W.CONTACTS + 6]:
            if k != 0xFF and apres[W.o(k) + 0xA] & 0x7F in (0x37, 0x38): ev['contacts barrière'] += 1
        if apres[0xB407] != img[0xB407] and apres[W.A_PIED] == 0: ev['rebonds armure'] += 1
        if apres[W.o(0) + 0xA] & 0x7F == 0x14 and img[W.o(0) + 0xA] & 0x7F != 0x14: ev['morts'] += 1
    return ev


def verif_tir():
    """&64EF (tir de l'armure) : image en &64EF, résultat au retour en &575E."""
    reglages = {0xB512: 0, 0xB519: 0, 0xB51A: 0, 0xB51B: 0xFF, 0xB51C: 0xFF}
    ok = True
    for nom, rg in (('rayon', reglages), ('rayon absent', dict(reglages, **{})) ):
        if nom == 'rayon absent':
            rg = {**reglages, 0xB51A: 0xFF}
        c = TR.depart(); TR.entrer(c, 0x3E, 0x24, 0x57, rg); TR.en_armure(c)
        plan = [((H,), 24), ((), 30), ((D,), 12), ((F,), 90), ((G,), 18), ((F, G), 120), ((F, D), 90)]
        paires = TR.tracer_entre(c, plan, 0x64EF, 0x575E)
        n = tirs = 0
        for img, apres in paires:
            m = bytearray(img)
            W.tir_pulsar(m)
            if not img[W.ACTIFS] & 2 and apres[W.ACTIFS] & 2: tirs += 1
            for a in list(range(W.OBJ, W.OBJ + 2 * W.TAILLE)) + [W.ACTIFS] + list(range(0x98AA, 0x98C0)):
                if m[a] != apres[a]:
                    n += 1
        print('%-14s %4d tours, %d tir(s) : %d écart(s)' % (nom, len(paires), tirs, n))
        ok = ok and n == 0
    return ok


def verif_mort():
    """&579C et &57D7 (mort et renaissance de Tal à pied) : image en &579C, résultat en &5792."""
    ok = True
    for nom, salle, reglages in (('mort', 0x0F, {0xB4FB: 3}), ('fin de partie', 0x0F, {0xB4FB: 3, 0xB551: 2})):
        c = TR.depart(); TR.entrer(c, salle, 0x24, 0x57, reglages)
        paires = TR.tracer_entre(c, [((), 900)], 0x579C, 0x5792)
        n, ev = 0, []
        for img, apres in paires:
            m = bytearray(img)
            r = W.mort_de_tal(m)
            if r and (not ev or ev[-1] != r):
                ev.append(r)
            for a in list(range(W.OBJ, W.OBJ + W.TAILLE)) + [0xB4FB, 0xB550, 0xB551]:
                if m[a] != apres[a]:
                    n += 1
        print('%-14s %4d tours, événements %s : %d écart(s)' % (nom, len(paires), ' '.join(ev), n))
        ok = ok and n == 0
    return ok


def verif_fin(nb_final=300, verbeux=False):
    """La fin de partie : la mine posée sur la cible de la salle &00, le compte à rebours qui défile, l'implosion
    (&5C31) et la boucle finale (&5CA6)."""
    rg = {0xB512: 0, 0xB519: 0, 0xB51A: 0, 0xB51B: 0, 0xB51C: 0}
    c = TR.depart(); TR.entrer(c, 0x00, 0x22, 0x50, rg); TR.en_armure(c)
    paires = TR.tracer(c, [((H,), 6), ((), 10), ((B,), 80)], arret=lambda m: m[W.ACTIFS] == 0)
    R, mem = c.R, c.mem
    c.keys = set()
    ecarts_tours, n_tours, avant, implosion_av, final, fin_modele = 0, 0, None, None, [], None
    # le tour du déclenchement (poignée 9) se vérifie comme les autres
    for img, apres in paires[-1:]:
        m, _ = avec_interruption(img, apres, W.fin_de_tour)
        ecarts_tours += len(ecarts(m, apres)); n_tours += 1
    while len(final) < nb_final + 1:
        pc = R[24]
        if pc == 0x5704:
            avant = bytes(mem)
        elif pc == 0x54FA and avant is not None:
            m, r = avec_interruption(avant, mem, W.fin_de_tour)
            d = ecarts(m, mem); ecarts_tours += len(d); n_tours += 1
            if d and verbeux: print('tour', n_tours, d[:5])
            avant = None
        elif pc == 0x5C31 and implosion_av is None:
            m, fin_modele = avec_interruption(avant, mem, W.fin_de_tour)
            t_imp = R[25]
            d = ecarts(m, mem); ecarts_tours += len(d); n_tours += 1
            if d and verbeux: print('déclenchement', d[:5])
            implosion_av = bytes(mem)
        elif pc == 0x5CA6:
            final.append(bytes(mem))
            if len(final) == 1:
                t_fin = R[25]
        c.run(1)
    m = bytearray(implosion_av); effaces = W.implosion(m)
    for _ in range((implosion_av[0xB541] + (t_fin - t_imp) // FRAME) // 100):   # interruptions pendant l'implosion
        W.toutes_les_deux_secondes(m)
    ecran = [a for a in range(0xC000, 0x10000) if m[a] != final[0][a]]
    d_imp = ecarts(m, final[0]) + ['écran %04X' % a for a in ecran]
    d_final = 0
    for a, b in zip(final, final[1:]):
        m, _ = avec_interruption(a, b, W.boucle_finale)
        d = ecarts(m, b); d_final += len(d)
        if d and verbeux: print('final', d[:5])
    print('fin de partie   %d tours jusqu’au déclenchement (%s), %d écart(s) ; implosion : %d octets effacés, %d écart(s) ; '
          'boucle finale %d tours, %d écart(s)' % (n_tours, fin_modele, ecarts_tours, len(set(effaces)), len(d_imp), nb_final, d_final))
    return not ecarts_tours and not d_imp and not d_final and fin_modele == 'fin'


if __name__ == '__main__':
    TOUS = dict(SCENARIOS, **{k: v + (True,) for k, v in EN_ARMURE.items()})
    noms = [a for a in sys.argv[1:] if not a.startswith('-')] or list(TOUS)
    ok = all([jouer(n, *TOUS[n], verbeux='-v' in sys.argv) for n in noms])
    if len(noms) == len(TOUS) or 'mort' in sys.argv:
        ok = verif_mort() and ok
        ok = verif_tir() and ok
        ok = verif_fin() and ok
    print('TOUT CONCORDE' if ok else 'DES ÉCARTS RESTENT')
