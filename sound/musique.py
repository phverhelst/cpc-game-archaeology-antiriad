"""La musique du titre (sons 1, 2 et 3) mise en mesures : événements par voix, découpage en valeurs de notes,
orthographe des hauteurs (sol mineur : si♭ et mi♭ à la clé). Sert à la gravure (gravure.py), au MusicXML et
au MIDI (export.py).
"""
import partition as P

DEBUT_MESURE = 24                 # mesures de 3/4 (24 unités) dès le début : les phrases font 96 unités, 4 mesures
VALEURS = [24, 16, 12, 8, 6, 4, 3, 2, 1]
TYPES = {24: ('half', 1), 16: ('half', 0), 12: ('quarter', 1), 8: ('quarter', 0), 6: ('eighth', 1), 4: ('eighth', 0),
         3: ('16th', 1), 2: ('16th', 0), 1: ('32nd', 0)}
ORTHO = [('C', 0), ('C', 1), ('D', 0), ('E', -1), ('E', 0), ('F', 0), ('F', 1), ('G', 0), ('A', -1), ('A', 0), ('B', -1), ('B', 0)]
CLE = {'B': -1, 'E': -1}
LETTRES = 'CDEFGAB'


def evenements(m, son):
    """[(début, durée, genre, valeur)] : genre 'note' (MIDI), 'perc' (période de bruit) ou 'silence' ; plus les
    changements de tempo [(début, tempo)]. Les notes jouées avec le son coupé (bruit seul) sont des percussions."""
    ev, _ = P.voix(m, son)
    t, sortie, tempos, mix = 0, [], [], 1
    bruit_p = 0
    for e in ev:
        g, v, d = e
        if g == 'tempo':
            tempos.append((t, v))
        elif g == 'mixage':
            mix = v
        elif g == 'bruit':
            bruit_p = v
            if d:
                sortie.append((t, d, 'perc', v)); t += d
        elif g == 'note':
            if mix & 1:
                sortie.append((t, d, 'note', v + 12))
            else:
                sortie.append((t, d, 'perc', bruit_p))
            t += d
        elif g == 'silence':
            sortie.append((t, d, 'silence', None)); t += d
    return sortie, tempos, t


# Les trois parties du morceau, délimitées par les changements de tempo de la voix 1, et leur découpage en
# mesures. La première partie est en 3/4, comme la transcription C64 : ses phrases font 96 unités. La deuxième
# commence par 6 unités (une croche pointée) avant des mesures de 4/4 : la basse y tient des notes de 96 unités
# à partir de là. La troisième est en 4/4 : la basse y change de note toutes les 64 unités. C'est une lecture :
# le code ne connaît que des durées.
PARTIES = [(0, 680, 24, 0), (680, 1070, 32, 6), (1070, 2118, 32, 0)]   # début, fin, mesure, levée


def mesures(total):
    """Débuts et longueurs des mesures."""
    res = []
    for debut, fin, L, levee in PARTIES:
        t = debut
        if levee:
            res.append((t, levee)); t += levee
        while t < min(fin, total):
            res.append((t, min(L, fin - t))); t += L
    return res


def tempo_reel(v):
    """La commande 85 v règle 6000 // (8 v) centièmes de seconde par unité : le tempo entendu, en noires par
    minute, n'est v qu'à l'arrondi près (107 → 107,1 ; 150 → 150 ; mais 155 → 187,5)."""
    return 6000 / (8 * (6000 // (8 * v)))


def chiffrage(L):
    return {24: (3, 4), 32: (4, 4), 8: (1, 4), 16: (2, 4), 6: (3, 16), 12: (3, 8)}.get(L, (L, 32))


def decouper(p, d, longueur):
    """Découpe une durée d qui commence en p (position dans la mesure) en valeurs écrites, sans franchir un temps
    sauf depuis le début d'un temps."""
    morceaux = []
    while d > 0:
        for v in VALEURS:
            if v > d or p + v > longueur:
                continue
            if v >= 8 and p % 8:
                continue
            if v < 8 and p % 8 + v > 8:
                continue
            break
        morceaux.append((p, v)); p += v; d -= v
    return morceaux


def voix_en_mesures(evs, total):
    """Pour chaque mesure, la liste des figures : dict(pos, val, genre, valeur, lie_suivant)."""
    ms = mesures(total)
    res = [[] for _ in ms]
    for (t, d, g, v) in evs:
        fin = t + d
        morceaux = []
        for i, (a, L) in enumerate(ms):
            b = a + L
            if b <= t or a >= fin:
                continue
            s, e = max(a, t), min(b, fin)
            for (p, val) in decouper(s - a, e - s, L):
                morceaux.append((i, p, val))
        for k, (i, p, val) in enumerate(morceaux):
            res[i].append({'pos': p, 'val': val, 'genre': g, 'valeur': v, 'lie': g == 'note' and k < len(morceaux) - 1})
    return ms, res


def orthographe(midi):
    lettre, alt = ORTHO[midi % 12]
    octave = midi // 12 - 1
    return lettre, alt, octave


def diatonique(lettre, octave):
    return LETTRES.index(lettre) + 7 * octave
