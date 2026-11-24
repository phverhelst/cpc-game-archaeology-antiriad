"""Mouvement de Tal dans l'armure — transcription de &5744 (vol, sol, plafond, mur), en complément de tal.py.

Un tour dans l'armure (&B4F1 = 0) :
    armure_tour() = &5744 : &62C5 (&63A9 commande, puis sol et plafond), &627B (flottement au neutre),
                    &67B6 version armure et &68A3 (rebond sur un mur), recharge par la cellule
    puis animer() de tal.py, l'animateur commun (&6B2F, &6C23)

Variables propres à l'armure (globales du jeu, ajoutées à la fiche de Tal) :
    gaz      &B51D  manette verticale de 0 (montée 4 lignes/tour) à 14 (descente 4), neutre 7
    glisse   &B51E  élan horizontal, 0 à 6 : nombre de tours de glissade restants au relâchement
    entree   &B51F  joystick du tour (forcé à « bas » sans énergie)
    sens_prec &B520 bits horizontaux du joystick au tour précédent
    en_vol   &B500  0 quand l'armure touche le sol ou le plafond
    phase    &B4F3  phase du flottement (0 à 15)
    energie  &B4FD  énergie de l'armure (31 au maximum)
    cellule  &B518  0 si Tal porte une cellule de recharge, &FF sinon
    deplaceur &B519 0 si le déplaceur de gravité a été trouvé (sinon l'armure ne décolle pas)
"""
from dataclasses import dataclass
import tal as M
from tal import TABLES as T, MONTE, DESCEND, VERS_GAUCHE, VERS_DROITE, poser_etat, sol, plafond

from tables import BINAIRE
_MEM = open(BINAIRE, 'rb').read()
# &8EF3 : (directions, vitesse) pour chaque cran de 0 à 14. La garde du code n'arrête la manette que
# sur 14 exactement ; après un rebond au plafond à pleins gaz (0 → 15), pousser vers le bas la fait
# monter au-delà, et le jeu lit alors les octets qui suivent la table. On les lit de même.
GAZ = [(_MEM[0x8EF3 + 2 * i + 1], _MEM[0x8EF3 + 2 * i]) for i in range(128)]
FLOTTEMENT = [(0x01, 1), (0x01, 0), (0x01, 0), (0x01, 0), (0x01, 1), (0x01, 0), (0x01, 0), (0x01, 0),
              (0x02, 1), (0x02, 0), (0x02, 0), (0x02, 0), (0x02, 1), (0x02, 0), (0x02, 0), (0x02, 0)]  # &8ED3


@dataclass
class TalArmure(M.Tal):
    gaz: int = 7
    glisse: int = 0
    entree: int = 0
    sens_prec: int = 0
    en_vol: int = 0
    phase: int = 0
    energie: int = 0x1F
    cellule: int = 0xFF
    deplaceur: int = 0


def regler_gaz(t):
    """&64DC : directions et vitesse verticales selon la manette."""
    h, l = GAZ[t.gaz & 0x7F]
    t.dirs = (t.dirs & 0x0C) | h
    t.vy = l


def ralentir(t):                                            # &6480
    if t.glisse:
        t.glisse -= 1


def pousser(t, sens):                                       # &6498
    t.dirs = (t.dirs & 3) | sens
    if t.glisse != 6:
        t.glisse += 1


def changer_etat(t, joy):
    """&6457 : à l'arrêt horizontal, demi-tour et poses selon le joystick."""
    t.dirs &= 3
    c = M.classe_joystick(joy)
    if t.energie == 0 and joy & M.HAUT:
        return
    n = T.transitions[t.e][0][c]
    if n:
        poser_etat(t, n)


