"""Les objets du jeu (ennemis, obstacles, pierre, Tal en tant qu'objet) : modèle transcrit du code Z80.

Le modèle travaille directement sur une image de la mémoire du jeu (64 Ko, `bytearray` ou liste) : il lit les
tables du binaire (scripts &97F8, animations &9021, propriétés des états &922A, sprites &9432, objets des
salles &9BC7) et lit et écrit les variables du jeu en &B400-&B5FF, avec les mêmes adresses. Chaque fonction
reproduit une routine, dont elle porte l'adresse. La partie de la boucle principale couverte va de &5704
(juste après la logique propre de Tal, à pied ou dans l'armure) à la fin du tour ; voir `fin_de_tour`.

Ce qui n'est pas modélisé ici : la logique de Tal lui-même (movement/tal.py et movement/armure.py), le
changement de salle (&69A7), le dessin, le son, les messages, le défilement du texte et l'affichage des jauges.
Les poignées de ramassage (cellule, pièces, armure) restent dans le bac à sable ; leur numéro est renvoyé.
"""

OBJ, TAILLE = 0xB400, 19
ACTIFS = 0xB4EE            # bit n : objet n actif
VIE_TAL = 0xB4FB           # énergie vitale de Tal à pied (31 au maximum)
ENERGIE_ARMURE = 0xB4FD    # énergie de l'armure
A_PIED = 0xB4F1            # 0 : Tal est dans l'armure
SALLE = 0xB4ED
SCORE_AFFICHE, SCORE = 0xB534, 0xB536
COUPS = 0xB543             # coups à encaisser, objets 2 à 7
CHRONO_GENERATEUR = 0xB54F
REPIT = 0xB552             # répit après un contact avec un obstacle (&30, &31, &3B, &3C)
PROCHAIN = 0xB553          # premier emplacement libre après les objets de la salle
JEU_LANCE = 0xB512         # 0 quand l'armure a été activée ; FF avant
NEGATEUR = 0xB51C          # 0 quand la pièce « particle negator » est ramassée
CONTACTS = 0xB502          # 6 octets pour Tal, puis 6 pour la pierre : numéro d'objet touché ou FF


def o(n):
    return OBJ + TAILLE * n


def mot(m, a):
    return m[a] | m[a + 1] << 8


def anim_ptr(m, etat):
    return mot(m, 0x9021 + 2 * etat)


def proprietes(m, etat):
    """Les 4 octets de &922A pour un état : drapeaux (bit 7 invulnérable, bit 6 apparition, bit 5 poignée
    de contact, bits 0-4 numéro de poignée), puis dégâts (bits 0-4) et coups à encaisser (bits 5-7), puis
    points gagnés."""
    a = 0x922A + 4 * ((etat - 1) & 0xFF)
    return m[a:a + 4] if isinstance(m, (bytes, bytearray)) else bytes(m[a:a + 4])


def actif(m, n):
    return m[ACTIFS] >> n & 1


# ---- création, changement d'état, destruction -------------------------------------------------------------

def creer(m, n, x, y, script, etat):                                 # &6A50
    m[ACTIFS] |= 1 << n
    b = o(n)
    for k in (0x11, 1, 2, 7, 0xB):
        m[b + k] = 0
    m[b + 3] = m[b + 5] = x
    m[b + 4] = m[b + 6] = y
    m[b + 0] = script
    m[b + 0xA] = etat
    p = anim_ptr(m, etat)
    m[b + 0xC] = m[p]
    m[b + 0xD] = m[b + 0xE] = m[p + 1]
    m[b + 0x12] = 1 if proprietes(m, etat)[0] & 0x40 else 0


def poser_etat(m, n, etat):                                          # &6AE2
    b = o(n)
    m[b + 0xA] = etat; m[b + 0xB] = 0; m[b + 0xC] = 0


def detruire(m, n):                                                  # &6955
    m[ACTIFS] &= ~(1 << n) & 0xFF


def tuer(m, n):                                                      # &5D9E : disparition en 13 tours
    b = o(n)
    if m[b + 0x12] == 0:
        m[b + 0x12] = 0xFF; m[b + 0x11] = 0x0C; m[b + 0] = 0; m[b + 7] = 0


