"""Gravure de la partition de la musique du titre, en SVG puis en PDF (rsvg-convert).

Un graveur volontairement simple : trois portées par système (voix 1 et 2 en clé de sol, voix 3 en clé de fa),
ligatures à l'intérieur de chaque temps, liaisons de tenue, altérations accidentelles valables jusqu'à la barre de
mesure, percussions (bruit du AY) en têtes en croix. Les glyphes de clés et de silences viennent de la police
FreeSerif (bloc Unicode des symboles musicaux).
Usage : python3 gravure.py [mesures] [sortie.pdf]
"""
import math, os, subprocess, sys
import musique as M
import partition as P

ICI = os.path.dirname(os.path.abspath(__file__))
S = 6.5                       # interligne (points)
LARGEUR, HAUTEUR = 595, 842
MARGE_G, MARGE_D, HAUT = 46, 28, 96
ECART_PORTEES, ECART_SYSTEMES = 68, 58
MESURES_PAR_SYSTEME = 4
CLES = ['sol', 'sol', 'fa']
NOMS_VOIX = ['Voix 1', 'Voix 2', 'Voix 3']
BAS = {'sol': M.diatonique('E', 4), 'fa': M.diatonique('G', 2)}         # ligne du bas de la portée
MILIEU = {'sol': M.diatonique('B', 4), 'fa': M.diatonique('D', 3)}
PERC = {'grave': M.diatonique('F', 4), 'moyen': M.diatonique('C', 5), 'aigu': M.diatonique('G', 5)}
POLICE = "font-family='FreeSerif'"
GLYPHE_SILENCE = {24: '\U0001D13C', 16: '\U0001D13C', 12: '\U0001D13D', 8: '\U0001D13D', 6: '\U0001D13E', 4: '\U0001D13E',
                  3: '\U0001D13F', 2: '\U0001D13F', 1: '\U0001D140'}


def perc_position(periode, cle):
    if cle == 'fa':
        return {'grave': M.diatonique('A', 2), 'moyen': M.diatonique('E', 3), 'aigu': M.diatonique('B', 3)}[
            'aigu' if periode < 6 else 'moyen' if periode < 20 else 'grave']
    return PERC['aigu' if periode < 6 else 'moyen' if periode < 20 else 'grave']


class Page:
    def __init__(self):
        self.el = []

    def ligne(self, x1, y1, x2, y2, l=0.7):
        self.el.append("<line x1='%.2f' y1='%.2f' x2='%.2f' y2='%.2f' stroke='#000' stroke-width='%.2f'/>" % (x1, y1, x2, y2, l))

    def texte(self, x, y, t, taille=10, style='', ancre='start'):
        self.el.append("<text x='%.2f' y='%.2f' font-size='%.1f' text-anchor='%s' %s>%s</text>" % (x, y, taille, ancre, style or "font-family='DejaVu Serif'", t))

    def tete(self, x, y, creuse):
        if creuse:
            self.el.append("<ellipse cx='%.2f' cy='%.2f' rx='%.2f' ry='%.2f' transform='rotate(-25 %.2f %.2f)' fill='none' stroke='#000' stroke-width='1.1'/>" % (x, y, S * 0.55, S * 0.36, x, y))
        else:
            self.el.append("<ellipse cx='%.2f' cy='%.2f' rx='%.2f' ry='%.2f' transform='rotate(-25 %.2f %.2f)' fill='#000'/>" % (x, y, S * 0.6, S * 0.42, x, y))

    def croix(self, x, y):
        d = S * 0.45
        self.ligne(x - d, y - d, x + d, y + d, 1.1); self.ligne(x - d, y + d, x + d, y - d, 1.1)

    def arc(self, x1, x2, y, haut):
        h = -S * 0.9 if haut else S * 0.9
        dy = -S * 0.45 if haut else S * 0.45
        self.el.append("<path d='M%.2f %.2f Q%.2f %.2f %.2f %.2f' fill='none' stroke='#000' stroke-width='0.9'/>" % (x1, y + dy, (x1 + x2) / 2, y + dy + h, x2, y + dy))

    def crochets(self, x, y, n, haut):
        for k in range(n):
            yy = y + (k * S * 0.8 if haut else -k * S * 0.8)
            if haut:
                self.el.append("<path d='M%.2f %.2f q %.2f %.2f %.2f %.2f' fill='none' stroke='#000' stroke-width='1.3'/>" % (x, yy, S * 1.2, S * 0.9, S * 0.7, S * 2.2))
            else:
                self.el.append("<path d='M%.2f %.2f q %.2f %.2f %.2f %.2f' fill='none' stroke='#000' stroke-width='1.3'/>" % (x, yy, S * 1.2, -S * 0.9, S * 0.7, -S * 2.2))

    def svg(self):
        return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'><rect width='100%%' height='100%%' fill='#fff'/>%s</svg>"
                % (LARGEUR, HAUTEUR, LARGEUR, HAUTEUR, ''.join(self.el)))


