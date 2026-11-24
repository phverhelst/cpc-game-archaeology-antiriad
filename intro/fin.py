"""La fin de partie filmée dans l'émulateur : du compte à rebours à la scène finale.

On reprend le scénario de enemies/verif.py (verif_fin) : Tal en armure dans la salle &00, la mine posée
sur la cible. Le jeu tourne dans l'émulateur cpcarch.emu ; à chaque trame (50 Hz) on relève la
mémoire écran, les palettes en vigueur dans chacune des six tranches d'interruption, le mode et le
registre 8 du CRTC. On en tire :
  - fin.mp4 : la séquence rendue, avec le tremblement de l'entrelacement (R8=1) simulé par un décalage
    d'une demi-ligne une trame sur deux, et le son de l'implosion (sons &17, &18, &19, pilote son/pilote.py) ;
  - fin_*.png : quelques images clés ;
  - les durées mesurées (implosion, attente par tirage).

Usage : python3 fin.py
"""
import os, sys, subprocess, pickle
import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
for d in ("../enemies", "../sound"):
    sys.path.insert(0, os.path.join(ICI, d))
import trace as TR
from cpcarch.emu import FRAME
from cpcarch.cpcgfx import HW

AVANT = 100      # trames gardées avant le déclenchement de l'implosion
APRES = 300      # trames filmées après l'entrée dans la boucle finale


def filmer():
    rg = {0xB512: 0, 0xB519: 0, 0xB51A: 0, 0xB51B: 0, 0xB51C: 0}
    c = TR.depart(); TR.entrer(c, 0x00, 0x22, 0x50, rg); TR.en_armure(c)
    TR.tracer(c, [(('joy_up',), 6), ((), 10), (('joy_down',), 80)], arret=lambda m: m[0xB4EE] == 0)
    c.keys = set()
    R, mem = c.R, c.mem
    trames, t_imp, t_fin, m_imp = [], None, None, None
    prochaine = (R[25] // FRAME + 1) * FRAME
    while True:
        pc = R[24]
        if pc == 0x5C31 and t_imp is None:
            t_imp = R[25]; m_imp = bytes(mem); n_imp = len(trames)
        if pc == 0x5CA6 and t_fin is None:
            t_fin = R[25]; n_fin = len(trames)
        c.run(1)
        if R[25] >= prochaine:
            prochaine += FRAME
            trames.append((bytes(mem[0xC000:0x10000]), [list(p) for p in c.slot_pal],
                           list(c.slot_mode), c.crtc.get(8, 0)))
            if t_imp is None and len(trames) > AVANT:
                trames.pop(0)
            if t_fin is not None and len(trames) >= n_fin + APRES:
                break
    return trames, n_imp, n_fin, t_imp, t_fin, m_imp


def rendu(ecran, slot_pal, slot_mode):
    """Comme CPC.shot_raster, en numpy : 320 x 200, chaque ligne avec la palette de sa tranche."""
    e = np.frombuffer(ecran, np.uint8)
    im = np.zeros((200, 320, 3), np.uint8)
    for y in range(200):
        s = ((y + 70) // 52) % 6
        pal = np.array([HW[c & 31] for c in slot_pal[s][:16]], np.uint8)
        a = (y % 8) * 0x800 + (y // 8) * 80
        b = e[a:a + 80].astype(np.int32)
        if slot_mode[s] == 1:
            px = np.stack([((b >> (7 - i)) & 1) | (((b >> (3 - i)) & 1) << 1) for i in range(4)], 1).reshape(-1)
            im[y] = pal[px]
        else:
            p0 = ((b >> 7) & 1) | (((b >> 3) & 1) << 1) | (((b >> 5) & 1) << 2) | (((b >> 1) & 1) << 3)
            p1 = ((b >> 6) & 1) | (((b >> 2) & 1) << 1) | (((b >> 4) & 1) << 2) | ((b & 1) << 3)
            px = np.stack([p0, p0, p1, p1], 1).reshape(-1)
            im[y] = pal[px]
    return im


def son(m_imp, n_tours):
    """Les sons &17, &18, &19 lancés en &5C3E sur les voies A, B et C, joués par le pilote transcrit."""
    import pilote as P
    from cpcarch import ay
    m = bytearray(m_imp)
    for voie, s in ((0, 0x17), (1, 0x18), (2, 0x19)):
        P.lancer(m, voie, s)
    regs = [P.tour(m) for _ in range(n_tours)]
    w = "/tmp/fin.wav"
    ay.ecrire_wav(w, ay.synthese(regs))
    return w


if __name__ == "__main__":
    trames, n_imp, n_fin, t_imp, t_fin, m_imp = filmer()
    duree = (t_fin - t_imp) / 4e6
    print("trames filmées %d ; implosion de la trame %d à la trame %d" % (len(trames), n_imp, n_fin))
    print("implosion : %.2f s (horloge du Z80 nu, interruptions comprises), %.0f µs par tirage"
          % (duree, (t_fin - t_imp) / 4 / 16384))
    pickle.dump((n_imp, n_fin, t_imp, t_fin), open("/tmp/fin_meta.pkl", "wb"))
    os.makedirs("/tmp/fin", exist_ok=True)
    for k, (e, sp, sm, r8) in enumerate(trames):
        im = rendu(e, sp, sm)
        im = np.repeat(im, 2, 0)                      # 320 x 400
        im = np.repeat(im, 2, 1)                      # 640 x 400
        if r8 & 1 and k % 2:                          # entrelacement : trame impaire décalée d'une demi-ligne
            im = np.vstack([im[:1] * 0, im[:-1]])
        Image.fromarray(im).save("/tmp/fin/%04d.png" % k)
    for nom, k in (("avant", n_imp - 1), ("milieu", (n_imp + n_fin) // 2), ("apres", n_fin + 100)):
        Image.open("/tmp/fin/%04d.png" % k).save(os.path.join(ICI, "fin_%s.png" % nom))
    # son : silence jusqu'à l'implosion, puis les trois voix, deux tours de pilote par trame (100 Hz)
    w = son(m_imp, 2 * (len(trames) - n_imp))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "50", "-i", "/tmp/fin/%04d.png",
                    "-itsoffset", "%.2f" % (n_imp / 50), "-i", w,
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-c:a", "aac", "-b:a", "96k", "-af", "apad", "-shortest",
                    os.path.join(ICI, "fin.mp4")], check=True)
    print("fin.mp4 écrit")