def fondus(m):                                                       # &5704
    for n in range(8):
        b = o(n); f = m[b + 0x12]
        if not f:
            continue
        if f < 0x80:                                                 # apparition : 12 tours
            m[b + 0x11] = (m[b + 0x11] + 1) & 0xFF
            if m[b + 0x11] == 0x0C:
                m[b + 0x12] = 0
        else:                                                        # disparition
            m[b + 0x11] = (m[b + 0x11] - 1) & 0xFF
            if m[b + 0x11] >= 0x80:
                m[b + 0x12] = 0
                detruire(m, n)


# ---- l'animateur commun (&6B0E) ---------------------------------------------------------------------------

def guidage(m, b):                                                   # &6CDE
    c = 0
    a = (m[0xB403] - 3) & 0xFF
    if a != m[b + 3]:
        c |= 4 if a < m[b + 3] else 8
    cible = (m[0xB404] + 0x0C) & 0xFF
    d = (cible - m[b + 4]) & 0xFF
    if d >= 0x80:
        d = (-d) & 0xFF
    if d >= 4 and cible != m[b + 4]:
        c |= 1 if cible < m[b + 4] else 2
    return c


def deplacer(m, b, c):                                               # &6C23-&6C93
    if c & 1:
        m[b + 4] = max(m[b + 4] - m[b + 9], 0)
    if c & 2:
        a = (m[b + 4] + m[b + 9]) & 0xFF
        s = a + m[b + 0x10]
        a = 0xFF if s > 0xFF else s
        m[b + 4] = (a - m[b + 0x10]) & 0xFF
    if c & 4:
        m[b + 3] = max(m[b + 3] - m[b + 8], 0)
    if c & 8:
        l2 = (m[b + 0xF] << 1) & 0xFF
        a = (l2 + m[b + 3] + m[b + 8]) & 0xFF
        m[b + 3] = (min(a, 0x4F) - l2) & 0xFF


def animer(m, n):                                                    # &6B2F
    b = o(n)
    e = m[b + 0xA] & 0x7F
    if e:
        if m[b + 0xC]:
            m[b + 0xC] -= 1
        else:
            while True:
                p = anim_ptr(m, e)
                code = m[p + 1 + m[b + 0xB]]
                if code == 0xFC:
                    m[b + 0xB] = 0
                    continue
                if code == 0xFD:
                    m[b + 0xA] |= 0x80
                elif code == 0xFE:
                    poser_etat(m, n, m[p + 2 + m[b + 0xB]])
                elif code == 0xFF:
                    detruire(m, n)
                    return
                else:
                    m[b + 0xD] = code
                    s = 0x9432 + 4 * (code & 0x7F)
                    m[b + 0xF], m[b + 0x10] = m[s + 2], m[s + 3]
                    m[b + 0xB] = (m[b + 0xB] + 1) & 0xFF
                    m[b + 0xC] = m[p]
                break
    if m[b] and not m[b + 0x12]:                                     # &6BB0 : script de mouvement
        if m[b + 2]:
            m[b + 2] -= 1
        else:
            while True:
                q = mot(m, 0x97F8 + 2 * m[b]) + 4 * m[b + 1]
                d = m[q]
                if d == 0xFC:
                    m[b + 1] = 0
                    continue
                if d == 0xFE:                                        # rend la main à Tal
                    m[b] = m[b + 1] = m[b + 2] = 0
                    m[0xB409] = 0; m[0xB408] = 1; m[0xB407] = 2
                elif d < 0xFC:
                    m[b + 7], m[b + 2], m[b + 8], m[b + 9] = m[q], m[q + 1], m[q + 2], m[q + 3]
                    m[b + 1] = (m[b + 1] + 1) & 0xFF
                break                                                # FD : garde les directions
    c = m[b + 7]
    deplacer(m, b, guidage(m, b) if c == 0x0F else c)
    if n and not m[b + 0x12]:                                        # &6C94 : faut-il redessiner ?
        e = m[b + 0xD] ^ m[b + 0xE]
        if not (e | m[b + 7]) or not (e | m[b + 8] | m[b + 9]):
            return
    m[b + 5], m[b + 6], m[b + 0xE] = m[b + 3], m[b + 4], m[b + 0xD]


def animateur(m):                                                    # &6B0E : objets 7 à 0
    for n in range(7, -1, -1):
        if actif(m, n):
            animer(m, n)


# ---- la pierre ------------------------------------------------------------------------------------------