def positions(mesure_voix, a, L, x0, x1):
    """Abscisse de chaque position de la mesure, espacée selon les durées (comme le ferait un graveur)."""
    debuts = sorted({f['pos'] for v in mesure_voix for f in v} | {0, L})
    poids = []
    for i in range(len(debuts) - 1):
        g = debuts[i + 1] - debuts[i]
        poids.append(1.0 + 1.1 * math.sqrt(g))
    tot = sum(poids)
    xs, x = {}, x0
    for i, p in enumerate(debuts[:-1]):
        xs[p] = x
        x += poids[i] / tot * (x1 - x0)
    xs[L] = x1
    return xs


def graver(nb_mesures, sortie):
    m = P.memoire()
    voix, tempos_tous = [], []
    for son in (1, 2, 3):
        evs, tempos, total = M.evenements(m, son)
        ms, res = M.voix_en_mesures(evs, total)
        voix.append(res); tempos_tous += tempos
    nb = min(nb_mesures, len(ms))
    besoin = []                                                      # largeur souhaitée de chaque mesure
    for i in range(nb):
        debuts = {f['pos'] for k in range(3) for f in voix[k][i]}
        besoin.append(26 + 8.5 * len(debuts) + (12 if i and ms[i - 1][1] != ms[i][1] else 0))
    systemes, i = [], 0
    while i < nb:                                                    # coupure des systèmes : on remplit la ligne
        dispo = LARGEUR - MARGE_D - MARGE_G - (60 if i == 0 else 42)
        j, tot = i, 0
        while j < nb and (j == i or tot + besoin[j] <= dispo) and j - i < 5:
            tot += besoin[j]; j += 1
        systemes.append((i, j)); i = j
    pages, page, y_sys = [], None, None
    systeme = 0
    for debut, fin in systemes:
        hauteur_sys = 2 * ECART_PORTEES + 4 * S
        if page is None or y_sys + hauteur_sys > HAUTEUR - 40:
            page = Page(); pages.append(page)
            y_sys = HAUT if len(pages) == 1 else 50
            if len(pages) == 1:
                page.texte(LARGEUR / 2, 42, "Antiriad — musique du titre (Amstrad CPC)", 17, ancre='middle')
                page.texte(LARGEUR - MARGE_D, 62, "Relevée dans le code du jeu (sons 1, 2, 3 ; pilote &amp;755E), boucle complète : 2 118 triples croches, 115,6 s", 8.5,
                           "font-family='DejaVu Serif' font-style='italic'", 'end')
                page.texte(LARGEUR - MARGE_D, 74, "Palace Software, 1986 — musique de Richard Joseph", 8.5,
                           "font-family='DejaVu Serif' font-style='italic'", 'end')
            page.texte(LARGEUR / 2, HAUTEUR - 18, str(len(pages)), 9, ancre='middle')
        tete = 60 if debut == 0 else 42
        x_debut = MARGE_G + tete
        dispo = LARGEUR - MARGE_D - x_debut
        plein = sum(besoin[debut:fin]) > 0.6 * dispo or fin < nb
        echelle = dispo / sum(besoin[debut:fin]) if plein else 1
        bords = [x_debut]
        for i in range(debut, fin):
            bords.append(bords[-1] + besoin[i] * echelle)
        ys = [y_sys + k * ECART_PORTEES for k in range(3)]
        for k, y in enumerate(ys):                                   # portées, clés, armure
            for l in range(5):
                page.ligne(MARGE_G, y + l * S, bords[-1], y + l * S, 0.6)
            if CLES[k] == 'sol':
                page.texte(MARGE_G + 2, y + 4 * S + 2.5, '\U0001D11E', 4.6 * S, "font-family='FreeSerif'")
            else:
                page.texte(MARGE_G + 2, y + 3 * S + 1.0, '\U0001D122', 3.9 * S, "font-family='FreeSerif'")
            for i, lettre in enumerate(['B', 'E']):                  # si♭, mi♭
                oc = (4 if lettre == 'B' else 5) if CLES[k] == 'sol' else (2 if lettre == 'B' else 3)
                d = M.diatonique(lettre, oc)
                yy = y + 4 * S - (d - BAS[CLES[k]]) * S / 2
                page.texte(MARGE_G + 26 + i * 7, yy + 3, '♭', 2.2 * S, "font-family='DejaVu Sans'")
            if debut == 0:
                page.texte(MARGE_G + 50, y + 1.9 * S, '3', 2 * S, "font-family='DejaVu Serif' font-weight='bold'", 'middle')
                page.texte(MARGE_G + 50, y + 3.9 * S, '4', 2 * S, "font-family='DejaVu Serif' font-weight='bold'", 'middle')
                page.texte(MARGE_G - 4, y + 2.6 * S, NOMS_VOIX[k], 6.5, "font-family='DejaVu Sans'", 'end')
        page.ligne(MARGE_G, ys[0], MARGE_G, ys[2] + 4 * S, 1.0)
        page.texte(MARGE_G - 4, ys[0] - 6, str(debut + 1), 7.5, "font-family='DejaVu Serif' font-style='italic'", 'end')
        for i in range(debut, fin):
            a, L = ms[i]
            x0, x1 = bords[i - debut], bords[i - debut + 1]
            for y in ys:
                page.ligne(x1, y, x1, y + 4 * S, 0.8)
            for (tt, v) in tempos_tous:
                if a <= tt < a + L:
                    reel = M.tempo_reel(v)
                    page.texte(x0 + 4, ys[0] - 10, '♩ = %d' % round(reel) + ('' if round(reel) == v else '  (commande : %d)' % v), 9.5,
                               "font-family='DejaVu Sans' font-weight='bold'")
            change = i > 0 and ms[i - 1][1] != L and i != debut or (i == debut and i > 0 and ms[i - 1][1] != L)
            if change:                                               # changement de mesure
                h, b = M.chiffrage(L)
                for y in ys:
                    page.texte(x0 + 7, y + 1.9 * S, str(h), 2 * S, "font-family='DejaVu Serif' font-weight='bold'", 'middle')
                    page.texte(x0 + 7, y + 3.9 * S, str(b), 2 * S, "font-family='DejaVu Serif' font-weight='bold'", 'middle')
                x0 += 12
            xs = positions([voix[k][i] for k in range(3)], a, L, x0 + 9, x1 - 7)
            for k in range(3):
                dessiner_mesure(page, voix[k][i], xs, ys[k], CLES[k])
        # liaisons d'une mesure à l'autre (et d'un système au suivant : demi-arc)
        y_sys += hauteur_sys + ECART_SYSTEMES
        systeme += 1
    fichiers = []
    for n, pg in enumerate(pages):
        f = '/tmp/antiriad_partition_%02d.svg' % n
        open(f, 'w').write(pg.svg()); fichiers.append(f)
    subprocess.run(['rsvg-convert', '-f', 'pdf', '-o', sortie] + fichiers, check=True)
    return fichiers


