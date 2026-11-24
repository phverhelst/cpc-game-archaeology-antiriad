"""Mouvement de Tal à pied (sans l'armure) dans The Sacred Armour of Antiriad (CPC, 1986).

Modèle Python pur, sans dépendance, transcrit du code Z80 d'origine. Chaque fonction renvoie
à la routine qu'elle reproduit. Une passe de jeu (« tour ») de Tal à pied enchaîne :

    pied_tour()   = &5787 : &65A2 (gravité, saut, lecture du joystick)
                            puis &67B6 (mur) et, s'il y a mur, &6876
    animer()      = la part de Tal dans &6B0E : pas d'animation (&6B2F),
                    puis application du déplacement (&6C23)

Les tables viennent du binaire (`tables.py`). Les collisions lisent l'écran, comme l'original :
le paramètre `ecran` est un objet qui fournit `octet(ligne, colonne)` (voir `EcranMemoire`).
"""
from dataclasses import dataclass, field
from tables import TABLES

T = TABLES

# Options qui s'écartent volontairement du jeu d'origine (toutes désactivées par défaut).
#   saut_diagonal : haut + la direction où Tal regarde lance un saut dans cette direction, à l'arrêt
#                   comme en marchant, sans le feu. Dans le jeu, haut + direction donne un saut vertical
#                   à l'arrêt et rien en marchant (la table &8F3B rabat la diagonale sur l'horizontale).
OPTIONS = {'saut_diagonal': False}

# Bits du joystick (&7A4C, ligne 9 de la matrice, inversée : 1 = appuyé)
HAUT, BAS, GAUCHE, DROITE, FEU = 1, 2, 4, 8, 16

# Bits de direction de l'objet (+7)
MONTE, DESCEND, VERS_GAUCHE, VERS_DROITE = 1, 2, 4, 8


@dataclass
class Tal:
    """Fiche d'objet de 19 octets en &B400 (Tal est l'objet 0), plus les globales du saut et du mur."""
    x: int = 0x24          # +3  colonne d'écran en octets (mode 0 : 2 pixels par octet)
    y: int = 0x57          # +4  ligne (0x32 = première ligne de l'écran)
    dirs: int = DESCEND    # +7  MONTE | DESCEND | VERS_GAUCHE | VERS_DROITE
    vx: int = 1            # +8  vitesse horizontale (octets par tour)
    vy: int = 0            # +9  vitesse verticale (lignes par tour)
    etat: int = 0x02       # +A  état d'animation ; bit 7 = animation terminée (FD atteint)
    pas: int = 0           # +B  position dans le script d'animation
    attente: int = 0       # +C  tours restants avant l'image suivante
    sprite: int = 0x08     # +D  sprite affiché ; bit 7 = tourné vers la droite
    demi_largeur: int = 3  # +F  largeur du sprite / 2, en octets
    hauteur: int = 0x2A    # +10 hauteur du sprite, en lignes
    saut: int = 0          # &B498 index dans la table des vitesses (montée : décroît, chute : croît)
    mur: int = 0xFF        # &B554 0 = mur rencontré au dernier test

    @property
    def e(self):
        return self.etat & 0x7F


class EcranMemoire:
    """Écran lu dans une image mémoire de 64 Ko, par la table d'adresses de lignes &8BF3."""
    def __init__(self, mem):
        self.mem = mem

    def octet(self, ligne, colonne):
        a = self.mem[0x8BF3 + 2 * ligne] | self.mem[0x8BF3 + 2 * ligne + 1] << 8
        return self.mem[(a + colonne) & 0xFFFF]


def classe_joystick(joy):
    """&656F : ramène le joystick à une des six classes (0 rien, 1 haut, 2 droite, 3 bas, 4 gauche, 5 feu)."""
    return T.classes[0x0F if joy & FEU else joy & 0x0F]


def poser_etat(t, e):
    """&6AE2 : nouvel état, animation reprise au début."""
    t.etat, t.pas, t.attente = e, 0, 0