def lancer_pierre(m):                                                # &68EF
    t = o(0)
    if m[t + 0xB] != 5:
        return
    if m[t + 0xA] == 0x0A:
        script, x = 2, m[t + 3] - 2
    elif m[t + 0xA] == 0x13:
        script, x = 1, m[t + 3] + 6
    else:
        return
    if actif(m, 1):
        return
    creer(m, 1, x & 0xFF, (m[t + 4] + 6) & 0xFF, script, 0x2C)


def arreter_pierre(m):                                               # &5D6F
    p = o(1)
    m[p + 4] = (m[p + 4] - 4) & 0xFF
    m[p] = 0; m[p + 7] = 0
    poser_etat(m, 1, 0x2D)


def pierre_sortie(m):                                                # &6932
    if not actif(m, 1) or m[o(1) + 0xA] & 0x7F == 0x2D:
        return
    x = m[o(1) + 3]
    if x == 0 or x >= 0x49:
        detruire(m, 1)


# ---- collisions (&5933) ---------------------------------------------------------------------------------

def collisions(m):
    hl = CONTACTS
    for n in (0, 1):
        if not actif(m, n):
            continue                                                 # les résultats précédents restent
        ix = o(n)
        for k in range(7, 1, -1):
            iy = o(k)
            r = 0xFF
            if actif(m, k) and not (m[iy + 0xA] & 0x7F == 0x2F and m[0xB403] < m[iy + 3]):
                dx = m[ix + 3] - m[iy + 3]
                d = m[ix + 0xF] if dx < 0 else m[iy + 0xF]
                if abs(dx) < ((d << 1) & 0xFF):
                    dy = m[ix + 4] - m[iy + 4]
                    if abs(dy) < (m[ix + 0x10] if dy < 0 else m[iy + 0x10]):
                        r = k
            m[hl + 7 - k] = r
        hl += 6


# ---- la pierre touche (&5CD7) ----------------------------------------------------------------------------

def coups_de_pierre(m):
    if not actif(m, 1):
        return
    for i in range(6):
        k = m[CONTACTS + 6 + i]
        if k != 0xFF:
            break
    else:
        return
    if m[o(1) + 0xA] & 0x7F == 0x2D:
        return
    b = o(k)
    if m[b + 0x12]:
        return
    pr = proprietes(m, m[b + 0xA] & 0x7F)
    if pr[0] & 0x80:                                                 # invulnérable : la pierre s'arrête
        arreter_pierre(m)
        return
    pierre = m[o(1) + 0xA] & 0x7F == 0x2C
    reste = m[COUPS + k - 2] - (1 if pierre else 2)
    m[COUPS + k - 2] = reste & 0xFF
    if reste > 0 and not (reste & 0xFF) >= 0x80:
        arreter_pierre(m)
        return
    tuer(m, k)
    points = pr[2] if pierre else pr[2] >> 1
    s = (mot(m, SCORE) + points) & 0xFFFF
    m[SCORE], m[SCORE + 1] = s & 0xFF, s >> 8
    arreter_pierre(m)


# ---- contacts de Tal (&59B5) -----------------------------------------------------------------------------

def degats(m, k):                                                    # &5B19, poignée 5
    b = o(k)
    if m[b + 0x12] or not actif(m, 0) or m[0xB412]:
        return
    s = m[b + 0xA] & 0x7F
    a = s
    accroupi = (0x05, 0x0E, 0x04, 0x0D)
    if s == 0x2F:
        a = m[0xB40A] & 0x7F
        if a in accroupi:
            return
    if a == 0x33 and m[0xB404] >= 0x78:
        a = m[0xB40A] & 0x7F
        if a in accroupi:
            return
    if m[REPIT] and s != 0x3B:
        return
    if s in (0x3B, 0x3C, 0x31, 0x30):
        m[REPIT] = 8
    pr = proprietes(m, s)
    d = pr[1] & 0x1F
    if m[A_PIED]:
        cible = VIE_TAL
    else:
        cible = ENERGIE_ARMURE
        d = (d >> 1) or 1
        if m[NEGATEUR] == 0:
            d = (d >> 1) or 1
    v = (m[cible] - d) & 0xFF
    m[cible] = 0 if v >= 0x80 else v
    if pr[0] & 0x80:
        return
    points = pr[2] if m[A_PIED] else pr[2] >> 1
    s2 = (mot(m, SCORE) + points) & 0xFFFF
    m[SCORE], m[SCORE + 1] = s2 & 0xFF, s2 >> 8
    tuer(m, k)
    m[COUPS + k - 2] = 0


