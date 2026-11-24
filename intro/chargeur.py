"""Exécution du chargeur CNGSoft (ANTIRIDE.BAS) jusqu'à l'entrée du jeu en &5400.

On récupère au passage :
  - l'image 1 (logo CNGSoft en overscan) au moment où elle s'affiche (PC=&0205),
    avec les registres CRTC programmés ;
  - l'image 2 (écran de chargement Antiriad, mode 2) au début du rideau (PC=&0281) ;
  - le journal de toutes les écritures vers le Gate Array (port &7Fxx) pendant le
    rideau, avec la valeur de D (position du rideau) à chaque image.

Les appels au firmware (&B900-&BDFF) sont interceptés : on rend la main tout de suite,
KM_WAIT_CHAR (&BB18) répond « espace ». Les HALT sont sautés (pas d'interruptions).
Le signal VSYNC (bit 0 du port B du PPI, &F5xx) est simulé : haut pendant les
8 premières lignes de chaque trame de 79872 T-states.

Sortie : intro/chargeur.pkl (lu par rideau.py et images.py).
"""
import os, sys, pickle
ICI = os.path.dirname(os.path.abspath(__file__))
from cpcarch.cpcsim import Simulator

REPERES = (0x0190, 0x0205, 0x020D, 0x0281, 0x02B9, 0x02C1, 0x5400)
TRAME = 79872          # T-states par trame (312 lignes x 64 µs x 4 MHz)
VSYNC = 8 * 256        # 8 lignes de 64 µs


def executer():
    data = open(os.path.join(ICI, '..', 'build', 'ANTIRIDE.BAS'), "rb").read()
    mem = [0] * 65536
    mem[0x170:0x170 + len(data)] = list(data)
    crtc = {"sel": 0, "regs": {}}
    journal = []          # écritures Gate Array pendant le rideau : (T, valeur)
    etat = {"rideau": False}

    class Traceur:
        def write_port(self, r, port, v, *a):
            hi = port >> 8
            if hi == 0xBC:
                crtc["sel"] = v
            elif hi == 0xBD:
                crtc["regs"][crtc["sel"]] = v
            elif hi == 0x7F and etat["rideau"]:
                journal.append((r[25], v))

        def read_port(self, r, port, *a):
            if port >> 8 == 0xF5:
                return 0xFE | (1 if r[25] % TRAME < VSYNC else 0)
            return 0xFF

    sim = Simulator(mem, {"PC": 0x190, "SP": 0xBFF0})
    sim.set_tracer(Traceur())
    R = sim.registers
    out = {"D": [], "reperes": {}}
    pas = 0
    while pas < 60_000_000:
        pc = R[24]
        if pc == 0x0205 and "img1" not in out:
            out["img1"] = list(mem[0xC000:0x10000]); out["crtc1"] = dict(crtc["regs"])
        if pc == 0x0281 and "img2" not in out:
            out["img2"] = list(mem[0xC000:0x10000]); out["crtc2"] = dict(crtc["regs"])
            out["regs"] = list(R); etat["rideau"] = True; out["T0"] = R[25]
        if pc == 0x026E and etat["rideau"]:
            out["D"].append(R[4])
        if pc == 0x02B9 and etat["rideau"]:
            etat["rideau"] = False; out["Tfin"] = R[25]
        if pc in REPERES and pc not in out["reperes"]:
            out["reperes"][pc] = R[25]
        if 0xB900 <= pc <= 0xBDFF:
            if pc == 0xBB18:
                R[0] = 0x20
            sp = R[12]; R[24] = mem[sp] | mem[sp + 1] << 8; R[12] = (sp + 2) & 0xFFFF
            continue
        if mem[pc] == 0x76:
            R[24] = pc + 1; pas += 1; continue
        sim.run(); pas += 1
        if R[24] == 0x5400:
            break
    out["reperes"][R[24]] = R[25]
    out["journal"] = journal
    out["pas"] = pas
    return out


if __name__ == "__main__":
    o = executer()
    pickle.dump(o, open(os.path.join(ICI, "chargeur.pkl"), "wb"))
    print("pas", o["pas"], "écritures GA pendant le rideau", len(o["journal"]),
          "positions D", len(o["D"]))
    print("CRTC image 1", {k: o["crtc1"][k] for k in sorted(o["crtc1"])})
    print("CRTC image 2", {k: o["crtc2"][k] for k in sorted(o["crtc2"])})
    for a, t in sorted(o["reperes"].items(), key=lambda x: x[1]):
        print("  &%04X  T=%10d  (%.3f s à 4 MHz, HALT non comptés)" % (a, t, t / 4e6))
    print("durée du rideau : %.2f trames" % ((o["Tfin"] - o["T0"]) / TRAME))