def commande(t, joy):
    """&63A9 : manette des gaz, glissade, demi-tours."""
    suivants, masque = T.transitions[t.e]
    if masque & 0x10 and not t.etat & 0x80:
        return
    c = joy
    t.entree = c
    if t.energie == 0:
        c = t.entree = 0x02
    # &6437 joue un son quand la manette quitte le cran 6 vers le haut ou le cran 8 vers le bas.
    # La routine de son (&752A) écrase IX : ce tour-là, &64DC écrit direction et vitesse ailleurs
    # en mémoire (&7A89+7, +9 dans nos relevés), et l'armure garde celles du tour précédent.
    perdu = (c & 1 and t.gaz == 6) or (c & 2 and t.gaz == 8)
    regler = (lambda t: None) if perdu else regler_gaz
    if c & 1:                                               # &64CC
        if t.gaz:
            t.gaz -= 1; regler(t)
    elif c & 2 or t.gaz < 7:                                # &64BB
        if t.gaz != 0x0E:
            t.gaz += 1; regler(t)
    elif t.gaz >= 8:
        t.gaz -= 1; regler(t)
    # &63F8
    if t.glisse == 0:
        changer_etat(t, joy)
    prec, t.sens_prec = t.sens_prec, t.entree & 0x0C
    if (t.entree & 0x0C) != prec:
        ralentir(t)
        return
    for etat, sens in ((0x1B, VERS_DROITE), (0x19, VERS_GAUCHE)):
        if t.e == etat:
            if t.entree & sens:
                pousser(t, sens)
            else:
                ralentir(t)


def reflechir(t):                                           # &6390
    t.gaz = 0x0F - t.gaz


def sol_et_plafond(t, ecran):
    """&62C5 (après &63A9) : sol sous l'armure, plafond au-dessus, rebonds."""
    t.en_vol = 0xFF
    au_sol = False
    b, ligne, c = t.vy + 1, t.y + t.hauteur + 1, 0
    for _ in range(b):
        if ligne < 0x32 or ligne >= 0xBA:
            break
        if sol(ecran, ligne, t.x):                          # &62F9
            if t.dirs & DESCEND:
                t.vy = c
            if c == 0:
                au_sol = True
                t.en_vol = 0
                if t.dirs & DESCEND and t.e in (0x16, 0x17):   # &639F : posée
                    t.dirs = 0
                    poser_etat(t, 0x17)
                    return
            break
        ligne += 1
        c += 1
    b, ligne, c = t.vy + 1, t.y + 3, 0                      # &6324
    for _ in range(b):
        if plafond(ecran, ligne, t.x):                      # &6340
            if t.dirs & MONTE:
                t.vy = c
            t.en_vol = 0
            if au_sol:
                t.dirs &= 0x0C                              # &6376 : coincée
                return
            if t.dirs & MONTE:                              # &6368 : rebond vers le bas
                t.dirs = (t.dirs & 0x0C) | DESCEND
                reflechir(t)
                return
            break
        ligne -= 1
        c += 1
    if au_sol and t.dirs & DESCEND:                         # &637F : rebond vers le haut
        t.dirs = (t.dirs & 0x0C) | MONTE
        reflechir(t)


def flotter(t):
    """&627B : au neutre et en vol, léger balancement."""
    if t.gaz != 7 or t.e == 0x17 or not t.en_vol:
        return
    t.phase = (t.phase + 1) & 0x0F
    h, l = FLOTTEMENT[t.phase]
    t.dirs = (t.dirs & 0x0C) | h
    t.vy = l


def test_mur(t, ecran):
    """&67B6, version armure : 38 lignes ; tout en haut de l'écran, les quatre premières lignes."""
    if t.e not in T.etats_mur:
        t.mur = 0xFF
        return False
    h = t.dirs & 0x0C
    if h == 0:
        t.mur = 0xFF                                        # (02/0B n'existent pas dans l'armure)
        return False
    col = (t.x + 7 if h & VERS_DROITE else t.x - 1) & 0xFF
    if t.y < 0x33:                                          # &6848
        for i in range(4):
            if ecran.octet(0x32 + i, col):
                t.mur = 0
                return True
        t.mur = 0xFF
        return False
    for k in range(0x26):
        b = ecran.octet((t.y + 4 + k) & 0xFF, col)
        if b & 0xAA == 0xA8 or b & 0x55 == 0x54:
            t.mur = 0
            return True
    t.mur = 0xFF
    return False


def rebond_mur(t):                                          # &68A3
    t.dirs ^= 0x0C
    t.sens_prec ^= 0x03


def armure_tour(t, joy, ecran):
    """&5744."""
    if t.deplaceur:                                         # pas de déplaceur de gravité : inerte
        return
    commande(t, joy)
    sol_et_plafond(t, ecran)
    flotter(t)
    if test_mur(t, ecran):
        rebond_mur(t)
    if t.cellule == 0:                                      # la cellule portée recharge l'armure
        t.cellule = 0xFF
        t.energie = 0x1F


def tour(t, joy, ecran):
    armure_tour(t, joy, ecran)
    M.animer(t)