def barriere(m):                                                     # &5BFF, poignée 8
    if m[A_PIED] == 0:                                               # l'armure rebondit (&68A3)
        m[0xB407] ^= 0x0C
        m[0xB520] ^= 0x03


def contacts_tal(m, poignees_hors_modele=None):
    """Appelle la poignée de chaque objet touché, de l'objet 2 à l'objet 7. Les poignées non modélisées
    (ramassage, armure, téléporteur, fin de partie) sont signalées dans `poignees_hors_modele`."""
    for i in range(5, -1, -1):
        k = m[CONTACTS + i]
        if k == 0xFF:
            continue
        e = (m[o(k) + 0xA] & 0x7F)
        pr = proprietes(m, e)
        if not pr[0] & 0x20:
            continue
        p = pr[0] & 0x1F
        if p == 5:
            degats(m, k)
        elif p == 8:
            barriere(m)
        elif p == 9:
            mine_posee(m)
        elif poignees_hors_modele is not None:
            poignees_hors_modele.append((p, k))


# ---- minuteries et générateur (&6217), apparition des objets (&7160) --------------------------------------

def liste_salle(m, salle):
    p = mot(m, 0x9BC7 + 2 * salle)
    return p, m[p]


def creer_liste(m, entree, n, nb):                                   # &7192 ; renvoie l'emplacement suivant
    """Crée `nb` objets de la liste de la salle à partir de l'entrée `entree`, dans les emplacements n, n+1…
    Un objet d'état &29 (matérialisation) interrompt la création : le reste viendra plus tard (&6217)."""
    p = m[0xB549] | m[0xB54A] << 8
    for i in range(nb):
        q = p + 4 * (entree + i)
        x, y, script, etat = m[q], m[q + 1], m[q + 2], m[q + 3]
        creer(m, n, x, y, script, etat)
        m[COUPS + n - 2] = proprietes(m, etat)[1] >> 5
        if etat == 0x29:
            m[CHRONO_GENERATEUR] = 0x28
            return None
        n += 1
    m[PROCHAIN] = n
    return n


def entrer_salle(m):
    """&723A, &7160, &71CD, &7202, &7113 : objets créés à l'entrée dans la salle &B4ED, une fois les huit
    emplacements libérés (&6A1F) ; Tal est réactivé ensuite (&6A2A)."""
    m[ACTIFS] = 0
    r = m[SALLE]
    if m[A_PIED] and r == m[0xB4F4]:                                 # l'armure, emplacement 7
        creer(m, 7, m[0xB4F6], m[0xB4F5], 0, 0x36)
    m[CHRONO_GENERATEUR] = 0xFF
    p, nb = liste_salle(m, r)
    m[0xB549], m[0xB54A] = (p + 1) & 0xFF, (p + 1) >> 8
    creer_liste(m, 0, 2, nb)
    for i in range(4):                                               # une pièce, emplacement 6
        q = 0x8F14 + 3 * i
        if m[0xB519 + i] and m[q] == r:
            creer(m, 6, m[q + 1], m[q + 2], 0, 0x1D + i)
            break
    for i in range(15):                                              # une cellule, emplacement 6 ou 7
        q = 0xA066 + 3 * i
        if m[q] == r:
            creer(m, 7 if m[ACTIFS] & 0x40 else 6, m[q + 1], m[q + 2], 0, 0x1C)
            m[0xB539], m[0xB53A] = q & 0xFF, q >> 8
            break
    for rangee in (0x13, 0x14, 0x15):                                # &7319 : jauge de radiation effacée
        texte(m, rangee, 0x1B, 0x8B8F)
    rayonnement(m)                                                   # &72C5
    if r < 2 and m[NEGATEUR]:                                        # rayonnement : verrou de sécurité
        m[VIE_TAL] = 0
        message(m, 0x12)
    m[ACTIFS] |= 1


def minuteries(m):                                                   # &6217
    if m[REPIT]:
        m[REPIT] -= 1
    m[0xB4F9] = (m[0xB4F9] + 1) & 0xFF
    if m[0xB517]:
        m[0xB517] -= 1
    if m[COUPS] == 0 or m[COUPS] >= 0x80:
        return
    c = m[CHRONO_GENERATEUR]
    if c == 0xFF:
        return
    if c:
        m[CHRONO_GENERATEUR] = c - 1
        return
    if m[o(2) + 0xA] & 0x7F != 0x29:
        return
    if actif(m, 2):
        tuer(m, 2)
        return
    p = m[0xB549] | m[0xB54A] << 8
    creer_liste(m, 1, 2, m[p - 1] - 1)
    m[CHRONO_GENERATEUR] = 0xFF


