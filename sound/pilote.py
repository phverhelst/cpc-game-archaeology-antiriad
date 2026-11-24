"""Le pilote de son et de musique de The Sacred Armour of Antiriad (Amstrad CPC), transcrit du code Z80.

Comme enemies/monde.py, le modèle travaille sur une image de la mémoire du jeu (64 Ko) et reproduit chaque
routine, dont il porte l'adresse. Le pilote est appelé 100 fois par seconde par l'interruption (&755E, aux
deuxième et cinquième des six interruptions de chaque image). Il interprète, sur chacune des trois voies du
AY-3-8912, un petit langage de commandes (« sons », table &8AEF), et calcule à chaque appel les 11 premiers
registres du AY, qu'il range en &7A50 avant de les envoyer (&78F2).

Fiche d'une voie (&2E octets, en &7A5B, &7A89, &7AB7) :
  +0,+1 début du son        +2,+3 position         +4,+5 tours restants   +6,+7 durée courante (tours)
  +8 mélangeur (1 son, 8 bruit)   +9 volume de base   +A,+B période de la note
  +C,+D minuteries de l'enveloppe de volume (2 phases)  +E,+F pas restants
  +10..+12 minuteries de l'enveloppe de hauteur (3 phases)  +13..+15 pas restants
  +16..+24 instrument (15 octets, table &7AF2) : +16,+17 et +18..+1A nombres de pas, +1B,+1C et +1D..+1F
           valeur d'un pas (signée), +20,+21 et +22..+24 tours entre deux pas
  +2A décalage de volume   +2B,+2C décalage de période (12 bits)   +2D reprises (bit 0 volume, bit 1 hauteur)
Enveloppe de bruit, commune (&7AE5) : 2 phases, même principe ; +4..+9 copiés de la table &7E49.
"""

VOIES = 0x7A5B
TAILLE = 0x2E
REGS = 0x7A50              # périodes A, B, C (6 octets), bruit, mélangeur, volumes A, B, C
TEMPO = 0x7A4F             # tours (1/100 s) par unité de durée
NOTES = 0x7974             # périodes du AY pour 96 demi-tons, du do 0 au si 7 (horloge 1 MHz)
SONS = 0x8AEF


def mot(m, a):
    return m[a] | m[a + 1] << 8


def ecrire_mot(m, a, v):
    m[a] = v & 0xFF
    m[a + 1] = (v >> 8) & 0xFF


def voie(n):
    return VOIES + TAILLE * n


def melangeur(m, n, actifs):                                         # &7887 : actifs = 1 son, 8 bruit
    e = ~actifs & 0xFF
    d = 9
    for _ in range(n):
        e = ((e << 1) | 1) & 0xFF
        d = (d << 1) & 0xFF
    m[0x7A57] = (m[0x7A57] | d) & e


def lancer(m, n, son):                                               # &752A : le son `son` sur la voie n
    p = mot(m, (SONS + 2 * son) & 0xFFFF)
    ix = voie(n)
    ecrire_mot(m, ix, p)
    ecrire_mot(m, ix + 2, p)
    for k in range(4, 4 + 0x2A):
        m[ix + k] = 0


def env_volume(m, ix):                                               # &773F
    for k in range(2):
        m[ix + 0xC + k] = m[ix + 0x20 + k]
        m[ix + 0xE + k] = m[ix + 0x16 + k]


def env_hauteur(m, ix):                                              # &7727
    for k in range(3):
        m[ix + 0x10 + k] = m[ix + 0x22 + k]
        m[ix + 0x13 + k] = m[ix + 0x18 + k]


def env_bruit(m):                                                    # &770B
    for k in range(2):
        m[0x7AE5 + k] = m[0x7AED + k]
        m[0x7AE7 + k] = m[0x7AE9 + k]


