"""Monte intro.mp4 : la séquence d'ouverture de la version disque CNGSoft, telle que le chargeur la produit,
puis l'écran titre du jeu avec sa musique.

Déroulé (durées : HALT comptés à 300 Hz, décompressions en temps Z80 nu mesuré par chargeur.py,
un peu plus longues sur la machine réelle) :
  logo CNGSoft en overscan        3,00 s   (225 x 4 HALT)
  écran éteint (R6=0), bordure noire, décompression de l'image 2
  rideau qui tombe et rebondit    3,52 s   (176 trames, rideau.py)
  image fixe, attente de la barre d'espace (ici 2 s)
  écran éteint, bordure bleu foncé, décompression du jeu
  écran titre du jeu, musique du titre (son/antiriad_titre_cpc.mp3), 40 s

Toile commune : 768 x 544 (la zone visible d'un moniteur CPC, lignes doublées).
Usage : python3 video.py   (après chargeur.py et rideau.py)
"""
import os, pickle, subprocess, shutil
import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
import images, rideau as RD

W, H = 768, 544
TITRE_S = 40


def toile(fond):
    return np.tile(np.array(fond, np.uint8), (H // 2, W, 1))


def poser(im, fond):
    """Centre une image de lignes simples sur la toile, puis double les lignes."""
    t = toile(fond)
    h, w = im.shape[:2]
    y, x = (H // 2 - h) // 2, (W - w) // 2
    t[y:y + h, x:x + w] = im
    return np.repeat(t, 2, 0)


if __name__ == "__main__":
    o = pickle.load(open(os.path.join(ICI, "chargeur.pkl"), "rb"))
    rp = o["reperes"]
    dec2 = (rp[0x0281] - rp[0x020D]) / 4e6
    dec_jeu = (rp[0x5400] - rp[0x02C1]) / 4e6
    d = "/tmp/intro_v"; shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    n = [0]

    def ecrire(im, fois=1):
        for _ in range(fois):
            Image.fromarray(im).save("%s/%05d.png" % (d, n[0])); n[0] += 1

    noir, bleu = (0, 0, 0), (0, 0, 128)
    ecrire(poser(np.zeros((0, 0, 3), np.uint8), noir), round(rp[0x0205] / 4e6 * 50))
    ecrire(poser(images.logo(o["img1"]), noir), 150)
    ecrire(poser(np.zeros((0, 0, 3), np.uint8), noir), round(dec2 * 50))
    r = o["regs"]
    w, Ds, fin = RD.rideau(D=r[4], IX=r[9], E=r[5], H=r[6], L=r[7], Calt=0x8E)
    for im in RD.trames(w, o["img2"], n_fin=100):
        ecrire(poser(im, bleu))
    ecrire(poser(np.zeros((0, 0, 3), np.uint8), bleu), round(dec_jeu * 50))
    debut_titre = n[0] / 50
    titre = np.array(Image.open(os.path.join(ICI, '..', 'build', 'ecran_titre.png')).convert("RGB"))[::2]
    ecrire(poser(titre, noir), TITRE_S * 50)
    sortie = os.path.join(ICI, "intro.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "50", "-i", d + "/%05d.png",
                    "-itsoffset", "%.2f" % debut_titre, "-i", os.path.join(ICI, "..", "sound", "antiriad_titre_cpc.mp3"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-c:a", "aac", "-b:a", "96k", "-af", "afade=t=out:st=%.1f:d=3" % (n[0] / 50 - 3), "-shortest",
                    sortie], check=True)
    print("décompression image 2 %.2f s, jeu %.2f s ; titre à %.2f s ; %d trames -> %s"
          % (dec2, dec_jeu, debut_titre, n[0], sortie))