# ---- comportements particuliers de quelques salles --------------------------------------------------------

def canon(m):                                                        # &5642
    p = o(5)
    if m[p + 0xA] & 0x7F == 0x33 and m[p + 3] >= 0x46:
        detruire(m, 5)
        poser_etat(m, 2, 0x2B)
    if m[o(2) + 0xA] & 0x7F != 0x2B or actif(m, 5) or m[o(2) + 0xC]:
        return
    creer(m, 5, 0x1B, 0x7F, 0x29, 0x32)
    poser_etat(m, 2, 0x2B)


def goutte(m):                                                       # &55F5
    g = o(2)
    if not actif(m, 2):
        if m[g + 0xA] & 0x7F != 0x3A:
            return
        p = m[0xB549] | m[0xB54A] << 8                               # la goutte renaît en haut
        creer(m, 2, m[p], m[p + 1], m[p + 2], m[p + 3])
        return
    if m[g + 0xA] & 0x7F != 0x39 or m[g + 4] < 0x92:
        return
    m[g + 4] = 0x95
    poser_etat(m, 2, 0x3A)
    m[g + 0] = 0; m[g + 7] = 0


def volatile(m):                                                     # &5598
    n = m[PROCHAIN]
    b = o(n)
    if m[b + 0xA] & 0x7F == 0x2E and m[b + 4] >= 0xA0:
        detruire(m, n)
    if not actif(m, 2) or m[o(2) + 0xA] & 0x7F != 0x27:
        return
    if (m[ACTIFS] >> n) & 1 or m[o(2) + 0x12]:
        return
    creer(m, n, (m[o(2) + 3] + 5) & 0xFF, (m[o(2) + 4] + 0x15) & 0xFF, 0x23, 0x2E)


# ---- le panneau de l'armure (mode 1, lignes d'écran 136 à 199) ---------------------------------------------
# Tout est écrit dans la mémoire d'écran (&C000-&FFFF), comme le fait le jeu.

def ligne_suivante(a):                                               # adresse de la ligne d'écran suivante
    a += 0x800
    if a & 0x3800 == 0:
        a = a - 0x4000 + 0x50
    return a & 0xFFFF


def texte(m, rangee, col, adr):                                      # &6FBE et &701E
    while True:
        c = m[adr]
        if c == 0x24:
            return
        if c == 0x0D:
            rangee += 1; adr += 1; continue
        if c >= 0x80:
            m[0xB499] = m[0x8BEF + (c & 0x7F)]
            adr += 1; continue
        if 0x30 <= c < 0x3A:
            g = c - 0x0E
        elif 0x41 <= c < 0x5B:
            g = c - 0x40
        else:
            g = c
            for i in range(19):
                if m[0x8B3D + i] == c:
                    g = m[0x8B50 + i]
                    break
        src = 0x0400 + 16 * g
        e = (mot(m, 0x8BBD + 2 * rangee) + 2 * col) & 0xFFFF
        for _ in range(8):
            m[e] = m[src] & m[0xB499]
            m[(e + 1) & 0xFFFF] = m[src + 1] & m[0xB499]
            src += 2
            e = (e + 0x800) & 0xFFFF
        adr += 1; col += 1