# ---------------------------------------------------------------- collisions (lecture de l'écran)

def sol(ecran, ligne, colonne):
    """&68B4 : y a-t-il un sol sous les pieds ? Seules les lignes de rang 2 dans leur bloc de 8 comptent.
    On compare 6 octets à partir de la colonne au motif &8E1C, pixel par pixel."""
    if ligne & 7 != 2:
        return False
    for i, motif in enumerate(T.motif_sol):
        b = ecran.octet(ligne, colonne + i)
        a = b & 0x8A
        if a and a == motif & 0xAA:
            return True
        a = b & 0x45
        if a and a == motif & 0x55:
            return True
    return False


def plafond(ecran, ligne, colonne):
    """&6714 : y a-t-il un plafond ? Sous la ligne &3A, seules les lignes de rang 1 comptent."""
    if ligne >= 0x3A and ligne & 7 != 1:
        return False
    for i in range(4):
        b = ecran.octet(ligne, colonne + 1 + i)
        a = b & 0x8A
        if a and a == 0x80:
            return True
        a = b & 0x45
        if a and a == 0x40:
            return True
    return False


def test_mur(t, ecran):
    """&67B6 (Tal à pied) : renvoie True s'il y a un mur devant. Met à jour &B554."""
    if t.e not in T.etats_mur:
        t.mur = 0xFF
        return False
    h = t.dirs & 0x0C
    if h == 0:
        if t.e == 0x02:
            col = t.x - 1
        elif t.e == 0x0B:
            col = t.x + 7
        else:
            t.mur = 0xFF
            return False
    else:
        col = t.x + 7 if h & VERS_DROITE else t.x - 1
    col &= 0xFF
    ligne = t.y + 4
    for k in range(0x23):                       # 0x26 dans l'armure
        b = ecran.octet((ligne + k) & 0xFF, col)
        if b & 0xAA == 0xA8 or b & 0x55 == 0x54:
            t.mur = 0
            return True
    t.mur = 0xFF
    return False


# ---------------------------------------------------------------- logique de Tal à pied

def transitions(t, joy):
    """&675C : transition d'état selon le joystick, et directions autorisées par l'état."""
    suivants, masque = T.transitions[t.e]
    if masque & 0x10 and not t.etat & 0x80:     # état ininterruptible tant que son animation n'est pas finie
        return
    c = classe_joystick(joy)
    t.dirs = (t.dirs & 3) | (joy & masque & 0x0F)
    n = suivants[c]
    if n == 0:
        return
    if t.mur == 0 and n in (0x0C, 0x03):        # pas de marche contre un mur
        return
    poser_etat(t, n)


def lancer_saut(t, c):
    """&66B1 : départ du saut. Les bits horizontaux de c sont conservés."""
    t.dirs = (c & 0x0C) | MONTE
    poser_etat(t, 0x10 if t.sprite & 0x80 else 0x07)
    t.saut = 0x0B


def entree(t, joy):
    """&6659 : au sol, lecture du joystick (saut ou transitions ordinaires)."""
    e = t.e
    if OPTIONS['saut_diagonal'] and joy & HAUT and not joy & FEU:      # option, absente du jeu
        face = VERS_GAUCHE if e in (0x02, 0x03) else VERS_DROITE if e in (0x0B, 0x0C) else 0
        if face and joy & 0x0C == face:
            if t.dirs & DESCEND:
                lancer_saut(t, face)
            return
    if not joy & FEU:
        if joy & HAUT and e in (0x02, 0x0B):
            if t.dirs & DESCEND:                # &66AB
                lancer_saut(t, t.dirs)
            return
        return transitions(t, joy)
    if e in (0x03, 0x0C):                       # feu en marchant : saut en courant
        if t.dirs & DESCEND:
            lancer_saut(t, t.dirs)
        return
    a = joy & 0x0D
    if a == 0 or bin(a).count('1') % 2:         # JP PO : nombre impair de bits
        return transitions(t, joy)
    c = (a & 0x0C) | 0x02
    if (c & VERS_GAUCHE and e == 0x02) or (c & VERS_DROITE and e == 0x0B):
        return lancer_saut(t, c)
    return transitions(t, joy)