LIEES = {}


def dessiner_mesure(page, figures, xs, y, cle):
    """Dessine les figures d'une voix dans une mesure : têtes, altérations, lignes supplémentaires, points,
    liaisons, et ligatures des croches et doubles croches à l'intérieur de chaque temps."""
    bas, milieu = BAS[cle], MILIEU[cle]
    alt_mesure = {}
    ypos = lambda d: y + 4 * S - (d - bas) * S / 2
    geo = []                                                         # figures à tige : géométrie, pour les ligatures
    for f in figures:
        x = xs[f['pos']]
        val = f['val']
        typ, points = M.TYPES[val]
        if f['genre'] == 'silence':
            yy = y + 2 * S
            if val in (24, 16):
                page.el.append("<rect x='%.2f' y='%.2f' width='%.2f' height='%.2f' fill='#000'/>" % (x - 2, y + 1.5 * S, S * 0.9, S * 0.5))
            else:
                page.texte(x - 2, yy + (0.8 * S if val >= 8 else 0.9 * S), GLYPHE_SILENCE[val], 3.4 * S, "font-family='FreeSerif'")
            if points:
                page.el.append("<circle cx='%.2f' cy='%.2f' r='1.1'/>" % (x + 7, y + 1.5 * S))
            geo.append(None)
            continue
        if f['genre'] == 'perc':
            d = perc_position(f['valeur'], cle)
            yy = ypos(d)
            page.croix(x, yy)
            if points:
                page.el.append("<circle cx='%.2f' cy='%.2f' r='1.1'/>" % (x + S * 1.2, yy - S * 0.3))
            geo.append({'f': f, 'x': x, 'y': yy, 'd': d, 'n': {'eighth': 1, '16th': 2, '32nd': 3}.get(typ, 0), 'perc': True})
            continue
        lettre, alt, octave = M.orthographe(f['valeur'])
        d = M.diatonique(lettre, octave)
        ottava = 0                                                    # trop loin de la portée : à l'octave, signalé
        if d > bas + 8 + 5:
            d -= 7; ottava = 1
        elif d < bas - 6:
            d += 7; ottava = -1
        yy = ypos(d)
        if ottava:
            page.texte(x, (yy - 2.2 * S) if ottava > 0 else (yy + 3.2 * S), '8va' if ottava > 0 else '8vb', 5.5,
                       "font-family='DejaVu Serif' font-style='italic'", 'middle')
        cle_alt = M.CLE.get(lettre, 0)
        attendu = alt_mesure.get(d, cle_alt)
        if alt != attendu:
            page.texte(x - S * 1.45, yy + 3, {1: '♯', -1: '♭', 0: '♮'}[alt], 2.1 * S, "font-family='DejaVu Sans'", 'middle')
            alt_mesure[d] = alt
        for dd in range(bas - 2, d - 1, -2):                         # lignes supplémentaires
            page.ligne(x - S * 0.95, ypos(dd), x + S * 0.95, ypos(dd), 0.8)
        for dd in range(bas + 10, d + 1, 2):
            page.ligne(x - S * 0.95, ypos(dd), x + S * 0.95, ypos(dd), 0.8)
        page.tete(x, yy, typ == 'half')
        if points:
            page.el.append("<circle cx='%.2f' cy='%.2f' r='1.15'/>" % (x + S * 1.25, yy - (S / 2 if (d - bas) % 2 == 0 else 0)))
        if f['lie']:
            suivantes = [g for g in figures if g['pos'] > f['pos']]
            x2 = xs[suivantes[0]['pos']] if suivantes else max(xs.values()) + 6
            page.arc(x + S * 0.5, x2 - S * 0.5, yy, d >= milieu)
        geo.append({'f': f, 'x': x, 'y': yy, 'd': d, 'n': {'eighth': 1, '16th': 2, '32nd': 3}.get(typ, 0), 'perc': False})
    # groupes ligaturés : figures brèves consécutives d'un même temps (8 unités)
    groupes, courant = [], []
    for g in geo:
        if g and g['n'] and courant and g['f']['pos'] // 8 == courant[-1]['f']['pos'] // 8 and \
                courant[-1]['f']['pos'] + courant[-1]['f']['val'] == g['f']['pos']:
            courant.append(g); continue
        if courant:
            groupes.append(courant)
        courant = [g] if g and g['n'] else []
        if g and not g['n']:
            groupes.append([g])
    if courant:
        groupes.append(courant)
    for grp in groupes:
        haut = all(g['perc'] for g in grp) or sum(g['d'] for g in grp) / len(grp) < milieu
        dx = S * 0.55 if haut else -S * 0.55
        if len(grp) == 1:
            g = grp[0]
            xt = g['x'] + (S * 0.45 if g['perc'] else dx)
            bout = g['y'] - 3.5 * S if haut else g['y'] + 3.5 * S
            page.ligne(xt, g['y'], xt, bout, 0.8)
            if g['n']:
                page.crochets(xt, bout, g['n'], haut)
            continue
        ext = min(g['y'] for g in grp) - 3.3 * S if haut else max(g['y'] for g in grp) + 3.3 * S
        xts = [g['x'] + (S * 0.45 if g['perc'] else dx) for g in grp]
        for g, xt in zip(grp, xts):
            page.ligne(xt, g['y'], xt, ext, 0.8)
        for niveau in range(1, 4):                                   # une barre par niveau de brièveté
            yb = ext + (niveau - 1) * S * 0.75 * (1 if haut else -1)
            k = 0
            while k < len(grp):
                if grp[k]['n'] < niveau:
                    k += 1; continue
                j = k
                while j + 1 < len(grp) and grp[j + 1]['n'] >= niveau:
                    j += 1
                if j > k:
                    xa, xb = xts[k], xts[j]
                else:                                                # barre partielle vers la voisine
                    xa = xts[k]
                    xb = xa + (S * 1.1 if k == 0 else -S * 1.1)
                page.el.append("<line x1='%.2f' y1='%.2f' x2='%.2f' y2='%.2f' stroke='#000' stroke-width='%.2f'/>" %
                               (min(xa, xb) - 0.4, yb, max(xa, xb) + 0.4, yb, S * 0.42))
                k = j + 1


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    sortie = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ICI, 'antiriad_titre_cpc.pdf')
    f = graver(n, sortie)
    print(sortie, len(f), 'page(s)')