def score_texte(m):                                                  # &56A8 : cinq chiffres en &8B82, puis &6FBE
    v = mot(m, SCORE_AFFICHE)
    for i, d in enumerate((10000, 1000, 100, 10)):
        m[0x8B82 + i] = (0x30 + v // d) & 0xFF
        v %= d
    m[0x8B86] = 0x30 + v
    texte(m, 0x14, 0x0A, 0x8B81)


def jauge(m, adr, var):                                              # &5DFC : la jauge rattrape la valeur, un cran par tour
    c, cible = m[var], m[var + 1]
    if cible == c:
        return
    if cible < c:
        c -= 1; b = 0xFF
    else:
        c += 1; b = 1
    m[var] = c
    adr += (c & 0x1C) >> 2
    motif = m[0x8EBE + (c & 3)]
    d = 0xF0
    if c & 0x1C == 0x1C:
        b = 1
    if c & 0x1C >= 0x10:
        d = 0xFF
    v = motif & d
    for _ in range(4):
        m[adr] = v
        if b == 0xFF:
            m[adr + 1] = 0
        adr = (adr + 0x800) & 0xFFFF


def bruit(m):                                                        # &5E56 : l'écran central montre la mémoire du jeu
    if m[0xB531]:
        return
    hl = mot(m, 0xB4F7)
    for n, de in ((3, 0xEE14), (8, 0xC664), (8, 0xC6B4), (4, 0xC704)):
        for _ in range(n):
            for k in range(10):
                m[de + k] = m[(hl + k) & 0xFFFF]
            hl = (hl + 10) & 0xFFFF
            de = (de + 0x800) & 0xFFFF
    m[0xB4F7], m[0xB4F8] = hl & 0xFF, hl >> 8


def image_piece(m, n):                                               # &5F83, &5F99, &5FC8 : image d'une pièce au centre
    if not 8 <= n < 0x0C:
        return
    a = 0xEE14
    for _ in range(0x17):
        for k in range(10):
            m[a + k] = 0
        a = ligne_suivante(a)
    src, de = 0x21D8 + (n - 8) * 0x60, 0xC666
    for _ in range(16):
        for k in range(6):
            m[de + k] = m[src + k]
        src += 6
        de = ligne_suivante(de)
    m[0xB531] = 0xFF


def lettre(m, hl):                                                   # &5F6B : la lettre suivante à faire défiler
    c = m[hl]
    a = 0 if c == 0x20 else (c - 0x40) & 0xFF
    m[0xB52B], m[0xB52C] = hl & 0xFF, hl >> 8
    g = 0x0400 + 16 * a
    m[0xB52D], m[0xB52E] = g & 0xFF, g >> 8


def message(m, n):                                                   # &5EA0 : file d'attente de 8 messages
    if m[A_PIED] & 1 and 8 <= n < 0x0C:                              # pièce ramassée à pied : différé (&5EFF)
        for i in range(4):
            if m[0xB53D + i] == 0xFF:
                m[0xB53D + i] = n
                break
        return
    autre = False
    for i in range(8):
        v = m[0xB521 + i]
        if v == n:
            return
        if v != 0xFF:
            autre = True
    b = m[0xB52A]
    m[0xB521 + b] = n
    m[0xB52A] = (b + 1) & 7
    if autre:
        return
    m[0xB530] = 0
    m[0xB529] = b
    image_piece(m, n)
    lettre(m, mot(m, 0xA093 + 2 * n))


def son_coupe(m):                                                    # &752A avec le son 0 sur la voie 0
    p = mot(m, 0x8AEF)
    m[0x7A5B] = m[0x7A5D] = p & 0xFF
    m[0x7A5C] = m[0x7A5E] = p >> 8
    for k in range(0x2A):
        m[0x7A5F + k] = 0


def message_suivant(m):                                              # &5FFC, au « $ » qui termine un texte
    m[0xB531] = 0
    i = 0xB521 + m[0xB529]
    if m[i]:
        m[i] = 0
        return mot(m, 0xA093)                                        # un blanc entre deux messages
    m[i] = 0xFF
    m[0xB529] = (m[0xB529] + 1) & 7
    n = m[0xB521 + m[0xB529]]
    if n == 0xFF:
        m[0xB530] = 0xFF                                             # plus rien à faire défiler
        son_coupe(m)
        return 0x7A5B                    # HL laissé par la routine de son (&752A, voie 0) : sans effet, le défilement s'arrête
    image_piece(m, n)
    hl = mot(m, 0xA093 + 2 * n)
    m[0xB52B], m[0xB52C] = hl & 0xFF, hl >> 8
    m[0xB530] = 0
    return hl


def defilement(m):                                                   # &5F12 : le texte avance d'un octet par tour
    """Renvoie True quand le texte atteint le caractère « y » (&79) : c'est le déclenchement de la fin (&5C31)."""
    if m[JEU_LANCE] or m[0xB530]:
        return False
    ix = mot(m, 0xB52D) + (1 if m[0xB52F] else 0)
    hl = 0xC74F
    for _ in range(8):
        for k in range(0x15):
            m[hl - 1 + k] = m[hl + k]
        m[hl + 0x14] = m[ix & 0xFFFF]
        hl = (hl + 0x800) & 0xFFFF
        ix += 2
    m[0xB52F] ^= 1
    if m[0xB52F]:
        return False
    hl = (mot(m, 0xB52B) + 1) & 0xFFFF                               # &5F55
    if m[hl] == 0x79:
        return True
    if m[hl] == 0x24:
        hl = message_suivant(m)
    lettre(m, hl)
    return False


def rayonnement(m, force=False):                                     # &72C5 (&72CA avec force) : radiation et affichage
    if m[JEU_LANCE] and not force:
        return
    r, b = m[SALLE], 6
    for i in range(6):
        if r < m[0x8B37 + i]:
            break
        b -= 1
    m[0xB538] = b
    texte(m, 0x17, 0x1B, 0x8B68 if b >= 5 else 0x8B97)
    q = 0x8B9A
    for _ in range(b + 1):
        texte(m, m[q], m[q + 1], q + 2)
        q += 5
    texte(m, 0x15, 0x1C, 0x8B94)


def palette_armure(m, dedans):                                       # &61BB, &61D2 : stylos 13 à 15 de la zone de jeu
    src = 0x8E06 if dedans else 0x8E03
    m[0x8E00:0x8E03] = m[src:src + 3]


def toutes_les_deux_secondes(m):                                     # &6F18, dans l'interruption, toutes les 100 images
    if m[A_PIED] == 0:                                               # dans l'armure : Tal récupère, salles &00-&01 usent l'armure
        if m[VIE_TAL] != 0x1F:
            m[VIE_TAL] += 1
        if m[SALLE] < 2:
            e = m[ENERGIE_ARMURE]
            if e < 2:
                m[ENERGIE_ARMURE] = 0
            elif e > 2:
                m[ENERGIE_ARMURE] = e - 2
    else:                                                            # à pied : la radiation use Tal (niveaux 2 à 4)
        r = m[0xB538]
        if 2 <= r < 5:
            v = (m[VIE_TAL] - (r >> 1)) & 0xFF
            m[VIE_TAL] = 0 if v >= 0x80 else v


def panneau_tour(m):                                                 # &5DDA
    """Jauges, écran central et défilement. Renvoie True si la fin de partie est déclenchée."""
    if m[JEU_LANCE]:
        return False
    jauge(m, 0xD69A, 0xB4FA)
    jauge(m, 0xD5FA, 0xB4FC)
    bruit(m)
    return defilement(m)


# ---- le tir de l'armure (&64EF, dans la logique de l'armure &5744) ---------------------------------------

def tir_pulsar(m):
    """Feu, armure tournée d'un côté (états &19 et &1B) : un rayon part dans l'emplacement 1. Le script du rayon
    (&03 vers la droite, &04 vers la gauche) est modifié en place : son premier pas reprend le mouvement de
    l'armure. Renvoie le numéro de message (&0E si le rayon n'est pas monté) ou None."""
    feu = m[0x7A4C] & 0x10
    e = m[0xB40A] & 0x7F
    if m[0xB51A]:
        return 0x0E if feu and e in (0x19, 0x1B) else None
    if not feu:
        return None
    if e == 0x19:
        script, etat, x = 4, 0x34, m[0xB403] - 6
    elif e == 0x1B:
        script, etat, x = 3, 0x32, m[0xB403] + 6
    else:
        return None
    if actif(m, 1):
        return None
    creer(m, 1, x & 0xFF, (m[0xB404] + 0x0E) & 0xFF, script, etat)
    m[0x98AA] = m[0x98BB] = m[0xB407]
    m[0x98AC] = m[0x98BD] = m[0xB408]
    m[0x98AD] = m[0x98BE] = m[0xB409]
    return None


# ---- la fin de partie ---------------------------------------------------------------------------------------

def mine_posee(m):                                                   # &5C0E, poignée 9 : la cible de la salle &00
    if m[0xB51B] or m[0xB40A] & 0x7F != 0x16 or not m[0xB407] & 2:
        return False
    poser_etat(m, 0, 0x17)
    message(m, 0x13)
    m[ACTIFS] = 0
    return True


def hasard(m):                                                       # &6584
    hl = mot(m, 0xB4EF)
    bc = hl
    hl = (hl * 3) & 0xFFFF
    bc = hl
    hl = (hl * 2) & 0xFFFF
    a = hl & 0xFF
    hl = (hl * 4 + bc) & 0xFFFF
    bc = hl
    hl = ((a << 8) | 0x29) - bc
    hl &= 0xFFFF
    m[0xB4EF], m[0xB4F0] = hl & 0xFF, hl >> 8
    return hl


def implosion(m):                                                    # &5C31 jusqu'à la boucle finale &5CA6
    """L'écran de jeu se désagrège (16 384 octets tirés au hasard mis à zéro), puis la scène finale :
    l'objet 4, état &3F, monte et descend au centre. Renvoie la liste des adresses effacées."""
    m[ACTIFS] = 0
    effaces = []
    for _ in range(0x40 * 256):
        a = hasard(m)
        if (a >> 8) & 7 < 5:
            a |= 0xC000
            m[a] = 0
            effaces.append(a)
    m[ACTIFS] = 0
    creer(m, 4, 0x26, 0x68, 0x2D, 0x3F)
    m[0xB529] = m[0xB52A] = m[0xB52F] = 0
    m[0xB530] = 0xFF
    for a in (0xB521, 0xB523, 0xB525, 0xB527):
        m[a] = m[a + 1] = 0xFF
    return effaces


def boucle_finale(m):                                                # &5CA6 : jusqu'à ce que le joueur appuie sur feu
    fondus(m)
    animateur(m)
    panneau_tour(m)
    message(m, 0x14)


def activation(m):                                                   # &604F
    """Mise en route de l'armure, lancée à la première entrée (&6112 : &B513 = 0, pointeur &8E12, &B514 = 7).
    Chaque tour lit un bit d'un motif (le panneau clignote) ; au premier octet nul, la partie est vraiment
    lancée : &B512 = 0 (jauges, score, ramassage, messages). Renvoie le bit lu (couleur du panneau) ou None."""
    if m[0xB513]:
        return None
    hl = mot(m, 0xB515)
    a = (m[0xB514] - 1) & 0xFF
    if a == 0:
        a = 7
        hl += 1
    m[0xB515], m[0xB516] = hl & 0xFF, hl >> 8
    m[0xB514] = a
    v = m[hl]
    if v == 0:
        m[0xB513] = 0xFF
        m[JEU_LANCE] = 0
        message(m, 0x11)
        return None
    bit = (v << a) >> 8 & 1                                          # &61E9 ou &61F8 : stylos 1 à 3 du panneau
    src = 0x8E0C if bit else 0x8E0F
    m[0x8E09:0x8E0C] = m[src:src + 3]
    return bit


def fin_de_tour(m, hors=None):
    """La boucle principale de &5704 à son retour en &54FA, hors dessin, son et messages."""
    fondus(m)                                                        # &5704
    if m[0xB40A] & 0x7F == 0x17:
        m[0xB407] = 0
    animateur(m)                                                     # &6B0E
    lancer_pierre(m)                                                 # &68EF
    fin = panneau_tour(m)                                            # &5DDA : jauges, écran central, défilement
    if fin:
        return 'fin'
    collisions(m)                                                    # &5933
    coups_de_pierre(m)                                               # &5CD7
    contacts_tal(m, hors)                                            # &59B5
    pierre_sortie(m)                                                 # &6932
    minuteries(m)                                                    # &6217
    bit = activation(m)                                              # &604F
    if not m[JEU_LANCE] and mot(m, SCORE_AFFICHE) < mot(m, SCORE):   # &568D
        s = mot(m, SCORE_AFFICHE) + 1
        m[SCORE_AFFICHE], m[SCORE_AFFICHE + 1] = s & 0xFF, s >> 8
        score_texte(m)
    canon(m)                                                         # &5642
    goutte(m)                                                        # &55F5
    volatile(m)                                                      # &5598
    return bit


# ---- mort et renaissance de Tal à pied (&579C, &57D7), dans la logique de Tal -------------------------------

def mort_de_tal(m):
    """&579C puis &57D7 : renvoie 'mort', 'renaissance', 'fin' ou None."""
    t = o(0)
    r = None
    if m[VIE_TAL] == 0 and m[t + 0xA] & 0x7F not in (0x10, 0x07, 0x08, 0x11) and m[t] == 0:
        m[t + 4] = (m[t + 4] + 6) & 0xFF
        poser_etat(m, 0, 0x14)
        m[t] = 0x2A; m[t + 1] = 0; m[t + 2] = 0
        m[0xB551] >>= 1
        r = 'mort'
    if m[t + 0xA] == 0x94:
        if m[0xB551] & 1:
            return 'fin'
        m[0xB550] = (m[0xB550] + 1) & 0xFF
        m[VIE_TAL] = 0x1F
        m[t + 4] = (m[t + 4] - 0x0B) & 0xFF
        poser_etat(m, 0, 0x15)
        m[t] = 0x2B; m[t + 1] = 0; m[t + 2] = 0
        r = 'renaissance'
    return r
