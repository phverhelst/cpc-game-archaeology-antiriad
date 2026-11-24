"""Le rideau du chargeur CNGSoft (&0251-&02B7), transcrit en Python.

Le modèle rejoue la boucle image par image avec les durées réelles du CPC, où chaque
instruction est étirée à un multiple de 4 T-states (1 µs, une « NOP »). Il produit la
liste des écritures vers le Gate Array, horodatées en µs depuis le début de la VSYNC.

Vérification : la suite des valeurs écrites et la suite des positions D doivent être
identiques à celles de l'émulateur (chargeur.py). L'horodatage, lui, ne peut pas être
comparé tel quel : l'émulateur compte les T-states du Z80 nu, sans l'étirement du CPC.

Rendu : chaque trame est reconstituée ligne par ligne et caractère par caractère
(1 µs = 1 caractère CRTC = 2 octets = 16 pixels en mode 2), bordures comprises.

  python3 rideau.py            vérifie, puis écrit rideau_*.png et rideau.gif
"""
import os, pickle
import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
LIGNE = 64            # µs par ligne
TRAME = 312 * LIGNE   # 19968 µs
VSYNC = 8 * LIGNE     # largeur de VSYNC programmée par le firmware (R3=&8E)
HAUT = 72             # lignes entre le début de la VSYNC et la 1re ligne affichée
                      # (VSYNC au rang R7=30 : 30*8=240 ; 312-240 = 72)

# Couleurs matérielles du Gate Array (valeur & &1F) -> RVB, palette CPC usuelle
HW = {0x00: (128, 128, 128), 0x04: (0, 0, 128), 0x0B: (255, 255, 255),
      0x14: (0, 0, 0)}


def rgb(v):
    return HW.get(v & 0x1F, (255, 0, 255))


# ---------------------------------------------------------------------------
# Le modèle
# ---------------------------------------------------------------------------
def rideau(D=1, IX=1, E=0x44, H=0xC0, L=0x40, Calt=None, t=0):
    """Rejoue la boucle à partir de &0281 (premier passage).

    t : instant (µs) d'entrée en &0281, compté depuis un début de VSYNC.
    Calt : contenu de C' (l'ombre du registre de mode tenue par le firmware) ;
    None = non connu, on écrit alors 'C\''.
    Retourne (écritures, positions D) ; écritures = [(t, valeur)].
    """
    w = []
    Ds = []

    def out(at, v):
        w.append((at, v))

    def bande(s, A):
        """CALL &0253 avec A ; s = instant du CALL. Retourne l'instant après le RET."""
        s += 5                      # CALL
        out(s + 3 + 3, 0x8E)        # LD BC,&7F8E (3) ; OUT (C),C : mode 2, ROM coupées
        s += 7
        out(s + 3 + 3, 0x00)        # LD BC,&7F01 (3) ; OUT (C),0 : stylo 0
        out(s + 7 + 3, A)           # OUT (C),A : couleur du stylo 0
        out(s + 11 + 3, 0x01)       # OUT (C),C : stylo 1
        out(s + 15 + 3, A)          # OUT (C),A
        out(s + 21 + 3, 0x10)       # LD C,&10 (2) ; OUT (C),C : bordure
        out(s + 25 + 3, A)          # OUT (C),A
        return s + 29 + 2 + 19 * 4 + 3 + 3   # LD B,&14 ; DJNZ x20 ; RET

    def attendre_vsync(s):
        """&0285 : LD B,&F5 puis deux boucles IN/RRCA/JR de 8 µs.
        L'échantillon du port est pris à la 4e µs du IN."""
        s += 2
        while not ((s + 3) % TRAME < VSYNC):      # attendre VSYNC active
            s += 8
        s += 7
        while (s + 3) % TRAME < VSYNC:            # attendre sa fin
            s += 8
        return s + 7

    def montrer(s):
        """&0291-&02A0 : rétablir l'image (stylo 0 = E, stylo 1 = L)."""
        s += 3 + 1                  # LD BC,&7F01 ; EXX
        out(s + 3, Calt if Calt is not None else "C'")
        s += 4 + 1                  # OUT (C),C' ; EXX
        out(s + 3, E); s += 4       # la dernière sélection était la bordure
        out(s + 3, 0x01); s += 4
        out(s + 3, L); s += 4
        out(s + 3, 0x00); s += 4
        out(s + 3, H); s += 4       # H=&C0 : configuration mémoire standard, sans effet
        return s

    # entrée en &0281
    s = t + 1                       # LD A,E
    s = bande(s, E)
    while True:
        s = attendre_vsync(s)
        s = montrer(s)
        IX = (IX + 1) & 255; s += 2
        a = D + IX; D = a & 255; s += 1 + 2 + 1
        if a < 256:
            s += 3
        else:
            s += 2 + 2 + 1          # JR NC non pris ; LD A,IXl ; ADD A,A
            if IX * 2 > 255:
                s += 3
            else:
                s += 2 + 2 + 1 + 1 + 2     # JR C non pris ; LD D,&FF ; RRCA ; CPL ; ADD
                D = 255
                a = ((~IX) & 255) + 4
                IX = a & 255; s += 2
                if a > 255:
                    return w, Ds, s        # sortie : l'image reste affichée
                s += 3
        # &026E : temporisation proportionnelle à D
        Ds.append(D)
        s += 1 + 73 * D - 1
        s = bande(s + 2, 0x40)      # &0276 : CALL &0251 (LD A,&40)
        s = bande(s + 2, 0x4B)      # &0279 : LD A,&4B
        s = bande(s + 2, 0x40)      # &027E
        s = bande(s + 1, E)         # &0281 : LD A,E