def lire(m, n, ix, journal, tour):
    """&757C-&75C0 : la durée de la voie est écoulée ; lit les commandes jusqu'à la prochaine note.
    Renvoie False si la voie est éteinte (pointeur nul)."""
    melangeur(m, n, 0)
    bc = mot(m, ix + 2)
    if bc == 0:
        return False
    while True:
        c = m[bc]
        if c < 0x80:                                                 # une note
            ecrire_mot(m, ix + 0xA, mot(m, NOTES + 2 * c))
            bc += 1
            note_on(m, n, ix, journal, tour, ('note', c))
            break
        c -= 0x80
        if c == 0:                                                   # &80 volume
            m[ix + 9] = m[bc + 1]; bc += 2
        elif c == 1:                                                 # &81 son, bruit ou les deux
            m[ix + 8] = m[bc + 1] & 9; bc += 2
        elif c == 2:                                                 # &82 reprise au début
            bc = mot(m, ix)
            if journal is not None:
                journal.append((tour, n, 'reprise'))
        elif c == 3:                                                 # &83 durée en unités
            ecrire_mot(m, ix + 6, m[bc + 1] * m[TEMPO]); bc += 2
        elif c == 4:                                                 # &84 silence : la voie reste coupée (&757C)
            bc += 1
            if journal is not None:
                journal.append((tour, n, 'silence', mot(m, ix + 6)))
            break
        elif c == 5:                                                 # &85 tempo
            d = (m[bc + 1] * 8) & 0xFFFF
            m[TEMPO] = (6000 // d) & 0xFF if d else 0xFF
            if journal is not None:
                journal.append((tour, n, 'tempo', m[bc + 1], m[TEMPO]))
            bc += 2
        elif c == 6:                                                 # &86 durée composée (somme des n-1 premières)
            k = m[bc + 1]; bc += 2
            de = hl = 0
            for _ in range(k):
                hl, de = de, (de + m[bc] * m[TEMPO]) & 0xFFFF
                bc += 1
            ecrire_mot(m, ix + 6, hl)
        elif c == 7:                                                 # &87 instrument
            m[ix + 0x2D] &= 0xFC
            src = 0x7AF2 + m[bc + 1] * 15
            for k in range(15):
                m[ix + 0x16 + k] = m[(src + k) & 0xFFFF]
            bc += 2
            for k in (0xC, 0xD, 0x10, 0x11, 0x12, 0x2A, 0x2B, 0x2C):
                m[ix + k] = 0
        elif c == 8:                                                 # &88 hauteur du bruit, frappe si bit 7 nul
            a = m[bc + 1]
            m[0x7AF0] = a & 0x1F
            env_bruit(m)
            bc += 2
            if a < 0x80:
                note_on(m, n, ix, journal, tour, ('frappe', a & 0x1F))
                break
        elif c == 9:                                                 # &89 enveloppe de bruit
            m[0x7AEF] &= ~4 & 0xFF
            src = 0x7E49 + m[bc + 1] * 6
            m[0x7AE5] = m[0x7AE6] = 0
            for k in range(6):
                m[0x7AE9 + k] = m[src + k]
            m[0x7AF1] = 0
            bc += 2
        elif c == 0xA:                                               # &8A reprises des enveloppes
            m[ix + 0x2D] |= m[bc + 1]
            m[0x7AEF] |= m[bc + 1]
            bc += 2
        elif c == 0xB:                                               # &8B : relance la voie sur le son &57 (vide)…
            lancer(m, n, 0x57)                                       # … et garde la position : la voie se tait
            note_on(m, n, ix, journal, tour, ('fin', None))
            break                                                    # la position reste sur &8B
        else:
            raise ValueError('commande %02X en %04X' % (c + 0x80, bc))
    ecrire_mot(m, ix + 2, bc)                                        # &75C0
    ecrire_mot(m, ix + 4, mot(m, ix + 6))
    return True


def note_on(m, n, ix, journal, tour, quoi):                          # &75A8
    melangeur(m, n, m[ix + 8])
    env_volume(m, ix)
    m[ix + 0x2A] = 0
    env_hauteur(m, ix)
    m[ix + 0x2B] = m[ix + 0x2C] = 0
    if journal is not None:
        journal.append((tour, n, quoi[0], quoi[1], mot(m, ix + 6), m[ix + 9], m[ix + 8],
                        bytes(m[ix + 0x16:ix + 0x25]), m[0x7AF0]))


def tour(m, journal=None, t=0):                                      # &755E
    for n in range(3):
        ix = voie(n)
        actif = True
        if mot(m, ix + 4) == 0:
            actif = lire(m, n, ix, journal, t)
        if actif:
            ecrire_mot(m, ix + 4, mot(m, ix + 4) - 1)
            c = False
            for k in range(2):                                       # enveloppe de volume
                if m[ix + 0xC + k]:
                    m[ix + 0xC + k] -= 1; c = True; break
                if m[ix + 0xE + k]:
                    m[ix + 0xE + k] -= 1
                    m[ix + 0x2A] = (m[ix + 0x2A] + m[ix + 0x1B + k]) & 0xFF
                    m[ix + 0xC + k] = m[ix + 0x20 + k]
                    c = True; break
            if not c:
                m[ix + 0x2A] = 0
                if m[ix + 0x2D] & 1:
                    env_volume(m, ix)
            c = False
            for k in range(3):                                       # enveloppe de hauteur
                if m[ix + 0x10 + k]:
                    m[ix + 0x10 + k] -= 1; c = True; break
                if m[ix + 0x13 + k]:
                    m[ix + 0x13 + k] -= 1
                    pas = m[ix + 0x1D + k]
                    v = (m[ix + 0x2C] << 8 | m[ix + 0x2B]) + (pas - 256 if pas >= 0x80 else pas)
                    m[ix + 0x2B] = v & 0xFF
                    m[ix + 0x2C] = (v >> 8) & 0x0F
                    m[ix + 0x10 + k] = m[ix + 0x22 + k]
                    c = True; break
            if not c and m[ix + 0x2D] & 2:
                env_hauteur(m, ix)
        m[0x7A58 + n] = (m[ix + 9] + m[ix + 0x2A]) & 0x0F            # &768F : registres
        lo = m[ix + 0xA] + m[ix + 0x2B]
        m[REGS + 2 * n] = lo & 0xFF
        m[REGS + 2 * n + 1] = (m[ix + 0xB] + m[ix + 0x2C] + (lo >> 8)) & 0xFF
    c = False                                                        # enveloppe de bruit
    for k in range(2):
        if m[0x7AE5 + k]:
            m[0x7AE5 + k] -= 1; c = True; break
        if m[0x7AE7 + k]:
            m[0x7AE7 + k] -= 1
            m[0x7AF1] = (m[0x7AF1] + m[0x7AEB + k]) & 0xFF
            m[0x7AE5 + k] = m[0x7AED + k]
            c = True; break
    if not c and m[0x7AEF] & 4:
        env_bruit(m)
    m[0x7A56] = (m[0x7AF0] + m[0x7AF1]) & 0xFF
    return bytes(m[REGS:REGS + 11])
