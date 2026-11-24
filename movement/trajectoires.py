"""Trajectoires de Tal calculées par le modèle, sur un sol plat sans obstacle.

Écrit trajectoires.png (si Pillow est présent) et imprime les chiffres : hauteur, durée, portée.
"""
import os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import tal as M

SOL = 0x9A                                   # une ligne de rang 2 (0x9A & 7 == 2)


class SolPlat:
    def octet(self, ligne, colonne):
        return 0x44 if ligne == SOL else 0x00  # 0x44 : pixel droit reconnu par le motif &8E1C


def depart(face_droite=False):
    t = M.Tal(x=0x20, y=SOL - 0x2A - 1, etat=0x8B if face_droite else 0x82,
              sprite=0x88 if face_droite else 0x08, dirs=M.DESCEND)
    return t


def simuler(t, entrees, n=60):
    e, pts = SolPlat(), []
    for i in range(n):
        joy = entrees(i)
        M.tour(t, joy, e)
        pts.append((t.x, t.y, t.e))
    return pts


def resume(nom, pts, y0):
    en_l_air = [i for i, (_, _, e) in enumerate(pts) if e in (0x07, 0x08, 0x10, 0x11)]
    if not en_l_air:
        print(nom, ': pas de saut'); return
    a, b = en_l_air[0], en_l_air[-1]
    haut = y0 - min(y for _, y, _ in pts)
    print('%-28s hauteur %2d lignes, en l\'air %2d tours, portée %2d octets (%d pixels mode 0), '
          'retour à la station debout %d tours après l\'atterrissage' % (nom, haut, b - a + 1, pts[b][0] - pts[a][0] if pts[b][0] >= pts[a][0]
                                                else pts[a][0] - pts[b][0], 2 * abs(pts[b][0] - pts[a][0]),
                                                next((i for i, (_, _, e) in enumerate(pts[b + 1:]) if e in (0x02, 0x0B)), -1) + 1))


def main():
    cas = {
        'saut vertical':          (False, lambda i: M.HAUT if i == 0 else 0),
        'saut de pied ferme (dr.)': (True, lambda i: M.HAUT | M.DROITE | M.FEU if i == 0 else 0),
        'saut en course (droite)': (True, lambda i: M.DROITE | (M.FEU if i == 6 else 0)),
        'chute depuis la marche':  (True, lambda i: M.DROITE),
    }
    res = {}
    for nom, (d, f) in cas.items():
        t = depart(d)
        y0 = t.y
        pts = simuler(t, f)
        res[nom] = pts
        if nom != 'chute depuis la marche':
            resume(nom, pts, y0)
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    # Proportions de l'écran d'origine : un octet (2 pixels mode 0) est à peu près 4 fois plus large
    # qu'une ligne n'est haute. Échelle : 8 pixels d'image par octet, 2 par ligne.
    OX, OY, x0 = 8, 2, 0x18
    W, H = 48 * OX, 70 * OY
    img = Image.new('RGB', (W, H), (16, 16, 24))
    d = ImageDraw.Draw(img)
    couleurs = [(240, 200, 80), (120, 220, 120), (120, 170, 255)]
    base = SOL - 0x2A - 1
    sol_y = H - 10 * OY
    d.line([(0, sol_y), (W, sol_y)], fill=(60, 160, 60), width=2)
    for c, nom in zip(couleurs, ['saut vertical', 'saut de pied ferme (dr.)', 'saut en course (droite)']):
        pts = [((x - x0) * OX, sol_y - (base - y) * OY) for x, y, _ in res[nom]]
        d.line(pts, fill=c, width=2)
        for p in pts:
            d.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], outline=c)
    img.save(os.path.join(ICI, 'trajectoires.png'))
    print('trajectoires.png écrit (un point par tour ; abscisse en pixels mode 0, ordonnée en lignes)')


if __name__ == '__main__':
    main()