# ---------------------------------------------------------------------------
# Vérification contre l'émulateur
# ---------------------------------------------------------------------------
def verifier():
    o = pickle.load(open(os.path.join(ICI, "chargeur.pkl"), "rb"))
    r = o["regs"]
    Calt = None
    w, Ds, fin = rideau(D=r[4], IX=r[9], E=r[5], H=r[6], L=r[7], Calt=Calt)
    # Dans l'émulateur, B'C' vaut 0 (le firmware n'a pas tourné pour de vrai) :
    # le OUT (C),C' part vers le port &0000 et n'apparaît pas dans le journal du
    # Gate Array. On l'écarte donc de la comparaison.
    emu = [v for _, v in o["journal"]]
    mod = [v for _, v in w if v != "C'"]
    ok_v = emu == mod
    ok_d = Ds == o["D"]
    print("écritures Gate Array : émulateur %d, modèle %d -> %s"
          % (len(emu), len(mod), "identiques" if ok_v else "DIFFÉRENTES"))
    print("positions D : %d trames -> %s" % (len(Ds), "identiques" if ok_d else "DIFFÉRENTES"))
    return ok_v and ok_d


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------
BORD_V = 32           # lignes de bordure visibles en haut et en bas
BORD_H = 4            # caractères (µs) de bordure visibles à gauche et à droite


def trames(w, img2, n_fin=50):
    """Découpe le journal en trames (de VSYNC à VSYNC) et rend chacune."""
    # état des couleurs : stylo 0, stylo 1, bordure, mode
    etat = {"sel": 0, 0: 0x44, 1: 0x44, 0x10: 0x44}
    ev = sorted(w, key=lambda x: x[0])
    t0 = 0
    fin = ev[-1][0]
    i = 0
    images = []
    mem = np.array(img2, dtype=np.uint8)
    # pixels mode 2 : bit -> stylo
    bits = np.unpackbits(mem).reshape(-1, 8)
    while t0 <= fin + n_fin * TRAME:
        H = 200 + 2 * BORD_V
        W = (40 + 2 * BORD_H) * 16
        im = np.zeros((H, W, 3), np.uint8)
        for y in range(H):
            ligne = HAUT - BORD_V + y
            for c in range(-BORD_H, 40 + BORD_H):
                t = t0 + ligne * LIGNE + c
                while i < len(ev) and ev[i][0] <= t:
                    _, v = ev[i]; i += 1
                    if isinstance(v, str):
                        continue
                    if v < 0x40:
                        etat["sel"] = 0x10 if v & 0x10 else v & 0x0F
                    elif v < 0x80:
                        etat[etat["sel"]] = v
                x = (c + BORD_H) * 16
                yy = y - BORD_V
                if 0 <= yy < 200 and 0 <= c < 40:
                    a = (yy % 8) * 0x800 + (yy // 8) * 80 + c * 2
                    px = np.concatenate([bits[a], bits[a + 1]])
                    col = np.array([rgb(etat[0]), rgb(etat[1])], np.uint8)
                    im[y, x:x + 16] = col[px]
                else:
                    im[y, x:x + 16] = rgb(etat[0x10])
        images.append(im)
        t0 += TRAME
    return images


if __name__ == "__main__":
    ok = verifier()
    o = pickle.load(open(os.path.join(ICI, "chargeur.pkl"), "rb"))
    r = o["regs"]
    w, Ds, fin = rideau(D=r[4], IX=r[9], E=r[5], H=r[6], L=r[7], Calt=0x8E)
    print("durée : %d trames, soit %.2f s à 50 Hz" % (len(Ds) + 1, (len(Ds) + 1) / 50))
    print("rebonds (sommets de D) :", [Ds[k] for k in range(1, len(Ds) - 1)
                                       if Ds[k] <= Ds[k - 1] and Ds[k] < Ds[k + 1]])
    ims = trames(w, o["img2"], n_fin=10)
    pickle.dump(ims, open("/tmp/rideau_trames.pkl", "wb"))
    for k in (15, 40, 175):
        Image.fromarray(ims[k]).save(os.path.join(ICI, "rideau_%03d.png" % k))
    gif = [Image.fromarray(im).resize((im.shape[1] // 2, im.shape[0])) for im in ims]
    gif[0].save(os.path.join(ICI, "rideau.gif"), save_all=True, append_images=gif[1:],
                duration=20, loop=0)
    print("ok" if ok else "ÉCART")
