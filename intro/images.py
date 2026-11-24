"""Les deux images du chargeur CNGSoft, rendues depuis la mémoire relevée par chargeur.py.

logo_cngsoft.png       image 1 : mode 0, overscan (R1=48 mots = 96 octets par ligne, R6=34 rangs = 272 lignes),
                       10 encres posées par le firmware ; l'image ne tient que dans 16 Ko : à partir de
                       la 22e rangée, le CRTC relit le début du bloc (voir INTRO.md)
ecran_chargement.png   image 2 : mode 2 (640 x 200, deux couleurs), bleu foncé et blanc

Usage : python3 images.py   (après chargeur.py)
"""
import os, pickle
import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
# couleurs du firmware 0-26
FW = [(0, 0, 0), (0, 0, 128), (0, 0, 255), (128, 0, 0), (128, 0, 128), (128, 0, 255), (255, 0, 0), (255, 0, 128),
      (255, 0, 255), (0, 128, 0), (0, 128, 128), (0, 128, 255), (128, 128, 0), (128, 128, 128), (128, 128, 255),
      (255, 128, 0), (255, 128, 128), (255, 128, 255), (0, 255, 0), (0, 255, 128), (0, 255, 255), (128, 255, 0),
      (128, 255, 128), (128, 255, 255), (255, 255, 0), (255, 255, 128), (255, 255, 255)]
# encres de l'image 1 : SCR_SET_INK (&BC32) appelé par le chargeur pour les stylos 0 à 9, bordure 1
ENCRES_1 = [1, 0, 2, 3, 6, 11, 15, 20, 24, 26]


def mode0(b):
    p0 = ((b >> 7) & 1) | (((b >> 3) & 1) << 1) | (((b >> 5) & 1) << 2) | (((b >> 1) & 1) << 3)
    p1 = ((b >> 6) & 1) | (((b >> 2) & 1) << 1) | (((b >> 4) & 1) << 2) | ((b & 1) << 3)
    return p0, p1


def adresse(ma, ra, k):
    """Adresse vue par le Gate Array : MA13-12 -> bloc de 16 Ko, RA -> bits 11-13, MA9-0 -> mot.
    MA10 et MA11 ne servent pas : un débordement au-delà de 1024 mots revient au début du bloc."""
    return ((ma & 0x3000) << 2) | (ra << 11) | ((ma & 0x3FF) << 1) | k


def logo(img1, r1=48, r6=34):
    mem = np.zeros(65536, np.uint8); mem[0xC000:] = img1
    im = np.zeros((r6 * 8, r1 * 2 * 2, 3), np.uint8)
    pal = np.array([FW[c] for c in ENCRES_1] + [FW[0]] * 6, np.uint8)
    for rang in range(r6):
        for ra in range(8):
            y = rang * 8 + ra
            for col in range(r1):
                ma = 0x3000 + rang * r1 + col
                for k in range(2):
                    p0, p1 = mode0(int(mem[adresse(ma, ra, k)]))
                    x = (col * 2 + k) * 2
                    im[y, x] = pal[p0]; im[y, x + 1] = pal[p1]
    return np.repeat(im, 4, 1)          # pixels de mode 0 : 4 fois plus larges que ceux du mode 2


def chargement(img2, fond=(0, 0, 128), encre=(128, 128, 128)):
    e = np.array(img2, np.uint8)
    im = np.zeros((200, 640, 3), np.uint8)
    for y in range(200):
        a = (y % 8) * 0x800 + (y // 8) * 80
        bits = np.unpackbits(e[a:a + 80])
        im[y] = np.where(bits[:, None] == 1, np.array(encre, np.uint8), np.array(fond, np.uint8))
    return im


if __name__ == "__main__":
    o = pickle.load(open(os.path.join(ICI, "chargeur.pkl"), "rb"))
    a = logo(o["img1"])
    Image.fromarray(np.repeat(a, 2, 0)).save(os.path.join(ICI, "logo_cngsoft.png"))
    b = chargement(o["img2"])
    Image.fromarray(np.repeat(b, 2, 0)).save(os.path.join(ICI, "ecran_chargement.png"))
    print("logo", a.shape, "chargement", b.shape)