def gravite(t, joy, ecran):
    """&65A2 : montée du saut, ou recherche du sol et chute."""
    if t.dirs & MONTE:                          # &66CE : montée
        b = T.vitesses[t.saut]
        t.vy = b
        ligne, c = t.y + 7, 0
        for _ in range(b):
            if ligne < 0x3A and plafond(ecran, ligne, t.x):
                t.vy = c
                if c:
                    return
                t.saut = 0
                t.dirs = (t.dirs & 0x0C) | DESCEND
                return
            ligne -= 1
            c += 1
        t.saut -= 1
        if t.saut == 0:
            t.dirs = (t.dirs & 0x0C) | DESCEND
        return

    b = T.vitesses[t.saut]                      # chute : le sol est-il à portée ?
    ligne, c = t.y + t.hauteur + 1, 0
    for _ in range(b):
        if ligne < 0x32 or ligne >= 0xBA:
            break
        if sol(ecran, ligne, t.x):              # &6610 : sol trouvé à c lignes
            t.vy = c
            if t.e in (0x07, 0x10) or t.saut:   # atterrissage
                t.saut = 0
                t.dirs &= 3
                poser_etat(t, 0x09 if t.e < 0x0B else 0x12)
                return
            return entree(t, joy)
        ligne += 1
        c += 1
    t.vy = T.vitesses[t.saut]                   # &65E2 : pas de sol, on tombe
    if t.saut + 1 < 0x11:
        t.saut += 1
    e = t.e
    if e < 0x0B:
        if e != 0x02:
            poser_etat(t, 0x08)
    elif e != 0x0B:
        poser_etat(t, 0x11)


def bloque(t):
    """&6876 : Tal a rencontré un mur."""
    if t.e == 0x0C:
        poser_etat(t, 0x0B)
    elif t.e == 0x03:
        poser_etat(t, 0x02)
    elif t.saut == 0x0A:                        # seulement au premier tour du saut
        t.dirs &= 3
        return
    t.dirs = DESCEND                            # sinon la montée est annulée


def pied_tour(t, joy, ecran):
    """&5787 : la logique propre à Tal à pied, un tour."""
    gravite(t, joy, ecran)
    if test_mur(t, ecran):
        bloque(t)


# ---------------------------------------------------------------- animateur commun (&6B0E)

def animer(t):
    """&6B2F puis &6C23 : image suivante de l'animation, puis déplacement selon +7, +8, +9."""
    if t.e:
        if t.attente:
            t.attente -= 1
        else:
            script = T.animations[t.e]
            while True:
                b = script.code[t.pas]
                if b == 0xFC:                   # boucle
                    t.pas = 0
                    continue
                if b == 0xFD:                   # fin : l'état est marqué terminé
                    t.etat |= 0x80
                elif b == 0xFE:                 # enchaîne sur un autre état
                    poser_etat(t, script.code[t.pas + 1])
                elif b == 0xFF:
                    raise NotImplementedError("FF : fin d'objet, jamais atteint par Tal")
                else:
                    t.sprite = b
                    t.demi_largeur, t.hauteur = T.sprites[b & 0x7F]
                    t.pas += 1
                    t.attente = script.delai
                break
    d = t.dirs
    if d & MONTE:
        t.y = max(t.y - t.vy, 0)
    if d & DESCEND:
        t.y = min(t.y + t.vy + t.hauteur, 0xFF) - t.hauteur
    if d & VERS_GAUCHE:
        t.x = max(t.x - t.vx, 0)
    if d & VERS_DROITE:
        l2 = 2 * t.demi_largeur & 0xFF
        t.x = min(t.x + l2 + t.vx, 0x4F) - l2


def tour(t, joy, ecran):
    pied_tour(t, joy, ecran)
    animer(t)
